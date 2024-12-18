from pymongo import MongoClient

def update_files(username, device_name, files):
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    file_collection = db['files']
    device_collection = db['devices']

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        response = "device_not_found"
        return response

    try:
        device_id = device['_id']  # Get the ObjectId for the device
    except KeyError:
        response = "device_id_not_found"
        return response

    # Update existing files that match the criteria
    for file_data in files:
        file_criteria = {
            "device_id": device_id,
            "file_name": file_data.get('file_name'),
            "file_type": file_data.get('file_type'),
        }

        # Define the new information to update
        updated_file = {
            "$set": {
                "file_path": file_data.get('file_path'),
                "date_uploaded": file_data.get('date_uploaded'),
                "date_modified": file_data.get('date_modified'),
                "file_size": file_data.get('file_size'),
                "file_priority": file_data.get('file_priority'),
                "file_parent": file_data.get('file_parent'),
                "original_device": file_data.get('original_device'),
                "kind": file_data.get('kind')
            }
        }

        # Update the document that matches the criteria
        file_collection.update_one(file_criteria, updated_file, upsert=True)

    response = "success"
    return response

