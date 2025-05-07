from pymongo.mongo_client import MongoClient
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from bson import ObjectId


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


def add_notification(request, notification):
    """Adds a notification for a specific user and sends a WebSocket update.

    Args:
        username (str): The username of the user to add the notification for.
        notification (dict): A dictionary containing notification details:
            - type (str): The type of notification.
            - title (str): The title of the notification.
            - description (str): The description of the notification.
            - timestamp (datetime): The timestamp when the notification was created.
            - read (bool): The read status of the notification.

    Returns:
        dict or str: A success dictionary with the username if successful,
                     or an error string "User not found" if the user doesn't exist.
    """
    # Find the user by username
    user = user_collection.find_one({'username': request.username_from_token})
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
    result = notifications_collection.insert_one({
        'user_id': user_id,
        'type': type,
        'title': title,
        'description': description,
        'timestamp': timestamp,
        'read': read
    })

    if result.inserted_id:                  
        # After successfully adding the notification
        if user_id:
                # Get the channel layer
            channel_layer = get_channel_layer()
            
            # Convert ObjectId to string before sending
            serializable_user_id = str(user_id)
            
            # Send notification update to user's group
            async_to_sync(channel_layer.group_send)(
                f"user_{serializable_user_id}",
                {
                    "type": "notification_update",
                    "user_id": serializable_user_id
                }
            )

    # Return success response
    response = {
        "result": "success",
        "username": request.username_from_token,
    }
    return response


def main():
    result = add_notification("mmills", "test")
    print(result)

if __name__ == "__main__":
    main()




