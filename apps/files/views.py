from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import bcrypt
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from ..forms import LoginForm
import requests
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .delete_files import delete_files
from .get_files_from_filepath import get_files_from_filepath as db_get_files_from_filepath
from .update_files import update_files
from websocket.utils import broadcast_new_file

import pymongo
import json
import re


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