from pymongo.mongo_client import MongoClient

def get_online_devices(request):
    """
    Retrieves a list of devices marked as online.

    Connects to MongoDB, finds the user by username (to include in the response),
    and then queries the devices collection for all documents where the 'online'
    field is True. It formats the results into a list of dictionaries,
    each containing the device name and the associated username.

    Note:
        This function currently fetches *all* online devices, regardless of the
        specified username, but includes the specified username in each item of
        the result list. It might be intended to filter by the user's devices.

    Args:
        username (str): The username to associate with the found online devices
                      in the response (and potentially for filtering, though not currently used).

    Returns:
        str or dict: Returns "User not found" if the user lookup fails. Otherwise,
                     returns a dictionary containing the result ("success"),
                     the list of online devices (each with device_name and username),
                     and the input username.
                     Example: {"result": "success", "online_devices": [...], "username": "user1"}
    """

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    device_collection = db['devices']

    # Find the user by username
    user = user_collection.find_one({'username': request.username_from_token})
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
        "username": request.username_from_token,
    }
    return response




