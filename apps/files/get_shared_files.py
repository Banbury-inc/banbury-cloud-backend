from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


try:
    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    file_collection = db["files"]
except Exception as e:
    print(f"Error connecting to MongoDB: {e}")


def get_shared_files(username):


    # Find the user by username
    user = user_collection.find_one({"username": username})

    if not user:
        return {"error": "Please login first."}

    shared_files = file_collection.find({"shared_with": user["_id"]})

    file_data = []
    for file in shared_files:
        file_data.append({
            "file_name": file.get("file_name"),
            "file_path": file.get("file_path"),
            "file_size": file.get("file_size"),
            "shared_with": str(file.get("shared_with")),
            "is_public": file.get("is_public"),
            "device_name": file.get("device_name"),
            "device_id": str(file.get("device_id")),
        })

    shared_files = {
        "shared_files": file_data,
    }

    return shared_files

if __name__ == "__main__":
    shared_files = get_shared_files("mmills6060@gmail.com")
    print(shared_files)