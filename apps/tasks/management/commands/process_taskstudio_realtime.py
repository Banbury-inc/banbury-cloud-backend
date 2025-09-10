import os
import time
import threading
from datetime import datetime, timezone
from django.core.management.base import BaseCommand
from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId
from apps.tasks.ai_runner import run_prompt_via_langgraph
from apps.conversations.models import Conversation


class Command(BaseCommand):
    help = 'Real-time TaskStudio processor using MongoDB change streams + scheduled task monitoring'

    def add_arguments(self, parser):
        parser.add_argument('--batch', type=int, default=50, help='Max tasks per batch')
        parser.add_argument('--initial-scan', action='store_true', help='Perform initial scan for existing due tasks')

    def handle(self, *args, **options):
        batch = int(options.get('batch') or 50)
        initial_scan = options.get('initial_scan', False)

        mongo_uri = os.getenv('MONGO_URI', 'mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority')
        client = MongoClient(mongo_uri)
        db = client['NeuraNet']
        tasks_col = db['taskstudio_tasks']
        users_col = db['users']

        self.stdout.write(self.style.SUCCESS(f'Starting Real-time TaskStudio daemon (batch={batch})'))
        print(f"Monitoring database: {db.name}")
        print(f"Collection: {tasks_col.name}")
        print("=" * 60)

        # Track scheduled tasks that need processing
        self.scheduled_tasks = {}
        self.processing_lock = threading.Lock()

        # Perform initial scan if requested
        if initial_scan:
            self.process_existing_due_tasks(tasks_col, users_col, batch)

        # Start change stream monitoring in a separate thread
        change_stream_thread = threading.Thread(
            target=self.monitor_change_streams,
            args=(tasks_col, users_col),
            daemon=True
        )
        change_stream_thread.start()

        # Start scheduled task processor in a separate thread
        scheduler_thread = threading.Thread(
            target=self.scheduled_task_processor,
            args=(tasks_col, users_col),
            daemon=True
        )
        scheduler_thread.start()

        try:
            # Keep main thread alive
            while True:
                time.sleep(60)  # Check every minute for housekeeping
                self.cleanup_completed_schedules()
        except KeyboardInterrupt:
            print("\n🛑 Shutting down real-time daemon...")
            return

    def process_existing_due_tasks(self, tasks_col, users_col, batch):
        """Process any existing due tasks on startup"""
        print("🔍 Scanning for existing due tasks...")
        now = datetime.now(timezone.utc)
        
        due_tasks = list(tasks_col.find({
            'status': 'scheduled',
            'scheduled_date': {'$lte': now}
        }).limit(batch))
        
        if due_tasks:
            print(f"📋 Found {len(due_tasks)} existing due tasks")
            for task in due_tasks:
                self.process_task(task, tasks_col, users_col)
        else:
            print("✅ No existing due tasks found")

    def monitor_change_streams(self, tasks_col, users_col):
        """Monitor MongoDB change streams for new/updated scheduled tasks"""
        print("👁️  Starting change stream monitoring...")
        
        try:
            # Watch for insertions and updates to scheduled tasks
            pipeline = [
                {
                    '$match': {
                        '$or': [
                            {
                                'operationType': 'insert',
                                'fullDocument.status': 'scheduled'
                            },
                            {
                                'operationType': 'update',
                                'updateDescription.updatedFields.status': 'scheduled'
                            },
                            {
                                'operationType': 'replace',
                                'fullDocument.status': 'scheduled'
                            }
                        ]
                    }
                }
            ]
            
            with tasks_col.watch(pipeline) as stream:
                for change in stream:
                    try:
                        task_doc = change.get('fullDocument')
                        if not task_doc:
                            continue
                            
                        task_id = str(task_doc.get('_id'))
                        scheduled_date = task_doc.get('scheduled_date')
                        
                        if not scheduled_date:
                            continue
                            
                        print(f"📨 New/updated scheduled task detected: {task_id}")
                        
                        # Check if task is already due
                        now = datetime.now(timezone.utc)
                        if scheduled_date <= now:
                            print(f"⚡ Task {task_id} is already due, processing immediately...")
                            self.process_task(task_doc, tasks_col, users_col)
                        else:
                            # Schedule for future processing
                            with self.processing_lock:
                                self.scheduled_tasks[task_id] = {
                                    'scheduled_date': scheduled_date,
                                    'task_doc': task_doc
                                }
                            print(f"⏰ Task {task_id} scheduled for {scheduled_date}")
                            
                    except Exception as e:
                        print(f"❌ Error processing change stream event: {e}")
                        
        except Exception as e:
            print(f"💥 Change stream error: {e}")
            print("🔄 Change stream will restart...")
            time.sleep(5)
            # Restart change stream monitoring
            self.monitor_change_streams(tasks_col, users_col)

    def scheduled_task_processor(self, tasks_col, users_col):
        """Process scheduled tasks when they become due"""
        print("⏰ Starting scheduled task processor...")
        
        while True:
            try:
                now = datetime.now(timezone.utc)
                due_task_ids = []
                
                with self.processing_lock:
                    for task_id, task_info in self.scheduled_tasks.items():
                        if task_info['scheduled_date'] <= now:
                            due_task_ids.append(task_id)
                
                for task_id in due_task_ids:
                    with self.processing_lock:
                        task_info = self.scheduled_tasks.pop(task_id, None)
                    
                    if task_info:
                        print(f"⚡ Processing due task: {task_id}")
                        self.process_task(task_info['task_doc'], tasks_col, users_col)
                
                # Sleep for 10 seconds before checking again
                time.sleep(10)
                
            except Exception as e:
                print(f"❌ Error in scheduled task processor: {e}")
                time.sleep(10)

    def cleanup_completed_schedules(self):
        """Remove old entries from scheduled_tasks dict"""
        with self.processing_lock:
            # Remove tasks that are more than 1 hour overdue (likely processed elsewhere)
            now = datetime.now(timezone.utc)
            expired_ids = [
                task_id for task_id, task_info in self.scheduled_tasks.items()
                if (now - task_info['scheduled_date']).total_seconds() > 3600
            ]
            
            for task_id in expired_ids:
                self.scheduled_tasks.pop(task_id, None)
            
            if expired_ids:
                print(f"🧹 Cleaned up {len(expired_ids)} expired scheduled task entries")

    def process_task(self, task_doc, tasks_col, users_col):
        """Process a single task"""
        task_id = str(task_doc.get('_id'))
        username = task_doc.get('username', '')
        description = task_doc.get('description', '') or ''
        
        try:
            # Mark as running
            tasks_col.update_one(
                {'_id': ObjectId(task_doc['_id'])}, 
                {'$set': {'status': 'running', 'updated_at': datetime.now(timezone.utc)}}
            )
            print(f"▶ Processing task {task_id} for user '{username}'")
            print(f"  Task description: {description[:100]}{'...' if len(description) > 100 else ''}")
            
            # Get user's bearer token
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
                {'_id': ObjectId(task_doc['_id'])},
                {'$set': {'status': 'completed', 'result': result_text, 'updated_at': datetime.now(timezone.utc)}}
            )
            print(f"✅ Task {task_id} completed for user '{username}'")
            
            # Save conversation
            try:
                Conversation.save_conversation(
                    username=username,
                    title=f"Task: {task_doc.get('title','Scheduled Task')}",
                    messages=[
                        {'role': 'user', 'content': [{'type': 'text', 'text': description}]},
                        {'role': 'assistant', 'content': [{'type': 'text', 'text': result_text}]},
                    ],
                    metadata={'taskId': task_id}
                )
                print(f"💾 Saved conversation for task {task_id}")
            except Exception as ce:
                print(f"⚠️  Failed to save conversation for task {task_id}: {str(ce)}")
                
        except Exception as te:
            error_msg = str(te)
            print(f"❌ Task {task_id} failed for user '{username}': {error_msg}")
            
            tasks_col.update_one(
                {'_id': ObjectId(task_doc['_id'])},
                {'$set': {'status': 'failed', 'error': error_msg, 'updated_at': datetime.now(timezone.utc)}}
            )
