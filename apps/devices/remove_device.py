from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def remove_device(username, device_name):
    """
    Removes a specific device associated with a user from the database.

    Connects to MongoDB, finds the user by username, finds the device by name
    belonging to that user, and deletes the device document.

    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device to remove.

    Returns:
        str: "success" if the device was deleted successfully.
             "user not found" if the user does not exist.
             "device not found" if the device does not exist for that user.
             "device not deleted" if the delete operation reported 0 deletions.
             "error" if an exception occurred during deletion.
    """
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
