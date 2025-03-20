from pymongo.mongo_client import MongoClient
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from bson import ObjectId
from datetime import datetime
import time


# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
user_collection = db['users']
ai_collection = db['ai']


def convert_objectid(obj):
    if isinstance(obj, ObjectId):
        return str(obj)
    if isinstance(obj, dict):
        return {key: convert_objectid(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    return obj


def add_downloaded_model(username, model):

    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response

    # Get user_id from username
    user_id = user['_id']
    name = model
    timestamp = datetime.now()

    # Add model to the user's models
    result = ai_collection.insert_one({
        'user_id': user_id,
        'name': name,
        'timestamp': timestamp,
    })

    # Return success response
    response = {
        "result": "success",
        "username": username
    }
    return response


def main():
    result = add_downloaded_model("mmills", "test")
    print(result)

if __name__ == "__main__":
    main()




