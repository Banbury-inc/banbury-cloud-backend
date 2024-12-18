from pymongo.mongo_client import MongoClient

def declare_device_offline(username, device_name):

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


