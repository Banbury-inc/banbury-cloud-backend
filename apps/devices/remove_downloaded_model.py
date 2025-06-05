import json
from pymongo import MongoClient
from bson import ObjectId


def remove_downloaded_model(username, device_id, model_name):
    """
    Removes a model name from the list of downloaded models for a specific device.

    Connects to MongoDB, finds the user and device, checks if the model exists
    in the 'downloaded_models' array, and removes it using $pull.

    Args:
        username (str): The username of the device owner.
        device_id (str): The id of the device as a string.
        model_name (str): The name of the model to remove.

    Returns:
        dict: A dictionary containing the result ("success" or "error"),
              a message or username, and an HTTP status code.
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
        return {"error": "User not found.", "status": 404}

    # Convert device_id string to ObjectId
    try:
        device_object_id = ObjectId(device_id)
    except Exception as e:
        return {"error": "Invalid device ID format.", "status": 400}

    # Find the device belonging to the user by device_id
    device = device_collection.find_one({
        "user_id": user["_id"],
        "_id": device_object_id,
    })
    if not device:
        return {"error": "Device not found.", "status": 404}

    # Ensure "downloaded_models" exists and is an array
    if not isinstance(device.get("downloaded_models"), list):
        return {"error": "No downloaded models found.", "status": 404}

    # Check if the model exists in the downloaded_models array
    if model_name not in device["downloaded_models"]:
        return {"error": "Model not found in downloaded models.", "status": 404}

    try:
        # Remove the model from the downloaded_models array
        device_collection.update_one(
            {"_id": device["_id"]},
            {"$pull": {"downloaded_models": model_name}}
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return {"error": "Failed to update device status.", "status": 500}

    # Return success response
    return {"result": "success", "username": username, "status": 200}

