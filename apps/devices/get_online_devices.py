from pymongo.mongo_client import MongoClient

def get_online_devices(username):

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response


    # Find all devices that are online
    online_devices = device_collection.find({'online': True})
    online_device_list = [{'device_name': device['device_name'], 'username': user['username']} for device in online_devices]

    # Return success response
    response = {
        "result": "success",
        "online_devices": online_device_list,
        "username": username
    }
    return response




