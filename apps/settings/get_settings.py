from core.mongodb_manager import get_mongodb_collection

def get_settings(username):

    # Get MongoDB collections using centralized manager
    user_collection = get_mongodb_collection('users')
    settings_collection = get_mongodb_collection('settings')

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




