import boto3
import os
from datetime import datetime
from botocore.exceptions import ClientError
from django.http import JsonResponse
from django.core.files.uploadedfile import UploadedFile
from pymongo.mongo_client import MongoClient
from .utils import broadcast_new_file

def upload_file_to_s3(request, username):
    """
    Uploads a file to an Amazon S3 bucket and stores metadata in MongoDB.
    
    Expects a multipart form data request containing:
    - file: The file to upload.
    - device_name (str, required): The name of the device from which the file is being uploaded.
    - file_path (str, optional): The file path where the file should be stored. Defaults to root.
    - file_parent (str, optional): The parent directory of the file. Defaults to empty.
    
    Args:
        request: The HTTP request object
        username (str): The username uploading the file.
        
    Returns:
        JsonResponse:
            - On Success: {"result": "success", "file_url": s3_url, "file_info": file_metadata}
            - On Error:
                - {"error": "No file provided."}, status=400
                - {"error": "Invalid file format."}, status=400
                - {"error": "Device not found."}, status=404
                - {"error": "User not found."}, status=404
                - {"error": "Failed to upload file: ..."}, status=500
    """
    # Check if the request contains a file
    if 'file' not in request.FILES:
        return JsonResponse({"error": "No file provided."}, status=400)
    
    # Get the uploaded file
    uploaded_file = request.FILES['file']
    
    # Check if uploaded_file is a valid file
    if not isinstance(uploaded_file, UploadedFile):
        return JsonResponse({"error": "Invalid file format."}, status=400)
    
    # Get additional parameters from the request
    device_name = request.POST.get('device_name')
    file_path = request.POST.get('file_path', '')  # Default to root if not provided
    file_parent = request.POST.get('file_parent', '')  # Default to empty if not provided
    
    if not device_name:
        return JsonResponse({"error": "Device name is required."}, status=400)
    
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    device_collection = db["devices"]
    file_collection = db["files"]
    
    # Find the user by username
    user = user_collection.find_one({"username": username})
    if not user:
        return JsonResponse({"error": "User not found."}, status=404)
    
    # Find the device by device_name for the user
    device = device_collection.find_one({
        "user_id": user["_id"],
        "device_name": device_name
    })
    if not device:
        return JsonResponse({"error": "Device not found."}, status=404)
    
    device_id = device["_id"]
    
    # Configure S3 client
    s3_client = boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
    
    # Set S3 bucket name
    bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
    
    # Generate S3 object key (path in S3 bucket)
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = uploaded_file.name
    object_key = f"{username}/{timestamp}_{file_name}"
    
    try:
        # Upload file to S3
        s3_client.upload_fileobj(
            uploaded_file,
            bucket_name,
            object_key,
            ExtraArgs={
                'ContentType': uploaded_file.content_type
            }
        )
        
        # Generate URL for the uploaded file
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
        
        # Get current time
        current_time = datetime.now().isoformat()
        
        # Prepare file metadata
        file_metadata = {
            "device_id": device_id,
            "file_type": os.path.splitext(file_name)[1],
            "file_name": file_name,
            "file_path": file_path,
            "date_uploaded": current_time,
            "date_modified": current_time,
            "file_size": uploaded_file.size,
            "file_parent": file_parent,
            "original_device": device_name,
            "kind": "file",
            "s3_url": s3_url,
            "s3_key": object_key
        }
        
        # Insert file metadata into MongoDB
        file_collection.insert_one(file_metadata)
        
        # Broadcast the new file (if needed, using existing utility)
        try:
            broadcast_new_file(file_metadata)
        except Exception as e:
            print(f"Warning: Failed to broadcast new file: {e}")
        
        # Return success response
        return JsonResponse({
            "result": "success",
            "file_url": s3_url,
            "file_info": {
                "file_name": file_name,
                "file_path": file_path,
                "file_size": uploaded_file.size,
                "file_type": os.path.splitext(file_name)[1],
                "date_uploaded": current_time,
                "date_modified": current_time,
                "original_device": device_name
            }
        })
        
    except ClientError as e:
        print(f"S3 upload error: {e}")
        return JsonResponse({"error": f"Failed to upload file: {str(e)}"}, status=500)
    except Exception as e:
        print(f"General error during file upload: {e}")
        return JsonResponse({"error": f"Failed to upload file: {str(e)}"}, status=500)
