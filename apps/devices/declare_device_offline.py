from core.mongodb_manager import get_mongodb_collection

def declare_device_offline(username, device_name):
    """
    Marks a specific device associated with a user as offline in the database.

    Uses centralized MongoDB connection manager to find the user by username, 
    then finds the specific device by name belonging to that user. Sets the 
    'online' field of the device document to False.

    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device to mark offline.

    Returns:
        str or dict: Returns error messages as strings ("User not found",
                     "Device not found", "Error updating device status") or a
                     dictionary indicating success along with the username.
                     Example success: {"result": "success", "username": "user1"}
    """
    print(f"[declare_device_offline] Starting - User: {username}, Device: {device_name}")

    # Get MongoDB collections using centralized manager
    try:
        user_collection = get_mongodb_collection('users')
        device_collection = get_mongodb_collection('devices')
    except Exception as e:
        print(f"[declare_device_offline] MongoDB connection error: {str(e)}")
        return "Database connection failed"

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        print(f"[declare_device_offline] User not found: {username}")
        return "User not found"

    print(f"[declare_device_offline] Found user: {user['_id']}")

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({'user_id': user['_id'], 'device_name': device_name})
    if not device:
        print(f"[declare_device_offline] Device not found: {device_name}")
        return "Device not found"

    print(f"[declare_device_offline] Found device: {device['_id']}")

    # Update the "online" field to False
    try:
        result = device_collection.update_one(
            {'_id': device['_id']},  # Find the device by its ID
            {'$set': {'online': False}}  # Update only the 'online' field
        )
        print(f"[declare_device_offline] Update result - Modified: {result.modified_count}")
    except Exception as e:
        print(f"[declare_device_offline] Error updating device status: {e}")
        return "Error updating device status"

    # Return success response
    return {
        "result": "success",
        "username": username,
    }


