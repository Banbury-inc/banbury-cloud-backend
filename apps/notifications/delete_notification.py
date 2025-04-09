from pymongo.mongo_client import MongoClient
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from bson.objectid import ObjectId

# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
user_collection = db['users']
notifications_collection = db['notifications']

def delete_notification(username, notification_id):
    """Deletes a specific notification for a user and sends a WebSocket update.

    Args:
        username (str): The username of the user whose notification is to be deleted.
        notification_id (str): The ID of the notification to delete.

    Returns:
        dict or str: A success dictionary if deletion is successful,
                     a dictionary with a failure message if the notification is not found,
                     or the string "User not found" if the user doesn't exist.
    """
    # Find the user by username
    user = user_collection.find_one({'username': username})
    if not user:
        response = "User not found"
        return response

    # Get user_id from username
    user_id = user['_id']

    # Turn notification_id into ObjectId
    notification_id = ObjectId(notification_id)

    print(notification_id)

    # Delete the notification - Fixed the delete operation
    result = notifications_collection.delete_one({'_id': notification_id})

    # Check if deletion was successful
    if result.deleted_count == 0:
        response = {
            "result": "fail",
            "message": "Notification not found"
        }
        return response

    # After successfully deleting the notification
    if user_id:
        # Get the channel layer
        channel_layer = get_channel_layer()
        
        # Send notification update to user's group
        async_to_sync(channel_layer.group_send)(
            f"user_{user_id}",
            {
                "type": "notification_update",
            }
        )

    # Return success response
    response = {
        "result": "success",
    }
    return response


def main():
    result = delete_notification("mmills", "6786b7fd23b4a6e067f7f6c0")
    print(result)

if __name__ == "__main__":
    main()




