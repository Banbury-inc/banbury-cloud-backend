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
            'scope': outlook_credentials.get('scope', 'Mail.Read Mail.ReadWrite Mail.Send User.Read Calendars.ReadWrite offline_access')
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
@require_http_methods(["GET"])
def outlook_calendar_status(request):
    """
    Get the calendar-specific connection status for the authenticated user.
    Reports whether the account is connected AND whether Calendar scopes are present.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    
    if not outlook_creds:
        return JsonResponse({
            'connected': False,
            'hasCalendarScope': False,
            'needsReconnect': False
        })
    
    # Check if token is still valid
    access_token, _ = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    
    if not access_token:
        return JsonResponse({
            'connected': False,
            'hasCalendarScope': False,
            'needsReconnect': False
        })
    
    # Verify connection by getting user info
    url = "https://graph.microsoft.com/v1.0/me"
    data, error = make_graph_api_request(url, access_token)
    
    if not data or error:
        return JsonResponse({
            'connected': False,
            'hasCalendarScope': False,
            'needsReconnect': False
        })
    
    # Check if calendar scope is present in stored scopes
    stored_scope = outlook_creds.get('scope', '')
    has_calendar_scope = 'Calendars.ReadWrite' in stored_scope or 'Calendars.Read' in stored_scope
    
    # If connected but missing calendar scope, user needs to reconnect
    needs_reconnect = not has_calendar_scope
    
    return JsonResponse({
        'connected': True,
        'hasCalendarScope': has_calendar_scope,
        'needsReconnect': needs_reconnect,
        'accountEmail': data.get('mail') or data.get('userPrincipalName'),
        'accountName': data.get('displayName')
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
        
        # Required Microsoft OAuth scopes for mail and calendar
        scopes = [
            'openid',
            'profile',
            'email',
            'offline_access',
            'Mail.Read',
            'Mail.ReadWrite',
            'Mail.Send',
            'User.Read',
            'Calendars.ReadWrite'
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
            
            # Redirect to frontend workspaces page with settings modal open
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return HttpResponseRedirect(f'{frontend_url}/workspaces?openSettings=true&settingsTab=connections&outlook_connected=true')
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


# ============================================================================
# OUTLOOK CALENDAR API PROXY ENDPOINTS
# ============================================================================

def _normalize_graph_event_to_calendar_event(graph_event, calendar_id=None):
    """
    Normalize a Microsoft Graph calendar event to match the frontend CalendarEvent interface.
    
    Graph Event fields → CalendarEvent fields:
    - subject → summary
    - bodyPreview / body.content → description
    - location.displayName → location
    - start.dateTime + start.timeZone → start
    - end.dateTime + end.timeZone → end
    - attendees[] → attendees[]
    - webLink → htmlLink
    - organizer → organizer
    - isOrganizer → (used for creator)
    """
    if not graph_event:
        return None
    
    # Build normalized event
    normalized = {
        'id': graph_event.get('id'),
        'calendarId': calendar_id,
        'status': 'confirmed' if not graph_event.get('isCancelled') else 'cancelled',
        'summary': graph_event.get('subject'),
        'description': graph_event.get('bodyPreview') or (graph_event.get('body', {}).get('content') if graph_event.get('body') else None),
        'htmlLink': graph_event.get('webLink'),
    }
    
    # Location
    location = graph_event.get('location')
    if location:
        normalized['location'] = location.get('displayName') or ''
    
    # Start time
    start = graph_event.get('start')
    if start:
        if start.get('dateTime'):
            normalized['start'] = {
                'dateTime': start.get('dateTime'),
                'timeZone': start.get('timeZone')
            }
        elif start.get('date'):
            normalized['start'] = {
                'date': start.get('date')
            }
    
    # End time
    end = graph_event.get('end')
    if end:
        if end.get('dateTime'):
            normalized['end'] = {
                'dateTime': end.get('dateTime'),
                'timeZone': end.get('timeZone')
            }
        elif end.get('date'):
            normalized['end'] = {
                'date': end.get('date')
            }
    
    # Organizer
    organizer = graph_event.get('organizer')
    if organizer:
        email_addr = organizer.get('emailAddress', {})
        normalized['organizer'] = {
            'email': email_addr.get('address'),
            'displayName': email_addr.get('name')
        }
        # Use organizer as creator too (Graph doesn't have separate creator)
        normalized['creator'] = normalized['organizer']
    
    # Attendees
    attendees = graph_event.get('attendees', [])
    if attendees:
        normalized['attendees'] = []
        for attendee in attendees:
            email_addr = attendee.get('emailAddress', {})
            response_status = attendee.get('status', {}).get('response', 'needsAction')
            # Map Graph response status to Google Calendar format
            status_map = {
                'none': 'needsAction',
                'organizer': 'accepted',
                'tentativelyAccepted': 'tentative',
                'accepted': 'accepted',
                'declined': 'declined',
                'notResponded': 'needsAction'
            }
            normalized['attendees'].append({
                'email': email_addr.get('address'),
                'displayName': email_addr.get('name'),
                'responseStatus': status_map.get(response_status, 'needsAction')
            })
    
    # Online meeting link (similar to hangoutLink)
    if graph_event.get('onlineMeeting'):
        normalized['hangoutLink'] = graph_event.get('onlineMeeting', {}).get('joinUrl')
    elif graph_event.get('onlineMeetingUrl'):
        normalized['hangoutLink'] = graph_event.get('onlineMeetingUrl')
    
    return normalized


def _normalize_graph_calendar_to_calendar_list_entry(graph_calendar):
    """
    Normalize a Microsoft Graph calendar to match the frontend CalendarListEntry interface.
    
    Graph Calendar fields → CalendarListEntry fields:
    - id → id
    - name → summary
    - color → backgroundColor (map to hex)
    - isDefaultCalendar → primary
    - canEdit → accessRole
    """
    if not graph_calendar:
        return None
    
    # Map Graph calendar colors to hex values
    color_map = {
        'auto': '#0078D4',
        'lightBlue': '#69AFE5',
        'lightGreen': '#7BD148',
        'lightOrange': '#FFB878',
        'lightGray': '#A4BDFC',
        'lightYellow': '#FBD75B',
        'lightTeal': '#51B749',
        'lightPink': '#DC2127',
        'lightBrown': '#8D6E63',
        'lightRed': '#E57373',
        'maxColor': '#795548'
    }
    
    graph_color = graph_calendar.get('color', 'auto')
    hex_color = color_map.get(graph_color, '#0078D4')
    
    # Determine access role
    can_edit = graph_calendar.get('canEdit', False)
    can_share = graph_calendar.get('canShare', False)
    is_owner = graph_calendar.get('isOwner', False)
    
    if is_owner:
        access_role = 'owner'
    elif can_share:
        access_role = 'writer'
    elif can_edit:
        access_role = 'writer'
    else:
        access_role = 'reader'
    
    return {
        'id': graph_calendar.get('id'),
        'summary': graph_calendar.get('name'),
        'description': None,  # Graph calendars don't have descriptions in list
        'summaryOverride': None,
        'colorId': graph_color,
        'backgroundColor': hex_color,
        'foregroundColor': '#FFFFFF',
        'hidden': not graph_calendar.get('isVisible', True),
        'selected': graph_calendar.get('isVisible', True),
        'primary': graph_calendar.get('isDefaultCalendar', False),
        'accessRole': access_role,
        'timeZone': None  # Would need separate call to get this
    }


def _convert_calendar_event_to_graph_event(event_data):
    """
    Convert frontend CalendarEvent format to Microsoft Graph event format for create/update.
    """
    if not event_data:
        return {}
    
    graph_event = {}
    
    # Summary → Subject
    if 'summary' in event_data:
        graph_event['subject'] = event_data['summary']
    
    # Description → Body
    if 'description' in event_data:
        graph_event['body'] = {
            'contentType': 'HTML' if '<' in str(event_data.get('description', '')) and '>' in str(event_data.get('description', '')) else 'text',
            'content': event_data['description'] or ''
        }
    
    # Location
    if 'location' in event_data:
        graph_event['location'] = {
            'displayName': event_data['location'] or ''
        }
    
    # Start time
    if 'start' in event_data:
        start = event_data['start']
        if isinstance(start, dict):
            if start.get('dateTime'):
                graph_event['start'] = {
                    'dateTime': start['dateTime'],
                    'timeZone': start.get('timeZone', 'UTC')
                }
            elif start.get('date'):
                # All-day event
                graph_event['start'] = {
                    'dateTime': f"{start['date']}T00:00:00",
                    'timeZone': start.get('timeZone', 'UTC')
                }
                graph_event['isAllDay'] = True
    
    # End time
    if 'end' in event_data:
        end = event_data['end']
        if isinstance(end, dict):
            if end.get('dateTime'):
                graph_event['end'] = {
                    'dateTime': end['dateTime'],
                    'timeZone': end.get('timeZone', 'UTC')
                }
            elif end.get('date'):
                # All-day event
                graph_event['end'] = {
                    'dateTime': f"{end['date']}T23:59:59",
                    'timeZone': end.get('timeZone', 'UTC')
                }
    
    # Attendees
    if 'attendees' in event_data and event_data['attendees']:
        graph_event['attendees'] = []
        for attendee in event_data['attendees']:
            if isinstance(attendee, dict) and attendee.get('email'):
                graph_event['attendees'].append({
                    'emailAddress': {
                        'address': attendee['email'],
                        'name': attendee.get('displayName', attendee['email'])
                    },
                    'type': 'required'
                })
    
    return graph_event


@csrf_exempt
@require_http_methods(["GET"])
def outlook_calendar_status(request):
    """
    Get the current Outlook Calendar connection status for the authenticated user.
    Returns connected status and whether Calendar scopes are present.
    """
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    outlook_creds = get_outlook_credentials(user)
    
    if not outlook_creds:
        return JsonResponse({
            'connected': False,
            'hasCalendarScope': False
        })
    
    # Check if Calendar scope is present
    scope = outlook_creds.get('scope', '')
    has_calendar_scope = 'Calendars.Read' in scope or 'Calendars.ReadWrite' in scope
    
    # Verify token is still valid
    access_token, _ = _refresh_outlook_access_token_if_needed(outlook_creds, user)
    
    if access_token:
        # Try to get user profile from Graph API
        url = "https://graph.microsoft.com/v1.0/me"
        data, error = make_graph_api_request(url, access_token)
        
        if data and not error:
            return JsonResponse({
                'connected': True,
                'hasCalendarScope': has_calendar_scope,
                'accountEmail': data.get('mail') or data.get('userPrincipalName'),
                'accountName': data.get('displayName')
            })
    
    return JsonResponse({
        'connected': False,
        'hasCalendarScope': False
    })


@csrf_exempt
@require_http_methods(["GET"])
def outlook_list_calendars(request):
    """
    List Outlook calendars for the authenticated user.
    Returns: { items: CalendarListEntry[], nextPageToken?: string }
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
    max_results = request.GET.get('maxResults', '100')
    skip_token = request.GET.get('pageToken')
    
    url = "https://graph.microsoft.com/v1.0/me/calendars"
    params = {
        '$top': max_results,
        '$select': 'id,name,color,isDefaultCalendar,canEdit,canShare,canViewPrivateItems,isOwner,owner'
    }
    
    if skip_token:
        params['$skip'] = skip_token
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    # Normalize calendars to CalendarListEntry format
    calendars = data.get('value', [])
    normalized_calendars = [
        _normalize_graph_calendar_to_calendar_list_entry(cal)
        for cal in calendars
    ]
    
    # Extract next page token
    next_link = data.get('@odata.nextLink')
    next_page_token = None
    if next_link and '$skip=' in next_link:
        import re
        match = re.search(r'\$skip=(\d+)', next_link)
        if match:
            next_page_token = match.group(1)
    
    return JsonResponse({
        'items': normalized_calendars,
        'nextPageToken': next_page_token
    })


@csrf_exempt
@require_http_methods(["GET", "POST"])
def outlook_calendar_events(request):
    """
    List or create Outlook calendar events.
    
    GET: list events
        Query params: calendarId, timeMin, timeMax, maxResults, pageToken, q, singleEvents, orderBy
        Returns: { items: CalendarEvent[], nextPageToken?: string }
    
    POST: create event
        Body: { calendarId?: string, event: CalendarEvent }
        Returns: CalendarEvent
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
    
    if request.method == "GET":
        return _outlook_list_events(request, access_token)
    
    if request.method == "POST":
        return _outlook_create_event(request, access_token)
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)


def _outlook_list_events(request, access_token):
    """List Outlook calendar events."""
    calendar_id = request.GET.get('calendarId')
    time_min = request.GET.get('timeMin')
    time_max = request.GET.get('timeMax')
    max_results = request.GET.get('maxResults', '250')
    skip_token = request.GET.get('pageToken')
    search_query = request.GET.get('q')
    order_by = request.GET.get('orderBy', 'start/dateTime')
    
    # Build URL - use specific calendar or default
    if calendar_id:
        url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"
    else:
        url = "https://graph.microsoft.com/v1.0/me/calendar/events"
    
    params = {
        '$top': max_results,
        '$select': 'id,subject,bodyPreview,body,start,end,location,organizer,attendees,webLink,onlineMeeting,onlineMeetingUrl,isCancelled,isAllDay,recurrence',
        '$orderby': order_by
    }
    
    # Build filter for time range
    filters = []
    if time_min:
        filters.append(f"start/dateTime ge '{time_min}'")
    if time_max:
        filters.append(f"end/dateTime le '{time_max}'")
    
    if filters:
        params['$filter'] = ' and '.join(filters)
    
    if skip_token:
        params['$skip'] = skip_token
    
    if search_query:
        # Use $search for text search (requires different endpoint)
        params['$search'] = f'"{search_query}"'
    
    data, error = make_graph_api_request(url, access_token, params=params)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    # Normalize events to CalendarEvent format
    events = data.get('value', [])
    normalized_events = [
        _normalize_graph_event_to_calendar_event(evt, calendar_id)
        for evt in events
    ]
    
    # Extract next page token
    next_link = data.get('@odata.nextLink')
    next_page_token = None
    if next_link:
        import re
        # Check for $skip or $skiptoken
        skip_match = re.search(r'\$skip=(\d+)', next_link)
        skiptoken_match = re.search(r'\$skiptoken=([^&]+)', next_link)
        if skip_match:
            next_page_token = skip_match.group(1)
        elif skiptoken_match:
            next_page_token = skiptoken_match.group(1)
    
    return JsonResponse({
        'items': normalized_events,
        'nextPageToken': next_page_token
    })


def _outlook_create_event(request, access_token):
    """Create a new Outlook calendar event."""
    try:
        payload = json.loads(request.body or '{}')
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    calendar_id = payload.get('calendarId')
    event_data = payload.get('event', {})
    
    if not event_data:
        return JsonResponse({'error': 'Event data is required'}, status=400)
    
    # Convert to Graph event format
    graph_event = _convert_calendar_event_to_graph_event(event_data)
    
    # Build URL
    if calendar_id:
        url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events"
    else:
        url = "https://graph.microsoft.com/v1.0/me/calendar/events"
    
    data, error = make_graph_api_request(url, access_token, method='POST', data=graph_event)
    
    if error:
        return JsonResponse({'error': error}, status=500)
    
    # Return normalized event
    normalized = _normalize_graph_event_to_calendar_event(data, calendar_id)
    return JsonResponse(normalized)


@csrf_exempt
@require_http_methods(["GET", "PUT", "DELETE"])
def outlook_calendar_event_detail(request, event_id):
    """
    Get, update, or delete a single Outlook calendar event by ID.
    
    GET: get event details
        Query params: calendarId (optional)
        Returns: CalendarEvent
    
    PUT: update event
        Query params: calendarId (optional)
        Body: { calendarId?: string, event: Partial<CalendarEvent> }
        Returns: CalendarEvent
    
    DELETE: delete event
        Query params: calendarId (optional)
        Returns: { success: true }
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
    
    calendar_id = request.GET.get('calendarId')
    
    # Build URL
    if calendar_id:
        url = f"https://graph.microsoft.com/v1.0/me/calendars/{calendar_id}/events/{event_id}"
    else:
        url = f"https://graph.microsoft.com/v1.0/me/events/{event_id}"
    
    if request.method == "GET":
        params = {
            '$select': 'id,subject,bodyPreview,body,start,end,location,organizer,attendees,webLink,onlineMeeting,onlineMeetingUrl,isCancelled,isAllDay,recurrence'
        }
        data, error = make_graph_api_request(url, access_token, params=params)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        normalized = _normalize_graph_event_to_calendar_event(data, calendar_id)
        return JsonResponse(normalized)
    
    if request.method == "PUT":
        try:
            payload = json.loads(request.body or '{}')
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)
        
        event_data = payload.get('event', {})
        calendar_id = payload.get('calendarId') or calendar_id
        
        # Convert to Graph event format
        graph_event = _convert_calendar_event_to_graph_event(event_data)
        
        data, error = make_graph_api_request(url, access_token, method='PATCH', data=graph_event)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        normalized = _normalize_graph_event_to_calendar_event(data, calendar_id)
        return JsonResponse(normalized)
    
    if request.method == "DELETE":
        data, error = make_graph_api_request(url, access_token, method='DELETE')
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        return JsonResponse({'success': True})
    
    return JsonResponse({'error': 'Method not allowed'}, status=405)

