"""
Flow node executor dispatcher.
Each executor module exposes an `execute(node_data, inputs, username, **kwargs)` function
and returns: { 'status': 'success'|'failed', 'data': {...}, 'error': str|None }
"""
from . import (
    format_executor,
    filter_executor,
    http_executor,
    database_executor,
    slack_executor,
    gmail_executor,
    calendar_executor,
    github_executor,
    x_api_executor,
    drive_executor,
    python_executor,
)


def execute_node(node: dict, inputs: dict, username: str) -> dict:
    """
    Execute a single flow node.

    Args:
        node: The node dict from graph_json (has 'id', 'type', 'data')
        inputs: Mapping of source_node_id -> output dict from that node
        username: The authenticated user running the flow

    Returns:
        Dict with 'status', 'data', and optional 'error'.
    """
    node_type = node.get('type', '')
    node_data = node.get('data', {})

    try:
        if node_type == 'start':
            return {'status': 'success', 'data': {}}

        if node_type == 'output':
            # Collect all upstream text/data for display
            parts = []
            for upstream in inputs.values():
                if isinstance(upstream, dict):
                    data = upstream.get('data', upstream)
                    if isinstance(data, dict):
                        text = data.get('text') or data.get('output') or str(data)
                    else:
                        text = str(data)
                    parts.append(text)
            return {'status': 'success', 'data': {'output': '\n'.join(parts)}}

        if node_type == 'format-text':
            return format_executor.execute(node_data, inputs)

        if node_type == 'filter-data':
            return filter_executor.execute(node_data, inputs)

        if node_type == 'http-request':
            return http_executor.execute(node_data, inputs)

        if node_type == 'database-query':
            return database_executor.execute(node_data, inputs, username)

        if node_type == 'slack-send-message':
            return slack_executor.execute(node_data, inputs, username)

        if node_type == 'gmail-send':
            return gmail_executor.execute(node_data, inputs, username)

        if node_type in ('google-calendar', 'microsoft-calendar'):
            return calendar_executor.execute(node_data, inputs, username, node_type)

        if node_type == 'github':
            return github_executor.execute(node_data, inputs, username)

        if node_type == 'x-api':
            return x_api_executor.execute(node_data, inputs, username)

        if node_type in ('google-drive', 'onedrive'):
            return drive_executor.execute(node_data, inputs, username, node_type)

        if node_type == 'python-code':
            return python_executor.execute(node_data, inputs, username)

        return {'status': 'skipped', 'data': {}, 'note': f'No executor for node type: {node_type}'}

    except Exception as exc:
        return {'status': 'failed', 'error': str(exc), 'data': {}}
