from pymongo import MongoClient

 
def search_for_file(username, file_name):
    """
    Searches for a specific file by name across all devices belonging to a user.

    Iterates through the user's devices and checks the file collection for a match
    based on device_id and file_name.

    Args:
        username (str): The username of the user whose devices will be searched.
        file_name (str): The exact name of the file to search for.

    Returns:
        dict or str: If the file is found, returns a dictionary containing file details
                     and the name of the device it was found on.
                     If the user is not found, returns the string "User not found".
                     If the user has no devices, returns "No devices found for this user."
                     If the file is not found on any device, returns {"result": "File not found"}.
    """
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
        file = file_collection.find_one(
            {'device_id': device['_id'], 'file_name': file_name})

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
                "device_id": str(file.get('device_id')),
                "kind": file.get('kind'),
                # Include device name for context
                "device_name": device.get('device_name'),
            }
            return file_data

    return {"result": "File not found"}
