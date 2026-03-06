import os
import time
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from pymongo.mongo_client import MongoClient


class Command(BaseCommand):
    help = 'Continuously process due scheduled flows, executing them server-side without a browser.'

    def get_adaptive_interval(self, flows_col, default_interval):
        try:
            next_flow = flows_col.find_one(
                {"schedule_enabled": True, "schedule_next_run": {"$ne": None}},
                sort=[("schedule_next_run", 1)],
            )
            if not next_flow:
                return min(default_interval * 10, 300)

            scheduled = next_flow.get("schedule_next_run")
            if not scheduled:
                return default_interval

            now = datetime.now(timezone.utc)
            if scheduled.tzinfo is None:
                scheduled = scheduled.replace(tzinfo=timezone.utc)
            time_until = (scheduled - now).total_seconds()

            if time_until <= 0:
                return 1
            if time_until <= 60:
                return 10
            if time_until <= 300:
                return 30
            if time_until <= 1800:
                return 120
            return 300
        except Exception as e:
            print(f"Error calculating adaptive interval: {e}")
            return default_interval

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=30, help='Default seconds between scans')
        parser.add_argument('--batch', type=int, default=20, help='Max flows per scan')
        parser.add_argument('--adaptive', action='store_true', help='Use adaptive interval')

    def handle(self, *args, **options):
        default_interval = int(options.get('interval') or 30)
        batch = int(options.get('batch') or 20)
        adaptive = options.get('adaptive', False)

        mongo_uri = os.getenv(
            'MONGO_URI',
            'mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority',
        )
        client = MongoClient(mongo_uri)
        db = client['NeuraNet']
        flows_col = db['flows']
        users_col = db['users']

        mode_desc = "adaptive" if adaptive else f"fixed {default_interval}s"
        self.stdout.write(self.style.SUCCESS(
            f'Starting Flow Scheduler daemon ({mode_desc} interval, batch={batch})'
        ))
        print(f"Monitoring collection: {flows_col.name}")
        print("=" * 60)

        while True:
            try:
                now = datetime.now(timezone.utc)
                now_naive = now.replace(tzinfo=None)
                print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')} UTC] Scanning for due flows...")

                due_query = {
                    "schedule_enabled": True,
                    "schedule_next_run": {"$lte": now_naive},
                    "$or": [
                        {"schedule_end_date": None},
                        {"schedule_end_date": {"$gte": now_naive}},
                    ],
                }
                due_flows = list(flows_col.find(due_query).limit(batch))

                if due_flows:
                    print(f"✓ Found {len(due_flows)} due flow(s) to process")
                else:
                    print(f"• No due flows found")

                for flow_doc in due_flows:
                    flow_id = flow_doc.get("id", "?")
                    username = flow_doc.get("username", "")
                    flow_name = flow_doc.get("name", "Untitled")

                    try:
                        print(f"▶ Executing flow '{flow_name}' ({flow_id}) for user '{username}'")

                        flows_col.update_one(
                            {"id": flow_id, "username": username},
                            {"$set": {"last_run_status": "running", "updated_at": now_naive}},
                        )

                        logs, success = self._execute_flow(flow_doc, username)
                        status_val = "success" if success else "failed"

                        flows_col.update_one(
                            {"id": flow_id, "username": username},
                            {"$set": {
                                "last_run_status": status_val,
                                "last_run_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow(),
                            }},
                        )

                        self._advance_schedule(flows_col, flow_doc)

                        log_preview = "; ".join(logs[-3:]) if logs else ""
                        if success:
                            print(f"✅ Flow '{flow_name}' completed successfully")
                        else:
                            print(f"❌ Flow '{flow_name}' failed: {log_preview}")

                    except Exception as te:
                        print(f"❌ Flow '{flow_name}' ({flow_id}) error: {te}")
                        flows_col.update_one(
                            {"id": flow_id, "username": username},
                            {"$set": {
                                "last_run_status": "failed",
                                "last_run_at": datetime.utcnow(),
                                "updated_at": datetime.utcnow(),
                            }},
                        )
                        self._advance_schedule(flows_col, flow_doc)

                if adaptive:
                    next_interval = self.get_adaptive_interval(flows_col, default_interval)
                    print(f"⏱️  Adaptive mode: sleeping for {next_interval} seconds...")
                else:
                    next_interval = default_interval
                    print(f"⏱️  Fixed mode: sleeping for {next_interval} seconds...")

                time.sleep(next_interval)

            except Exception as e:
                self.stderr.write(f"Daemon error: {e}")
                time.sleep(default_interval)

    def _execute_flow(self, flow: dict, username: str):
        """Execute a flow graph. Re-uses the same logic as views._execute_flow."""
        from collections import defaultdict, deque
        from apps.flows.executors import execute_node

        graph_json = flow.get('graph_json', {})
        node_list = graph_json.get('nodes', [])
        edge_list = graph_json.get('edges', [])

        nodes = {n['id']: n for n in node_list}

        adj = defaultdict(list)
        reverse_adj = defaultdict(list)
        in_degree = defaultdict(int)

        for edge in edge_list:
            src = edge.get('source', '')
            tgt = edge.get('target', '')
            if src and tgt:
                adj[src].append(tgt)
                reverse_adj[tgt].append(src)
                in_degree[tgt] += 1

        queue = deque(nid for nid in nodes if in_degree[nid] == 0)

        node_outputs = {}
        logs = []
        executed_count = 0
        success = True

        logs.append(
            f"Starting flow '{flow.get('name', '?')}' with {len(nodes)} node(s) and {len(edge_list)} edge(s)."
        )

        while queue:
            nid = queue.popleft()
            node = nodes.get(nid)
            if node is None:
                continue

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

            for tgt in adj[nid]:
                in_degree[tgt] -= 1
                if in_degree[tgt] == 0:
                    queue.append(tgt)

        if executed_count < len(nodes):
            skipped = len(nodes) - executed_count
            logs.append(f"  ⚠ {skipped} node(s) were not reached.")

        if success:
            logs.append("Flow completed successfully.")
        else:
            logs.append("Flow completed with errors.")

        return logs, success

    def _advance_schedule(self, flows_col, flow_doc):
        """Compute and set the next scheduled run time."""
        from apps.flows.models import compute_next_run

        flow_id = flow_doc.get("id")
        username = flow_doc.get("username")
        now = datetime.utcnow()

        next_run = compute_next_run(
            pattern=flow_doc.get("schedule_pattern", "daily"),
            time_of_day=flow_doc.get("schedule_time", "09:00"),
            timezone_str=flow_doc.get("schedule_timezone", "UTC"),
            days_of_week=flow_doc.get("schedule_days_of_week"),
            day_of_month=flow_doc.get("schedule_day_of_month"),
            interval_minutes=flow_doc.get("schedule_interval_minutes"),
            after=now,
        )

        end_date = flow_doc.get("schedule_end_date")
        if end_date and next_run and next_run > end_date:
            flows_col.update_one(
                {"id": flow_id, "username": username},
                {"$set": {
                    "schedule_enabled": False,
                    "schedule_next_run": None,
                    "schedule_last_triggered": now,
                    "updated_at": now,
                }},
            )
            print(f"  ⏹ Schedule ended for flow '{flow_doc.get('name', '?')}' (past end date)")
            return

        flows_col.update_one(
            {"id": flow_id, "username": username},
            {"$set": {
                "schedule_next_run": next_run,
                "schedule_last_triggered": now,
                "updated_at": now,
            }},
        )
        if next_run:
            print(f"  ⏭ Next run for '{flow_doc.get('name', '?')}': {next_run.strftime('%Y-%m-%d %H:%M:%S')} UTC")
