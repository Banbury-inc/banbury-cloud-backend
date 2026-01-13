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
from .s3_upload_service import trigger_s3_upload_for_completed_meeting, MeetingS3UploadService
from .desktop_recording_service import create_upload_token_sync, get_sdk_upload_sync, handle_sdk_webhook_sync
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
            participants_from_bot = []
            recall_bot_id = session.get('recall_bot_id')
            if recall_bot_id:
                recall_bot_result = get_recall_bot_sync(recall_bot_id)
                if recall_bot_result['success']:
                    bot_data = recall_bot_result['bot_data']
                    
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
                    
                    
                    # Try to extract from transcript_segments first
                    if bot_data.get('transcript_segments'):
                        logger.info(f"Recall bot {recall_bot_id} has transcript_segments: {len(bot_data['transcript_segments'])}")
                        seen_participants = set()
                        for segment in bot_data['transcript_segments']:
                            if segment.get('participant'):
                                participant = segment['participant']
                                participant_name = participant.get('name', 'Unknown Speaker')
                                participant_id = participant.get('id', 100)
                                
                                # Create unique key to avoid duplicates
                                participant_key = f"{participant_id}_{participant_name}"
                                if participant_key not in seen_participants:
                                    seen_participants.add(participant_key)
                                    participants_from_bot.append({
                                        'id': str(participant_id),
                                        'name': participant_name,
                                        'email': participant.get('email', ''),
                                        'role': 'host' if participant.get('is_host', False) else 'participant',
                                        'joinTime': segment.get('start_time', 0),
                                        'leaveTime': segment.get('end_time'),
                                        'duration': segment.get('end_time', 0) - segment.get('start_time', 0) if segment.get('end_time') else None
                                    })
                    
                    # Also check if there are participants in the meeting metadata
                    meeting_metadata = bot_data.get('meeting_metadata', {})
                    logger.info(f"Recall bot {recall_bot_id} meeting_metadata: {meeting_metadata}")
                    if meeting_metadata.get('participants'):
                        logger.info(f"Recall bot {recall_bot_id} has participants in metadata: {len(meeting_metadata['participants'])}")
                        for participant in meeting_metadata['participants']:
                            participant_name = participant.get('name', 'Unknown Speaker')
                            participant_id = participant.get('id', 100)
                            
                            # Check if we already have this participant
                            if not any(p['id'] == str(participant_id) for p in participants_from_bot):
                                participants_from_bot.append({
                                    'id': str(participant_id),
                                    'name': participant_name,
                                    'email': participant.get('email', ''),
                                    'role': 'host' if participant.get('is_host', False) else 'participant',
                                    'joinTime': participant.get('join_time', 0),
                                    'leaveTime': participant.get('leave_time'),
                                    'duration': participant.get('duration')
                                })
                    
                    # If we have a transcript URL but no participants yet, try to fetch and parse the transcript
                    if not participants_from_bot and transcript_url:
                        logger.info(f"Recall bot {recall_bot_id} attempting to fetch transcript from URL for participants")
                        try:
                            import requests
                            response = requests.get(transcript_url, timeout=10)
                            if response.status_code == 200:
                                transcript_data = response.json()
                                logger.info(f"Recall bot {recall_bot_id} transcript data type: {type(transcript_data)}")
                                
                                # Parse transcript data to extract participants
                                if isinstance(transcript_data, list):
                                    seen_participants = set()
                                    for utterance in transcript_data:
                                        if utterance.get('participant') and utterance.get('words'):
                                            participant = utterance['participant']
                                            participant_name = participant.get('name', 'Unknown Speaker')
                                            participant_id = participant.get('id', 100)
                                            
                                            # Create unique key to avoid duplicates
                                            participant_key = f"{participant_id}_{participant_name}"
                                            if participant_key not in seen_participants:
                                                seen_participants.add(participant_key)
                                                participants_from_bot.append({
                                                    'id': str(participant_id),
                                                    'name': participant_name,
                                                    'email': participant.get('email', ''),
                                                    'role': 'host' if participant.get('is_host', False) else 'participant',
                                                    'joinTime': utterance.get('start_time', 0),
                                                    'leaveTime': utterance.get('end_time'),
                                                    'duration': utterance.get('end_time', 0) - utterance.get('start_time', 0) if utterance.get('end_time') else None
                                                })
                                    logger.info(f"Recall bot {recall_bot_id} extracted {len(participants_from_bot)} participants from transcript URL")
                        except Exception as e:
                            logger.error(f"Recall bot {recall_bot_id} failed to fetch transcript for participants: {str(e)}")
                    
                    logger.info(f"Recall bot {recall_bot_id} final participants: {len(participants_from_bot)}")
                    
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

            # Use participants from bot data if available, otherwise use session participants
            session_participants = participants_from_bot if participants_from_bot else session.get('participants', [])
            
            # TEMPORARY: Add mock participants for testing if no participants found
            if not session_participants and recall_bot:
                logger.info(f"Session {session['session_id']} adding mock participants for testing")
                session_participants = [
                    {
                        'id': 'mock_1',
                        'name': 'Meeting Host',
                        'email': 'host@example.com',
                        'role': 'host',
                        'joinTime': session.get('start_time', 0),
                        'leaveTime': session.get('end_time'),
                        'duration': session.get('duration', 0)
                    },
                    {
                        'id': 'mock_2', 
                        'name': 'Participant 1',
                        'email': 'participant1@example.com',
                        'role': 'participant',
                        'joinTime': session.get('start_time', 0),
                        'leaveTime': session.get('end_time'),
                        'duration': session.get('duration', 0)
                    }
                ]
            
            logger.info(f"Session {session['session_id']} participants: {len(session_participants)} from bot, {len(session.get('participants', []))} from session")
            
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
                'participants': session_participants,
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
        logger.info(f"Session: {session}")
        
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
            logger.info(f"Recall bot result: {recall_bot_result}")
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
        
        # Get bot settings (profile picture and bot name) from user config
        logger.info(f"🔍 Fetching bot settings for user: {username}")
        config_result = MeetingAgentConfig.get_or_create_config(username, username)
        bot_name = 'Meeting Recorder'
        profile_picture_url = ''
        if config_result["success"]:
            config = config_result["config"]
            bot_name = config.get('bot_name', 'Meeting Recorder')
            profile_picture_url = config.get('profile_picture_url', '')
            
            logger.info(f"📋 Bot config retrieved - bot_name: {bot_name}, has profile_picture: {bool(profile_picture_url)}")
            
            # Profile pictures are uploaded with public-read ACL
            # No need to generate pre-signed URL - use raw URL directly
            if profile_picture_url:
                logger.info(f"✅ Using public profile picture URL for Recall AI bot: {profile_picture_url}")
            else:
                logger.info(f"ℹ️ No profile picture URL found in config for user: {username}")
        else:
            logger.error(f"❌ Failed to fetch bot config: {config_result.get('error', 'Unknown error')}")
        
        # Merge bot settings into metadata
        merged_settings = {**settings}
        merged_settings['botName'] = bot_name
        if profile_picture_url:
            merged_settings['profilePictureUrl'] = profile_picture_url
            logger.info(f"🔗 Profile picture URL added to session metadata")
        else:
            logger.info(f"⚠️ No profile picture URL to add to session metadata")
        
        # Create meeting session
        session_data = {
            'user_id': username,  # Use username as user_id following your pattern
            'username': username,
            'title': title,
            'platform_id': meeting_info['platform'],
            'meeting_url': meeting_url,
            'start_time': datetime.fromisoformat(scheduled_start_time.replace('Z', '+00:00')) if scheduled_start_time else datetime.utcnow(),
            'metadata': merged_settings,
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
            
            # Trigger S3 upload for completed meeting
            try:
                s3_result = trigger_s3_upload_for_completed_meeting(session_id)
                if s3_result['success']:
                    logger.info(f"S3 upload triggered successfully for session {session_id}")
                else:
                    logger.warning(f"S3 upload failed for session {session_id}: {s3_result.get('error', 'Unknown error')}")
            except Exception as e:
                logger.error(f"Error triggering S3 upload for session {session_id}: {str(e)}")
            
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
@require_http_methods(["POST"])
def trigger_s3_upload(request, session_id):
    """Manually trigger S3 upload for a completed meeting session"""
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
        
        if session['status'] != 'completed':
            return JsonResponse({
                'success': False,
                'message': 'Meeting must be completed before triggering S3 upload'
            }, status=400)
        
        # Trigger S3 upload for completed meeting
        try:
            logger.info(f"Manually triggering S3 upload for session {session_id}")
            s3_result = trigger_s3_upload_for_completed_meeting(session_id)
            if s3_result['success']:
                logger.info(f"S3 upload triggered successfully for session {session_id}")
                return JsonResponse({
                    'success': True,
                    'message': 'S3 upload triggered successfully',
                    'video_url': s3_result.get('video_upload', {}).get('s3_url') if s3_result.get('video_upload', {}).get('success') else None,
                    'transcript_url': s3_result.get('transcript_upload', {}).get('s3_url') if s3_result.get('transcript_upload', {}).get('success') else None
                })
            else:
                logger.warning(f"S3 upload failed for session {session_id}: {s3_result.get('error', 'Unknown error')}")
                return JsonResponse({
                    'success': False,
                    'message': f"S3 upload failed: {s3_result.get('error', 'Unknown error')}"
                }, status=500)
        except Exception as e:
            logger.error(f"Error triggering S3 upload for session {session_id}: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': f'Error triggering S3 upload: {str(e)}'
            }, status=500)
            
    except Exception as e:
        logger.error(f"Failed to trigger S3 upload: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to trigger S3 upload: {str(e)}'
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


@csrf_exempt
@require_http_methods(["GET", "POST"])
def bot_settings(request):
    """Get or update bot settings (profile picture and bot name)"""
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'error': 'Authentication required'
            }, status=401)
        
        if request.method == 'GET':
            # Get bot settings from config
            result = MeetingAgentConfig.get_or_create_config(username, username)
            
            if not result["success"]:
                return JsonResponse({
                    'error': result["error"]
                }, status=500)
            
            config = result["config"]
            profile_picture_url = config.get('profile_picture_url', '')
            
            # Profile pictures are uploaded with public-read ACL, so no pre-signed URL needed
            # Just return the raw URL which is publicly accessible
            return JsonResponse({
                'profilePictureUrl': profile_picture_url,
                'botName': config.get('bot_name', 'Meeting Recorder')
            })
        
        elif request.method == 'POST':
            # Update bot settings
            data = json.loads(request.body)
            logger.info(f"💾 Updating bot settings for user: {username}")
            logger.info(f"📝 Request data: profilePictureUrl={data.get('profilePictureUrl', 'not provided')[:100]}, botName={data.get('botName', 'not provided')}")
            
            update_data = {}
            
            if 'profilePictureUrl' in data:
                update_data['profile_picture_url'] = data['profilePictureUrl']
                logger.info(f"🖼️ Updating profile_picture_url to: {data['profilePictureUrl'][:100]}")
            if 'botName' in data:
                update_data['bot_name'] = data['botName']
                logger.info(f"📛 Updating bot_name to: {data['botName']}")
            
            if not update_data:
                logger.warning(f"⚠️ No settings provided to update for user: {username}")
                return JsonResponse({
                    'success': False,
                    'message': 'No settings provided to update'
                }, status=400)
            
            result = MeetingAgentConfig.update_config(username, update_data)
            
            if result["success"]:
                logger.info(f"✅ Bot settings updated successfully for user: {username}")
            else:
                logger.error(f"❌ Failed to update bot settings for user {username}: {result.get('error', 'Unknown error')}")
            
            return JsonResponse({
                'success': result["success"],
                'message': result.get("message", "Bot settings updated successfully")
            })
    except Exception as e:
        logger.error(f"Failed to handle bot settings request: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Failed to handle bot settings request: {str(e)}'
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
            # Handle recording completion - trigger async transcription and S3 upload
            recording_data = data.get('recording', {})
            recording_id = recording_data.get('id')
            bot_data = data.get('bot')
            
            if recording_id and bot_data:
                bot_id = bot_data.get('id')
                
                logger.info(f"Processing recording.done for bot {bot_id}, recording {recording_id}")
                
                # Find the session associated with this bot
                try:
                    # Get all sessions and find the one with this bot_id
                    sessions_result = MeetingSession.get_all_sessions()
                    if sessions_result.get('success'):
                        sessions = sessions_result.get('sessions', [])
                        matching_session = None
                        for session in sessions:
                            if session.get('recall_bot_id') == bot_id:
                                matching_session = session
                                break
                        
                        if matching_session:
                            session_id = matching_session['session_id']
                            logger.info(f"Found matching session {session_id} for bot {bot_id}")
                            
                            # Extract URLs from bot data (same logic as in get_meeting_sessions)
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
                                
                                # Extract transcript URL
                                if 'transcript' in media_shortcuts and media_shortcuts['transcript']:
                                    transcript_data = media_shortcuts['transcript'].get('data', {})
                                    transcript_url = transcript_data.get('download_url')
                                
                                logger.info(f"Extracted URLs for session {session_id}: video={bool(video_url)}, audio={bool(audio_url)}, transcript={bool(transcript_url)}")
                                
                                # Update session with recording URLs from bot data
                                update_data = {
                                    'status': 'completed',
                                    'recall_bot': {
                                        'video_url': video_url,
                                        'transcript_url': transcript_url,
                                        'audio_url': audio_url
                                    },
                                    # Also store URLs at the top level for easier access
                                    'recording_url': video_url,
                                    'transcription_url': transcript_url,
                                    'audio_url': audio_url
                                }
                                
                                MeetingSession.update_session(session_id, update_data)
                                logger.info(f"Updated session {session_id} with recording URLs")
                                
                                # Only trigger S3 upload if we have at least one URL
                                if video_url or transcript_url or audio_url:
                                    try:
                                        s3_result = trigger_s3_upload_for_completed_meeting(session_id)
                                        if s3_result['success']:
                                            logger.info(f"S3 upload triggered successfully for session {session_id} via webhook")
                                        else:
                                            logger.warning(f"S3 upload failed for session {session_id} via webhook: {s3_result.get('error', 'Unknown error')}")
                                    except Exception as e:
                                        logger.error(f"Error triggering S3 upload for session {session_id} via webhook: {str(e)}")
                                else:
                                    logger.info(f"No URLs available yet for session {session_id}, skipping S3 upload")
                            else:
                                logger.info(f"No recordings available yet for session {session_id}, skipping S3 upload")
                        else:
                            logger.warning(f"No matching session found for bot {bot_id}")
                    else:
                        logger.error(f"Failed to get sessions for bot {bot_id}: {sessions_result.get('error')}")
                        
                except Exception as e:
                    logger.error(f"Error processing recording.done webhook for bot {bot_id}: {str(e)}")
                
                # Create transcript
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
                    
                    # Find the session associated with this transcript and update it
                    try:
                        sessions_result = MeetingSession.get_all_sessions()
                        if sessions_result.get('success'):
                            sessions = sessions_result.get('sessions', [])
                            # Find session by transcript_id or by looking for sessions that need transcript updates
                            for session in sessions:
                                if session.get('status') == 'completed' and session.get('recall_bot_id'):
                                    session_id = session['session_id']
                                    
                                    # Update session with transcript URL
                                    update_data = {
                                        'recall_bot': {
                                            **session.get('recall_bot', {}),
                                            'transcript_url': download_url
                                        },
                                        # Also store at top level
                                        'transcription_url': download_url
                                    }
                                    
                                    MeetingSession.update_session(session_id, update_data)
                                    logger.info(f"Updated session {session_id} with transcript URL")
                                    
                                    # Trigger S3 upload now that we have transcript
                                    try:
                                        s3_result = trigger_s3_upload_for_completed_meeting(session_id)
                                        if s3_result['success']:
                                            logger.info(f"S3 upload triggered successfully for session {session_id} via transcript.done webhook")
                                        else:
                                            logger.warning(f"S3 upload failed for session {session_id} via transcript.done webhook: {s3_result.get('error', 'Unknown error')}")
                                    except Exception as e:
                                        logger.error(f"Error triggering S3 upload for session {session_id} via transcript.done webhook: {str(e)}")
                                    break
                    except Exception as e:
                        logger.error(f"Error processing transcript.done webhook: {str(e)}")
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


@csrf_exempt
@require_http_methods(["POST"])
def update_session_urls_from_bot(request, session_id):
    """Manually update session URLs from Recall AI bot data"""
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
        recall_bot_id = session.get('recall_bot_id')
        
        if not recall_bot_id:
            return JsonResponse({
                'success': False,
                'message': 'No Recall bot associated with this session'
            }, status=400)
        
        # Get bot data from Recall AI
        bot_result = get_recall_bot_sync(recall_bot_id)
        if not bot_result['success']:
            return JsonResponse({
                'success': False,
                'message': 'Failed to fetch bot data from Recall AI'
            }, status=400)
        
        bot_data = bot_result['bot_data']
        
        # Extract URLs from bot data (same logic as in get_meeting_sessions)
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
            
            # Extract transcript URL
            if 'transcript' in media_shortcuts and media_shortcuts['transcript']:
                transcript_data = media_shortcuts['transcript'].get('data', {})
                transcript_url = transcript_data.get('download_url')
        
        # Update session with URLs
        update_data = {
            'recall_bot': {
                'video_url': video_url,
                'transcript_url': transcript_url,
                'audio_url': audio_url
            },
            # Also store at top level for easier access
            'recording_url': video_url,
            'transcription_url': transcript_url,
            'audio_url': audio_url
        }
        
        MeetingSession.update_session(session_id, update_data)
        
        return JsonResponse({
            'success': True,
            'message': 'Session URLs updated successfully',
            'video_url': video_url,
            'transcript_url': transcript_url,
            'audio_url': audio_url
        })
        
    except Exception as e:
        logger.error(f"Error updating session URLs: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_and_upload_sessions(request):
    """Check for sessions that need S3 upload and upload them"""
    try:
        # Get sessions that need S3 upload
        sessions_result = MeetingSession.get_sessions_needing_s3_upload(limit=20)
        
        if not sessions_result['success']:
            return JsonResponse({
                "success": False,
                "error": f"Failed to get sessions: {sessions_result['error']}"
            }, status=500)
        
        sessions = sessions_result['sessions']
        logger.info(f"Found {len(sessions)} sessions needing S3 upload")
        
        if not sessions:
            return JsonResponse({
                "success": True,
                "message": "No sessions need S3 upload",
                "uploaded_count": 0,
                "failed_count": 0
            })
        
        # Initialize S3 upload service
        s3_service = MeetingS3UploadService()
        
        uploaded_count = 0
        failed_count = 0
        results = []
        
        for session in sessions:
            session_id = session['session_id']
            user_id = session.get('user_id', 'unknown')
            
            try:
                logger.info(f"Processing S3 upload for session {session_id}")
                
                # Mark that we're attempting upload
                MeetingSession.mark_s3_upload_attempted(session_id)
                
                # Trigger S3 upload
                upload_result = s3_service.upload_meeting_assets(session_id)
                
                if upload_result['success']:
                    uploaded_count += 1
                    logger.info(f"S3 upload successful for session {session_id}")
                    
                    # Update session with upload status
                    video_uploaded = upload_result.get('video_upload', {}).get('success', False)
                    transcript_uploaded = upload_result.get('transcript_upload', {}).get('success', False)
                    
                    MeetingSession.update_s3_upload_status(session_id, {
                        "video_uploaded": video_uploaded,
                        "transcript_uploaded": transcript_uploaded,
                        "audio_uploaded": False,  # Not implemented in current service
                        "upload_attempted": True,
                        "last_upload_attempt": datetime.utcnow(),
                        "upload_errors": []
                    })
                else:
                    failed_count += 1
                    error_msg = upload_result.get('error', 'Unknown error')
                    logger.error(f"S3 upload failed for session {session_id}: {error_msg}")
                    
                    # Mark upload attempt with error
                    MeetingSession.mark_s3_upload_attempted(session_id, error_msg)
                
                results.append({
                    "session_id": session_id,
                    "success": upload_result['success'],
                    "message": upload_result.get('message', ''),
                    "error": upload_result.get('error', '') if not upload_result['success'] else None
                })
                
            except Exception as e:
                failed_count += 1
                error_msg = f"Exception during S3 upload: {str(e)}"
                logger.error(f"Exception for session {session_id}: {error_msg}")
                
                # Mark upload attempt with error
                MeetingSession.mark_s3_upload_attempted(session_id, error_msg)
                
                results.append({
                    "session_id": session_id,
                    "success": False,
                    "message": "",
                    "error": error_msg
                })
        
        return JsonResponse({
            "success": True,
            "message": f"Processed {len(sessions)} sessions",
            "uploaded_count": uploaded_count,
            "failed_count": failed_count,
            "results": results
        })
        
    except Exception as e:
        logger.error(f"Error in check_and_upload_sessions: {str(e)}")
        return JsonResponse({
            "success": False,
            "error": str(e)
        }, status=500)


# ============================================================================
# Desktop Recording SDK Endpoints
# ============================================================================

@csrf_exempt
@require_http_methods(["POST"])
def create_desktop_upload_token(request):
    """
    Create an upload token for desktop recording
    
    This endpoint is called by the Electron desktop app before starting
    a desktop recording to get a token for uploading the recording.
    """
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        # Parse request body for optional metadata
        try:
            body = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            body = {}
        
        # Build metadata for the upload
        metadata = {
            'user_id': username,
            'username': username,
            'platform': body.get('platform', 'desktop'),
            'meeting_title': body.get('meeting_title', 'Desktop Recording'),
            'transcription_enabled': body.get('transcription_enabled', True),
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Add any additional metadata from request
        if body.get('metadata'):
            metadata.update(body.get('metadata'))
        
        logger.info(f"Creating desktop upload token for user: {username}")
        
        # Create the upload token
        result = create_upload_token_sync(metadata)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'upload_token': result['upload_token'],
                'token_id': result['token_id'],
                'expires_at': result.get('expires_at'),
                'message': 'Upload token created successfully'
            })
        else:
            logger.error(f"Failed to create upload token: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to create upload token'),
                'message': result.get('message', 'Unknown error')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error creating desktop upload token: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'message': 'Failed to create upload token'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def desktop_recording_webhook(request):
    """
    Handle webhook events from the Desktop Recording SDK
    
    This endpoint receives events like:
    - sdk_upload.complete: Recording upload completed
    - sdk_upload.failed: Recording upload failed
    - transcript.complete: Transcription completed
    """
    try:
        # Parse webhook payload
        try:
            payload = json.loads(request.body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in desktop webhook payload")
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON payload'
            }, status=400)
        
        # Get event type from payload
        event_type = payload.get('event')
        if not event_type:
            logger.error("Missing event type in desktop webhook payload")
            return JsonResponse({
                'success': False,
                'error': 'Missing event type'
            }, status=400)
        
        logger.info(f"Received desktop recording webhook: {event_type}")
        
        # Process the webhook
        result = handle_sdk_webhook_sync(event_type, payload)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'message': result.get('message', 'Webhook processed')
            })
        else:
            logger.error(f"Webhook processing failed: {result.get('error')}")
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Webhook processing failed')
            }, status=500)
            
    except Exception as e:
        logger.error(f"Error processing desktop webhook: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@require_http_methods(["GET"])
def get_desktop_upload(request, upload_id):
    """
    Get information about a desktop SDK upload
    """
    try:
        username = getattr(request, 'username_from_token', None)
        if not username:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        
        logger.info(f"Getting desktop upload {upload_id} for user: {username}")
        
        result = get_sdk_upload_sync(upload_id)
        
        if result['success']:
            return JsonResponse({
                'success': True,
                'upload': result['upload_data']
            })
        else:
            return JsonResponse({
                'success': False,
                'error': result.get('error', 'Failed to get upload')
            }, status=404)
            
    except Exception as e:
        logger.error(f"Error getting desktop upload: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


# Initialize platforms on module load
try:
    initialize_meeting_platforms()
except Exception as e:
    logger.error(f"Failed to initialize meeting platforms: {e}")