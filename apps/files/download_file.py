from core.mongodb_manager import get_mongodb_collection

# Get MongoDB collections using centralized manager
file_collection = get_mongodb_collection('files')
file_sync_collection = get_mongodb_collection('file_sync')
device_collection = get_mongodb_collection('devices')

def download_file(file_id, is_file_sync):
    """
    Retrieves file information for download, potentially triggering a download request.

    Handles two cases based on 'is_file_sync':
    1. If True: Looks for the file in the 'file_sync' collection.
    2. If False: Looks for the file in the 'files' collection, verifies the associated device
       and user, checks if the device is online, and (placeholder) sends a download request.


    Args:
        username (str): The username of the user requesting the download (used for verification).
        file_id (str): The unique identifier of the file to be downloaded.
        is_file_sync (bool): Flag indicating whether the file is from the file_sync collection.

    Returns:
        str: A status string indicating the outcome:
             "file_not_found": If the file ID doesn't exist in the relevant collection.
             "device_not_found": If the device associated with the file doesn't exist.
             "user_not_found": If the user associated with the device doesn't exist.
             "device_not_online": If the device holding the file is not online.
             "success": If the file information is found (and potentially download initiated).
             Note: The actual file download mechanism is not fully implemented.
    """

    if is_file_sync:
        file = file_sync_collection.find_one({"file_id": file_id})
        if not file:
            return "file_not_found"
    else:
        file = file_collection.find_one({"file_id": file_id})
        if not file:
            return "file_not_found"
        # find the device_id from the file
        device_id = file.get("device_id")
        device_with_file = device_collection.find_one({"device_id": device_id})
        if not device_with_file:
            return "device_not_found"

        # find the user associate with the device
        user_id = device_with_file.get("user_id")
        if not user_id:
            return "user_not_found"

        # check to see if the device with file is online
        device_status = device_with_file.get("online")
        if device_status != True:
            return "device_not_online"

        else:
            # send a request via websocket to the device to download the file
            pass



        return "success"

