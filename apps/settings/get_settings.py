from pymongo.mongo_client import MongoClient

def get_settings(username):

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client['NeuraNet']
    user_collection = db['users']
    settings_collection = db['settings']

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response

    # Get user_id from username
    user_id = user['_id']


    # Find all settings for the user
    settings = settings_collection.find_one({'user_id': user_id})

    # Return success response
    response = {
        "result": "success",
        "settings": settings,
        "username": username,
    }
    return response


def main():
    result = get_settings("mmills")
    print(result)

if __name__ == "__main__":
    main()




