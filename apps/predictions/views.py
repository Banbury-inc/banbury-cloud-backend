from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from .get_device_predictions import get_device_predictions as db_get_device_predictions
from .update_sync_storage_capacity import update_sync_storage_capacity as db_update_sync_storage_capacity
from .add_device_id_to_file_sync_file import add_device_id_to_file_sync_file as db_add_device_id_to_file_sync_file
from .get_download_queue import get_download_queue as db_get_download_queue
from .db_add_file_to_sync import db_add_file_to_sync as db_add_file_to_sync
from .pipeline import pipeline
from .get_file_sync import get_file_sync as db_get_file_sync
from .update_file_priority import update_file_priority as db_update_file_priority
from .db_remove_file_from_sync import db_remove_file_from_sync as db_remove_file_from_sync
import json
from pymongo import MongoClient
import datetime
from bson import ObjectId


@csrf_exempt
@require_http_methods(["GET"])
def run_pipeline(request):
    """
    Executes the prediction pipeline for the specified user.

    Args:
        request: The HttpRequest object.
        username: The username for whom to run the pipeline.

    Returns:
        JsonResponse: A JSON response indicating success and containing the pipeline results.
    """
    username = request.username_from_token
    result = pipeline(username)
    response_data = {
        "result": "success",
        "data": result,
    }   
    return JsonResponse(response_data)



@csrf_exempt
@require_http_methods(["POST"])
def add_file_to_sync(request):
    """
    Adds a file to the synchronization list for a specific device belonging to the user.

    Expects a JSON body with 'device_name' and 'file_path'.

    Args:
        request: The HttpRequest object containing the file details in its body.
        username: The username who owns the device.

    Returns:
        JsonResponse: A JSON response indicating the result of the operation.
    """
    data = json.loads(request.body)
    device_name = data.get("device_name")
    file_path = data.get("file_path")
    username = request.username_from_token
    response = db_add_file_to_sync(username, device_name, file_path)
    username = request.username_from_token

    user_data = {
        "result": response,
        "username": username,  # Return username if success, None if fail
    }

    return JsonResponse(user_data)


@csrf_exempt
@require_http_methods(["POST"])
def remove_file_from_sync(request):
    """
    Removes a file from the synchronization list for a specific device belonging to the user.

    Expects a JSON body with 'device_name' and 'file_path'.

    Args:
        request: The HttpRequest object containing the file details in its body.
        username: The username who owns the device.

    Returns:
        JsonResponse: A JSON response indicating the result of the operation.
    """
    data = json.loads(request.body)
    device_name = data.get("device_name")
    file_path = data.get("file_path")
    username = request.username_from_token
    response = db_remove_file_from_sync(username, device_name, file_path)
    username = request.username_from_token

    user_data = {
        "result": response,
        "username": username,  # Return username if success, None if fail
    }

    return JsonResponse(user_data)



@csrf_exempt
@require_http_methods(["POST"])
def get_files_to_sync(request):
    """
    Retrieves the list of files marked for synchronization for a user.

    Optionally filters by a specific global file path provided in the JSON body.
    Expects an optional JSON body with 'global_file_path'.

    Args:
        request: The HttpRequest object, potentially containing 'global_file_path'.
        username: The username whose sync files are being requested.

    Returns:
        JsonResponse: A JSON response containing the list of files or an error message.
    """
    try:
        # Parse request body
        data = json.loads(request.body)
        global_file_path = data.get('global_file_path')
        
        # Call database function with optional global_file_path
        username = request.username_from_token
        response, status_code = db_get_file_sync(username, global_file_path)
        
        if status_code != 200:
            return JsonResponse({
                "result": "error",
                "message": response.get("error", "Unknown error occurred"),
                "files": []
            }, status=status_code)
            
        return JsonResponse({
            "result": "success",
            "files": response.get("files", [])
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "result": "error",
            "message": "Invalid JSON",
            "files": []
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "error",
            "message": str(e),
            "files": []
        }, status=500)



@csrf_exempt
@require_http_methods(["POST"])
def update_file_priority(request):
    """
    Updates the synchronization priority of a specific file for the user.

    Expects a JSON body with 'file_id' and 'priority'.

    Args:
        request: The HttpRequest object containing 'file_id' and 'priority'.
        username: The username whose file priority is being updated.

    Returns:
        JsonResponse: A JSON response indicating the result and message of the operation.
    """
    try:
        data = json.loads(request.body)
        file_id = data.get("file_id")
        priority = data.get("priority")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    username = request.username_from_token

    response = db_update_file_priority(username, file_id, priority)


    files_data = {
        "result": response.get("result"),
        "message": response.get("message"),
    }

    return JsonResponse(files_data)



@csrf_exempt
@require_http_methods(["POST"])
def add_device_id_to_file_sync_file(request):
    """
    Associates a device ID with a specific file in the user's synchronization list.

    Expects a JSON body with 'file_name' and 'device_name'.

    Args:
        request: The HttpRequest object containing 'file_name' and 'device_name'.
        username: The username who owns the file and device.

    Returns:
        JsonResponse: A JSON response indicating the result and message of the operation.
    """
    try:
        data = json.loads(request.body)
        file_name = data.get("file_name")
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    username = request.username_from_token

    response = db_add_device_id_to_file_sync_file(username, file_name, device_name)
    print(response)


    files_data = {
        "result": response.get("result"),
        "message": response.get("message"),
    }

    return JsonResponse(files_data)


@csrf_exempt
@require_http_methods(["POST"])
def update_sync_storage_capacity(request):
    """
    Updates the reported storage capacity for a specific device associated with the user.

    Expects a JSON body with 'device_name' and 'storage_capacity'.

    Args:
        request: The HttpRequest object containing 'device_name' and 'storage_capacity'.
        username: The username who owns the device.

    Returns:
        JsonResponse: A JSON response indicating the result and message of the operation,
                      or an error if JSON is invalid.
    """
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        storage_capacity = data.get("storage_capacity")
        username = request.username_from_token
        response = db_update_sync_storage_capacity(username, device_name, storage_capacity)

        print(response)

        files_data = {
            "result": response.get("result"),
            "message": response.get("message"),
        }

        return JsonResponse(files_data)



    except json.JSONDecodeError:

        return JsonResponse({"error": "Invalid JSON"}, status=400)



@csrf_exempt
@require_http_methods(["POST"])
def get_download_queue(request):
    """
    Retrieves the download queue for a specific device belonging to the user.

    Expects a JSON body with 'device_id'.

    Args:
        request: The HttpRequest object containing 'device_id'.
        username: The username who owns the device.

    Returns:
        JsonResponse: A JSON response containing the download queue or an error message.
    """
    username = request.username_from_token
    try:
        data = json.loads(request.body)
        device_id = data.get("device_id")
        response = db_get_download_queue(username, device_id)
        print("response: ", response)
        return JsonResponse({
            "result": "success",
            "download_queue": response,
            "message": "Download queue retrieved successfully",
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
@require_http_methods(["GET"])
def get_device_prediction_data(request):
    """
    Retrieves the device prediction data for the specified user.

    Args:
        request: The HttpRequest object.
        username: The username whose prediction data is being requested.

    Returns:
        JsonResponse: A JSON response containing the device prediction data.
    """
    username = request.username_from_token
    result = db_get_device_predictions(username)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["POST"])
def store_device_predictions(request):
    """
    Stores device predictions in the device_info_predictions MongoDB collection.
    Expects a JSON body with predictions.
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    collection = db["device_info_predictions"]

    try:
        data = json.loads(request.body)
        predictions = data.get("predictions", [])
        for doc in predictions:
            # Convert ISO string to Python datetime for MongoDB
            if "timestamp" in doc and isinstance(doc["timestamp"], str):
                try:
                    doc["timestamp"] = datetime.datetime.fromisoformat(doc["timestamp"].replace("Z", "+00:00"))
                except Exception:
                    pass  # If conversion fails, leave as is
            # Convert metadata.device_id to ObjectId
            if "metadata" in doc and isinstance(doc["metadata"], dict):
                device_id = doc["metadata"].get("device_id")
                if device_id and isinstance(device_id, str):
                    try:
                        doc["metadata"]["device_id"] = ObjectId(device_id)
                    except Exception:
                        pass  # If conversion fails, leave as is
        result = collection.insert_many(predictions)
        return JsonResponse({"result": "success", "inserted_ids": [str(_id) for _id in result.inserted_ids]})
    except Exception as e:
        return JsonResponse({"result": "error", "message": str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_device_timeseries_prediction_data(request, device_id):
    """
    Retrieves all timeseries data for a given device_id from the device_info_predictions collection.
    Expects a JSON body with 'device_id'.
    Authenticates using request.username_from_token.
    Returns all documents for the user and device_id.
    """
    try:
        if not device_id:
            return JsonResponse({"result": "error", "message": "Missing device_id"}, status=400)
        username = request.username_from_token
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        device_info_predictions_collection = db["device_info_predictions"]
        user = user_collection.find_one({"username": username})

        device_obj_id = ObjectId(device_id)
        if not user:
            return JsonResponse({"result": "error", "message": "User not found"}, status=401)
        # Query for all timeseries docs for this user and device_id

        timeseries_docs = list(device_info_predictions_collection.find({"metadata.device_id": device_obj_id}))
        # Convert ObjectId and datetime fields to strings for JSON serialization
        for doc in timeseries_docs:
            doc["_id"] = str(doc["_id"])
            if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
                doc["timestamp"] = doc["timestamp"].isoformat()
            if "metadata" in doc and "device_id" in doc["metadata"]:
                doc["metadata"]["device_id"] = str(doc["metadata"]["device_id"])
        return JsonResponse({"result": "success", "data": timeseries_docs})
    except json.JSONDecodeError:
        return JsonResponse({"result": "error", "message": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"result": "error", "message": str(e)}, status=500)
