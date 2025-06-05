from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
from bson import ObjectId
from .remove_device import remove_device
from .get_online_devices import get_online_devices
from .update_device_configuration_preferences import update_device_configuration_preferences as db_update_device_configuration_preferences
from .get_single_device_info import get_single_device_info as db_get_single_device_info
from .get_single_device_info_with_device_name import get_single_device_info_with_device_name as db_get_single_device_info_with_device_name
from .add_downloaded_model import add_downloaded_model as db_add_downloaded_model
from .remove_downloaded_model import remove_downloaded_model as db_remove_downloaded_model
from .add_device import add_device
from .update_device import update_device_info as db_update_device_info
import json

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_device_view(request, device_name):
    """
    View function that handles the add_device request.
    
    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.
        device_name (str): The name of the device (passed in URL but overridden by POST body).

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    username = getattr(request, 'username_from_token', None)
    return add_device(request, username, device_name)





@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def delete_device(request):
    """
    Deletes a device associated with a specific user.

    Retrieves the device name from the POST request body and removes the
    corresponding device entry for the user identified by the username in the URL.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        username = request.username_from_token
        response = remove_device(username, device_name)
        print('response', response)
        if response == "success":
            return JsonResponse({
                "result": "success",
                "message": "Device deleted successfully.",
            })
        else:
            return JsonResponse({
                "result": "fail",
                "message": response,
            })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)





@csrf_exempt
@require_http_methods(["GET", "POST"])
def update_device_configuration_preferences(request):
    """
    Updates the configuration preferences for a specific device.

    Retrieves the device name and configuration settings from the request body
    and updates the corresponding device for the user identified by the username.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.

    Returns:
        JsonResponse: A JSON response indicating success and returning the updated data.
    """
    data = json.loads(request.body)
    device_name = data.get("device_name")
    username = request.username_from_token
    device_configurations = {
        "use_device_in_file_sync": data.get("use_device_in_file_sync"),
        "use_predicted_cpu_usage": data.get("use_predicted_cpu_usage"),
        "use_predicted_gpu_usage": data.get("use_predicted_gpu_usage"),
        "use_predicted_ram_usage": data.get("use_predicted_ram_usage"),
        "use_predicted_download_speed": data.get("use_predicted_download_speed"),
        "use_predicted_upload_speed": data.get("use_predicted_upload_speed"),
        "use_files_needed": data.get("use_files_needed"),
        "use_files_available_for_download": data.get("use_files_available_for_download"),
    }
    result = db_update_device_configuration_preferences(username, device_name, device_configurations)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)



@csrf_exempt
@require_http_methods(["GET"])
def getdeviceinfo(request):
    """
    Retrieves information for all devices associated with a specific user.

    Fetches device details from the database for the user identified
    by the username in the URL.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the user whose devices are to be retrieved.

    Returns:
        JsonResponse: A JSON response containing a list of device details
                      or an error message if the user is not found.
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    username = request.username_from_token

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({"error": "Please login first."}, status=401)

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))

    # Prepare devices data for response
    device_data = []
    for device in devices:
        device_data.append({
            "_id": str(device.get("_id")),
            "device_name": device.get("device_name"),
            "device_type": device.get("device_type"),
            "storage_capacity_gb": device.get("storage_capacity_gb"),
            "device_manufacturer": device.get("device_manufacturer"),
            "device_model": device.get("device_model"),
            "device_version": device.get("device_version"),
            "cpu_info_manufacturer": device.get("cpu_info_manufacturer"),
            "cpu_info_brand": device.get("cpu_info_brand"),
            "cpu_info_speed": device.get("cpu_info_speed"),
            "cpu_info_cores": device.get("cpu_info_cores"),
            "cpu_info_physical_cores": device.get("cpu_info_physical_cores"),
            "cpu_info_processors": device.get("cpu_info_processors"),
            "date_added": device.get("date_added"),
            "upload_speed": device.get("upload_speed"),
            "download_speed": device.get("download_speed"),
            "battery_status": device.get("battery_status"),
            "gpu_usage": device.get("gpu_usage"),
            "cpu_usage": device.get("cpu_usage"),
            "ram_usage": device.get("ram_usage"),
            "ram_total": device.get("ram_total"),
            "ram_free": device.get("ram_free"),
            "sync_status": device.get("sync_status"),
            "online": device.get("online"),
            "scanned_folders": device.get("scanned_folders"),
            "downloaded_models": device.get("downloaded_models"),
        })

    device_data = {
        "devices": device_data,
    }

    return JsonResponse(device_data)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def handle_get_online_devices(request):
    """
    Retrieves a list of online devices for a specific user.

    Calls the get_online_devices function to fetch the status of devices
    for the user identified by the username.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the user.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
                      On success, the message indicates successful deletion (which seems incorrect based on function name).
                      TODO: Review the response message for accuracy.
    """
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        username = data.get("username")

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    response = get_online_devices(username)

    if response == "fail":
        return JsonResponse({"result": "fail", "message": "fail"})
    if response == "success":
        return JsonResponse({
            "result": "success",
            "message": "Files deleted successfully.",
        })



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def declare_device_online(request):
    """
    Marks a specific device as online in the database.

    Retrieves the device name from the POST request body and sets the 'online'
    status to True for the corresponding device of the specified user.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        username = request.username_from_token
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        user_data = {"result": "fail cant find user", "username": username}
        return JsonResponse(user_data)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        # Return success response
        user_data = {"result": "fail cant find device", "username": username}
        return JsonResponse(user_data)

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"online": True}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def declare_device_offline(request):
    """
    Marks a specific device as offline in the database.

    Retrieves the device name from the POST request body and sets the 'online'
    status to False for the corresponding device of the specified user.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.

    Returns:
        JsonResponse: A JSON response indicating success or failure.
    """
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        username = request.username_from_token
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"online": False}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)



@require_http_methods(["POST"])
def get_single_device_info(request, device_id):
    """
    Retrieves detailed information for a single device using its database ID.

    Calls the db_get_single_device_info function to fetch details.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.
        device_id (str): The MongoDB ObjectId of the device as a string.

    Returns:
        JsonResponse: A JSON response containing the device information.
    """
    username = request.username_from_token

    device_info = db_get_single_device_info(username, device_id)

    return JsonResponse(device_info)

def get_single_device_info_with_device_name(request, device_name):
    """
    Retrieves detailed information for a single device using its name.

    Calls the db_get_single_device_info_with_device_name function to fetch details.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.
        device_name (str): The name of the device.

    Returns:
        JsonResponse: A JSON response containing the device information.
    """
    username = request.username_from_token
    device_info = db_get_single_device_info_with_device_name(username, device_name)
    return JsonResponse(device_info)



@csrf_exempt
@require_http_methods(["POST"])
def add_downloaded_model(request):
    """
    Adds a record indicating a model has been downloaded to a specific device.

    Retrieves the device ID (as string) and model name from the POST request body.
    Updates the device record for the specified user.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.

    Returns:
        JsonResponse: A JSON response indicating success or failure, including
                      appropriate status codes and messages.
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        device_id = data.get("device_id")
        model_name = data.get("model_name")
        
        # Convert string device_id to ObjectId
        if device_id == "":
            return JsonResponse({
                "result": "fail",
                "message": "Device ID is required",
            }, status=400)
            
        response = db_add_downloaded_model(username, device_id, model_name)
        
        if response.get("status") == 200:
            return JsonResponse({
                "result": "success",
                "message": response.get("message", "Model added successfully"),
            })
        else:
            return JsonResponse({
                "result": "fail",
                "message": response.get("error", "Failed to add model"),
            }, status=response.get("status", 500))
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "fail",
            "message": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def remove_downloaded_model(request):
    """
    Adds a record indicating a model has been downloaded to a specific device.

    Retrieves the device ID (as string) and model name from the POST request body.
    Updates the device record for the specified user.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.

    Returns:
        JsonResponse: A JSON response indicating success or failure, including
                      appropriate status codes and messages.
    """
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        device_id = data.get("device_id")
        model_name = data.get("model_name")
        
        # Convert string device_id to ObjectId
        if device_id == "":
            return JsonResponse({
                "result": "fail",
                "message": "Device ID is required",
            }, status=400)
            
        response = db_remove_downloaded_model(username, device_id, model_name)
        
        if response.get("status") == 200:
            return JsonResponse({
                "result": "success",
                "message": response.get("message", "Model removed successfully"),
            })
        else:
            return JsonResponse({
                "result": "fail",
                "message": response.get("error", "Failed to add model"),
            }, status=response.get("status", 500))
            
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "fail",
            "message": str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_single_device_info_with_device_name(request, device_name):
    username = request.username_from_token
    result = db_get_single_device_info_with_device_name(username, device_name)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)

@csrf_exempt
@require_http_methods(["POST"])
def update_device_info(request):
    data = json.loads(request.body)
    username = request.username_from_token
    device_info = data.get("device_info")
    sending_device_name = data.get("sending_device_name")
    print("View received username:", username, "sending_device_name:", sending_device_name, "device_info:", device_info, flush=True)
    result = db_update_device_info(username, sending_device_name, device_info)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)

@csrf_exempt
@require_http_methods(["GET"])
def get_device_timeseries_data(request, device_id):
    """
    Returns all timeseries data for a given device_id from the device_info collection.
    Args:
        request: The Django HttpRequest object.
        device_id (str): The MongoDB ObjectId of the device as a string.
    Returns:
        JsonResponse: A JSON response containing a list of timeseries data documents.
    """
    from bson import ObjectId
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    device_info_collection = db["device_info"]
    try:
        device_obj_id = ObjectId(device_id)
    except Exception:
        return JsonResponse({"error": "Invalid device_id format."}, status=400)
    # Query all timeseries data for this device_id
    timeseries_docs = list(device_info_collection.find({"metadata.device_id": device_obj_id}))
    # Convert ObjectId and datetime fields to strings for JSON serialization
    for doc in timeseries_docs:
        doc["_id"] = str(doc["_id"])
        if "timestamp" in doc and hasattr(doc["timestamp"], "isoformat"):
            doc["timestamp"] = doc["timestamp"].isoformat()
        if "metadata" in doc and "device_id" in doc["metadata"]:
            doc["metadata"]["device_id"] = str(doc["metadata"]["device_id"])
    return JsonResponse({"result": "success", "data": timeseries_docs})
