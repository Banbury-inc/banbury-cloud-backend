from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson.objectid import ObjectId

def get_single_device_info(device_id):
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
        "_id": str(device["_id"]) if device else None,
        "user_id": str(device["user_id"]) if device else None,
        "device_name": device["device_name"] if device else None,
        "device_type": device["device_type"] if device else None,
        "storage_capacity_gb": device["storage_capacity_gb"] if device else None,
        "sync_storage_capacity_gb": device["sync_storage_capacity_gb"] if device else None,
        "device_manufacturer": device["device_manufacturer"] if device else None,
        "device_model": device["device_model"] if device else None,
        "device_version": device["device_version"] if device else None,
        "cpu_info_manufacturer": device["cpu_info_manufacturer"] if device else None,
        "cpu_info_brand": device["cpu_info_brand"] if device else None,
        "cpu_info_speed": device["cpu_info_speed"] if device else None,
        "cpu_info_cores": device["cpu_info_cores"] if device else None,
        "cpu_info_physical_cores": device["cpu_info_physical_cores"] if device else None,
        "cpu_info_processors": device["cpu_info_processors"] if device else None,
        "date_added": device["date_added"] if device else None,
        "current_time": device["current_time"] if device else None,
        "upload_speed": device["upload_speed"] if device else None,
        "download_speed": device["download_speed"] if device else None,
        "battery_status": device["battery_status"] if device else None,
        "gpu_usage": device["gpu_usage"] if device else None,
        "cpu_usage": device["cpu_usage"] if device else None,
        "ram_usage": device["ram_usage"] if device else None,
        "ram_total": device["ram_total"] if device else None,
        "ram_free": device["ram_free"] if device else None,
        "sync_status": device["sync_status"] if device else None,
        "online": device["online"] if device else None,
        "scanned_folders": device["scanned_folders"] if device else None,
    }

    device_data = {
        "device_info": device_data,
    }

    return device_data

if __name__ == "__main__":
    device_info = get_single_device_info("mmills", "6756092e76ebec5a4ac8cd09")
    print(device_info)