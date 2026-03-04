import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError

from .models import Flow, flows_collection


def _get_username(request) -> str | None:
    auth = JWTAuthentication()
    try:
        validated = auth.authenticate(request)
        if validated is None:
            return None
        user, _ = validated
        return user.username
    except (InvalidToken, TokenError):
        return None


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

    logs = []
    success = True
    try:
        nodes = flow.get("graph_json", {}).get("nodes", [])
        edges = flow.get("graph_json", {}).get("edges", [])
        logs.append(f"Starting flow '{flow['name']}' with {len(nodes)} nodes and {len(edges)} edges.")
        for node in nodes:
            logs.append(f"  Executing node: {node.get('data', {}).get('label', node.get('id', '?'))}")
        logs.append("Flow completed successfully.")
    except Exception as exc:
        success = False
        logs.append(f"Error: {str(exc)}")

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
