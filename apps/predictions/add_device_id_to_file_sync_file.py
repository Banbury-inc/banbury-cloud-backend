from pymongo.mongo_client import MongoClient

def add_device_id_to_file_sync_file(username, file_name, device_name):
    """Adds a device ID to the device_ids array of a specific file sync entry.

    Args:
        username (str): The username of the user.
        file_name (str): The name of the file sync entry to update.
        device_name (str): The name of the device whose ID should be added.

    Returns:
        dict: A dictionary indicating the success or failure of the operation,
              including details like username, file_name, and modified count,
              or an error message.
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client['NeuraNet']
        user_collection = db['users']
        device_collection = db['devices']
        file_sync_collection = db['file_sync']

        # Find the user by username
        user = user_collection.find_one({'username': username})
        if not user:
            return {"error": "User not found"}

        device_id = device_collection.find_one({'device_name': device_name}, {'_id': 1})
        if not device_id:
            return {"error": "Device not found"}

        # Update the device_ids array for the specific file sync entry
        try:
            result = file_sync_collection.update_one(
                {
                    'user_id': user['_id'],
                    'file_name': file_name
                },
                {'$addToSet': {'device_ids': device_id['_id']}}
            )


            return {
                "result": "success",
                "username": username,
                "file_name": file_name,
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
    result = add_device_id_to_file_sync_file(
        username="mmills",
        # device_name="michael-mills-ubuntu",
        device_name="Michaels-MacBook-Pro-3.local",
        file_name="windowsxp.jpeg",
        
    )
    print(result)

if __name__ == "__main__":
    main()


