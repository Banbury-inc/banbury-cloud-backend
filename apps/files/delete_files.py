from pymongo import MongoClient

def delete_files(username, device_name, files):
    """
    Deletes specified files associated with a device belonging to a user.

    Args:
        username (str): The username of the user (used indirectly).
        device_name (str): The name of the device from which files will be deleted.
        files (list): A list of dictionaries, each containing at least a 'file_name'.

    Returns:
        str: A status string indicating the outcome:
             "device_not_found": If the specified device doesn't exist.
             "invalid_files": If the 'files' argument is not a list.
             "no_files_to_delete": If the 'files' list is empty or lacks 'file_name'.
             "no_files_deleted": If no matching files were found to delete.
             "success": If the deletion operation was initiated successfully.
    """
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    file_collection = db['files']
    device_collection = db['devices']

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        return "device_not_found"

    device_id = device.get('_id')  # Get the ObjectId for the device

    # Ensure files is a list, in case it's passed incorrectly
    if not isinstance(files, list):
        return "invalid_files"

    # Prepare the list of file names to be deleted
    file_names = [file_data.get('file_name') for file_data in files if 'file_name' in file_data]

    if not file_names:
        return "no_files_to_delete"

    # Delete files that match both the file names and device_id
    delete_result = file_collection.delete_many({
        "device_id": device_id,
        "file_name": {"$in": file_names}
    })

    # Check if files were deleted
    if delete_result.deleted_count == 0:
        return "no_files_deleted"

    return "success"

