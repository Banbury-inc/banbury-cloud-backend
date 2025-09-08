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
        users_col = db['users']  # Need access to users collection for bearer tokens

        self.stdout.write(self.style.SUCCESS(f'Starting TaskStudio daemon (interval={interval}s, batch={batch})'))
        print(f"Monitoring database: {db.name}")
        print(f"Collection: {tasks_col.name}")
        print("=" * 60)

        while True:
            try:
                now = datetime.now(timezone.utc)
                print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')} UTC] Scanning for due tasks...")
                
                # Find due scheduled tasks across all users
                due = list(tasks_col.find({
                    'status': 'scheduled',
                    'scheduled_date': { '$lte': now }
                }).limit(batch))
                
                if len(due) > 0:
                    print(f"✓ Found {len(due)} due tasks to process")
                else:
                    print(f"• No due tasks found (checked up to {batch} scheduled tasks)")
                for doc in due:
                    task_id = str(doc.get('_id'))
                    username = doc.get('username', '')
                    description = doc.get('description', '') or ''
                    try:
                        tasks_col.update_one({ '_id': ObjectId(doc['_id']) }, { '$set': { 'status': 'running', 'updated_at': now } })
                        print(f"▶ Processing task {task_id} for user '{username}'")
                        print(f"  Task description: {description[:100]}{'...' if len(description) > 100 else ''}")
                        
                        # Get user's bearer token from users collection
                        user_doc = users_col.find_one({'username': username})
                        if not user_doc:
                            raise Exception(f"User '{username}' not found in users collection")
                        
                        user_bearer_token = user_doc.get('bearer_token')
                        if not user_bearer_token:
                            raise Exception(f"No bearer token found for user '{username}'. User may need to log in again.")
                        
                        print(f"  🔑 Using user's bearer token for authentication")
                        print(f"  🤖 Calling LangGraph API...")
                        result_text = run_prompt_via_langgraph(description, user_bearer_token)
                        
                        # Mark completed
                        tasks_col.update_one(
                            { '_id': ObjectId(doc['_id']) },
                            { '$set': { 'status': 'completed', 'result': result_text, 'updated_at': datetime.now(timezone.utc) } }
                        )
                        print(f"✅ Task {task_id} completed for user '{username}'")
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
                            print(f"💾 Saved conversation for task {task_id}")
                        except Exception as ce:
                            print(f"⚠️  Failed to save conversation for task {task_id}: {str(ce)}")
                    except Exception as te:
                        error_msg = str(te)
                        # Check if it's a token-related error
                        if 'bearer token' in error_msg.lower() or 'authentication' in error_msg.lower():
                            print(f"🔑 Authentication error for user '{username}': {error_msg}")
                            print(f"   User may need to log in again to refresh their token")
                        else:
                            print(f"❌ Task {task_id} failed for user '{username}': {error_msg}")
                        
                        tasks_col.update_one(
                            { '_id': ObjectId(doc['_id']) },
                            { '$set': { 'status': 'failed', 'error': error_msg, 'updated_at': datetime.now(timezone.utc) } }
                        )
                
                print(f"⏱️  Sleeping for {interval} seconds...")
                time.sleep(interval)
            except Exception as e:
                self.stderr.write(f"Daemon error: {e}")
                time.sleep(interval)


