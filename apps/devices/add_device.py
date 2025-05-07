from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
import json
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def add_device(request, device_name):
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
        data = json.loads(request.body)
        device_name = data.get("device_name")
        device_type = data.get("device_type")
        storage_capacity_gb = data.get("storage_capacity_gb")
        sync_storage_capacity_gb = data.get("sync_storage_capacity_gb")
        date_added = data.get("date_added")
        upload_network_speed = data.get("upload_network_speed")
        download_network_speed = data.get("download_network_speed")
        gpu_usage = data.get("gpu_usage")
        cpu_usage = data.get("cpu_usage")
        ram_usage = data.get("ram_usage")
        ram_total = data.get("ram_total")
        ram_free = data.get("ram_free")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority" 
    client = MongoClient(uri)
    db = client["NeuraNet"]
    device_collection = db["devices"]
    user_collection = db["users"]

    # Find the user_id based on username
    user = user_collection.find_one({"username": request.username_from_token})
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
        "device_type": device_type,
        "storage_capacity_gb": storage_capacity_gb,
        "sync_storage_capacity_gb": sync_storage_capacity_gb,
        "date_added": [],
        "upload_network_speed": [],
        "download_network_speed": [],
        "gpu_usage": [],
        "cpu_usage": [],
        "ram_usage": [],
        "ram_total": [],
        "ram_free": [],
        "sync_status": False,
        "online": True,
    }

    try:
        # Insert the new device and get the inserted_id
        result = device_collection.insert_one(new_device)
        device_id = result.inserted_id

        # Update the user collection to add the device_id to the user's list of devices
        user_collection.update_one({"_id": user_id}, {"$push": {"devices": device_id}})

        # Append all usage data and other arrays in the device document
        device_collection.update_one(
            {"_id": device_id},
            {
                "$push": {
                    "gpu_usage": gpu_usage,
                    "cpu_usage": cpu_usage,
                    "ram_usage": ram_usage,
                    "ram_total": ram_total,
                    "ram_free": ram_free,
                    "download_network_speed": download_network_speed,
                    "upload_network_speed": upload_network_speed,
                    "date_added": date_added,
                }
            },
        )

    except Exception as e:
        print(f"Error sending to device: {e}")
        return JsonResponse({
            "result": "error",
            "message": f"Failed to add device: {str(e)}"
        }, status=500)

    result = "success"

    user_data = {
        "result": result,
        "username": request.username_from_token,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)
