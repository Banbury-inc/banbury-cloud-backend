from pymongo.mongo_client import MongoClient

def declare_device_online(username, device_name):
    print(f"[declare_device_online] Starting - User: {username}, Device: {device_name}")

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    try:
        client = MongoClient(uri)
        db = client['NeuraNet']
        user_collection = db['users']
        device_collection = db['devices']
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
            {'$set': {'online': True}}
        )
        print(f"[declare_device_online] Update result - Modified: {result.modified_count}")
        
        if result.modified_count > 0:
            return {
                "result": "success",
                "username": username,
                "modified_count": result.modified_count
            }
        else:
            return {
                "result": "error",
                "message": "Update operation did not modify any documents",
                "modified_count": result.modified_count
            }
            
    except Exception as e:
        print(f"[declare_device_online] Error updating device status: {str(e)}")
        return {"result": "error", "message": f"Error updating device status: {str(e)}"}


