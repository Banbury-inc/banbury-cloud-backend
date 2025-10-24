"""
GitHub OAuth Integration Views

This module provides endpoints for GitHub OAuth authentication and API proxy functionality.
Users can connect their GitHub accounts and perform various GitHub operations through these endpoints.
"""

import json
import os
import requests
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
from rest_framework_simplejwt.tokens import AccessToken


def get_mongo_client():
    """Get MongoDB client instance."""
    mongo_uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    return MongoClient(mongo_uri)


def get_user_from_token(request):
    """Extract and validate user from JWT token."""
    auth_header = request.headers.get('Authorization')
    if not auth_header or ' ' not in auth_header:
        return None, JsonResponse({'error': 'Authentication required'}, status=401)
    
    auth_type, token = auth_header.split(' ', 1)
    if auth_type.lower() != 'bearer':
        return None, JsonResponse({'error': 'Invalid authentication type'}, status=401)
    
    try:
        validated = AccessToken(token)
        username = validated.payload.get('username')
        if not username:
            return None, JsonResponse({'error': 'Invalid token'}, status=401)
        
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user = user_collection.find_one({"username": username})
        
        if not user:
            return None, JsonResponse({'error': 'User not found'}, status=404)
        
        return user, None
    except Exception as e:
        return None, JsonResponse({'error': f'Token validation failed: {str(e)}'}, status=401)


def get_github_credentials(user):
    """Extract GitHub credentials from user document."""
    github_creds = user.get('github_credentials', {})
    access_token = github_creds.get('access_token')
    return access_token


@csrf_exempt
@require_http_methods(["GET"])
def github_connection_status(request):
    """Check if user has connected their GitHub account."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    
    if access_token:
        # Verify token is still valid by getting user info
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            response = requests.get('https://api.github.com/user', headers=headers, timeout=10)
            
            if response.status_code == 200:
                user_data = response.json()
                return JsonResponse({
                    'connected': True,
                    'username': user_data.get('login'),
                    'name': user_data.get('name'),
                    'avatar_url': user_data.get('avatar_url')
                })
            else:
                # Token is invalid or expired
                return JsonResponse({
                    'connected': False
                })
        except Exception as e:
            return JsonResponse({
                'connected': False,
                'error': f'Error verifying connection: {str(e)}'
            })
    else:
        return JsonResponse({
            'connected': False
        })


@csrf_exempt
@require_http_methods(["POST"])
def github_initiate_oauth(request):
    """Initiate GitHub OAuth flow for user connection."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        # Parse request body
        data = json.loads(request.body) if request.body else {}
        callback_url = data.get('callback_url')
        
        if not callback_url:
            return JsonResponse({'error': 'Callback URL is required'}, status=400)

        # Get GitHub OAuth credentials from environment
        github_client_id = os.environ.get('GH_CLIENT_ID')
        github_client_secret = os.environ.get('GH_CLIENT_SECRET')
        
        if not github_client_id or not github_client_secret:
            return JsonResponse({'error': 'GitHub credentials not configured'}, status=500)

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
                    "github_oauth_state": state,
                    "github_oauth_callback": callback_url
                }
            }
        )
        
        # Required GitHub OAuth scopes
        scopes = [
            'repo',  # Full control of private repositories
            'read:org',  # Read org and team membership
            'user:email',  # Access user email addresses
            'gist',  # Create gists
            'notifications',  # Access notifications
        ]
        
        # Generate authorization URL
        auth_url = (
            f"https://github.com/login/oauth/authorize?"
            f"client_id={github_client_id}"
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
def github_oauth_callback(request):
    """Handle GitHub OAuth callback and complete the connection."""
    try:
        # Get OAuth parameters
        code = request.GET.get('code')
        state = request.GET.get('state')
        error = request.GET.get('error')
        
        if error:
            return JsonResponse({'error': f'OAuth error: {error}'}, status=400)
        
        if not code or not state:
            return JsonResponse({'error': 'Missing OAuth parameters'}, status=400)

        # Get GitHub OAuth credentials from environment
        github_client_id = os.environ.get('GH_CLIENT_ID')
        github_client_secret = os.environ.get('GH_CLIENT_SECRET')
        
        if not github_client_id or not github_client_secret:
            return JsonResponse({'error': 'GitHub credentials not configured'}, status=500)

        # Find user by OAuth state
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        user = user_collection.find_one({"github_oauth_state": state})
        if not user:
            return JsonResponse({'error': 'Invalid OAuth state'}, status=400)
        
        username = user.get('username')
        callback_url = user.get('github_oauth_callback')
        
        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            'client_id': github_client_id,
            'client_secret': github_client_secret,
            'code': code,
            'redirect_uri': callback_url,
            'state': state
        }
        
        headers = {
            'Accept': 'application/json'
        }
        
        response = requests.post(token_url, data=token_data, headers=headers, timeout=30)
        
        if response.status_code == 200:
            token_response = response.json()
            access_token = token_response.get('access_token')
            
            if not access_token:
                error_description = token_response.get('error_description', 'Unknown error')
                return JsonResponse({'error': f'Failed to get access token: {error_description}'}, status=400)
            
            # Get user info from GitHub
            user_headers = {
                'Authorization': f'Bearer {access_token}',
                'Accept': 'application/vnd.github.v3+json'
            }
            user_response = requests.get('https://api.github.com/user', headers=user_headers, timeout=10)
            
            if user_response.status_code != 200:
                return JsonResponse({'error': 'Failed to get user info from GitHub'}, status=400)
            
            github_user = user_response.json()
            
            # Store credentials in user document
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "github_credentials": {
                            "access_token": access_token,
                            "username": github_user.get('login'),
                            "name": github_user.get('name'),
                            "avatar_url": github_user.get('avatar_url'),
                            "connected_at": token_response.get('created_at')
                        }
                    },
                    "$unset": {
                        "github_oauth_state": "",
                        "github_oauth_callback": ""
                    }
                }
            )
            
            # Redirect to frontend success page
            frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
            return HttpResponse(f'''
                <html>
                <head>
                    <title>GitHub Connected</title>
                    <script>
                        window.opener.postMessage({{ type: 'github_auth_success' }}, '{frontend_url}');
                        window.close();
                    </script>
                </head>
                <body>
                    <h1>GitHub account connected successfully!</h1>
                    <p>This window will close automatically...</p>
                    <script>
                        setTimeout(function() {{
                            window.close();
                        }}, 2000);
                    </script>
                </body>
                </html>
            ''')
        else:
            return JsonResponse({'error': 'Failed to exchange code for token'}, status=400)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def github_disconnect(request):
    """Disconnect user's GitHub account."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        
        # Remove GitHub credentials from user document
        user_collection.update_one(
            {"username": user['username']},
            {
                "$unset": {
                    "github_credentials": "",
                    "github_oauth_state": "",
                    "github_oauth_callback": ""
                }
            }
        )
        
        return JsonResponse({
            'success': True,
            'message': 'GitHub account disconnected successfully'
        })
        
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


# GitHub API proxy endpoints

@csrf_exempt
@require_http_methods(["GET"])
def github_list_repos(request):
    """List user's GitHub repositories."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        visibility = request.GET.get('visibility', 'all')  # all, public, private
        sort = request.GET.get('sort', 'updated')  # created, updated, pushed, full_name
        per_page = min(int(request.GET.get('per_page', 30)), 100)
        page = int(request.GET.get('page', 1))
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        params = {
            'visibility': visibility,
            'sort': sort,
            'per_page': per_page,
            'page': page
        }
        
        response = requests.get(
            'https://api.github.com/user/repos',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'repositories': response.json()
            })
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def github_get_repo(request, owner, repo):
    """Get details about a specific repository."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def github_create_issue(request):
    """Create an issue in a repository."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        data = json.loads(request.body) if request.body else {}
        owner = data.get('owner')
        repo = data.get('repo')
        title = data.get('title')
        body = data.get('body', '')
        labels = data.get('labels', [])
        assignees = data.get('assignees', [])
        
        if not owner or not repo or not title:
            return JsonResponse({'error': 'owner, repo, and title are required'}, status=400)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        issue_data = {
            'title': title,
            'body': body,
            'labels': labels,
            'assignees': assignees
        }
        
        response = requests.post(
            f'https://api.github.com/repos/{owner}/{repo}/issues',
            headers=headers,
            json=issue_data,
            timeout=30
        )
        
        if response.status_code == 201:
            return JsonResponse(response.json())
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def github_list_issues(request, owner, repo):
    """List issues for a repository."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        state = request.GET.get('state', 'open')  # open, closed, all
        per_page = min(int(request.GET.get('per_page', 30)), 100)
        page = int(request.GET.get('page', 1))
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        params = {
            'state': state,
            'per_page': per_page,
            'page': page
        }
        
        response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/issues',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'issues': response.json()
            })
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def github_list_pull_requests(request, owner, repo):
    """List pull requests for a repository."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        state = request.GET.get('state', 'open')  # open, closed, all
        per_page = min(int(request.GET.get('per_page', 30)), 100)
        page = int(request.GET.get('page', 1))
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        params = {
            'state': state,
            'per_page': per_page,
            'page': page
        }
        
        response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/pulls',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return JsonResponse({
                'pull_requests': response.json()
            })
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def github_get_file_contents(request, owner, repo):
    """Get contents of a file from a repository."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        path = request.GET.get('path')
        ref = request.GET.get('ref', 'main')  # branch, tag, or commit SHA
        
        if not path:
            return JsonResponse({'error': 'path parameter is required'}, status=400)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        params = {
            'ref': ref
        }
        
        response = requests.get(
            f'https://api.github.com/repos/{owner}/{repo}/contents/{path}',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def github_search_code(request):
    """Search code across GitHub repositories."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response
    
    access_token = get_github_credentials(user)
    if not access_token:
        return JsonResponse({'error': 'GitHub not connected'}, status=400)
    
    try:
        query = request.GET.get('q')
        per_page = min(int(request.GET.get('per_page', 30)), 100)
        page = int(request.GET.get('page', 1))
        
        if not query:
            return JsonResponse({'error': 'q (query) parameter is required'}, status=400)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        params = {
            'q': query,
            'per_page': per_page,
            'page': page
        }
        
        response = requests.get(
            'https://api.github.com/search/code',
            headers=headers,
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            return JsonResponse(response.json())
        else:
            return JsonResponse({
                'error': f'GitHub API error: {response.status_code}',
                'details': response.text
            }, status=response.status_code)
            
    except Exception as e:
        return JsonResponse({'error': f'Error: {str(e)}'}, status=500)

