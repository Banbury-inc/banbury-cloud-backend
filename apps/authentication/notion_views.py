"""
Notion integration views for Banbury backend.
Handles OAuth flow and API proxy endpoints for connected Notion workspaces.
"""
import base64
import json
import os
import urllib.parse
import uuid
from datetime import datetime

import requests
from django.http import HttpResponseRedirect, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from pymongo import MongoClient
from rest_framework_simplejwt.tokens import AccessToken


NOTION_API_BASE_URL = "https://api.notion.com/v1"
NOTION_API_VERSION = os.environ.get("NOTION_API_VERSION", "2022-06-28")
NOTION_MEETING_SUMMARY_DATABASE_ID = os.environ.get(
    "NOTION_MEETING_SUMMARY_DATABASE_ID",
    "35f1d300a72480908ab7de360cf72bc4",
)


def get_mongo_client():
    """Get MongoDB client connection."""
    uri = os.environ.get(
        "MONGO_URI",
        "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
    )
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


def get_notion_credentials(user):
    """Get Notion credentials from user document."""
    notion_creds = user.get("notion_credentials", {})
    if not notion_creds.get("access_token"):
        return None
    return notion_creds


def make_notion_api_request(endpoint, access_token, method="GET", data=None, params=None):
    """Make a request to Notion API."""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }
    url = f"{NOTION_API_BASE_URL}{endpoint}"

    try:
        if method == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=60)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data or {}, timeout=60)
        else:
            return None, "Invalid HTTP method", 400

        if response.status_code in [200, 201, 202, 204]:
            if response.content:
                return response.json(), None, response.status_code
            return {}, None, response.status_code

        error_data = response.json() if response.content else {}
        error_message = error_data.get("message") or error_data.get("error") or f"HTTP {response.status_code}"
        return None, error_message, response.status_code

    except Exception as e:
        return None, str(e), 500


def get_authenticated_notion_credentials(request):
    """Authenticate request and return connected Notion credentials."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return None, None, error_response

    notion_creds = get_notion_credentials(user)
    if not notion_creds:
        return user, None, JsonResponse({"error": "Notion not connected"}, status=400)

    return user, notion_creds, None


def parse_json_body(request):
    """Parse a JSON request body."""
    if not request.body:
        return {}

    try:
        return json.loads(request.body)
    except json.JSONDecodeError:
        return None


def get_notion_env_value(*names):
    """Return the first configured Notion environment variable from the provided names."""
    for name in names:
        value = os.environ.get(name)
        if value:
            return value
    return None


def get_bounded_int(value, default, maximum):
    """Parse an integer query/body value and clamp it to a maximum."""
    try:
        return min(int(value), maximum)
    except (TypeError, ValueError):
        return default


def get_required_string(body, field_name):
    """Read a required string field from a parsed JSON body."""
    value = body.get(field_name)
    if not isinstance(value, str) or not value.strip():
        return None
    return value.strip()


def build_summary_database_properties(name, summary, sentiment, timestamp):
    """Build Notion database properties for the meeting summary row."""
    return {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": name,
                    },
                }
            ],
        },
        "Summary": {
            "rich_text": [
                {
                    "text": {
                        "content": summary,
                    },
                }
            ],
        },
        "Sentiment": {
            "select": {
                "name": sentiment,
            },
        },
        "Timestamp": {
            "date": {
                "start": timestamp,
            },
        },
    }


@csrf_exempt
@require_http_methods(["GET"])
def notion_connection_status(request):
    """Get the current Notion connection status for the authenticated user."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    notion_creds = get_notion_credentials(user)
    if not notion_creds:
        return JsonResponse({"connected": False})

    return JsonResponse({
        "connected": True,
        "workspace": notion_creds.get("workspace", {}),
        "botId": notion_creds.get("bot_id"),
        "connectedAt": notion_creds.get("connected_at"),
    })


@csrf_exempt
@require_http_methods(["POST"])
def notion_initiate_oauth(request):
    """Initiate Notion OAuth flow for user connection."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    data = parse_json_body(request)
    if data is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    callback_url = data.get("callback_url")
    if not callback_url:
        return JsonResponse({"error": "Callback URL is required"}, status=400)

    notion_client_id = get_notion_env_value("NOTION_CLIENT_ID")
    notion_client_secret = get_notion_env_value("NOTION_CLIENT_SECRET")
    if not notion_client_id or not notion_client_secret:
        return JsonResponse({"error": "Notion credentials not configured"}, status=500)

    state = str(uuid.uuid4())

    client = get_mongo_client()
    db = client["NeuraNet"]
    user_collection = db["users"]
    user_collection.update_one(
        {"username": user["username"]},
        {
            "$set": {
                "notion_oauth_state": state,
                "notion_oauth_callback": callback_url,
            }
        },
    )

    params = {
        "client_id": notion_client_id,
        "response_type": "code",
        "owner": "user",
        "redirect_uri": callback_url,
        "state": state,
    }
    auth_url = f"https://api.notion.com/v1/oauth/authorize?{urllib.parse.urlencode(params)}"

    return JsonResponse({"auth_url": auth_url})


@csrf_exempt
@require_http_methods(["GET"])
def notion_oauth_callback(request):
    """Handle Notion OAuth callback and complete the connection."""
    code = request.GET.get("code")
    state = request.GET.get("state")
    error = request.GET.get("error")

    if error:
        return JsonResponse({"error": f"OAuth error: {error}"}, status=400)

    if not code or not state:
        return JsonResponse({"error": "Missing OAuth parameters"}, status=400)

    notion_client_id = get_notion_env_value("NOTION_CLIENT_ID")
    notion_client_secret = get_notion_env_value("NOTION_CLIENT_SECRET")
    if not notion_client_id or not notion_client_secret:
        return JsonResponse({"error": "Notion credentials not configured"}, status=500)

    client = get_mongo_client()
    db = client["NeuraNet"]
    user_collection = db["users"]

    user = user_collection.find_one({"notion_oauth_state": state})
    if not user:
        return JsonResponse({"error": "Invalid OAuth state"}, status=400)

    callback_url = user.get("notion_oauth_callback")
    token_url = "https://api.notion.com/v1/oauth/token"
    token_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": callback_url,
    }
    auth_value = f"{notion_client_id}:{notion_client_secret}".encode("utf-8")
    encoded_auth_value = base64.b64encode(auth_value).decode("utf-8")
    headers = {
        "Authorization": f"Basic {encoded_auth_value}",
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Notion-Version": NOTION_API_VERSION,
    }

    response = requests.post(token_url, headers=headers, json=token_data, timeout=30)
    if response.status_code != 200:
        error_data = response.json() if response.content else {}
        error_message = error_data.get("message", "Failed to exchange code for token")
        return JsonResponse({"error": error_message}, status=500)

    token_response = response.json()
    access_token = token_response.get("access_token")
    if not access_token:
        return JsonResponse({"error": "Failed to get access token"}, status=400)

    workspace = {
        "id": token_response.get("workspace_id"),
        "name": token_response.get("workspace_name"),
        "icon": token_response.get("workspace_icon"),
    }
    notion_credentials = {
        "access_token": access_token,
        "bot_id": token_response.get("bot_id"),
        "duplicated_template_id": token_response.get("duplicated_template_id"),
        "owner": token_response.get("owner"),
        "workspace": workspace,
        "connected_at": datetime.utcnow().isoformat(),
    }

    user_collection.update_one(
        {"username": user.get("username")},
        {
            "$set": {"notion_credentials": notion_credentials},
            "$unset": {
                "notion_oauth_state": "",
                "notion_oauth_callback": "",
            },
        },
    )

    frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
    return HttpResponseRedirect(f"{frontend_url}/workspaces?openSettings=true&settingsTab=connections&notion_connected=true")


@csrf_exempt
@require_http_methods(["POST"])
def notion_disconnect(request):
    """Disconnect user's Notion workspace."""
    user, error_response = get_user_from_token(request)
    if error_response:
        return error_response

    client = get_mongo_client()
    db = client["NeuraNet"]
    user_collection = db["users"]
    user_collection.update_one(
        {"username": user["username"]},
        {
            "$unset": {
                "notion_credentials": "",
                "notion_oauth_state": "",
                "notion_oauth_callback": "",
            }
        },
    )

    return JsonResponse({"success": True, "message": "Notion workspace disconnected successfully"})


@csrf_exempt
@require_http_methods(["GET"])
def notion_search(request):
    """Search connected Notion pages and data sources."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    body = {}
    query = request.GET.get("query")
    resource_filter = request.GET.get("filter")
    limit = request.GET.get("limit")
    cursor = request.GET.get("cursor")

    if query:
        body["query"] = query
    if resource_filter:
        body["filter"] = {"property": "object", "value": resource_filter}
    if limit:
        body["page_size"] = get_bounded_int(limit, 100, 100)
    if cursor:
        body["start_cursor"] = cursor

    data, error, status_code = make_notion_api_request("/search", notion_creds["access_token"], method="POST", data=body)
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse({
        "results": data.get("results", []),
        "nextCursor": data.get("next_cursor"),
        "hasMore": data.get("has_more", False),
    })


@csrf_exempt
@require_http_methods(["GET"])
def notion_get_page(request, page_id):
    """Get metadata and properties for a connected Notion page."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    data, error, status_code = make_notion_api_request(f"/pages/{page_id}", notion_creds["access_token"])
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data)


@csrf_exempt
@require_http_methods(["GET"])
def notion_get_page_blocks(request, page_id):
    """Read block children for a connected Notion page."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    params = {
        "page_size": get_bounded_int(request.GET.get("page_size"), 100, 100),
    }
    cursor = request.GET.get("cursor")
    if cursor:
        params["start_cursor"] = cursor

    data, error, status_code = make_notion_api_request(
        f"/blocks/{page_id}/children",
        notion_creds["access_token"],
        params=params,
    )
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse({
        "results": data.get("results", []),
        "nextCursor": data.get("next_cursor"),
        "hasMore": data.get("has_more", False),
    })


@csrf_exempt
@require_http_methods(["POST"])
def notion_query_data_source(request, data_source_id):
    """Query pages from a connected Notion data source."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    notion_body = {}
    if body.get("filter"):
        notion_body["filter"] = body["filter"]
    if body.get("sorts"):
        notion_body["sorts"] = body["sorts"]
    if body.get("pageSize"):
        notion_body["page_size"] = get_bounded_int(body.get("pageSize"), 100, 100)
    if body.get("startCursor"):
        notion_body["start_cursor"] = body["startCursor"]

    data, error, status_code = make_notion_api_request(
        f"/data_sources/{data_source_id}/query",
        notion_creds["access_token"],
        method="POST",
        data=notion_body,
    )
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse({
        "results": data.get("results", []),
        "nextCursor": data.get("next_cursor"),
        "hasMore": data.get("has_more", False),
    })


@csrf_exempt
@require_http_methods(["GET"])
def notion_list_templates(request, data_source_id):
    """List templates for a connected Notion data source."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    params = {
        "page_size": get_bounded_int(request.GET.get("page_size"), 100, 100),
    }
    start_cursor = request.GET.get("start_cursor")
    if start_cursor:
        params["start_cursor"] = start_cursor

    data, error, status_code = make_notion_api_request(
        f"/data_sources/{data_source_id}/templates",
        notion_creds["access_token"],
        params=params,
    )
    if error:
        return JsonResponse({"error": error}, status=status_code)

    templates = data.get("results", [])
    name_filter = request.GET.get("name")
    if name_filter:
        lowered_name_filter = name_filter.lower()
        templates = [
            template for template in templates
            if lowered_name_filter in json.dumps(template).lower()
        ]

    return JsonResponse({
        "results": templates,
        "nextCursor": data.get("next_cursor"),
        "hasMore": data.get("has_more", False),
    })


@csrf_exempt
@require_http_methods(["POST"])
def notion_create_page(request):
    """Create a page in the connected Notion workspace."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)
    if not body.get("parent"):
        return JsonResponse({"error": "Parent is required"}, status=400)

    data, error, status_code = make_notion_api_request(
        "/pages",
        notion_creds["access_token"],
        method="POST",
        data=body,
    )
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def notion_append_summary(request):
    """Append a meeting summary entry to the configured Notion database."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    name = get_required_string(body, "Name")
    summary = get_required_string(body, "Summary")
    sentiment = get_required_string(body, "Sentiment")
    timestamp = get_required_string(body, "Timestamp")
    missing_fields = [
        field_name for field_name, field_value in {
            "Name": name,
            "Summary": summary,
            "Sentiment": sentiment,
            "Timestamp": timestamp,
        }.items()
        if field_value is None
    ]
    if missing_fields:
        return JsonResponse({
            "error": "Missing required fields",
            "fields": missing_fields,
        }, status=400)

    notion_body = {
        "parent": {"database_id": NOTION_MEETING_SUMMARY_DATABASE_ID},
        "properties": build_summary_database_properties(
            name,
            summary,
            sentiment,
            timestamp,
        ),
    }
    data, error, status_code = make_notion_api_request(
        "/pages",
        notion_creds["access_token"],
        method="POST",
        data=notion_body,
    )
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def notion_create_page_from_template(request, data_source_id):
    """Create a page from a Notion data source template when supported by the Notion API."""
    _, notion_creds, error_response = get_authenticated_notion_credentials(request)
    if error_response:
        return error_response

    body = parse_json_body(request)
    if body is None:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    template_id = body.get("templateId")
    if not template_id:
        return JsonResponse({"error": "Template ID is required"}, status=400)

    notion_body = {
        "template": {"type": "template_id", "template_id": template_id},
    }
    if body.get("parent"):
        notion_body["parent"] = body["parent"]
    else:
        notion_body["parent"] = {"data_source_id": data_source_id}
    if body.get("properties"):
        notion_body["properties"] = body["properties"]

    data, error, status_code = make_notion_api_request(
        "/pages",
        notion_creds["access_token"],
        method="POST",
        data=notion_body,
    )
    if error:
        return JsonResponse({"error": error}, status=status_code)

    return JsonResponse(data, status=201)
