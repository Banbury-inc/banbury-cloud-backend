from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId

def declare_device_offline_with_id(device_id):
    """
    Marks a device as offline in the database using its MongoDB ObjectId.

    Connects to MongoDB, finds the device by its ID, and sets the 'online'
    field to False. It uses upsert=True, which means if the device is somehow
    not found after the initial check, it might create a new entry (though the
    initial check should prevent this).

    Args:
        device_id (str): The MongoDB ObjectId of the device as a string.

    Returns:
        dict: A dictionary indicating success or error, along with a message
              or the device_id on success.
    """
    print(f"[declare_device_offline] Starting - Device ID: {device_id}")

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    try:
        client = MongoClient(uri)
        db = client['NeuraNet']
        user_collection = db['users']
        device_collection = db['devices']
    except Exception as e:
        print(f"[declare_device_offline] MongoDB connection error: {str(e)}")
        return {"result": "error", "message": "Database connection failed"}

    # Find the device by device_id
    try:
        object_id = ObjectId(device_id)
        device = device_collection.find_one({'_id': object_id})
    except Exception as e:
        print(f"[declare_device_offline] Invalid device ID format: {str(e)}")
        return {"result": "error", "message": "Invalid device ID format"}

    if not device:
        print(f"[declare_device_offline] Device not found: {device_id}")
        return {"result": "error", "message": "Device not found"}

    print(f"[declare_device_offline] Found device: {device['_id']}")
    # Update the "online" field to True
    try:
        result = device_collection.update_one(
            {'_id': device['_id']},
            {'$set': {'online': False}},
            upsert=True  # Create new document if not found
        )
        print(f"[declare_device_offline] Update result - Modified: {result.modified_count}")
        
        return {
            "result": "success",
            "device_id": str(device['_id'])
        }
            
    except Exception as e:
        print(f"[declare_device_offline] Error updating device status: {str(e)}")
        return {"result": "error", "message": f"Error updating device status: {str(e)}"}


