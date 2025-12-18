import boto3
import os
from botocore.exceptions import ClientError
from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from bson.objectid import ObjectId

def delete_s3_file(username, file_id):
    """
    Deletes a file from S3 and removes its metadata from MongoDB.
    Only the file owner can delete files.
    
    Args:
        username (str): The username requesting the deletion
        file_id (str): The ID of the file to delete
        
    Returns:
        dict: Result of the delete operation
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
        
        user_id = user["_id"]
        
        # Find the file by ID
        file = file_collection.find_one({"_id": ObjectId(file_id), "s3_url": {"$exists": True}})
        if not file:
            return {"error": "File not found or not stored in S3", "status_code": 404}
        
        # Only owner can delete - check ownership
        file_owner_id = file.get("user_id")
        if file_owner_id != user_id:
            return {"error": "Access denied. Only the file owner can delete this file.", "status_code": 403}
        
        # Configure S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Get S3 bucket name
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        if not bucket_name:
            print(f"Error: AWS_S3_BUCKET_NAME environment variable not set")
            return {"error": "S3 bucket configuration missing", "status_code": 500}
        
        # Get the S3 object key
        object_key = file.get('s3_key')
        if not object_key:
            return {"error": "S3 key not found for file", "status_code": 404}
        
        try:
            # Delete the file from S3
            s3_client.delete_object(Bucket=bucket_name, Key=object_key)
            
            # Delete the file metadata from MongoDB
            delete_result = file_collection.delete_one({"_id": ObjectId(file_id)})
            
            if delete_result.deleted_count == 0:
                return {"error": "Failed to delete file metadata", "status_code": 500}
            
            return {
                "result": "success",
                "message": "File deleted successfully from S3 and database"
            }
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchKey':
                # File doesn't exist in S3, but we should still remove the metadata
                delete_result = file_collection.delete_one({"_id": ObjectId(file_id)})
                return {
                    "result": "success",
                    "message": "File metadata deleted (file was not found in S3)"
                }
            else:
                return {"error": f"S3 error: {str(e)}", "status_code": 500}
            
    except Exception as e:
        print(f"Error deleting S3 file: {e}")
        return {"error": f"Failed to delete file: {str(e)}", "status_code": 500}

def delete_multiple_s3_files(username, file_ids):
    """
    Deletes multiple files from S3 and removes their metadata from MongoDB.
    
    Args:
        username (str): The username requesting the deletion
        file_ids (list): List of file IDs to delete
        
    Returns:
        dict: Result of the delete operations
    """
    results = []
    errors = []
    
    for file_id in file_ids:
        result = delete_s3_file(username, file_id)
        if "error" in result:
            errors.append(f"File {file_id}: {result['error']}")
        else:
            results.append(f"File {file_id}: {result['message']}")
    
    if errors:
        return {
            "result": "partial_success" if results else "error",
            "message": f"Deleted {len(results)} files successfully, {len(errors)} failed",
            "errors": errors,
            "successes": results
        }
    else:
        return {
            "result": "success",
            "message": f"Successfully deleted {len(results)} files",
            "successes": results
        } 