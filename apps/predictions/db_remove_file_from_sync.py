from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime

def db_remove_file_from_sync(username, device_name, file_name):
    try:
        if not file_name or not device_name:
            return "Missing files or device_name"

    except Exception as e:
        return f"Invalid data: {str(e)}"

    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_sync_collection = db["file_sync"]

    # Delete the file sync record
    result = file_sync_collection.delete_one({"file_name": file_name})

    if result.deleted_count == 0:
        return "File not found in sync collection"

    return "success"


def main():


    result = db_remove_file_from_sync("mmills", "michael-mills-ubuntu", "11-0-Night.jpg")
    print(result)

if __name__ == "__main__":
    main()
