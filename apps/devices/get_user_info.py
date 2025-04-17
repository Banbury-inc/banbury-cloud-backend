from pymongo.mongo_client import MongoClient

def get_user_info(user_id):
    """
    Retrieves information for a single user using their MongoDB ObjectId.

    Connects to MongoDB and fetches the user document corresponding to the
    provided user_id. Formats selected user data into a dictionary within a list.

    Args:
        user_id (str or ObjectId): The MongoDB ObjectId of the user (can be string or ObjectId).

    Returns:
        dict: A dictionary containing a list with a single user's details under
              the key "user_info", or an error message under the key "error"
              if the connection fails or the user is not found.
              Note: List/array fields (devices, friends, friend_requests) are converted to strings.
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return {"error": "Failed to connect to MongoDB"}


    # Find the user by username
    user = user_collection.find_one({"_id": user_id})

    if not user:
        return {"error": "Please login first."}


    # Prepare devices data for response
    user_data = []
    user_data.append({
        "username": user.get("username"),
        "first_name": user.get("first_name"),
        "last_name": user.get("last_name"),
        "email": user.get("email"),
        "phone_number": user.get("phone_number"),
        "online": user.get("online"),
        "devices": str( user.get("devices")),
        "friends": str(user.get("friends")),
        "friend_requests": str(user.get("friend_requests")),
    })

    user_data = {
        "user_info": user_data,
    }

    return user_data

if __name__ == "__main__":
    """Script execution entry point for testing get_user_info."""
    # Note: The function expects an ObjectId, but "mmills" is passed.
    # This will likely fail unless there's a user document with _id="mmills".
    # Replace "mmills" with a valid ObjectId string for testing.
    # Example with a placeholder ObjectId string:
    # user_info = get_user_info(ObjectId("507f1f77bcf86cd799439011"))
    user_info = get_user_info("mmills") # Original call, likely needs correction
    print(user_info)
