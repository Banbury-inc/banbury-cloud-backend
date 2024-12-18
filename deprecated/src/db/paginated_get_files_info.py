from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def paginated_get_files_info(username, page=1, items_per_page=10):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    file_collection = db["files"]

    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

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
                "device_name": device.get("device_name"),
            })

    # Calculate pagination values
    total_items = len(all_files_data)
    total_pages = -(-total_items // items_per_page)  # Ceiling division
    start_idx = (page - 1) * items_per_page
    end_idx = start_idx + items_per_page

    # Get paginated data
    paginated_files = all_files_data[start_idx:end_idx]

    files_data = {
        "files": paginated_files,
        "pagination": {
            "current_page": page,
            "total_pages": total_pages,
            "items_per_page": items_per_page,
            "total_items": total_items
        }
    }

    return files_data
