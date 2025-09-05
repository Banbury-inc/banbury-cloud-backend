import os
import time
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId
from apps.tasks.ai_runner import run_prompt_via_langgraph
from apps.conversations.models import Conversation


class Command(BaseCommand):
    help = 'Continuously process due TaskStudio tasks for all users, using LangGraph stream and saving results.'

    def add_arguments(self, parser):
        parser.add_argument('--interval', type=int, default=30, help='Seconds between scans')
        parser.add_argument('--batch', type=int, default=50, help='Max tasks per scan')

    def handle(self, *args, **options):
        interval = int(options.get('interval') or 30)
        batch = int(options.get('batch') or 50)

        mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority')
        client = MongoClient(mongo_uri)
        db = client['NeuraNet']
        tasks_col = db['taskstudio_tasks']

        self.stdout.write(self.style.SUCCESS(f'Starting TaskStudio daemon (interval={interval}s, batch={batch})'))

        while True:
            try:
                now = datetime.now(timezone.utc)
                # Find due scheduled tasks across all users
                due = list(tasks_col.find({
                    'status': 'scheduled',
                    'scheduled_date': { '$lte': now }
                }).limit(batch))
                print(f"Found {len(due)} due tasks")
                for doc in due:
                    task_id = str(doc.get('_id'))
                    username = doc.get('username', '')
                    description = doc.get('description', '') or ''
                    try:
                        tasks_col.update_one({ '_id': ObjectId(doc['_id']) }, { '$set': { 'status': 'running', 'updated_at': now } })
                        print(f"Processing task {task_id} for user {username}")
                        # Call AI via Banbury-Website langgraph stream
                        bearer = os.getenv('DAEMON_BEARER')  # optional service token
                        result_text = run_prompt_via_langgraph(description, bearer)
                        # Mark completed
                        tasks_col.update_one(
                            { '_id': ObjectId(doc['_id']) },
                            { '$set': { 'status': 'completed', 'result': result_text, 'updated_at': datetime.now(timezone.utc) } }
                        )
                        print(f"Marked task {task_id} for user {username} as completed")
                        # Save conversation directly via model (no HTTP auth needed)
                        try:
                            Conversation.save_conversation(
                                username=username,
                                title=f"Task: {doc.get('title','Scheduled Task')}",
                                messages=[
                                    { 'role': 'user', 'content': [{ 'type': 'text', 'text': description }] },
                                    { 'role': 'assistant', 'content': [{ 'type': 'text', 'text': result_text }] },
                                ],
                                metadata={ 'taskId': task_id }
                            )
                            print(f"Saved conversation for task {task_id} for user {username}")
                        except Exception:
                            print(f"Failed to save conversation for task {task_id} for user {username}")
                    except Exception as te:
                        tasks_col.update_one(
                            { '_id': ObjectId(doc['_id']) },
                            { '$set': { 'status': 'failed', 'error': str(te), 'updated_at': datetime.now(timezone.utc) } }
                        )
                        print(f"Marked task {task_id} for user {username} as failed")
                time.sleep(interval)
            except Exception as e:
                self.stderr.write(f"Daemon error: {e}")
                time.sleep(interval)


