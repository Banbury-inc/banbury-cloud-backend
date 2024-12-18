from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_file_sync(username, global_file_path=None):
    client = None
    try:
        if not username:
            return {"error": "Missing username"}, 400

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        file_sync_collection = db["file_sync"]
        user_collection = db["users"]

        # Get user_id from username
        user = user_collection.find_one({"username": username})
        if not user:
            return {"error": "User not found"}, 404
        
        user_id = user.get("_id")


        # Find files in file_sync collection for this user
        sync_files = list(file_sync_collection.find({"user_id": user_id}))

        print(sync_files)
        
        # Remove MongoDB _id field for JSON serialization
        for file in sync_files:
            file["_id"] = str(file["_id"])
            file["user_id"] = str(file["user_id"])
            file["device_ids"] = [str(device_id) for device_id in file["device_ids"]]
            file["proposed_device_ids"] = [str(device_id) for device_id in file["proposed_device_ids"]]

            
        return {"files": sync_files}, 200

    except Exception as e:
        logger.error(f"Error in get_file_sync for user {username}: {str(e)}")
        return {"error": f"Error retrieving files: {str(e)}"}, 500
        
    finally:
        if client:
            client.close()


def main():
    test_data = [
        {"file_name": "test_file.txt", "file_path": "/home/michael/test_file.txt", "file_type": "text", "file_size": 1024, "date_uploaded": datetime.now().isoformat(), "date_modified": datetime.now().isoformat(), "file_parent": "michael-ubuntu", "original_device": "michael-ubuntu", "kind": "file"}
    ]
    result = get_file_sync("mmills")
    print(result)

if __name__ == "__main__":
    main()