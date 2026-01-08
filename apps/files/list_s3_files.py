from core.mongodb_manager import get_mongodb_database

# Ensure index exists for efficient S3 file queries
# This runs once at module import time
try:
    _db = get_mongodb_database()
    _file_collection = _db["files"]
    # Compound index for user_id + s3_url existence check
    _file_collection.create_index([("user_id", 1), ("s3_url", 1)])
except Exception:
    pass  # Index may already exist or DB not available at import time

def list_s3_files(username):
    """
    Lists all S3 files for a specific user from the MongoDB database.
    
    Args:
        username (str): The username whose S3 files to list
        
    Returns:
        dict: A dictionary containing the list of files and any error message
    """
    try:
        # Use the connection-pooled MongoDB manager
        db = get_mongodb_database()
        user_collection = db["users"]
        file_collection = db["files"]
        
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            return {"error": "User not found", "status_code": 404}
        
        # Find all files with s3_url field that belong to the user
        # Query with user_id first (more selective) for better index usage
        s3_files = list(file_collection.find({
            "user_id": user["_id"],
            "s3_url": {"$exists": True}
        }))
        
        # Transform the results
        files_data = []
        for file in s3_files:
            files_data.append({
                "file_id": str(file.get("_id")),
                "file_name": file.get("file_name"),
                "file_path": file.get("file_path"),
                "file_type": file.get("file_type"),
                "file_size": file.get("file_size"),
                "date_uploaded": file.get("date_uploaded"),
                "date_modified": file.get("date_modified"),
                "s3_url": file.get("s3_url"),
                "device_name": file.get("original_device")
            })
            
        return {
            "result": "success",
            "files": files_data
        }
        
    except Exception as e:
        print(f"Error listing S3 files: {e}")
        return {"error": f"Failed to list S3 files: {str(e)}", "status_code": 500} 
