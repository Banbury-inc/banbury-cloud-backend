from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime

def update_device_score(username, device_name, device_score):
    '''
    Update a single device's score in the database while preserving prediction data
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

    # Only update score-related fields
    score_update = {
        "score": device_score,
        "score_timestamp": datetime.now()  # separate timestamp for score updates
    }

    # Update only the score fields while preserving other data
    try:
        predictions_collection.update_one(
            {"device_id": device["_id"]},  # find by device_id
            {"$set": score_update},        # only update score-related fields
            upsert=True                    # create new document if none exists
        )
        return "success"
    except Exception as e:
        print(f"Error updating device score: {e}")
        return "error"
