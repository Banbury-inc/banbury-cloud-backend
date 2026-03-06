"""
X (Twitter) API executor.
"""
import re
import requests as http_requests
from pymongo import MongoClient
import os

_MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
)


def _get_x_credentials(username: str) -> dict | None:
    client = MongoClient(_MONGO_URI)
    db = client["NeuraNet"]
    user = db["users"].find_one({"username": username})
    if not user:
        return None
    creds = user.get('x_credentials') or user.get('twitter_credentials') or {}
    if not creds.get('access_token') and not creds.get('bearer_token'):
        return None
    return creds


def _resolve(template: str, context: dict) -> str:
    def replace(match):
        key_path = match.group(1).strip()
        parts = key_path.split('.')
        val = context
        for p in parts:
            if isinstance(val, dict):
                val = val.get(p)
            else:
                return match.group(0)
            if val is None:
                return ''
        return str(val)
    return re.sub(r'\{\{([^}]+)\}\}', replace, template)


def execute(node_data: dict, inputs: dict, username: str) -> dict:
    operation = node_data.get('operation', 'search')

    creds = _get_x_credentials(username)
    if not creds:
        return {'status': 'failed', 'error': 'X (Twitter) is not connected'}

    bearer = creds.get('bearer_token')
    access_token = creds.get('access_token')

    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)

    try:
        if operation == 'search':
            query = _resolve(node_data.get('query', ''), context)
            headers = {'Authorization': f'Bearer {bearer}'} if bearer else {}
            r = http_requests.get(
                'https://api.twitter.com/2/tweets/search/recent',
                headers=headers,
                params={'query': query, 'max_results': 10},
                timeout=15,
            )
            return {'status': 'success', 'data': r.json()}

        if operation == 'post-tweet':
            text = _resolve(node_data.get('text', ''), context)
            if not access_token:
                return {'status': 'failed', 'error': 'OAuth access token required to post tweets'}
            # Use OAuth 1.0a for posting — delegates to backend proxy
            r = http_requests.post(
                'https://api.twitter.com/2/tweets',
                headers={'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'},
                json={'text': text},
                timeout=15,
            )
            return {'status': 'success' if r.ok else 'failed', 'data': r.json()}

        if operation == 'get-user':
            username_param = _resolve(node_data.get('username', ''), context)
            headers = {'Authorization': f'Bearer {bearer}'} if bearer else {}
            r = http_requests.get(
                f'https://api.twitter.com/2/users/by/username/{username_param}',
                headers=headers,
                timeout=15,
            )
            return {'status': 'success', 'data': r.json()}

        if operation == 'get-tweets':
            target_username = _resolve(node_data.get('username', ''), context)
            headers = {'Authorization': f'Bearer {bearer}'} if bearer else {}
            # First resolve to user id
            r_user = http_requests.get(
                f'https://api.twitter.com/2/users/by/username/{target_username}',
                headers=headers, timeout=15,
            )
            user_id = r_user.json().get('data', {}).get('id')
            if not user_id:
                return {'status': 'failed', 'error': 'User not found'}
            r = http_requests.get(
                f'https://api.twitter.com/2/users/{user_id}/tweets',
                headers=headers,
                params={'max_results': 10},
                timeout=15,
            )
            return {'status': 'success', 'data': r.json()}

        return {'status': 'failed', 'error': f'Unknown operation: {operation}'}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
