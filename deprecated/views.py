from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.conf import settings
import os
from bson import ObjectId
import pymongo
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from datetime import datetime
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .forms import UserForm
import bcrypt
from .forms import LoginForm
from .forms import UserProfileForm
from .src.delete_files import delete_files
from .src.update_files import update_files
from .src.get_online_devices import get_online_devices
from .src.db.remove_device import remove_device
from .src.pipeline import pipeline
from .src.prediction_service import PredictionService
from .consumers import broadcast_new_file
from .src.db.db_add_file_to_sync import db_add_file_to_sync as db_add_file_to_sync
from .src.db.paginated_get_files_info import paginated_get_files_info
from .src.db.get_files_from_filepath import get_files_from_filepath as db_get_files_from_filepath
from .src.db.get_file_sync import get_file_sync as db_get_file_sync
from .src.db.update_file_priority import update_file_priority as db_update_file_priority
from .src.db.update_sync_storage_capacity import update_sync_storage_capacity as db_update_sync_storage_capacity
from .src.db.get_download_queue import get_download_queue as db_get_download_queue
from .src.db.get_device_predictions import get_device_predictions as db_get_device_predictions
from .src.db.update_device_configuration_preferences import update_device_configuration_preferences as db_update_device_configuration_preferences
import json
import re


@api_view(["GET"])
def ping(request):
    result = "pong"

    response = {
        "result": result,
    }

    return JsonResponse(response)


@api_view(["GET"])
def get_small_user_info(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})
    if not user:
        print("Please login first.")
    else:
        if user["username"] == username:
            first_name = user.get("first_name")
            last_name = user.get("last_name")
            phone_number = user.get("phone_number")
            email = user.get("email")

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "email": email,
            }
            return JsonResponse(user_data)


@api_view(["GET"])
def getuserinfo2(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})
    if not user:
        print("Please login first.")
    else:
        if user["username"] == username:
            first_name = user.get("first_name")
            last_name = user.get("last_name")
            phone_number = user.get("phone_number")
            email = user.get("email")

            devices = user.get("devices", [])
            number_of_files = user.get("number_of_files", [])
            number_of_devices = user.get("number_of_devices", [])
            overall_date_added = user.get("overall_date_added", [])
            total_average_upload_speed = user.get("total_average_upload_speed", [])
            total_average_download_speed = user.get("total_average_download_speed", [])
            total_device_storage = user.get("total_device_storage", [])

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "email": email,
                "devices": devices,
                "number_of_devices": number_of_devices,
                "number_of_files": number_of_files,
                "overall_date_added": overall_date_added,
                "total_average_upload_speed": total_average_upload_speed,
                "total_average_download_speed": total_average_download_speed,
                "total_device_storage": total_device_storage,
            }
            return JsonResponse(user_data)


@api_view(["GET"])
def getuserinfo(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    username = username
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})
    if not user:
        print("Please login first.")
    else:
        if user["username"] == username:
            first_name = user.get("first_name")
            last_name = user.get("last_name")
            phone_number = user.get("phone_number")
            email = user.get("email")

            user_data = {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "email": email,
            }
            return JsonResponse(user_data)


@api_view(["GET"])
def getdeviceinfo(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({"error": "Please login first."}, status=401)

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))

    # Prepare devices data for response
    device_data = []
    for device in devices:
        device_data.append({
            "device_name": device.get("device_name"),
            "device_type": device.get("device_type"),
            "storage_capacity_gb": device.get("storage_capacity_gb"),
            "device_manufacturer": device.get("device_manufacturer"),
            "device_model": device.get("device_model"),
            "device_version": device.get("device_version"),
            "cpu_info_manufacturer": device.get("cpu_info_manufacturer"),
            "cpu_info_brand": device.get("cpu_info_brand"),
            "cpu_info_speed": device.get("cpu_info_speed"),
            "cpu_info_cores": device.get("cpu_info_cores"),
            "cpu_info_physical_cores": device.get("cpu_info_physical_cores"),
            "cpu_info_processors": device.get("cpu_info_processors"),
            "date_added": device.get("date_added"),
            "upload_speed": device.get("upload_speed"),
            "download_speed": device.get("download_speed"),
            "battery_status": device.get("battery_status"),
            "gpu_usage": device.get("gpu_usage"),
            "cpu_usage": device.get("cpu_usage"),
            "ram_usage": device.get("ram_usage"),
            "ram_total": device.get("ram_total"),
            "ram_free": device.get("ram_free"),
            "sync_status": device.get("sync_status"),
            "online": device.get("online"),
            "scanned_folders": device.get("scanned_folders"),
        })

    device_data = {
        "devices": device_data,
    }

    return JsonResponse(device_data)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def handle_get_online_devices(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    response = get_online_devices(username)

    if response == "fail":
        return JsonResponse({"result": "fail", "message": "fail"})
    if response == "success":
        return JsonResponse({
            "result": "success",
            "message": "Files deleted successfully.",
        })

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def delete_device(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        response = remove_device(username, device_name)
        if response == "success":
            return JsonResponse({
                "result": "success",
                "message": "Device deleted successfully.",
            })
        else:
            return JsonResponse({
                "result": "fail",
                "message": "Device not deleted.",
            })
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def declare_device_online(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        user_data = {"result": "fail cant find user", "username": username}
        return JsonResponse(user_data)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        # Return success response
        user_data = {"result": "fail cant find device", "username": username}
        return JsonResponse(user_data)

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"online": True}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def declare_device_offline(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)

    # Update the "online" field to True
    try:
        device_collection.update_one(
            {"_id": device["_id"]},  # Find the device by its ID
            {"$set": {"online": False}},  # Update only the 'online' field
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def add_scanned_folder(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        folder_path = data.get("scanned_folder")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)

    # Ensure "scanned_folders" is an array, then add "folder_path" to it
    try:
        # Check if "scanned_folders" is not an array, set it as an empty array
        if not isinstance(device.get("scanned_folders"), list):
            device_collection.update_one(
                {"_id": device["_id"]},
                {"$set": {"scanned_folders": []}}
            )

        # Push "folder_path" to the "scanned_folders" array
        device_collection.update_one(
            {"_id": device["_id"]},
            {"$push": {"scanned_folders": folder_path}}
        )
    except Exception as e:
        print(f"Error updating device status: {e}")
        return JsonResponse({"error": "Failed to update device status."}, status=500)

    # Return success response
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)

@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def remove_scanned_folder(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        folder_to_remove = data.get("scanned_folder")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)

    # Ensure "scanned_folders" is an array
    if not isinstance(device.get("scanned_folders"), list):
        device_collection.update_one(
            {"_id": device["_id"]},
            {"$set": {"scanned_folders": []}}
        )
    
    # Find the device and remove the matching folder from scanned_folders
    result = device_collection.update_one(
        {"_id": device["_id"]},
        {"$pull": {"scanned_folders": folder_to_remove}}
    )
    
    if result.modified_count == 1:
        return JsonResponse({"status": "success", "message": "Folder removed successfully"})
    else:
        return JsonResponse({"status": "not_found", "message": "Folder not found in scanned_folders"})

@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_scanned_folders(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)
    
    # Find the device belonging to the user by device_name
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name,
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)
    
    # Return the scanned folders
    return JsonResponse({
        "result": "success",
        "scanned_folders": device.get("scanned_folders", [])
    })


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_prediction_data(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


    result = "success"
    
    
    # Return the scanned folders
    return JsonResponse({
        "result": "success",
        "prediction_data": result
    })


@api_view(["GET"])
def getfileinfo(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    file_collection = db["files"]

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({"error": "Please login first."}, status=401)

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

    return JsonResponse(files_data)


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_files_from_filepath(request, username):
    try:
        data = json.loads(request.body)
        filepath = data.get("global_file_path")
        response = db_get_files_from_filepath(username, filepath)
        if response.get('result') == "success":
            files_data = {
                "files": response.get("files"),
            }
            return JsonResponse(files_data)
        else:
            return JsonResponse({"error": "Failed to get files"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def update_sync_storage_capacity(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        storage_capacity = data.get("storage_capacity")
        response = db_update_sync_storage_capacity(username, device_name, storage_capacity)

        print(response)

        files_data = {
            "result": response.get("result"),
            "message": response.get("message"),
        }

        return JsonResponse(files_data)



    except json.JSONDecodeError:

        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_download_queue(request, username):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        response = db_get_download_queue(username, device_name)
        return JsonResponse({
            "result": "success",
            "download_queue": response,
            "message": "Download queue retrieved successfully",
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_files_to_sync(request, username):
    try:
        # Parse request body
        data = json.loads(request.body)
        global_file_path = data.get('global_file_path')
        
        # Call database function with optional global_file_path
        response, status_code = db_get_file_sync(username, global_file_path)
        
        if status_code != 200:
            return JsonResponse({
                "result": "error",
                "message": response.get("error", "Unknown error occurred"),
                "files": []
            }, status=status_code)
            
        return JsonResponse({
            "result": "success",
            "files": response.get("files", [])
        })

    except json.JSONDecodeError:
        return JsonResponse({
            "result": "error",
            "message": "Invalid JSON",
            "files": []
        }, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "error",
            "message": str(e),
            "files": []
        }, status=500)

@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def update_file_priority(request, username):
    try:
        data = json.loads(request.body)
        file_id = data.get("file_id")
        priority = data.get("priority")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    response = db_update_file_priority(username, file_id, priority)


    files_data = {
        "result": response.get("result"),
        "message": response.get("message"),
    }



    return JsonResponse(files_data)




@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def paginated_get_files_info(request, username):
    try:
        data = json.loads(request.body)
        page = data.get("page", 1)
        items_per_page = data.get("items_per_page", 10)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    return paginated_get_files_info(username, page=page, items_per_page=items_per_page)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def update_settings(request, username):
    try:
        data = json.loads(request.body)
        sync_entire_device_checked = data.get("sync_entire_device_checked")
        predicted_upload_speed_weighting = data.get("predicted_upload_speed_weighting")
        predicted_download_speed_weighting = data.get("predicted_download_speed_weighting")
        predicted_cpu_usage_weighting = data.get("predicted_cpu_usage_weighting")
        predicted_ram_usage_weighting = data.get("predicted_ram_usage_weighting")
        predicted_gpu_usage_weighting = data.get("predicted_gpu_usage_weighting")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    settings_collection = db["settings"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    user_id = user["_id"]

    # Check if settings already exist for this user
    existing_settings = settings_collection.find_one({
        "user_id": user_id
    })

    settings_data = {
        "sync_entire_device_checked": sync_entire_device_checked,
        "predicted_upload_speed_weighting": predicted_upload_speed_weighting,
        "predicted_download_speed_weighting": predicted_download_speed_weighting,
        "predicted_cpu_usage_weighting": predicted_cpu_usage_weighting,
        "predicted_ram_usage_weighting": predicted_ram_usage_weighting,
        "predicted_gpu_usage_weighting": predicted_gpu_usage_weighting,
    }

    try:
        if existing_settings:
            # Update existing settings
            settings_collection.update_one(
                {"_id": existing_settings["_id"]},
                {"$set": settings_data}
            )
            message = "Settings updated successfully"
        else:
            # Create new settings
            settings_data.update({
                "user_id": user_id
            })
            settings_collection.insert_one(settings_data)
            message = "Settings created successfully"

        return JsonResponse({
            "result": "success",
            "message": message,
            "username": username
        })

    except Exception as e:
        print(f"Error updating settings: {e}")
        return JsonResponse({
            "result": "error",
            "message": str(e)
        }, status=500)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def get_partial_file_info(request, username):
    try:
        data = json.loads(request.body)
        folder_path = data.get("folder_path")
        max_depth = data.get(
            "max_depth", 4
        )  # Default to 4 levels deep if not specified
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    file_collection = db["files"]

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({"error": "User not found."}, status=404)

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))

    # Prepare file data for response
    all_files_data = []
    for device in devices:
        # Construct the regular expression for matching file paths based on the max_depth
        depth_pattern = f"([^/]+/)" * (max_depth - 1) + "[^/]+/?$"
        regex_pattern = f"^{re.escape(folder_path)}{depth_pattern}"

        # Build the query with an optional file type filter
        query = {"device_id": device["_id"], "file_path": {"$regex": regex_pattern}}

        # Find all files for the current device within the specified folder and depth
        files = list(file_collection.find(query))

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

    return JsonResponse(files_data)


@api_view(["GET"])
def getuserinfo3(request, username, password):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({
            "result": "fail",
            "message": "User not found. Please login first.",
        })

    # Assuming password stored in the database is hashed and saved as bytes.
    # Also assuming 'password' parameter from the function call is the plaintext password to verify.
    stored_hashed_password = user["password"]
    password_bytes = password.encode("utf-8")  # Encode the plaintext password to bytes

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get("username")
    else:
        result = "fail"
        username = None

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@api_view(["GET"])
def getuserinfo4(request, username, password):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({
            "result": "fail",
            "message": "User not found. Please login first.",
        })

    # Assuming password stored in the database is hashed and saved as bytes.
    # Also assuming 'password' parameter from the function call is the plaintext password to verify.
    try:
        stored_hashed_password = user["password"]
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    try:
        password_bytes = password.encode(
            "utf-8"
        )  # Encode the plaintext password to bytes
    except:
        return JsonResponse({"result": "fail", "message": "Can't find user password"})

    if bcrypt.checkpw(password_bytes, stored_hashed_password):
        result = "success"
        username = user.get("username")
    else:
        result = "fail"
        username = None

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@api_view(["GET"])
def get_neuranet_info(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    server_data_collection = db["server"]

    # Find the document
    server_data = server_data_collection.find_one({})

    # Extract the specific fields
    total_data_processed = server_data.get("total_data_processed", None)
    total_number_of_requests = server_data.get("total_number_of_requests", None)

    collected_server_data = {
        "total_data_processed": total_data_processed,
        "total_number_of_requests": total_number_of_requests,
    }

    return JsonResponse(collected_server_data)


@csrf_exempt
@api_view(["GET"])
def update_devices(request, username):
    if request.method == "POST":
        try:
            # Load JSON data from the request body
            data = json.loads(request.body)
            new_files = data.get("files", [])
            device_name = data.get("device_name")

            # Connection URI to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["myDatabase"]

            # Find the user by username
            user = user_collection.find_one({"username": username})

            # Update the files array for the specific device
            result = user_collection.update_one(
                {"_id": user["_id"], "devices.device_name": device_name},
                {"$set": {"devices.$.files": new_files}},
            )

            # Check if the update was successful
            if result.modified_count > 0:
                return JsonResponse({"response": "success"})
            else:
                # return JsonResponse({'error': 'Device not found or no update needed'}, status=404)
                return JsonResponse({"response": "no change needed"})

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "GET":
        return JsonResponse({"response": "success"})

    else:
        return JsonResponse({"error": "Invalid method"}, status=405)


@api_view(["GET"])
def change_profile(request, username, password, first_name, last_name, email):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    if not user:
        return JsonResponse({
            "result": "fail",
            "message": "User not found. Please login first.",
        })

    if password == "undefined":
        user_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "email": email,
                }
            },
        )
    else:
        password_bytes = password.encode("utf-8")  # Encode the string to bytes
        hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

        user_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "username": username,
                    "email": email,
                    "password": hashed_password,
                }
            },
        )

    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@api_view(["GET"])
def register(request, username, password, firstName, lastName):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["myDatabase"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    password_bytes = password.encode("utf-8")  # Encode the string to bytes
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    if user:
        user_data = {"result": "user_already_exists", "username": username}
        return JsonResponse(user_data)

    new_user = {
        "username": username,
        "password": hashed_password,
        "first_name": firstName,
        "last_name": lastName,
        "phone_number": None,
        "email": None,
        "devices": [],
        "number_of_devices": [],
        "number_of_files": [],
        "overall_date_added": [],
        "total_average_download_speed": [],
        "total_average_upload_speed": [],
        "total_device_storage": [],
        "total_average_cpu_usage": [],
        "total_average_gpu_usage": [],
        "total_average_ram_usage": [],
    }

    try:
        user_collection.insert_one(new_user)
    except Exception as e:
        print(f"Error sending to device: {e}")
    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@api_view(["GET"])
def new_register(request, username, password, firstName, lastName):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": username})

    password_bytes = password.encode("utf-8")  # Encode the string to bytes
    hashed_password = bcrypt.hashpw(password_bytes, bcrypt.gensalt())

    if user:
        user_data = {"result": "user_already_exists", "username": username}
        return JsonResponse(user_data)

    new_user = {
        "username": username,
        "password": hashed_password,
        "first_name": firstName,
        "last_name": lastName,
        "phone_number": None,
        "email": None,
        "devices": [],
    }

    try:
        user_collection.insert_one(new_user)
    except Exception as e:
        print(f"Error sending to device: {e}")
    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_device(request, username, device_name):
    try:
        data = json.loads(request.body)
        device_name = data.get("device_name")
        device_type = data.get("device_type")
        storage_capacity_gb = data.get("storage_capacity_gb")
        sync_storage_capacity_gb = data.get("sync_storage_capacity_gb")
        date_added = data.get("date_added")
        upload_network_speed = data.get("upload_network_speed")
        download_network_speed = data.get("download_network_speed")
        gpu_usage = data.get("gpu_usage")
        cpu_usage = data.get("cpu_usage")
        ram_usage = data.get("ram_usage")
        ram_total = data.get("ram_total")
        ram_free = data.get("ram_free")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    device_collection = db["devices"]
    user_collection = db["users"]

    # Find the user_id based on username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"result": "error", "message": "Device not found."})

    user_id = user["_id"]  # Get the ObjectId for the device

    new_device = {
        "user_id": user_id,
        "device_name": device_name,
        "device_type": device_type,
        "storage_capacity_gb": storage_capacity_gb,
        "sync_storage_capacity_gb": sync_storage_capacity_gb,
        "date_added": [],
        "upload_network_speed": [],
        "download_network_speed": [],
        "gpu_usage": [],
        "cpu_usage": [],
        "ram_usage": [],
        "ram_total": [],
        "ram_free": [],
        "sync_status": False,
        "online": True,
    }

    try:
        # Insert the new device and get the inserted_id
        result = device_collection.insert_one(new_device)
        device_id = result.inserted_id

        # Update the user collection to add the device_id to the user's list of devices
        user_collection.update_one({"_id": user_id}, {"$push": {"devices": device_id}})

        # Append all usage data and other arrays in the device document
        device_collection.update_one(
            {"_id": device_id},
            {
                "$push": {
                    "gpu_usage": gpu_usage,
                    "cpu_usage": cpu_usage,
                    "ram_usage": ram_usage,
                    "ram_total": ram_total,
                    "ram_free": ram_free,
                    "download_network_speed": download_network_speed,
                    "upload_network_speed": upload_network_speed,
                    "date_added": date_added,
                }
            },
        )

    except Exception as e:
        print(f"Error sending to device: {e}")

    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }
    return JsonResponse(user_data)

@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def add_file_to_sync(request, username):
    data = json.loads(request.body)
    device_name = data.get("device_name")
    file_path = data.get("file_path")
    response = db_add_file_to_sync(username, device_name, file_path)

    user_data = {
        "result": response,
        "username": username,  # Return username if success, None if fail
    }

    return JsonResponse(user_data)
            
        

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_file(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

        # Extract specific data from the JSON (for example: device_id and date_added)
        file_type = data.get("file_type")
        file_name = data.get("file_name")
        file_path = data.get("file_path")
        date_uploaded = data.get("date_uploaded")
        date_modified = data.get("date_modified")
        file_size = data.get("file_size")
        file_size = 2
        file_priority = data.get("file_priority")
        file_parent = data.get("file_parent")
        original_device = data.get("original_device")
        kind = data.get("kind")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_collection = db["files"]
    device_collection = db["devices"]

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": original_device})
    if not device:
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        })

    try:
        device_id = device["_id"]  # Get the ObjectId for the device
    except:
        return JsonResponse({
            "result": "object_id_not_found",
            "message": "Device id not found.",
        })

    new_file = {
        "device_id": device_id,
        "file_type": file_type,
        "file_name": file_name,
        "file_path": file_path,
        "date_uploaded": date_uploaded,
        "date_modified": date_modified,
        "file_size": file_size,
        "file_size": 2,
        "file_priority": file_priority,
        "file_parent": file_parent,
        "original_device": original_device,
        "kind": kind,
    }

    try:
        file_collection.insert_one(new_file)
    except Exception as e:
        print(f"Error sending to device: {e}")
    result = "success"

    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }

    result = broadcast_new_file(new_file)

    return JsonResponse(user_data)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_site_visitor_info(request):
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        # Extract specific data from the JSON (for example: device_id and date_added)
        ip_address = data.get("ip_address")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Fetch location data based on the IP address
    try:
        geo_response = requests.get(f"https://ipapi.co/{ip_address}/json/")
        if geo_response.status_code == 200:
            geo_data = geo_response.json()
            city = geo_data.get("city", "Unknown")
            region = geo_data.get("region", "Unknown")
            country = geo_data.get("country_name", "Unknown")
        else:
            city = "Unknown"
            region = "Unknown"
            country = "Unknown"
    except requests.RequestException:
        city = "Unknown"
        region = "Unknown"
        country = "Unknown"

    time = datetime.now()

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    site_collection = db["site"]

    # Prepare the document to insert
    new_visitor = {
        "ip_address": ip_address,
        "time": time,
        "city": city,
        "region": region,
        "country": country,
    }

    try:
        site_collection.insert_one(new_visitor)
        result = "success"
    except Exception as e:
        print(f"Error inserting to MongoDB: {e}")
        result = "failed"

    # Return the result
    return JsonResponse({"result": result})


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_files(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        # Extract specific data from the JSON
        files = data.get("files")
        device_name = data.get("device_name")
        if not files or not device_name:
            return JsonResponse({"error": "Missing files or device_name"}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_collection = db["files"]
    device_collection = db["devices"]
    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        })
    device_id = device.get("_id")
    if not device_id:
        return JsonResponse({
            "result": "object_id_not_found",
            "message": "Device ID not found.",
        })
    # Prepare the list of new files to insert
    new_files = []
    for file_data in files:
        # Validate that file_data is a dictionary and contains the necessary fields
        if not isinstance(file_data, dict):
            return JsonResponse(
                {"error": f"Invalid file data format: {file_data}"}, status=400
            )
        required_fields = ["file_name", "file_path"]
        missing_fields = [
            field for field in required_fields if not file_data.get(field)
        ]
        if missing_fields:
            return JsonResponse(
                {"error": f"Missing fields: {missing_fields}"}, status=401
            )
        # Prepare new file data for insertion
        new_file = {
            "device_id": device_id,
            "file_type": file_data.get("file_type"),
            "file_name": file_data.get("file_name"),
            "file_path": file_data.get("file_path"),
            "file_size": file_data.get("file_size"),
            "date_uploaded": file_data.get("date_uploaded"),
            "date_modified": file_data.get("date_modified"),
            # "file_size": file_data.get('file_size'),
            # "file_priority": file_data.get('file_priority'),
            "file_parent": file_data.get("file_parent"),
            "original_device": file_data.get("original_device"),
            "kind": file_data.get("kind"),
        }
        new_files.append(new_file)
    # If no valid files to add, return early
    if not new_files:
        return JsonResponse({
            "result": "no_files_to_add",
            "message": "No valid files to add.",
        })
    # Insert all new files in one go
    try:
        file_collection.insert_many(new_files)
    except Exception as e:
        print(f"Error inserting files: {e}")
        return JsonResponse(
            {"result": "failure", "message": f"Error inserting files: {str(e)}"},
            status=500,
        )
    return JsonResponse({
        "result": "success",
        "message": f"{len(new_files)} files added successfully.",
    })

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def handle_delete_files(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        # Extract specific data from the JSON
        files = data.get("files")
        device_name = data.get("device_name")
        if not files or not device_name:
            return JsonResponse({"error": "Missing files or device_name"}, status=400)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    response = delete_files(username, device_name, files)
    if response == "device_not_found":
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        })
    if response == "device_id_not_found":
        return JsonResponse({
            "result": "device_id_not_found",
            "message": "Device id not found.",
        })
    if response == "success":
        return JsonResponse({
            "result": "success",
            "message": "Files deleted successfully.",
        })

@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def handle_update_files(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

        # Extract specific data from the JSON
        files = data.get("files")
        device_name = data.get("device_name")

        if not files or not device_name:
            return JsonResponse({"error": "Missing files or device_name"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    response = update_files(username, device_name, files)

    if response == "device_not_found":
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        })
    if response == "device_id_not_found":
        return JsonResponse({
            "result": "device_id_not_found",
            "message": "Device id not found.",
        })
    if response == "success":
        return JsonResponse({
            "result": "success",
            "message": "Files deleted successfully.",
        })



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def search_file(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

        # Extract specific data from the JSON
        device_name = data.get("device_name")
        file_name = data.get("file_name")

        if not device_name or not file_name:
            return JsonResponse({"error": "Missing device_name or file_name"}, status=400)

    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_collection = db["files"]
    device_collection = db["devices"]

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        }, status=200)

    device_id = device.get("_id")
    if not device_id:
        return JsonResponse({
            "result": "object_id_not_found",
            "message": "Device ID not found.",
        }, status=200)

    # Search for the file based on device_id and file_name
    file = file_collection.find_one({"device_id": device_id, "file_name": file_name})
    if not file:
        return JsonResponse({
            "result": "file_not_found",
            "message": "File not found for the given device.",
        }, status=200)

    # If file is found, return all the file information
    return JsonResponse({
        "result": "success",
        "file": {
            "file_name": file.get("file_name"),
            "file_path": file.get("file_path"),
            "file_size": file.get("file_size"),
            "file_type": file.get("file_type"),
            "date_uploaded": file.get("date_uploaded"),
            "date_modified": file.get("date_modified"),
            "file_parent": file.get("file_parent"),
            "original_device": file.get("original_device"),
            "kind": file.get("kind"),
        }
    }, status=200)


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_task(request, username):
    try:
        data = json.loads(request.body)
        task_name = data.get("task_name")
        task_device = data.get("task_device")
        task_progress = data.get("task_progress")
        task_status = data.get("task_status")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    session_collection = db["sessions"]
    device_collection = db["devices"]

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": task_device})
    if not device:
        return JsonResponse({
            "result": "device_not_found",
            "message": "Device not found.",
        })

    try:
        device_id = device["_id"]  # Get the ObjectId for the device
    except:
        return JsonResponse({
            "result": "object_id_not_found",
            "message": "Device id not found.",
        })

    new_task = {
        "device_id": device_id,
        "username": username,
        "task_name": task_name,
        "task_device": task_device,
        "task_status": task_status,
        "task_progress": task_progress,
        "task_date_added": datetime.now(),
        "task_date_modified": datetime.now(),
    }

    try:
        result = session_collection.insert_one(new_task)
        return JsonResponse({
            "result": "success",
            "username": username,
            "task_id": str(result.inserted_id)  # Return the task ID
        })
    except Exception as e:
        return JsonResponse({"result": "error", "message": str(e)})


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def update_task(request, username):
    try:
        data = json.loads(request.body)
        task_id = data.get("task_id")  # Get task_id instead of task_name
        task_progress = data.get("task_progress")
        task_status = data.get("task_status")
        task_name = data.get("task_name")  # Optional for updating name
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    session_collection = db["sessions"]

    update_fields = {
        "task_status": task_status,
        "task_progress": task_progress,
        "task_date_modified": datetime.now(),
    }
    if task_name:
        update_fields["task_name"] = task_name

    update_result = session_collection.update_one(
        {"_id": ObjectId(task_id)},  # Use task_id to find the task
        {"$set": update_fields}
    )

    if update_result.matched_count == 0:
        return JsonResponse({"result": "task_not_found", "message": "Task not found."})

    return JsonResponse({
        "result": "success",
        "task_id": str(task_id),
        "message": "Task status updated successfully.",
    })


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def fail_task(request, username):
    try:
        # Parse the JSON body
        data = json.loads(request.body)

        task_name = data.get("task_name")
        task_progress = data.get("task_progress")
        result = data.get("result")
        task_device = data.get(
            "task_device"
        )  # You may also want to use the device name for better specificity
        task_status = data.get("task_status")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    session_collection = db["sessions"]

    # Use both task_name and task_device to find the specific task
    query = {"task_name": task_name}
    if task_device:
        query["task_device"] = task_device

    # Update the task with the new status and update the task_date_modified field
    update_result = session_collection.update_one(
        query,
        {
            "$set": {
                "task_status": task_status,
                "task_name": result,
                "task_progress": task_progress,
                "task_date_modified": datetime.now(),  # Update the modification date
            }
        },
    )

    if update_result.matched_count == 0:
        return JsonResponse({"result": "task_not_found", "message": "Task not found."})

    return JsonResponse({
        "result": "success",
        "message": "Task status updated successfully.",
    })


@csrf_exempt
@require_http_methods(["POST"])
@api_view(["POST"])
def get_session(request, username):
    # Parse the JSON body
    data = json.loads(request.body)
    task_device = data.get("task_device")

    if not task_device:
        return JsonResponse(
            {"result": "no_device_provided", "message": "No device provided."},
            status=400,
        )
    if not username:
        return JsonResponse(
            {"result": "no_username_provided", "message": "No username provided."},
            status=400,
        )

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    try:
        session_collection = db["sessions"]
    except:
        return JsonResponse({"error": "Can't find session collection"})

    sessions = session_collection.find({
        "username": username,
        "task_device": task_device,
    })

    all_sessions_data = []
    # Convert the cursor to a list of dictionaries and serialize ObjectId to string
    for session in sessions:
        all_sessions_data.append({
            "task_id": session["_id"],
            "task_name": session["task_name"],
            "task_device": session["task_device"],
            "task_status": session["task_status"],
            "task_progress": session["task_progress"],
            "task_date_added": session["task_date_added"],
            "task_date_modified": session["task_date_modified"],
        })

    response_data = {"result": "success", "sessions": all_sessions_data}

    return JsonResponse(response_data, status=200)


@csrf_exempt
@require_http_methods(["GET"])
@api_view(["GET"])
def run_pipeline(request, username):
    result = pipeline(username)
    response_data = {
        "result": "success",
        "data": result,
    }   
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["GET"])
@api_view(["GET"])
def get_device_prediction_data(request, username):
    result = db_get_device_predictions(username)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_view(["GET", "POST"])
def update_device_configuration_preferences(request, username):
    data = json.loads(request.body)
    device_name = data.get("device_name")
    device_configurations = {
        "use_predicted_cpu_usage": data.get("use_predicted_cpu_usage"),
        "use_predicted_gpu_usage": data.get("use_predicted_gpu_usage"),
        "use_predicted_ram_usage": data.get("use_predicted_ram_usage"),
        "use_predicted_download_speed": data.get("use_predicted_download_speed"),
        "use_predicted_upload_speed": data.get("use_predicted_upload_speed"),
        "use_files_needed": data.get("use_files_needed"),
        "use_files_available_for_download": data.get("use_files_available_for_download"),
    }
    result = db_update_device_configuration_preferences(username, device_name, device_configurations)
    response_data = {   
        "result": "success",
        "data": result,
    }
    return JsonResponse(response_data)



@csrf_exempt
@require_http_methods(["GET", "POST"])
@api_view(["GET", "POST"])
def get_recent_session(request, username):
    # Parse the JSON body
    data = json.loads(request.body)
    task_device = data.get("task_device")

    if not task_device:
        return JsonResponse(
            {"result": "no_device_provided", "message": "No device provided."},
            status=400,
        )
    if not username:
        return JsonResponse(
            {"result": "no_username_provided", "message": "No username provided."},
            status=400,
        )

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    try:
        session_collection = db["sessions"]
    except:
        return JsonResponse({"error": "Can't find session collection"})

    sessions = session_collection.find({
        "username": username,
        "task_device": task_device,
    })

    all_sessions_data = []
    for session in sessions:
        # Use .get() with default values for all fields
        all_sessions_data.append({
            "task_id": str(session["_id"]),
            "task_name": session.get("task_name", ""),
            "task_device": session.get("task_device", ""),
            "task_progress": session.get("task_progress", 0),  # Default to 0
            "task_status": session.get("task_status", "unknown"),  # Default to "unknown"
            "task_date_added": session.get("task_date_added", None),
            "task_date_modified": session.get("task_date_modified", None)
        })

    response_data = {"sessions": all_sessions_data}
    return JsonResponse(response_data, status=200)




# def registration_api(request, firstName, lastName, username, password):

#
#     uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"

#     client = pymongo.MongoClient(uri, server_api=ServerApi('1'))
#     db = client['myDatabase']
#     user_collection = db['users']

#     # Ensure the request body is JSON

#     hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

#     # Create a new user document with additional fields set to null
#     new_user = {
#         "username": username,
#         "password": hashed_password,
#         "first_name": firstName,
#         "last_name": lastName,
#         "phone_number": None,
#         "email": None,
#         "devices": [],
#         "number_of_devices": [],
#         "number_of_files": [],
#         "overall_date_added": [],
#         "total_average_download_speed": [],
#         "total_average_upload_speed": [],
#         "total_device_storage": [],
#         "total_average_cpu_usage": [],
#         "total_average_gpu_usage": [],
#         "total_average_ram_usage": [],
#     }


#     try:
#         user_collection.insert_one(new_user)
#         message = {
#             "response": "success",
#                 }
#         return JsonResponse(message)
#     except Exception as e:
#         message = {
#             "response": "fail",
#         }
#         return JsonResponse(message)


@api_view(["GET"])
def homepage(request):
    service = os.environ.get("K_SERVICE", "Unknown service")
    revision = os.environ.get("K_REVISION", "Unknown revision")

    return render(
        request,
        "homepage.html",
        context={
            "message": "It's running!",
            "Service": service,
            "Revision": revision,
        },
    )


@api_view(["GET"])
def aboutpage(request):
    return render(request, "aboutpage.html", context={})


@api_view(["GET"])
def download_debian_package(request):
    file_path = os.path.join(
        settings.BASE_DIR, "helloapp/templates/bcloud_1.0.0_all.deb"
    )
    if os.path.exists(file_path):
        with open(file_path, "rb") as fh:
            response = HttpResponse(
                fh.read(), content_type="application/vnd.debian.binary-package"
            )
            response["Content-Disposition"] = (
                'attachment; filename="bcloud_1.0.0.0_all.deb"'
            )
            return response
    else:
        response = HttpResponse("File not found.", status=404)
    return response


@api_view(["GET"])
def addusernopassword(request):
    # MongoDB connection string

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    # Create a MongoDB client
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))

    # Select the database and collection
    db = client["myDatabase"]
    user_collection = db["users"]

    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            # Insert the user into the database
            try:
                user_collection.insert_one({"username": username})
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"
            return render(request, "user_added.html", {"message": message})
    else:
        form = UserForm()

    return render(request, "add_user.html", {"form": form})


@api_view(["GET"])
def adduser1(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["first_name"]
            username = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]  # Get the password from the form

            # Hash the password
            hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

            try:
                # Insert the user with the hashed password into the database
                user_collection.insert_one({
                    "username": username,
                    "password": hashed_password,
                })
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"
            return render(request, "user_added.html", {"message": message})
    else:
        form = UserForm()

    return render(request, "add_user.html", {"form": form})


@api_view(["GET"])
def adduser(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    if request.method == "POST":
        form = UserForm(request.POST)
        if form.is_valid():
            firstName = form.cleaned_data["first_name"]
            lastName = form.cleaned_data["last_name"]
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"].encode("utf-8")

            hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

            # Create a new user document with additional fields set to null
            new_user = {
                "username": username,
                "password": hashed_password,
                "first_name": firstName,
                "last_name": lastName,
                "phone_number": None,
                "email": None,
                "devices": [],
                "files": [],
            }

            try:
                user_collection.insert_one(new_user)
                message = f"User '{username}' added successfully."
            except pymongo.errors.OperationFailure as e:
                message = f"An error occurred: {e}"

            return render(request, "user_added.html", {"message": message})

    else:
        form = UserForm()

    return render(request, "add_user.html", {"form": form})


@api_view(["GET"])
def login(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"].encode("utf-8")

            user = user_collection.find_one({"username": username})

            if user and bcrypt.checkpw(password, user["password"]):
                return redirect(
                    "dashboard", username=username
                )  # Redirect to a home page or dashboard
            else:
                return render(
                    request,
                    "login.html",
                    {"form": form, "error": "Invalid username or password"},
                )
    else:
        form = LoginForm()

    return render(request, "login.html", {"form": form})


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["GET"])
def login_api(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    # Ensure the request body is JSON
    try:
        data = json.loads(request.body)

        # extract username and password from the JSON data
        username = data.get("username")
        password = data.get("password").encode("utf-8")

        user = user_collection.find_one({"username": username})

        if user and bcrypt.checkpw(password, user["password"]):
            return JsonResponse({"response": "success"})
        else:
            return JsonResponse({"response": "fail"})

    except ValueError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@api_view(["GET"])
def dashboard(request, username):
    # Render the dashboard template with the username
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    user = user_collection.find_one({"username": username})
    first_name = user.get(
        "first_name", "User"
    )  # Default to 'User' if first name is not set
    files = user.get("files", "files")  # Default to 'User' if first name is not set
    devices = user.get(
        "devices", "devices"
    )  # Default to 'User' if first name is not set
    return render(
        request,
        "dashboard.html",
        {
            "username": username,
            "first_name": first_name,
            "files": files,
            "devices": devices,
        },
    )


@api_view(["GET"])
def update_user_profile(request, username):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = pymongo.MongoClient(uri, server_api=ServerApi("1"))
    db = client["myDatabase"]
    user_collection = db["users"]

    user = user_collection.find_one({"username": username})

    if request.method == "POST":
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "first_name": form.cleaned_data["first_name"]
                        or user["first_name"],
                        "last_name": form.cleaned_data["last_name"]
                        or user["last_name"],
                        "phone_number": form.cleaned_data["phone_number"]
                        or user["phone_number"],
                        "email": form.cleaned_data["email"] or user["email"],
                    }
                },
            )
            return redirect("dashboard", username=username)
    else:
        form = UserProfileForm(initial=user)

    return render(request, "update_profile.html", {"form": form, "username": username})


@api_view(["GET"])
def file_sync_view(request, username):
    response_data, status_code = get_file_sync(username)
    return JsonResponse(response_data, status=status_code)
