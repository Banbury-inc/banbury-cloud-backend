from pymongo.mongo_client import MongoClient

def declare_device_offline(username, device_name):
    """
    Marks a specific device associated with a user as offline in the database.

    Connects to MongoDB, finds the user by username, then finds the specific
    device by name belonging to that user. Sets the 'online' field of the
    device document to False.

    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device to mark offline.

    Returns:
        str or dict: Returns error messages as strings ("User not found",
                     "Device not found", "Error updating device status") or a
                     dictionary indicating success along with the username.
                     Example success: {"result": "success", "username": "user1"}
    """

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response


    # Find the device belonging to the user by device_name
    device = device_collection.find_one({'user_id': user['_id'], 'device_name': device_name})
    if not device:
        response = "Device not found"
        return response

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {'_id': device['_id']},  # Find the device by its ID
            {'$set': {'online': False}}  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        response = "Error updating device status"
        return response

    # Return success response
    response = {
        "result": "success",
        "username": username
    }

    return response


