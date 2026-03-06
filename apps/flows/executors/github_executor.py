"""
GitHub executor: list repos/issues, create issues, search code, get file contents.
"""
import re
import requests as http_requests
from pymongo import MongoClient
import os

_MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
)


def _get_github_token(username: str) -> str | None:
    client = MongoClient(_MONGO_URI)
    db = client["NeuraNet"]
    user = db["users"].find_one({"username": username})
    if not user:
        return None
    return user.get('github_access_token') or user.get('github_credentials', {}).get('access_token')


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
    operation = node_data.get('operation', 'list-repos')
    token = _get_github_token(username)
    if not token:
        return {'status': 'failed', 'error': 'GitHub is not connected'}

    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)

    headers = {
        'Authorization': f'token {token}',
        'Accept': 'application/vnd.github.v3+json',
    }
    base = 'https://api.github.com'

    owner = _resolve(node_data.get('owner', ''), context)
    repo = _resolve(node_data.get('repo', ''), context)

    try:
        if operation == 'list-repos':
            r = http_requests.get(f'{base}/user/repos', headers=headers, params={'per_page': 50}, timeout=15)
            return {'status': 'success', 'data': {'repositories': r.json()}}

        if operation == 'get-repo':
            r = http_requests.get(f'{base}/repos/{owner}/{repo}', headers=headers, timeout=15)
            return {'status': 'success', 'data': {'repository': r.json()}}

        if operation == 'list-issues':
            r = http_requests.get(f'{base}/repos/{owner}/{repo}/issues', headers=headers, params={'per_page': 50}, timeout=15)
            return {'status': 'success', 'data': {'issues': r.json()}}

        if operation == 'create-issue':
            title = _resolve(node_data.get('title', ''), context)
            body = _resolve(node_data.get('body', ''), context)
            r = http_requests.post(
                f'{base}/repos/{owner}/{repo}/issues',
                headers=headers,
                json={'title': title, 'body': body},
                timeout=15,
            )
            return {'status': 'success', 'data': {'issue': r.json()}}

        if operation == 'list-prs':
            r = http_requests.get(f'{base}/repos/{owner}/{repo}/pulls', headers=headers, params={'per_page': 50}, timeout=15)
            return {'status': 'success', 'data': {'pull_requests': r.json()}}

        if operation == 'get-file':
            path = _resolve(node_data.get('path', ''), context)
            r = http_requests.get(f'{base}/repos/{owner}/{repo}/contents/{path}', headers=headers, timeout=15)
            return {'status': 'success', 'data': {'file': r.json()}}

        if operation == 'search-code':
            query = _resolve(node_data.get('query', ''), context)
            r = http_requests.get(f'{base}/search/code', headers=headers, params={'q': query, 'per_page': 30}, timeout=15)
            return {'status': 'success', 'data': r.json()}

        return {'status': 'failed', 'error': f'Unknown operation: {operation}'}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
