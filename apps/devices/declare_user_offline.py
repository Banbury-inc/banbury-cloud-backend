from pymongo.mongo_client import MongoClient
from bson.objectid import ObjectId

def declare_user_offline(user_id):
    print(f"[declare_user_offline] Starting - User ID: {user_id}")

    # MongoDB connection
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    try:
        client = MongoClient(uri)
        db = client['NeuraNet']
        user_collection = db['users']
    except Exception as e:
        print(f"[declare_user_offline] MongoDB connection error: {str(e)}")
        return {"result": "error", "message": "Database connection failed"}

    # Find the user by user_id
    try:
        object_id = ObjectId(user_id)
        user = user_collection.find_one({'_id': object_id})
    except Exception as e:
        print(f"[declare_user_offline] Invalid user ID format: {str(e)}")
        return {"result": "error", "message": "Invalid user ID format"}

    if not user:
        print(f"[declare_user_offline] User not found: {user_id}")
        return {"result": "error", "message": "User not found"}

    print(f"[declare_user_offline] Found user: {user['_id']}")
    # Update the "online" field to True
    try:
        result = user_collection.update_one(
            {'_id': user['_id']},
            {'$set': {'online': False}},
            upsert=True  # Create new document if not found
        )
        print(f"[declare_user_offline] Update result - Modified: {result.modified_count}")
        
        return {
            "result": "success",
            "user_id": str(user['_id'])
        }
            
    except Exception as e:
        print(f"[declare_user_offline] Error updating user status: {str(e)}")
        return {"result": "error", "message": f"Error updating user status: {str(e)}"}


