"""
Slack integration views for Banbury backend.
Handles OAuth flow and API proxy endpoints for Slack.
"""
import os
import json
from datetime import datetime
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


def get_slack_credentials(user):
    """Get Slack credentials from user document."""
    slack_creds = user.get('slack_credentials', {})
    if not slack_creds.get('access_token'):
        return None
    return slack_creds


def make_slack_api_request(url, access_token, method='GET', data=None):
    """Make a request to Slack API."""
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, timeout=30)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=30)
        else:
            return None, 'Invalid HTTP method'
        
        if response.status_code == 200:
            return response.json(), None
        else:
            error_data = response.json() if response.content else {}
            error_msg = error_data.get('error', f'HTTP {response.status_code}')
            return None, error_msg
            
    except Exception as e:
        return None, str(e)


def resolve_channel_id(channel_name_or_id, access_token):
    """
    Resolve a channel name to its ID. If already an ID, return as-is.
    Slack channel IDs start with 'C' or 'G' (for private groups).
    """
    # If it looks like a channel ID already, return it
    if channel_name_or_id and (channel_name_or_id.startswith('C') or channel_name_or_id.startswith('G')):
        return channel_name_or_id, None
    
    # Strip '#' if present
    channel_name = channel_name_or_id.lstrip('#')
    
    # Fetch all channels to find the matching name
    url = "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=1000"
    data, error = make_slack_api_request(url, access_token)
    
    if error:
        return None, f"Failed to resolve channel: {error}"
    
    if not data.get('ok'):
        return None, f"Failed to resolve channel: {data.get('error', 'Unknown error')}"
    
    # Find channel by name
    channels = data.get('channels', [])
    for channel in channels:
        if channel.get('name') == channel_name:
            return channel.get('id'), None
    
    return None, f"Channel '{channel_name}' not found"


# OAuth Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def slack_connection_status(request):
    """Get the current Slack connection status for the authenticated user."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    slack_creds = get_slack_credentials(user)
    
    if slack_creds:
        return JsonResponse({
            'connected': True,
            'teamName': slack_creds.get('team_name'),
            'userName': slack_creds.get('user_name')
        })
    else:
        return JsonResponse({
            'connected': False
        })


@csrf_exempt
@require_http_methods(["POST"])
def slack_initiate_oauth(request):
    """Initiate Slack OAuth flow for user connection."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        # Parse request body
        data = json.loads(request.body) if request.body else {}
        callback_url = data.get('callback_url')
        
        if not callback_url:
            return JsonResponse({'error': 'Callback URL is required'}, status=400)

        # Get Slack OAuth credentials from environment
        slack_client_id = os.environ.get('SLACK_CLIENT_ID')
        slack_client_secret = os.environ.get('SLACK_CLIENT_SECRET')
        
        if not slack_client_id or not slack_client_secret:
            return JsonResponse({'error': 'Slack credentials not configured'}, status=500)

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
                    "slack_oauth_state": state,
                    "slack_oauth_callback": callback_url
                }
            }
        )
        
        # Required Slack OAuth scopes
        scopes = [
            'channels:history',
            'channels:read',
            'chat:write',
            'users:read',
            'reactions:write',
            'groups:history',
            'groups:read',
            'search:read'
        ]
        
        # Generate authorization URL
        auth_url = (
            f"https://slack.com/oauth/v2/authorize?"
            f"client_id={slack_client_id}"
            f"&redirect_uri={callback_url}"
            f"&scope={' '.join(scopes)}"
            f"&state={state}"
        )
        
        return JsonResponse({
            'auth_url': auth_url
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def slack_oauth_callback(request):
    """Handle Slack OAuth callback and complete the connection."""
    try:
        # Get OAuth parameters
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            return JsonResponse({'error': f'OAuth error: {error}'}, status=400)
        
        if not code or not state:
            return JsonResponse({'error': 'Missing OAuth parameters'}, status=400)

        # Get Slack OAuth credentials from environment
        slack_client_id = os.environ.get('SLACK_CLIENT_ID')
        slack_client_secret = os.environ.get('SLACK_CLIENT_SECRET')
        
        if not slack_client_id or not slack_client_secret:
            return JsonResponse({'error': 'Slack credentials not configured'}, status=500)

        # Find user by OAuth state
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user = user_collection.find_one({"slack_oauth_state": state})
        if not user:
            return JsonResponse({'error': 'Invalid OAuth state'}, status=400)
        
        username = user.get('username')
        callback_url = user.get('slack_oauth_callback')
        
        # Exchange code for access token
        token_url = "https://slack.com/api/oauth.v2.access"
        token_data = {
            'client_id': slack_client_id,
            'client_secret': slack_client_secret,
            'code': code,
            'redirect_uri': callback_url
        }
        
        response = requests.post(token_url, data=token_data, timeout=30)
        
        if response.status_code == 200:
            token_response = response.json()
            
            if not token_response.get('ok'):
                error_msg = token_response.get('error', 'Unknown error')
                return JsonResponse({'error': f'Slack OAuth error: {error_msg}'}, status=400)
            
            # Extract credentials
            access_token = token_response.get('access_token')
            team_id = token_response.get('team', {}).get('id')
            team_name = token_response.get('team', {}).get('name')
            authed_user = token_response.get('authed_user', {})
            user_id = authed_user.get('id')
            
            # Get user info from Slack
            user_info_url = f"https://slack.com/api/users.info?user={user_id}"
            headers = {'Authorization': f'Bearer {access_token}'}
            user_info_response = requests.get(user_info_url, headers=headers, timeout=30)
            
            user_name = None
            if user_info_response.status_code == 200:
                user_info_data = user_info_response.json()
                if user_info_data.get('ok'):
                    user_name = user_info_data.get('user', {}).get('name')
            
            # Store the credentials
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "slack_credentials": {
                            "access_token": access_token,
                            "team_id": team_id,
                            "team_name": team_name,
                            "user_id": user_id,
                            "user_name": user_name,
                            "connected_at": datetime.utcnow().isoformat(),
                            "scope": token_response.get('scope', '')
                        }
                    },
                    "$unset": {
                        "slack_oauth_state": "",
                        "slack_oauth_callback": ""
                    }
                }
            )
            
            # Redirect to frontend settings page with success
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return HttpResponseRedirect(f'{frontend_url}/settings?tab=connections&slack_connected=true')
        else:
            return JsonResponse({'error': 'Failed to exchange code for token'}, status=500)
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def slack_disconnect(request):
    """Disconnect user's Slack account."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        # Remove Slack credentials from user document
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user_collection.update_one(
            {"username": user['username']},
            {
                "$unset": {
                    "slack_credentials": "",
                    "slack_oauth_state": "",
                    "slack_oauth_callback": ""
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Slack account disconnected successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# Slack API Proxy Endpoints

@csrf_exempt
@require_http_methods(["GET"])
def slack_list_channels(request):
    """List all Slack channels the user has access to."""
    try:
        print("[SLACK DEBUG] Starting slack_list_channels")
        user, error_response = get_user_from_token(request)
        if error_response:
            print(f"[SLACK DEBUG] Auth failed: {error_response}")
            return error_response
        
        print(f"[SLACK DEBUG] User authenticated: {user.get('username')}")
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            print("[SLACK DEBUG] No Slack credentials found")
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        print("[SLACK DEBUG] Slack credentials found, making API request")
        # Get both public and private channels
        channels = []
        
        # Public channels
        url = "https://slack.com/api/conversations.list?types=public_channel,private_channel"
        data, error = make_slack_api_request(url, slack_creds['access_token'])
        
        if error:
            print(f"[SLACK DEBUG] API request error: {error}")
            return JsonResponse({'error': error}, status=500)
        
        print(f"[SLACK DEBUG] API response ok: {data.get('ok')}")
        if data.get('ok'):
            channels = data.get('channels', [])
            
            # Format channels for frontend
            formatted_channels = [
                {
                    'id': ch.get('id'),
                    'name': ch.get('name'),
                    'is_member': ch.get('is_member', False),
                    'num_members': ch.get('num_members', 0),
                    'is_private': ch.get('is_private', False)
                }
                for ch in channels
            ]
            
            print(f"[SLACK DEBUG] Returning {len(formatted_channels)} channels")
            return JsonResponse({'channels': formatted_channels})
        else:
            print(f"[SLACK DEBUG] Slack API returned error: {data.get('error')}")
            return JsonResponse({'error': data.get('error', 'Failed to fetch channels')}, status=500)
    except Exception as e:
        import traceback
        error_msg = f'Exception: {str(e)}'
        traceback_str = traceback.format_exc()
        print(f"[SLACK DEBUG] Exception occurred: {error_msg}")
        print(f"[SLACK DEBUG] Traceback: {traceback_str}")
        return JsonResponse({'error': error_msg, 'traceback': traceback_str}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def slack_send_message(request):
    """Send a message to a Slack channel."""
    try:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        data = json.loads(request.body) if request.body else {}
        channel = data.get('channel')
        text = data.get('text')
        thread_ts = data.get('thread_ts')
        
        if not channel or not text:
            return JsonResponse({'error': 'Channel and text are required'}, status=400)
        
        # Resolve channel name to ID if needed
        channel_id, resolve_error = resolve_channel_id(channel, slack_creds['access_token'])
        if resolve_error:
            return JsonResponse({'error': resolve_error}, status=400)
        
        # Prepare message payload
        payload = {
            'channel': channel_id,
            'text': text
        }
        
        if thread_ts:
            payload['thread_ts'] = thread_ts
        
        url = "https://slack.com/api/chat.postMessage"
        result, error = make_slack_api_request(url, slack_creds['access_token'], method='POST', data=payload)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        if result.get('ok'):
            return JsonResponse(result)
        else:
            return JsonResponse({'error': result.get('error', 'Failed to send message')}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def slack_channel_history(request):
    """Get message history from a Slack channel."""
    try:
        print("[SLACK DEBUG] Starting slack_channel_history")
        user, error_response = get_user_from_token(request)
        if error_response:
            print(f"[SLACK DEBUG] Auth failed")
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            print("[SLACK DEBUG] No Slack credentials")
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        channel = request.GET.get('channel')
        limit = request.GET.get('limit', '20')
        oldest = request.GET.get('oldest')
        latest = request.GET.get('latest')
        
        print(f"[SLACK DEBUG] Channel param: {channel}")
        
        if not channel:
            return JsonResponse({'error': 'Channel parameter is required'}, status=400)
        
        # Resolve channel name to ID if needed
        channel_id, resolve_error = resolve_channel_id(channel, slack_creds['access_token'])
        if resolve_error:
            print(f"[SLACK DEBUG] Failed to resolve channel: {resolve_error}")
            return JsonResponse({'error': resolve_error}, status=400)
        
        print(f"[SLACK DEBUG] Resolved channel ID: {channel_id}")
        
        # Build URL with parameters
        url = f"https://slack.com/api/conversations.history?channel={channel_id}&limit={limit}"
        if oldest:
            url += f"&oldest={oldest}"
        if latest:
            url += f"&latest={latest}"
        
        print(f"[SLACK DEBUG] Making API request to: {url}")
        data, error = make_slack_api_request(url, slack_creds['access_token'])
        
        if error:
            print(f"[SLACK DEBUG] API request error: {error}")
            return JsonResponse({'error': error}, status=500)
        
        print(f"[SLACK DEBUG] API response ok: {data.get('ok')}, error: {data.get('error')}")
        if data.get('ok'):
            print(f"[SLACK DEBUG] Returning {len(data.get('messages', []))} messages")
            return JsonResponse({'messages': data.get('messages', [])})
        else:
            print(f"[SLACK DEBUG] Slack API error: {data.get('error')}")
            return JsonResponse({'error': data.get('error', 'Failed to fetch channel history')}, status=500)
    except Exception as e:
        import traceback
        error_msg = f'Exception: {str(e)}'
        traceback_str = traceback.format_exc()
        print(f"[SLACK DEBUG] Exception: {error_msg}")
        print(f"[SLACK DEBUG] Traceback: {traceback_str}")
        return JsonResponse({'error': error_msg, 'traceback': traceback_str}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def slack_thread_replies(request):
    """Get all replies in a specific Slack thread."""
    try:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        channel = request.GET.get('channel')
        thread_ts = request.GET.get('thread_ts')
        limit = request.GET.get('limit', '20')
        
        if not channel or not thread_ts:
            return JsonResponse({'error': 'Channel and thread_ts parameters are required'}, status=400)
        
        # Resolve channel name to ID if needed
        channel_id, resolve_error = resolve_channel_id(channel, slack_creds['access_token'])
        if resolve_error:
            return JsonResponse({'error': resolve_error}, status=400)
        
        url = f"https://slack.com/api/conversations.replies?channel={channel_id}&ts={thread_ts}&limit={limit}"
        data, error = make_slack_api_request(url, slack_creds['access_token'])
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        if data.get('ok'):
            return JsonResponse({'messages': data.get('messages', [])})
        else:
            return JsonResponse({'error': data.get('error', 'Failed to fetch thread replies')}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def slack_search_messages(request):
    """Search for messages across all Slack channels."""
    try:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        query = request.GET.get('query')
        count = request.GET.get('count', '20')
        sort = request.GET.get('sort', 'timestamp')
        
        if not query:
            return JsonResponse({'error': 'Query parameter is required'}, status=400)
        
        url = f"https://slack.com/api/search.messages?query={query}&count={count}&sort={sort}"
        data, error = make_slack_api_request(url, slack_creds['access_token'])
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        if data.get('ok'):
            messages_data = data.get('messages', {})
            return JsonResponse({
                'messages': messages_data.get('matches', []),
                'total': messages_data.get('total', 0)
            })
        else:
            return JsonResponse({'error': data.get('error', 'Failed to search messages')}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def slack_user_info(request):
    """Get information about a Slack user by their user ID."""
    try:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        user_id = request.GET.get('user_id')
        
        if not user_id:
            return JsonResponse({'error': 'user_id parameter is required'}, status=400)
        
        url = f"https://slack.com/api/users.info?user={user_id}"
        data, error = make_slack_api_request(url, slack_creds['access_token'])
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        if data.get('ok'):
            return JsonResponse({'user': data.get('user', {})})
        else:
            return JsonResponse({'error': data.get('error', 'Failed to fetch user info')}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def slack_set_channel_topic(request):
    """Set or update the topic for a Slack channel."""
    try:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        data = json.loads(request.body) if request.body else {}
        channel = data.get('channel')
        topic = data.get('topic')
        
        if not channel or topic is None:
            return JsonResponse({'error': 'Channel and topic are required'}, status=400)
        
        # Resolve channel name to ID if needed
        channel_id, resolve_error = resolve_channel_id(channel, slack_creds['access_token'])
        if resolve_error:
            return JsonResponse({'error': resolve_error}, status=400)
        
        payload = {
            'channel': channel_id,
            'topic': topic
        }
        
        url = "https://slack.com/api/conversations.setTopic"
        result, error = make_slack_api_request(url, slack_creds['access_token'], method='POST', data=payload)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        if result.get('ok'):
            return JsonResponse(result)
        else:
            return JsonResponse({'error': result.get('error', 'Failed to set channel topic')}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def slack_add_reaction(request):
    """Add an emoji reaction to a Slack message."""
    try:
        user, error_response = get_user_from_token(request)
        if error_response:
            return error_response
        
        slack_creds = get_slack_credentials(user)
        if not slack_creds:
            return JsonResponse({'error': 'Slack not connected'}, status=400)
        
        data = json.loads(request.body) if request.body else {}
        channel = data.get('channel')
        timestamp = data.get('timestamp')
        name = data.get('name')
        
        if not channel or not timestamp or not name:
            return JsonResponse({'error': 'Channel, timestamp, and name are required'}, status=400)
        
        # Resolve channel name to ID if needed
        channel_id, resolve_error = resolve_channel_id(channel, slack_creds['access_token'])
        if resolve_error:
            return JsonResponse({'error': resolve_error}, status=400)
        
        payload = {
            'channel': channel_id,
            'timestamp': timestamp,
            'name': name
        }
        
        url = "https://slack.com/api/reactions.add"
        result, error = make_slack_api_request(url, slack_creds['access_token'], method='POST', data=payload)
        
        if error:
            return JsonResponse({'error': error}, status=500)
        
        if result.get('ok'):
            return JsonResponse(result)
        else:
            return JsonResponse({'error': result.get('error', 'Failed to add reaction')}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': f'Exception: {str(e)}'}, status=500)

