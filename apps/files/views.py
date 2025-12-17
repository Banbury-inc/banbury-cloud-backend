from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
from rest_framework.decorators import authentication_classes
from .delete_files import delete_files
from .get_files_from_filepath import get_files_from_filepath as db_get_files_from_filepath
from .update_files import update_files
from .get_file_info import get_file_info as db_get_file_info
from websocket.utils import broadcast_new_file
from .get_shared_files import get_shared_files as db_get_shared_files
from .upload_to_s3 import upload_file_to_s3
from .list_s3_files import list_s3_files
from .search_s3_files import search_s3_files
from .download_s3_file import download_s3_file
from .delete_s3_file import delete_s3_file, delete_multiple_s3_files
from .update_s3_file import update_s3_file
from .google_drive_service import (
    list_drive_files, download_drive_file, upload_drive_file,
    create_drive_file, update_drive_file, delete_drive_file,
    check_user_drive_credentials, remove_user_drive_credentials, update_user_drive_credentials
)
import json
import re
import boto3
from django.core.files.uploadedfile import UploadedFile
import os
from datetime import datetime, timedelta
import base64
from botocore.exceptions import ClientError
import jwt


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@authentication_classes([])
def add_file(request):
    """
    Adds metadata for a single file to the database for a given user and device.

    Expects a POST request with a JSON body containing file details:
    - file_type (str)
    - file_name (str)
    - file_path (str)
    - date_uploaded (str/datetime)
    - date_modified (str/datetime)
    - file_size (int)
    - file_priority (any)
    - file_parent (str)
    - original_device (str): Name of the device uploading the file.
    - kind (str)

    URL Parameters:
        username (str): The username associated with the file.

    Returns:
        JsonResponse:
            - On Success: {"result": "success", "username": username}. Broadcasts the new file via websocket.
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"result": "device_not_found", "message": "Device not found."}
                - {"result": "object_id_not_found", "message": "Device id not found."}
                - If DB insert fails (prints error, returns success response but DB might be inconsistent).
    """
    try:
        username = request.username_from_token
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
    user_collection = db["users"]

    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found"}, status=404)

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
        "user_id": user["_id"],
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

    username = request.username_from_token
    user_data = {
        "result": result,
        "username": username,  # Return username if success, None if fail
    }

    result = broadcast_new_file(new_file)

    return JsonResponse(user_data)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def add_files(request):
    """
    Adds metadata for multiple files to the database for a given user and device.

    Expects a POST request with a JSON body containing:
    - files (list): A list of file metadata dictionaries. Each dictionary should contain:
        - file_name (str, required)
        - file_path (str, required)
        - file_type (str, optional)
        - file_size (int, optional)
        - date_uploaded (str/datetime, optional)
        - date_modified (str/datetime, optional)
        - file_parent (str, optional)
        - original_device (str, optional)
        - kind (str, optional)
        - shared_with (list, optional)
        - is_public (bool, optional)
    - device_name (str, required): The name of the device associated with these files.

    URL Parameters:
        username (str): The username associated with the files.

    Returns:
        JsonResponse:
            - On Success: {"result": "success", "message": "X files added successfully."}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "Missing files or device_name"}, status=400
                - {"result": "device_not_found", "message": "Device not found."}
                - {"result": "object_id_not_found", "message": "Device ID not found."}
                - {"error": "Invalid file data format: ..."}, status=400 (if a file item is not a dict)
                - {"error": "Missing fields: ['field_name', ...]"}, status=401 (if required fields missing in a file item)
                - {"result": "no_files_to_add", "message": "No valid files to add."}
                - {"result": "failure", "message": "Error inserting files: ..."}, status=500
    """
    try:
        # Parse the JSON body
        data = json.loads(request.body)
        username = request.username_from_token
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
    user_collection = db["users"]
    file_collection = db["files"]
    device_collection = db["devices"]
    # Find the device_id based on device_name and matching user_id
    user = user_collection.find_one({"username": username})
    device = device_collection.find_one({"device_name": device_name, "user_id": user["_id"]})
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
            "user_id": user["_id"],
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
            "shared_with": file_data.get("shared_with"),
            "is_public": file_data.get("is_public"),
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
def handle_delete_files(request):
    """
    Handles the deletion of metadata for multiple files associated with a user and device.

    Delegates the core deletion logic to the `delete_files` utility function.

    Expects a POST request with a JSON body containing:
    - files (list): A list of file identifiers (e.g., paths or IDs) to be deleted.
    - device_name (str): The name of the device associated with these files.

    URL Parameters:
        username (str): The username initiating the deletion.

    Returns:
        JsonResponse: Based on the result from `delete_files`:
            - {"result": "success", "message": "Files deleted successfully."}
            - {"result": "device_not_found", "message": "Device not found."}
            - {"result": "device_id_not_found", "message": "Device id not found."}
            - {"error": "Invalid JSON"}, status=400
            - {"error": "Missing files or device_name"}, status=400
    """
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
    username = request.username_from_token
    response = delete_files(device_name, files)
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
    if response == "invalid_files":
        return JsonResponse({
            "result": "invalid_files",
            "message": "Invalid files format.",
        })
    if response == "no_files_to_delete":
        return JsonResponse({
            "result": "no_files_to_delete",
            "message": "No files to delete.",
        })
    if response == "no_files_deleted":
        return JsonResponse({
            "result": "no_files_deleted",
            "message": "No files were deleted.",
        })
    if response == "success":
        return JsonResponse({
            "result": "success",
            "message": "Files deleted successfully.",
        })
    
    # Handle any unexpected responses
    return JsonResponse({
        "result": "error",
        "message": f"Unexpected response: {response}",
    })



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def handle_update_files(request):
    """
    Handles the update of metadata for multiple files associated with a user and device.

    Delegates the core update logic to the `update_files` utility function.

    Expects a POST request with a JSON body containing:
    - files (list): A list of file objects, each containing the updated metadata
                    (structure depends on `update_files` implementation).
    - device_name (str): The name of the device associated with these files.

    URL Parameters:
        username (str): The username initiating the update.

    Returns:
        JsonResponse: Based on the result from `update_files`:
            - {"result": "success", "message": "Files updated successfully."} (Note: Message says "deleted" currently)
            - {"result": "device_not_found", "message": "Device not found."}
            - {"result": "device_id_not_found", "message": "Device id not found."}
            - {"error": "Invalid JSON"}, status=400
            - {"error": "Missing files or device_name"}, status=400
    """
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

    username = request.username_from_token
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
            "message": "Files updated successfully.", # Corrected message
        })




def getfileinfo(request):
    """
    Retrieves metadata for all files associated with all devices for a given user.

    Iterates through all devices linked to the user and collects metadata for all
    files associated with each device.

    URL Parameters:
        username (str): The username whose files are to be retrieved.

    Returns:
        JsonResponse:
            - On Success: {"files": [list_of_file_metadata_dicts]}
              Each file metadata dictionary contains keys like:
              "file_name", "file_size", "file_type", "file_path", "date_uploaded",
              "date_modified", "date_accessed", "kind", "device_name".
            - On Error:
                - {"error": "Please login first."}, status=401 (If user not found)
    """
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    file_collection = db["files"]

    # Find the user by username
    username = request.username_from_token
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
def get_files_from_filepath(request):
    """
    Retrieves files located under a specific 'global_file_path' for a user.

    Delegates the retrieval logic to `db_get_files_from_filepath`.

    Expects a POST request with a JSON body containing:
    - global_file_path (str): The base path to search within. If missing or null,
                               defaults to an empty path ("").

    URL Parameters:
        username (str): The username whose files are being queried.

    Returns:
        JsonResponse:
            - On Success (from `db_get_files_from_filepath`): {"result": "success", "files": [list_of_files]}
            - On Error:
                - {"result": "error", "message": "Empty request body"}, status=400
                - {"result": "error", "message": "Invalid JSON format: ..."}, status=400
                - {"result": "error", "message": "No files found or invalid response format"}, status=404
                - {"result": "error", "message": "Server error: ..."}, status=500 (Generic server error)
                - Potentially other errors returned directly from `db_get_files_from_filepath` if it returns a JsonResponse.
    """
    try:
        # Check if request body is empty
        if not request.body:
            return JsonResponse({
                "result": "error",
                "message": "Empty request body"
            }, status=400)

        data = json.loads(request.body)
        filepath = data.get("global_file_path")
        
        # Handle case where filepath might be None
        if filepath is None:
            filepath = ""  # or "Core" depending on your default behavior
        
        username = request.username_from_token
        response = db_get_files_from_filepath(username, filepath)
        
        # Check if response is a JsonResponse object
        if isinstance(response, JsonResponse):
            return response
            
        # Handle the response data
        if response and 'files' in response:
            return JsonResponse({
                "result": "success",
                "files": response['files']
            })
        else:
            return JsonResponse({
                "result": "error",
                "message": "No files found or invalid response format"
            }, status=404)

    except json.JSONDecodeError as e:
        return JsonResponse({
            "result": "error",
            "message": f"Invalid JSON format: {str(e)}"
        }, status=400)
    except Exception as e:
        print(f"Error in get_files_from_filepath: {str(e)}")  # Log the error
        return JsonResponse({
            "result": "error",
            "message": f"Server error: {str(e)}"
        }, status=500)




@csrf_exempt
@require_http_methods(["POST"])
def paginated_get_files_info(request):
    """
    Retrieves paginated file information for a user.

    *** WARNING: THIS ENDPOINT CURRENTLY CAUSES INFINITE RECURSION. ***
    It calls itself instead of fetching data with pagination parameters.
    Needs to be refactored to call a database query function with limit/skip.

    Expects a POST request with a JSON body optionally containing:
    - page (int, optional, default=1): The page number to retrieve.
    - items_per_page (int, optional, default=10): The number of items per page.

    URL Parameters:
        username (str): The username whose files are being queried.

    Returns:
        JsonResponse:
            - Intended: Paginated file information.
            - Actual: Infinite recursion leading to server error/timeout.
            - On Error: {"error": "Invalid JSON"}, status=400
    """
    try:
        data = json.loads(request.body)
        page = data.get("page", 1)
        items_per_page = data.get("items_per_page", 10)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    
    username = request.username_from_token
    return paginated_get_files_info(username, page=page, items_per_page=items_per_page)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
def get_partial_file_info(request):
    """
    Retrieves file metadata within a specified folder path up to a maximum depth.

    Finds all devices for the user, then queries the files collection for each device,
    filtering by a regex constructed from the `folder_path` and `max_depth`.

    Expects a POST request with a JSON body containing:
    - folder_path (str): The base folder path to search within.
    - max_depth (int, optional, default=4): The maximum directory depth relative
                                            to `folder_path` to include results from.

    URL Parameters:
        username (str): The username whose files are being queried.

    Returns:
        JsonResponse:
            - On Success: {"files": [list_of_matching_file_metadata_dicts]}
              File metadata includes: "file_name", "file_size", "file_type", "file_path",
              "date_uploaded", "date_modified", "date_accessed", "kind", "device_name".
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404
    """
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
    username = request.username_from_token
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
def search_file(request):
    """
    Searches for a specific file by name on a specific device for a user.

    Expects a POST request with a JSON body containing:
    - device_name (str, required): The name of the device to search on.
    - file_name (str, required): The exact name of the file to search for.

    URL Parameters:
        username (str): The username associated with the device/file (though not directly used in the query).

    Returns:
        JsonResponse (always status 200, even for 'not found' results):
            - On Success: {"result": "success", "file": file_metadata_dict}
              File metadata includes: "file_name", "file_path", "file_size", "file_type",
              "date_uploaded", "date_modified", "file_parent", "original_device", "kind".
            - If Device Not Found: {"result": "device_not_found", "message": "Device not found."}
            - If Device ID Missing: {"result": "object_id_not_found", "message": "Device ID not found."}
            - If File Not Found: {"result": "file_not_found", "message": "File not found for the given device."}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "Missing device_name or file_name"}, status=400
    """
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
def add_scanned_folder(request):
    """
    Adds a folder path to the list of scanned folders for a specific user's device.

    Finds the user and the specified device, then adds the given folder path
    to the 'scanned_folders' array field in the device's document. Initializes
    'scanned_folders' as an empty array if it doesn't exist or isn't a list.

    Expects a POST request with a JSON body containing:
    - device_name (str, required): The name of the device to update.
    - scanned_folder (str, required): The folder path to add.

    URL Parameters:
        username (str): The username who owns the device.

    Returns:
        JsonResponse:
            - On Success: {"result": "success", "username": username}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404
                - {"error": "Device not found."}, status=404
                - {"error": "Failed to update device status."}, status=500 (If DB update fails)
    """
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
    username = request.username_from_token
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
    username = request.username_from_token
    user_data = {"result": "success", "username": username}

    return JsonResponse(user_data)



@csrf_exempt
@require_http_methods(["POST"])
def remove_scanned_folder(request):
    """
    Removes a folder path from the list of scanned folders for a specific user's device.

    Finds the user and the specified device, then removes the given folder path
    from the 'scanned_folders' array field using MongoDB's $pull operator.

    Expects a POST request with a JSON body containing:
    - device_name (str, required): The name of the device to update.
    - scanned_folder (str, required): The folder path to remove.

    URL Parameters:
        username (str): The username who owns the device.

    Returns:
        JsonResponse:
            - If Removed: {"status": "success", "message": "Folder removed successfully"}
            - If Not Found in Array: {"status": "not_found", "message": "Folder not found in scanned_folders"}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404
                - {"error": "Device not found."}, status=404
    """
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
    username = request.username_from_token
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
def get_scanned_folders(request):
    """
    Retrieves the list of scanned folders for a specific user's device.

    Finds the user and the specified device, then returns the 'scanned_folders'
    array field from the device's document. Defaults to an empty list if the
    field doesn't exist.

    Expects a POST request with a JSON body containing:
    - device_name (str, required): The name of the device whose scanned folders are requested.

    URL Parameters:
        username (str): The username who owns the device.

    Returns:
        JsonResponse:
            - On Success: {"result": "success", "scanned_folders": [list_of_folder_paths]}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404
                - {"error": "Device not found."}, status=404
    """
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
    username = request.username_from_token
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
def share_file(request):
    """
    Shares a file owned by 'username' with 'friend_username'.

    Finds the user initiating the share ('username'), the user to share with
    ('friend_username'), and the file ('file_name'). Adds the friend's user ID
    to the file's 'shared_with' array field using MongoDB's $addToSet operator
    (ensures uniqueness).

    Note: This currently finds *any* file matching `file_name`, not necessarily
          one owned by 'username' or associated with a specific device. This might
          need refinement depending on desired behavior.

    Expects a POST request with JSON body containing:
    - file_name (str, required): The name of the file to share.
    - username (str, required): The username of the file owner initiating the share.
    - friend_username (str, required): The username of the user to share the file with.

    Returns:
        JsonResponse:
            - On Success: {"status": "success", "message": "File shared successfully"}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404 (If 'username' not found)
                - {"error": "Friend not found."}, status=404 (If 'friend_username' not found)
                - {"error": "File not found."}, status=404 (If 'file_name' not found)
    """
    try:
        data = json.loads(request.body)
        file_name = data.get("file_name")
        username = data.get("username")
        friend_username = data.get("friend_username")


        # MongoDB connection
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

        # Find the friend by username
        friend = user_collection.find_one({"username": friend_username})
        if not friend:
            return JsonResponse({"error": "Friend not found."}, status=404)

        # Find the file by file_name
        file = file_collection.find_one({"file_name": file_name})
        if not file:
            return JsonResponse({"error": "File not found."}, status=404)
        

        file_collection.update_one(
            {"file_name": file_name},
            {"$addToSet": {"shared_with": friend["_id"]}}
        )
        return JsonResponse({"status": "success", "message": "File shared successfully"})


    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def make_file_public(request):
    """
    Sets the 'is_public' flag to True for a specific file associated with a user's device.

    Finds the user, the device, and the file. Updates the file document, setting
    'is_public' to True, ensuring the update targets the file matching both
    'file_name' and the found 'device_id'.

    Expects a POST request with JSON body containing:
    - file_name (str, required): The name of the file to make public.
    - username (str, required): The username of the file owner.
    - device_name (str, required): The name of the device the file belongs to.

    Returns:
        JsonResponse:
            - On Success: {"status": "success", "message": "File made public successfully"}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404
                - {"error": "Device not found."}, status=404 (Implicitly, as device["_id"] would fail)
                - {"error": "File not found."}, status=404 (If file_name doesn't match any file, even if device exists)
                - Potential KeyError if device is found but lacks "_id".
    """
    try:
        data = json.loads(request.body)
        file_name = data.get("file_name")
        username = data.get("username")
        device_name = data.get("device_name")


        # MongoDB connection
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

        device = device_collection.find_one({"user_id": user["_id"], "device_name": device_name})

        print(device)
        print()


        # Find the file by file_name
        file = file_collection.find_one({"file_name": file_name})
        if not file:
            return JsonResponse({"error": "File not found."}, status=404)

        print(file)
        

        file_collection.update_one(
            {"file_name": file_name, "device_id": device["_id"]},
            {"$set": {"is_public": True}}
        )


        return JsonResponse({"status": "success", "message": "File made public successfully"})


    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)



@csrf_exempt
@require_http_methods(["POST"])
def make_file_private(request):
    """
    Sets the 'is_public' flag to False for a specific file associated with a user's device.

    Finds the user, the device, and the file. Updates the file document, setting
    'is_public' to False, ensuring the update targets the file matching both
    'file_name' and the found 'device_id'.

    Expects a POST request with JSON body containing:
    - file_name (str, required): The name of the file to make private.
    - username (str, required): The username of the file owner.
    - device_name (str, required): The name of the device the file belongs to.

    Returns:
        JsonResponse:
            - On Success: {"status": "success", "message": "File made private successfully"}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - {"error": "User not found."}, status=404
                - {"error": "Device not found."}, status=404 (Implicitly, as device["_id"] would fail)
                - {"error": "File not found."}, status=404 (If file_name doesn't match any file, even if device exists)
                - Potential KeyError if device is found but lacks "_id".
    """
    try:
        data = json.loads(request.body)
        file_name = data.get("file_name")
        device_name = data.get("device_name")
        username = data.get("username")


        # MongoDB connection
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

        device = device_collection.find_one({"user_id": user["_id"], "device_name": device_name})
        # Find the file by file_name
        file = file_collection.find_one({"file_name": file_name})
        if not file:
            return JsonResponse({"error": "File not found."}, status=404)
        

        file_collection.update_one(
            {"file_name": file_name, "device_id": device["_id"]},
            {"$set": {"is_public": False}}
        )
        return JsonResponse({"status": "success", "message": "File made private successfully"})


    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_shared_files(request):
    """
    Retrieves metadata for files shared with the specified user.

    Delegates the core logic to the `db_get_shared_files` utility function.

    Expects a POST request with JSON body containing:
    - username (str, required): The username whose shared files are being requested.

    Returns:
        JsonResponse:
            - On Success: {"status": "success", "shared_files": [list_of_shared_file_metadata]}
              (The structure of metadata depends on `db_get_shared_files` implementation).
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - Potential errors from `db_get_shared_files` if it raises exceptions (not explicitly handled here).
    """
    try:
        data = json.loads(request.body)
        username = data.get("username")
        shared_files = db_get_shared_files(username)
        return JsonResponse({"status": "success", "shared_files": shared_files})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def get_shared_files_from_filepath(request):
    """
    Retrieves shared files under a specific filepath for the specified user.

    *** WARNING: This endpoint calls a function `get_shared_files_from_filepath` which is
          likely undefined or not imported in the current context. ***
    It needs to be implemented or imported correctly.

    Expects a POST request with JSON body containing:
    - username (str, required): The username whose shared files are being requested.
    - filepath (str, required): The specific file path to filter shared files by.

    Returns:
        JsonResponse:
            - On Success (if helper function works): {"status": "success", "shared_files": [list_of_filtered_shared_files]}
            - On Error:
                - {"error": "Invalid JSON"}, status=400
                - NameError if `get_shared_files_from_filepath` is not defined.
    """
    try:
        data = json.loads(request.body)
        username = data.get("username")
        filepath = data.get("filepath")
        shared_files = get_shared_files_from_filepath(username, filepath)
        return JsonResponse({"status": "success", "shared_files": shared_files})
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_drive_list_files(request):
    """
    List files from Google Drive for the authenticated user.
    
    Query Parameters:
        page_token (str, optional): Token for pagination
        folder_id (str, optional): ID of specific folder to list
        query (str, optional): Search query for files
        
    Returns:
        JsonResponse: List of files from Google Drive
    """
    username = request.username_from_token
    page_token = request.GET.get('page_token')
    folder_id = request.GET.get('folder_id')
    query = request.GET.get('query')
    
    result = list_drive_files(username, page_token, folder_id, query)
    
    if isinstance(result, JsonResponse):
        return result
    
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_drive_download_file(request, file_id):
    """
    Download a file from Google Drive.
    
    URL Parameters:
        file_id (str): The Google Drive file ID to download
        
    Returns:
        HttpResponse: The file content for download
        or
        JsonResponse: Error details if download fails
    """
    username = request.username_from_token
    return download_drive_file(username, file_id)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def google_drive_upload_file(request):
    """
    Upload a file to Google Drive.
    
    Expects a multipart form data request containing:
    - file: The file to upload
    - parent_folder_id (str, optional): ID of parent folder
    
    Returns:
        JsonResponse: Result of the upload operation
    """
    username = request.username_from_token
    
    if 'file' not in request.FILES:
        return JsonResponse({"error": "No file provided."}, status=400)
    
    uploaded_file = request.FILES['file']
    parent_folder_id = request.POST.get('parent_folder_id')
    
    if not isinstance(uploaded_file, UploadedFile):
        return JsonResponse({"error": "Invalid file format."}, status=400)
    
    # Create a file-like object from the uploaded file
    file_obj = uploaded_file.open()
    
    result = upload_drive_file(username, file_obj, uploaded_file.name, parent_folder_id)
    
    if isinstance(result, JsonResponse):
        return result
    
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def google_drive_create_file(request):
    """
    Create a new file in Google Drive with content.
    
    Expects a POST request with JSON body containing:
    - filename (str): Name of the file to create
    - content (str): Content of the file
    - mime_type (str, optional): MIME type of the file (default: text/plain)
    - parent_folder_id (str, optional): ID of parent folder
    
    Returns:
        JsonResponse: Result of the create operation
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        filename = data.get('filename')
        content = data.get('content')
        mime_type = data.get('mime_type', 'text/plain')
        parent_folder_id = data.get('parent_folder_id')
        
        if not filename or content is None:
            return JsonResponse({"error": "Filename and content are required."}, status=400)
        
        result = create_drive_file(username, filename, content, mime_type, parent_folder_id)
        
        if isinstance(result, JsonResponse):
            return result
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
@authentication_classes([])
def google_drive_update_file(request, file_id):
    """
    Update an existing file in Google Drive.
    
    URL Parameters:
        file_id (str): The Google Drive file ID to update
    
    Expects a PUT request with JSON body containing:
    - content (str, optional): New content for the file
    - filename (str, optional): New name for the file
    
    Returns:
        JsonResponse: Result of the update operation
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        content = data.get('content')
        filename = data.get('filename')
        
        result = update_drive_file(username, file_id, content, filename)
        
        if isinstance(result, JsonResponse):
            return result
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
@authentication_classes([])
def google_drive_delete_file(request, file_id):
    """
    Delete a file from Google Drive.
    
    URL Parameters:
        file_id (str): The Google Drive file ID to delete
        
    Returns:
        JsonResponse: Result of the delete operation
    """
    username = request.username_from_token
    
    result = delete_drive_file(username, file_id)
    
    if isinstance(result, JsonResponse):
        return result
    
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def upload_to_s3(request):
    """
    Wrapper for the upload_file_to_s3 function in upload_to_s3.py.
    
    Uploads a file to an Amazon S3 bucket and stores metadata in MongoDB.
    See the upload_file_to_s3 function documentation for details.
    """
    username = request.username_from_token
    return upload_file_to_s3(request, username)


@csrf_exempt
@require_http_methods(["GET"])
def get_s3_files(request):
    """
    Retrieves all S3 files for a specific user.
    
    URL Parameters:
        username (str): The username whose S3 files to list
        
    Returns:
        JsonResponse: A list of files stored in S3 for the user
    """
    username = request.username_from_token
    result = list_s3_files(username)
    
    if "error" in result:
        return JsonResponse({"error": result["error"]}, status=result.get("status_code", 500))
    
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def search_s3_files_view(request):
    """
    Searches S3 files for a specific user by query string.
    
    Expects a POST request with JSON body containing:
    - query (str): The search query to match against file names
        
    Returns:
        JsonResponse: A list of matching files stored in S3 for the user
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        query = data.get("query")
        
        if not query:
            return JsonResponse({"error": "Missing query parameter"}, status=400)
        
        result = search_s3_files(username, query)
        
        if "error" in result:
            return JsonResponse({"error": result["error"]}, status=result.get("status_code", 500))
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def download_s3_file_view(request, file_id):
    """
    Downloads a file from S3 for a specific user.
    
    URL Parameters:
        username (str): The username requesting the download
        file_id (str): The ID of the file to download
        
    Returns:
        HttpResponse: The file content for download
        or
        JsonResponse: Error details if download fails
    """
    username = request.username_from_token
    return download_s3_file(username, file_id)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_s3_file_view(request, file_id):
    """
    Deletes a file from S3 and removes its metadata from MongoDB.
    
    URL Parameters:
        file_id (str): The ID of the file to delete
        
    Returns:
        JsonResponse: Result of the delete operation
    """
    username = request.username_from_token
    result = delete_s3_file(username, file_id)
    
    if "error" in result:
        return JsonResponse({"error": result["error"]}, status=result.get("status_code", 500))
    
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
def delete_multiple_s3_files_view(request):
    """
    Deletes multiple files from S3 and removes their metadata from MongoDB.
    
    Expects a POST request with JSON body containing:
    - file_ids (list): List of file IDs to delete
        
    Returns:
        JsonResponse: Result of the delete operations
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        file_ids = data.get("file_ids")
        
        if not file_ids or not isinstance(file_ids, list):
            return JsonResponse({"error": "Missing or invalid file_ids"}, status=400)
        
        result = delete_multiple_s3_files(username, file_ids)
        
        if result["result"] == "error":
            return JsonResponse({"error": result["message"]}, status=500)
        
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def update_s3_file_view(request, file_id):
    """
    Updates a file in S3 and its metadata in MongoDB.
    
    URL Parameters:
        file_id (str): The ID of the file to update
        
    For file updates (multipart/form-data):
        - file: The new file to upload (optional)
        - Additional form fields for metadata updates
        
    For metadata-only updates (JSON):
        - file_name (str, optional): New file name
        - metadata (dict, optional): Additional metadata
        - tags (list, optional): File tags
        - description (str, optional): File description
        
    Returns:
        JsonResponse: Result of the update operation
    """
    username = request.username_from_token
    return update_s3_file(username, file_id, request)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_drive_check_credentials(request):
    """
    Check if the user has Google Drive credentials stored.
    
    Returns:
        JsonResponse: Status of user's Google Drive credentials
    """
    username = request.username_from_token
    result = check_user_drive_credentials(username)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["DELETE"])
@authentication_classes([])
def google_drive_remove_credentials(request):
    """
    Remove Google Drive credentials for the authenticated user.
    
    Returns:
        JsonResponse: Result of the credential removal operation
    """
    username = request.username_from_token
    result = remove_user_drive_credentials(username)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_drive_oauth_callback(request):
    """
    Handle Google Drive OAuth callback specifically for integration (not login).
    This is separate from the main login OAuth flow.
    """
    code = request.GET.get("code")
    
    if not code:
        return JsonResponse({
            "success": False,
            "error": "No authorization code provided"
        }, status=400)
    
    try:
        # Get the username from the token in the request
        username = request.username_from_token
        
        if not username:
            return JsonResponse({
                "success": False,
                "error": "Authentication required"
            }, status=401)
        
        # Get Google OAuth configuration
        from apps.authentication.views import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
        from google_auth_oauthlib.flow import Flow
        
        # Define the Google Drive, Gmail, and Calendar scopes
        DRIVE_SCOPES = [
            "https://www.googleapis.com/auth/userinfo.profile",
            "https://www.googleapis.com/auth/userinfo.email",
            "https://www.googleapis.com/auth/drive",
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/gmail.modify",
            "https://www.googleapis.com/auth/calendar",
            "openid"
        ]
        
        # Use a consistent redirect URI (match what frontend sends)
        redirect_uri = 'http://localhost:3000/files/google_drive/oauth_callback'
        
        # Create OAuth flow
        flow_instance = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri],
                }
            },
            scopes=DRIVE_SCOPES
        )
        flow_instance.redirect_uri = redirect_uri
        
        # Exchange the authorization code for credentials
        flow_instance.fetch_token(code=code)
        credentials = flow_instance.credentials
        
        # Store the credentials for the authenticated user
        update_user_drive_credentials(username, credentials)
        
        return JsonResponse({
            "success": True,
            "message": "Google Drive integration enabled successfully"
        })
        
    except Exception as e:
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=400)


# =============================================================================
# Gmail API Views
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_search(request):
    """
    Search for emails using Gmail API.
    
    Query Parameters:
        q: Gmail search query
        maxResults: Maximum number of results (default: 10)
    """
    username = request.username_from_token
    query = request.GET.get('q', '')
    max_results = int(request.GET.get('maxResults', 10))
    
    if not query:
        return JsonResponse({
            "error": "Search query is required"
        }, status=400)
    
    from .gmail_service import search_emails
    result = search_emails(username, query, max_results)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_get_message(request, message_id):
    """
    Get a specific email message by ID.
    """
    username = request.username_from_token
    
    from .gmail_service import get_message
    result = get_message(username, message_id)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_get_thread(request, thread_id):
    """
    Get an email thread by ID.
    """
    username = request.username_from_token
    
    from .gmail_service import get_thread
    result = get_thread(username, thread_id)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def gmail_create_draft(request):
    """
    Create a draft email.
    
    Expected JSON payload:
    {
        "to": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "cc": "cc@example.com" (optional),
        "bcc": "bcc@example.com" (optional)
    }
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        
        if not to or not subject or not body:
            return JsonResponse({
                "error": "Missing required fields: to, subject, body"
            }, status=400)
        
        from .gmail_service import create_draft
        result = create_draft(username, to, subject, body, cc, bcc)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def gmail_send_message(request):
    """
    Send an email message.
    
    Expected JSON payload:
    {
        "to": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "cc": "cc@example.com" (optional),
        "bcc": "bcc@example.com" (optional)
    }
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        in_reply_to = data.get('in_reply_to')
        references = data.get('references')
        thread_id = data.get('thread_id')
        raw_attachments = data.get('attachments') or []
        attachments = []
        # attachments expected as list of { filename, mimeType, content }
        if isinstance(raw_attachments, list):
            for att in raw_attachments:
                try:
                    filename = att.get('filename')
                    mime_type = att.get('mimeType') or att.get('mime_type')
                    content_b64 = att.get('content')
                    if content_b64 is None:
                        continue
                    content_bytes = base64.b64decode(content_b64)
                    attachments.append({
                        'filename': filename,
                        'mime_type': mime_type,
                        'content': content_bytes,
                    })
                except Exception as e:
                    # Skip bad attachment entries
                    print(f"Attachment parse error: {e}")
        
        if not to or not subject or not body:
            return JsonResponse({
                "error": "Missing required fields: to, subject, body"
            }, status=400)
        
        from .gmail_service import send_message
        result = send_message(username, to, subject, body, cc, bcc, in_reply_to, references, thread_id, attachments)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_check_access(request):
    """
    Check if user has Gmail access through existing Google credentials.
    """
    username = request.username_from_token
    
    from .gmail_service import check_gmail_access
    result = check_gmail_access(username)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def gmail_send_reply(request):
    """
    Send a reply to an existing email message with proper threading.
    
    Expected JSON payload:
    {
        "original_message_id": "message_id_to_reply_to",
        "to": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "cc": "cc@example.com" (optional),
        "bcc": "bcc@example.com" (optional)
    }
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        original_message_id = data.get('original_message_id')
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        raw_attachments = data.get('attachments') or []
        attachments = []
        if isinstance(raw_attachments, list):
            for att in raw_attachments:
                try:
                    filename = att.get('filename')
                    mime_type = att.get('mimeType') or att.get('mime_type')
                    content_b64 = att.get('content')
                    if content_b64 is None:
                        continue
                    content_bytes = base64.b64decode(content_b64)
                    attachments.append({
                        'filename': filename,
                        'mime_type': mime_type,
                        'content': content_bytes,
                    })
                except Exception as e:
                    print(f"Attachment parse error: {e}")
        
        if not original_message_id or not to or not subject or not body:
            return JsonResponse({
                "error": "Missing required fields: original_message_id, to, subject, body"
            }, status=400)
        
        from .gmail_service import send_reply
        result = send_reply(username, original_message_id, to, subject, body, cc, bcc, attachments)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_get_thread(request):
    """
    Get a specific thread with all its messages.
    
    Query Parameters:
        thread_id: The ID of the thread to retrieve
    """
    username = request.username_from_token
    thread_id = request.GET.get('thread_id')
    
    if not thread_id:
        return JsonResponse({
            "error": "Missing required parameter: thread_id"
        }, status=400)
    
    from .gmail_service import get_thread
    result = get_thread(username, thread_id)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_list_threads(request):
    """
    List threads with optional query filtering.
    
    Query Parameters:
        q: Search query (optional)
        maxResults: Maximum number of threads to return (default: 10)
    """
    username = request.username_from_token
    query = request.GET.get('q')
    max_results = int(request.GET.get('maxResults', 10))
    
    from .gmail_service import list_threads
    result = list_threads(username, query, max_results)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def gmail_get_signature(request):
    """
    Get the user's Gmail signature from their account settings.
    """
    username = request.username_from_token
    
    from .gmail_service import get_email_signature
    result = get_email_signature(username)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def gmail_send_message_with_signature(request):
    """
    Send an email with the user's signature automatically added.
    
    Expected JSON payload:
    {
        "to": "recipient@example.com",
        "subject": "Email subject",
        "body": "Email body content",
        "cc": "cc@example.com" (optional),
        "bcc": "bcc@example.com" (optional),
        "isDraft": false (optional)
    }
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        to = data.get('to')
        subject = data.get('subject')
        body = data.get('body')
        cc = data.get('cc')
        bcc = data.get('bcc')
        is_draft = data.get('isDraft', False)
        raw_attachments = data.get('attachments') or []
        attachments = []
        if isinstance(raw_attachments, list):
            for att in raw_attachments:
                try:
                    filename = att.get('filename')
                    mime_type = att.get('mimeType') or att.get('mime_type')
                    content_b64 = att.get('content')
                    if content_b64 is None:
                        continue
                    content_bytes = base64.b64decode(content_b64)
                    attachments.append({
                        'filename': filename,
                        'mime_type': mime_type,
                        'content': content_bytes,
                    })
                except Exception as e:
                    print(f"Attachment parse error: {e}")
        
        if not is_draft and (not to or not subject or not body):
            return JsonResponse({
                "error": "Missing required fields: to, subject, body (unless isDraft is true)"
            }, status=400)
        
        from .gmail_service import send_message_with_signature
        result = send_message_with_signature(username, to, subject, body, cc, bcc, is_draft, attachments)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


# =============================================================================
# Google Calendar API Views
# =============================================================================

@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_calendar_check_access(request):
    """
    Check if user has Google Calendar access through existing Google credentials.
    """
    username = request.username_from_token
    
    from .google_calendar_service import check_calendar_access
    result = check_calendar_access(username)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_calendar_list_events(request):
    """
    List calendar events from Google Calendar.
    
    Query Parameters:
        timeMin: Lower bound for event start time (RFC3339 timestamp)
        timeMax: Upper bound for event start time (RFC3339 timestamp)
        maxResults: Maximum number of events to return (default: 50)
        q: Free text search terms
        calendarId: Calendar identifier (default: 'primary')
    """
    username = request.username_from_token
    
    calendar_id = request.GET.get('calendarId', 'primary')
    time_min = request.GET.get('timeMin')
    time_max = request.GET.get('timeMax')
    max_results = int(request.GET.get('maxResults', 50))
    q = request.GET.get('q')
    
    from .google_calendar_service import list_calendar_events
    result = list_calendar_events(username, calendar_id, time_min, time_max, max_results, q)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["GET"])
@authentication_classes([])
def google_calendar_get_event(request, calendar_id, event_id):
    """
    Get details of a specific calendar event.
    """
    username = request.username_from_token
    
    from .google_calendar_service import get_calendar_event
    result = get_calendar_event(username, event_id, calendar_id)
    return JsonResponse(result)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def google_calendar_create_event(request):
    """
    Create a new calendar event.
    
    Expected JSON payload:
    {
        "summary": "Event title",
        "start": {"dateTime": "2024-01-01T10:00:00-07:00"},
        "end": {"dateTime": "2024-01-01T11:00:00-07:00"},
        "description": "Event description" (optional),
        "location": "Event location" (optional),
        "attendees": [{"email": "attendee@example.com"}] (optional),
        "calendarId": "primary" (optional)
    }
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        
        # Validate required fields
        if not data.get('summary'):
            return JsonResponse({
                "error": "Missing required field: summary"
            }, status=400)
        
        if not data.get('start') or not data.get('end'):
            return JsonResponse({
                "error": "Missing required fields: start and end times"
            }, status=400)
        
        from .google_calendar_service import create_calendar_event
        result = create_calendar_event(username, data)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["PUT"])
@authentication_classes([])
def google_calendar_update_event(request):
    """
    Update an existing calendar event.
    
    Expected JSON payload:
    {
        "eventId": "event_id_to_update",
        "calendarId": "primary" (optional),
        "summary": "Updated event title" (optional),
        "start": {"dateTime": "2024-01-01T10:00:00-07:00"} (optional),
        "end": {"dateTime": "2024-01-01T11:00:00-07:00"} (optional),
        "description": "Updated event description" (optional),
        "location": "Updated event location" (optional),
        "attendees": [{"email": "attendee@example.com"}] (optional)
    }
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        
        event_id = data.get('eventId')
        if not event_id:
            return JsonResponse({
                "error": "Missing required field: eventId"
            }, status=400)
        
        # Remove eventId from data as it's passed separately
        event_data = {k: v for k, v in data.items() if k != 'eventId'}
        
        from .google_calendar_service import update_calendar_event
        result = update_calendar_event(username, event_id, event_data)
        return JsonResponse(result)
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)


@csrf_exempt
@require_http_methods(["DELETE"])
@authentication_classes([])
def google_calendar_delete_event(request, calendar_id, event_id):
    """
    Delete a calendar event.
    """
    username = request.username_from_token
    
    from .google_calendar_service import delete_calendar_event
    result = delete_calendar_event(username, event_id, calendar_id)
    return JsonResponse(result)


# ============ Starred S3 Files Endpoints ============

@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def get_starred_s3_files(request):
    """
    Get all starred S3 file IDs for the authenticated user.
    
    Returns:
        JsonResponse: {"result": "success", "file_ids": [list of file_id strings]}
    """
    username = request.username_from_token
    
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    starred_collection = db["starred_s3_files"]
    
    try:
        starred_docs = list(starred_collection.find({"username": username}))
        file_ids = [doc.get("file_id") for doc in starred_docs if doc.get("file_id")]
        
        return JsonResponse({
            "result": "success",
            "file_ids": file_ids
        })
    except Exception as e:
        return JsonResponse({
            "result": "error",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def star_s3_file(request):
    """
    Star an S3 file for the authenticated user.
    
    Expects JSON body: {"file_id": "..."}
    
    Returns:
        JsonResponse: {"result": "success"} or {"result": "error", "error": "..."}
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        file_id = data.get("file_id")
        
        if not file_id:
            return JsonResponse({
                "result": "error",
                "error": "Missing required field: file_id"
            }, status=400)
        
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        starred_collection = db["starred_s3_files"]
        
        # Upsert: insert if not exists, otherwise do nothing
        starred_collection.update_one(
            {"username": username, "file_id": file_id},
            {"$setOnInsert": {
                "username": username,
                "file_id": file_id,
                "created_at": datetime.utcnow()
            }},
            upsert=True
        )
        
        return JsonResponse({"result": "success"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "error",
            "error": str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
@authentication_classes([])
def unstar_s3_file(request):
    """
    Unstar an S3 file for the authenticated user.
    
    Expects JSON body: {"file_id": "..."}
    
    Returns:
        JsonResponse: {"result": "success"} or {"result": "error", "error": "..."}
    """
    username = request.username_from_token
    
    try:
        data = json.loads(request.body)
        file_id = data.get("file_id")
        
        if not file_id:
            return JsonResponse({
                "result": "error",
                "error": "Missing required field: file_id"
            }, status=400)
        
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        starred_collection = db["starred_s3_files"]
        
        starred_collection.delete_one({"username": username, "file_id": file_id})
        
        return JsonResponse({"result": "success"})
        
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({
            "result": "error",
            "error": str(e)
        }, status=500)
