from pymongo.mongo_client import MongoClient
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def update_device(username, sending_device_name, requesting_device_name, device_info):

    storage_capacity_gb = device_info['storageCapacity']

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

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"storage_capacity_gb": storage_capacity_gb}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return "error"








