import boto3
import os
from pymongo.mongo_client import MongoClient
from django.http import JsonResponse

def list_s3_files(username):
    """
    Lists all S3 files for a specific user from the MongoDB database.
    
    Args:
        username (str): The username whose S3 files to list
        
    Returns:
        dict: A dictionary containing the list of files and any error message
    """
    try:
        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        # Find the user by username
        user = user_collection.find_one({"username": username})
        if not user:
            return {"error": "User not found", "status_code": 404}
        
        # Find all files with s3_url field (indicating they're stored in S3)
        s3_files = list(file_collection.find({"s3_url": {"$exists": True}}))
        
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
