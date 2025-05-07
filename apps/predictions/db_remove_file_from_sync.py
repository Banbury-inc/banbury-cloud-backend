from pymongo.mongo_client import MongoClient

def db_remove_file_from_sync(device_name, file_name):
    """Removes a file from the file synchronization list.

    Deletes the corresponding entry from the 'file_sync' collection based on
    the file name.

    Args:
        username (str): The username (currently unused but kept for consistency).
        device_name (str): The device name (currently unused but kept for consistency).
        file_name (str): The name of the file to remove from the sync list.

    Returns:
        str: "success" if the deletion is successful, "File not found in sync collection"
             if the file wasn't found, or an error message string for invalid data.
    """
    try:
        if not file_name or not device_name:
            return "Missing files or device_name"

    except Exception as e:
        return f"Invalid data: {str(e)}"

    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_sync_collection = db["file_sync"]

    # Delete the file sync record
    result = file_sync_collection.delete_one({"file_name": file_name})

    if result.deleted_count == 0:
        return "File not found in sync collection"

    return "success"


def main():


    result = db_remove_file_from_sync("mmills", "michael-mills-ubuntu", "11-0-Night.jpg")
    print(result)

if __name__ == "__main__":
    main()
