from pymongo.mongo_client import MongoClient
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import json
from datetime import datetime

def parse_timestamp(ts):
    if isinstance(ts, datetime):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.utcfromtimestamp(ts)
    if isinstance(ts, str):
        try:
            return datetime.fromisoformat(ts)
        except Exception:
            pass
        try:
            return datetime.utcfromtimestamp(float(ts))
        except Exception:
            pass
    return datetime.utcnow()

def update_device_info(username, sending_device_name, device_info):
    """
    Updates the information for a specific device based on received data.

    Connects to MongoDB, finds the user by username, finds the device by the
    'sending_device_name', and updates its details using $set for static info
    and $push for time-series data (usage, speeds, etc.).

    Args:
        username (str): The username of the device owner.
        sending_device_name (str): The name of the device whose info is being updated.
        device_info (dict): A dictionary containing the new device details.
                            Expected keys include static info (like manufacturer,
                            model, capacity) and time-series data points (like
                            cpu_usage, ram_usage, speeds, current_time).

    Returns:
        str: "success" if the update was successful.
             "user not found" if the user does not exist.
             "device not found" if the sending device does not exist for that user.
             "error" if an exception occurred during the database update.
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    device_info_collection = db["device_info"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return "user not found"

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": sending_device_name,
    })
    if not device:
        return "device not found"

    # Instead of inserting a new document, append time-series data to arrays in a single document per device_id
    if device_info is None:
        print("Error: device_info is None. Not inserting.")
        return "error: device_info is None"
    try:
        doc = {
            "timestamp": parse_timestamp(device_info.get('current_time')),
            "metadata": {
                "device_id": device["_id"],
                "username": username,
                "device_name": sending_device_name,
            },
            "storage_capacity_gb": device_info.get('storage_capacity_gb'),
            "battery_status": device_info.get('battery_status'),
            "battery_time_remaining": device_info.get('battery_time_remaining'),
            "cpu_usage": device_info.get('cpu_usage'),
            "gpu_usage": device_info.get('gpu_usage'),
            "ram_usage": device_info.get('ram_usage'),
            "ram_total": device_info.get('ram_total'),
            "ram_free": device_info.get('ram_free'),
            "upload_speed": device_info.get('upload_speed'),
            "download_speed": device_info.get('download_speed'),
            # Add other fields as needed
        }
        print("Inserting time series device info:", doc)
        result = device_info_collection.insert_one(doc)
        print("Insert successful, inserted_id:", result.inserted_id)
        return "success"
    except Exception as e:
        print(f"Error updating device status: {e}")
        return "error"

def update_device_info_view(request):
    data = json.loads(request.body)
    username = request.username_from_token
    device_info = data.get("device_info")
    sending_device_name = data.get("sending_device_name")
    print("View received username:", username, "sending_device_name:", sending_device_name, "device_info:", device_info, flush=True)
    result = update_device_info(username, sending_device_name, device_info)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)

def add_model_to_device(username, device_name, model_name):
    """
    Adds a model to the downloaded_models array for a specific device.
    
    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device.
        model_name (str): The name of the model to add.
    
    Returns:
        str: "success" if successful, "user not found", "device not found", or "error".
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    try:
        print(f"DEBUG: Looking for user: {username}")
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            print(f"DEBUG: User not found: {username}")
            return "user not found"

        print(f"DEBUG: User found: {user['_id']}")
        print(f"DEBUG: Looking for device: {device_name} for user: {username}")
        
        # Find the device belonging to the user by device_name
        device = device_collection.find_one({
            "user_id": user["_id"],
            "device_name": device_name,
        })
        
        if not device:
            # Debug: Let's see what devices exist for this user
            all_user_devices = list(device_collection.find({"user_id": user["_id"]}))
            print(f"DEBUG: Device not found. Available devices for user {username}:")
            for d in all_user_devices:
                print(f"  - Device name: '{d.get('device_name')}'")
            print(f"DEBUG: Searched for device name: '{device_name}'")
            return "device not found"

        print(f"DEBUG: Device found: {device['_id']}")
        # Add model to downloaded_models array (using $addToSet to avoid duplicates)
        device_collection.update_one(
            {"_id": device["_id"]},
            {"$addToSet": {"downloaded_models": model_name}}
        )
        print(f"Added model {model_name} to device {device_name} for user {username}")
        return "success"
    except Exception as e:
        print(f"Error adding model to device: {e}")
        return "error"

def remove_model_from_device(username, device_name, model_name):
    """
    Removes a model from the downloaded_models array for a specific device.
    
    Args:
        username (str): The username of the device owner.
        device_name (str): The name of the device.
        model_name (str): The name of the model to remove.
    
    Returns:
        str: "success" if successful, "user not found", "device not found", or "error".
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    try:
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            return "user not found"

        # Find the device belonging to the user by device_name
        device = device_collection.find_one({
            "user_id": user["_id"],
            "device_name": device_name,
        })
        if not device:
            return "device not found"

        # Remove model from downloaded_models array
        device_collection.update_one(
            {"_id": device["_id"]},
            {"$pull": {"downloaded_models": model_name}}
        )
        print(f"Removed model {model_name} from device {device_name} for user {username}")
        return "success"
    except Exception as e:
        print(f"Error removing model from device: {e}")
        return "error"

@csrf_exempt
def add_downloaded_model_view(request):
    """
    View function to add a model to a device's downloaded_models array.
    """
    if request.method != 'POST':
        return JsonResponse({"result": "error", "error": "Only POST method allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        device_name = data.get("device_name")
        model_name = data.get("model_name")
        
        if not device_name or not model_name:
            return JsonResponse({"result": "error", "error": "device_name and model_name are required"}, status=400)
        
        print(f"Adding model {model_name} to device {device_name} for user {username}")
        result = add_model_to_device(username, device_name, model_name)
        
        if result == "success":
            return JsonResponse({"result": "success"})
        elif result == "user not found":
            return JsonResponse({"result": "error", "error": "user not found"}, status=404)
        elif result == "device not found":
            return JsonResponse({"result": "error", "error": "device not found"}, status=404)
        else:
            return JsonResponse({"result": "error", "error": "failed to add model"}, status=500)
            
    except Exception as e:
        print(f"Error in add_downloaded_model_view: {e}")
        return JsonResponse({"result": "error", "error": str(e)}, status=500)

@csrf_exempt
def remove_downloaded_model_view(request):
    """
    View function to remove a model from a device's downloaded_models array.
    """
    if request.method != 'POST':
        return JsonResponse({"result": "error", "error": "Only POST method allowed"}, status=405)
    
    try:
        data = json.loads(request.body)
        username = request.username_from_token
        device_name = data.get("device_name")
        model_name = data.get("model_name")
        
        if not device_name or not model_name:
            return JsonResponse({"result": "error", "error": "device_name and model_name are required"}, status=400)
        
        print(f"Removing model {model_name} from device {device_name} for user {username}")
        result = remove_model_from_device(username, device_name, model_name)
        
        if result == "success":
            return JsonResponse({"result": "success"})
        elif result == "user not found":
            return JsonResponse({"result": "error", "error": "user not found"}, status=404)
        elif result == "device not found":
            return JsonResponse({"result": "error", "error": "device not found"}, status=404)
        else:
            return JsonResponse({"result": "error", "error": "failed to remove model"}, status=500)
            
    except Exception as e:
        print(f"Error in remove_downloaded_model_view: {e}")
        return JsonResponse({"result": "error", "error": str(e)}, status=500)

