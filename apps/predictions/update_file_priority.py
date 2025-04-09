from pymongo.mongo_client import MongoClient
from bson import ObjectId

def update_file_priority(username, file_id, priority):
    """Updates the priority of a specific file in the file sync list.

    Finds the file sync entry by user ID and file ID and sets the 'file_priority' field.

    Args:
        username (str): The username of the user.
        file_id (str): The string representation of the ObjectId of the file sync entry.
        priority (int): The new priority value for the file (e.g., 1, 2, 3).

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

        # Find the user by username
        user = user_collection.find_one({'username': username})
        if not user:
            return {"error": "User not found"}

        # Update the proposed_device_ids for the specific file sync entry
        try:
            result = file_sync_collection.update_one(
                {
                    'user_id': user['_id'],
                    '_id': ObjectId(file_id)
                },
                {'$set': {'file_priority': priority}}
            )

            if result.modified_count == 0:
                return {
                    "error": "File sync entry not found or no changes made",
                    "username": username,
                    "file_id": file_id
                }

            return {
                "result": "success",
                "username": username,
                "file_id": file_id,
                "modified_count": result.modified_count
            }

        except Exception as e:
            print(f"Error updating file sync priority: {e}")
            return {"error": f"Error updating file sync: {str(e)}"}

    except Exception as e:
        print(f"Error connecting to database: {e}")
        return {"error": f"Database connection error: {str(e)}"}

def main():
    # Example proposed device IDs array
    priority = 1
    result = update_file_priority(
        username="mmills",
        file_id="your_file_id_here",
        priority=priority
    )
    print(result)

if __name__ == "__main__":
    main()


