from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging
import re
import json
from urllib.parse import urlparse
from datetime import datetime, date

from .models import (
    MeetingPlatform, MeetingSession, MeetingAgentConfig, MeetingAgentStatus,
    get_user_id_from_django_user, get_username_from_django_user,
    initialize_meeting_platforms, get_duration_minutes
)
from .services import MeetingAgentService, TranscriptionService, SummaryService

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def get_platforms(request):
    """Get all supported meeting platforms"""
    try:
        result = MeetingPlatform.get_all()
        
        if not result["success"]:
            return JsonResponse({
                'error': result["error"]
            }, status=500)
        
        # Transform for frontend
        platform_data = []
        for platform in result["platforms"]:
            platform_data.append({
                'id': platform['platform_id'],
                'name': platform['name'],
                'icon': platform['icon'],
                'supported': platform['supported'],
                'authRequired': platform['auth_required']
            })
        
        return JsonResponse({'platforms': platform_data})
    except Exception as e:
        logger.error(f"Failed to get platforms: {str(e)}")
        
        # Return default platforms if database is not available
        default_platforms = [
            {'id': 'zoom', 'name': 'Zoom', 'icon': '🎥', 'supported': True, 'authRequired': True},
            {'id': 'teams', 'name': 'Microsoft Teams', 'icon': '💼', 'supported': True, 'authRequired': True},
            {'id': 'meet', 'name': 'Google Meet', 'icon': '📞', 'supported': True, 'authRequired': True},
            {'id': 'webex', 'name': 'Cisco Webex', 'icon': '🎦', 'supported': False, 'authRequired': True}
        ]
        return JsonResponse({'platforms': default_platforms})


@csrf_exempt
@require_http_methods(["POST"])
def test_platform_auth(request, platform_id):
    """Test authentication for a specific platform"""
    try:
        result = MeetingPlatform.get_by_id(platform_id)
        if not result["success"]:
            return JsonResponse({
                'success': False,
                'message': 'Platform not found',
                'auth_status': 'invalid'
            }, status=404)
        
        platform = result["platform"]
        
        # This would typically test actual API credentials
        # For now, we'll simulate the test
        auth_status = 'valid'  # This would be determined by actual API call
        
        return JsonResponse({
            'success': True,
            'message': f'Authentication test for {platform["name"]} completed',
            'auth_status': auth_status
        })
    except Exception as e:
        logger.error(f"Auth test failed for platform {platform_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Authentication test failed: {str(e)}',
            'auth_status': 'invalid'
        }, status=400)


@require_http_methods(["GET"])
def get_meeting_sessions(request):
    """Get user's meeting sessions"""
    try:
        # Get username from token (following your pattern)
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        # Get query parameters from GET request
        status_filter = request.GET.get('status')
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        # Use username as user_id (following your pattern)
        result = MeetingSession.get_user_sessions(username, status_filter, limit, offset)
        
        if not result["success"]:
            return JsonResponse({
                'error': result["error"]
            }, status=500)
        
        # Transform sessions for frontend
        session_data = []
        for session in result["sessions"]:
            # Get platform data
            platform_result = MeetingPlatform.get_by_id(session.get('platform_id', ''))
            platform_data = None
            if platform_result["success"]:
                platform = platform_result["platform"]
                platform_data = {
                    'id': platform['platform_id'],
                    'name': platform['name'],
                    'icon': platform['icon'],
                    'supported': platform['supported'],
                    'authRequired': platform['auth_required']
                }
            
            session_data.append({
                'id': session['session_id'],
                'title': session.get('title', ''),
                'platform': platform_data,
                'meetingUrl': session.get('meeting_url', ''),
                'status': session.get('status', ''),
                'startTime': session.get('start_time'),
                'endTime': session.get('end_time'),
                'duration': session.get('duration'),
                'agentJoinTime': session.get('agent_join_time'),
                'recordingUrl': session.get('recording_url', ''),
                'transcriptionUrl': session.get('transcription_url', ''),
                'transcriptionText': session.get('transcription_text', ''),
                'metadata': session.get('metadata', {}),
                'participants': session.get('participants', []),
                'summary': session.get('summary'),
                'createdAt': session.get('created_at'),
                'updatedAt': session.get('updated_at')
            })
        
        return JsonResponse({
            'sessions': session_data,
            'total': result["total"],
            'hasMore': result["has_more"]
        })
    except Exception as e:
        logger.error(f"Failed to get meeting sessions: {str(e)}")
        return JsonResponse({
            'error': 'Failed to retrieve sessions'
        }, status=500)


@require_http_methods(["GET"])
def get_meeting_session(request, session_id):
    """Get a specific meeting session"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        result = MeetingSession.get_session(session_id, username)
        
        if not result["success"]:
            return JsonResponse({
                'error': result["error"]
            }, status=404)
        
        session = result["session"]
        
        # Transform session for frontend
        platform_result = MeetingPlatform.get_by_id(session.get('platform_id', ''))
        platform_data = None
        if platform_result["success"]:
            platform = platform_result["platform"]
            platform_data = {
                'id': platform['platform_id'],
                'name': platform['name'],
                'icon': platform['icon'],
                'supported': platform['supported'],
                'authRequired': platform['auth_required']
            }
        
        session_data = {
            'id': session['session_id'],
            'title': session.get('title', ''),
            'platform': platform_data,
            'meetingUrl': session.get('meeting_url', ''),
            'status': session.get('status', ''),
            'startTime': session.get('start_time'),
            'endTime': session.get('end_time'),
            'duration': session.get('duration'),
            'agentJoinTime': session.get('agent_join_time'),
            'recordingUrl': session.get('recording_url', ''),
            'transcriptionUrl': session.get('transcription_url', ''),
            'transcriptionText': session.get('transcription_text', ''),
            'metadata': session.get('metadata', {}),
            'participants': session.get('participants', []),
            'summary': session.get('summary'),
            'createdAt': session.get('created_at'),
            'updatedAt': session.get('updated_at')
        }
        
        return JsonResponse(session_data)
    except Exception as e:
        logger.error(f"Failed to get meeting session: {str(e)}")
        return JsonResponse({
            'error': 'Failed to retrieve session'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def join_meeting(request):
    """Join a meeting"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        # Parse JSON body
        data = json.loads(request.body)
        meeting_url = data.get('meetingUrl')
        platform_id = data.get('platform')
        title = data.get('title', '')
        settings = data.get('settings', {})
        scheduled_start_time = data.get('scheduledStartTime')
        
        if not meeting_url:
            return JsonResponse({
                'success': False,
                'message': 'Meeting URL is required'
            }, status=400)
        
        # Parse meeting URL to extract platform info
        meeting_info = parse_meeting_url(meeting_url)
        if not meeting_info['is_valid']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid meeting URL or unsupported platform'
            }, status=400)
        
        # Get platform
        platform_result = MeetingPlatform.get_by_id(meeting_info['platform'])
        if not platform_result["success"]:
            return JsonResponse({
                'success': False,
                'message': f'Platform {meeting_info["platform"]} not found'
            }, status=400)
        
        # Create meeting session
        session_data = {
            'user_id': username,  # Use username as user_id following your pattern
            'username': username,
            'title': title,
            'platform_id': meeting_info['platform'],
            'meeting_url': meeting_url,
            'start_time': datetime.fromisoformat(scheduled_start_time.replace('Z', '+00:00')) if scheduled_start_time else datetime.utcnow(),
            'metadata': settings,
            'status': 'joining'
        }
        
        result = MeetingSession.create_session(session_data)
        
        if not result["success"]:
            return JsonResponse({
                'success': False,
                'message': result["error"]
            }, status=500)
        
        session_id = result["session_id"]
        
        # Start the meeting agent service
        session_result = MeetingSession.get_session(session_id)
        if session_result["success"]:
            agent_service = MeetingAgentService()
            agent_result = agent_service.join_meeting(session_result["session"])
            
            if agent_result['success']:
                MeetingSession.update_session(session_id, {
                    'status': 'active',
                    'agent_join_time': datetime.utcnow()
                })
                
                return JsonResponse({
                    'success': True,
                    'sessionId': session_id,
                    'message': 'Successfully joined meeting'
                })
            else:
                MeetingSession.update_session(session_id, {'status': 'failed'})
                
                return JsonResponse({
                    'success': False,
                    'message': agent_result.get('message', 'Failed to join meeting')
                }, status=400)
        
        return JsonResponse({
            'success': False,
            'message': 'Failed to retrieve created session'
        }, status=500)
            
    except Exception as e:
        logger.error(f"Failed to join meeting: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to join meeting: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def leave_meeting(request, session_id):
    """Leave a meeting"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        result = MeetingSession.get_session(session_id, username)
        
        if not result["success"]:
            return JsonResponse({
                'success': False,
                'message': 'Session not found'
            }, status=404)
        
        session = result["session"]
        
        if session['status'] not in ['active', 'recording']:
            return JsonResponse({
                'success': False,
                'message': 'Meeting is not active'
            }, status=400)
        
        # Stop the meeting agent
        agent_service = MeetingAgentService()
        agent_result = agent_service.leave_meeting(session)
        
        if agent_result['success']:
            end_time = datetime.utcnow()
            duration = None
            if session.get('start_time'):
                start_time = session['start_time']
                if isinstance(start_time, str):
                    start_time = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                duration = int((end_time - start_time).total_seconds())
            
            update_data = {
                'status': 'completed',
                'end_time': end_time,
                'duration': duration
            }
            
            MeetingSession.update_session(session_id, update_data)
            
            # Start transcription processing if enabled
            if session.get('metadata', {}).get('transcription_enabled', False):
                MeetingSession.update_session(session_id, {'status': 'transcribing'})
                
                # Start async transcription
                transcription_service = TranscriptionService()
                transcription_service.start_transcription(session)
            
            return JsonResponse({
                'success': True,
                'message': 'Successfully left meeting'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': agent_result.get('message', 'Failed to leave meeting')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Failed to leave meeting: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to leave meeting: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_transcription(request, session_id):
    """Get transcription for a meeting session"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        result = MeetingSession.get_session(session_id, username)
        
        if not result["success"]:
            return JsonResponse({
                'error': result["error"]
            }, status=404)
        
        session = result["session"]
        segments = session.get('transcription_segments', [])
        full_text = '\n'.join([f"{seg.get('speaker_name', 'Unknown')}: {seg.get('text', '')}" for seg in segments])
        
        is_complete = session.get('status') == 'completed'
        processing_status = session.get('status', '')
        
        return JsonResponse({
            'segments': segments,
            'full_text': full_text,
            'is_complete': is_complete,
            'processing_status': processing_status
        })
    except Exception as e:
        logger.error(f"Failed to get transcription: {str(e)}")
        return JsonResponse({
            'error': 'Failed to retrieve transcription'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "POST"])
def meeting_summary(request, session_id):
    """Get or generate meeting summary"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        result = MeetingSession.get_session(session_id, username)
        
        if not result["success"]:
            return JsonResponse({
                'error': result["error"]
            }, status=404)
        
        session = result["session"]
        
        if request.method == 'GET':
            # Return existing summary
            summary = session.get('summary')
            if summary:
                return JsonResponse(summary)
            else:
                return JsonResponse({
                    'error': 'No summary available for this session'
                }, status=404)
        
        elif request.method == 'POST':
            # Generate new summary
            if session.get('status') != 'completed':
                return JsonResponse({
                    'success': False,
                    'message': 'Meeting must be completed before generating summary'
                }, status=400)
            
            summary_service = SummaryService()
            summary_service.generate_summary(session)
            
            return JsonResponse({
                'success': True,
                'message': 'Summary generated successfully'
            })
            
    except Exception as e:
        logger.error(f"Failed to handle summary request: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to handle summary request: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def download_recording(request, session_id):
    """Get recording download URL"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        result = MeetingSession.get_session(session_id, username)
        
        if not result["success"]:
            return JsonResponse({
                'success': False,
                'message': 'Session not found'
            }, status=404)
        
        session = result["session"]
        recording_url = session.get('recording_url')
        if not recording_url:
            return JsonResponse({
                'success': False,
                'message': 'No recording available for this session'
            }, status=404)
        
        # Generate signed download URL (this would typically be a presigned S3 URL)
        download_url = recording_url  # In production, generate presigned URL
        
        return JsonResponse({
            'success': True,
            'download_url': download_url,
            'message': 'Recording download URL generated'
        })
    except Exception as e:
        logger.error(f"Failed to get recording URL: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to get recording URL: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_meeting_session(request, session_id):
    """Delete a meeting session"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        result = MeetingSession.delete_session(session_id, username)
        
        return JsonResponse({
            'success': result["success"],
            'message': result["message"]
        }, status=200 if result["success"] else 404)
    except Exception as e:
        logger.error(f"Failed to delete session: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to delete session: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET", "PUT"])
def agent_config(request):
    """Get or update meeting agent configuration"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        if request.method == 'GET':
            # Get or create config
            result = MeetingAgentConfig.get_or_create_config(username, username)
            
            if not result["success"]:
                return JsonResponse({
                    'error': result["error"]
                }, status=500)
            
            config = result["config"]
            return JsonResponse({
                'name': config['name'],
                'default_settings': config['default_settings'],
                'webhook_url': config.get('webhook_url', ''),
                'notification_settings': config['notification_settings'],
                'created_at': config['created_at'],
                'updated_at': config['updated_at']
            })
        
        elif request.method == 'PUT':
            # Update config
            data = json.loads(request.body)
            update_data = {}
            
            if 'name' in data:
                update_data['name'] = data['name']
            if 'default_settings' in data:
                update_data['default_settings'] = data['default_settings']
            if 'webhook_url' in data:
                update_data['webhook_url'] = data['webhook_url']
            if 'notification_settings' in data:
                update_data['notification_settings'] = data['notification_settings']
            
            result = MeetingAgentConfig.update_config(username, update_data)
            
            return JsonResponse({
                'success': result["success"],
                'message': result["message"]
            })
    except Exception as e:
        logger.error(f"Failed to handle config request: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to handle config request: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def agent_status(request):
    """Get current agent status"""
    try:
        # Get or create status record
        result = MeetingAgentStatus.get_or_create_status()
        
        if not result["success"]:
            return JsonResponse({
                'error': result["error"]
            }, status=500)
        
        status_data = result["status"]
        
        # Update real-time stats
        active_result = MeetingSession.get_active_count()
        today_result = MeetingSession.get_today_count()
        
        update_data = {
            'active_connections': active_result["count"] if active_result["success"] else 0,
            'total_meetings_today': today_result["count"] if today_result["success"] else 0,
            'last_activity': datetime.utcnow()
        }
        
        MeetingAgentStatus.update_status(update_data)
        
        # Get updated status
        result = MeetingAgentStatus.get_or_create_status()
        status_data = result["status"]
        
        return JsonResponse({
            'isOnline': status_data['is_online'],
            'activeConnections': status_data['active_connections'],
            'totalMeetingsToday': status_data['total_meetings_today'],
            'totalRecordingTime': status_data['total_recording_time'],
            'lastActivity': status_data.get('last_activity'),
            'systemHealth': status_data['system_health'],
            'updatedAt': status_data['updated_at']
        })
    except Exception as e:
        logger.error(f"Failed to get agent status: {str(e)}")
        return JsonResponse({
            'error': 'Failed to retrieve agent status'
        }, status=500)


def parse_meeting_url(url):
    """Parse meeting URL to extract platform and meeting info"""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname.lower() if parsed.hostname else ''
        
        # Zoom URLs
        if 'zoom.us' in hostname:
            match = re.search(r'/j/(\d+)', parsed.path)
            return {
                'platform': 'zoom',
                'meeting_id': match.group(1) if match else None,
                'is_valid': bool(match)
            }
        
        # Microsoft Teams URLs
        if 'teams.microsoft.com' in hostname or 'teams.live.com' in hostname:
            return {
                'platform': 'teams',
                'meeting_id': parsed.path,
                'is_valid': True
            }
        
        # Google Meet URLs
        if 'meet.google.com' in hostname:
            match = re.search(r'/([a-z-]+)', parsed.path)
            return {
                'platform': 'meet',
                'meeting_id': match.group(1) if match else None,
                'is_valid': bool(match)
            }
        
        # Webex URLs
        if 'webex.com' in hostname:
            return {
                'platform': 'webex',
                'meeting_id': parsed.path.split('/')[-1],
                'is_valid': True
            }
        
        return {
            'platform': None,
            'meeting_id': None,
            'is_valid': False
        }
        
    except Exception as e:
        logger.error(f"Failed to parse meeting URL: {str(e)}")
        return {
            'platform': None,
            'meeting_id': None,
            'is_valid': False
        }


# Initialize platforms on module load
try:
    initialize_meeting_platforms()
except Exception as e:
    logger.error(f"Failed to initialize meeting platforms: {e}")