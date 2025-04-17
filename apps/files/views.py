from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
from rest_framework.decorators import api_view
from .delete_files import delete_files
from .get_files_from_filepath import get_files_from_filepath as db_get_files_from_filepath
from .update_files import update_files
from .get_file_info import get_file_info as db_get_file_info
from websocket.utils import broadcast_new_file
from .get_shared_files import get_shared_files as db_get_shared_files
import json
import re


@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def add_file(request, username):
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
@api_view(["POST"])
def handle_delete_files(request, username):
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




@api_view(["GET"])
def getfileinfo(request, username):
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
@api_view(["POST"])
def paginated_get_files_info(request, username):
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
    
    return paginated_get_files_info(username, page=page, items_per_page=items_per_page)



@csrf_exempt  # Disable CSRF token for this view only if necessary (e.g., for external API access)
@require_http_methods(["POST"])
@api_view(["POST"])
def get_partial_file_info(request, username):
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
@api_view(["POST"])
def add_scanned_folder(request, username):
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
@api_view(["POST"])
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
@api_view(["POST"])
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
@api_view(["POST"])
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
@api_view(["POST"])
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
@api_view(["GET"])
def download_file(request, username, file_id, is_file_sync):
    """
    Initiates a file download process.

    *** WARNING: The actual download logic seems missing. This endpoint calls a
          function `download_file` which is likely undefined or not imported correctly. ***
    The implementation details for fetching and streaming the file content are needed.

    URL Parameters:
        username (str): The username requesting the download.
        file_id (str): The ID (_id) of the file to download.
        is_file_sync (bool): Boolean flag indicating if this is part of a file sync process
                             (usage within the missing `download_file` function is unknown).

    Returns:
        JsonResponse:
            - On Success (if helper function works): {"status": "success", "message": "File downloaded successfully"}
            - On Error:
                - {"error": str(e)}, status=500 (Catches any exception from the missing `download_file` call)
                - NameError if `download_file` is not defined.
    """
    try:
        download_file(username, file_id, is_file_sync)
        return JsonResponse({"status": "success", "message": "File downloaded successfully"})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)



@csrf_exempt
@require_http_methods(["GET"])
@api_view(["GET"])
def get_file_info(request, username, file_id):
    """
    Retrieves detailed metadata information for a specific file by its ID.

    Delegates the core logic to the `db_get_file_info` utility function.

    URL Parameters:
        username (str): The username requesting the file info (potentially used for authorization
                       within the helper function, though not directly used in this view).
        file_id (str): The ID (_id) of the file whose information is requested.

    Returns:
        JsonResponse:
            - On Success: {"status": "success", "file_info": file_metadata_dict}
              (The structure of metadata depends on `db_get_file_info` implementation).
            - On Error:
                - {"error": str(e)}, status=500 (Catches any exception from `db_get_file_info`).
    """
    try:
        file_info = db_get_file_info(username, file_id)
        return JsonResponse({"status": "success", "file_info": file_info})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
