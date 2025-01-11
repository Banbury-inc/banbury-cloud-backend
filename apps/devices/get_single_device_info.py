from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson.objectid import ObjectId

def get_single_device_info(username, device_id):
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

    device_id = ObjectId(device_id)
    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    device = device_collection.find_one({"user_id": user["_id"], "_id": device_id})

    device_data = {
        "device_name": device["device_name"],
        "device_type": device["device_type"],
        "storage_capacity_gb": device["storage_capacity_gb"],
        "sync_storage_capacity_gb": device["sync_storage_capacity_gb"],
        "device_manufacturer": device["device_manufacturer"],
        "device_model": device["device_model"],
        "device_version": device["device_version"],
        "cpu_info_manufacturer": device["cpu_info_manufacturer"],
        "cpu_info_brand": device["cpu_info_brand"],
        "cpu_info_speed": device["cpu_info_speed"],
        "cpu_info_cores": device["cpu_info_cores"],
        "cpu_info_physical_cores": device["cpu_info_physical_cores"],
        "cpu_info_processors": device["cpu_info_processors"],
        "date_added": device["date_added"],
        "current_time": device["current_time"],
        "upload_speed": device["upload_speed"],
        "download_speed": device["download_speed"],
        "battery_status": device["battery_status"],
        "gpu_usage": device["gpu_usage"],
        "cpu_usage": device["cpu_usage"],
        "ram_usage": device["ram_usage"],
        "ram_total": device["ram_total"],
        "ram_free": device["ram_free"],
        "sync_status": device["sync_status"],
        "online": device["online"],
        "scanned_folders": device["scanned_folders"],
    }

    device_data = {
        "device_info": device_data,
    }

    return device_data

if __name__ == "__main__":
    device_info = get_single_device_info("mmills", "6756092e76ebec5a4ac8cd09")
    print(device_info)