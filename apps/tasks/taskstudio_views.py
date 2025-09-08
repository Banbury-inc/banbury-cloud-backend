from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from datetime import datetime, timezone
from bson.objectid import ObjectId
from bson.errors import InvalidId
from pymongo.mongo_client import MongoClient
import traceback

# Reuse the same MongoDB configuration pattern as existing task views
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
taskstudio_collection = db["taskstudio_tasks"]
users_collection = db["users"]


def _store_user_bearer_token(request, username: str):
    """Extract and store the user's bearer token for daemon access."""
    try:
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            bearer_token = auth_header[7:]  # Remove 'Bearer ' prefix
            
            # Store the bearer token in the user document
            from datetime import datetime
            users_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "bearer_token": bearer_token,
                        "token_updated_at": datetime.utcnow()
                    }
                }
            )
            print(f"Updated bearer token for user '{username}'")
            return True
    except Exception as e:
        print(f"Warning: Failed to store bearer token for user {username}: {e}")
    
    return False


def _run_ai_on_description(username: str, description: str) -> str:
    """Stub AI processor: here we would call your AI pipeline.
    For now, echo a processed string. Replace with real integration.
    """
    try:
        description = description or ''
        return f"AI processed for {username}: {description[:500]}"
    except Exception as e:
        return f"AI error: {str(e)}"


def process_due_tasks_internal(limit: int = 25):
    """Core processor for due tasks. Returns list of processed task infos.
    This is used by both the HTTP endpoint and the management command.
    """
    now = datetime.now(timezone.utc)
    due_query = { 'status': 'scheduled', 'scheduled_date': { '$lte': now } }
    docs = list(taskstudio_collection.find(due_query).limit(limit))
    processed = []
    for doc in docs:
        task_id = str(doc.get('_id'))
        username = doc.get('username', '')
        description = doc.get('description', '')
        try:
            taskstudio_collection.update_one({ '_id': doc['_id'] }, { '$set': { 'status': 'running', 'updated_at': now } })
            ai_output = _run_ai_on_description(username, description)
            taskstudio_collection.update_one(
                { '_id': doc['_id'] },
                { '$set': { 'status': 'completed', 'result': ai_output, 'updated_at': datetime.now(timezone.utc) } }
            )
            processed.append({ 'id': task_id, 'status': 'completed' })
        except Exception as te:
            taskstudio_collection.update_one(
                { '_id': doc['_id'] },
                { '$set': { 'status': 'failed', 'error': str(te), 'trace': traceback.format_exc(), 'updated_at': datetime.now(timezone.utc) } }
            )
            processed.append({ 'id': task_id, 'status': 'failed' })
    return processed

@csrf_exempt
@require_http_methods(["GET"])
def get_tasks(request):
    """Get all tasks for the authenticated user (MongoDB)."""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        status_filter = request.GET.get('status')

        query: dict = { 'username': username }
        if status_filter in ['scheduled', 'running', 'completed', 'cancelled', 'failed']:
            query['status'] = status_filter

        mongo_tasks = list(taskstudio_collection.find(query).sort('created_at', -1))

        tasks_data = []
        now = datetime.now(timezone.utc)
        for doc in mongo_tasks:
            scheduled_dt = doc.get('scheduled_date')
            if scheduled_dt and getattr(scheduled_dt, 'tzinfo', None) is None:
                scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
            is_overdue = bool(
                scheduled_dt and doc.get('status') == 'scheduled' and scheduled_dt <= now
            )
            tasks_data.append({
                'id': str(doc.get('_id')),
                'title': doc.get('title', ''),
                'description': doc.get('description', '') or '',
                'status': doc.get('status', 'scheduled'),
                'priority': doc.get('priority', 'medium'),
                'scheduledDate': scheduled_dt.isoformat() if scheduled_dt else None,
                'estimatedDuration': doc.get('estimated_duration', 0),
                'assignedTo': doc.get('assigned_to', '') or '',
                'tags': doc.get('tags', []),
                'result': doc.get('result', ''),
                'error': doc.get('error', ''),
                'createdAt': ((doc.get('created_at') or now).astimezone(timezone.utc)).isoformat(),
                'updatedAt': ((doc.get('updated_at') or now).astimezone(timezone.utc)).isoformat(),
                'isOverdue': is_overdue,
                'durationDisplay': _format_duration(doc.get('estimated_duration')),
            })

        return JsonResponse({'success': True, 'tasks': tasks_data, 'count': len(tasks_data)})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["GET"])
def get_task(request, task_id):
    """Get a specific task by ID (MongoDB)."""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        try:
            object_id = ObjectId(task_id)
        except (InvalidId, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid task ID'}, status=400)

        doc = taskstudio_collection.find_one({'_id': object_id, 'username': username})
        if not doc:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)

        now = datetime.now(timezone.utc)
        scheduled_dt = doc.get('scheduled_date')
        if scheduled_dt and getattr(scheduled_dt, 'tzinfo', None) is None:
            scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        is_overdue = bool(scheduled_dt and doc.get('status') == 'scheduled' and scheduled_dt <= now)

        task_data = {
            'id': str(doc.get('_id')),
            'title': doc.get('title', ''),
            'description': doc.get('description', '') or '',
            'status': doc.get('status', 'scheduled'),
            'priority': doc.get('priority', 'medium'),
            'scheduledDate': scheduled_dt.isoformat() if scheduled_dt else None,
            'estimatedDuration': doc.get('estimated_duration', 0),
            'assignedTo': doc.get('assigned_to', '') or '',
            'tags': doc.get('tags', []),
            'result': doc.get('result', ''),
            'error': doc.get('error', ''),
            'createdAt': ((doc.get('created_at') or now).astimezone(timezone.utc)).isoformat(),
            'updatedAt': ((doc.get('updated_at') or now).astimezone(timezone.utc)).isoformat(),
            'isOverdue': is_overdue,
            'durationDisplay': _format_duration(doc.get('estimated_duration')),
        }

        return JsonResponse({'success': True, 'task': task_data})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_task(request):
    """Create a new task (MongoDB)."""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        # Store/update the user's bearer token for daemon access
        _store_user_bearer_token(request, username)

        data = json.loads(request.body)

        required_fields = ['title', 'priority', 'scheduledDate', 'estimatedDuration']
        for field in required_fields:
            if field not in data:
                return JsonResponse({'success': False, 'error': f'Missing required field: {field}'}, status=400)

        try:
            scheduled_date = datetime.fromisoformat(data['scheduledDate'].replace('Z', '+00:00'))
            if getattr(scheduled_date, 'tzinfo', None) is None:
                scheduled_date = scheduled_date.replace(tzinfo=timezone.utc)
            else:
                scheduled_date = scheduled_date.astimezone(timezone.utc)
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid scheduledDate format. Use ISO 8601 format.'}, status=400)

        if data['priority'] not in ['low', 'medium', 'high', 'urgent']:
            return JsonResponse({'success': False, 'error': 'Invalid priority. Must be one of: low, medium, high, urgent'}, status=400)

        try:
            duration = int(data['estimatedDuration'])
            if duration <= 0:
                raise ValueError('Duration must be positive')
        except (ValueError, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid estimatedDuration. Must be a positive integer.'}, status=400)

        now = datetime.now(timezone.utc)
        new_task = {
            'username': username,
            'title': data['title'].strip(),
            'description': (data.get('description') or '').strip(),
            'status': 'scheduled',
            'priority': data['priority'],
            'scheduled_date': scheduled_date,
            'estimated_duration': duration,
            'assigned_to': (data.get('assignedTo') or '').strip() or None,
            'tags': data.get('tags', []) if isinstance(data.get('tags'), list) else [],
            'created_at': now,
            'updated_at': now,
        }

        result = taskstudio_collection.insert_one(new_task)
        new_task['_id'] = result.inserted_id

        scheduled_dt = new_task.get('scheduled_date')
        if scheduled_dt and getattr(scheduled_dt, 'tzinfo', None) is None:
            scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        is_overdue = bool(scheduled_dt and new_task.get('status') == 'scheduled' and scheduled_dt <= now)

        task_data = {
            'id': str(new_task['_id']),
            'title': new_task['title'],
            'description': new_task.get('description', '') or '',
            'status': new_task['status'],
            'priority': new_task['priority'],
            'scheduledDate': scheduled_dt.isoformat() if scheduled_dt else None,
            'estimatedDuration': new_task['estimated_duration'],
            'assignedTo': new_task.get('assigned_to', '') or '',
            'tags': new_task.get('tags', []),
            'createdAt': new_task['created_at'].isoformat(),
            'updatedAt': new_task['updated_at'].isoformat(),
            'isOverdue': is_overdue,
            'durationDisplay': _format_duration(new_task.get('estimated_duration')),
        }

        return JsonResponse({'success': True, 'task': task_data, 'message': 'Task created successfully'}, status=201)

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["PUT", "PATCH"])
def update_task(request, task_id):
    """Update an existing task (MongoDB)."""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        # Store/update the user's bearer token for daemon access
        _store_user_bearer_token(request, username)

        data = json.loads(request.body)

        try:
            object_id = ObjectId(task_id)
        except (InvalidId, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid task ID'}, status=400)

        update_fields: dict = {}

        if 'title' in data:
            update_fields['title'] = (data['title'] or '').strip()

        if 'description' in data:
            update_fields['description'] = (data['description'] or '').strip()

        if 'status' in data:
            if data['status'] not in ['scheduled', 'running', 'completed', 'cancelled', 'failed']:
                return JsonResponse({'success': False, 'error': 'Invalid status. Must be one of: scheduled, running, completed, cancelled'}, status=400)
            update_fields['status'] = data['status']

        if 'priority' in data:
            if data['priority'] not in ['low', 'medium', 'high', 'urgent']:
                return JsonResponse({'success': False, 'error': 'Invalid priority. Must be one of: low, medium, high, urgent'}, status=400)
            update_fields['priority'] = data['priority']

        if 'scheduledDate' in data:
            try:
                sd = datetime.fromisoformat(data['scheduledDate'].replace('Z', '+00:00'))
                if getattr(sd, 'tzinfo', None) is None:
                    sd = sd.replace(tzinfo=timezone.utc)
                else:
                    sd = sd.astimezone(timezone.utc)
                update_fields['scheduled_date'] = sd
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Invalid scheduledDate format. Use ISO 8601 format.'}, status=400)

        if 'estimatedDuration' in data:
            try:
                duration = int(data['estimatedDuration'])
                if duration <= 0:
                    raise ValueError('Duration must be positive')
                update_fields['estimated_duration'] = duration
            except (ValueError, TypeError):
                return JsonResponse({'success': False, 'error': 'Invalid estimatedDuration. Must be a positive integer.'}, status=400)

        if 'assignedTo' in data:
            assigned_to = (data.get('assignedTo') or '').strip()
            update_fields['assigned_to'] = assigned_to or None

        if 'tags' in data:
            if isinstance(data['tags'], list):
                update_fields['tags'] = data['tags']
            else:
                return JsonResponse({'success': False, 'error': 'Tags must be a list'}, status=400)

        if 'result' in data:
            update_fields['result'] = str(data.get('result', ''))

        if 'error' in data:
            update_fields['error'] = str(data.get('error', ''))

        if not update_fields:
            return JsonResponse({'success': False, 'error': 'No valid fields to update'}, status=400)

        update_fields['updated_at'] = datetime.now(timezone.utc)

        result = taskstudio_collection.update_one(
            { '_id': object_id, 'username': username },
            { '$set': update_fields }
        )

        if result.matched_count == 0:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)

        doc = taskstudio_collection.find_one({ '_id': object_id, 'username': username })
        now = datetime.now(timezone.utc)
        scheduled_dt = doc.get('scheduled_date')
        if scheduled_dt and getattr(scheduled_dt, 'tzinfo', None) is None:
            scheduled_dt = scheduled_dt.replace(tzinfo=timezone.utc)
        is_overdue = bool(scheduled_dt and doc.get('status') == 'scheduled' and scheduled_dt <= now)

        task_data = {
            'id': str(doc.get('_id')),
            'title': doc.get('title', ''),
            'description': doc.get('description', '') or '',
            'status': doc.get('status', 'scheduled'),
            'priority': doc.get('priority', 'medium'),
            'scheduledDate': scheduled_dt.isoformat() if scheduled_dt else None,
            'estimatedDuration': doc.get('estimated_duration', 0),
            'assignedTo': doc.get('assigned_to', '') or '',
            'tags': doc.get('tags', []),
            'createdAt': ((doc.get('created_at') or now).astimezone(timezone.utc)).isoformat(),
            'updatedAt': ((doc.get('updated_at') or now).astimezone(timezone.utc)).isoformat(),
            'isOverdue': is_overdue,
            'durationDisplay': _format_duration(doc.get('estimated_duration')),
        }

        return JsonResponse({'success': True, 'task': task_data, 'message': 'Task updated successfully'})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_task(request, task_id):
    """Delete a task (MongoDB)."""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        try:
            object_id = ObjectId(task_id)
        except (InvalidId, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid task ID'}, status=400)

        result = taskstudio_collection.delete_one({ '_id': object_id, 'username': username })
        if result.deleted_count == 0:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)

        return JsonResponse({'success': True, 'message': 'Task deleted successfully'})

    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def update_task_status(request, task_id):
    """Update only the status of a task (MongoDB convenience endpoint)."""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({'success': False, 'error': 'Unauthorized'}, status=401)

        # Store/update the user's bearer token for daemon access
        _store_user_bearer_token(request, username)

        data = json.loads(request.body)
        new_status = data.get('status')

        if not new_status:
            return JsonResponse({'success': False, 'error': 'Status is required'}, status=400)

        if new_status not in ['scheduled', 'running', 'completed', 'cancelled', 'failed']:
            return JsonResponse({'success': False, 'error': 'Invalid status. Must be one of: scheduled, running, completed, cancelled'}, status=400)

        try:
            object_id = ObjectId(task_id)
        except (InvalidId, TypeError):
            return JsonResponse({'success': False, 'error': 'Invalid task ID'}, status=400)

        updated_at = datetime.now(timezone.utc)
        result = taskstudio_collection.update_one(
            { '_id': object_id, 'username': username },
            { '$set': { 'status': new_status, 'updated_at': updated_at } }
        )

        if result.matched_count == 0:
            return JsonResponse({'success': False, 'error': 'Task not found'}, status=404)

        return JsonResponse({'success': True, 'message': f'Task status updated to {new_status}', 'task': { 'id': task_id, 'status': new_status, 'updatedAt': updated_at.isoformat() }})

    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


def _format_duration(minutes_value):
    try:
        minutes = int(minutes_value or 0)
    except (TypeError, ValueError):
        return '0m'
    hours = minutes // 60
    mins = minutes % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


@csrf_exempt
@require_http_methods(["POST"])  # Admin/cron endpoint to process due tasks
def process_due_tasks(request):
    """Find tasks with status 'scheduled' and scheduled_date <= now, run AI, update status.
    Stores the AI output into task.result field.
    """
    try:
        processed = process_due_tasks_internal(limit=25)
        return JsonResponse({ 'success': True, 'processed': processed, 'count': len(processed) })
    except Exception as e:
        return JsonResponse({ 'success': False, 'error': str(e) }, status=500)
