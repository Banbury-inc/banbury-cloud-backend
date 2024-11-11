from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from bson import ObjectId

def get_device_predictions(username):
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
            "device_id": prediction.get("_id"),  # Keep as ObjectId
            "device_name": prediction.get("device_name"),
            "sync_storage_capacity_gb": prediction.get("sync_storage_capacity_gb"),
            "predicted_upload_speed": prediction.get("predicted_upload_speed"),
            "predicted_download_speed": prediction.get("predicted_download_speed"),
            "predicted_gpu_usage": prediction.get("predicted_gpu_usage"),
            "predicted_cpu_usage": prediction.get("predicted_cpu_usage"),
            "predicted_ram_usage": prediction.get("predicted_ram_usage"),
            "score_timestamp": prediction.get("score_timestamp"),
            "timestamp": prediction.get("timestamp"),
            "score": prediction.get("score"),
        })

    response_data = {
        "device_predictions": predictions_data,
    }

    return response_data

if __name__ == "__main__":
    predictions = get_device_predictions("mmills")
    print(predictions)
