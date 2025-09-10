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
from .recall_service import create_recall_bot_sync, get_recall_bot_sync, stop_recall_bot_sync, create_async_transcript_sync, get_transcript_sync
import requests

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
            
            # Get Recall bot data if available
            recall_bot = None
            recall_bot_id = session.get('recall_bot_id')
            if recall_bot_id:
                recall_bot_result = get_recall_bot_sync(recall_bot_id)
                if recall_bot_result['success']:
                    bot_data = recall_bot_result['bot_data']
                    logger.info(f"Recall bot {recall_bot_id} full data: {json.dumps(bot_data, indent=2, default=str)}")
                    logger.info(f"Recall bot {recall_bot_id} summary: status_changes={bot_data.get('status_changes')}, video_url={bool(bot_data.get('video_url'))}, video_url_value={bot_data.get('video_url')}")
                    
                    # Get the current bot status
                    bot_status = 'unknown'
                    if bot_data.get('status_changes'):
                        bot_status = bot_data['status_changes'][-1].get('code', 'unknown')
                    
                    # Extract video URL and transcript URL from nested recordings structure
                    video_url = None
                    audio_url = None
                    transcript_url = None
                    
                    recordings = bot_data.get('recordings', [])
                    if recordings:
                        # Get the most recent recording
                        latest_recording = recordings[-1]
                        media_shortcuts = latest_recording.get('media_shortcuts', {})
                        
                        # Extract video URL
                        if 'video_mixed' in media_shortcuts and media_shortcuts['video_mixed']:
                            video_data = media_shortcuts['video_mixed'].get('data', {})
                            video_url = video_data.get('download_url')
                        
                        # Extract audio URL (if available)
                        if 'audio_mixed' in media_shortcuts and media_shortcuts['audio_mixed']:
                            audio_data = media_shortcuts['audio_mixed'].get('data', {})
                            audio_url = audio_data.get('download_url')
                        
                        # Extract transcript URL - this should now be available with the new config
                        if 'transcript' in media_shortcuts and media_shortcuts['transcript']:
                            transcript_data = media_shortcuts['transcript'].get('data', {})
                            transcript_url = transcript_data.get('download_url')
                            logger.info(f"Found transcript URL in media_shortcuts for bot {recall_bot_id}: {bool(transcript_url)}")
                    
                    # Determine recording status more accurately
                    recording_status = 'not_started'
                    if video_url:
                        recording_status = 'completed'
                    elif bot_status in ['done', 'leaving', 'left']:
                        # Bot has finished but video might still be processing
                        recording_status = 'processing'
                    elif bot_status in ['in_call_recording', 'recording']:
                        recording_status = 'recording'
                    elif bot_status in ['in_call_not_recording', 'in_call']:
                        recording_status = 'not_started'
                    elif bot_status in ['call_ended']:
                        recording_status = 'processing'
                    
                    logger.info(f"Recall bot {recall_bot_id} determined status: bot_status={bot_status}, recording_status={recording_status}")
                    logger.info(f"Recall bot {recall_bot_id} extracted URLs: video_url={bool(video_url)}, audio_url={bool(audio_url)}, transcript_url={bool(transcript_url)}")
                    
                    # Determine transcription status
                    transcription_status = 'not_started'
                    if transcript_url:
                        transcription_status = 'completed'
                        logger.info(f"Transcription completed for bot {recall_bot_id}")
                    elif bot_data.get('transcript_segments'):
                        transcription_status = 'completed'
                    elif recording_status == 'completed':
                        transcription_status = 'processing'
                    elif recording_status == 'recording':
                        transcription_status = 'processing'
                    
                    recall_bot = {
                        'id': bot_data.get('id'),
                        'status': bot_status,
                        'meetingUrl': bot_data.get('meeting_url'),
                        'recordingStatus': recording_status,
                        'transcriptionStatus': transcription_status,
                        'createdAt': bot_data.get('join_at'),  # Recall uses 'join_at' not 'created_at'
                        'joinedAt': bot_data.get('join_at'),
                        'leftAt': None,  # Need to extract from status_changes if available
                        'metadata': {
                            'bot_name': bot_data.get('bot_name'),
                            'recording_mode': bot_data.get('recording_config', {}).get('video_mixed_layout', 'speaker_view'),
                            'transcription_options': {
                                'provider': 'recall',
                                'language': 'en'
                            }
                        },
                        'videoUrl': video_url,
                        'audioUrl': audio_url,
                        'transcriptUrl': transcript_url,
                        'chatMessagesUrl': bot_data.get('chat_messages_url')
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
                'updatedAt': session.get('updated_at'),
                'recallBot': recall_bot
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
        
        # Get Recall bot data if available
        recall_bot = None
        recall_bot_id = session.get('recall_bot_id')
        if recall_bot_id:
            recall_bot_result = get_recall_bot_sync(recall_bot_id)
            if recall_bot_result['success']:
                bot_data = recall_bot_result['bot_data']
                recall_bot = {
                    'id': bot_data.get('id'),
                    'status': bot_data.get('status_changes', [])[-1].get('code', 'unknown') if bot_data.get('status_changes') else 'unknown',
                    'meetingUrl': bot_data.get('meeting_url'),
                    'recordingStatus': 'completed' if bot_data.get('video_url') else 'processing',
                    'transcriptionStatus': 'completed' if bot_data.get('transcript_segments') else 'processing',
                    'createdAt': bot_data.get('created_at'),
                    'joinedAt': bot_data.get('joined_at'),
                    'leftAt': bot_data.get('left_at'),
                    'metadata': {
                        'bot_name': bot_data.get('bot_name'),
                        'recording_mode': bot_data.get('recording_mode', 'speaker_view'),
                        'transcription_options': {
                            'provider': 'recall',
                            'language': 'en'
                        }
                    },
                    'videoUrl': bot_data.get('video_url'),
                    'audioUrl': bot_data.get('audio_url'),
                    'transcriptUrl': bot_data.get('transcript_url'),
                    'chatMessagesUrl': bot_data.get('chat_messages_url')
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
            'updatedAt': session.get('updated_at'),
            'recallBot': recall_bot
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
                    'recall_bot_id': agent_result.get('bot_id'),
                    'message': agent_result.get('message', 'Successfully joined meeting')
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
        segments = []
        full_text = ""
        
        # First, try to get transcription from async transcript data
        recall_transcript_url = session.get('recall_transcript_url')
        recall_transcript_data = session.get('recall_transcript_data')
        
        if recall_transcript_url:
            # Fetch the raw transcript JSON and return it directly to frontend
            transcript_download_url = recall_transcript_url
            try:
                logger.info(f"Fetching async transcript from URL: {transcript_download_url}")
                response = requests.get(transcript_download_url, timeout=10)
                if response.status_code == 200:
                    transcript_json = response.json()
                    
                    # Parse transcript and create segments with speaker attribution
                    segments = []
                    participants_from_transcript = []
                    full_text = ""
                    
                    if isinstance(transcript_json, list):
                        for utterance in transcript_json:
                            if utterance.get('participant') and utterance.get('words'):
                                participant = utterance['participant']
                                participant_name = participant.get('name', 'Unknown Speaker')
                                participant_id = participant.get('id', 100)
                                
                                # Track unique participants
                                if not any(p.get('name') == participant_name for p in participants_from_transcript):
                                    participants_from_transcript.append({
                                        'name': participant_name,
                                        'id': participant_id,
                                        'is_host': participant.get('is_host', False)
                                    })
                                
                                # Process words for this participant
                                words = utterance['words']
                                if words and len(words) > 0:
                                    # Join all words to form the complete utterance
                                    text = ' '.join([word.get('text', '') for word in words if word.get('text')])
                                    
                                    if text.strip():
                                        # Get start and end times from first and last words
                                        start_time = words[0].get('start_timestamp', {}).get('relative', 0)
                                        end_time = words[-1].get('end_timestamp', {}).get('relative', start_time + 1)
                                        
                                        # Create segment
                                        segment = {
                                            'id': f'seg_{int(start_time * 1000)}',
                                            'speakerId': str(participant_id),
                                            'speakerName': participant_name,
                                            'text': text.strip(),
                                            'startTime': start_time,
                                            'endTime': end_time,
                                            'confidence': 1.0
                                        }
                                        segments.append(segment)
                                        
                                        # Add to full text
                                        full_text += f"{participant_name}: {text.strip()}\n"
                    
                    # Sort segments by start time
                    segments.sort(key=lambda x: x['startTime'])
                    
                    # Return parsed segments and raw transcript
                    return JsonResponse({
                        'segments': segments,
                        'full_text': full_text,
                        'raw_transcript': transcript_json,
                        'is_complete': True,
                        'processing_status': 'completed',
                        'session_info': {
                            'title': session.get('title', 'Untitled Meeting'),
                            'start_time': session.get('start_time'),
                            'end_time': session.get('end_time'),
                            'duration': session.get('duration'),
                            'participants': participants_from_transcript if participants_from_transcript else session.get('participants', []),
                            'platform': session.get('platform_id', 'unknown')
                        }
                    })
                else:
                    logger.warning(f"Failed to fetch async transcript: HTTP {response.status_code}")
                    segments = []
                    full_text = ""
            except Exception as e:
                logger.error(f"Error fetching async transcript content: {str(e)}")
                segments = []
                full_text = ""
        
        # Fallback: try to get transcription from bot data if no async transcript
        elif session.get('recall_bot_id'):
            try:
                recall_bot_result = get_recall_bot_sync(session['recall_bot_id'])
                if recall_bot_result['success']:
                    bot_data = recall_bot_result['bot_data']
                    
                    # Check if there are recordings with transcripts
                    recordings = bot_data.get('recordings', [])
                    if recordings:
                        latest_recording = recordings[-1]
                        media_shortcuts = latest_recording.get('media_shortcuts', {})
                        
                        # Check for direct transcript in media_shortcuts
                        if 'transcript' in media_shortcuts and media_shortcuts['transcript']:
                            transcript_data = media_shortcuts['transcript'].get('data', {})
                            transcript_download_url = transcript_data.get('download_url')
                            
                            if transcript_download_url:
                                # Fetch the raw transcript JSON and return it directly to frontend
                                try:
                                    logger.info(f"Fetching transcript from URL: {transcript_download_url}")
                                    response = requests.get(transcript_download_url, timeout=10)
                                    
                                    if response.status_code == 200:
                                        transcript_json = response.json()
                                        
                                        # Parse transcript and create segments with speaker attribution
                                        segments = []
                                        participants_from_transcript = []
                                        full_text = ""
                                        
                                        if isinstance(transcript_json, list):
                                            for utterance in transcript_json:
                                                if utterance.get('participant') and utterance.get('words'):
                                                    participant = utterance['participant']
                                                    participant_name = participant.get('name', 'Unknown Speaker')
                                                    participant_id = participant.get('id', 100)
                                                    
                                                    # Track unique participants
                                                    if not any(p.get('name') == participant_name for p in participants_from_transcript):
                                                        participants_from_transcript.append({
                                                            'name': participant_name,
                                                            'id': participant_id,
                                                            'is_host': participant.get('is_host', False)
                                                        })
                                                    
                                                    # Process words for this participant
                                                    words = utterance['words']
                                                    if words and len(words) > 0:
                                                        # Join all words to form the complete utterance
                                                        text = ' '.join([word.get('text', '') for word in words if word.get('text')])
                                                        
                                                        if text.strip():
                                                            # Get start and end times from first and last words
                                                            start_time = words[0].get('start_timestamp', {}).get('relative', 0)
                                                            end_time = words[-1].get('end_timestamp', {}).get('relative', start_time + 1)
                                                            
                                                            # Create segment
                                                            segment = {
                                                                'id': f'seg_{int(start_time * 1000)}',
                                                                'speakerId': str(participant_id),
                                                                'speakerName': participant_name,
                                                                'text': text.strip(),
                                                                'startTime': start_time,
                                                                'endTime': end_time,
                                                                'confidence': 1.0
                                                            }
                                                            segments.append(segment)
                                                            
                                                            # Add to full text
                                                            full_text += f"{participant_name}: {text.strip()}\n"
                                        
                                        # Sort segments by start time
                                        segments.sort(key=lambda x: x['startTime'])
                                        
                                        # Return parsed segments and raw transcript
                                        return JsonResponse({
                                            'segments': segments,
                                            'full_text': full_text,
                                            'raw_transcript': transcript_json,
                                            'is_complete': True,
                                            'processing_status': 'completed',
                                            'session_info': {
                                                'title': session.get('title', 'Untitled Meeting'),
                                                'start_time': session.get('start_time'),
                                                'end_time': session.get('end_time'),
                                                'duration': session.get('duration'),
                                                'participants': participants_from_transcript if participants_from_transcript else session.get('participants', []),
                                                'platform': session.get('platform_id', 'unknown')
                                            }
                                        })
                                    else:
                                        logger.warning(f"Failed to fetch transcript: HTTP {response.status_code}")
                                        segments = []
                                        full_text = ""
                                        
                                except Exception as e:
                                    logger.error(f"Error fetching transcript content: {str(e)}")
                                    segments = []
                                    full_text = ""
                        
                        # No transcript found in media_shortcuts
                        else:
                            logger.info("No transcript found in media_shortcuts")
                
            except Exception as e:
                logger.warning(f"Failed to fetch Recall AI transcription for session {session_id}: {str(e)}")
        
        # Fall back to local transcription segments if no Recall AI transcript found
        if not segments and not full_text:
            segments = session.get('transcription_segments', [])
            if segments:
                full_text = '\n'.join([f"{seg.get('speaker_name', 'Unknown')}: {seg.get('text', '')}" for seg in segments])
            else:
                # Check for basic transcription text
                transcription_text = session.get('transcription_text', '')
                if transcription_text:
                    full_text = transcription_text
        
        # If still no transcription found
        if not segments and not full_text:
            return JsonResponse({
                'segments': [],
                'full_text': '',
                'is_complete': False,
                'processing_status': 'No transcription available',
                'message': 'No transcription data found for this meeting session'
            })
        
        is_complete = session.get('status') == 'completed'
        processing_status = session.get('status', '')
        
        return JsonResponse({
            'segments': segments,
            'full_text': full_text,
            'is_complete': is_complete,
            'processing_status': processing_status,
            'session_info': {
                'title': session.get('title', 'Untitled Meeting'),
                'start_time': session.get('start_time'),
                'end_time': session.get('end_time'),
                'duration': session.get('duration'),
                'participants': session.get('participants', []),
                'platform': session.get('platform_id', 'unknown')
            }
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


# Recall AI Bot Management Views

@csrf_exempt
@require_http_methods(["POST"])
def create_recall_bot(request):
    """Create a new Recall AI bot"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        data = json.loads(request.body)
        meeting_url = data.get('meeting_url')
        
        if not meeting_url:
            return JsonResponse({
                'success': False,
                'message': 'Meeting URL is required'
            }, status=400)
        
        # Extract metadata
        metadata = {
            'bot_name': data.get('bot_name', 'Meeting Recorder'),
            'recording_mode': data.get('recording_mode', 'speaker_view'),
            'user_id': username
        }
        
        result = create_recall_bot_sync(meeting_url, metadata)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'bot': result['bot_data'],
                'message': 'Bot created successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('message', 'Failed to create bot'),
                'error': result.get('error')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error creating Recall bot: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error creating bot: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def get_recall_bot(request, bot_id):
    """Get information about a specific Recall AI bot"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        result = get_recall_bot_sync(bot_id)
        
        if result['success']:
            bot_data = result['bot_data']
            
            # Transform bot data to match frontend expectations
            transformed_bot = {
                'id': bot_data.get('id'),
                'status': bot_data.get('status_changes', [])[-1].get('code', 'unknown') if bot_data.get('status_changes') else 'unknown',
                'meetingUrl': bot_data.get('meeting_url'),
                'recordingStatus': 'recording' if bot_data.get('status_changes', [])[-1].get('code') == 'recording' else 'not_started',
                'transcriptionStatus': 'processing' if bot_data.get('transcription') else 'not_started',
                'createdAt': bot_data.get('created_at'),
                'joinedAt': bot_data.get('joined_at'),
                'leftAt': bot_data.get('left_at'),
                'metadata': {
                    'bot_name': bot_data.get('bot_name'),
                    'recording_mode': bot_data.get('recording_mode', 'speaker_view'),
                },
                'videoUrl': bot_data.get('video_url'),
                'audioUrl': bot_data.get('audio_url'),
                'transcriptUrl': bot_data.get('transcript_url')
            }
            
            return JsonResponse(transformed_bot)
        else:
            return JsonResponse({
                'error': result.get('message', 'Failed to fetch bot')
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error getting Recall bot {bot_id}: {str(e)}")
        return JsonResponse({
            'error': f'Error fetching bot: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def stop_recall_bot(request, bot_id):
    """Stop a running Recall AI bot"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required'
            }, status=401)
        
        result = stop_recall_bot_sync(bot_id)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': 'Bot stopped successfully'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': result.get('message', 'Failed to stop bot')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Error stopping Recall bot {bot_id}: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Error stopping bot: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def recall_webhook(request):
    """Handle webhooks from Recall AI"""
    try:
        # Parse webhook payload
        webhook_data = json.loads(request.body)
        event_type = webhook_data.get('event')
        data = webhook_data.get('data', {})
        
        logger.info(f"Received Recall webhook: {event_type}")
        logger.info(f"Webhook data: {json.dumps(webhook_data, indent=2, default=str)}")
        
        if event_type == 'recording.done':
            # Handle recording completion - trigger async transcription
            recording_data = data.get('recording', {})
            recording_id = recording_data.get('id')
            bot_data = data.get('bot')
            
            if recording_id and bot_data:
                bot_id = bot_data.get('id')
                
                # Find the session associated with this bot
                # Note: We'll need to add this method to the MeetingSession model
                logger.info(f"Processing recording.done for bot {bot_id}, recording {recording_id}")
                
                # For now, we'll create the transcript directly
                # In production, you'd find the session and check settings
                transcript_result = create_async_transcript_sync(recording_id, 'en')
                
                if transcript_result.get('success'):
                    transcript_id = transcript_result.get('transcript_id')
                    logger.info(f"Async transcript {transcript_id} created for recording {recording_id}")
                else:
                    logger.error(f"Failed to create async transcript: {transcript_result.get('message')}")
            
        elif event_type == 'transcript.done':
            # Handle transcript completion
            transcript_data = data.get('transcript', {})
            transcript_id = transcript_data.get('id')
            
            if transcript_id:
                logger.info(f"Transcript {transcript_id} completed, fetching data...")
                
                # Fetch the transcript data
                transcript_result = get_transcript_sync(transcript_id)
                if transcript_result.get('success'):
                    transcript_full_data = transcript_result.get('transcript_data', {})
                    download_url = transcript_full_data.get('data', {}).get('download_url')
                    
                    logger.info(f"Transcript data fetched successfully: {download_url}")
                    
                    # TODO: Update the corresponding session with transcript data
                    # For now, just log the success
                else:
                    logger.error(f"Failed to fetch transcript data: {transcript_result.get('message')}")
                    
        elif event_type == 'transcript.failed':
            # Handle transcript failure
            transcript_data = data.get('transcript', {})
            transcript_id = transcript_data.get('id')
            
            logger.error(f"Transcript {transcript_id} failed")
        
        # Return success response to Recall AI
        return JsonResponse({
            'success': True,
            'message': 'Webhook processed successfully'
        })
        
    except Exception as e:
        logger.error(f"Error processing Recall webhook: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Webhook processing failed: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
def debug_create_transcript(request, recording_id):
    """Debug endpoint to manually create transcript for a recording"""
    try:
        language = request.GET.get('language', 'en')
        
        logger.info(f"DEBUG: Manually creating transcript for recording {recording_id}")
        
        result = create_async_transcript_sync(recording_id, language)
        
        return JsonResponse({
            'success': result.get('success', False),
            'transcript_id': result.get('transcript_id'),
            'message': result.get('message'),
            'error': result.get('error'),
            'details': result.get('details')
        })
        
    except Exception as e:
        logger.error(f"DEBUG: Error creating transcript: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def debug_get_transcript(request, transcript_id):
    """Debug endpoint to get transcript data"""
    try:
        logger.info(f"DEBUG: Getting transcript data for {transcript_id}")
        
        result = get_transcript_sync(transcript_id)
        
        return JsonResponse({
            'success': result.get('success', False),
            'transcript_data': result.get('transcript_data'),
            'message': result.get('message'),
            'error': result.get('error')
        })
        
    except Exception as e:
        logger.error(f"DEBUG: Error getting transcript: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def debug_bot_recordings(request, bot_id):
    """Debug endpoint to get bot recordings and check if they're ready for transcription"""
    try:
        logger.info(f"DEBUG: Getting recordings for bot {bot_id}")
        
        # Get bot data including recordings
        bot_result = get_recall_bot_sync(bot_id)
        
        if not bot_result.get('success'):
            return JsonResponse({
                'success': False,
                'error': 'Failed to get bot data',
                'details': bot_result.get('message')
            })
        
        bot_data = bot_result.get('bot_data', {})
        recordings = bot_data.get('recordings', [])
        
        recording_info = []
        for recording in recordings:
            recording_id = recording.get('id')
            status = recording.get('status', {})
            
            recording_info.append({
                'id': recording_id,
                'status': status,
                'completed_at': recording.get('completed_at'),
                'created_at': recording.get('created_at'),
                'has_video': bool(recording.get('media_shortcuts', {}).get('video_mixed')),
                'has_audio': bool(recording.get('media_shortcuts', {}).get('audio_mixed')),
                'ready_for_transcription': status.get('code') == 'done'
            })
        
        return JsonResponse({
            'success': True,
            'bot_id': bot_id,
            'bot_status': bot_data.get('status_changes', [])[-1] if bot_data.get('status_changes') else {},
            'recordings': recording_info,
            'total_recordings': len(recordings)
        })
        
    except Exception as e:
        logger.error(f"DEBUG: Error getting bot recordings: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Initialize platforms on module load
try:
    initialize_meeting_platforms()
except Exception as e:
    logger.error(f"Failed to initialize meeting platforms: {e}")