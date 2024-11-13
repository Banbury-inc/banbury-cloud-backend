from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os

def get_files_from_filepath(username, filepath):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    file_collection = db["files"]

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))
    device_ids = [device["_id"] for device in devices]

    print(f"File path: {filepath}")

    if filepath == None:
        files_data = []
        files_data.append({
            "file_name": "file_name",
            "file_size": "file_size", 
            "file_type": "file_type",
            "file_path": "file_path",
            "date_uploaded": "date_uploaded",
            "date_modified": "date_modified",
            "date_accessed": "date_accessed",
            "kind": "kind",
            "device_name": "device_name"
        })
        return {
            "result": "success",
            "files": files_data
        }
    else:
        # Get directory path without filename
        directory_path = os.path.dirname(filepath)
        if directory_path:
            directory_path += '/'  # Add trailing slash if path exists

        # Find all files in the directory and immediate subdirectories across user's devices
        files = list(file_collection.find({
            "device_id": {"$in": device_ids},
            "file_path": {"$regex": f"^{directory_path}[^/]*(/[^/]*)?$"}  # Match files in current dir and one level deep
        }))

        # Process files and add device names
        files_data = []
        for file in files:
            # Find matching device to get device name
            device = next((d for d in devices if d["_id"] == file["device_id"]), None)
            device_name = device["device_name"] if device else "Unknown Device"
            
            files_data.append({
                "file_name": file.get("file_name"),
                "file_size": file.get("file_size"), 
                "file_type": file.get("file_type"),
                "file_path": file.get("file_path"),
                "date_uploaded": file.get("date_uploaded"),
                "date_modified": file.get("date_modified"),
                "date_accessed": file.get("date_accessed"),
                "kind": file.get("kind"),
                "device_name": device_name
            })

        return {
            "files": files_data
        }
