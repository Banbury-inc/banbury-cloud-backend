from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime

def get_file_sync(username):
    try:
        if not username:
            return "Missing username"

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

        # Find all files in file_sync collection for this user
        sync_files = list(file_sync_collection.find({"user_id": user_id}))
        
        # Remove MongoDB _id field for JSON serialization
        for file in sync_files:
            file["_id"] = str(file["_id"])
            
        return sync_files

    except Exception as e:
        return f"Error retrieving files: {str(e)}"


def main():
    test_data = [
        {"file_name": "test_file.txt", "file_path": "/home/michael/test_file.txt", "file_type": "text", "file_size": 1024, "date_uploaded": datetime.now().isoformat(), "date_modified": datetime.now().isoformat(), "file_parent": "michael-ubuntu", "original_device": "michael-ubuntu", "kind": "file"}
    ]
    result = get_file_sync("mmills")
    print(result)

if __name__ == "__main__":
    main()