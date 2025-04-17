from pymongo.mongo_client import MongoClient
from datetime import datetime

def update_device_score(username, device_name, device_score):
    """Updates or inserts the score for a specific device.

    Finds the user and device, then updates only the 'score' and 'score_timestamp'
    fields in the corresponding 'device_predictions' document using upsert.
    Preserves existing prediction data.

    Args:
        username (str): The username of the user.
        device_name (str): The name of the device whose score is being updated.
        device_score (float): The new calculated score for the device.

    Returns:
        str: "success" if the update/insert is successful, "user not found" or
             "device not found" if lookups fail, or "error" if a database
             exception occurs.
    """
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
