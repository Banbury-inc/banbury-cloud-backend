from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId

# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client['NeuraNet']
notifications_collection = db['notifications']

def mark_notification_as_read(request, notification_id):
    """Marks a specific notification as read.

    Args:
        notification_id (str): The ID of the notification to mark as read.

    Returns:
        dict: A dictionary indicating the success of the operation.
    """
    # Add notification to the user's notifications

    # Set the notification_id to an object id
    notification_id = ObjectId(notification_id)

    notifications_collection.update_one(
        {'_id': notification_id},
        {'$set': {'read': True}}
    )

    # Return success response
    response = {
        "result": "success",
    }
    return response


def main():
    result = mark_notification_as_read("mmills", "6699112233445566778899")
    print(result)

if __name__ == "__main__":
    main()




