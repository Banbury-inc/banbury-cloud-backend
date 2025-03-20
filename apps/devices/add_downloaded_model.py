import json
from pymongo import MongoClient

def add_downloaded_model(username, device_name, model_name):
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

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return {"error": "Device not found.", "status": 404}

    # Ensure "downloaded_models" is an array, then add "name" to it
    try:
        # Check if "downloaded_models" is not an array, set it as an empty array
        if not isinstance(device.get("downloaded_models"), list):
            device_collection.update_one(
                {"_id": device["_id"]},
                {"$set": {"downloaded_models": []}}
            )

        # Push "name" to the "downloaded_models" array
        device_collection.update_one(
            {"_id": device["_id"]},
            {"$push": {"downloaded_models": model_name}}
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return {"error": "Failed to update device status.", "status": 500}

    # Return success response
    return {"result": "success", "username": username, "status": 200}

def main():
    # Test the function
    username = "mmills"
    device_name = "michael-mills-ubuntu"
    model_name = "model_1"
    
    print(f"Testing with username: {username}, device: {device_name}, model: {model_name}")
    response = add_downloaded_model(username, device_name, model_name)
    print(f"\nResponse:")
    print(json.dumps(response, indent=2))

if __name__ == "__main__":
    main()
