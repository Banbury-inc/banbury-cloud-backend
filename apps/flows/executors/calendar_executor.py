"""
Calendar executor: Google Calendar and Microsoft Calendar operations.
"""
import re


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


# ---- Google Calendar ----

def _execute_google(node_data: dict, inputs: dict, username: str) -> dict:
    operation = node_data.get('operation', 'list')
    calendar_id = node_data.get('calendarId') or 'primary'
    context = _build_context(inputs)

    try:
        from apps.files.google_drive_service import get_user_drive_credentials
        from googleapiclient.discovery import build

        creds = get_user_drive_credentials(username)
        if not creds:
            return {'status': 'failed', 'error': 'Google Calendar is not connected'}

        service = build('calendar', 'v3', credentials=creds)

        if operation == 'list':
            time_min = _resolve(node_data.get('timeMin', ''), context) or None
            time_max = _resolve(node_data.get('timeMax', ''), context) or None
            params = {'calendarId': calendar_id, 'maxResults': 50, 'singleEvents': True, 'orderBy': 'startTime'}
            if time_min:
                params['timeMin'] = time_min
            if time_max:
                params['timeMax'] = time_max
            result = service.events().list(**params).execute()
            return {'status': 'success', 'data': {'events': result.get('items', [])}}

        if operation == 'get':
            event_id = _resolve(node_data.get('eventId', ''), context)
            event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            return {'status': 'success', 'data': {'event': event}}

        if operation == 'create':
            event_body = node_data.get('event') or {}
            event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
            return {'status': 'success', 'data': {'event': event}}

        if operation == 'update':
            event_id = _resolve(node_data.get('eventId', ''), context)
            event_body = node_data.get('event') or {}
            event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event_body).execute()
            return {'status': 'success', 'data': {'event': event}}

        if operation == 'delete':
            event_id = _resolve(node_data.get('eventId', ''), context)
            service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return {'status': 'success', 'data': {'deleted': True}}

        return {'status': 'failed', 'error': f'Unknown operation: {operation}'}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


# ---- Microsoft Calendar ----

def _get_ms_token(username: str) -> str | None:
    from pymongo import MongoClient
    import os
    uri = os.getenv("MONGODB_URI", "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority")
    client = MongoClient(uri)
    db = client["NeuraNet"]
    user = db["users"].find_one({"username": username})
    if not user:
        return None
    return user.get('outlook_access_token') or user.get('ms_access_token')


def _execute_microsoft(node_data: dict, inputs: dict, username: str) -> dict:
    import requests as http_requests
    operation = node_data.get('operation', 'list')
    calendar_id = node_data.get('calendarId', '')
    context = _build_context(inputs)

    token = _get_ms_token(username)
    if not token:
        return {'status': 'failed', 'error': 'Microsoft Calendar is not connected'}

    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
    base = 'https://graph.microsoft.com/v1.0/me'
    cal_base = f'{base}/calendars/{calendar_id}/events' if calendar_id else f'{base}/events'

    try:
        if operation == 'list-calendars':
            r = http_requests.get(f'{base}/calendars', headers=headers, timeout=15)
            return {'status': 'success', 'data': r.json()}

        if operation == 'list':
            params = {}
            time_min = _resolve(node_data.get('timeMin', ''), context) or None
            time_max = _resolve(node_data.get('timeMax', ''), context) or None
            if time_min or time_max:
                filter_parts = []
                if time_min:
                    filter_parts.append(f"start/dateTime ge '{time_min}'")
                if time_max:
                    filter_parts.append(f"end/dateTime le '{time_max}'")
                params['$filter'] = ' and '.join(filter_parts)
            r = http_requests.get(cal_base, headers=headers, params=params, timeout=15)
            return {'status': 'success', 'data': r.json()}

        if operation == 'create':
            event_body = node_data.get('event') or {}
            r = http_requests.post(cal_base, headers=headers, json=event_body, timeout=15)
            return {'status': 'success', 'data': r.json()}

        return {'status': 'failed', 'error': f'Unknown operation: {operation}'}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}


# ---- Dispatcher ----

def execute(node_data: dict, inputs: dict, username: str, node_type: str) -> dict:
    if node_type == 'google-calendar':
        return _execute_google(node_data, inputs, username)
    if node_type == 'microsoft-calendar':
        return _execute_microsoft(node_data, inputs, username)
    return {'status': 'failed', 'error': f'Unknown calendar type: {node_type}'}
