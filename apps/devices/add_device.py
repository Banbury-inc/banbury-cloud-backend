from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
import json
from django.views.decorators.csrf import csrf_exempt
from .update_device_configuration_preferences import update_device_configuration_preferences

@csrf_exempt
def add_device(request, username, device_name):
    """
    Adds a new device associated with a specific user.

    Retrieves device details from the POST request body and associates
    the new device with the user identified by the username in the URL.

    Args:
        request: The Django HttpRequest object.
        username (str): The username of the owner of the device.
        device_name (str): The name of the device (passed in URL but overridden by POST body).

    Returns:
        JsonResponse: A JSON response indicating success or failure.
                      On success, includes the username.
    """
    try:
        print(request)
        data = json.loads(request.body)
        # Map frontend camelCase fields to backend snake_case
        device_name = data.get("device_name", device_name)
        storage_capacity_gb = data.get("storageCapacityGB")
        max_storage_capacity_gb = data.get("maxStorageCapacityGB")
        device_manufacturer = data.get("device_manufacturer")
        device_model = data.get("device_model")
        device_version = data.get("device_version")
        services = data.get("services")
        cpu_info_brand = data.get("cpu_info_brand")
        cpu_info_cores = data.get("cpu_info_cores")
        cpu_info_processors = data.get("cpu_info_processors")
        cpu_info_physical_cores = data.get("cpu_info_physicalCores")
        ip_address = data.get("ip_address")
        mac_address = data.get("mac_address")
        device_priority = data.get("device_priority", 1)
        sync_status = data.get("sync_status", False)
        optimization_status = data.get("optimization_status", False)
        online = data.get("online", True)
        date_added = data.get("date_added")
        sync_storage_capacity_gb = data.get("sync_storage_capacity_gb")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority" 
    client = MongoClient(uri)
    db = client["NeuraNet"]
    device_collection = db["devices"]
    user_collection = db["users"]

    # Find the user_id based on username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"result": "error", "message": "User not found."})

    user_id = user["_id"]  # Get the ObjectId for the device

    # Check if device with same name already exists for this user
    existing_device = device_collection.find_one({
        "user_id": user_id,
        "device_name": device_name
    })
    
    if existing_device:
        return JsonResponse({
            "result": "error",
            "message": "Device already exists."
        })

    new_device = {
        "user_id": user_id,
        "device_name": device_name,
        "storage_capacity_gb": storage_capacity_gb,
        "max_storage_capacity_gb": max_storage_capacity_gb,
        "device_manufacturer": device_manufacturer,
        "device_model": device_model,
        "device_version": device_version,
        "services": services,
        "cpu_info_brand": cpu_info_brand,
        "cpu_info_cores": cpu_info_cores,
        "cpu_info_processors": cpu_info_processors,
        "cpu_info_physical_cores": cpu_info_physical_cores,
        "ip_address": ip_address,
        "mac_address": mac_address,
        "device_priority": device_priority,
        "sync_status": sync_status,
        "optimization_status": optimization_status,
        "online": online,
        "date_added": date_added,
        "sync_storage_capacity_gb": sync_storage_capacity_gb,
        "scanned_folders": [],
        "downloaded_models": [],
    }

    try:
        # Insert the new device and get the inserted_id
        result = device_collection.insert_one(new_device)
        device_id = result.inserted_id

        # Update the user collection to add the device_id to the user's list of devices
        user_collection.update_one({"_id": user_id}, {"$push": {"devices": device_id}})

        # No need to $push usage arrays if they're empty or not provided

        device_configurations = {
            "device_id": device_id,
        }
        update_device_configuration_preferences(username, device_name, device_configurations=device_configurations)

    except Exception as e:
        print(f"Error sending to device: {e}")
        return JsonResponse({
            "result": "error",
            "message": f"Failed to add device: {str(e)}"
        }, status=500)

    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)
