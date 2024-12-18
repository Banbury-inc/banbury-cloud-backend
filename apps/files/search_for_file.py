from pymongo import MongoClient

def search_for_file(username, file_name):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']
    file_collection = db['files']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    
    if not user:
        return "User not found"

    # Find all devices belonging to the user
    devices = list(device_collection.find({'user_id': user['_id']}))

    if not devices:
        return "No devices found for this user."

    # Search for the file in all of the user's devices
    for device in devices:
        # Search for the file in the current device
        file = file_collection.find_one({'device_id': device['_id'], 'file_name': file_name})

        if file:
            # If the file is found, return the device and file details
            file_data = {
                "file_name": file.get('file_name'),
                "file_size": file.get('file_size'),
                "file_type": file.get('file_type'),
                "file_path": file.get('file_path'),
                "date_uploaded": file.get('date_uploaded'),
                "date_modified": file.get('date_modified'),
                "date_accessed": file.get('date_accessed'),
                "kind": file.get('kind'),
                "device_name": device.get('device_name'),  # Include device name for context
            }
            return {"result": "File found", "file_data": file_data}

    return {"result": "File not found"}
