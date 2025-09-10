from core.mongodb_manager import get_mongodb_collection
from bson.objectid import ObjectId

def get_file_info(file_id):
    """
    Retrieves detailed information for a specific file based on its ObjectId.

    Args:
        username (str): The username of the user (currently unused in the function).
        file_id (str): The ObjectId string of the file to retrieve information for.

    Returns:
        dict or None: A dictionary containing file details (file_name, file_size, etc.)
                      if the file is found, otherwise None.
                      Returns None if the file ID is invalid or the file is not found.
    """
    # Get MongoDB collection using centralized manager
    try:
        file_collection = get_mongodb_collection('files')
    except Exception as e:
        print(f"[get_file_info] MongoDB connection error: {str(e)}")
        return None

    file_name = "csvs_ohio.zip"

    file_id = ObjectId(file_id)

    try:
        file = file_collection.find_one({"_id": file_id})
    except Exception as e:
        print(e)
        return None

    if file is None:
        return None

    file_data = {
        "file_name": file.get("file_name"),
        "file_size": file.get("file_size"),
        "file_type": file.get("file_type"),
        "file_path": file.get("file_path"),
        "date_uploaded": file.get("date_uploaded"),
        "date_modified": file.get("date_modified"),
        "date_accessed": file.get("date_accessed"),
        "kind": file.get("kind"),
        "device_id": str(file.get("device_id"))
    }

    return file_data



def main():
    print(get_file_info("mmills6060", "67659e872b46a3ef70402ead"))

if __name__ == "__main__":
    main()
