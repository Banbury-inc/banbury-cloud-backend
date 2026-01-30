"""
Transfer handlers for copying files between cloud providers (Google Drive, OneDrive) and S3.
"""
import io
import os
import json
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo.mongo_client import MongoClient
import requests

from .google_drive_service import (
    get_drive_service,
    get_user_drive_credentials,
    upload_drive_file
)
from googleapiclient.http import MediaIoBaseDownload


def get_mongo_client():
    """Get MongoDB client connection."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    return MongoClient(uri)


def get_s3_client():
    """Get S3 client."""
    return boto3.client(
        's3',
        aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'),
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )


def get_onedrive_credentials(user):
    """Get OneDrive credentials from user document."""
    onedrive_creds = user.get('onedrive_credentials', {})
    if not onedrive_creds.get('access_token'):
        return None
    return onedrive_creds


def refresh_onedrive_token_if_needed(onedrive_credentials, user_doc):
    """
    Ensure we have a valid OneDrive access token; refresh using refresh_token when required.
    Returns (access_token, error_message).
    """
    if not onedrive_credentials:
        return None, "No OneDrive credentials found"
    
    access_token = onedrive_credentials.get('access_token')
    refresh_token = onedrive_credentials.get('refresh_token')
    expires_at = onedrive_credentials.get('expires_at')
    
    if not access_token:
        return None, "No access token found"
    
    # Check if token needs refresh (expires within 5 minutes)
    needs_refresh = False
    if expires_at:
        try:
            from datetime import timedelta
            expiry_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            if datetime.now(expiry_time.tzinfo) >= expiry_time - timedelta(minutes=5):
                needs_refresh = True
        except (ValueError, TypeError):
            pass
    
    if not needs_refresh:
        return access_token, None
    
    if not refresh_token:
        return None, "Token expired and no refresh token available"
    
    ms_client_id = os.environ.get('MS_CLIENT_ID')
    ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
    
    if not ms_client_id or not ms_client_secret:
        return access_token, None
    
    try:
        from datetime import timedelta
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        token_data = {
            'client_id': ms_client_id,
            'client_secret': ms_client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': onedrive_credentials.get('scope', 'openid profile email offline_access User.Read Files.ReadWrite.All')
        }
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code == 200:
            token_response = response.json()
            new_access_token = token_response.get('access_token')
            new_refresh_token = token_response.get('refresh_token', refresh_token)
            expires_in = token_response.get('expires_in', 3600)
            new_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + 'Z'
            
            client = get_mongo_client()
            db = client["NeuraNet"]
            user_collection = db["users"]
            
            user_collection.update_one(
                {"_id": user_doc.get("_id")},
                {
                    "$set": {
                        "onedrive_credentials.access_token": new_access_token,
                        "onedrive_credentials.refresh_token": new_refresh_token,
                        "onedrive_credentials.expires_at": new_expires_at
                    }
                }
            )
            
            return new_access_token, None
        else:
            return access_token, None
            
    except Exception as e:
        print(f"Error refreshing OneDrive token: {e}")
        return access_token, None


@csrf_exempt
@require_http_methods(["POST"])
def transfer_drive_to_s3(request):
    """
    Copy a file from Google Drive to S3 (Banbury Local storage).
    
    Expects JSON body:
    - drive_file_id (str): The Google Drive file ID
    
    Returns:
    - { result: "success", local_file_id, local_path, file_name }
    - Or error response
    """
    try:
        username = request.username_from_token
        if not username:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        data = json.loads(request.body)
        drive_file_id = data.get('drive_file_id')
        
        if not drive_file_id:
            return JsonResponse({"error": "drive_file_id is required"}, status=400)
        
        # Get Drive service for this user
        service = get_drive_service(username)
        if not service:
            return JsonResponse({"error": "Google Drive not connected. Please activate Google Drive first."}, status=400)
        
        # Get file metadata
        file_metadata = service.files().get(fileId=drive_file_id, fields='id,name,mimeType,size').execute()
        file_name = file_metadata.get('name', 'unknown')
        mime_type = file_metadata.get('mimeType', 'application/octet-stream')
        
        # Determine if this is a Google Workspace document that needs export
        file_io = io.BytesIO()
        
        if mime_type.startswith('application/vnd.google-apps'):
            # Export Google Workspace documents
            if mime_type == 'application/vnd.google-apps.document':
                export_mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                file_name = file_name + '.docx' if not file_name.endswith('.docx') else file_name
            elif mime_type == 'application/vnd.google-apps.spreadsheet':
                export_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                file_name = file_name + '.xlsx' if not file_name.endswith('.xlsx') else file_name
            elif mime_type == 'application/vnd.google-apps.presentation':
                export_mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                file_name = file_name + '.pptx' if not file_name.endswith('.pptx') else file_name
            else:
                export_mime_type = 'application/pdf'
                file_name = file_name + '.pdf' if not file_name.endswith('.pdf') else file_name
            
            request_obj = service.files().export_media(fileId=drive_file_id, mimeType=export_mime_type)
            content_type = export_mime_type
        else:
            # Regular file download
            request_obj = service.files().get_media(fileId=drive_file_id)
            content_type = mime_type
        
        # Download the file
        downloader = MediaIoBaseDownload(file_io, request_obj)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        
        file_io.seek(0)
        file_content = file_io.read()
        file_size = len(file_content)
        
        # Upload to S3
        s3_client = get_s3_client()
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        
        # Create unique path: imports/google-drive/<driveFileId>/<filename>
        unique_path = f"imports/google-drive/{drive_file_id}/{file_name}"
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        object_key = f"{username}/{timestamp}_{file_name}"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=content_type
        )
        
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
        current_time = datetime.now().isoformat()
        
        # Save metadata to MongoDB
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        file_metadata_doc = {
            "user_id": user["_id"],
            "device_id": None,
            "file_type": os.path.splitext(file_name)[1],
            "file_name": file_name,
            "file_path": unique_path,
            "date_uploaded": current_time,
            "date_modified": current_time,
            "file_size": file_size,
            "file_parent": f"imports/google-drive/{drive_file_id}",
            "original_device": "google-drive-import",
            "kind": "file",
            "s3_url": s3_url,
            "s3_key": object_key,
            "source_provider": "google-drive",
            "source_file_id": drive_file_id
        }
        
        result = file_collection.insert_one(file_metadata_doc)
        local_file_id = str(result.inserted_id)
        
        return JsonResponse({
            "result": "success",
            "local_file_id": local_file_id,
            "local_path": unique_path,
            "file_name": file_name
        })
        
    except Exception as e:
        print(f"Error in transfer_drive_to_s3: {e}")
        return JsonResponse({"error": f"Failed to copy file: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def transfer_onedrive_to_s3(request):
    """
    Copy a file from OneDrive to S3 (Banbury Local storage).
    
    Expects JSON body:
    - onedrive_item_id (str): The OneDrive item ID
    
    Returns:
    - { result: "success", local_file_id, local_path, file_name }
    - Or error response
    """
    try:
        username = request.username_from_token
        if not username:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        data = json.loads(request.body)
        onedrive_item_id = data.get('onedrive_item_id')
        
        if not onedrive_item_id:
            return JsonResponse({"error": "onedrive_item_id is required"}, status=400)
        
        # Get user and OneDrive credentials
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        onedrive_creds = get_onedrive_credentials(user)
        if not onedrive_creds:
            return JsonResponse({"error": "OneDrive not connected. Please connect OneDrive first."}, status=400)
        
        access_token, error = refresh_onedrive_token_if_needed(onedrive_creds, user)
        if error or not access_token:
            return JsonResponse({"error": error or "Failed to get OneDrive access token"}, status=400)
        
        # Get file metadata from OneDrive
        headers = {'Authorization': f'Bearer {access_token}'}
        metadata_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{onedrive_item_id}"
        metadata_params = {'$select': 'id,name,size,file,@microsoft.graph.downloadUrl'}
        
        metadata_resp = requests.get(metadata_url, headers=headers, params=metadata_params, timeout=30)
        if metadata_resp.status_code != 200:
            return JsonResponse({"error": f"Failed to get OneDrive file metadata: {metadata_resp.text}"}, status=500)
        
        metadata = metadata_resp.json()
        file_name = metadata.get('name', 'unknown')
        file_size = metadata.get('size', 0)
        mime_type = metadata.get('file', {}).get('mimeType', 'application/octet-stream')
        download_url = metadata.get('@microsoft.graph.downloadUrl')
        
        if not download_url:
            # Fallback to content endpoint
            download_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{onedrive_item_id}/content"
        
        # Download the file
        if '@microsoft.graph.downloadUrl' in metadata:
            # Pre-authenticated URL
            download_resp = requests.get(download_url, timeout=120)
        else:
            download_resp = requests.get(download_url, headers=headers, timeout=120)
        
        if download_resp.status_code != 200:
            return JsonResponse({"error": f"Failed to download file from OneDrive: HTTP {download_resp.status_code}"}, status=500)
        
        file_content = download_resp.content
        actual_size = len(file_content)
        
        # Upload to S3
        s3_client = get_s3_client()
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        
        # Create unique path: imports/onedrive/<itemId>/<filename>
        unique_path = f"imports/onedrive/{onedrive_item_id}/{file_name}"
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        object_key = f"{username}/{timestamp}_{file_name}"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=file_content,
            ContentType=mime_type
        )
        
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{object_key}"
        current_time = datetime.now().isoformat()
        
        file_metadata_doc = {
            "user_id": user["_id"],
            "device_id": None,
            "file_type": os.path.splitext(file_name)[1],
            "file_name": file_name,
            "file_path": unique_path,
            "date_uploaded": current_time,
            "date_modified": current_time,
            "file_size": actual_size,
            "file_parent": f"imports/onedrive/{onedrive_item_id}",
            "original_device": "onedrive-import",
            "kind": "file",
            "s3_url": s3_url,
            "s3_key": object_key,
            "source_provider": "onedrive",
            "source_file_id": onedrive_item_id
        }
        
        result = file_collection.insert_one(file_metadata_doc)
        local_file_id = str(result.inserted_id)
        
        return JsonResponse({
            "result": "success",
            "local_file_id": local_file_id,
            "local_path": unique_path,
            "file_name": file_name
        })
        
    except Exception as e:
        print(f"Error in transfer_onedrive_to_s3: {e}")
        return JsonResponse({"error": f"Failed to copy file: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def transfer_s3_to_drive(request):
    """
    Copy a file from S3 (Banbury Local) to Google Drive root.
    
    Expects JSON body:
    - s3_file_id (str): The MongoDB file ID for the S3 file
    
    Returns:
    - { result: "success", drive_file_id, drive_file_name }
    - Or error response
    """
    try:
        username = request.username_from_token
        if not username:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        data = json.loads(request.body)
        s3_file_id = data.get('s3_file_id')
        
        if not s3_file_id:
            return JsonResponse({"error": "s3_file_id is required"}, status=400)
        
        # Check Drive credentials
        credentials = get_user_drive_credentials(username)
        if not credentials:
            return JsonResponse({"error": "Google Drive not connected. Please activate Google Drive first."}, status=400)
        
        # Get file metadata from MongoDB
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        from bson.objectid import ObjectId
        try:
            file_doc = file_collection.find_one({"_id": ObjectId(s3_file_id), "s3_url": {"$exists": True}})
        except Exception:
            return JsonResponse({"error": "Invalid file ID format"}, status=400)
        
        if not file_doc:
            return JsonResponse({"error": "File not found"}, status=404)
        
        # Verify ownership or shared access
        if file_doc.get("user_id") != user["_id"]:
            shared_with = file_doc.get("shared_with", [])
            shared_with_edit = file_doc.get("shared_with_edit", [])
            if user["_id"] not in shared_with and user["_id"] not in shared_with_edit:
                return JsonResponse({"error": "Access denied"}, status=403)
        
        # Download from S3
        s3_client = get_s3_client()
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        object_key = file_doc.get('s3_key')
        
        if not object_key:
            return JsonResponse({"error": "S3 key not found for file"}, status=404)
        
        try:
            s3_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            file_content = s3_obj['Body'].read()
        except ClientError as e:
            return JsonResponse({"error": f"Failed to download from S3: {str(e)}"}, status=500)
        
        file_name = file_doc.get('file_name', 'unknown')
        
        # Upload to Google Drive root
        file_io = io.BytesIO(file_content)
        result = upload_drive_file(username, file_io, file_name, parent_folder_id=None)
        
        if isinstance(result, JsonResponse):
            return result
        
        if result.get("result") == "success":
            return JsonResponse({
                "result": "success",
                "drive_file_id": result.get("file_info", {}).get("id"),
                "drive_file_name": result.get("file_info", {}).get("name", file_name)
            })
        else:
            return JsonResponse({"error": result.get("error", "Failed to upload to Drive")}, status=500)
        
    except Exception as e:
        print(f"Error in transfer_s3_to_drive: {e}")
        return JsonResponse({"error": f"Failed to copy file: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def transfer_s3_to_onedrive(request):
    """
    Copy a file from S3 (Banbury Local) to OneDrive root.
    Uses conflict behavior 'rename' to avoid overwriting existing files.
    
    Expects JSON body:
    - s3_file_id (str): The MongoDB file ID for the S3 file
    
    Returns:
    - { result: "success", onedrive_item_id, onedrive_file_name }
    - Or error response
    """
    try:
        username = request.username_from_token
        if not username:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        data = json.loads(request.body)
        s3_file_id = data.get('s3_file_id')
        
        if not s3_file_id:
            return JsonResponse({"error": "s3_file_id is required"}, status=400)
        
        # Get user and OneDrive credentials
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        onedrive_creds = get_onedrive_credentials(user)
        if not onedrive_creds:
            return JsonResponse({"error": "OneDrive not connected. Please connect OneDrive first."}, status=400)
        
        access_token, error = refresh_onedrive_token_if_needed(onedrive_creds, user)
        if error or not access_token:
            return JsonResponse({"error": error or "Failed to get OneDrive access token"}, status=400)
        
        # Get file from MongoDB
        from bson.objectid import ObjectId
        try:
            file_doc = file_collection.find_one({"_id": ObjectId(s3_file_id), "s3_url": {"$exists": True}})
        except Exception:
            return JsonResponse({"error": "Invalid file ID format"}, status=400)
        
        if not file_doc:
            return JsonResponse({"error": "File not found"}, status=404)
        
        # Verify ownership or shared access
        if file_doc.get("user_id") != user["_id"]:
            shared_with = file_doc.get("shared_with", [])
            shared_with_edit = file_doc.get("shared_with_edit", [])
            if user["_id"] not in shared_with and user["_id"] not in shared_with_edit:
                return JsonResponse({"error": "Access denied"}, status=403)
        
        # Download from S3
        s3_client = get_s3_client()
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        object_key = file_doc.get('s3_key')
        
        if not object_key:
            return JsonResponse({"error": "S3 key not found for file"}, status=404)
        
        try:
            s3_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            file_content = s3_obj['Body'].read()
            content_type = s3_obj.get('ContentType', 'application/octet-stream')
        except ClientError as e:
            return JsonResponse({"error": f"Failed to download from S3: {str(e)}"}, status=500)
        
        file_name = file_doc.get('file_name', 'unknown')
        file_size = len(file_content)
        
        # Upload to OneDrive root with conflict behavior 'rename'
        import urllib.parse
        
        if file_size <= 4 * 1024 * 1024:  # 4MB limit for simple upload
            upload_url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{urllib.parse.quote(file_name)}:/content?@microsoft.graph.conflictBehavior=rename"
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': content_type
            }
            
            upload_resp = requests.put(upload_url, headers=headers, data=file_content, timeout=120)
            
            if upload_resp.status_code in [200, 201]:
                upload_result = upload_resp.json()
                return JsonResponse({
                    "result": "success",
                    "onedrive_item_id": upload_result.get("id"),
                    "onedrive_file_name": upload_result.get("name", file_name)
                })
            else:
                return JsonResponse({"error": f"Failed to upload to OneDrive: {upload_resp.text}"}, status=500)
        else:
            # For larger files, we'd need upload sessions - for now return error
            return JsonResponse({
                "error": "File too large. Files over 4MB are not currently supported for OneDrive upload."
            }, status=400)
        
    except Exception as e:
        print(f"Error in transfer_s3_to_onedrive: {e}")
        return JsonResponse({"error": f"Failed to copy file: {str(e)}"}, status=500)


def get_google_workspace_mime_type(file_extension):
    """
    Map file extensions to Google Workspace MIME types for conversion.
    Returns (google_workspace_mime_type, source_mime_type) or (None, None) if not convertible.
    """
    extension_map = {
        # Word documents -> Google Docs
        '.doc': ('application/vnd.google-apps.document', 'application/msword'),
        '.docx': ('application/vnd.google-apps.document', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        '.odt': ('application/vnd.google-apps.document', 'application/vnd.oasis.opendocument.text'),
        '.rtf': ('application/vnd.google-apps.document', 'application/rtf'),
        '.txt': ('application/vnd.google-apps.document', 'text/plain'),
        '.html': ('application/vnd.google-apps.document', 'text/html'),
        '.htm': ('application/vnd.google-apps.document', 'text/html'),
        # Spreadsheets -> Google Sheets
        '.xls': ('application/vnd.google-apps.spreadsheet', 'application/vnd.ms-excel'),
        '.xlsx': ('application/vnd.google-apps.spreadsheet', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
        '.ods': ('application/vnd.google-apps.spreadsheet', 'application/vnd.oasis.opendocument.spreadsheet'),
        '.csv': ('application/vnd.google-apps.spreadsheet', 'text/csv'),
        # Presentations -> Google Slides
        '.ppt': ('application/vnd.google-apps.presentation', 'application/vnd.ms-powerpoint'),
        '.pptx': ('application/vnd.google-apps.presentation', 'application/vnd.openxmlformats-officedocument.presentationml.presentation'),
        '.odp': ('application/vnd.google-apps.presentation', 'application/vnd.oasis.opendocument.presentation'),
    }
    return extension_map.get(file_extension.lower(), (None, None))


def convert_to_pdf(file_content, file_name):
    """
    Convert a document to PDF using LibreOffice in headless mode.
    
    Requires LibreOffice to be installed on the server.
    Install on Ubuntu/Debian: sudo apt-get install libreoffice
    
    Args:
        file_content: bytes content of the source file
        file_name: original file name with extension
        
    Returns:
        tuple: (pdf_content_bytes, error_message)
    """
    import subprocess
    import tempfile
    import shutil
    
    file_extension = os.path.splitext(file_name)[1].lower()
    base_name = os.path.splitext(file_name)[0]
    
    # Supported formats for LibreOffice conversion
    supported_extensions = {
        '.doc', '.docx', '.odt', '.rtf', '.txt', '.html', '.htm',
        '.xls', '.xlsx', '.ods', '.csv',
        '.ppt', '.pptx', '.odp'
    }
    
    if file_extension not in supported_extensions:
        return None, f"File type '{file_extension}' cannot be converted to PDF"
    
    temp_dir = None
    try:
        # Create a temporary directory for the conversion
        temp_dir = tempfile.mkdtemp(prefix='pdf_convert_')
        input_path = os.path.join(temp_dir, file_name)
        
        # Write the input file
        with open(input_path, 'wb') as f:
            f.write(file_content)
        
        # Run LibreOffice in headless mode
        cmd = [
            'libreoffice',
            '--headless',
            '--convert-to', 'pdf',
            '--outdir', temp_dir,
            input_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode != 0:
            return None, f"LibreOffice conversion failed: {result.stderr}"
        
        # Read the output PDF
        pdf_path = os.path.join(temp_dir, base_name + '.pdf')
        
        if not os.path.exists(pdf_path):
            return None, "PDF file was not created by LibreOffice"
        
        with open(pdf_path, 'rb') as f:
            pdf_content = f.read()
        
        return pdf_content, None
        
    except subprocess.TimeoutExpired:
        return None, "PDF conversion timed out"
    except FileNotFoundError:
        return None, "LibreOffice is not installed. Install with: sudo apt-get install libreoffice"
    except Exception as e:
        return None, f"Conversion error: {str(e)}"
    finally:
        # Clean up temp directory
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)


@csrf_exempt
@require_http_methods(["POST"])
def save_as_pdf(request):
    """
    Convert an S3 file to PDF and save back to S3.
    
    Uses LibreOffice headless for PDF conversion, then uploads to S3.
    
    Supported formats: .doc, .docx, .xls, .xlsx, .ppt, .pptx, .odt, .ods, .odp, .rtf, .txt, .html, .csv
    Files already in PDF format are saved directly.
    
    Expects JSON body:
    - s3_file_id (str): The MongoDB file ID for the S3 file
    
    Returns:
    - { result: "success", local_file_id, local_path, file_name }
    - Or error response
    """
    try:
        username = request.username_from_token
        if not username:
            return JsonResponse({"error": "Authentication required"}, status=401)
        
        data = json.loads(request.body)
        s3_file_id = data.get('s3_file_id')
        
        if not s3_file_id:
            return JsonResponse({"error": "s3_file_id is required"}, status=400)
        
        # Get file metadata from MongoDB
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        file_collection = db["files"]
        
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({"error": "User not found"}, status=404)
        
        from bson.objectid import ObjectId
        try:
            file_doc = file_collection.find_one({"_id": ObjectId(s3_file_id), "s3_url": {"$exists": True}})
        except Exception:
            return JsonResponse({"error": "Invalid file ID format"}, status=400)
        
        if not file_doc:
            return JsonResponse({"error": "File not found"}, status=404)
        
        # Verify ownership or shared access
        if file_doc.get("user_id") != user["_id"]:
            shared_with = file_doc.get("shared_with", [])
            shared_with_edit = file_doc.get("shared_with_edit", [])
            if user["_id"] not in shared_with and user["_id"] not in shared_with_edit:
                return JsonResponse({"error": "Access denied"}, status=403)
        
        # Download from S3
        s3_client = get_s3_client()
        bucket_name = os.environ.get('AWS_S3_BUCKET_NAME')
        object_key = file_doc.get('s3_key')
        
        if not object_key:
            return JsonResponse({"error": "S3 key not found for file"}, status=404)
        
        try:
            s3_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            file_content = s3_obj['Body'].read()
        except ClientError as e:
            return JsonResponse({"error": f"Failed to download from S3: {str(e)}"}, status=500)
        
        file_name = file_doc.get('file_name', 'unknown')
        file_extension = os.path.splitext(file_name)[1].lower()
        base_name = os.path.splitext(file_name)[0]
        pdf_file_name = base_name + '.pdf'
        
        # If file is already a PDF, use it directly
        if file_extension == '.pdf':
            pdf_content = file_content
        else:
            # Convert to PDF using LibreOffice
            pdf_content, error = convert_to_pdf(file_content, file_name)
            
            if error:
                return JsonResponse({"error": error}, status=400)
        
        # Upload the PDF to S3
        pdf_size = len(pdf_content)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        pdf_object_key = f"{username}/{timestamp}_{pdf_file_name}"
        unique_path = f"{pdf_file_name}"
        
        s3_client.put_object(
            Bucket=bucket_name,
            Key=pdf_object_key,
            Body=pdf_content,
            ContentType='application/pdf'
        )
        
        s3_url = f"https://{bucket_name}.s3.amazonaws.com/{pdf_object_key}"
        current_time = datetime.now().isoformat()
        
        # Save metadata to MongoDB
        file_metadata_doc = {
            "user_id": user["_id"],
            "device_id": None,
            "file_type": ".pdf",
            "file_name": pdf_file_name,
            "file_path": unique_path,
            "date_uploaded": current_time,
            "date_modified": current_time,
            "file_size": pdf_size,
            "file_parent": "",
            "original_device": "web-editor",
            "kind": "file",
            "s3_url": s3_url,
            "s3_key": pdf_object_key,
            "source_provider": "local",
            "source_file_id": str(s3_file_id)
        }
        
        result = file_collection.insert_one(file_metadata_doc)
        local_file_id = str(result.inserted_id)
        
        return JsonResponse({
            "result": "success",
            "local_file_id": local_file_id,
            "local_path": unique_path,
            "file_name": pdf_file_name
        })
        
    except Exception as e:
        print(f"Error in save_as_pdf: {e}")
        return JsonResponse({"error": f"Failed to save file as PDF: {str(e)}"}, status=500)
