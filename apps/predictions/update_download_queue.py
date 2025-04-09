from pymongo.mongo_client import MongoClient

def update_download_queue(username, device_name, files_needed, files_available_for_download):
    """Updates the download queue status for a specific device.

    Finds the device prediction document by device name and updates the
    'files_needed' and 'files_available_for_download' fields using upsert.

    Args:
        username (str): The username of the user.
        device_name (str): The name of the device whose queue status is being updated.
        files_needed (int): The number of files needed by the device.
        files_available_for_download (int): The number of needed files that are
                                            currently available from online peers.

    Returns:
        dict or str: A success dictionary containing result, username, and device name
                     if successful. An error message string if the user or device is
                     not found, or if a database update error occurs.
    """

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']
    device_predictions_collection = db['device_predictions']


    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = f"User not found {username}"
        return response


    # Find the device belonging to the user by device_name
    device = device_predictions_collection.find_one({'device_name': device_name})
    if not device:
        response = f"Device not found. {device_name}"
        return response

    # Update the "files_needed" and "files_available_for_download" fields
    try:
        device_predictions_collection.update_one(
            {'_id': device['_id']},  # Find the device by its ID
            {'$set': {'files_needed': files_needed, 'files_available_for_download': files_available_for_download}}  # Update the download queue fields
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        response = f"Error updating device status. {device_name}"
        return response


    # Update the "files_needed" and "files_available_for_download" fields in the device_predictions collection
    try:
        result = device_predictions_collection.update_one(
            {'_id': device['_id']},  # Find the device by its ID
            {'$set': {
                'files_needed': files_needed,
                'files_available_for_download': files_available_for_download
            }},  # Update the download queue fields
            upsert=True  # Create the document if it doesn't exist
        )
        if result.matched_count == 0:
            print(f"No document found in device_predictions collection for device_id: {device['_id']}, created new document.")
    except Exception as e:
        print(f"Error updating device predictions: {e}")
        response = f"Error updating device predictions. {device_name}"
        return response

    return {
        "result": "success",
        "username": username,
        "device_name": device_name,
    }

def main():
    result = update_download_queue("mmills", "Michaels-MacBook-Pro-3.local", [], [])
    print(result)

if __name__ == "__main__":
    main()  


