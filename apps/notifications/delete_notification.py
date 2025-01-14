from pymongo.mongo_client import MongoClient

# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
user_collection = db['users']
notifications_collection = db['notifications']

def delete_notification(username, notification_id):


    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response

    # Get user_id from username
    user_id = user['_id']

    # Delete the notification
    notifications_collection.delete_one({'user_id': user_id, 'notification_id': notification_id})

    # Return success response
    response = {
        "result": "success",
        "username": username
    }
    return response


def main():
    result = delete_notification("mmills", "123")
    print(result)

if __name__ == "__main__":
    main()




