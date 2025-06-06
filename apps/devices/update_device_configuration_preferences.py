from pymongo.mongo_client import MongoClient
from datetime import datetime

def update_device_configuration_preferences(username, device_id, device_configurations):
    """
    Updates or creates the prediction configuration preferences for a specific device.

    Connects to MongoDB, finds the user and device, then updates or inserts
    a document in the 'device_predictions' collection with the provided
    configuration settings. Uses upsert=True.

    Initializes boolean configuration fields to False if the document is created.

    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device.
        device_configurations (dict): A dictionary containing the configuration
                                      key-value pairs to update (e.g.,
                                      {"use_predicted_cpu_usage": True}).

    Returns:
        str: "success" if the update/insert was successful.
             "user not found" if the user doesn't exist.
             "device not found: [device_name]" if the device doesn't exist.
             "error" if an exception occurred during the database operation.
    """

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    predictions_collection = db["device_predictions"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return "user not found"

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "_id": device_id,
    })
    if not device:
        return f"device not found: {device_id}"

    # First check if a prediction document exists
    existing_config = predictions_collection.find_one({
        "user_id": user["_id"],
        "device_id": device["_id"]
    })

    # Prepare the update data with only the new configuration fields
    configuration_data = {
        "updated_at": datetime.utcnow(),
    }
    
    # Add the new fields
    fields = {
        'use_device_in_file_sync': True,
        'use_predicted_upload_speed': True,
        'use_predicted_download_speed': True,
        'use_predicted_gpu_usage': True,
        'use_predicted_cpu_usage': True,
        'use_predicted_ram_usage': True,
        'use_files_needed': True,
        'use_files_available_for_download': True,
        'files_needed': [],
        'files_available_for_download': [],
        'sync_storage_capacity_gb': 100,
        'score': 100,
    }
    
    # If document doesn't exist, include all boolean fields with defaults
    if not existing_config:
        configuration_data.update(fields)
    
    # Update with any provided configurations
    for key in fields.keys():
        if key in device_configurations:
            configuration_data[key] = device_configurations[key]

    # Update existing prediction or insert new one using upsert
    try:
        result = predictions_collection.update_one(
            {
                "user_id": user["_id"],
                "device_id": device["_id"]
            },
            {"$set": configuration_data},
            upsert=True
        )
        return "success"
    except Exception as e:
        print(f"Error updating device predictions: {e}")
        return "error"
