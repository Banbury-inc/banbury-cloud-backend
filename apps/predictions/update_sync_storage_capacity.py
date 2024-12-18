from pymongo.mongo_client import MongoClient

def update_sync_storage_capacity(username, device_name, sync_storage_capacity_gb):

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']
    device_predictions_collection = db['device_predictions']


    sync_storage_capacity_gb = int(sync_storage_capacity_gb)

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = f"User not found {username}"
        return response


    # Find the device belonging to the user by device_name
    device = device_collection.find_one({'user_id': user['_id'], 'device_name': device_name})
    if not device:
        response = "Device not found"
        return response

    # Update the "sync_storage_capacity_gb" field
    try:
        device_collection.update_one(
            {'_id': device['_id']},  # Find the device by its ID
            {'$set': {'sync_storage_capacity_gb': sync_storage_capacity_gb}}  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        response = "Error updating device status"
        return response


    # Update the "sync_storage_capacity_gb" field in the device_predictions collection
    try:
        result = device_predictions_collection.update_one(
            {'device_id': device['_id']},  # Find the device by its ID
            {'$set': {'sync_storage_capacity_gb': sync_storage_capacity_gb}},  # Update only the 'sync_storage_capacity_gb' field
            upsert=True  # Create the document if it doesn't exist
        )
        if result.matched_count == 0:
            print(f"No document found in device_predictions collection for device_id: {device['_id']}, created new document.")
    except Exception as e:
        print(f"Error updating device predictions: {e}")
        response = "Error updating device predictions"
        return response

    return {
        "result": "success",
        "username": username,
    }

def main():
    result = update_sync_storage_capacity("mmills", "Michaels-MacBook-Pro-3.local", 60)
    print(result)

if __name__ == "__main__":
    main()  


