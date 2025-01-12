from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

def get_user_info(user_id):
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
    user_info = get_user_info("mmills")
    print(user_info)
