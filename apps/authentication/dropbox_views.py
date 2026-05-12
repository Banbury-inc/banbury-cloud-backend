"""
Dropbox integration views for Banbury backend.
Handles OAuth flow and API proxy endpoints for Dropbox file operations.
"""
import json
import os
import urllib.parse
import uuid
from datetime import datetime, timedelta

import requests
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
from rest_framework_simplejwt.tokens import AccessToken


DROPBOX_API_URL = "https://api.dropboxapi.com/2"
DROPBOX_CONTENT_URL = "https://content.dropboxapi.com/2"
DROPBOX_OAUTH_AUTHORIZE_URL = "https://www.dropbox.com/oauth2/authorize"
DROPBOX_OAUTH_TOKEN_URL = "https://api.dropboxapi.com/oauth2/token"
DROPBOX_SCOPES = [
    "account_info.read",
    "files.metadata.read",
    "files.content.read",
    "files.content.write",
    "sharing.write",
]


def get_mongo_client():
    """Get MongoDB client connection."""
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    return MongoClient(uri)


def get_user_from_token(request):
    """Extract and validate user from JWT token."""
    auth_header = request.headers.get("Authorization")
    if not auth_header or " " not in auth_header:
        return None, JsonResponse({"message": "Authentication required"}, status=401)

    auth_type, token = auth_header.split(" ", 1)
    if auth_type.lower() != "bearer":
        return None, JsonResponse({"message": "Invalid authentication type"}, status=401)

    try:
        validated = AccessToken(token)
        username = validated.payload.get("username")

        if not username:
            return None, JsonResponse({"message": "Invalid token"}, status=401)

        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user = user_collection.find_one({"username": username})

        if not user:
            return None, JsonResponse({"message": "User not found"}, status=404)

        return user, None

    except Exception as e:
        return None, JsonResponse({"message": str(e)}, status=401)


def get_dropbox_credentials(user):
    """Get Dropbox credentials from user document."""
    dropbox_creds = user.get("dropbox_credentials", {})
    if not dropbox_creds.get("access_token"):
        return None
    return dropbox_creds


def _get_dropbox_app_credentials():
    app_key = os.environ.get("DROPBOX_APP_KEY") or os.environ.get("DROPBOX_CLIENT_ID")
    app_secret = os.environ.get("DROPBOX_APP_SECRET") or os.environ.get("DROPBOX_CLIENT_SECRET")
    return app_key, app_secret


def _refresh_dropbox_access_token_if_needed(dropbox_credentials, user_doc):
    """
    Ensure we have a valid access token; refresh using refresh_token when required.
    Returns (access_token, error_message).
    """
    if not dropbox_credentials:
        return None, "No Dropbox credentials found"

    access_token = dropbox_credentials.get("access_token")
    refresh_token = dropbox_credentials.get("refresh_token")
    expires_at = dropbox_credentials.get("expires_at")

    if not access_token:
        return None, "No access token found"

    needs_refresh = False
    if expires_at:
        try:
            expiry_time = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
            if datetime.now(expiry_time.tzinfo) >= expiry_time - timedelta(minutes=5):
                needs_refresh = True
        except (ValueError, TypeError):
            pass

    if not needs_refresh:
        return access_token, None

    if not refresh_token:
        return None, "Token expired and no refresh token available"

    app_key, app_secret = _get_dropbox_app_credentials()
    if not app_key or not app_secret:
        return access_token, None

    try:
        response = requests.post(
            DROPBOX_OAUTH_TOKEN_URL,
            data={
                "client_id": app_key,
                "client_secret": app_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=30,
        )

        if response.status_code != 200:
            return access_token, None

        token_response = response.json()
        new_access_token = token_response.get("access_token")
        expires_in = token_response.get("expires_in", 14400)
        new_expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"

        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user_collection.update_one(
            {"_id": user_doc.get("_id")},
            {
                "$set": {
                    "dropbox_credentials.access_token": new_access_token,
                    "dropbox_credentials.expires_at": new_expires_at,
                }
            },
        )

        return new_access_token, None

    except Exception as e:
        print(f"Error refreshing Dropbox token: {e}")
        return access_token, None


def make_dropbox_api_request(endpoint, access_token, data=None):
    """Make a request to Dropbox API JSON endpoints."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            f"{DROPBOX_API_URL}{endpoint}",
            headers=headers,
            json=data or {},
            timeout=60,
        )

        if response.status_code in [200, 201, 202, 204]:
            if response.content:
                return response.json(), None
            return {}, None

        error_data = response.json() if response.content else {}
        error_summary = error_data.get("error_summary") or error_data.get("error", {}).get(".tag")
        return None, error_summary or f"HTTP {response.status_code}"

    except Exception as e:
        return None, str(e)


def _get_authenticated_dropbox(request):
    user, error_response = get_user_from_token(request)
    if error_response:
        return None, None, error_response

    dropbox_creds = get_dropbox_credentials(user)
    if not dropbox_creds:
        return None, None, JsonResponse({"error": "Dropbox not connected"}, status=400)

    access_token, error = _refresh_dropbox_access_token_if_needed(dropbox_creds, user)
    if error or not access_token:
        return None, None, JsonResponse({"error": error or "Failed to get access token"}, status=400)

    return user, access_token, None


def _get_dropbox_path(request, default=""):
    path = request.GET.get("path", default)
    if path in ["/", "root"]:
        return ""
    return path


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_connection_status(request):
    """Get the current Dropbox connection status for the authenticated user."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    dropbox_creds = get_dropbox_credentials(user)
    if not dropbox_creds:
        return JsonResponse({"connected": False})

    access_token, _ = _refresh_dropbox_access_token_if_needed(dropbox_creds, user)
    if not access_token:
        return JsonResponse({"connected": False})

    data, error = make_dropbox_api_request("/users/get_current_account", access_token)
    if error or not data:
        return JsonResponse({"connected": False})

    return JsonResponse({
        "connected": True,
        "accountEmail": data.get("email"),
        "accountName": data.get("name", {}).get("display_name"),
    })


@csrf_exempt
@require_http_methods(["POST"])
def dropbox_initiate_oauth(request):
    """Initiate Dropbox OAuth flow for user connection."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    try:
        data = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    callback_url = data.get("callback_url")
    if not callback_url:
        return JsonResponse({"error": "Callback URL is required"}, status=400)

    app_key, app_secret = _get_dropbox_app_credentials()
    if not app_key or not app_secret:
        return JsonResponse({"error": "Dropbox credentials not configured"}, status=500)

    state = str(uuid.uuid4())

    client = get_mongo_client()
    db = client["NeuraNet"]
    user_collection = db["users"]
    user_collection.update_one(
        {"username": user["username"]},
        {
            "$set": {
                "dropbox_oauth_state": state,
                "dropbox_oauth_callback": callback_url,
            }
        },
    )

    params = {
        "client_id": app_key,
        "response_type": "code",
        "redirect_uri": callback_url,
        "state": state,
        "token_access_type": "offline",
        "scope": " ".join(DROPBOX_SCOPES),
    }

    auth_url = f"{DROPBOX_OAUTH_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"
    return JsonResponse({"auth_url": auth_url})


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_oauth_callback(request):
    """Handle Dropbox OAuth callback and complete the connection."""
    try:
        code = request.GET.get("code")
        state = request.GET.get("state")
        error = request.GET.get("error")
        error_description = request.GET.get("error_description")

        if error:
            return JsonResponse({"error": f"OAuth error: {error} - {error_description}"}, status=400)

        if not code or not state:
            return JsonResponse({"error": "Missing OAuth parameters"}, status=400)

        app_key, app_secret = _get_dropbox_app_credentials()
        if not app_key or not app_secret:
            return JsonResponse({"error": "Dropbox credentials not configured"}, status=500)

        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]

        user = user_collection.find_one({"dropbox_oauth_state": state})
        if not user:
            return JsonResponse({"error": "Invalid OAuth state"}, status=400)

        username = user.get("username")
        callback_url = user.get("dropbox_oauth_callback")

        response = requests.post(
            DROPBOX_OAUTH_TOKEN_URL,
            data={
                "client_id": app_key,
                "client_secret": app_secret,
                "code": code,
                "redirect_uri": callback_url,
                "grant_type": "authorization_code",
            },
            timeout=30,
        )

        if response.status_code != 200:
            error_data = response.json() if response.content else {}
            return JsonResponse({
                "error": error_data.get("error_description", "Failed to exchange code for token")
            }, status=500)

        token_response = response.json()
        access_token = token_response.get("access_token")
        refresh_token = token_response.get("refresh_token")
        expires_in = token_response.get("expires_in", 14400)
        scope = token_response.get("scope", "")

        if not access_token:
            return JsonResponse({"error": "Failed to get access token"}, status=400)

        account_info, _ = make_dropbox_api_request("/users/get_current_account", access_token)
        expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + "Z"

        user_collection.update_one(
            {"username": username},
            {
                "$set": {
                    "dropbox_credentials": {
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "expires_at": expires_at,
                        "scope": scope,
                        "account_id": account_info.get("account_id") if account_info else None,
                        "account_email": account_info.get("email") if account_info else None,
                        "account_name": account_info.get("name", {}).get("display_name") if account_info else None,
                        "connected_at": datetime.utcnow().isoformat(),
                    }
                },
                "$unset": {
                    "dropbox_oauth_state": "",
                    "dropbox_oauth_callback": "",
                },
            },
        )

        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
        return HttpResponseRedirect(f"{frontend_url}/workspaces?openSettings=true&settingsTab=connections&dropbox_connected=true")

    except Exception as e:
        return JsonResponse({"error": f"Error: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def dropbox_disconnect(request):
    """Disconnect user's Dropbox account."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user_collection.update_one(
            {"username": user["username"]},
            {
                "$unset": {
                    "dropbox_credentials": "",
                    "dropbox_oauth_state": "",
                    "dropbox_oauth_callback": "",
                    "dropbox_deleted_items": "",
                }
            },
        )

        return JsonResponse({
            "success": True,
            "message": "Dropbox account disconnected successfully",
        })

    except Exception as e:
        return JsonResponse({"error": f"Error: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_list_folder(request):
    """List files and folders in a Dropbox folder."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    cursor = request.GET.get("cursor")
    limit = int(request.GET.get("limit", "100"))

    if cursor:
        data, error = make_dropbox_api_request("/files/list_folder/continue", access_token, {"cursor": cursor})
    else:
        data, error = make_dropbox_api_request(
            "/files/list_folder",
            access_token,
            {
                "path": _get_dropbox_path(request),
                "limit": limit,
                "include_deleted": False,
            },
        )

    if error:
        return JsonResponse({"error": error}, status=500)

    return JsonResponse({
        "items": data.get("entries", []),
        "cursor": data.get("cursor"),
        "hasMore": data.get("has_more", False),
    })


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_search_files(request):
    """Search for files and folders in Dropbox."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    query = request.GET.get("q")
    if not query:
        return JsonResponse({"error": "Search query (q) is required"}, status=400)

    data, error = make_dropbox_api_request(
        "/files/search_v2",
        access_token,
        {
            "query": query,
            "options": {
                "path": _get_dropbox_path(request),
                "max_results": int(request.GET.get("limit", "50")),
                "file_status": "active",
            },
        },
    )

    if error:
        return JsonResponse({"error": error}, status=500)

    return JsonResponse({"items": data.get("matches", [])})


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_get_metadata(request):
    """Get metadata for a Dropbox file or folder."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    path = _get_dropbox_path(request, None)
    if not path:
        return JsonResponse({"error": "path is required"}, status=400)

    data, error = make_dropbox_api_request(
        "/files/get_metadata",
        access_token,
        {
            "path": path,
            "include_media_info": True,
        },
    )

    if error:
        return JsonResponse({"error": error}, status=500)

    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_download_file(request):
    """Download a file from Dropbox."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    path = _get_dropbox_path(request, None)
    if not path:
        return JsonResponse({"error": "path is required"}, status=400)

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Dropbox-API-Arg": json.dumps({"path": path}),
    }

    try:
        response = requests.post(
            f"{DROPBOX_CONTENT_URL}/files/download",
            headers=headers,
            timeout=120,
        )

        if response.status_code != 200:
            return JsonResponse({"error": f"Failed to download file: HTTP {response.status_code}"}, status=response.status_code)

        metadata = json.loads(response.headers.get("Dropbox-API-Result", "{}"))
        file_name = metadata.get("name", "download")
        content_type = response.headers.get("Content-Type", "application/octet-stream")
        download_response = HttpResponse(response.content, content_type=content_type)
        download_response["Content-Disposition"] = f'attachment; filename="{file_name}"'
        return download_response

    except Exception as e:
        return JsonResponse({"error": f"Download failed: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def dropbox_upload_file(request):
    """Upload a file to Dropbox."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    uploaded_file = request.FILES.get("file")
    if not uploaded_file:
        return JsonResponse({"error": "No file provided"}, status=400)

    parent_path = request.POST.get("parent_path", "")
    if parent_path == "/":
        parent_path = ""

    file_name = uploaded_file.name
    dropbox_path = f"{parent_path.rstrip('/')}/{file_name}" if parent_path else f"/{file_name}"
    content = uploaded_file.read()

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/octet-stream",
        "Dropbox-API-Arg": json.dumps({
            "path": dropbox_path,
            "mode": "add",
            "autorename": True,
            "mute": False,
        }),
    }

    try:
        response = requests.post(
            f"{DROPBOX_CONTENT_URL}/files/upload",
            headers=headers,
            data=content,
            timeout=120,
        )

        if response.status_code != 200:
            return JsonResponse({"error": response.text or f"HTTP {response.status_code}"}, status=500)

        return JsonResponse(response.json())

    except Exception as e:
        return JsonResponse({"error": f"Upload failed: {str(e)}"}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def dropbox_create_folder(request):
    """Create a Dropbox folder."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    path = payload.get("path")
    if not path:
        return JsonResponse({"error": "path is required"}, status=400)

    data, error = make_dropbox_api_request(
        "/files/create_folder_v2",
        access_token,
        {
            "path": path,
            "autorename": True,
        },
    )

    if error:
        return JsonResponse({"error": error}, status=500)

    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def dropbox_delete_item(request):
    """Delete a Dropbox file or folder."""
    user, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    try:
        payload = json.loads(request.body or "{}") if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    path = payload.get("path") or _get_dropbox_path(request, None)
    if not path:
        return JsonResponse({"error": "path is required"}, status=400)

    data, error = make_dropbox_api_request("/files/delete_v2", access_token, {"path": path})
    if error:
        return JsonResponse({"error": error}, status=500)

    try:
        client = get_mongo_client()
        db = client["NeuraNet"]
        user_collection = db["users"]
        user_collection.update_one(
            {"username": user["username"]},
            {
                "$push": {
                    "dropbox_deleted_items": {
                        "path": path,
                        "deleted_at": datetime.utcnow().isoformat(),
                    }
                }
            },
        )
    except Exception:
        pass

    return JsonResponse({"success": True, "metadata": data.get("metadata")})


@csrf_exempt
@require_http_methods(["PATCH", "POST"])
def dropbox_move_item(request):
    """Move or rename a Dropbox file or folder."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    from_path = payload.get("from_path")
    to_path = payload.get("to_path")

    if not from_path or not to_path:
        return JsonResponse({"error": "from_path and to_path are required"}, status=400)

    data, error = make_dropbox_api_request(
        "/files/move_v2",
        access_token,
        {
            "from_path": from_path,
            "to_path": to_path,
            "autorename": True,
        },
    )

    if error:
        return JsonResponse({"error": error}, status=500)

    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["POST"])
def dropbox_create_share_link(request):
    """Create or return an existing Dropbox shared link for a file or folder."""
    _, access_token, error_response = _get_authenticated_dropbox(request)
    if error_response:
        return error_response

    try:
        payload = json.loads(request.body or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    path = payload.get("path")
    if not path:
        return JsonResponse({"error": "path is required"}, status=400)

    data, error = make_dropbox_api_request(
        "/sharing/create_shared_link_with_settings",
        access_token,
        {"path": path},
    )

    if error and "shared_link_already_exists" in error:
        data, error = make_dropbox_api_request(
            "/sharing/list_shared_links",
            access_token,
            {
                "path": path,
                "direct_only": True,
            },
        )
        links = data.get("links", []) if data else []
        if links:
            return JsonResponse(links[0])

    if error:
        return JsonResponse({"error": error}, status=500)

    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["GET"])
def dropbox_trash_list(request):
    """List recently deleted Dropbox items tracked by Banbury."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    deleted_items = sorted(
        user.get("dropbox_deleted_items", []),
        key=lambda item: item.get("deleted_at", ""),
        reverse=True,
    )

    return JsonResponse({
        "items": deleted_items[:50],
        "note": "Dropbox restore/recycle bin operations should be completed in Dropbox.",
    })
