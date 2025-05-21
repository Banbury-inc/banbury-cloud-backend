from pymongo.mongo_client import MongoClient


def get_single_device_info_with_device_name(username, device_name):
    """
    Retrieves detailed information for a single device using its name and owner's username.

    Connects to MongoDB, finds the user by username, then finds the specific
    device by its name associated with that user's ID. Formats the device
    data into a dictionary.

    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device to retrieve.

    Returns:
        dict: A dictionary containing the device details under the key "device_info",
              or an error message under the key "error" if the connection fails,
              the user is not found, or the device is not found for that user.
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        device_collection = db["devices"]
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return {"error": "Failed to connect to MongoDB"}

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"result": "error", "message": "Please login first."}

    # Find all devices belonging to the user
    device = device_collection.find_one({"user_id": user["_id"], "device_name": device_name})

    if not device:
        return {"result": "error", "message": f"Device '{device_name}' not found for user '{username}'."}

    device_data = {
        "_id": str(device["_id"]),
        "device_name": device.get("device_name", ""),
        "device_type": device.get("device_type", ""),
        "storage_capacity_gb": device.get("storage_capacity_gb", ""),
        "sync_storage_capacity_gb": device.get("sync_storage_capacity_gb", ""),
        "device_manufacturer": device.get("device_manufacturer", ""),
        "device_model": device.get("device_model", ""),
        "device_version": device.get("device_version", ""),
        "cpu_info_manufacturer": device.get("cpu_info_manufacturer", ""),
        "cpu_info_brand": device.get("cpu_info_brand", ""),
        "cpu_info_speed": device.get("cpu_info_speed", ""),
        "cpu_info_cores": device.get("cpu_info_cores", ""),
        "cpu_info_physical_cores": device.get("cpu_info_physical_cores", ""),
        "cpu_info_processors": device.get("cpu_info_processors", ""),
        "date_added": device.get("date_added", ""),
        "current_time": device.get("current_time", ""),
        "upload_speed": device.get("upload_speed", ""),
        "download_speed": device.get("download_speed", ""),
        "battery_status": device.get("battery_status", ""),
        "gpu_usage": device.get("gpu_usage", ""),
        "cpu_usage": device.get("cpu_usage", ""),
        "ram_usage": device.get("ram_usage", ""),
        "ram_total": device.get("ram_total", ""),
        "ram_free": device.get("ram_free", ""),
        "sync_status": device.get("sync_status", ""),
        "online": device.get("online", ""),
        "scanned_folders": device.get("scanned_folders", ""),
    }

    device_data = {
        "device_info": device_data,
    }

    return device_data

if __name__ == "__main__":
    """Script execution entry point for testing get_single_device_info_with_device_name."""
    device_info = get_single_device_info_with_device_name("mmills", "michael-mills-ubuntu")
    print(device_info)
