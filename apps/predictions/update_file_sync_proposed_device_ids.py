from pymongo.mongo_client import MongoClient
from bson import ObjectId

def update_file_sync_proposed_device_ids(username, file_id, proposed_device_ids):
    """Updates the list of proposed device IDs for a specific file sync entry.

    Finds the file sync entry by user ID and file ID and sets the
    'proposed_device_ids' field to the provided list.

    Args:
        username (str): The username of the user.
        file_id (str): The string representation of the ObjectId of the file sync entry.
        proposed_device_ids (list): A list of device ObjectIds (or strings to be
                                    interpreted as such by the allocation service)
                                    proposed to hold this file.

    Returns:
        dict: A dictionary indicating success (with username, file_id, modified_count)
              or failure (with an error message).
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        user_collection = db['users']
        file_sync_collection = db['file_sync']

        if not username:
            return {"error": "Username not provided"}
        if not file_id:
            return {"error": "File ID not provided"}
        if not proposed_device_ids:
            return {"error": "Proposed device IDs not provided"}

        # Find the user by username
        user = user_collection.find_one({'username': username})
        if not user:
            return {"error": "User not found"}

        print(f"Updating file sync proposed device IDs for user {username} and file ID {file_id}")


        # Update the proposed_device_ids for the specific file sync entry
        try:
            result = file_sync_collection.update_one(
                {
                    'user_id': user['_id'],
                    '_id': ObjectId(file_id)
                },
                {'$set': {'proposed_device_ids': proposed_device_ids}}
            )

            return {
                "result": "success",
                "username": username,
                "file_id": file_id,
                "modified_count": result.modified_count
            }

        except Exception as e:
            print(f"Error updating file sync proposed device IDs: {e}")
            return {"error": f"Error updating file sync: {str(e)}"}

    except Exception as e:
        print(f"Error connecting to database: {e}")
        return {"error": f"Database connection error: {str(e)}"}

def main():
    # Example proposed device IDs array
    proposed_device_ids = ["device_id_1", "device_id_2", "device_id_3"]
    result = update_file_sync_proposed_device_ids(
        username="mmills",
        file_id="67560b9076ebec5a4ac8ce31",
        proposed_device_ids=proposed_device_ids
    )
    print(result)

if __name__ == "__main__":
    main()


