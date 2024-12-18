from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

# At the module level, outside of any function
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
user_collection = db["users"]

# Create an index on username (run this once)
user_collection.create_index("username")

def get_user_info(username):
    try:
        # Find the user by username
        user = user_collection.find_one({"username": username})
        
        if not user:
            return {"error": "Please login first."}
        
        # Prepare devices data for response
        user_data = []
        user_data.append({
                "username": user.get("username"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "email": user.get("email"),
            })

        user_data = {
            "user": user_data,
        }

        return user_data
    except Exception as e:
        print(f"Error connecting to MongoDB: {e}")
        return {"error": "Failed to connect to MongoDB"}

if __name__ == "__main__":
    user_info = get_user_info("mmills")
    print(user_info)
