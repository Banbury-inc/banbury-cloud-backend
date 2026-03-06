"""
Drive executor: Google Drive and OneDrive operations.
"""
import re
import requests as http_requests
from pymongo import MongoClient
import os

_MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
)


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


def _build_context(inputs: dict) -> dict:
    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)
    return context


# ---- Google Drive ----

def _execute_google_drive(node_data: dict, inputs: dict, username: str) -> dict:
    operation = node_data.get('operation', 'list')
    context = _build_context(inputs)

    try:
        from apps.files.google_drive_service import get_user_drive_credentials
        from googleapiclient.discovery import build

        creds = get_user_drive_credentials(username)
        if not creds:
            return {'status': 'failed', 'error': 'Google Drive is not connected'}

        service = build('drive', 'v3', credentials=creds)

        if operation == 'list':
            folder_id = _resolve(node_data.get('folderId', ''), context)
            q = f"'{folder_id}' in parents" if folder_id else None
            params = {'pageSize': 50, 'fields': 'files(id,name,mimeType,size,modifiedTime)'}
            if q:
                params['q'] = q
            result = service.files().list(**params).execute()
            return {'status': 'success', 'data': {'files': result.get('files', [])}}

        if operation == 'search':
            query = _resolve(node_data.get('query', ''), context)
            result = service.files().list(
                q=query,
                pageSize=50,
                fields='files(id,name,mimeType,size,modifiedTime)',
            ).execute()
            return {'status': 'success', 'data': {'files': result.get('files', [])}}

        if operation == 'get':
            file_id = _resolve(node_data.get('fileId', ''), context)
            f = service.files().get(fileId=file_id, fields='id,name,mimeType,size,modifiedTime').execute()
            return {'status': 'success', 'data': {'file': f}}

        return {'status': 'failed', 'error': f'Unknown operation: {operation}'}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


# ---- OneDrive ----

def _get_ms_token(username: str) -> str | None:
    client = MongoClient(_MONGO_URI)
    db = client["NeuraNet"]
    user = db["users"].find_one({"username": username})
    if not user:
        return None
    return user.get('outlook_access_token') or user.get('ms_access_token') or user.get('onedrive_access_token')


def _execute_onedrive(node_data: dict, inputs: dict, username: str) -> dict:
    operation = node_data.get('operation', 'list')
    context = _build_context(inputs)

    token = _get_ms_token(username)
    if not token:
        return {'status': 'failed', 'error': 'OneDrive is not connected'}

    headers = {'Authorization': f'Bearer {token}'}
    base = 'https://graph.microsoft.com/v1.0/me/drive'

    try:
        if operation == 'list':
            folder_id = _resolve(node_data.get('folderId', ''), context)
            url = f'{base}/items/{folder_id}/children' if folder_id else f'{base}/root/children'
            r = http_requests.get(url, headers=headers, timeout=15)
            return {'status': 'success', 'data': r.json()}

        if operation == 'search':
            query = _resolve(node_data.get('query', ''), context)
            r = http_requests.get(f'{base}/root/search(q=\'{query}\')', headers=headers, timeout=15)
            return {'status': 'success', 'data': r.json()}

        if operation == 'get':
            file_id = _resolve(node_data.get('fileId', ''), context)
            r = http_requests.get(f'{base}/items/{file_id}', headers=headers, timeout=15)
            return {'status': 'success', 'data': r.json()}

        return {'status': 'failed', 'error': f'Unknown operation: {operation}'}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


# ---- Dispatcher ----

def execute(node_data: dict, inputs: dict, username: str, node_type: str) -> dict:
    if node_type == 'google-drive':
        return _execute_google_drive(node_data, inputs, username)
    if node_type == 'onedrive':
        return _execute_onedrive(node_data, inputs, username)
    return {'status': 'failed', 'error': f'Unknown drive type: {node_type}'}
