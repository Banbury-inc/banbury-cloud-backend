from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import motor.motor_asyncio
from asgiref.sync import sync_to_async


uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
user_collection = db["users"]
device_collection = db["devices"]
file_collection = db["files"]

# Add these indexes first
file_collection.create_index([("device_id", 1)])
file_collection.create_index([("file_parent", 1)])  # Add index for file_parent

def get_files_from_filepath(username, filepath):

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    # Find all devices belonging to the user
    devices = list(device_collection.find({"user_id": user["_id"]}))
    device_ids = [device["_id"] for device in devices]


    if filepath == None or filepath == "" or filepath == "Core" or filepath == "Core/Devices":
        files_data = []
        for device in devices:
            files_data.append({
                "file_name": "file_name",
                # "file_size": "file_size", 
                "file_type": "file_type",
                "file_path": "file_path",
                # "date_uploaded": "date_uploaded",
                # "date_modified": "date_modified",
                # "date_accessed": "date_accessed",
                "kind": "kind",
                "device_name": device["device_name"]
            })

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

async def get_files_from_filepath_async(username, filepath):
    # Convert your MongoDB client to async
    client = motor.motor_asyncio.AsyncIOMotorClient(uri)
    db = client["NeuraNet"]
    
    # Perform async queries
    user = await db.users.find_one({"username": username})
    devices = await db.devices.find({"user_id": user["_id"]}).to_list(None)
    
