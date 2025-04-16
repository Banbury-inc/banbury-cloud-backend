from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson.objectid import ObjectId

def get_single_device_info(device_id):
    """
    Retrieves detailed information for a single device using its MongoDB ObjectId.

    Connects to MongoDB and fetches the device document corresponding to the
    provided device_id. Formats the device data into a dictionary.

    Args:
        device_id (str): The MongoDB ObjectId of the device as a string.

    Returns:
        dict: A dictionary containing the device details under the key "device_info".
              If the connection fails, returns {"error": "..."}.
              If the device is not found, returns a dictionary with None values
              for all device fields under "device_info".
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        device_collection = db["devices"]
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return {"error": "Failed to connect to MongoDB"}

    device_id = ObjectId(device_id)

    # Find all devices belonging to the user
    device = device_collection.find_one({"_id": device_id})

    device_data = {
        "_id": str(device.get("_id")) if device and device.get("_id") else None,
        "user_id": str(device.get("user_id")) if device and device.get("user_id") else None,
        "device_name": device.get("device_name") if device else None,
        "device_type": device.get("device_type") if device else None,
        "storage_capacity_gb": device.get("storage_capacity_gb") if device else None,
        "sync_storage_capacity_gb": device.get("sync_storage_capacity_gb") if device else None,
        "device_manufacturer": device.get("device_manufacturer") if device else None,
        "device_model": device.get("device_model") if device else None,
        "device_version": device.get("device_version") if device else None,
        "cpu_info_manufacturer": device.get("cpu_info_manufacturer") if device else None,
        "cpu_info_brand": device.get("cpu_info_brand") if device else None,
        "cpu_info_speed": device.get("cpu_info_speed") if device else None,
        "cpu_info_cores": device.get("cpu_info_cores") if device else None,
        "cpu_info_physical_cores": device.get("cpu_info_physical_cores") if device else None,
        "cpu_info_processors": device.get("cpu_info_processors") if device else None,
        "date_added": device.get("date_added") if device else None,
        "current_time": device.get("current_time") if device else None,
        "upload_speed": device.get("upload_speed") if device else None,
        "download_speed": device.get("download_speed") if device else None,
        "battery_status": device.get("battery_status") if device else None,
        "gpu_usage": device.get("gpu_usage") if device else None,
        "cpu_usage": device.get("cpu_usage") if device else None,
        "ram_usage": device.get("ram_usage") if device else None,
        "ram_total": device.get("ram_total") if device else None,
        "ram_free": device.get("ram_free") if device else None,
        "sync_status": device.get("sync_status") if device else None,
        "online": device.get("online") if device else None,
        "scanned_folders": device.get("scanned_folders") if device else None,
    }

    device_data = {
        "device_info": device_data,
    }

    return device_data

if __name__ == "__main__":
    """Script execution entry point for testing get_single_device_info."""
    # Note: The original call had two arguments, but the function only takes one.
    # Assuming the first argument was intended to be the device_id.
    # Replace "6756092e76ebec5a4ac8cd09" with a valid ObjectId for testing.
    device_info = get_single_device_info("6756092e76ebec5a4ac8cd09")
    print(device_info)