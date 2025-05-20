from pymongo import MongoClient

def getUserFriends(request):
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    user = user_collection.find_one({"username": request.username_from_token})
    friends = user.get("friends", [])
    
    # Get full user info for each friend
    friend_details = []
    for friend_id in friends:
        friend_info = user_collection.find_one({"_id": friend_id})
        if friend_info:
            # You might want to exclude sensitive information
            friend_details.append({
                "username": friend_info.get("username"),
                "first_name": friend_info.get("first_name"),
                "last_name": friend_info.get("last_name"),
                "picture": friend_info.get("picture"),
                "email": friend_info.get("email"),
                "phone_number": friend_info.get("phone_number"),
            })
        else:
            print(f"Friend info not found for {friend_id}") 
            return []

    response = {
        "result": "success",
        "friends": friend_details
    }

    
    return response
