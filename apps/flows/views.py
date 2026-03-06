import json
from collections import defaultdict, deque
from datetime import datetime, timezone
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import Flow, flows_collection, users_collection, compute_next_run
from .executors import execute_node


def _get_username(request):
    return getattr(request, 'username_from_token', None)


def _store_user_bearer_token(request, username: str):
    """Extract and store the user's bearer token for daemon access."""
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            bearer_token = auth_header[7:]
            users_collection.update_one(
                {"username": username},
                {"$set": {
                    "bearer_token": bearer_token,
                    "token_updated_at": datetime.utcnow(),
                }},
            )
            return True
    except Exception:
        pass
    return False


def _execute_flow(flow: dict, username: str) -> tuple[list[str], bool]:
    """
    Execute a flow graph using Kahn's topological sort algorithm.

    Returns (logs, success).
    Each node is executed in dependency order; its output is passed as input
    to downstream nodes so that template variables can be resolved.
    """
    graph_json = flow.get('graph_json', {})
    node_list = graph_json.get('nodes', [])
    edge_list = graph_json.get('edges', [])

    # Index nodes by id
    nodes = {n['id']: n for n in node_list}

    # Build adjacency list (source -> [target, ...]) and reverse (target -> [source, ...])
    adj: dict[str, list[str]] = defaultdict(list)
    reverse_adj: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = defaultdict(int)

    for edge in edge_list:
        src = edge.get('source', '')
        tgt = edge.get('target', '')
        if src and tgt:
            adj[src].append(tgt)
            reverse_adj[tgt].append(src)
            in_degree[tgt] += 1

    # Kahn's algorithm — start with nodes that have no incoming edges
    queue: deque[str] = deque(
        nid for nid in nodes if in_degree[nid] == 0
    )

    node_outputs: dict[str, dict] = {}
    logs: list[str] = []
    executed_count = 0
    success = True

    logs.append(
        f"Starting flow '{flow['name']}' with {len(nodes)} node(s) and {len(edge_list)} edge(s)."
    )

    while queue:
        nid = queue.popleft()
        node = nodes.get(nid)
        if node is None:
            continue

        # Gather outputs from all upstream (source) nodes
        inputs = {
            src_id: node_outputs[src_id]
            for src_id in reverse_adj[nid]
            if src_id in node_outputs
        }

        label = node.get('data', {}).get('label') or node.get('type', nid)
        logs.append(f"  → Executing [{node.get('type', '?')}] \"{label}\"…")

        result = execute_node(node, inputs, username)
        node_outputs[nid] = result
        executed_count += 1

        status = result.get('status', 'unknown')
        if status == 'failed':
            error = result.get('error', 'Unknown error')
            logs.append(f"    ✗ Failed: {error}")
            success = False
        elif status == 'skipped':
            logs.append(f"    ⟳ Skipped: {result.get('note', '')}")
        else:
            # Summarise output
            data = result.get('data', {})
            if isinstance(data, dict):
                summary_parts = []
                for k, v in data.items():
                    if isinstance(v, list):
                        summary_parts.append(f"{k}={len(v)} items")
                    elif isinstance(v, str) and len(v) > 60:
                        summary_parts.append(f"{k}=…")
                    else:
                        summary_parts.append(f"{k}={v!r}")
                summary = ', '.join(summary_parts[:3])
            else:
                summary = str(data)[:80]
            logs.append(f"    ✓ {summary or 'done'}")

        # Reduce in-degree for all downstream nodes
        for tgt in adj[nid]:
            in_degree[tgt] -= 1
            if in_degree[tgt] == 0:
                queue.append(tgt)

    if executed_count < len(nodes):
        skipped = len(nodes) - executed_count
        logs.append(f"  ⚠ {skipped} node(s) were not reached (possible cycle or disconnected node).")

    if success:
        logs.append("Flow completed successfully.")
    else:
        logs.append("Flow completed with errors.")

    return logs, success


@csrf_exempt
def flows_list(request):
    """GET /flows/  – list user flows
       POST /flows/ – create a new flow
    """
    username = _get_username(request)
    if not username:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "GET":
        flows = Flow.list_for_user(username)
        return JsonResponse({"flows": flows})

    if request.method == "POST":
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            body = {}
        name = body.get("name", "Untitled Flow")
        flow = Flow.create(username, name)
        return JsonResponse(flow, status=201)

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def flow_detail(request, flow_id: str):
    """GET /flows/{id}/    – get a flow
       PUT /flows/{id}/    – update graph / name
       DELETE /flows/{id}/ – delete a flow
    """
    username = _get_username(request)
    if not username:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    if request.method == "GET":
        flow = Flow.get(flow_id, username)
        if flow is None:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse(flow)

    if request.method in ("PUT", "PATCH"):
        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            body = {}

        updates: dict = {}
        if "name" in body:
            updates["name"] = body["name"]
        if any(k in body for k in ("nodes", "edges", "viewport")):
            existing = Flow.get(flow_id, username)
            if existing is None:
                return JsonResponse({"error": "Not found"}, status=404)
            graph = dict(existing.get("graph_json", {}))
            if "nodes" in body:
                graph["nodes"] = body["nodes"]
            if "edges" in body:
                graph["edges"] = body["edges"]
            if "viewport" in body:
                graph["viewport"] = body["viewport"]
            updates["graph_json"] = graph

        flow = Flow.update(flow_id, username, updates)
        if flow is None:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse(flow)

    if request.method == "DELETE":
        deleted = Flow.delete(flow_id, username)
        if not deleted:
            return JsonResponse({"error": "Not found"}, status=404)
        return JsonResponse({"success": True, "message": "Flow deleted"})

    return JsonResponse({"error": "Method not allowed"}, status=405)


@csrf_exempt
def flow_run(request, flow_id: str):
    """POST /flows/{id}/run/ – execute the flow"""
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    username = _get_username(request)
    if not username:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    flow = Flow.get(flow_id, username)
    if flow is None:
        return JsonResponse({"error": "Not found"}, status=404)

    # Mark running
    flows_collection.update_one(
        {"id": flow_id, "username": username},
        {"$set": {"last_run_status": "running", "updated_at": datetime.utcnow()}},
    )

    logs, success = _execute_flow(flow, username)

    status_val = "success" if success else "failed"
    flows_collection.update_one(
        {"id": flow_id, "username": username},
        {
            "$set": {
                "last_run_status": status_val,
                "last_run_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return JsonResponse({"success": success, "logs": logs})


@csrf_exempt
def flow_schedule(request, flow_id: str):
    """GET  /flows/{id}/schedule/ – get schedule config
       PUT  /flows/{id}/schedule/ – update schedule config
    """
    username = _get_username(request)
    if not username:
        return JsonResponse({"error": "Unauthorized"}, status=401)

    flow = Flow.get(flow_id, username)
    if flow is None:
        return JsonResponse({"error": "Not found"}, status=404)

    if request.method == "GET":
        return JsonResponse({
            "schedule_enabled": flow.get("schedule_enabled", False),
            "schedule_pattern": flow.get("schedule_pattern"),
            "schedule_time": flow.get("schedule_time"),
            "schedule_days_of_week": flow.get("schedule_days_of_week"),
            "schedule_day_of_month": flow.get("schedule_day_of_month"),
            "schedule_interval_minutes": flow.get("schedule_interval_minutes"),
            "schedule_timezone": flow.get("schedule_timezone", "UTC"),
            "schedule_next_run": flow.get("schedule_next_run"),
            "schedule_end_date": flow.get("schedule_end_date"),
            "schedule_last_triggered": flow.get("schedule_last_triggered"),
        })

    if request.method in ("PUT", "PATCH"):
        _store_user_bearer_token(request, username)

        try:
            body = json.loads(request.body)
        except (json.JSONDecodeError, ValueError):
            return JsonResponse({"error": "Invalid JSON"}, status=400)

        enabled = body.get("schedule_enabled", False)
        pattern = body.get("schedule_pattern", "daily")
        time_of_day = body.get("schedule_time", "09:00")
        days_of_week = body.get("schedule_days_of_week")
        day_of_month = body.get("schedule_day_of_month")
        interval_minutes = body.get("schedule_interval_minutes")
        tz_str = body.get("schedule_timezone", "UTC")

        end_date = None
        if body.get("schedule_end_date"):
            try:
                end_date = datetime.fromisoformat(
                    body["schedule_end_date"].replace("Z", "+00:00")
                )
                if end_date.tzinfo:
                    end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)
            except (ValueError, TypeError):
                return JsonResponse({"error": "Invalid schedule_end_date"}, status=400)

        valid_patterns = [
            "every_minute", "hourly", "daily", "weekly",
            "monthly", "custom_interval",
        ]
        if enabled and pattern not in valid_patterns:
            return JsonResponse({
                "error": f"Invalid pattern. Must be one of: {', '.join(valid_patterns)}"
            }, status=400)

        next_run = None
        if enabled:
            next_run = compute_next_run(
                pattern=pattern,
                time_of_day=time_of_day,
                timezone_str=tz_str,
                days_of_week=days_of_week,
                day_of_month=day_of_month,
                interval_minutes=interval_minutes,
            )

        updates = {
            "schedule_enabled": enabled,
            "schedule_pattern": pattern if enabled else None,
            "schedule_time": time_of_day if enabled else None,
            "schedule_days_of_week": days_of_week if enabled else None,
            "schedule_day_of_month": day_of_month if enabled else None,
            "schedule_interval_minutes": interval_minutes if enabled else None,
            "schedule_timezone": tz_str,
            "schedule_next_run": next_run,
            "schedule_end_date": end_date,
        }

        updated_flow = Flow.update(flow_id, username, updates)
        if updated_flow is None:
            return JsonResponse({"error": "Not found"}, status=404)

        return JsonResponse(updated_flow)

    return JsonResponse({"error": "Method not allowed"}, status=405)
