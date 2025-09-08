import os
import requests


def run_prompt_via_langgraph(prompt: str, bearer_token: str | None = None) -> str:
    """Call the Banbury-Website langgraph-stream endpoint and return the accumulated text.

    Environment:
      - BANBURY_WEBSITE_ORIGIN (e.g., https://app.dev.banbury.io or http://localhost:3000)
    """
    origin = os.getenv('BANBURY_WEBSITE_ORIGIN', 'https://www.banbury.io')
    url = f"{origin}/api/assistant/langgraph-stream"

    headers = {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
    }
    import logging
    logging.getLogger('taskstudio_daemon').info(f"bearer_token: {bearer_token}")
    if bearer_token:
        headers['Authorization'] = f"Bearer {bearer_token}"

    payload = {
        'messages': [
            { 'role': 'user', 'content': [ { 'type': 'text', 'text': prompt } ] }
        ],
        'recursionLimit': 1000,
        'toolPreferences': {
            'web_search': True,
            'read_file': True,
            'gmail': True,
            'browser': False,
            'browserbase': False,
            'x_api': False,
            'langgraph_mode': True,
            'tiptap_ai': True,
        },
    }

    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=300) as resp:
            if resp.status_code == 401:
                raise Exception("Authentication failed - bearer token may be expired or invalid")
            elif resp.status_code == 403:
                raise Exception("Access forbidden - bearer token may lack required permissions")
            resp.raise_for_status()
            full_text: str = ''
            buffer: str = ''
            for chunk in resp.iter_content(chunk_size=8192):
                if not chunk:
                    continue
                buffer += chunk.decode('utf-8', errors='ignore')
                # Events are separated by double newlines
                parts = buffer.split('\n\n')
                buffer = parts.pop() or ''
                for part in parts:
                    line = part.strip()
                    if not line.startswith('data:'):
                        continue
                    data = line[5:].strip()
                    if not data:
                        continue
                    try:
                        import json as _json
                        evt = _json.loads(data)
                        if isinstance(evt, dict) and evt.get('type') == 'text-delta':
                            text_piece = evt.get('text')
                            if isinstance(text_piece, str):
                                full_text += text_piece
                    except Exception:
                        # Ignore malformed event frames
                        continue
            return full_text.strip()
    except requests.exceptions.RequestException as e:
        if "401" in str(e) or "Unauthorized" in str(e):
            raise Exception(f"Authentication failed - bearer token may be expired: {str(e)}")
        elif "403" in str(e) or "Forbidden" in str(e):
            raise Exception(f"Access forbidden - bearer token may lack permissions: {str(e)}")
        else:
            raise Exception(f"Request failed: {str(e)}")


