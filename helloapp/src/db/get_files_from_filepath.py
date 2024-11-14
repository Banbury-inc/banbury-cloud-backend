from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
user_collection = db["users"]
device_collection = db["devices"]
file_collection = db["files"]

# Add these indexes first
file_collection.create_index([("device_id", 1)])
file_collection.create_index([("file_parent", 1)])  # Add index for file_parent

def get_files_from_filepath(username, filepath):

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))
    device_ids = [device["_id"] for device in devices]


    if filepath == None or filepath == "" or filepath == "Core" or filepath == "Core/Devices":
        files_data = []
        for device in devices:
            files_data.append({
                "file_name": "file_name",
                "file_size": "file_size", 
                "file_type": "file_type",
                "file_path": "file_path",
                "date_uploaded": "date_uploaded",
                "date_modified": "date_modified",
                "date_accessed": "date_accessed",
                "kind": "kind",
                "device_name": device["device_name"]
            })

        return {
            "result": "success",
            "files": files_data
        }

    else:

        # Find the specific device
        filepath = filepath.replace("Core/Devices/", "")
        device_name = filepath.split("/")[0]
        target_device = next((d for d in devices if d["device_name"] == device_name), None)
        
        if not target_device:
            return {
                "result": "error",
                "message": f"Device '{device_name}' not found"
            }

        # Simple query using device_id only
        query = {
            "device_id": target_device["_id"]
        }

        # If we're looking at a specific directory, use file_parent
        remaining_path = '/'.join(filepath.split("/")[1:])
        if remaining_path:
            # You might need to adjust this depending on your exact path structure
            query["file_parent"] = {"$regex": f".*{remaining_path}$"}

        files = list(file_collection.find(query).limit(100))  # Limit added for safety

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
            "result": "success",
            "files": files_data
        }
