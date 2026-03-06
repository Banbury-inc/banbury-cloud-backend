"""
Slack executor: sends messages via the Slack API using the user's stored credentials.
Supports {{variable}} template substitution in the message.
"""
import re
from pymongo import MongoClient
import os
import requests as http_requests

_MONGO_URI = os.getenv(
    "MONGODB_URI",
    "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority",
)


def _get_slack_token(username: str) -> str | None:
    client = MongoClient(_MONGO_URI)
    db = client["NeuraNet"]
    user = db["users"].find_one({"username": username})
    if not user:
        return None
    return user.get('slack_credentials', {}).get('access_token')


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


def _resolve_channel_id(channel_name_or_id: str, token: str) -> str:
    """Resolve channel name to ID if needed."""
    if channel_name_or_id and (
        channel_name_or_id.startswith('C') or channel_name_or_id.startswith('G')
    ):
        return channel_name_or_id

    name = channel_name_or_id.lstrip('#')
    resp = http_requests.get(
        'https://slack.com/api/conversations.list',
        headers={'Authorization': f'Bearer {token}'},
        params={'limit': 200},
        timeout=15,
    )
    if resp.ok:
        for ch in resp.json().get('channels', []):
            if ch.get('name') == name:
                return ch['id']
    return channel_name_or_id


def execute(node_data: dict, inputs: dict, username: str) -> dict:
    channel = node_data.get('channel', '')
    message_template = node_data.get('messageTemplate', '')

    if not channel:
        return {'status': 'failed', 'error': 'Slack channel is required'}
    if not message_template:
        return {'status': 'failed', 'error': 'Message template is required'}

    token = _get_slack_token(username)
    if not token:
        return {'status': 'failed', 'error': 'Slack is not connected for this user'}

    # Build context from upstream inputs for template resolution
    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)

    # If upstream has rows, send one message per row (or join as text)
    rows = context.get('rows') or context.get('items') or context.get('results')

    messages_to_send = []
    if isinstance(rows, list) and rows:
        for row in rows:
            row_context = {**context, **row} if isinstance(row, dict) else context
            messages_to_send.append(_resolve(message_template, row_context))
    else:
        messages_to_send.append(_resolve(message_template, context))

    channel_id = _resolve_channel_id(channel, token)

    sent = 0
    errors = []
    for msg_text in messages_to_send:
        resp = http_requests.post(
            'https://slack.com/api/chat.postMessage',
            headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
            json={'channel': channel_id, 'text': msg_text},
            timeout=15,
        )
        result = resp.json() if resp.ok else {}
        if result.get('ok'):
            sent += 1
        else:
            errors.append(result.get('error', f'HTTP {resp.status_code}'))

    if errors and sent == 0:
        return {'status': 'failed', 'error': '; '.join(errors)}

    return {
        'status': 'success',
        'data': {'messages_sent': sent, 'channel': channel_id},
    }
