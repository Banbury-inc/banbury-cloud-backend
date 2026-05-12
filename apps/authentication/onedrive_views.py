"""
OneDrive/Microsoft Graph integration views for Banbury backend.
Handles OAuth flow and API proxy endpoints for OneDrive file operations.
"""
import os
import json
import uuid
import urllib.parse
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
from rest_framework_simplejwt.tokens import AccessToken
import requests


# MongoDB connection
def get_mongo_client():
    """Get MongoDB client connection."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    return MongoClient(uri)


def get_user_from_token(request):
    """Extract and validate user from JWT token."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or ' ' not in auth_header:
        return None, JsonResponse({'message': 'Authentication required'}, status=401)
    
    auth_type, token = auth_header.split(' ', 1)
    if auth_type.lower() != 'bearer':
        return None, JsonResponse({'message': 'Invalid authentication type'}, status=401)
        
    try:
        validated = AccessToken(token)
        username = validated.payload.get('username')
        
        if not username:
            return None, JsonResponse({'message': 'Invalid token'}, status=401)
        
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user = user_collection.find_one({"username": username})
        
        if not user:
            return None, JsonResponse({'message': 'User not found'}, status=404)
            
        return user, None
        
    except Exception as e:
        return None, JsonResponse({'message': str(e)}, status=401)


def get_onedrive_credentials(user):
    """Get OneDrive credentials from user document."""
    onedrive_creds = user.get('onedrive_credentials', {})
    if not onedrive_creds.get('access_token'):
        return None
    return onedrive_creds


def _refresh_onedrive_access_token_if_needed(onedrive_credentials, user_doc):
    """
    Ensure we have a valid access token; refresh using refresh_token when required.
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


def make_graph_api_request(url, access_token, method='GET', data=None, params=None, stream=False):
    """Make a request to Microsoft Graph API."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=60, stream=stream)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=60)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data, timeout=60)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=60)
        elif method == 'PUT':
            # For file uploads, we send raw content
            if isinstance(data, bytes):
                headers['Content-Type'] = 'application/octet-stream'
                response = requests.put(url, headers=headers, data=data, timeout=120)
            else:
                response = requests.put(url, headers=headers, json=data, timeout=60)
        else:
            return None, 'Invalid HTTP method'
        
        if stream:
            return response, None
        
        if response.status_code in [200, 201, 202, 204]:
            if response.content:
                return response.json(), None
            return {}, None
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
            return None, error_msg
            
    except Exception as e:
        return None, str(e)


# ============================================================
# OAuth Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["GET"])
def onedrive_connection_status(request):
    """Get the current OneDrive connection status for the authenticated user."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    
    if onedrive_creds:
        access_token, _ = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
        
        if access_token:
            url = "https://graph.microsoft.com/v1.0/me"
            data, error = make_graph_api_request(url, access_token)
            
            if data and not error:
                return JsonResponse({
                    'connected': True,
                    'accountEmail': data.get('mail') or data.get('userPrincipalName'),
                    'accountName': data.get('displayName')
                })
        
        return JsonResponse({'connected': False})
    else:
        return JsonResponse({'connected': False})


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_initiate_oauth(request):
    """Initiate Microsoft OAuth flow for OneDrive connection."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        data = json.loads(request.body) if request.body else {}
        callback_url = data.get('callback_url')
        
        if not callback_url:
            return JsonResponse({'error': 'Callback URL is required'}, status=400)

        ms_client_id = os.environ.get('MS_CLIENT_ID')
        ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
        
        if not ms_client_id or not ms_client_secret:
            return JsonResponse({'error': 'Microsoft credentials not configured'}, status=500)

        state = str(uuid.uuid4())
        
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$set": {
                    "onedrive_oauth_state": state,
                    "onedrive_oauth_callback": callback_url
                }
            }
        )
        
        # OneDrive scopes for personal accounts with full file access
        scopes = [
            'openid',
            'profile',
            'email',
            'offline_access',
            'User.Read',
            'Files.ReadWrite.All'
        ]
        
        auth_url = (
            f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={ms_client_id}"
            f"&response_type=code"
            f"&redirect_uri={urllib.parse.quote(callback_url, safe='')}"
            f"&scope={urllib.parse.quote(' '.join(scopes), safe='')}"
            f"&state={state}"
            f"&response_mode=query"
        )
        
        return JsonResponse({'auth_url': auth_url})
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_oauth_callback(request):
    """Handle Microsoft OAuth callback and complete the OneDrive connection."""
    try:
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        error_description = request.GET.get('error_description')
        
        if error:
            return JsonResponse({'error': f'OAuth error: {error} - {error_description}'}, status=400)
        
        if not code or not state:
            return JsonResponse({'error': 'Missing OAuth parameters'}, status=400)

        ms_client_id = os.environ.get('MS_CLIENT_ID')
        ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
        
        if not ms_client_id or not ms_client_secret:
            return JsonResponse({'error': 'Microsoft credentials not configured'}, status=500)

        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user = user_collection.find_one({"onedrive_oauth_state": state})
        if not user:
            return JsonResponse({'error': 'Invalid OAuth state'}, status=400)
        
        username = user.get('username')
        callback_url = user.get('onedrive_oauth_callback')
        
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        token_data = {
            'client_id': ms_client_id,
            'client_secret': ms_client_secret,
            'code': code,
            'redirect_uri': callback_url,
            'grant_type': 'authorization_code'
        }
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code == 200:
            token_response = response.json()
            
            access_token = token_response.get('access_token')
            refresh_token = token_response.get('refresh_token')
            expires_in = token_response.get('expires_in', 3600)
            scope = token_response.get('scope', '')
            
            if not access_token:
                return JsonResponse({'error': 'Failed to get access token'}, status=400)
            
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + 'Z'
            
            # Get user info from Microsoft Graph
            user_info_url = "https://graph.microsoft.com/v1.0/me"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
            
            account_email = None
            account_name = None
            if user_info_response.status_code == 200:
                user_info_data = user_info_response.json()
                account_email = user_info_data.get('mail') or user_info_data.get('userPrincipalName')
                account_name = user_info_data.get('displayName')
            
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "onedrive_credentials": {
                            "access_token": access_token,
                            "refresh_token": refresh_token,
                            "expires_at": expires_at,
                            "scope": scope,
                            "account_email": account_email,
                            "account_name": account_name,
                            "connected_at": datetime.utcnow().isoformat()
                        }
                    },
                    "$unset": {
                        "onedrive_oauth_state": "",
                        "onedrive_oauth_callback": ""
                    }
                }
            )
            
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return HttpResponseRedirect(f'{frontend_url}/workspaces?openSettings=true&settingsTab=connections&onedrive_connected=true')
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error_description', 'Failed to exchange code for token')
            return JsonResponse({'error': error_msg}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_disconnect(request):
    """Disconnect user's OneDrive account."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$unset": {
                    "onedrive_credentials": "",
                    "onedrive_oauth_state": "",
                    "onedrive_oauth_callback": "",
                    "onedrive_favorites": ""
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'OneDrive account disconnected successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# ============================================================
# OneDrive File Proxy Endpoints (Microsoft Graph)
# ============================================================

@csrf_exempt
@require_http_methods(["GET"])
def onedrive_list_root_children(request):
    """
    List files and folders in the root of the user's OneDrive.
    Query params: top (pageSize), skipToken (for pagination)
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    top = request.GET.get('top', '100')
    skip_token = request.GET.get('skipToken')
    order_by = request.GET.get('orderBy', 'name asc')
    
    url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    params = {
        '$top': top,
        '$orderby': order_by,
        '$select': 'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,folder,file,parentReference'
    }
    
    if skip_token:
        params['$skiptoken'] = skip_token
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    items = data.get('value', [])
    next_link = data.get('@odata.nextLink')
    
    next_skip_token = None
    if next_link and '$skiptoken=' in next_link:
        import re
        match = re.search(r'\$skiptoken=([^&]+)', next_link)
        if match:
            next_skip_token = match.group(1)
    
    return JsonResponse({
        'items': items,
        'nextSkipToken': next_skip_token
    })


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_list_item_children(request, item_id):
    """
    List files and folders within a specific folder.
    Query params: top (pageSize), skipToken (for pagination)
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    top = request.GET.get('top', '100')
    skip_token = request.GET.get('skipToken')
    order_by = request.GET.get('orderBy', 'name asc')
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/children"
    params = {
        '$top': top,
        '$orderby': order_by,
        '$select': 'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,folder,file,parentReference'
    }
    
    if skip_token:
        params['$skiptoken'] = skip_token
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    items = data.get('value', [])
    next_link = data.get('@odata.nextLink')
    
    next_skip_token = None
    if next_link and '$skiptoken=' in next_link:
        import re
        match = re.search(r'\$skiptoken=([^&]+)', next_link)
        if match:
            next_skip_token = match.group(1)
    
    return JsonResponse({
        'items': items,
        'nextSkipToken': next_skip_token
    })


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_recent_files(request):
    """
    Get recently accessed files from OneDrive.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    top = request.GET.get('top', '50')
    
    url = "https://graph.microsoft.com/v1.0/me/drive/recent"
    params = {
        '$top': top,
        '$select': 'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,folder,file,parentReference'
    }
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    items = data.get('value', [])
    
    return JsonResponse({'items': items})


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_search_files(request):
    """
    Search for files in OneDrive.
    Query params: q (search query), top (max results)
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    query = request.GET.get('q')
    if not query:
        return JsonResponse({'error': 'Search query (q) is required'}, status=400)
    
    top = request.GET.get('top', '50')
    
    # Use the search endpoint
    url = f"https://graph.microsoft.com/v1.0/me/drive/root/search(q='{urllib.parse.quote(query)}')"
    params = {
        '$top': top,
        '$select': 'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,folder,file,parentReference'
    }
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    items = data.get('value', [])
    
    return JsonResponse({'items': items})


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_get_item(request, item_id):
    """
    Get metadata for a specific OneDrive item (file or folder).
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
    params = {
        '$select': 'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,folder,file,parentReference,@microsoft.graph.downloadUrl'
    }
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_download_file(request, item_id):
    """
    Download a file from OneDrive.
    Returns the file content as a binary response.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    # First get file metadata
    metadata_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
    metadata_params = {'$select': 'name,file,@microsoft.graph.downloadUrl'}
    
    metadata, error = make_graph_api_request(metadata_url, access_token, params=metadata_params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    file_name = metadata.get('name', 'download')
    mime_type = metadata.get('file', {}).get('mimeType', 'application/octet-stream')
    download_url = metadata.get('@microsoft.graph.downloadUrl')
    
    if not download_url:
        # Fallback to content endpoint
        download_url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
    
    # Download the file
    try:
        if '@microsoft.graph.downloadUrl' in metadata:
            # Pre-authenticated URL, no auth header needed
            download_resp = requests.get(download_url, timeout=120, stream=True)
        else:
            headers = {'Authorization': f'Bearer {access_token}'}
            download_resp = requests.get(download_url, headers=headers, timeout=120, stream=True)
        
        if download_resp.status_code != 200:
            return JsonResponse({
                'error': f'Failed to download file: HTTP {download_resp.status_code}'
            }, status=download_resp.status_code)
        
        response = HttpResponse(download_resp.content, content_type=mime_type)
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response
        
    except Exception as e:
        return JsonResponse({'error': f'Download failed: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["PUT", "POST"])
def onedrive_update_file(request, item_id):
    """
    Update/overwrite file content in OneDrive.
    For small files (<4MB), uses simple upload. For larger files, would need upload session.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    # Accept both the raw-content contract and the older multipart wrapper shape.
    uploaded_file = request.FILES.get('file')
    content = uploaded_file.read() if uploaded_file else request.body
    
    if len(content) > 4 * 1024 * 1024:  # 4MB limit for simple upload
        return JsonResponse({
            'error': 'File too large. Files over 4MB require upload session (not implemented).'
        }, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/content"
    
    data, error = make_graph_api_request(url, access_token, method='PUT', data=content)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_create_folder(request):
    """
    Create a new folder in OneDrive.
    Expects JSON: { parent_id (optional, defaults to root), name }
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    parent_id = payload.get('parent_id', 'root')
    folder_name = payload.get('name')
    
    if not folder_name:
        return JsonResponse({'error': 'Folder name is required'}, status=400)
    
    if parent_id == 'root':
        url = "https://graph.microsoft.com/v1.0/me/drive/root/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}/children"
    
    folder_data = {
        'name': folder_name,
        'folder': {},
        '@microsoft.graph.conflictBehavior': 'rename'
    }
    
    data, error = make_graph_api_request(url, access_token, method='POST', data=folder_data)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_upload_file(request):
    """
    Upload a new file to OneDrive.
    Expects multipart form data with 'file' and optional 'parent_id'.
    For simple upload (<4MB files).
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    uploaded_file = request.FILES.get('file')
    if not uploaded_file:
        return JsonResponse({'error': 'No file provided'}, status=400)
    
    parent_id = request.POST.get('parent_id', 'root')
    file_name = uploaded_file.name
    content = uploaded_file.read()
    
    if len(content) > 4 * 1024 * 1024:
        return JsonResponse({
            'error': 'File too large. Files over 4MB require upload session (not implemented).'
        }, status=400)
    
    if parent_id == 'root':
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:/{urllib.parse.quote(file_name)}:/content"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{parent_id}:/{urllib.parse.quote(file_name)}:/content"
    
    data, error = make_graph_api_request(url, access_token, method='PUT', data=content)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["PATCH"])
def onedrive_rename_move(request, item_id):
    """
    Rename or move a OneDrive item.
    Expects JSON: { name (optional), parent_id (optional for move) }
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    update_data = {}
    
    if 'name' in payload:
        update_data['name'] = payload['name']
    
    if 'parent_id' in payload:
        update_data['parentReference'] = {'id': payload['parent_id']}
    
    if not update_data:
        return JsonResponse({'error': 'No rename/move parameters provided'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
    
    data, error = make_graph_api_request(url, access_token, method='PATCH', data=update_data)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["DELETE"])
def onedrive_delete_item(request, item_id):
    """
    Delete a OneDrive item (moves to recycle bin).
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
    
    data, error = make_graph_api_request(url, access_token, method='DELETE')
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    # Also track deleted item in Banbury for "recently deleted" feature
    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$push": {
                    "onedrive_deleted_items": {
                        "item_id": item_id,
                        "deleted_at": datetime.utcnow().isoformat()
                    }
                }
            }
        )
    except Exception:
        pass  # Don't fail the delete if tracking fails
    
    return JsonResponse({'success': True, 'message': 'Item deleted successfully'})


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_create_share_link(request, item_id):
    """
    Create a sharing link for a OneDrive item.
    Expects JSON: { type: 'view' | 'edit', scope: 'anonymous' | 'organization' }
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    link_type = payload.get('type', 'view')  # 'view' or 'edit'
    link_scope = payload.get('scope', 'anonymous')  # 'anonymous' or 'organization'
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/createLink"
    
    link_data = {
        'type': link_type,
        'scope': link_scope
    }
    
    data, error = make_graph_api_request(url, access_token, method='POST', data=link_data)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_invite(request, item_id):
    """
    Invite users to access a OneDrive item.
    Expects JSON: { recipients: [{ email }], roles: ['read' | 'write'], message (optional) }
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    recipients = payload.get('recipients', [])
    roles = payload.get('roles', ['read'])
    message = payload.get('message', '')
    
    if not recipients:
        return JsonResponse({'error': 'Recipients are required'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/invite"
    
    invite_data = {
        'recipients': [{'email': r.get('email')} for r in recipients],
        'roles': roles,
        'requireSignIn': True,
        'sendInvitation': True
    }
    
    if message:
        invite_data['message'] = message
    
    data, error = make_graph_api_request(url, access_token, method='POST', data=invite_data)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["GET"])
def onedrive_get_permissions(request, item_id):
    """
    Get sharing permissions for a OneDrive item.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}/permissions"
    
    data, error = make_graph_api_request(url, access_token)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse({'permissions': data.get('value', [])})


# ============================================================
# Banbury-Managed Favorites
# ============================================================

@csrf_exempt
@require_http_methods(["GET"])
def onedrive_favorites_list(request):
    """
    List user's favorite OneDrive items (Banbury-managed).
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    access_token, error = _refresh_onedrive_access_token_if_needed(onedrive_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    # Get favorite item IDs from user document
    favorites = user.get('onedrive_favorites', [])
    
    if not favorites:
        return JsonResponse({'items': []})
    
    # Fetch metadata for each favorite item
    items = []
    for fav in favorites:
        item_id = fav.get('item_id')
        if not item_id:
            continue
        
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{item_id}"
        params = {'$select': 'id,name,size,createdDateTime,lastModifiedDateTime,webUrl,folder,file,parentReference'}
        
        data, error = make_graph_api_request(url, access_token, params=params)
        
        if data and not error:
            data['favorited_at'] = fav.get('favorited_at')
            items.append(data)
    
    return JsonResponse({'items': items})


@csrf_exempt
@require_http_methods(["POST"])
def onedrive_favorites_add(request, item_id):
    """
    Add an item to favorites.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    onedrive_creds = get_onedrive_credentials(user)
    if not onedrive_creds:
        return JsonResponse({'error': 'OneDrive not connected'}, status=400)
    
    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Check if already favorited
        existing = user.get('onedrive_favorites', [])
        if any(f.get('item_id') == item_id for f in existing):
            return JsonResponse({'message': 'Item already in favorites'})
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$push": {
                    "onedrive_favorites": {
                        "item_id": item_id,
                        "favorited_at": datetime.utcnow().isoformat()
                    }
                }
            }
        )
        
        return JsonResponse({'success': True, 'message': 'Item added to favorites'})
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def onedrive_favorites_remove(request, item_id):
    """
    Remove an item from favorites.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$pull": {
                    "onedrive_favorites": {"item_id": item_id}
                }
            }
        )
        
        return JsonResponse({'success': True, 'message': 'Item removed from favorites'})
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# ============================================================
# Banbury-Managed Trash (Recently Deleted)
# ============================================================

@csrf_exempt
@require_http_methods(["GET"])
def onedrive_trash_list(request):
    """
    List recently deleted items (Banbury-managed metadata).
    Note: OneDrive recycle bin isn't fully accessible via Graph for personal accounts,
    so we track deletions in Banbury and provide "Open in OneDrive" fallback.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    deleted_items = user.get('onedrive_deleted_items', [])
    
    # Sort by deletion time, newest first
    deleted_items = sorted(
        deleted_items,
        key=lambda x: x.get('deleted_at', ''),
        reverse=True
    )
    
    # Limit to recent items
    deleted_items = deleted_items[:50]
    
    return JsonResponse({
        'items': deleted_items,
        'note': 'For full recycle bin access, please use OneDrive web interface.'
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def onedrive_trash_clear(request):
    """
    Clear the Banbury-managed deleted items list.
    Note: This doesn't affect the actual OneDrive recycle bin.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {"$unset": {"onedrive_deleted_items": ""}}
        )
        
        return JsonResponse({'success': True, 'message': 'Deleted items list cleared'})
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)

