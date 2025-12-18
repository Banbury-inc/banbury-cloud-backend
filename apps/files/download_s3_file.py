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
        
        user_id = user["_id"]
        
        # Find the file by ObjectId
        try:
            file = file_collection.find_one({"_id": ObjectId(file_id), "s3_url": {"$exists": True}})
        except Exception as e:
            # Invalid ObjectId format
            return JsonResponse({"error": "Invalid file ID format"}, status=400)
        
        if not file:
            # Let's also check if the file exists without the s3_url requirement
            try:
                file_without_s3 = file_collection.find_one({"_id": ObjectId(file_id)})
                if file_without_s3:
                    return JsonResponse({"error": "File found but no S3 URL available"}, status=404)
                else:
                    return JsonResponse({"error": "File not found"}, status=404)
            except:
                return JsonResponse({"error": "File not found"}, status=404)
        
        # Check access permission: user must be owner OR in shared_with OR in shared_with_edit
        file_owner_id = file.get("user_id")
        shared_with = file.get("shared_with", [])
        shared_with_edit = file.get("shared_with_edit", [])
        
        is_owner = file_owner_id == user_id
        is_shared_view = user_id in shared_with
        is_shared_edit = user_id in shared_with_edit
        
        if not (is_owner or is_shared_view or is_shared_edit):
            return JsonResponse({"error": "Access denied. You do not have permission to download this file."}, status=403)
        
        # Check if this is a meeting file with Recall AI URL
        s3_url = file.get('s3_url')
        if s3_url and s3_url.startswith('http') and ('recall.ai' in s3_url or 'recallai' in s3_url):
            # This is a Recall AI URL, try to refresh it if it's expired
            try:
                # Check if we have a recall_bot_id in the file metadata
                recall_bot_id = file.get('recall_bot_id')
                if recall_bot_id:
                    # Import here to avoid circular imports
                    from apps.meeting_agent.recall_service import get_recall_bot_sync
                    
                    # Try to get fresh bot data from Recall AI
                    bot_result = get_recall_bot_sync(recall_bot_id)
                    if bot_result['success']:
                        bot_data = bot_result['bot_data']
                        # Check for updated video URL
                        updated_video_url = bot_data.get('video_url')
                        if updated_video_url and updated_video_url != s3_url:
                            # Update the file record with the new URL
                            file_collection.update_one(
                                {"_id": ObjectId(file_id)},
                                {"$set": {"s3_url": updated_video_url}}
                            )
                            s3_url = updated_video_url
                            print(f"Updated Recall AI video URL for file {file_id}")
            except Exception as e:
                print(f"Failed to refresh Recall AI URL for file {file_id}: {str(e)}")
                # Continue with the original URL
            
            # Return the URL (either original or refreshed)
            return JsonResponse({
                "url": s3_url,
                "download_url": s3_url,
                "presigned_url": s3_url,
                "file_name": file.get("file_name"),
                "file_type": "recall_ai_url"
            })
        
        # Configure S3 client only for actual S3 files
        s3_client = boto3.client(
            's3',
            aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        # Get S3 bucket name
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        if not bucket_name:
            return JsonResponse({"error": "S3 bucket configuration missing"}, status=500)
        
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
        return JsonResponse({"error": f"Failed to download file: {str(e)}"}, status=500) 
