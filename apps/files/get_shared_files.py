from pymongo.mongo_client import MongoClient


try:
    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    file_collection = db["files"]
    device_collection = db["devices"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")


def get_shared_files(request):
    """
    Retrieves a list of all files shared with the specified user.

    For each shared file, it attempts to find the associated device belonging to the user
    to determine its availability and fetches the original owner's username.

    Args:
        username (str): The username of the user whose shared files are being queried.

    Returns:
        dict: A dictionary containing:
              - "shared_files": A list of dictionaries, each representing a shared file
                                with details like name, path, size, owner, availability, etc.
              - "error": An error message string if the user is not found.
                       Note: Does not explicitly handle MongoDB connection errors after initial try/except.
    """

    # Find the user by username
    user = user_collection.find_one({"username": request.username_from_token})

    if not user:
        return {"error": "Please login first."}

    shared_files = file_collection.find({"shared_with": user["_id"]})

    file_data = []
    for file in shared_files:
        # Look up device availability
        device_id = file.get("device_id")
        device = device_collection.find_one({"_id": device_id, "user_id": user["_id"]})
        device_available = device.get("available") if device else None

        # Look up the owner's information
        owner_id = device.get("user_id")
        owner = user_collection.find_one({"_id": owner_id})
        owner_username = owner.get("username") if owner else None

        file_data.append({
            "file_name": file.get("file_name"),
            "file_path": file.get("file_path"),
            "file_size": file.get("file_size"),
            "shared_with": str(file.get("shared_with")),
            "is_public": file.get("is_public"),
            "device_name": file.get("device_name"),
            "device_id": str(file.get("device_id")),
            "available": device_available,
            "original_device": file.get("original_device"),
            "date_uploaded": file.get("date_uploaded"),
            "date_modified": file.get("date_modified"),
            "owner": owner_username,
        })

    shared_files = {
        "shared_files": file_data,
    }

    return shared_files

if __name__ == "__main__":
    shared_files = get_shared_files("mmills6060@gmail.com")
    print(shared_files)
