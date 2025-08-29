import boto3
import json
from botocore.exceptions import ClientError
from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime
import os
from bson import ObjectId


def update_s3_file(username, file_id, request):
    """
    Updates a file in S3 and its metadata in MongoDB.
    
    Parameters:
        username (str): The username of the file owner
        file_id (str): The ID of the file to update
        request: Django request object containing the new file data
        
    Returns:
        JsonResponse: Result of the update operation
    """
    try:
        # MongoDB connection
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        s3_files_collection = db["s3_files"]
        user_collection = db["users"]

        # Find the user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        # Find the file in MongoDB
        try:
            file_object_id = ObjectId(file_id)
        except Exception:
            return JsonResponse({"error": "Invalid file ID format"}, status=400)

        file_doc = s3_files_collection.find_one({
            "_id": file_object_id,
            "user_id": user["_id"]
        })
        
        if not file_doc:
            return JsonResponse({"error": "File not found"}, status=404)

        # Check if a new file is being uploaded
        if 'file' in request.FILES:
            uploaded_file = request.FILES['file']
            
            # AWS S3 configuration
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            bucket_name = os.getenv('S3_BUCKET_NAME', 'banbury-cloud-storage')
            
            if not aws_access_key_id or not aws_secret_access_key:
                return JsonResponse({"error": "AWS credentials not configured"}, status=500)

            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name='us-east-1'
            )

            # Generate S3 key (keep the same key to overwrite the existing file)
            s3_key = file_doc["s3_key"]

            try:
                # Upload the new file to S3 (overwrites existing file)
                s3_client.upload_fileobj(
                    uploaded_file,
                    bucket_name,
                    s3_key,
                    ExtraArgs={
                        'ContentType': uploaded_file.content_type or 'application/octet-stream',
                        'Metadata': {
                            'username': username,
                            'original_filename': uploaded_file.name,
                            'file_id': str(file_id)
                        }
                    }
                )

                # Update file metadata in MongoDB
                update_data = {
                    "file_name": uploaded_file.name,
                    "file_size": uploaded_file.size,
                    "content_type": uploaded_file.content_type or 'application/octet-stream',
                    "last_modified": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }

                # Update any additional metadata from POST data
                if hasattr(request, 'POST') and request.POST:
                    metadata = {}
                    for key, value in request.POST.items():
                        if key not in ['file']:  # Skip the file field
                            metadata[key] = value
                    if metadata:
                        update_data["metadata"] = metadata

                result = s3_files_collection.update_one(
                    {"_id": file_object_id},
                    {"$set": update_data}
                )

                if result.modified_count == 0:
                    return JsonResponse({"error": "Failed to update file metadata"}, status=500)

                return JsonResponse({
                    "result": "success",
                    "message": "File updated successfully",
                    "file_id": str(file_id),
                    "file_name": uploaded_file.name,
                    "file_size": uploaded_file.size,
                    "s3_key": s3_key
                })

            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'NoSuchBucket':
                    return JsonResponse({"error": "S3 bucket not found"}, status=500)
                elif error_code == 'AccessDenied':
                    return JsonResponse({"error": "Access denied to S3 bucket"}, status=500)
                else:
                    return JsonResponse({"error": f"S3 upload failed: {str(e)}"}, status=500)

        else:
            # No new file uploaded, just update metadata
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({"error": "Invalid JSON or no file provided"}, status=400)

            # Prepare update data for metadata only
            update_data = {
                "updated_at": datetime.utcnow()
            }

            # Update allowed metadata fields
            allowed_fields = ['file_name', 'metadata', 'tags', 'description']
            for field in allowed_fields:
                if field in data:
                    update_data[field] = data[field]

            # If updating file_name, also update last_modified
            if 'file_name' in data:
                update_data["last_modified"] = datetime.utcnow()

            if len(update_data) == 1:  # Only updated_at was set
                return JsonResponse({"error": "No valid fields to update"}, status=400)

            result = s3_files_collection.update_one(
                {"_id": file_object_id},
                {"$set": update_data}
            )

            if result.modified_count == 0:
                return JsonResponse({"error": "Failed to update file metadata"}, status=500)

            return JsonResponse({
                "result": "success",
                "message": "File metadata updated successfully",
                "file_id": str(file_id)
            })

    except Exception as e:
        print(f"Error updating S3 file: {str(e)}")
        return JsonResponse({"error": "Internal server error"}, status=500)
    finally:
        if 'client' in locals():
            client.close()
