import boto3
import os
from botocore.exceptions import ClientError
from pymongo.mongo_client import MongoClient
from django.http import HttpResponse, JsonResponse
from bson.objectid import ObjectId

def download_s3_file(username, file_id):
    """
    Downloads a file from S3 for a specific user.
    
    Args:
        username (str): The username requesting the download
        file_id (str): The ID of the file to download
        
    Returns:
        HttpResponse or JsonResponse: The file content for download or an error response
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
            return JsonResponse({"error": "User not found"}, status=404)
        
        # Find the file by ID
        file = file_collection.find_one({"_id": ObjectId(file_id), "s3_url": {"$exists": True}})
        if not file:
            return JsonResponse({"error": "File not found or not stored in S3"}, status=404)
        
        # Configure S3 client
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Get S3 bucket name
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        
        # Get the S3 object key
        object_key = file.get('s3_key')
        if not object_key:
            return JsonResponse({"error": "S3 key not found for file"}, status=404)
        
        # Get file metadata
        try:
            # Get the file from S3
            file_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            file_content = file_obj['Body'].read()
            
            # Prepare the response
            response = HttpResponse(
                file_content,
                content_type=file_obj.get('ContentType', 'application/octet-stream')
            )
            
            # Set content disposition header to trigger download
            response['Content-Disposition'] = f'attachment; filename="{file.get("file_name")}"'
            
            # Set content length header
            response['Content-Length'] = file_obj.get('ContentLength', len(file_content))
            
            return response
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code')
            if error_code == 'NoSuchKey':
                return JsonResponse({"error": "File not found in S3 bucket"}, status=404)
            else:
                return JsonResponse({"error": f"S3 error: {str(e)}"}, status=500)
            
    except Exception as e:
        print(f"Error downloading S3 file: {e}")
        return JsonResponse({"error": f"Failed to download file: {str(e)}"}, status=500) 