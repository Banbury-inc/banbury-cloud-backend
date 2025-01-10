from pymongo import MongoClient


# Connect to MongoDB
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
file_collection = db['files']
file_sync_collection = db['file_sync']
device_collection = db['devices']

def download_file(username, file_id, is_file_sync):

    if is_file_sync:
        file = file_sync_collection.find_one({"file_id": file_id})
        if not file:
            return "file_not_found"
    else:
        file = file_collection.find_one({"file_id": file_id})
        if not file:
            return "file_not_found"
        # find the device_id from the file
        device_id = file.get("device_id")
        device_with_file = device_collection.find_one({"device_id": device_id})
        if not device_with_file:
            return "device_not_found"

        # find the user associate with the device
        user_id = device_with_file.get("user_id")
        if not user_id:
            return "user_not_found"

        # check to see if the device with file is online
        device_status = device_with_file.get("online")
        if device_status != True:
            return "device_not_online"

        else:
            # send a request via websocket to the device to download the file
            pass



        return "success"

