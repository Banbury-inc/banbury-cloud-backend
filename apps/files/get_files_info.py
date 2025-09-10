from core.mongodb_manager import get_mongodb_collection

def get_files_info(username):
    """
    Retrieves information for all files associated with all devices belonging to a user.

    Args:
        username (str): The username of the user whose files are being queried.

    Returns:
        dict: A dictionary containing:
              - "files": A list of dictionaries, each representing a file with its details
                         (name, size, type, path, dates, kind, device_name).
              - "error": An error message string if the user is not found.
    """
    # Get MongoDB collections using centralized manager
    try:
        user_collection = get_mongodb_collection('users')
        device_collection = get_mongodb_collection('devices')
        file_collection = get_mongodb_collection('files')
    except Exception as e:
        print(f"[get_files_info] MongoDB connection error: {str(e)}")
        return {"error": "Database connection failed"}

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))

    # Prepare file data for response
    all_files_data = []
    for device in devices:
        # Find all files for the current device
        files = list(file_collection.find({"device_id": device["_id"]}))

        # Process each file and append to the list
        for file in files:
            all_files_data.append({
                "file_name": file.get("file_name"),
                "file_size": file.get("file_size"),
                "file_type": file.get("file_type"),
                "file_path": file.get("file_path"),
                "date_uploaded": file.get("date_uploaded"),
                "date_modified": file.get("date_modified"),
                "date_accessed": file.get("date_accessed"),
                "kind": file.get("kind"),
                "device_name": device.get(
                    "device_name"
                ),  # Include device name for context
            })

    files_data = {
        "files": all_files_data,
    }

    return files_data
