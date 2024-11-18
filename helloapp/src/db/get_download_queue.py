from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime

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

        downloaded_files = []
        # Remove MongoDB _id field for JSON serialization
        for file in sync_files:
            print("Processing file " + str(len(downloaded_files) + 1) + " of " + str(len(sync_files)))
            file["_id"] = str(file["_id"])
            updated_device_ids = []
            for device_id in file['device_ids']:
                device_obj = device_collection.find_one({"_id": device_id})
                if device_obj:
                    device_name = device_obj["device_name"]
                    print(device_name + " has the file, looking to see if online")
                    device = device_collection.find_one({"device_name": device_name})
                    if device["online"] == True:
                        print(device_name + " is online, adding to download queue")
                        '''
                        TODO: Download the file
                        '''
                        download_success = True

                        if download_success == True:
                            downloaded_files.append(file)
                    else:
                        print(device_name + " is offline, skipping. Looking for next device that has the file.")
                    updated_device_ids.append({"device_id": device_id, "device_name": device_name})
                else:
                    updated_device_ids.append({"device_id": device_id, "device_name": "Unknown"})
            file['device_ids'] = updated_device_ids

        result = {
            "files needed": len(sync_files),
            "files downloaded": len(downloaded_files),
            "files": downloaded_files
            }
            
        return result

    except Exception as e:
        return f"Error retrieving files: {str(e)}"


def main():
    # Test getting download queue for a specific device
    # result = get_download_queue("mmills", "michael-ubuntu")
    result = get_download_queue("mmills", "Michaels-MacBook-Pro-3.local")
if __name__ == "__main__":
    main()