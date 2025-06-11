"""
Gmail API service functions for handling Gmail operations.
Uses the same Google credentials as Google Drive.
"""

import base64
import email
from datetime import datetime
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pymongo.mongo_client import MongoClient
from .google_drive_service import get_user_drive_credentials


def get_gmail_service(username: str):
    """Get Gmail service instance for a user using existing Google Drive credentials."""
    credentials = get_user_drive_credentials(username)
    if not credentials:
        return None
        
    try:
        # Check if the credentials have Gmail scope
        required_scopes = ['https://www.googleapis.com/auth/gmail.modify']
        if not any(scope in credentials.scopes for scope in required_scopes):
            print(f"Gmail scope not found in credentials for user: {username}")
            return None
            
        service = build('gmail', 'v1', credentials=credentials)
        return service
        
    except Exception as e:
        print(f"Error building Gmail service: {e}")
        return None


def search_emails(username: str, query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search for emails using Gmail API."""
    try:
        service = get_gmail_service(username)
        if not service:
            return {
                "result": "error",
                "error": "Gmail service not available. Please ensure Google Drive integration is configured with Gmail scope."
            }
        
        # Search for messages
        results = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=max_results
        ).execute()
        
        messages = results.get('messages', [])
        
        if not messages:
            return {
                "result": "success",
                "messages": [],
                "total_count": 0
            }
        
        # Get basic info for each message
        message_list = []
        for msg in messages:
            try:
                message = service.users().messages().get(
                    userId='me',
                    id=msg['id'],
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                
                # Extract common fields
                from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                subject_header = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
                
                message_list.append({
                    'id': message['id'],
                    'threadId': message['threadId'],
                    'snippet': message.get('snippet', ''),
                    'from': from_header,
                    'subject': subject_header,
                    'date': date_header
                })
                
            except Exception as e:
                print(f"Error getting message {msg['id']}: {e}")
                continue
        
        return {
            "result": "success",
            "messages": message_list,
            "total_count": len(message_list)
        }
        
    except HttpError as e:
        print(f"Gmail API error in search_emails: {e}")
        return {
            "result": "error",
            "error": f"Gmail API error: {str(e)}"
        }
    except Exception as e:
        print(f"Error searching emails: {e}")
        return {
            "result": "error",
            "error": f"Error searching emails: {str(e)}"
        }


def get_message(username: str, message_id: str) -> Dict[str, Any]:
    """Get a specific email message by ID."""
    try:
        service = get_gmail_service(username)
        if not service:
            return {
                "result": "error",
                "error": "Gmail service not available"
            }
        
        message = service.users().messages().get(
            userId='me',
            id=message_id,
            format='full'
        ).execute()
        
        headers = message['payload'].get('headers', [])
        
        # Extract headers
        from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
        to_header = next((h['value'] for h in headers if h['name'] == 'To'), 'Unknown')
        subject_header = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
        
        # Extract body
        body = extract_message_body(message['payload'])
        
        return {
            "result": "success",
            "id": message['id'],
            "threadId": message['threadId'],
            "from": from_header,
            "to": to_header,
            "subject": subject_header,
            "date": date_header,
            "body": body,
            "snippet": message.get('snippet', '')
        }
        
    except HttpError as e:
        print(f"Gmail API error in get_message: {e}")
        return {
            "result": "error",
            "error": f"Gmail API error: {str(e)}"
        }
    except Exception as e:
        print(f"Error getting message: {e}")
        return {
            "result": "error",
            "error": f"Error getting message: {str(e)}"
        }


def get_thread(username: str, thread_id: str) -> Dict[str, Any]:
    """Get an email thread by ID."""
    try:
        service = get_gmail_service(username)
        if not service:
            return {
                "result": "error",
                "error": "Gmail service not available"
            }
        
        thread = service.users().threads().get(
            userId='me',
            id=thread_id,
            format='metadata',
            metadataHeaders=['From', 'Subject', 'Date']
        ).execute()
        
        messages = []
        for msg in thread.get('messages', []):
            headers = msg['payload'].get('headers', [])
            
            from_header = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            subject_header = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            date_header = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown Date')
            
            messages.append({
                'id': msg['id'],
                'from': from_header,
                'subject': subject_header,
                'date': date_header,
                'snippet': msg.get('snippet', '')
            })
        
        return {
            "result": "success",
            "id": thread['id'],
            "messages": messages
        }
        
    except HttpError as e:
        print(f"Gmail API error in get_thread: {e}")
        return {
            "result": "error",
            "error": f"Gmail API error: {str(e)}"
        }
    except Exception as e:
        print(f"Error getting thread: {e}")
        return {
            "result": "error",
            "error": f"Error getting thread: {str(e)}"
        }


def create_draft(username: str, to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> Dict[str, Any]:
    """Create a draft email."""
    try:
        service = get_gmail_service(username)
        if not service:
            return {
                "result": "error",
                "error": "Gmail service not available"
            }
        
        message = create_message(to, subject, body, cc, bcc)
        
        draft = service.users().drafts().create(
            userId='me',
            body={'message': message}
        ).execute()
        
        return {
            "result": "success",
            "id": draft['id'],
            "message": "Draft created successfully"
        }
        
    except HttpError as e:
        print(f"Gmail API error in create_draft: {e}")
        return {
            "result": "error",
            "error": f"Gmail API error: {str(e)}"
        }
    except Exception as e:
        print(f"Error creating draft: {e}")
        return {
            "result": "error",
            "error": f"Error creating draft: {str(e)}"
        }


def send_message(username: str, to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> Dict[str, Any]:
    """Send an email message."""
    try:
        service = get_gmail_service(username)
        if not service:
            return {
                "result": "error",
                "error": "Gmail service not available"
            }
        
        message = create_message(to, subject, body, cc, bcc)
        
        sent_message = service.users().messages().send(
            userId='me',
            body=message
        ).execute()
        
        return {
            "result": "success",
            "id": sent_message['id'],
            "message": "Email sent successfully"
        }
        
    except HttpError as e:
        print(f"Gmail API error in send_message: {e}")
        return {
            "result": "error",
            "error": f"Gmail API error: {str(e)}"
        }
    except Exception as e:
        print(f"Error sending message: {e}")
        return {
            "result": "error",
            "error": f"Error sending message: {str(e)}"
        }


def create_message(to: str, subject: str, body: str, cc: str = None, bcc: str = None) -> Dict[str, Any]:
    """Create a message for Gmail API."""
    message = email.mime.text.MIMEText(body)
    message['to'] = to
    message['subject'] = subject
    
    if cc:
        message['cc'] = cc
    if bcc:
        message['bcc'] = bcc
    
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    
    return {'raw': raw_message}


def extract_message_body(payload: Dict[str, Any]) -> str:
    """Extract the body text from a message payload."""
    body = ""
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
                    break
            elif part['mimeType'] == 'text/html' and not body:
                data = part['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8')
    else:
        if payload['body'].get('data'):
            body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    return body


def check_gmail_access(username: str) -> Dict[str, Any]:
    """Check if user has Gmail access through existing Google credentials."""
    try:
        credentials = get_user_drive_credentials(username)
        if not credentials:
            return {
                "result": "error",
                "has_access": False,
                "message": "No Google credentials found"
            }
        
        # Check if Gmail scope is available
        gmail_scopes = [
            'https://www.googleapis.com/auth/gmail.modify',
            'https://www.googleapis.com/auth/gmail.readonly'
        ]
        
        has_gmail_scope = any(scope in credentials.scopes for scope in gmail_scopes)
        
        if not has_gmail_scope:
            return {
                "result": "warning",
                "has_access": False,
                "message": "Google credentials found but Gmail scope not granted. Re-authenticate to get Gmail access."
            }
        
        # Try to build Gmail service
        service = build('gmail', 'v1', credentials=credentials)
        
        # Test access with a simple profile call
        profile = service.users().getProfile(userId='me').execute()
        
        return {
            "result": "success",
            "has_access": True,
            "message": "Gmail access confirmed",
            "email": profile.get('emailAddress', 'Unknown')
        }
        
    except Exception as e:
        return {
            "result": "error",
            "has_access": False,
            "message": f"Error checking Gmail access: {str(e)}"
        } 