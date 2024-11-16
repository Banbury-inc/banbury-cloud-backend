from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime

def add_file_to_sync(username, device_name, file_name):
    try:
        if not file_name or not device_name:
            return "Missing files or device_name"

    except Exception as e:
        return f"Invalid data: {str(e)}"

    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_collection = db["files"]
    file_sync_collection = db["file_sync"]
    device_collection = db["devices"]
    user_collection = db["users"]

    # Get user_id from username
    user = user_collection.find_one({"username": username})
    if not user:
        return "User not found."
    user_id = user.get("_id")

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        return "Device not found."

    device_id = device.get("_id")
    if not device_id:
        return "Device ID not found."

    file_document = file_collection.find_one({"file_name": file_name})
    if not file_document:
        return "File not found."    

    # Convert ObjectId to string for JSON serialization
    file_document['_id'] = str(file_document['_id'])

    # Prepare lists for both collections
    new_files = []
    sync_files = []


    # Prepare new file data for the files collection
    new_file = {
        "device_id": device_id,
        "file_type": file_document.get("file_type"),
        "file_name": file_document.get("file_name"),
        "file_path": file_document.get("file_path"),
        "file_size": file_document.get("file_size"),
        "date_uploaded": file_document.get("date_uploaded"),
        "date_modified": file_document.get("date_modified"),
        "file_parent": file_document.get("file_parent"),
        "original_device": file_document.get("original_device"),
        "kind": file_document.get("kind"),
    }
    new_files.append(new_file)

    # Prepare sync file data for the file_sync collection
    # Check if file already exists in file_sync collection
    existing_sync = file_sync_collection.find_one({
        "file_name": file_document.get("file_name")
    })

    if existing_sync:
        # Update existing sync record
        if device_id not in existing_sync.get("device_ids", []):
            file_sync_collection.update_one(
                {"file_name": file_document.get("file_name")},
                {
                    "$set": {
                        "file_size": file_document.get("file_size"),
                        "file_priority": file_document.get("file_priority", 1),
                        "user_id": user_id
                    },
                    "$addToSet": {"device_ids": device_id}
                }
            )
    else:
        # Create new sync record with user_id
        sync_file = {
            "device_ids": [device_id],
            "proposed_device_ids": [device_id],
            "user_id": user_id,
            "file_name": file_document.get("file_name"),
            "file_size": file_document.get("file_size"),
            "file_priority": file_document.get("file_priority", 1),
        }
        sync_files.append(sync_file)

    # Insert all new files in one go
    try:
        if new_files:
            file_collection.insert_many(new_files)
        if sync_files:
            file_sync_collection.insert_many(sync_files)
    except Exception as e:
        print(f"Error inserting files: {e}")
        return f"Error inserting files: {str(e)}"

    return "success"


def main():


    result = add_file_to_sync("mmills", "michael-ubuntu", "/home/mmills/BCloud/374-656-726_96j8_382.jpg")
    print(result)

if __name__ == "__main__":
    main()