from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def update_device(username, sending_device_name, requesting_device_name, device_info):
    """
    Updates the information for a specific device based on received data.

    Connects to MongoDB, finds the user by username, finds the device by the
    'sending_device_name', and updates its details using $set for static info
    and $push for time-series data (usage, speeds, etc.).

    Args:
        username (str): The username of the device owner.
        sending_device_name (str): The name of the device whose info is being updated.
        requesting_device_name (str): The name of the device that requested the info (currently unused).
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
    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

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

    # Prepare update data
    update_data = {
        "storage_capacity_gb": device_info['storage_capacity_gb'],
        "device_manufacturer": device_info['device_manufacturer'],
        "device_model": device_info['device_model'],
        "device_version": device_info['device_version'],
        "cpu_info_manufacturer": device_info['cpu_info_manufacturer'],
        "cpu_info_brand": device_info['cpu_info_brand'],
        "cpu_info_speed": device_info['cpu_info_speed'],
        "cpu_info_cores": device_info['cpu_info_cores'],
        "cpu_info_physical_cores": device_info['cpu_info_physical_cores'],
        "cpu_info_processors": device_info['cpu_info_processors'],
        "ip_address": device_info['ip_address'],
        "mac_address": device_info['mac_address'],
        "battery_status": device_info['battery_status'],
        "battery_time_remaining": device_info['battery_time_remaining'],
        "bluetooth_status": device_info['bluetooth_status'],
    }

    # Update the device information
    try:
        device_collection.update_one(
            {"_id": device["_id"]},
            {
                "$set": update_data,
                "$push": {
                    "current_time": device_info['current_time'],
                    "cpu_usage": device_info['cpu_usage'],
                    "gpu_usage": device_info['gpu_usage'],
                    "ram_usage": device_info['ram_usage'],
                    "ram_total": device_info['ram_total'],
                    "ram_free": device_info['ram_free'],
                    "upload_speed": device_info['upload_speed'],
                    "download_speed": device_info['download_speed'],
                }
            }
        )
        return "success"
    except Exception as e:
        print(f"Error updating device status: {e}")
        return "error"
