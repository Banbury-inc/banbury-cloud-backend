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

    print("filepath")
    print(filepath)

    if filepath == None or filepath == "" or filepath == "Core" or filepath == "Core/Devices":
        print("filepath is none or core or devices")
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

        # take filepath and remove Core/Devices from the front
        filepath = filepath.replace("Core/Devices/","")

        print("true filepath")
        print(filepath)

        # Take the value until the next / and set it as the device name
        device_name = filepath.split("/")[0]
        print("device_name")
        print(device_name)

        # Get the remaining path after device name
        remaining_path = '/'.join(filepath.split("/")[1:])
        directory_path = remaining_path + '/' if remaining_path else ""

        print("directory_path")
        print(directory_path)

        # If directory_path is empty, find all files for the specific device
        if directory_path == "":
            # First find the specific device by device_name
            target_device = next((d for d in devices if d["device_name"] == device_name), None)
            print("target_device")
            print(target_device.get("device_name"))
            if not target_device:
                return {
                    "result": "error",
                    "message": f"Device '{device_name}' not found"
                }
            
            # Start with first level search
            files = list(file_collection.find({
                "device_id": target_device.get("_id"),
                "file_path": {"$regex": "^[^/]+(/[^/]+)?$"}  # Match first level dirs and their immediate children
            }))

            # If no files found, progressively search deeper until files are found
            depth = 2
            while not files and depth <= 10:  # Limit depth to avoid infinite loops
                regex_pattern = "^" + ("/[^/]+" * depth) + "(/[^/]+)?$"
                files = list(file_collection.find({
                    "device_id": target_device.get("_id"),
                    "file_path": {"$regex": regex_pattern}
                }))
                depth += 1

        else:

            # add a / in front of directory_path if it doesn't have one
            if not directory_path.startswith('/'):
                directory_path = '/' + directory_path

            # Modified query to get all nested directories
            files = list(file_collection.find({
                    "device_id": {"$in": device_ids},
                    "file_path": {"$regex": f"^{directory_path}.*"}  # Match all files under this directory path
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
            "result": "success",
            "files": files_data
        }
