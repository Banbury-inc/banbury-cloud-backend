import boto3
import json
from botocore.exceptions import ClientError
from pymongo.mongo_client import MongoClient
from django.http import JsonResponse
from datetime import datetime
import os
from bson.objectid import ObjectId


def update_s3_file(username, file_id, request):
    """
    Updates a file in S3 and its metadata in MongoDB.
    
    Parameters:
        username (str): The username of the file owner or editor
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
        file_collection = db["files"]
        user_collection = db["users"]

        # Find the user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)

        user_id = user["_id"]

        # Find the file in MongoDB
        try:
            file_object_id = ObjectId(file_id)
        except Exception:
            return JsonResponse({"error": "Invalid file ID format"}, status=400)

        # Find the file without restricting to owner only
        file_doc = file_collection.find_one({"_id": file_object_id, "s3_key": {"$exists": True}})
        
        if not file_doc:
            return JsonResponse({"error": "File not found"}, status=404)
        
        # Check access permission: user must be owner OR in shared_with_edit
        file_owner_id = file_doc.get("user_id")
        shared_with_edit = file_doc.get("shared_with_edit", [])
        
        is_owner = file_owner_id == user_id
        is_shared_edit = user_id in shared_with_edit
        
        if not (is_owner or is_shared_edit):
            return JsonResponse({"error": "Access denied. You do not have permission to edit this file."}, status=403)

        if not file_doc.get("s3_key"):
            return JsonResponse({"error": "S3 key not found for file"}, status=404)

        # File-content update path: use POST for multipart uploads
        if request.method == 'POST':
            if 'file' not in request.FILES:
                return JsonResponse({"error": "Missing file in multipart upload"}, status=400)
            uploaded_file = request.FILES['file']
            
            # AWS S3 configuration
            aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
            aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
            bucket_name = os.getenv('AWS_S3_BUCKET_NAME')
            
            if not aws_access_key_id or not aws_secret_access_key:
                return JsonResponse({"error": "AWS credentials not configured"}, status=500)
            if not bucket_name:
                return JsonResponse({"error": "S3 bucket configuration missing"}, status=500)

            # Initialize S3 client
            s3_client = boto3.client(
                's3',
                aws_access_key_id=aws_access_key_id,
                aws_secret_access_key=aws_secret_access_key,
                region_name=os.environ.get('AWS_REGION', 'us-east-1')
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

                result = file_collection.update_one(
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
            # Metadata-only update path: use PUT with JSON body
            if request.method != 'PUT':
                return JsonResponse({"error": "Unsupported method for metadata update"}, status=405)
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

            result = file_collection.update_one(
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
