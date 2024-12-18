import json
from pymongo.mongo_client import MongoClient


def add_files(data, username):
    try:
        # Parse the JSON body
        # data = json.loads(request.body)

        # Extract specific data from the JSON
        files = data.get("files")
        device_name = data.get("device_name")

        if not files or not device_name:
            # return JsonResponse({"error": "Missing files or device_name"}, status=400)
            response = "missing_files_or_device_name"
            return response
    except Exception as e:
        # return JsonResponse({"error": f"Error parsing JSON: {str(e)}"}, status=400)
        response = f"error_parsing_json: {str(e)}"
        return


    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    file_collection = db["files"]
    device_collection = db["devices"]

    # Find the device_id based on device_name
    device = device_collection.find_one({"device_name": device_name})
    if not device:
        # return JsonResponse({
            # "result": "device_not_found",
            # "message": "Device not found.",
        # })

            response = "device_not_found"
            return response

    device_id = device.get("_id")
    if not device_id:
        # return JsonResponse({
            # "result": "object_id_not_found",
            # "message": "Device ID not found.",
        # })

            response = "object_id_not_found"
            return response
    # Prepare the list of new files to insert
    new_files = []
    for file_data in files:
        # Validate that file_data is a dictionary and contains the necessary fields
        if not isinstance(file_data, dict):
            # return JsonResponse(
                # {"error": f"Invalid file data format: {file_data}"}, status=400
            # )
            response = f"invalid_file_data_format: {file_data}"
            return response

        required_fields = ["file_name", "file_path", "file_size"]
        missing_fields = [
            field for field in required_fields if not file_data.get(field)
        ]
        if missing_fields:
            # return JsonResponse(
                # {"error": f"Missing fields: {missing_fields}"}, status=400
            # )
            response = f"missing_fields: {missing_fields}"
            return response

        # Prepare new file data for insertion
        new_file = {
            "device_id": device_id,
            "file_type": file_data.get("file_type"),
            "file_name": file_data.get("file_name"),
            "file_path": file_data.get("file_path"),
            "file_size": 2,
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
        # return JsonResponse({
            # "result": "no_files_to_add",
            # "message": "No valid files to add.",
        # })
        response = "no_files_to_add"
        return response

    # Insert all new files in one go
    try:
        file_collection.insert_many(new_files)
    except Exception as e:
        print(f"Error inserting files: {e}")
        # return JsonResponse(
            # {"result": "failure", "message": f"Error inserting files: {str(e)}"},
            # status=500,
        # )
        response = f"error_inserting_files: {str(e)}"
        return response


    # return JsonResponse({
        # "result": "success",
        # "message": f"{len(new_files)} files added successfully.",
    # })
    response = f"{len(new_files)} files added successfully."
    return response

def main():
    username = "mmills"
    data = {
        "files": [
            {
                "file_name": "file1.txt",
                "file_path": "/home/mmills/Documents/file1.txt",
                "file_size": 1000,
                "date_uploaded": "2021-10-01",
                "date_modified": "2021-10-01",
                "file_type": "text",
                "file_parent": "Documents",
                "original_device": "My Laptop",
                "kind": "document",
            },
            {
                "file_name": "file2.txt",
                "file_path": "/home/mmills/Documents/file2.txt",
                "file_size": 1500,
                "date_uploaded": "2021-10-01",
                "date_modified": "2021-10-01",
                "file_type": "text",
                "file_parent": "Documents",
                "original_device": "My Laptop",
                "kind": "document",
            },
        ],
        "device_name": "michael-ubuntu",
    }
    result = add_files(data, username)
    print(result)



if __name__ == '__main__':
    main()
