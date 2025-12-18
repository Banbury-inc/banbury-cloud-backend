"""
Outlook/Microsoft Graph integration views for Banbury backend.
Handles OAuth flow and API proxy endpoints for Outlook Mail.
"""
import os
import json
import urllib.parse
from datetime import datetime, timedelta
from django.http import JsonResponse, HttpResponseRedirect
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
        
        # Get user from database
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user = user_collection.find_one({"username": username})
        
        if not user:
            return None, JsonResponse({'message': 'User not found'}, status=404)
            
        return user, None
        
    except Exception as e:
        return None, JsonResponse({'message': str(e)}, status=401)


def get_outlook_credentials(user):
    """Get Outlook credentials from user document."""
    outlook_creds = user.get('outlook_credentials', {})
    if not outlook_creds.get('access_token'):
        return None
    return outlook_creds


def _refresh_outlook_access_token_if_needed(outlook_credentials, user_doc):
    """
    Ensure we have a valid access token; refresh using refresh_token when required.
    Returns (access_token, error_message).
    """
    if not outlook_credentials:
        return None, "No Outlook credentials found"
    
    access_token = outlook_credentials.get('access_token')
    refresh_token = outlook_credentials.get('refresh_token')
    expires_at = outlook_credentials.get('expires_at')
    
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
            # If we can't parse expiry, try to use the token anyway
            pass
    
    if not needs_refresh:
        return access_token, None
    
    # Need to refresh the token
    if not refresh_token:
        return None, "Token expired and no refresh token available"
    
    ms_client_id = os.environ.get('MS_CLIENT_ID')
    ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
    
    if not ms_client_id or not ms_client_secret:
        return access_token, None  # Return existing token if we can't refresh
    
    try:
        token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
        token_data = {
            'client_id': ms_client_id,
            'client_secret': ms_client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token',
            'scope': outlook_credentials.get('scope', 'Mail.Read Mail.ReadWrite Mail.Send User.Read offline_access')
        }
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code == 200:
            token_response = response.json()
            new_access_token = token_response.get('access_token')
            new_refresh_token = token_response.get('refresh_token', refresh_token)
            expires_in = token_response.get('expires_in', 3600)
            new_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + 'Z'
            
            # Update credentials in database
            client = get_mongo_client()
            db = client["NeuraNet"]
            user_collection = db["users"]
            
            user_collection.update_one(
                {"_id": user_doc.get("_id")},
                {
                    "$set": {
                        "outlook_credentials.access_token": new_access_token,
                        "outlook_credentials.refresh_token": new_refresh_token,
                        "outlook_credentials.expires_at": new_expires_at
                    }
                }
            )
            
            return new_access_token, None
        else:
            # Token refresh failed, return existing token
            return access_token, None
            
    except Exception as e:
        print(f"Error refreshing Outlook token: {e}")
        return access_token, None


def make_graph_api_request(url, access_token, method='GET', data=None, params=None):
    """Make a request to Microsoft Graph API."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == 'PATCH':
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            return None, 'Invalid HTTP method'
        
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


# OAuth Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def outlook_connection_status(request):
    """Get the current Outlook connection status for the authenticated user."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    
    if outlook_creds:
        # Verify token is still valid by getting user info
        access_token, _ = _refresh_outlook_access_token_if_needed(outlook_creds, user)
        
        if access_token:
            # Try to get user profile from Graph API
            url = "https://graph.microsoft.com/v1.0/me"
            data, error = make_graph_api_request(url, access_token)
            
            if data and not error:
                return JsonResponse({
                    'connected': True,
                    'accountEmail': data.get('mail') or data.get('userPrincipalName'),
                    'accountName': data.get('displayName')
                })
        
        # Token invalid, treat as not connected
        return JsonResponse({
            'connected': False
        })
    else:
        return JsonResponse({
            'connected': False
        })


@csrf_exempt
@require_http_methods(["POST"])
def outlook_initiate_oauth(request):
    """Initiate Microsoft OAuth flow for Outlook connection."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        # Parse request body
        data = json.loads(request.body) if request.body else {}
        callback_url = data.get('callback_url')
        
        if not callback_url:
            return JsonResponse({'error': 'Callback URL is required'}, status=400)

        # Get Microsoft OAuth credentials from environment
        ms_client_id = os.environ.get('MS_CLIENT_ID')
        ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
        
        if not ms_client_id or not ms_client_secret:
            return JsonResponse({'error': 'Microsoft credentials not configured'}, status=500)

        # Generate state parameter to prevent CSRF
        import uuid
        state = str(uuid.uuid4())
        
        # Store state temporarily in user document
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$set": {
                    "outlook_oauth_state": state,
                    "outlook_oauth_callback": callback_url
                }
            }
        )
        
        # Required Microsoft OAuth scopes for mail
        scopes = [
            'openid',
            'profile',
            'email',
            'offline_access',
            'Mail.Read',
            'Mail.ReadWrite',
            'Mail.Send',
            'User.Read'
        ]
        
        # Generate authorization URL (using common tenant for multi-tenant)
        auth_url = (
            f"https://login.microsoftonline.com/common/oauth2/v2.0/authorize?"
            f"client_id={ms_client_id}"
            f"&response_type=code"
            f"&redirect_uri={urllib.parse.quote(callback_url, safe='')}"
            f"&scope={urllib.parse.quote(' '.join(scopes), safe='')}"
            f"&state={state}"
            f"&response_mode=query"
        )
        
        return JsonResponse({
            'auth_url': auth_url
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def outlook_oauth_callback(request):
    """Handle Microsoft OAuth callback and complete the connection."""
    try:
        # Get OAuth parameters
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        error_description = request.GET.get('error_description')
        
        if error:
            return JsonResponse({'error': f'OAuth error: {error} - {error_description}'}, status=400)
        
        if not code or not state:
            return JsonResponse({'error': 'Missing OAuth parameters'}, status=400)

        # Get Microsoft OAuth credentials from environment
        ms_client_id = os.environ.get('MS_CLIENT_ID')
        ms_client_secret = os.environ.get('MS_CLIENT_SECRET')
        
        if not ms_client_id or not ms_client_secret:
            return JsonResponse({'error': 'Microsoft credentials not configured'}, status=500)

        # Find user by OAuth state
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user = user_collection.find_one({"outlook_oauth_state": state})
        if not user:
            return JsonResponse({'error': 'Invalid OAuth state'}, status=400)
        
        username = user.get('username')
        callback_url = user.get('outlook_oauth_callback')
        
        # Exchange code for access token
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
            
            # Calculate expiry time
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
            
            # Store the credentials
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "outlook_credentials": {
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
                        "outlook_oauth_state": "",
                        "outlook_oauth_callback": ""
                    }
                }
            )
            
            # Redirect to frontend settings page with success
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return HttpResponseRedirect(f'{frontend_url}/settings?tab=connections&outlook_connected=true')
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error_description', 'Failed to exchange code for token')
            return JsonResponse({'error': error_msg}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def outlook_disconnect(request):
    """Disconnect user's Outlook account."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        # Remove Outlook credentials from user document
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$unset": {
                    "outlook_credentials": "",
                    "outlook_oauth_state": "",
                    "outlook_oauth_callback": ""
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Outlook account disconnected successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# Outlook Mail API Proxy Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def outlook_list_messages(request):
    """
    List Outlook messages for the authenticated user.
    Query params: folderId, maxResults (top), pageToken (skip), q (filter/search)
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    # Get query parameters
    folder_id = request.GET.get('folderId', 'inbox')
    max_results = request.GET.get('maxResults', '25')
    skip_token = request.GET.get('pageToken')
    search_query = request.GET.get('q')
    
    # Build Graph API URL
    if folder_id.lower() in ['inbox', 'sentitems', 'drafts', 'deleteditems', 'junkemail']:
        base_url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
    else:
        base_url = f"https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}/messages"
    
    params = {
        '$top': max_results,
        '$orderby': 'receivedDateTime desc',
        '$select': 'id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead,hasAttachments,flag,parentFolderId,conversationId'
    }
    
    if skip_token:
        params['$skip'] = skip_token
    
    if search_query:
        params['$search'] = f'"{search_query}"'
    
    data, error = make_graph_api_request(base_url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    # Format response to match Gmail-like structure
    messages = data.get('value', [])
    next_link = data.get('@odata.nextLink')
    
    # Extract skip token from next link if present
    next_page_token = None
    if next_link and '$skip=' in next_link:
        import re
        match = re.search(r'\$skip=(\d+)', next_link)
        if match:
            next_page_token = match.group(1)
    
    return JsonResponse({
        'messages': messages,
        'nextPageToken': next_page_token
    })


@csrf_exempt
@require_http_methods(["GET"])
def outlook_get_message(request, message_id):
    """Get a specific Outlook message by ID (full format)."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
    params = {
        '$select': 'id,subject,from,toRecipients,ccRecipients,bccRecipients,receivedDateTime,sentDateTime,body,bodyPreview,isRead,hasAttachments,flag,parentFolderId,conversationId,internetMessageHeaders,attachments'
    }
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def outlook_get_messages_batch(request):
    """Get multiple Outlook messages in a single batch request."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    message_ids = payload.get('messageIds', [])
    if not message_ids:
        return JsonResponse({'error': 'No message IDs provided'}, status=400)
    
    # Use concurrent requests for better performance
    import concurrent.futures
    
    messages = {}
    
    def fetch_message(msg_id):
        try:
            url = f"https://graph.microsoft.com/v1.0/me/messages/{msg_id}"
            params = {
                '$select': 'id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead,hasAttachments,flag,parentFolderId,conversationId'
            }
            data, err = make_graph_api_request(url, access_token, params=params)
            if data and not err:
                return msg_id, data
            else:
                return msg_id, {"error": err}
        except Exception as e:
            return msg_id, {"error": str(e)}
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        future_to_id = {executor.submit(fetch_message, msg_id): msg_id for msg_id in message_ids}
        
        for future in concurrent.futures.as_completed(future_to_id):
            message_id, result = future.result()
            messages[message_id] = result
    
    return JsonResponse({'messages': messages})


@csrf_exempt
@require_http_methods(["GET"])
def outlook_list_folders(request):
    """List Outlook mail folders (equivalent to Gmail labels)."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    url = "https://graph.microsoft.com/v1.0/me/mailFolders"
    params = {
        '$top': '100',
        '$select': 'id,displayName,parentFolderId,childFolderCount,unreadItemCount,totalItemCount'
    }
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    folders = data.get('value', [])
    
    # Format folders to match Gmail-like label structure
    formatted_folders = []
    for folder in folders:
        folder_type = 'user'
        # Mark well-known folders as system
        well_known = ['inbox', 'sentitems', 'drafts', 'deleteditems', 'junkemail', 'outbox', 'archive']
        if folder.get('displayName', '').lower().replace(' ', '') in well_known:
            folder_type = 'system'
        
        formatted_folders.append({
            'id': folder.get('id'),
            'name': folder.get('displayName'),
            'type': folder_type,
            'parentFolderId': folder.get('parentFolderId'),
            'messagesUnread': folder.get('unreadItemCount', 0),
            'messagesTotal': folder.get('totalItemCount', 0)
        })
    
    return JsonResponse({'folders': formatted_folders})


@csrf_exempt
@require_http_methods(["POST"])
def outlook_send_message(request):
    """Send an email via Outlook. Expects JSON: to, subject, body (HTML allowed), cc?, bcc?"""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    to_addr = payload.get('to')
    subject = payload.get('subject', '')
    body = payload.get('body', '')
    cc = payload.get('cc')
    bcc = payload.get('bcc')
    is_draft = payload.get('isDraft', False)
    
    if not is_draft and not to_addr:
        return JsonResponse({'error': 'Recipient "to" is required'}, status=400)
    
    # Build message object
    message = {
        'subject': subject,
        'body': {
            'contentType': 'HTML' if '<' in body and '>' in body else 'Text',
            'content': body
        }
    }
    
    # Parse recipients
    def parse_recipients(addr_string):
        if not addr_string:
            return []
        addresses = [a.strip() for a in addr_string.split(',') if a.strip()]
        return [{'emailAddress': {'address': addr}} for addr in addresses]
    
    if to_addr:
        message['toRecipients'] = parse_recipients(to_addr)
    if cc:
        message['ccRecipients'] = parse_recipients(cc)
    if bcc:
        message['bccRecipients'] = parse_recipients(bcc)
    
    if is_draft:
        # Create draft
        url = "https://graph.microsoft.com/v1.0/me/messages"
        data, error = make_graph_api_request(url, access_token, method='POST', data=message)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse(data)
    else:
        # Send message
        url = "https://graph.microsoft.com/v1.0/me/sendMail"
        send_payload = {
            'message': message,
            'saveToSentItems': True
        }
        
        data, error = make_graph_api_request(url, access_token, method='POST', data=send_payload)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse({'success': True, 'message': 'Email sent successfully'})


@csrf_exempt
@require_http_methods(["POST"])
def outlook_send_reply(request):
    """Send a reply to an existing Outlook message."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    original_message_id = payload.get('original_message_id')
    comment = payload.get('body', '')
    
    if not original_message_id:
        return JsonResponse({'error': 'original_message_id is required'}, status=400)
    
    # Use Graph API reply endpoint
    url = f"https://graph.microsoft.com/v1.0/me/messages/{original_message_id}/reply"
    reply_payload = {
        'comment': comment
    }
    
    data, error = make_graph_api_request(url, access_token, method='POST', data=reply_payload)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    return JsonResponse({'success': True, 'message': 'Reply sent successfully'})


@csrf_exempt
@require_http_methods(["POST"])
def outlook_modify_message(request, message_id):
    """
    Modify an Outlook message.
    Supports: marking read/unread, flagging/unflagging (star), moving to folder, deleting.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    # Handle different modification types
    action = payload.get('action')
    
    if action == 'delete':
        # Move to deleted items (soft delete)
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/move"
        data, error = make_graph_api_request(url, access_token, method='POST', data={'destinationId': 'deleteditems'})
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse({'success': True, 'message': 'Message deleted'})
    
    elif action == 'permanentDelete':
        # Permanently delete
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
        data, error = make_graph_api_request(url, access_token, method='DELETE')
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse({'success': True, 'message': 'Message permanently deleted'})
    
    elif action == 'move':
        # Move to folder
        destination_folder = payload.get('destinationFolderId')
        if not destination_folder:
            return JsonResponse({'error': 'destinationFolderId is required for move action'}, status=400)
        
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/move"
        data, error = make_graph_api_request(url, access_token, method='POST', data={'destinationId': destination_folder})
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse(data)
    
    else:
        # Default: PATCH message properties (read/unread, flag)
        update_data = {}
        
        if 'isRead' in payload:
            update_data['isRead'] = payload['isRead']
        
        if 'flag' in payload:
            # flag can be: 'flagged', 'notFlagged', 'complete'
            flag_status = payload['flag']
            update_data['flag'] = {'flagStatus': flag_status}
        
        # Handle Gmail-like label operations
        add_labels = payload.get('addLabelIds', [])
        remove_labels = payload.get('removeLabelIds', [])
        
        # Map STARRED to flag
        if 'STARRED' in add_labels:
            update_data['flag'] = {'flagStatus': 'flagged'}
        if 'STARRED' in remove_labels:
            update_data['flag'] = {'flagStatus': 'notFlagged'}
        
        # Map UNREAD
        if 'UNREAD' in add_labels:
            update_data['isRead'] = False
        if 'UNREAD' in remove_labels:
            update_data['isRead'] = True
        
        if not update_data:
            return JsonResponse({'error': 'No valid update properties provided'}, status=400)
        
        url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}"
        data, error = make_graph_api_request(url, access_token, method='PATCH', data=update_data)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse(data)


@csrf_exempt
@require_http_methods(["GET"])
def outlook_get_attachment(request, message_id, attachment_id):
    """Get an Outlook message attachment."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    url = f"https://graph.microsoft.com/v1.0/me/messages/{message_id}/attachments/{attachment_id}"
    data, error = make_graph_api_request(url, access_token)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    # Return attachment data (contentBytes is base64 encoded)
    return JsonResponse({
        'id': data.get('id'),
        'name': data.get('name'),
        'contentType': data.get('contentType'),
        'size': data.get('size'),
        'data': data.get('contentBytes')  # Base64 encoded content
    })


@csrf_exempt
@require_http_methods(["GET"])
def outlook_get_thread(request, conversation_id):
    """Get all messages in a conversation/thread."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    if not outlook_creds:
        return JsonResponse({'error': 'Outlook not connected'}, status=400)
    
    access_token, error = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    if error or not access_token:
        return JsonResponse({'error': error or 'Failed to get access token'}, status=400)
    
    # Get all messages with this conversationId
    url = "https://graph.microsoft.com/v1.0/me/messages"
    params = {
        '$filter': f"conversationId eq '{conversation_id}'",
        '$orderby': 'receivedDateTime asc',
        '$select': 'id,subject,from,toRecipients,receivedDateTime,bodyPreview,isRead,hasAttachments,flag'
    }
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    messages = data.get('value', [])
    
    return JsonResponse({
        'result': 'success',
        'id': conversation_id,
        'messages': messages
    })

