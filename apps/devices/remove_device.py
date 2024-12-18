from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def remove_device(username, device_name):
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
        "device_name": device_name,
    })
    if not device:
        return "device not found"

    # Delete the device
    try:
        result = device_collection.delete_one({"_id": device["_id"]})
        if result.deleted_count == 1:
            return "success"
        else:
            return "device not deleted"
    except Exception as e:
        print(f"Error deleting device: {e}")
        return "error"
