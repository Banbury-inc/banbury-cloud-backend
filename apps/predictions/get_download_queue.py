from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime
import json
import asyncio

def get_download_queue(username, device_name):
    try:
        if not username or not device_name:
            return "Missing username or device_name"

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        file_sync_collection = db["file_sync"]
        user_collection = db["users"]
        device_collection = db["devices"]
        device_predictions_collection = db["device_predictions"]

        # Get user_id from username
        user = user_collection.find_one({"username": username})
        if not user:
            return "User not found."
        user_id = user.get("_id")

        # Get device_id from device_name
        device = device_predictions_collection.find_one({"device_name": device_name})
        if not device:
            return "Device not found."
        device_id = device.get("_id")

        # Find files that have device_id in proposed_device_ids but not in device_ids array
        sync_files = list(file_sync_collection.find({
            "user_id": user_id,
            "proposed_device_ids": device_id,
            "device_ids": {"$not": {"$in": [device_id]}}
        }))
        files_available_for_download = []
        files = []
        # Remove MongoDB _id field for JSON serialization
        for file in sync_files:
            print(f"Processing file {len(files_available_for_download) + 1} of {len(sync_files)}")
            file["_id"] = str(file["_id"])
            
            # Find online devices that have this file
            for device_id in file['device_ids']:
                device_obj = device_collection.find_one({"_id": device_id})
                if not device_obj:
                    continue
                    
                device_name = device_obj["device_name"]
                print(f"{device_name} has the file, checking if online")
                
                if device_obj.get("online"):
                    print(f"{device_name} is online, adding to download queue")
                    files_available_for_download.append(file)
                    files.append({
                        "file_name": file["file_name"],
                        "device_name": device_name
                    })
                    break  # Found an online device with the file, move to next file
                else:
                    print(f"{device_name} is offline, checking next device")

        result = {
            "files_needed": len(sync_files),
            "files_available_for_download": len(files_available_for_download), 
            "files": files
        }
            
        return result

    except Exception as e:
        return f"Error retrieving files: {str(e)}"


def main():
    # Test getting download queue for a specific device
    result = get_download_queue("mmills", "michael-ubuntu")
    # result = get_download_queue("mmills", "Michaels-MacBook-Pro-3.local")
    print(result)
if __name__ == "__main__":
    main()