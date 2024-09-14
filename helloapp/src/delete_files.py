
from pymongo.mongo_client import MongoClient

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
        response = "device_not_found"
        return response

    try:
        device_id = device['_id']  # Get the ObjectId for the device
    except KeyError:
        response = "device_id_not_found"
        return response

    # Delete existing files that match the criteria
    for file_data in files:
        file_criteria = {
            "device_id": device_id,
            "file_name": file_data.get('file_name'),
            "file_type": file_data.get('file_type'),
        }
        file_collection.delete_many(file_criteria)


    response = "success"
    return response



