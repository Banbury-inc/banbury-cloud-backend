from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime

def get_download_queue(username, device_id):
    try:
        if not username or not device_id:
            return "Missing username or device_id"

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        file_sync_collection = db["file_sync"]
        user_collection = db["users"]

        # Get user_id from username
        user = user_collection.find_one({"username": username})
        if not user:
            return "User not found."
        user_id = user.get("_id")

        # Find files that have device_id in proposed_device_ids but not in device_ids array
        sync_files = list(file_sync_collection.find({
            "user_id": user_id,
            "proposed_device_ids": device_id,
            "device_ids": {"$not": {"$in": [device_id]}}
        }))
        
        # Remove MongoDB _id field for JSON serialization
        for file in sync_files:
            file["_id"] = str(file["_id"])
            
        return sync_files

    except Exception as e:
        return f"Error retrieving files: {str(e)}"


def main():
    # Test getting download queue for a specific device
    result = get_download_queue("mmills", "michael-ubuntu")
    print(result)
    result = get_download_queue("mmills", "Michaels-MacBook-Pro-3.local")
    print(result)

if __name__ == "__main__":
    main()