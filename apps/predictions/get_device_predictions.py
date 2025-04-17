from pymongo.mongo_client import MongoClient

def get_device_predictions(username):
    """Retrieves device prediction data for a specific user.

    Fetches all prediction documents associated with the user's ID from the
    'device_predictions' collection.

    Args:
        username (str): The username of the user whose predictions are to be retrieved.

    Returns:
        dict: A dictionary containing a list of device predictions under the key
              "device_predictions". Each prediction includes details like device ID,
              name, capacity, predicted speeds/usage, sync status, scores, and timestamps.
              Returns an error dictionary if the user is not found or a database
              connection error occurs.
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        device_predictions_collection = db["device_predictions"]
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return {"error": "Failed to connect to MongoDB"}

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all device predictions belonging to the user
    device_predictions = list(device_predictions_collection.find({"user_id": user["_id"]}))

    # Prepare predictions data for response
    predictions_data = []
    for prediction in device_predictions:
        predictions_data.append({
            "device_id": str(prediction.get("_id")),  # Convert ObjectId to string
            "device_name": prediction.get("device_name"),
            "sync_storage_capacity_gb": prediction.get("sync_storage_capacity_gb"),
            "predicted_upload_speed": prediction.get("predicted_upload_speed"),
            "predicted_download_speed": prediction.get("predicted_download_speed"),
            "predicted_gpu_usage": prediction.get("predicted_gpu_usage"),
            "predicted_cpu_usage": prediction.get("predicted_cpu_usage"),
            "predicted_ram_usage": prediction.get("predicted_ram_usage"),
            "use_device_in_file_sync": prediction.get("use_device_in_file_sync"),
            "use_predicted_upload_speed": prediction.get("use_predicted_upload_speed"),
            "use_predicted_download_speed": prediction.get("use_predicted_download_speed"),
            "use_predicted_gpu_usage": prediction.get("use_predicted_gpu_usage"),
            "use_predicted_cpu_usage": prediction.get("use_predicted_cpu_usage"),
            "use_predicted_ram_usage": prediction.get("use_predicted_ram_usage"),
            "use_files_needed": prediction.get("use_files_needed"),
            "use_files_available_for_download": prediction.get("use_files_available_for_download"),
            "score_timestamp": prediction.get("score_timestamp"),
            "timestamp": prediction.get("timestamp"),
            "score": prediction.get("score"),
            "files_needed": prediction.get("files_needed"),
            "files_available_for_download": prediction.get("files_available_for_download"),
        })

    response_data = {
        "device_predictions": predictions_data,
    }

    return response_data

if __name__ == "__main__":
    predictions = get_device_predictions("mmills")
    print(predictions)
