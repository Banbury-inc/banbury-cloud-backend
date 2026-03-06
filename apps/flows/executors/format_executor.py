"""
Format Text executor: replaces {{variable}} placeholders with values from inputs.
"""
import re


def _resolve(template: str, context: dict) -> str:
    """Replace {{key}} and {{a.b.c}} references in template from context dict."""
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


def execute(node_data: dict, inputs: dict) -> dict:
    template = node_data.get('template', '')
    if not template:
        return {'status': 'success', 'data': {'text': ''}}

    # Build a flat context from all upstream inputs
    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)

    result = _resolve(template, context)
    return {'status': 'success', 'data': {'text': result}}
