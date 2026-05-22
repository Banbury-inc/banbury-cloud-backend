from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
from .get_settings import get_settings as db_get_settings
import json
from bson.json_util import dumps



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def get_settings(request):
    """Retrieves settings for a given username."""
    try:
        username = request.username_from_token
        response = db_get_settings(username)
        json_data = json.loads(dumps(response))
        return JsonResponse(json_data, safe=True)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def update_settings(request):
    """Updates settings for a given username."""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    allowed_settings = [
        "sync_entire_device_checked",
        "predicted_upload_speed_weighting",
        "predicted_download_speed_weighting",
        "predicted_cpu_usage_weighting",
        "predicted_ram_usage_weighting",
        "predicted_gpu_usage_weighting",
        "marketing_emails_enabled",
    ]
    settings_data = {
        setting: data[setting]
        for setting in allowed_settings
        if setting in data
    }

    if not settings_data:
        return JsonResponse({"error": "No settings provided."}, status=400)

    if "marketing_emails_enabled" in settings_data and not isinstance(settings_data["marketing_emails_enabled"], bool):
        return JsonResponse({"error": "marketing_emails_enabled must be a boolean."}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    settings_collection = db["settings"]

    # Find the user by username
    user = user_collection.find_one({"username": request.username_from_token})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    user_id = user["_id"]

    # Check if settings already exist for this user
    existing_settings = settings_collection.find_one({
        "user_id": user_id
    })

    try:
        if existing_settings:
            # Update existing settings
            settings_collection.update_one(
                {"_id": existing_settings["_id"]},
                {"$set": settings_data}
            )
            message = "Settings updated successfully"
        else:
            # Create new settings
            settings_data.update({
                "user_id": user_id
            })
            settings_collection.insert_one(settings_data)
            message = "Settings created successfully"

        return JsonResponse({
            "result": "success",
            "message": message,
            "username": request.username_from_token,
        })

    except Exception as e:
        print(f"Error updating settings: {e}")
        return JsonResponse({
            "result": "error",
            "message": str(e)
        }, status=500)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def delete_account(request):
    """Deletes a user's account."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    settings_collection = db["settings"]
    device_collection = db["devices"]  
    file_collection = db["files"]  
    sessions_collection = db["sessions"]
    file_sync_collection = db["file_sync"]

    try:

        # Delete user from users collection
        user = user_collection.find_one({"username": request.username_from_token})
        if not user:
            return JsonResponse({"error": "User not found."}, status=404)
        
        # Find all devices belonging to the user
        user_devices = list(device_collection.find({"user_id": user["_id"]}))
        device_ids = [device.get("_id") for device in user_devices]
        
        # Delete all files associated with each device
        deleted_files_count = 0
        deleted_sessions_count = 0
        
        for device_id in device_ids:
            # Delete files for this device
            files_result = file_collection.delete_many({"device_id": device_id})
            deleted_files_count += files_result.deleted_count
            
            # Delete sessions for this device
            sessions_result = sessions_collection.delete_many({"device_id": device_id})
            deleted_sessions_count += sessions_result.deleted_count
        
        # Delete all file sync records for this user
        file_sync_result = file_sync_collection.delete_many({"user_id": user["_id"]})
        deleted_file_sync_count = file_sync_result.deleted_count
        
        # Delete user's settings
        settings_collection.delete_one({"username": request.username_from_token})

        # Delete user's devices
        device_collection.delete_one({"user_id": user["_id"]})
        
        # Finally delete the user
        user_collection.delete_one({"username": request.username_from_token})

        # Create response data
        response_data = {
            "result": "success",
            "message": "Account deleted successfully",
            "deleted_devices": device_ids,
            "deleted_files_count": deleted_files_count,
            "deleted_sessions_count": deleted_sessions_count,
            "deleted_file_sync_count": deleted_file_sync_count
        }
        
        # Use bson.json_util.dumps to handle MongoDB ObjectId serialization
        json_data = json.loads(dumps(response_data))
        return JsonResponse(json_data, safe=True)
        
    except Exception as e:
        print(f"Error deleting account: {e}")
        error_response = {
            "result": "error",
            "message": f"Error deleting account: {str(e)}"
        }
        json_error = json.loads(dumps(error_response))
        return JsonResponse(json_error, status=500, safe=True)

        
        
