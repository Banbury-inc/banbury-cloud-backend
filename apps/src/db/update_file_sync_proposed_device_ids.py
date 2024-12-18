from pymongo.mongo_client import MongoClient
from bson import ObjectId

def update_file_sync_proposed_device_ids(username, file_id, proposed_device_ids):
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
                {'$set': {'proposed_device_ids': proposed_device_ids}}
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
        file_id="your_file_id_here",
        proposed_device_ids=proposed_device_ids
    )
    print(result)

if __name__ == "__main__":
    main()


