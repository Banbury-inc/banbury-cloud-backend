"""
Google Drive API service functions for handling Drive operations.
"""

import io
import os
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
from googleapiclient.errors import HttpError
from pymongo.mongo_client import MongoClient
from django.http import JsonResponse, HttpResponse


def get_user_drive_credentials(username):
    """Get Google Drive credentials for a user from MongoDB."""
    try:
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user = user_collection.find_one({"username": username})
        if not user or "google_drive_credentials" not in user:
            return None
            
        cred_data = user["google_drive_credentials"]
        
        # Convert expiry string back to datetime if it exists
        expiry = None
        if cred_data.get("expiry"):
            try:
                expiry = datetime.fromisoformat(cred_data["expiry"])
            except ValueError:
                pass
        
        credentials = Credentials(
            token=cred_data["access_token"],
            refresh_token=cred_data["refresh_token"],
            token_uri=cred_data["token_uri"],
            client_id=cred_data["client_id"],
            client_secret=cred_data["client_secret"],
            scopes=cred_data["scopes"],
            expiry=expiry
        )
        
        return credentials
        
    except Exception as e:
        print(f"Error getting user Drive credentials: {e}")
        return None


def update_user_drive_credentials(username, credentials):
    """Update user's Google Drive credentials in MongoDB."""
    try:
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # First, check if the user exists
        user = user_collection.find_one({"username": username})
        if not user:
            return
        
        drive_credentials = {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "token_uri": credentials.token_uri,
            "client_id": credentials.client_id,
            "client_secret": credentials.client_secret,
            "scopes": credentials.scopes,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None
        }
        
        result = user_collection.update_one(
            {"username": username},
            {"$set": {"google_drive_credentials": drive_credentials}}
        )
        
    except Exception as e:
        print(f"ERROR: Exception in update_user_drive_credentials: {e}")
        import traceback
        traceback.print_exc()


def get_drive_service(username):
    """Get Google Drive service instance for a user."""
    credentials = get_user_drive_credentials(username)
    if not credentials:
        return None
        
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        # If credentials were refreshed, update them in the database
        if credentials.token != get_user_drive_credentials(username).token:
            update_user_drive_credentials(username, credentials)
            
        return service
        
    except Exception as e:
        print(f"Error building Drive service: {e}")
        return None


def list_drive_files(username, page_token=None, folder_id=None, query=None):
    """List files from Google Drive."""
    service = get_drive_service(username)
    if not service:
        return JsonResponse({"error": "Drive service not available"}, status=401)
    
    try:
        # Build query
        q = ""
        if folder_id:
            q = f"'{folder_id}' in parents"
        elif query:
            q = query
        else:
            q = "trashed=false"
        
        # Call the Drive v3 API
        results = service.files().list(
            pageSize=1000,
            fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, createdTime, parents, webViewLink, thumbnailLink)",
            q=q,
            pageToken=page_token
        ).execute()
        
        items = results.get('files', [])
        
        # Format files for frontend
        formatted_files = []
        for item in items:
            file_info = {
                'id': item['id'],
                'file_name': item['name'],
                'kind': 'Folder' if item['mimeType'] == 'application/vnd.google-apps.folder' else 'File',
                'file_size': int(item.get('size', 0)) if item.get('size') else 0,
                'date_modified': item.get('modifiedTime'),
                'date_uploaded': item.get('createdTime'),
                'mime_type': item['mimeType'],
                'web_view_link': item.get('webViewLink'),
                'thumbnail_link': item.get('thumbnailLink'),
                'parents': item.get('parents', []),
                'source': 'google_drive'
            }
            formatted_files.append(file_info)
        
        return {
            'files': formatted_files,
            'nextPageToken': results.get('nextPageToken')
        }
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return JsonResponse({"error": f"Drive API error: {error}"}, status=500)


def download_drive_file(username, file_id):
    """Download a file from Google Drive."""
    service = get_drive_service(username)
    if not service:
        return JsonResponse({"error": "Drive service not available"}, status=401)
    
    try:
        # Get file metadata
        file_metadata = service.files().get(fileId=file_id).execute()
        
        # Check if it's a Google Workspace document
        if file_metadata['mimeType'].startswith('application/vnd.google-apps'):
            # Export Google Workspace documents
            if file_metadata['mimeType'] == 'application/vnd.google-apps.document':
                export_mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                file_extension = '.docx'
            elif file_metadata['mimeType'] == 'application/vnd.google-apps.spreadsheet':
                export_mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                file_extension = '.xlsx'
            elif file_metadata['mimeType'] == 'application/vnd.google-apps.presentation':
                export_mime_type = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                file_extension = '.pptx'
            else:
                export_mime_type = 'application/pdf'
                file_extension = '.pdf'
                
            request = service.files().export_media(fileId=file_id, mimeType=export_mime_type)
            filename = file_metadata['name'] + file_extension
        else:
            # Download regular files
            request = service.files().get_media(fileId=file_id)
            filename = file_metadata['name']
        
        file_io = io.BytesIO()
        downloader = MediaIoBaseDownload(file_io, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        file_io.seek(0)
        
        # Create HTTP response
        response = HttpResponse(
            file_io.getvalue(),
            content_type='application/octet-stream'
        )
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        response['Content-Length'] = len(file_io.getvalue())
        
        return response
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return JsonResponse({"error": f"Drive API error: {error}"}, status=500)


def upload_drive_file(username, file_obj, filename, parent_folder_id=None, target_mime_type=None):
    """
    Upload a file to Google Drive.

    Args:
        username: User's username
        file_obj: File object to upload
        filename: Name of the file
        parent_folder_id: Optional parent folder ID
        target_mime_type: Optional target MIME type (e.g., 'application/vnd.google-apps.presentation' to convert PPTX to Google Slides)
    """
    service = get_drive_service(username)
    if not service:
        return JsonResponse({"error": "Drive service not available"}, status=401)

    try:
        # File metadata
        file_metadata = {'name': filename}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]

        # If target_mime_type is specified, set it to convert the file
        # For example, setting 'application/vnd.google-apps.presentation' will convert PPTX to Google Slides
        if target_mime_type:
            file_metadata['mimeType'] = target_mime_type

        # Create media upload
        media = MediaIoBaseUpload(file_obj, mimetype='application/octet-stream', resumable=True)

        # Upload file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size, mimeType, createdTime'
        ).execute()

        return {
            "result": "success",
            "file_info": {
                "id": file.get('id'),
                "name": file.get('name'),
                "size": file.get('size'),
                "mime_type": file.get('mimeType'),
                "created_time": file.get('createdTime')
            }
        }

    except HttpError as error:
        print(f'An error occurred: {error}')
        return JsonResponse({"error": f"Drive API error: {error}"}, status=500)


def create_drive_file(username, filename, content, mime_type='text/plain', parent_folder_id=None):
    """Create a new file in Google Drive with content."""
    service = get_drive_service(username)
    if not service:
        return JsonResponse({"error": "Drive service not available"}, status=401)
    
    try:
        # File metadata
        file_metadata = {'name': filename}
        if parent_folder_id:
            file_metadata['parents'] = [parent_folder_id]
        
        # Create file content
        file_io = io.BytesIO(content.encode('utf-8') if isinstance(content, str) else content)
        media = MediaIoBaseUpload(file_io, mimetype=mime_type, resumable=True)
        
        # Create file
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, name, size, mimeType, createdTime'
        ).execute()
        
        return {
            "result": "success",
            "file_info": {
                "id": file.get('id'),
                "name": file.get('name'),
                "size": file.get('size'),
                "mime_type": file.get('mimeType'),
                "created_time": file.get('createdTime')
            }
        }
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return JsonResponse({"error": f"Drive API error: {error}"}, status=500)


def update_drive_file(username, file_id, content=None, filename=None):
    """Update an existing file in Google Drive."""
    service = get_drive_service(username)
    if not service:
        return JsonResponse({"error": "Drive service not available"}, status=401)
    
    try:
        # File metadata
        file_metadata = {}
        if filename:
            file_metadata['name'] = filename
        
        # Update file
        if content:
            file_io = io.BytesIO(content.encode('utf-8') if isinstance(content, str) else content)
            media = MediaIoBaseUpload(file_io, resumable=True)
            file = service.files().update(
                fileId=file_id,
                body=file_metadata,
                media_body=media,
                fields='id, name, size, mimeType, modifiedTime'
            ).execute()
        else:
            file = service.files().update(
                fileId=file_id,
                body=file_metadata,
                fields='id, name, size, mimeType, modifiedTime'
            ).execute()
        
        return {
            "result": "success",
            "file_info": {
                "id": file.get('id'),
                "name": file.get('name'),
                "size": file.get('size'),
                "mime_type": file.get('mimeType'),
                "modified_time": file.get('modifiedTime')
            }
        }
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return JsonResponse({"error": f"Drive API error: {error}"}, status=500)


def delete_drive_file(username, file_id):
    """Delete a file from Google Drive."""
    service = get_drive_service(username)
    if not service:
        return JsonResponse({"error": "Drive service not available"}, status=401)
    
    try:
        service.files().delete(fileId=file_id).execute()
        return {"result": "success", "message": "File deleted successfully"}
        
    except HttpError as error:
        print(f'An error occurred: {error}')
        return JsonResponse({"error": f"Drive API error: {error}"}, status=500)


def grant_drive_permission(username, file_id, recipient_email, role="writer"):
    """
    Grant permission on a Google Drive file to another user.
    
    Args:
        username (str): The username of the file owner (must have Drive connected)
        file_id (str): The Google Drive file ID
        recipient_email (str): The email address of the user to share with
        role (str): The role to grant - "reader", "writer", or "commenter" (default: "writer")
        
    Returns:
        dict: Result of the permission grant operation
    """
    service = get_drive_service(username)
    if not service:
        return {"error": "Drive service not available", "status_code": 401}
    
    try:
        # Create the permission
        permission = {
            "type": "user",
            "role": role,
            "emailAddress": recipient_email
        }
        
        # Create the permission on the file
        result = service.permissions().create(
            fileId=file_id,
            body=permission,
            sendNotificationEmail=True,  # Notify the user they've been granted access
            fields="id, type, role, emailAddress"
        ).execute()
        
        return {
            "result": "success",
            "permission_id": result.get("id"),
            "role": result.get("role"),
            "email": result.get("emailAddress"),
            "message": f"Permission granted to {recipient_email}"
        }
        
    except HttpError as error:
        error_reason = error.reason if hasattr(error, 'reason') else str(error)
        print(f'Error granting Drive permission: {error}')
        
        # Handle specific error cases
        if error.resp.status == 404:
            return {"error": "File not found", "status_code": 404}
        elif error.resp.status == 403:
            return {"error": "You don't have permission to share this file", "status_code": 403}
        elif error.resp.status == 400:
            return {"error": f"Invalid request: {error_reason}", "status_code": 400}
        else:
            return {"error": f"Drive API error: {error_reason}", "status_code": 500}


def share_drive_file_with_users(username, file_id, recipients, role="writer"):
    """
    Share a Google Drive file with multiple users.
    
    Args:
        username (str): The username of the file owner
        file_id (str): The Google Drive file ID
        recipients (list): List of dicts with "username" or "email" keys
        role (str): The role to grant (default: "writer")
        
    Returns:
        dict: Result of the share operations
    """
    # Get MongoDB connection to lookup user emails
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user_collection = db["users"]
    
    results = []
    errors = []
    
    for recipient in recipients:
        recipient_email = recipient.get("email")
        recipient_username = recipient.get("username")
        
        # If no email provided, look up by username
        if not recipient_email and recipient_username:
            recipient_user = user_collection.find_one({"username": recipient_username})
            if recipient_user:
                recipient_email = recipient_user.get("email")
        
        if not recipient_email:
            errors.append({
                "recipient": recipient_username or "unknown",
                "error": "Could not find email address for user"
            })
            continue
        
        # Grant permission
        result = grant_drive_permission(username, file_id, recipient_email, role)
        
        if "error" in result:
            errors.append({
                "recipient": recipient_email,
                "error": result["error"]
            })
        else:
            results.append({
                "recipient": recipient_email,
                "permission_id": result.get("permission_id"),
                "role": result.get("role")
            })
    
    if errors and not results:
        return {
            "result": "error",
            "message": "Failed to share with any recipients",
            "errors": errors
        }
    elif errors:
        return {
            "result": "partial_success",
            "message": f"Shared with {len(results)} user(s), {len(errors)} failed",
            "successes": results,
            "errors": errors
        }
    else:
        return {
            "result": "success",
            "message": f"Successfully shared with {len(results)} user(s)",
            "successes": results
        }


def check_user_drive_credentials(username):
    """Check if user has Google Drive credentials stored (without making API calls)."""
    try:
        credentials = get_user_drive_credentials(username)
        return {
            "result": "success",
            "has_credentials": credentials is not None,
            "message": "Credentials found" if credentials is not None else "No credentials found"
        }
    except Exception as e:
        print(f"Error checking user Drive credentials: {e}")
        return {
            "result": "error", 
            "has_credentials": False,
            "message": f"Error checking credentials: {str(e)}"
        }


def remove_user_drive_credentials(username):
    """Remove Google Drive credentials from user's MongoDB document."""
    try:
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Remove the google_drive_credentials field from the user document
        result = user_collection.update_one(
            {"username": username},
            {"$unset": {"google_drive_credentials": ""}}
        )
        
        if result.modified_count > 0:
            return {
                "result": "success",
                "message": "Google Drive credentials removed successfully"
            }
        else:
            return {
                "result": "success",
                "message": "No Google Drive credentials found to remove"
            }
        
    except Exception as e:
        print(f"Error removing user Drive credentials: {e}")
        return {
            "result": "error",
            "message": f"Error removing credentials: {str(e)}"
        } 