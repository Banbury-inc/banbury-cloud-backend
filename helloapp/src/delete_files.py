from pymongo import MongoClient

def delete_files(username, device_name, files):
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    file_collection = db['files']
    device_collection = db['devices']

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        return "device_not_found"

    device_id = device.get('_id')  # Get the ObjectId for the device

    # Ensure files is a list, in case it's passed incorrectly
    if not isinstance(files, list):
        return "invalid_files"

    # Delete existing files that match the criteria
    for file_data in files:
        file_criteria = {
            "file_name": file_data.get('file_name'),
        }
        
        file_collection.delete_many(file_criteria)

    return "success"
