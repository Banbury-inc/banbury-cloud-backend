from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
import pymongo
from datetime import datetime, timedelta


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
analytics_collection = db["analytics"]
file_collection = db["files"]


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



