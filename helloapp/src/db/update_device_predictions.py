from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime

def update_device_predictions(username, device_name, device_predictions):
    '''
    Update a single device's predictions in the database
    '''

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    predictions_collection = db["device_predictions"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return "user not found"

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return "device not found"

    # Create prediction document
    prediction_data = {
        "user_id": user["_id"],
        "device_id": device["_id"],
        "device_name": device_name,
        "sync_storage_capacity_gb": device.get("sync_storage_capacity_gb"),
        "predicted_upload_speed": device_predictions['predicted_upload_speed'],
        "predicted_download_speed": device_predictions['predicted_download_speed'],
        "predicted_gpu_usage": device_predictions['predicted_gpu_usage'],
        "predicted_cpu_usage": device_predictions['predicted_cpu_usage'],
        "predicted_ram_usage": device_predictions['predicted_ram_usage'],
        "timestamp": datetime.now()
    }

    # Update existing prediction or insert new one using upsert
    try:
        predictions_collection.update_one(
            {"device_id": device["_id"]},  # find by device_id
            {"$set": prediction_data},      # update with new prediction data
            upsert=True                     # create new document if none exists
        )
        return "success"
    except Exception as e:
        print(f"Error updating device predictions: {e}")
        return "error"
