from bson.objectid import ObjectId
from core.mongodb_manager import get_mongodb_collection

def declare_user_online(user_id):
    """
    Marks a user as online in the database using their MongoDB ObjectId.

    Uses centralized MongoDB connection manager to find the user by their ID, 
    and sets the 'online' field to True. It uses upsert=True, meaning if the 
    user is not found after the initial check, it might create a new user 
    document (though the initial check should prevent this).

    Args:
        user_id (str): The MongoDB ObjectId of the user as a string.

    Returns:
        dict: A dictionary indicating success or error, along with a message
              or the user_id on success.
    """
    print(f"[declare_user_online] Starting - User ID: {user_id}")

    # Get MongoDB collection using centralized manager
    try:
        user_collection = get_mongodb_collection('users')
    except Exception as e:
        print(f"[declare_user_online] MongoDB connection error: {str(e)}")
        return {"result": "error", "message": "Database connection failed"}

    # Find the user by user_id
    try:
        object_id = ObjectId(user_id)
        user = user_collection.find_one({'_id': object_id})
    except Exception as e:
        print(f"[declare_user_online] Invalid user ID format: {str(e)}")
        return {"result": "error", "message": "Invalid user ID format"}

    if not user:
        print(f"[declare_user_online] User not found: {user_id}")
        return {"result": "error", "message": "User not found"}

    print(f"[declare_user_online] Found user: {user['_id']}")
    # Update the "online" field to True
    try:
        result = user_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'online': True}},
            upsert=True  # Create new document if not found
        )
        print(f"[declare_user_online] Update result - Modified: {result.modified_count}")
        
        return {
            "result": "success",
            "user_id": str(user['_id'])
        }
            
    except Exception as e:
        print(f"[declare_user_online] Error updating user status: {str(e)}")
        return {"result": "error", "message": f"Error updating user status: {str(e)}"}


