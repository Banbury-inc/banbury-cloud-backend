"""
HTTP Request executor: makes HTTP requests with optional template variable substitution.
"""
import re
import json
import requests as http_requests


def _resolve(value: str, context: dict) -> str:
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

    return re.sub(r'\{\{([^}]+)\}\}', replace, value)


def execute(node_data: dict, inputs: dict) -> dict:
    method = node_data.get('method', 'GET').upper()
    url = node_data.get('url', '')
    headers = node_data.get('headers', {})
    body_template = node_data.get('body', '')

    if not url:
        return {'status': 'failed', 'error': 'URL is required'}

    # Build context from inputs for template substitution
    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)

    resolved_url = _resolve(url, context)
    resolved_headers = {k: _resolve(v, context) for k, v in (headers or {}).items()}

    body = None
    if body_template and method not in ('GET', 'DELETE'):
        resolved_body = _resolve(body_template, context)
        try:
            body = json.loads(resolved_body)
        except (json.JSONDecodeError, ValueError):
            body = resolved_body

    try:
        response = http_requests.request(
            method=method,
            url=resolved_url,
            headers=resolved_headers,
            json=body if isinstance(body, dict) else None,
            data=body if isinstance(body, str) else None,
            timeout=30,
        )
        try:
            data = response.json()
        except Exception:
            data = {'text': response.text}

        return {
            'status': 'success' if response.ok else 'failed',
            'data': data,
            'status_code': response.status_code,
        }
    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
