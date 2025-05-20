import uuid
import os
from django.conf import settings
from pymongo.mongo_client import MongoClient
from datetime import datetime
from bson import ObjectId

# MongoDB connection
def get_mongodb_connection():
    """Get MongoDB connection for API keys"""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    return db["api keys"]

def generate_api_key():
    """
    Generate a new API key
    """
    return str(uuid.uuid4())

def validate_api_key(api_key):
    """
    Check if an API key is valid in MongoDB
    """
    api_keys_collection = get_mongodb_connection()
    key_record = api_keys_collection.find_one({"api_key": api_key})
    
    # Also check settings for backward compatibility
    settings_valid = False
    if hasattr(settings, 'API_KEYS'):
        settings_valid = api_key in settings.API_KEYS
        
    return key_record is not None or settings_valid

def get_api_key_details(api_key):
    """
    Get the details (user, role) for an API key
    """
    api_keys_collection = get_mongodb_connection()
    key_record = api_keys_collection.find_one({"api_key": api_key})
    
    if key_record:
        # Convert ObjectId to string for JSON serialization if needed
        user_id = key_record.get("user_id")
        if isinstance(user_id, ObjectId):
            user_id = str(user_id)
            
        return {
            "user_id": user_id,
            "role": key_record.get("role"),
            "created_at": key_record.get("created_at")
        }
    return None

def register_api_key(api_key, user_id=None, role="user"):
    """
    Add a new API key to MongoDB with user ID and role
    """
    # Also add to settings for backward compatibility
    if not hasattr(settings, 'API_KEYS'):
        settings.API_KEYS = []
    
    if api_key not in settings.API_KEYS:
        settings.API_KEYS.append(api_key)
    
    # Store in MongoDB
    api_keys_collection = get_mongodb_connection()
    
    # Check if the key already exists
    existing_key = api_keys_collection.find_one({"api_key": api_key})
    if existing_key:
        return False
    
    # Try to convert user_id to ObjectId if it's a string representation of an ObjectId
    # This helps ensure proper reference relationships in MongoDB
    try:
        if user_id and isinstance(user_id, str) and ObjectId.is_valid(user_id):
            user_id = ObjectId(user_id)
    except Exception:
        # If conversion fails, keep it as a string
        pass
        
    # Insert the new key
    api_keys_collection.insert_one({
        "api_key": api_key,
        "user_id": user_id,
        "role": role,
        "created_at": datetime.now()
    })
    
    return True

def list_user_api_keys(user_id):
    """
    List all API keys for a specific user
    """
    api_keys_collection = get_mongodb_connection()
    
    # Try to convert user_id to ObjectId if it's a string representation of an ObjectId
    if isinstance(user_id, str) and ObjectId.is_valid(user_id):
        user_id = ObjectId(user_id)
    
    keys = api_keys_collection.find({"user_id": user_id})
    
    return [{
        "api_key": k.get("api_key"),
        "role": k.get("role"),
        "created_at": k.get("created_at")
    } for k in keys]

def delete_api_key(api_key):
    """
    Delete an API key from MongoDB
    """
    api_keys_collection = get_mongodb_connection()
    result = api_keys_collection.delete_one({"api_key": api_key})
    
    # Also remove from settings for backward compatibility
    if hasattr(settings, 'API_KEYS') and api_key in settings.API_KEYS:
        settings.API_KEYS.remove(api_key)
        
    return result.deleted_count > 0 