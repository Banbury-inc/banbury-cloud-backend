from pymongo.mongo_client import MongoClient
from bson import ObjectId
import json


# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
user_collection = db['users']
notifications_collection = db['notifications']


def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    return obj


def get_notifications(username):

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response

    # Get user_id from username
    user_id = user['_id']

    # Find all notifications for the user
    notifications = list(notifications_collection.find({'user_id': user_id}))
    # Convert ObjectIds to strings
    notifications = convert_objectid(notifications)





    # Return success response
    response = {
        "result": "success",
        "notifications": notifications,
    }
    return response

def main():
    result = get_notifications("mmills")
    print(result)

if __name__ == "__main__":
    main()




