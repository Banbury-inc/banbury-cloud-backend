"""
Google Calendar API service functions for handling calendar operations.
Uses the same Google credentials as Google Drive.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pymongo.mongo_client import MongoClient
from .google_drive_service import get_user_drive_credentials


def get_google_calendar_service(username: str):
    """Get Google Calendar service instance for a user using existing Google Drive credentials."""
    credentials = get_user_drive_credentials(username)
    if not credentials:
        return None
        
    try:
        # Check if the credentials have Calendar scope
        required_scopes = ['https://www.googleapis.com/auth/calendar']
        if not any(scope in credentials.scopes for scope in required_scopes):
            print(f"Google Calendar scope not found in credentials for user: {username}")
            return None
            
        service = build('calendar', 'v3', credentials=credentials)
        return service
        
    except Exception as e:
        print(f"Error building Google Calendar service: {e}")
        return None


def check_calendar_access(username: str) -> Dict[str, Any]:
    """Check if user has Google Calendar access."""
    try:
        credentials = get_user_drive_credentials(username)
        if not credentials:
            return {
                'has_access': False,
                'message': 'No Google credentials found. Please configure Google Drive integration first.'
            }
        
        # Check if Calendar scope is included
        required_scopes = ['https://www.googleapis.com/auth/calendar']
        has_calendar_scope = any(scope in credentials.scopes for scope in required_scopes)
        
        if not has_calendar_scope:
            return {
                'has_access': False,
                'message': 'Google Calendar scope not granted. Please re-authorize Google Drive integration to include Calendar access.'
            }
        
        # Try to build the service and make a test call
        service = build('calendar', 'v3', credentials=credentials)
        service.calendarList().list().execute()
        
        return {
            'has_access': True,
            'message': 'Google Calendar access confirmed'
        }
        
    except HttpError as e:
        if e.resp.status == 403:
            return {
                'has_access': False,
                'message': 'Google Calendar API not enabled or insufficient permissions'
            }
        return {
            'has_access': False,
            'message': f'Google Calendar API error: {str(e)}'
        }
    except Exception as e:
        return {
            'has_access': False,
            'message': f'Error checking Google Calendar access: {str(e)}'
        }


def list_calendar_events(
    username: str,
    calendar_id: str = 'primary',
    time_min: Optional[str] = None,
    time_max: Optional[str] = None,
    max_results: int = 50,
    q: Optional[str] = None
) -> Dict[str, Any]:
    """List calendar events for a user."""
    try:
        service = get_google_calendar_service(username)
        if not service:
            return {
                'error': 'Google Calendar service not available. Please check your Google credentials.'
            }
        
        # Build the request parameters
        request_params = {
            'calendarId': calendar_id,
            'maxResults': max_results,
            'singleEvents': True,
            'orderBy': 'startTime'
        }
        
        if time_min:
            request_params['timeMin'] = time_min
        if time_max:
            request_params['timeMax'] = time_max
        if q:
            request_params['q'] = q
        
        # Execute the request
        events_result = service.events().list(**request_params).execute()
        events = events_result.get('items', [])
        
        return {
            'events': events,
            'count': len(events)
        }
        
    except HttpError as e:
        return {
            'error': f'Google Calendar API error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Error listing calendar events: {str(e)}'
        }


def get_calendar_event(username: str, event_id: str, calendar_id: str = 'primary') -> Dict[str, Any]:
    """Get details of a specific calendar event."""
    try:
        service = get_google_calendar_service(username)
        if not service:
            return {
                'error': 'Google Calendar service not available. Please check your Google credentials.'
            }
        
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        
        return event
        
    except HttpError as e:
        if e.resp.status == 404:
            return {
                'error': f'Event with ID {event_id} not found'
            }
        return {
            'error': f'Google Calendar API error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Error retrieving calendar event: {str(e)}'
        }


def create_calendar_event(username: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new calendar event."""
    try:
        service = get_google_calendar_service(username)
        if not service:
            return {
                'error': 'Google Calendar service not available. Please check your Google credentials.'
            }
        
        calendar_id = event_data.pop('calendarId', 'primary')
        
        # Create the event
        event = service.events().insert(calendarId=calendar_id, body=event_data).execute()
        
        return event
        
    except HttpError as e:
        return {
            'error': f'Google Calendar API error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Error creating calendar event: {str(e)}'
        }


def update_calendar_event(username: str, event_id: str, event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Update an existing calendar event."""
    try:
        service = get_google_calendar_service(username)
        if not service:
            return {
                'error': 'Google Calendar service not available. Please check your Google credentials.'
            }
        
        calendar_id = event_data.pop('calendarId', 'primary')
        
        # Update the event
        event = service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_data
        ).execute()
        
        return event
        
    except HttpError as e:
        if e.resp.status == 404:
            return {
                'error': f'Event with ID {event_id} not found'
            }
        return {
            'error': f'Google Calendar API error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Error updating calendar event: {str(e)}'
        }


def delete_calendar_event(username: str, event_id: str, calendar_id: str = 'primary') -> Dict[str, Any]:
    """Delete a calendar event."""
    try:
        service = get_google_calendar_service(username)
        if not service:
            return {
                'error': 'Google Calendar service not available. Please check your Google credentials.'
            }
        
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        
        return {
            'success': True,
            'message': f'Event {event_id} deleted successfully'
        }
        
    except HttpError as e:
        if e.resp.status == 404:
            return {
                'error': f'Event with ID {event_id} not found'
            }
        return {
            'error': f'Google Calendar API error: {str(e)}'
        }
    except Exception as e:
        return {
            'error': f'Error deleting calendar event: {str(e)}'
        } 