from pymongo.mongo_client import MongoClient
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def update_device(username, sending_device_name, requesting_device_name, device_info):

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    user_collection = db["users"]

    storage_capcity_gb = device_info['storageCapacity']

    # Find the user by username
    user = user_collection.find_one({"username": username})

    # Update the storage capacity for the specific device
    result = user_collection.update_one(
        {"_id": user["_id"], "devices.device_name": sending_device_name},
        {"$set": {"devices.$.storage_capacity_gb": storage_capcity_gb}}
    )

    # Check if the update was successful
    if result.modified_count > 0:
        response = "success"
        return response
    else:
        response = "no change needed"
        return response
