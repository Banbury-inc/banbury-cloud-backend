from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
import pymongo
from datetime import datetime, timedelta
import json
import statistics


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
analytics_collection = db["analytics"]
file_collection = db["files"]
api_usage_collection = db["api_usage_logs"]
user_engagement_collection = db["user_engagement_sessions"]
feature_usage_collection = db["feature_usage_events"]
error_logs_collection = db["error_logs"]
user_activity_collection = db["user_activity_daily"]


@csrf_exempt
@require_http_methods(["POST", "GET"])
def add_file_request(request):
    """Increments the file_requests count in the analytics collection."""
    # Find the analytics document for this user, or create if it doesn't exist
    analytics = analytics_collection.find_one_and_update(
        {"_id": "analytics"},  # Filter to find the document
        {"$inc": {"file_requests": 1}},  # Update operation to increment file_requests
        upsert=True,  # Create document if it doesn't exist
        return_document=pymongo.ReturnDocument.AFTER  # Return updated document
    )

    return JsonResponse({
        "result": "success", 
        "message": "File request added successfully",
        "file_requests": analytics["file_requests"]
    }, status=200)


@csrf_exempt
@require_http_methods(["POST", "GET"])
def add_file_request_success(request):
    """Increments the file_requests_success count in the analytics collection."""
    # Find the analytics document for this user, or create if it doesn't exist
    analytics = analytics_collection.find_one_and_update(
        {"_id": "analytics"},  # Filter to find the document
        {"$inc": {"file_requests_success": 1}},  # Update operation to increment file_requests_success
        upsert=True,  # Create document if it doesn't exist
        return_document=pymongo.ReturnDocument.AFTER  # Return updated document
    )

    return JsonResponse({
        "result": "success", 
        "message": "File request added successfully",
        "file_requests_success": analytics["file_requests_success"]
    }, status=200)



@csrf_exempt
@require_http_methods(["GET"])
def get_analytics(request):
    """Retrieves analytics data for a specific user."""

    response_data = {"result": "success", "analytics": "analytics"}

    return JsonResponse(response_data, status=200)


@csrf_exempt
@require_http_methods(["GET"])
def get_file_type_analytics(request):
    """
    Retrieves file type analytics including:
    - Total files by type
    - Total storage by type
    - Recent uploads by type
    - Daily upload trends by type
    - User filtering support
    """
    try:
        # Get query parameters
        days = int(request.GET.get('days', 30))
        limit = int(request.GET.get('limit', 1000))
        excluded_users = request.GET.get('excluded_users', '')
        
        # Calculate date range
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Parse excluded users
        excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()] if excluded_users else []
        
        # Build query filter
        query_filter = {}
        if excluded_user_list:
            # Get user collection to find user IDs by username/email
            from bson.objectid import ObjectId
            user_collection = db['users']
            
            # Find user IDs for excluded usernames/emails
            excluded_user_ids = []
            for user_identifier in excluded_user_list:
                # Try to find by username or email
                user = user_collection.find_one({
                    '$or': [
                        {'username': user_identifier},
                        {'email': user_identifier}
                    ]
                })
                if user:
                    excluded_user_ids.append(user['_id'])
            
            if excluded_user_ids:
                query_filter['user_id'] = {'$nin': excluded_user_ids}
        
        # Get all files with filter
        all_files = list(file_collection.find(query_filter, {
            'file_type': 1, 
            'file_size': 1, 
            'date_uploaded': 1,
            'user_id': 1
        }).limit(limit))
        
        # Get recent files (within date range)
        recent_files = [f for f in all_files if f.get('date_uploaded') and 
                       (isinstance(f['date_uploaded'], datetime) and f['date_uploaded'] >= cutoff_date or
                        isinstance(f['date_uploaded'], str) and datetime.fromisoformat(f['date_uploaded'].replace('Z', '+00:00')) >= cutoff_date)]
        
        # Normalize file types (remove leading dot, lowercase)
        def normalize_file_type(file_type):
            if not file_type:
                return 'unknown'
            ft = str(file_type).lower().strip()
            if ft.startswith('.'):
                ft = ft[1:]
            return ft if ft else 'unknown'
        
        # Categorize file types
        def categorize_file_type(file_type):
            ft = normalize_file_type(file_type)
            
            # Images
            if ft in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp', 'ico', 'tiff']:
                return 'Images'
            # Videos
            elif ft in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'mkv', 'webm', 'm4v']:
                return 'Videos'
            # Audio
            elif ft in ['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma']:
                return 'Audio'
            # Documents
            elif ft in ['pdf', 'doc', 'docx', 'txt', 'rtf', 'odt']:
                return 'Documents'
            # Spreadsheets
            elif ft in ['xls', 'xlsx', 'csv', 'ods']:
                return 'Spreadsheets'
            # Presentations
            elif ft in ['ppt', 'pptx', 'odp']:
                return 'Presentations'
            # Archives
            elif ft in ['zip', 'rar', '7z', 'tar', 'gz', 'bz2']:
                return 'Archives'
            # Code
            elif ft in ['py', 'js', 'ts', 'jsx', 'tsx', 'html', 'css', 'json', 'xml', 'java', 'c', 'cpp', 'h', 'go', 'rs', 'php', 'rb', 'swift']:
                return 'Code'
            else:
                return 'Other'
        
        # Calculate statistics for all files
        file_type_stats = {}
        category_stats = {}
        
        for file in all_files:
            file_type = normalize_file_type(file.get('file_type'))
            category = categorize_file_type(file.get('file_type'))
            file_size = file.get('file_size', 0) or 0
            
            # File type stats
            if file_type not in file_type_stats:
                file_type_stats[file_type] = {'count': 0, 'size': 0, 'category': category}
            file_type_stats[file_type]['count'] += 1
            file_type_stats[file_type]['size'] += file_size
            
            # Category stats
            if category not in category_stats:
                category_stats[category] = {'count': 0, 'size': 0}
            category_stats[category]['count'] += 1
            category_stats[category]['size'] += file_size
        
        # Calculate statistics for recent files
        recent_file_type_stats = {}
        recent_category_stats = {}
        
        for file in recent_files:
            file_type = normalize_file_type(file.get('file_type'))
            category = categorize_file_type(file.get('file_type'))
            file_size = file.get('file_size', 0) or 0
            
            # Recent file type stats
            if file_type not in recent_file_type_stats:
                recent_file_type_stats[file_type] = {'count': 0, 'size': 0, 'category': category}
            recent_file_type_stats[file_type]['count'] += 1
            recent_file_type_stats[file_type]['size'] += file_size
            
            # Recent category stats
            if category not in recent_category_stats:
                recent_category_stats[category] = {'count': 0, 'size': 0}
            recent_category_stats[category]['count'] += 1
            recent_category_stats[category]['size'] += file_size
        
        # Calculate daily stats for recent files
        daily_stats = {}
        for file in recent_files:
            date_uploaded = file.get('date_uploaded')
            if date_uploaded:
                if isinstance(date_uploaded, datetime):
                    date_str = date_uploaded.strftime('%Y-%m-%d')
                else:
                    try:
                        dt = datetime.fromisoformat(str(date_uploaded).replace('Z', '+00:00'))
                        date_str = dt.strftime('%Y-%m-%d')
                    except:
                        continue
                
                file_type = normalize_file_type(file.get('file_type'))
                category = categorize_file_type(file.get('file_type'))
                
                if date_str not in daily_stats:
                    daily_stats[date_str] = {'total': 0, 'by_category': {}}
                
                daily_stats[date_str]['total'] += 1
                if category not in daily_stats[date_str]['by_category']:
                    daily_stats[date_str]['by_category'][category] = 0
                daily_stats[date_str]['by_category'][category] += 1
        
        # Convert to sorted arrays
        file_type_array = [
            {
                'file_type': ft,
                'category': data['category'],
                'count': data['count'],
                'size': data['size']
            }
            for ft, data in sorted(file_type_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        recent_file_type_array = [
            {
                'file_type': ft,
                'category': data['category'],
                'count': data['count'],
                'size': data['size']
            }
            for ft, data in sorted(recent_file_type_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        category_array = [
            {
                'category': cat,
                'count': data['count'],
                'size': data['size']
            }
            for cat, data in sorted(category_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        recent_category_array = [
            {
                'category': cat,
                'count': data['count'],
                'size': data['size']
            }
            for cat, data in sorted(recent_category_stats.items(), key=lambda x: x[1]['count'], reverse=True)
        ]
        
        daily_stats_array = [
            {
                'date': date,
                'count': data['total'],
                'by_category': data['by_category']
            }
            for date, data in sorted(daily_stats.items())
        ]
        
        # Calculate summary statistics
        summary = {
            'total_files': len(all_files),
            'total_storage': sum(f.get('file_size', 0) or 0 for f in all_files),
            'recent_files': len(recent_files),
            'recent_storage': sum(f.get('file_size', 0) or 0 for f in recent_files),
            'unique_file_types': len(file_type_stats),
            'unique_categories': len(category_stats),
            'period_days': days,
            'most_common_type': file_type_array[0]['file_type'] if file_type_array else None,
            'most_common_category': category_array[0]['category'] if category_array else None
        }
        
        return JsonResponse({
            'result': 'success',
            'summary': summary,
            'file_type_stats': file_type_array,
            'category_stats': category_array,
            'recent_file_type_stats': recent_file_type_array,
            'recent_category_stats': recent_category_array,
            'daily_stats': daily_stats_array
        }, status=200)
        
    except Exception as e:
        print(f"Error getting file type analytics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def track_file_upload(request):
    """
    Tracks file upload events for analytics.
    This can be called whenever a file is uploaded to increment counters.
    """
    try:
        # Get file type from request
        import json
        data = json.loads(request.body) if request.body else {}
        
        file_type = data.get('file_type', 'unknown')
        file_size = data.get('file_size', 0)
        username = data.get('username')
        
        # Normalize file type
        if file_type and file_type.startswith('.'):
            file_type = file_type[1:].lower()
        else:
            file_type = str(file_type).lower()
        
        # Update analytics collection with file type tracking
        analytics_collection.find_one_and_update(
            {"_id": "file_type_analytics"},
            {
                "$inc": {
                    f"file_types.{file_type}.count": 1,
                    f"file_types.{file_type}.total_size": file_size,
                    "total_files": 1,
                    "total_size": file_size
                },
                "$set": {
                    f"file_types.{file_type}.last_upload": datetime.utcnow(),
                    "last_updated": datetime.utcnow()
                }
            },
            upsert=True,
            return_document=pymongo.ReturnDocument.AFTER
        )
        
        return JsonResponse({
            'result': 'success',
            'message': 'File upload tracked successfully'
        }, status=200)
        
    except Exception as e:
        print(f"Error tracking file upload: {e}")
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_api_usage_analytics(request):
    """Get API usage analytics aggregated by endpoint, user, and time period."""
    try:
        days = int(request.GET.get('days', 30))
        excluded_users = request.GET.get('excluded_users', '').strip()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query filter
        query_filter = {"timestamp": {"$gte": cutoff_date}}
        
        # Add user exclusions if provided
        if excluded_users:
            excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()]
            if excluded_user_list:
                query_filter["username"] = {"$nin": excluded_user_list}
        
        # Get all logs in date range
        logs = list(api_usage_collection.find(query_filter))
        
        if not logs:
            return JsonResponse({
                'result': 'success',
                'summary': {
                    'total_requests': 0,
                    'unique_endpoints': 0,
                    'avg_response_time': 0,
                    'error_rate': 0,
                    'period_days': days
                },
                'endpoint_stats': [],
                'daily_stats': [],
                'hourly_stats': [],
                'user_stats': []
            }, status=200)
        
        # Calculate percentiles
        def percentile(data, percentile):
            sorted_data = sorted(data)
            index = int(len(sorted_data) * percentile / 100)
            return sorted_data[index] if sorted_data else 0
        
        # Group by endpoint
        endpoint_stats_map = {}
        response_times_by_endpoint = {}
        error_count_by_endpoint = {}
        
        for log in logs:
            endpoint = log.get('endpoint', 'unknown')
            response_time = log.get('response_time_ms', 0)
            status_code = log.get('status_code', 200)
            
            if endpoint not in endpoint_stats_map:
                endpoint_stats_map[endpoint] = {'count': 0, 'errors': 0, 'response_times': []}
            
            endpoint_stats_map[endpoint]['count'] += 1
            endpoint_stats_map[endpoint]['response_times'].append(response_time)
            
            if status_code >= 400:
                endpoint_stats_map[endpoint]['errors'] += 1
        
        # Build endpoint stats
        endpoint_stats = []
        for endpoint, data in endpoint_stats_map.items():
            response_times = data['response_times']
            endpoint_stats.append({
                'endpoint': endpoint,
                'count': data['count'],
                'avg_response_time': sum(response_times) / len(response_times) if response_times else 0,
                'error_count': data['errors'],
                'p95_response_time': percentile(response_times, 95) if response_times else 0
            })
        endpoint_stats.sort(key=lambda x: x['count'], reverse=True)
        
        # Daily stats
        daily_map = {}
        for log in logs:
            date_str = log.get('timestamp').strftime('%Y-%m-%d') if isinstance(log.get('timestamp'), datetime) else datetime.fromisoformat(str(log.get('timestamp'))).strftime('%Y-%m-%d')
            if date_str not in daily_map:
                daily_map[date_str] = {'count': 0, 'response_times': []}
            daily_map[date_str]['count'] += 1
            daily_map[date_str]['response_times'].append(log.get('response_time_ms', 0))
        
        daily_stats = [{
            'date': date,
            'count': data['count'],
            'avg_response_time': sum(data['response_times']) / len(data['response_times']) if data['response_times'] else 0
        } for date, data in sorted(daily_map.items())]
        
        # Hourly stats
        hourly_map = {}
        for log in logs:
            hour = log.get('timestamp').hour if isinstance(log.get('timestamp'), datetime) else datetime.fromisoformat(str(log.get('timestamp'))).hour
            hourly_map[hour] = hourly_map.get(hour, 0) + 1
        
        hourly_stats = [{'hour': hour, 'count': count} for hour, count in sorted(hourly_map.items())]
        
        # User stats
        user_map = {}
        for log in logs:
            username = log.get('username') or 'anonymous'
            user_map[username] = user_map.get(username, 0) + 1
        
        user_stats = [{'username': username, 'count': count} for username, count in sorted(user_map.items(), key=lambda x: x[1], reverse=True)[:20]]
        
        # Calculate summary
        total_requests = len(logs)
        unique_endpoints = len(endpoint_stats_map)
        all_response_times = [log.get('response_time_ms', 0) for log in logs]
        avg_response_time = sum(all_response_times) / len(all_response_times) if all_response_times else 0
        error_count = sum(1 for log in logs if log.get('status_code', 200) >= 400)
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        return JsonResponse({
            'result': 'success',
            'summary': {
                'total_requests': total_requests,
                'unique_endpoints': unique_endpoints,
                'avg_response_time': round(avg_response_time, 2),
                'error_rate': round(error_rate, 2),
                'period_days': days
            },
            'endpoint_stats': endpoint_stats[:50],  # Top 50
            'daily_stats': daily_stats,
            'hourly_stats': hourly_stats,
            'user_stats': user_stats
        }, status=200)
        
    except Exception as e:
        print(f"Error getting API usage analytics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def track_user_engagement(request):
    """Track user engagement session data."""
    try:
        data = json.loads(request.body) if request.body else {}
        
        session_data = {
            'user_id': data.get('user_id'),
            'username': data.get('username'),
            'session_start': datetime.fromisoformat(data['session_start'].replace('Z', '+00:00')) if isinstance(data.get('session_start'), str) else data.get('session_start'),
            'session_end': datetime.fromisoformat(data['session_end'].replace('Z', '+00:00')) if isinstance(data.get('session_end'), str) and data.get('session_end') else None,
            'active_time_seconds': data.get('active_time_seconds', 0),
            'feature_interactions': data.get('feature_interactions', []),
            'timestamp': datetime.utcnow()
        }
        
        user_engagement_collection.insert_one(session_data)
        
        return JsonResponse({
            'result': 'success',
            'message': 'User engagement tracked successfully'
        }, status=200)
        
    except Exception as e:
        print(f"Error tracking user engagement: {e}")
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_user_engagement_analytics(request):
    """Get user engagement analytics."""
    try:
        days = int(request.GET.get('days', 30))
        excluded_users = request.GET.get('excluded_users', '').strip()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query filter
        query_filter = {"timestamp": {"$gte": cutoff_date}}
        
        # Add user exclusions if provided
        if excluded_users:
            excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()]
            if excluded_user_list:
                query_filter["username"] = {"$nin": excluded_user_list}
        
        sessions = list(user_engagement_collection.find(query_filter))
        
        if not sessions:
            return JsonResponse({
                'result': 'success',
                'summary': {
                    'total_sessions': 0,
                    'avg_session_duration': 0,
                    'total_active_time': 0,
                    'avg_active_time_per_session': 0
                },
                'daily_stats': [],
                'session_duration_distribution': []
            }, status=200)
        
        # Calculate session durations
        session_durations = []
        total_active_time = 0
        
        for session in sessions:
            start = session.get('session_start')
            end = session.get('session_end') or datetime.utcnow()
            
            if isinstance(start, str):
                start = datetime.fromisoformat(start.replace('Z', '+00:00'))
            if isinstance(end, str):
                end = datetime.fromisoformat(end.replace('Z', '+00:00'))
            
            if start and end:
                duration = (end - start).total_seconds()
                session_durations.append(duration)
            
            active_time = session.get('active_time_seconds', 0)
            total_active_time += active_time
        
        # Daily stats
        daily_map = {}
        for session in sessions:
            date_str = session.get('timestamp').strftime('%Y-%m-%d') if isinstance(session.get('timestamp'), datetime) else datetime.fromisoformat(str(session.get('timestamp'))).strftime('%Y-%m-%d')
            if date_str not in daily_map:
                daily_map[date_str] = {'sessions': 0, 'active_time': 0}
            daily_map[date_str]['sessions'] += 1
            daily_map[date_str]['active_time'] += session.get('active_time_seconds', 0)
        
        daily_stats = [{
            'date': date,
            'sessions': data['sessions'],
            'active_time': data['active_time']
        } for date, data in sorted(daily_map.items())]
        
        # Session duration distribution
        duration_ranges = {
            '0-5 min': 0,
            '5-15 min': 0,
            '15-30 min': 0,
            '30-60 min': 0,
            '1+ hours': 0
        }
        
        for duration in session_durations:
            minutes = duration / 60
            if minutes < 5:
                duration_ranges['0-5 min'] += 1
            elif minutes < 15:
                duration_ranges['5-15 min'] += 1
            elif minutes < 30:
                duration_ranges['15-30 min'] += 1
            elif minutes < 60:
                duration_ranges['30-60 min'] += 1
            else:
                duration_ranges['1+ hours'] += 1
        
        session_duration_distribution = [{'range': k, 'count': v} for k, v in duration_ranges.items()]
        
        total_sessions = len(sessions)
        avg_session_duration = sum(session_durations) / len(session_durations) if session_durations else 0
        avg_active_time_per_session = total_active_time / total_sessions if total_sessions > 0 else 0
        
        return JsonResponse({
            'result': 'success',
            'summary': {
                'total_sessions': total_sessions,
                'avg_session_duration': round(avg_session_duration, 2),
                'total_active_time': round(total_active_time, 2),
                'avg_active_time_per_session': round(avg_active_time_per_session, 2)
            },
            'daily_stats': daily_stats,
            'session_duration_distribution': session_duration_distribution
        }, status=200)
        
    except Exception as e:
        print(f"Error getting user engagement analytics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_retention_analytics(request):
    """Get retention analytics (DAU/WAU/MAU and cohort retention)."""
    try:
        excluded_users = request.GET.get('excluded_users', '').strip()
        
        # Parse excluded users list
        excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()] if excluded_users else []
        
        # Get user activity from various sources
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Build base query filter
        base_filter = {}
        if excluded_user_list:
            base_filter["username"] = {"$nin": excluded_user_list}
        
        # Calculate DAU - unique users active today
        dau_users = set()
        dau_query = {"timestamp": {"$gte": today}, **base_filter}
        dau_logs = api_usage_collection.find(dau_query, {"username": 1})
        for log in dau_logs:
            username = log.get('username')
            if username:
                dau_users.add(username)
        
        # Calculate WAU - unique users active in last 7 days
        wau_users = set()
        wau_query = {"timestamp": {"$gte": week_ago}, **base_filter}
        wau_logs = api_usage_collection.find(wau_query, {"username": 1})
        for log in wau_logs:
            username = log.get('username')
            if username:
                wau_users.add(username)
        
        # Calculate MAU - unique users active in last 30 days
        mau_users = set()
        mau_query = {"timestamp": {"$gte": month_ago}, **base_filter}
        mau_logs = api_usage_collection.find(mau_query, {"username": 1})
        for log in mau_logs:
            username = log.get('username')
            if username:
                mau_users.add(username)
        
        # Daily active users over last 30 days
        daily_active_map = {}
        daily_query = {"timestamp": {"$gte": month_ago}, **base_filter}
        for log in api_usage_collection.find(daily_query, {"username": 1, "timestamp": 1}):
            date_str = log.get('timestamp').strftime('%Y-%m-%d') if isinstance(log.get('timestamp'), datetime) else datetime.fromisoformat(str(log.get('timestamp'))).strftime('%Y-%m-%d')
            username = log.get('username')
            if username:
                if date_str not in daily_active_map:
                    daily_active_map[date_str] = set()
                daily_active_map[date_str].add(username)
        
        daily_active_users = [{
            'date': date,
            'count': len(users)
        } for date, users in sorted(daily_active_map.items())]
        
        # Cohort retention (simplified - by signup month)
        user_collection = db['users']
        cohorts = []
        for user in user_collection.find({}, {"username": 1, "created_at": 1}):
            if not user.get('created_at'):
                continue
            created = user.get('created_at')
            if isinstance(created, str):
                try:
                    created = datetime.fromisoformat(created.replace('Z', '+00:00'))
                except:
                    continue
            cohort_month = created.strftime('%Y-%m')
            username = user.get('username')
            if not username:
                continue
            
            # Check activity at day 0, 7, 30
            day_0 = 0
            day_7 = 0
            day_30 = 0
            
            # Apply user exclusions to cohort retention checks
            if excluded_user_list and username in excluded_user_list:
                continue
            
            # Check if active on signup day
            signup_day_start = created.replace(hour=0, minute=0, second=0, microsecond=0)
            signup_day_end = signup_day_start + timedelta(days=1)
            if api_usage_collection.count_documents({"username": username, "timestamp": {"$gte": signup_day_start, "$lt": signup_day_end}}) > 0:
                day_0 = 1
            
            # Check if active 7 days after signup
            day_7_start = signup_day_start + timedelta(days=7)
            day_7_end = day_7_start + timedelta(days=1)
            if api_usage_collection.count_documents({"username": username, "timestamp": {"$gte": day_7_start, "$lt": day_7_end}}) > 0:
                day_7 = 1
            
            # Check if active 30 days after signup
            day_30_start = signup_day_start + timedelta(days=30)
            day_30_end = day_30_start + timedelta(days=1)
            if api_usage_collection.count_documents({"username": username, "timestamp": {"$gte": day_30_start, "$lt": day_30_end}}) > 0:
                day_30 = 1
            
            cohorts.append({
                'cohort': cohort_month,
                'username': username,
                'day_0': day_0,
                'day_7': day_7,
                'day_30': day_30
            })
        
        # Aggregate by cohort
        cohort_agg = {}
        for cohort_data in cohorts:
            cohort = cohort_data['cohort']
            if cohort not in cohort_agg:
                cohort_agg[cohort] = {'day_0': 0, 'day_7': 0, 'day_30': 0, 'total': 0}
            cohort_agg[cohort]['day_0'] += cohort_data['day_0']
            cohort_agg[cohort]['day_7'] += cohort_data['day_7']
            cohort_agg[cohort]['day_30'] += cohort_data['day_30']
            cohort_agg[cohort]['total'] += 1
        
        retention_cohorts = [{
            'cohort': cohort,
            'day_0': data['day_0'],
            'day_7': data['day_7'],
            'day_30': data['day_30'],
            'total': data['total']
        } for cohort, data in sorted(cohort_agg.items())]
        
        return JsonResponse({
            'result': 'success',
            'dau': len(dau_users),
            'wau': len(wau_users),
            'mau': len(mau_users),
            'retention_cohorts': retention_cohorts[:12],  # Last 12 months
            'daily_active_users': daily_active_users
        }, status=200)
        
    except Exception as e:
        print(f"Error getting retention analytics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def track_feature_usage(request):
    """Track feature usage events."""
    try:
        data = json.loads(request.body) if request.body else {}
        
        feature_data = {
            'user_id': data.get('user_id'),
            'username': data.get('username'),
            'feature': data.get('feature'),
            'context': data.get('context', {}),
            'timestamp': datetime.utcnow()
        }
        
        feature_usage_collection.insert_one(feature_data)
        
        return JsonResponse({
            'result': 'success',
            'message': 'Feature usage tracked successfully'
        }, status=200)
        
    except Exception as e:
        print(f"Error tracking feature usage: {e}")
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_feature_usage_analytics(request):
    """Get feature usage analytics."""
    try:
        days = int(request.GET.get('days', 30))
        excluded_users = request.GET.get('excluded_users', '').strip()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query filter
        query_filter = {"timestamp": {"$gte": cutoff_date}}
        
        # Add user exclusions if provided
        if excluded_users:
            excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()]
            if excluded_user_list:
                query_filter["username"] = {"$nin": excluded_user_list}
        
        events = list(feature_usage_collection.find(query_filter))
        
        if not events:
            return JsonResponse({
                'result': 'success',
                'summary': {
                    'total_feature_uses': 0,
                    'unique_features': 0,
                    'unique_users': 0
                },
                'feature_stats': [],
                'daily_stats': []
            }, status=200)
        
        # Group by feature
        feature_map = {}
        users_by_feature = {}
        
        for event in events:
            feature = event.get('feature', 'unknown')
            username = event.get('username')
            
            feature_map[feature] = feature_map.get(feature, 0) + 1
            
            if feature not in users_by_feature:
                users_by_feature[feature] = set()
            if username:
                users_by_feature[feature].add(username)
        
        feature_stats = [{
            'feature': feature,
            'count': count,
            'unique_users': len(users_by_feature.get(feature, set()))
        } for feature, count in sorted(feature_map.items(), key=lambda x: x[1], reverse=True)]
        
        # Daily stats by feature
        daily_map = {}
        for event in events:
            date_str = event.get('timestamp').strftime('%Y-%m-%d') if isinstance(event.get('timestamp'), datetime) else datetime.fromisoformat(str(event.get('timestamp'))).strftime('%Y-%m-%d')
            feature = event.get('feature', 'unknown')
            key = f"{date_str}_{feature}"
            daily_map[key] = daily_map.get(key, 0) + 1
        
        daily_stats = [{
            'date': key.split('_')[0],
            'feature': '_'.join(key.split('_')[1:]),
            'count': count
        } for key, count in sorted(daily_map.items())]
        
        unique_users = set()
        for event in events:
            if event.get('username'):
                unique_users.add(event.get('username'))
        
        return JsonResponse({
            'result': 'success',
            'summary': {
                'total_feature_uses': len(events),
                'unique_features': len(feature_map),
                'unique_users': len(unique_users)
            },
            'feature_stats': feature_stats,
            'daily_stats': daily_stats
        }, status=200)
        
    except Exception as e:
        print(f"Error getting feature usage analytics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def track_error(request):
    """Track error events."""
    try:
        data = json.loads(request.body) if request.body else {}
        
        error_data = {
            'user_id': data.get('user_id'),
            'username': data.get('username'),
            'error_type': data.get('error_type', 'unknown'),
            'error_message': data.get('error_message', ''),
            'endpoint': data.get('endpoint'),
            'stack_trace': data.get('stack_trace'),
            'timestamp': datetime.utcnow()
        }
        
        error_logs_collection.insert_one(error_data)
        
        return JsonResponse({
            'result': 'success',
            'message': 'Error tracked successfully'
        }, status=200)
        
    except Exception as e:
        print(f"Error tracking error: {e}")
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_error_analytics(request):
    """Get error analytics."""
    try:
        days = int(request.GET.get('days', 30))
        excluded_users = request.GET.get('excluded_users', '').strip()
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Build query filter
        query_filter = {"timestamp": {"$gte": cutoff_date}}
        api_query_filter = {"timestamp": {"$gte": cutoff_date}, "status_code": {"$gte": 400}}
        
        # Add user exclusions if provided
        if excluded_users:
            excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()]
            if excluded_user_list:
                query_filter["username"] = {"$nin": excluded_user_list}
                api_query_filter["username"] = {"$nin": excluded_user_list}
        
        errors = list(error_logs_collection.find(query_filter))
        
        # Also get API errors (status codes >= 400)
        api_error_count = api_usage_collection.count_documents(api_query_filter)
        
        # Get total requests for error rate calculation
        total_requests_filter = {"timestamp": {"$gte": cutoff_date}}
        if excluded_users:
            excluded_user_list = [u.strip() for u in excluded_users.split(',') if u.strip()]
            if excluded_user_list:
                total_requests_filter["username"] = {"$nin": excluded_user_list}
        total_requests = api_usage_collection.count_documents(total_requests_filter)
        
        if not errors and api_error_count == 0:
            return JsonResponse({
                'result': 'success',
                'summary': {
                    'total_errors': 0,
                    'error_rate': 0,
                    'unique_error_types': 0
                },
                'error_by_type': [],
                'error_by_endpoint': [],
                'daily_error_stats': []
            }, status=200)
        
        # Group by error type
        error_type_map = {}
        for error in errors:
            error_type = error.get('error_type', 'unknown')
            error_type_map[error_type] = error_type_map.get(error_type, 0) + 1
        
        # Add API errors
        if api_error_count > 0:
            error_type_map['api_error'] = error_type_map.get('api_error', 0) + api_error_count
        
        error_by_type = [{
            'error_type': error_type,
            'count': count
        } for error_type, count in sorted(error_type_map.items(), key=lambda x: x[1], reverse=True)]
        
        # Group by endpoint
        endpoint_map = {}
        for error in errors:
            endpoint = error.get('endpoint', 'unknown')
            endpoint_map[endpoint] = endpoint_map.get(endpoint, 0) + 1
        
        error_by_endpoint = [{
            'endpoint': endpoint,
            'count': count
        } for endpoint, count in sorted(endpoint_map.items(), key=lambda x: x[1], reverse=True)[:20]]
        
        # Daily error stats
        daily_map = {}
        for error in errors:
            date_str = error.get('timestamp').strftime('%Y-%m-%d') if isinstance(error.get('timestamp'), datetime) else datetime.fromisoformat(str(error.get('timestamp'))).strftime('%Y-%m-%d')
            daily_map[date_str] = daily_map.get(date_str, 0) + 1
        
        daily_error_stats = [{
            'date': date,
            'count': count
        } for date, count in sorted(daily_map.items())]
        
        total_errors = len(errors) + api_error_count
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        return JsonResponse({
            'result': 'success',
            'summary': {
                'total_errors': total_errors,
                'error_rate': round(error_rate, 2),
                'unique_error_types': len(error_type_map)
            },
            'error_by_type': error_by_type,
            'error_by_endpoint': error_by_endpoint,
            'daily_error_stats': daily_error_stats
        }, status=200)
        
    except Exception as e:
        print(f"Error getting error analytics: {e}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'result': 'error',
            'error': str(e)
        }, status=500)



