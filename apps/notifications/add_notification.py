from pymongo.mongo_client import MongoClient


# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
user_collection = db['users']
notifications_collection = db['notifications']


def add_notification(username, notification):

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response

    # Get user_id from username
    user_id = user['_id']

    type = notification['type']
    title = notification['title']
    description = notification['description']
    timestamp = notification['timestamp']
    read = notification['read']

    # Add notification to the user's notifications
    notifications_collection.insert_one({
        'user_id': user_id,
        'type': type,
        'title': title,
        'description': description,
        'timestamp': timestamp,
        'read': read
    })


    # Return success response
    response = {
        "result": "success",
        "username": username
    }
    return response


def main():
    result = add_notification("mmills", "test")
    print(result)

if __name__ == "__main__":
    main()




