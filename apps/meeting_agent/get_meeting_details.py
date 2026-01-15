from django.http import JsonResponse
import requests
import os
import logging
from .models import MeetingSession

logger = logging.getLogger(__name__)


def get_meeting_details(request, session_id):
    """Get meeting details for a meeting session"""
    try:
        # Get username from token (following the pattern from other views)
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        # Get the session from the database
        result = MeetingSession.get_session(session_id, username)
        if not result["success"]:
            return JsonResponse({
                'error': result.get("error", "Session not found")
            }, status=404)
        
        session = result["session"]
        recording_id = session.get('recording_id')
        if not recording_id:
            return JsonResponse({
                'error': 'Recording ID not found for this session'
            }, status=404)
        api_key = os.environ.get('RECALL_API_KEY')
        if api_key:
            recording_response = requests.get(
                f'https://us-west-2.recall.ai/api/v1/recording/{recording_id}/',
                headers={
                    'Authorization': f'Token {api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            if recording_response.status_code == 200:
                recording_data = recording_response.json()
                return JsonResponse(recording_data)
            else:
                # Extract error details from response
                error_detail = {
                    'status_code': recording_response.status_code,
                    'error': 'Failed to get meeting details from Recall API'
                }
                try:
                    error_detail['message'] = recording_response.text[:500]  # Limit error message length
                except:
                    pass
                logger.error(f"Recall API returned status {recording_response.status_code} for session {session_id}")
                return JsonResponse(error_detail, status=500)
        else:
            logger.error("RECALL_API_KEY not configured")
            return JsonResponse({
                'error': 'RECALL_API_KEY not configured'
            }, status=500)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request exception while getting meeting details for session {session_id}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get meeting details from Recall API',
            'message': str(e)
        }, status=500)
    except Exception as e:
        logger.error(f"Failed to get meeting details for session {session_id}: {str(e)}")
        return JsonResponse({
            'error': 'Failed to get meeting details',
            'message': str(e)
        }, status=500)