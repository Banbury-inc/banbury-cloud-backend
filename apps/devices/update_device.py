from pymongo.mongo_client import MongoClient
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json

def update_device_info(username, sending_device_name, device_info):
    """
    Updates the information for a specific device based on received data.

    Connects to MongoDB, finds the user by username, finds the device by the
    'sending_device_name', and updates its details using $set for static info
    and $push for time-series data (usage, speeds, etc.).

    Args:
        username (str): The username of the device owner.
        sending_device_name (str): The name of the device whose info is being updated.
        device_info (dict): A dictionary containing the new device details.
                            Expected keys include static info (like manufacturer,
                            model, capacity) and time-series data points (like
                            cpu_usage, ram_usage, speeds, current_time).

    Returns:
        str: "success" if the update was successful.
             "user not found" if the user does not exist.
             "device not found" if the sending device does not exist for that user.
             "error" if an exception occurred during the database update.
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    device_info_collection = db["device_info"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return "user not found"

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": sending_device_name,
    })
    if not device:
        return "device not found"

    # Instead of inserting a new document, append time-series data to arrays in a single document per device_id
    if device_info is None:
        print("Error: device_info is None. Not inserting.")
        return "error: device_info is None"
    try:
        # Prepare the $push update for time-series fields
        push_update = {
            "timestamp": device_info.get('current_time'),
            "storage_capacity_gb": device_info.get('storage_capacity_gb'),
            "battery_status": device_info.get('battery_status'),
            "battery_time_remaining": device_info.get('battery_time_remaining'),
            "cpu_usage": device_info.get('cpu_usage'),
            "cpu_info_speed": device_info.get('cpu_info_speed'),
            "gpu_usage": device_info.get('gpu_usage'),
            "ram_usage": device_info.get('ram_usage'),
            "ram_total": device_info.get('ram_total'),
            "ram_free": device_info.get('ram_free'),
            "upload_speed": device_info.get('upload_speed'),
            "download_speed": device_info.get('download_speed'),
        }
        # Prepare the $set update for static fields
        set_update = {
            "device_id": device["_id"],
            "username": username,
            "device_name": sending_device_name,
        }
        print("Attempting to update device info arrays for device_id:", device["_id"])
        result = device_info_collection.update_one(
            {"device_id": device["_id"]},
            {
                "$push": {k: v for k, v in push_update.items() if v is not None},
                "$set": {k: v for k, v in set_update.items() if v is not None},
            },
            upsert=True
        )
        print("Update successful, matched_count:", result.matched_count, "modified_count:", result.modified_count)
        return "success"
    except Exception as e:
        print(f"Error updating device status: {e}")
        return "error"

def update_device_info_view(request):
    data = json.loads(request.body)
    username = request.username_from_token
    device_info = data.get("device_info")
    sending_device_name = data.get("sending_device_name")
    print("View received username:", username, "sending_device_name:", sending_device_name, "device_info:", device_info, flush=True)
    result = update_device_info(username, sending_device_name, device_info)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)

