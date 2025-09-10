from core.mongodb_manager import get_mongodb_collection

def declare_device_online(username, device_name):
    """
    Marks a specific device associated with a user as online in the database.

    Uses centralized MongoDB connection manager to find the user by username, 
    then finds the specific device by name belonging to that user. Sets the 
    'online' field of the device document to True. Uses upsert=True for the 
    update operation.

    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device to mark online.

    Returns:
        dict: A dictionary indicating success or error, along with a message.
              On success, includes username and the string representation of
              the device_id.
              Example success: {"result": "success", "username": "user1", "device_id": "..."}
              Example error: {"result": "error", "message": "User not found"}
    """
    print(f"[declare_device_online] Starting - User: {username}, Device: {device_name}")

    # Get MongoDB collections using centralized manager
    try:
        user_collection = get_mongodb_collection('users')
        device_collection = get_mongodb_collection('devices')
    except Exception as e:
        print(f"[declare_device_online] MongoDB connection error: {str(e)}")
        return {"result": "error", "message": "Database connection failed"}

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        print(f"[declare_device_online] User not found: {username}")
        return {"result": "error", "message": "User not found"}

    print(f"[declare_device_online] Found user: {user['_id']}")

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({'user_id': user['_id'], 'device_name': device_name})
    if not device:
        print(f"[declare_device_online] Device not found: {device_name}")
        return {"result": "error", "message": "Device not found"}

    print(f"[declare_device_online] Found device: {device['_id']}")

    # Update the "online" field to True
    try:
        result = device_collection.update_one(
            {'_id': device['_id']},
            {'$set': {'online': True}},
            upsert=True  # Create new document if not found
        )
        print(f"[declare_device_online] Update result - Modified: {result.modified_count}")
        
        return {
            "result": "success",
            "username": username,
            "device_id": str(device['_id'])
        }
            
    except Exception as e:
        print(f"[declare_device_online] Error updating device status: {str(e)}")
        return {"result": "error", "message": f"Error updating device status: {str(e)}"}


