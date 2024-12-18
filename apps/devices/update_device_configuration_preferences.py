from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime

def update_device_configuration_preferences(username, device_name, device_configurations):
    '''
    Update a single device's prediction preferences in the database
    '''

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
        "device_name": device_name,
    })
    if not device:
        return f"device not found: {device_name}"

    # First check if a prediction document exists
    existing_config = predictions_collection.find_one({
        "user_id": user["_id"],
        "device_id": device["_id"]
    })

    # Prepare the update data with only the new configuration fields
    configuration_data = {
        "updated_at": datetime.utcnow(),
    }
    
    # Add the new boolean flag fields
    boolean_fields = {
        'use_predicted_upload_speed': False,
        'use_predicted_download_speed': False,
        'use_predicted_gpu_usage': False,
        'use_predicted_cpu_usage': False,
        'use_predicted_ram_usage': False,
        'use_files_needed': False,
        'use_files_available_for_download': False
    }
    
    # If document doesn't exist, include all boolean fields with defaults
    if not existing_config:
        configuration_data.update(boolean_fields)
    
    # Update with any provided configurations
    for key in boolean_fields.keys():
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
