from pymongo import MongoClient
import re

def getfileinfo(username):
    # Set the folder path you want to search within
    folder_path = "/home/mmills/BCloud/"

    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']
    file_collection = db['files']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    
    if not user:
        return "User not found."

    # Find all devices belonging to the user
    devices = list(device_collection.find({'user_id': user['_id']}))

    # Prepare file data for response
    all_files_data = []
    for device in devices:
        # Regular expression to match files within two levels of the folder_path
        # For example: /home/mmills/Downloads/level1/level2/file.txt
        regex_pattern = f'^{re.escape(folder_path)}[^/]+(/[^/]+)?/?$'
        
        # Find all files for the current device within the specified folder and up to two levels deep
        files = list(file_collection.find({
            'device_id': device['_id'],
            'file_path': {'$regex': regex_pattern}
        }))
        
        # Process each file and append to the list
        for file in files:
            all_files_data.append({
                "file_name": file.get('file_name'),
                "file_size": file.get('file_size'),
                "file_type": file.get('file_type'),
                "file_path": file.get('file_path'),
                "date_uploaded": file.get('date_uploaded'),
                "date_modified": file.get('date_modified'),
                "date_accessed": file.get('date_accessed'),
                "kind": file.get('kind'),
                "device_name": device.get('device_name'),  # Include device name for context
            })

    files_data = {
        "files": all_files_data,
    }
    
    return files_data

def main():
    # Test the function
    username = "mmills"
    response_data = getfileinfo(username)
    print(response_data)

if __name__ == '__main__':
    main()

