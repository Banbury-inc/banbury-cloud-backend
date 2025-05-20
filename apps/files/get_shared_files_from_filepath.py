from pymongo.mongo_client import MongoClient
import motor.motor_asyncio


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
user_collection = db["users"]
device_collection = db["devices"]
file_collection = db["files"]

# Add these indexes first
file_collection.create_index([("device_id", 1)])
file_collection.create_index([("file_parent", 1)])  # Add index for file_parent

def get_shared_files_from_filepath(username, filepath):

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))
    device_ids = [device["_id"] for device in devices]


    if filepath == None or filepath == "" or filepath == "Core" or filepath == "Core/Devices":
        # First get one file from each device
        first_files_pipeline = [
            {"$match": {"device_id": {"$in": device_ids}}},
            {"$sort": {"date_uploaded": -1}},  # Sort by most recent
            {"$group": {
                "_id": "$device_id",
                "first_file": {"$first": "$$ROOT"}
            }},
            {"$replaceRoot": {"newRoot": "$first_file"}},
            # ... rest of lookups and projections ...
            {"$lookup": {
                "from": "devices",
                "localField": "device_id",
                "foreignField": "_id",
                "as": "device"
            }},
            {"$project": {
                "file_name": 1,
                "file_type": 1,
                "file_path": 1,
                "file_size": 1,
                "shared_with": {
                    "$ifNull": ["$shared_with", "$$REMOVE"]
                },
                "is_public": {
                    "$ifNull": ["$is_public", "$$REMOVE"]
                },
                "date_uploaded": 1,
                "kind": 1,
                "device_name": {"$arrayElemAt": ["$device.device_name", 0]},
                "device_id": {"$toString": "$device_id"},
                "_id": {"$toString": "$_id"}
            }}
        ]

        # Then get remaining files up to limit
        remaining_files_pipeline = [
            {"$match": {"device_id": {"$in": device_ids}}},
            {"$sort": {"date_uploaded": -1}},
            {"$limit": 100},
            # ... same lookups and projections ...
            {"$lookup": {
                "from": "devices",
                "localField": "device_id",
                "foreignField": "_id",
                "as": "device"
            }},
            {"$project": {
                "file_name": 1,
                "file_type": 1,
                "file_path": 1,
                "file_size": 1,
                "shared_with": {
                    "$ifNull": ["$shared_with", "$$REMOVE"]
                },
                "is_public": {
                    "$ifNull": ["$is_public", "$$REMOVE"]
                },
                "date_uploaded": 1,
                "kind": 1,
                "device_name": {"$arrayElemAt": ["$device.device_name", 0]},
                "device_id": {"$toString": "$device_id"},
                "_id": {"$toString": "$_id"}
            }}
        ]

        # Combine results
        files_data = list(file_collection.aggregate([
            {"$facet": {
                "first_files": first_files_pipeline,
                "remaining_files": remaining_files_pipeline
            }},
            {"$project": {
                "all_files": {
                    "$setUnion": ["$first_files", "$remaining_files"]
                }
            }},
            {"$unwind": "$all_files"},
            {"$replaceRoot": {"newRoot": "$all_files"}},
            {"$limit": 100}
        ]))

        return {
            "result": "success",
            "files": files_data
        }

    else:

        # Find the specific device
        filepath = filepath.replace("Core/Devices/", "")
        device_name = filepath.split("/")[0]
        target_device = next((d for d in devices if d["device_name"] == device_name), None)
        
        if not target_device:
            return {
                "result": "error",
                "message": f"Device '{device_name}' not found"
            }

        # Simple query using device_id only
        query = {
            "device_id": target_device["_id"]
        }

        # If we're looking at a specific directory, use file_parent
        remaining_path = '/'.join(filepath.split("/")[1:])
        if remaining_path:
            # You might need to adjust this depending on your exact path structure
            query["file_parent"] = {"$regex": f".*{remaining_path}$"}

        pipeline = [
            {"$match": query},
            {"$limit": 100},
            {"$lookup": {
                "from": "devices",
                "localField": "device_id",
                "foreignField": "_id",
                "as": "device"
            }},
            {"$project": {
                "file_name": 1,
                "file_type": 1,
                "file_path": 1,
                "file_size": 1,
                "shared_with": {
                    "$ifNull": ["$shared_with", "$$REMOVE"]
                },
                "is_public": {
                    "$ifNull": ["$is_public", "$$REMOVE"]
                },
                "date_uploaded": 1,
                "kind": 1,
                "device_name": {"$arrayElemAt": ["$device.device_name", 0]},
                "device_id": {"$toString": "$device_id"},
                "_id": {"$toString": "$_id"}
            }}
        ]
        
        files_data = list(file_collection.aggregate(pipeline))

        return {
            "result": "success",
            "files": files_data
        }

def get_shared_files_from_filepath(request, filepath):
    """
    Retrieves files shared with the specified user, optionally filtered by a filepath.

    Handles different filepath scenarios for shared files:
    - If filepath is None, empty, "Core", or "Core/Shared", it fetches all files
      directly shared with the user (up to 100), sorted by upload date.
    - If filepath specifies a path within the shared context (e.g., "Core/Shared/FolderName"),
      it attempts to fetch shared files matching that parent path.

    Args:
        username (str): The username of the user whose shared files are being queried.
        filepath (str or None): The path within the shared context to filter by.

    Returns:
        dict: A dictionary containing:
              - "result": Always "success" in this implementation.
              - "files": A list of shared file data dictionaries.
              - "error": An error message string if the user is not found.
    """
    # Find the user by username
    user = user_collection.find_one({"username": request.username_from_token})

    if not user:
        return {"error": "Please login first."}

    if filepath == None or filepath == "" or filepath == "Core" or filepath == "Core/Shared":
        # Get shared files
        pipeline = [
            {"$match": {"shared_with": user["_id"]}},
            {"$sort": {"date_uploaded": -1}},
            {"$limit": 100},
            {"$lookup": {
                "from": "devices",
                "localField": "device_id",
                "foreignField": "_id",
                "as": "device"
            }},
            {"$project": {
                "file_name": 1,
                "file_type": 1,
                "file_path": 1,
                "file_size": 1,
                "shared_with": 1,
                "is_public": 1,
                "date_uploaded": 1,
                "kind": 1,
                "device_name": {"$arrayElemAt": ["$device.device_name", 0]},
                "device_id": {"$toString": "$device_id"},
                "_id": {"$toString": "$_id"}
            }}
        ]
        
        files_data = list(file_collection.aggregate(pipeline))

    else:
        # Handle specific shared folder path
        filepath = filepath.replace("Core/Shared/", "")
        
        pipeline = [
            {"$match": {
                "shared_with": user["_id"],
                "file_parent": {"$regex": f".*{filepath}$"}
            }},
            {"$sort": {"date_uploaded": -1}},
            {"$limit": 100},
            {"$lookup": {
                "from": "devices",
                "localField": "device_id",
                "foreignField": "_id",
                "as": "device"
            }},
            {"$project": {
                "file_name": 1,
                "file_type": 1,
                "file_path": 1,
                "file_size": 1,
                "shared_with": 1,
                "is_public": 1,
                "date_uploaded": 1,
                "kind": 1,
                "device_name": {"$arrayElemAt": ["$device.device_name", 0]},
                "device_id": {"$toString": "$device_id"},
                "_id": {"$toString": "$_id"}
            }}
        ]
        
        files_data = list(file_collection.aggregate(pipeline))

    return {
        "result": "success",
        "files": files_data
    }

async def get_shared_files_from_filepath_async(request, filepath):
    """
    Asynchronous version intended to mirror get_shared_files_from_filepath.

    Fetches user information asynchronously but currently lacks the
    full implementation for fetching shared file data asynchronously.

    Args:
        username (str): The username of the user.
        filepath (str or None): The filepath within the shared context to filter by.

    Returns:
        # Currently incomplete - intended to return shared file data similarly to the sync version.
        # The function body only fetches the user async, needs file fetching logic.
        pass # Placeholder, actual return value depends on full implementation
    """
    # Convert your MongoDB client to async
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client["NeuraNet"]
    
    # Perform async queries
    user = await db.users.find_one({"username": request.username_from_token})
    # ... implement async version similarly ...
