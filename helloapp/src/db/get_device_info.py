from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def get_device_info(username):
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
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))

    # Prepare devices data for response
    device_data = []
    for device in devices:
        device_data.append({
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
            "current_time": device.get("current_time"),
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
        })

    device_data = {
        "devices": device_data,
    }

    return device_data

if __name__ == "__main__":
    device_info = get_device_info("mmills")
    print(device_info)
