from pymongo.mongo_client import MongoClient
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_file_sync(request, global_file_path=None):
    """Retrieves the file synchronization information for a user.

    Fetches all entries from the 'file_sync' collection associated with the
    given username.

    Args:
        username (str): The username of the user.
        global_file_path (str, optional): Path filter (currently unused). Defaults to None.

    Returns:
        tuple: A tuple containing:
               - dict: A dictionary with a "files" key holding a list of sync file
                       documents (ObjectIds converted to strings). If an error occurs,
                       this dictionary contains an "error" key with a message.
               - int: The HTTP status code (200 for success, 400 for missing username,
                      404 for user not found, 500 for database errors).
    """
    client = None
    try:
        if not request.username_from_token:
            return {"error": "Missing username"}, 400

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        file_sync_collection = db["file_sync"]
        user_collection = db["users"]

        # Get user_id from username
        user = user_collection.find_one({"username": request.username_from_token})
        if not user:
            return {"error": "User not found"}, 404
        
        user_id = user.get("_id")


        # Find files in file_sync collection for this user
        sync_files = list(file_sync_collection.find({"user_id": user_id}))

        
        # Remove MongoDB _id field for JSON serialization
        for file in sync_files:
            file["_id"] = str(file["_id"])
            file["user_id"] = str(file["user_id"])
            file["device_ids"] = [str(device_id) for device_id in file["device_ids"]]
            file["proposed_device_ids"] = [str(device_id) for device_id in file["proposed_device_ids"]]

            
        return {"files": sync_files}, 200

    except Exception as e:
        logger.error(f"Error in get_file_sync for user {request.username_from_token}: {str(e)}")
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
