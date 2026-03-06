"""
Gmail executor: sends emails via Gmail using stored Google credentials.
Supports {{variable}} template substitution.
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


def execute(node_data: dict, inputs: dict, username: str) -> dict:
    to_template = node_data.get('to', '')
    subject_template = node_data.get('subject', '')
    body_template = node_data.get('body', '')
    cc_template = node_data.get('cc', '')
    bcc_template = node_data.get('bcc', '')

    if not to_template:
        return {'status': 'failed', 'error': '"To" address is required'}
    if not subject_template:
        return {'status': 'failed', 'error': 'Subject is required'}

    # Build context from upstream inputs
    context = {}
    for upstream_output in inputs.values():
        if isinstance(upstream_output, dict):
            data = upstream_output.get('data', upstream_output)
            if isinstance(data, dict):
                context.update(data)

    try:
        from apps.files.gmail_service import get_gmail_service
        import base64
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        service = get_gmail_service(username)
        if not service:
            return {'status': 'failed', 'error': 'Gmail is not connected for this user'}

        rows = context.get('rows') or context.get('items') or context.get('results')
        contexts_to_send = []
        if isinstance(rows, list) and rows:
            for row in rows:
                row_context = {**context, **row} if isinstance(row, dict) else context
                contexts_to_send.append(row_context)
        else:
            contexts_to_send.append(context)

        sent = 0
        errors = []

        for ctx in contexts_to_send:
            to = _resolve(to_template, ctx)
            subject = _resolve(subject_template, ctx)
            body = _resolve(body_template, ctx)
            cc = _resolve(cc_template, ctx) if cc_template else ''
            bcc = _resolve(bcc_template, ctx) if bcc_template else ''

            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            if cc:
                message['cc'] = cc
            if bcc:
                message['bcc'] = bcc
            message.attach(MIMEText(body, 'plain'))

            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            result = service.users().messages().send(userId='me', body={'raw': raw}).execute()

            if result.get('id'):
                sent += 1
            else:
                errors.append('Send failed')

        if errors and sent == 0:
            return {'status': 'failed', 'error': '; '.join(errors)}

        return {'status': 'success', 'data': {'emails_sent': sent}}

    except Exception as e:
        return {'status': 'failed', 'error': str(e)}
