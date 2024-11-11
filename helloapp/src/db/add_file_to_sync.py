from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime

def add_file_to_sync(username, device_name, files):
    try:
        if not files or not device_name:
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

    # Prepare lists for both collections
    new_files = []
    sync_files = []
    
    for file_data in files:
        if not isinstance(file_data, dict):
            return f"Invalid file data format: {file_data}"

        required_fields = ["file_name", "file_path"]
        missing_fields = [
            field for field in required_fields if not file_data.get(field)
        ]
        if missing_fields:
            return f"Missing fields: {missing_fields}"

        # Prepare new file data for the files collection
        new_file = {
            "device_id": device_id,
            "file_type": file_data.get("file_type"),
            "file_name": file_data.get("file_name"),
            "file_path": file_data.get("file_path"),
            "file_size": file_data.get("file_size"),
            "date_uploaded": file_data.get("date_uploaded"),
            "date_modified": file_data.get("date_modified"),
            "file_parent": file_data.get("file_parent"),
            "original_device": file_data.get("original_device"),
            "kind": file_data.get("kind"),
        }
        new_files.append(new_file)

        # Prepare sync file data for the file_sync collection
        # Check if file already exists in file_sync collection
        existing_sync = file_sync_collection.find_one({
            "file_name": file_data.get("file_name")
        })

        if existing_sync:
            # Update existing sync record
            if device_id not in existing_sync.get("device_ids", []):
                file_sync_collection.update_one(
                    {"file_name": file_data.get("file_name")},
                    {
                        "$set": {
                            "file_size": file_data.get("file_size"),
                            "file_priority": file_data.get("file_priority", 1),
                            "user_id": user_id
                        },
                        "$addToSet": {"device_ids": device_id}
                    }
                )
        else:
            # Create new sync record with user_id
            sync_file = {
                "device_ids": [device_id],
                "user_id": user_id,
                "file_name": file_data.get("file_name"),
                "file_size": file_data.get("file_size"),
                "file_priority": file_data.get("file_priority", 1),
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
    test_data = [
        {"file_name": "test_file.txt", "file_path": "/home/michael/test_file.txt", "file_type": "text", "file_size": 1024, "date_uploaded": datetime.now().isoformat(), "date_modified": datetime.now().isoformat(), "file_parent": "michael-ubuntu", "original_device": "michael-ubuntu", "kind": "file"}
    ]
    result = add_file_to_sync("mmills", "michael-ubuntu", test_data)
    print(result)

if __name__ == "__main__":
    main()