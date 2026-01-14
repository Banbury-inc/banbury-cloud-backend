"""
Desktop Recording Service using Recall AI Bot API

This service handles:
- Creating bots for desktop/meeting recordings
- Managing bot lifecycle and recording sessions
- Processing webhooks from Recall AI
"""

import os
import logging
import asyncio
import json
from typing import Dict, Any, Optional
from .recall_service import RecallAIService

logger = logging.getLogger(__name__)


class DesktopRecordingService:
    """Service for managing Recall AI Bot-based desktop recordings"""
    
    def __init__(self):
        self.api_key = os.environ.get('RECALL_API_KEY')
        
        if not self.api_key:
            logger.error("RECALL_API_KEY environment variable is not set!")
            raise ValueError("RECALL_API_KEY is required for Desktop Recording integration")
        
        # Use the existing RecallAIService for bot operations
        self.recall_service = RecallAIService()
    
    async def create_bot_for_meeting(self, meeting_url: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a Recall AI bot to join and record a meeting
        
        Args:
            meeting_url: The meeting URL to join (Zoom, Google Meet, Teams, etc.)
            metadata: Optional metadata to associate with the bot/recording
            
        Returns:
            dict: Contains bot_id and bot details on success
        """
        try:
            if not metadata:
                metadata = {}
            
            # Extract configuration from metadata
            bot_name = metadata.get('bot_name', metadata.get('meeting_title', 'Meeting Recorder'))
            recording_mode = metadata.get('recording_mode', 'speaker_view')
            transcription_enabled = metadata.get('transcription_enabled', True)
            profile_picture_url = metadata.get('profile_picture_url', '')
            
            logger.info(f"Creating Recall AI bot for meeting: {meeting_url}")
            logger.info(f"Bot config: name={bot_name}, mode={recording_mode}, transcription={transcription_enabled}")
            
            # Create bot using RecallAIService
            bot_metadata = {
                'bot_name': bot_name,
                'recording_mode': recording_mode,
                'transcription_enabled': transcription_enabled,
                'profile_picture_url': profile_picture_url,
                'user_id': metadata.get('user_id', 'unknown'),
                'username': metadata.get('username', 'unknown'),
                'platform': metadata.get('platform', 'desktop')
            }
            
            result = await self.recall_service.create_bot(meeting_url, bot_metadata)
            
            if result['success']:
                bot_id = result['bot_id']
                logger.info(f"Successfully created bot: {bot_id}")
                return {
                    'success': True,
                    'bot_id': bot_id,
                    'bot_data': result.get('bot_data', {}),
                    'message': 'Bot created successfully'
                }
            else:
                logger.error(f"Failed to create bot: {result.get('message')}")
                return {
                    'success': False,
                    'error': result.get('error', 'Failed to create bot'),
                    'message': result.get('message', 'Failed to create bot'),
                    'details': result.get('details')
                }
                    
        except Exception as e:
            logger.error(f"Error creating bot: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create bot due to unexpected error'
            }
    
    async def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """
        Get information about a bot
        
        Args:
            bot_id: The Recall AI bot ID
            
        Returns:
            dict: Bot information from Recall AI
        """
        try:
            result = await self.recall_service.get_bot(bot_id)
            return result
                    
        except Exception as e:
            logger.error(f"Error fetching bot {bot_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to fetch bot information'
            }
    
    async def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """
        Stop a bot and end the recording
        
        Args:
            bot_id: The Recall AI bot ID
            
        Returns:
            dict: Bot stop response
        """
        try:
            logger.info(f"Stopping bot: {bot_id}")
            result = await self.recall_service.stop_bot(bot_id)
            return result
                    
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to stop bot'
            }
    
    def handle_bot_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook events from Recall AI bots
        
        Args:
            event_type: The type of webhook event
            payload: The webhook payload
            
        Returns:
            dict: Processing result
        """
        try:
            logger.info(f"Processing bot webhook event: {event_type}")
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            if event_type == 'bot.status_change':
                return self._handle_bot_status_change(payload)
            elif event_type == 'recording.ready':
                return self._handle_recording_ready(payload)
            elif event_type == 'transcript.complete':
                return self._handle_transcript_complete(payload)
            elif event_type == 'sdk_upload.recording_started':
                return self._handle_sdk_upload_recording_started(payload)
            elif event_type == 'sdk_upload.recording_ended':
                return self._handle_sdk_upload_recording_ended(payload)
            elif event_type == 'sdk_upload.complete':
                return self._handle_sdk_upload_complete(payload)
            else:
                logger.warning(f"Unknown bot webhook event type: {event_type}")
                return {
                    'success': True,
                    'message': f'Unhandled event type: {event_type}'
                }
                
        except Exception as e:
            logger.error(f"Error processing bot webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process bot webhook'
            }
    
    def _handle_bot_status_change(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle bot.status_change webhook event"""
        bot_id = payload.get('data', {}).get('id')
        status = payload.get('data', {}).get('status', {}).get('code', 'unknown')
        
        logger.info(f"Bot status change - bot_id: {bot_id}, status: {status}")
        
        # Update session status based on bot status
        from .models import MeetingSession
        
        try:
            # Find session by bot ID
            session = MeetingSession.find_by_bot_id(bot_id)
            if session:
                session_id = session['session_id']
                
                # Map bot status to session status
                if status in ['in_call_recording', 'in_call']:
                    MeetingSession.update_status(session_id, 'recording')
                    logger.info(f"Updated session {session_id} to recording status")
                elif status in ['done', 'finished']:
                    MeetingSession.update_status(session_id, 'completed')
                    logger.info(f"Updated session {session_id} to completed status")
                elif status in ['fatal', 'failed', 'error']:
                    MeetingSession.update_status(session_id, 'failed')
                    logger.error(f"Updated session {session_id} to failed status")
                    
        except Exception as e:
            logger.error(f"Error updating session for bot status change: {str(e)}")
        
        return {
            'success': True,
            'message': f'Bot status change processed for {bot_id}'
        }
    
    def _handle_recording_ready(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle recording.ready webhook event"""
        bot_id = payload.get('data', {}).get('bot_id')
        recording_id = payload.get('data', {}).get('id')
        
        logger.info(f"Recording ready - bot_id: {bot_id}, recording_id: {recording_id}")
        
        # Update session with recording information
        from .models import MeetingSession
        
        try:
            session = MeetingSession.find_by_bot_id(bot_id)
            if session:
                session_id = session['session_id']
                MeetingSession.set_recording_id(session_id, recording_id)
                logger.info(f"Updated session {session_id} with recording {recording_id}")
                
                return {
                    'success': True,
                    'session_id': session_id,
                    'message': 'Recording ready and session updated'
                }
        except Exception as e:
            logger.error(f"Error updating session with recording: {str(e)}")
        
        return {
            'success': True,
            'message': f'Recording ready processed for bot {bot_id}'
        }
    
    def _handle_transcript_complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transcript.complete webhook event"""
        data = payload.get('data', {})
        transcript_id = data.get('id')
        bot_id = data.get('bot_id')
        sdk_upload_id = data.get('sdk_upload_id') or data.get('sdk_upload', {}).get('id')
        recording_id = data.get('recording_id')
        
        logger.info(f"Transcript complete - transcript_id: {transcript_id}, bot_id: {bot_id}, sdk_upload_id: {sdk_upload_id}")
        
        # Update the session with transcript data
        from .models import MeetingSession
        
        try:
            session = None
            
            # Try to find session by bot_id first (for bot-based recordings)
            if bot_id:
                session = MeetingSession.find_by_bot_id(bot_id)
            
            # Try to find by sdk_upload_id (for SDK uploads / desktop recordings)
            if not session and sdk_upload_id:
                session = MeetingSession.find_by_sdk_upload_id(sdk_upload_id)
            
            if session:
                session_id = session['session_id']
                MeetingSession.set_transcript_id(session_id, transcript_id)
                
                # Also update status to completed since transcript is now ready
                MeetingSession.update_status(session_id, 'completed')
                
                logger.info(f"Updated session {session_id} with transcript {transcript_id}")
            else:
                logger.warning(f"No session found for transcript.complete: bot_id={bot_id}, sdk_upload_id={sdk_upload_id}")
        except Exception as e:
            logger.error(f"Error updating session with transcript: {str(e)}")
        
        return {
            'success': True,
            'message': 'Transcript complete processed'
        }
    
    def _handle_sdk_upload_recording_started(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sdk_upload.recording_started webhook event"""
        data = payload.get('data', {})
        upload_id = data.get('id')
        
        logger.info(f"SDK upload recording started - upload_id: {upload_id}")
        logger.info(f"SDK upload data: {json.dumps(data, indent=2)}")
        
        # Update session status if we can find it by sdk_upload_id
        from .models import MeetingSession
        
        try:
            session = MeetingSession.find_by_sdk_upload_id(upload_id)
            if session:
                session_id = session['session_id']
                MeetingSession.update_status(session_id, 'recording')
                logger.info(f"Updated session {session_id} to recording status (SDK upload)")
        except Exception as e:
            logger.error(f"Error updating session for SDK upload recording started: {str(e)}")
        
        return {
            'success': True,
            'message': f'SDK upload recording started processed for {upload_id}'
        }
    
    def _handle_sdk_upload_recording_ended(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sdk_upload.recording_ended webhook event"""
        data = payload.get('data', {})
        upload_id = data.get('id')
        
        logger.info(f"SDK upload recording ended - upload_id: {upload_id}")
        logger.info(f"SDK upload data: {json.dumps(data, indent=2)}")
        
        # Update session status if we can find it by sdk_upload_id
        from .models import MeetingSession
        
        try:
            session = MeetingSession.find_by_sdk_upload_id(upload_id)
            if session:
                session_id = session['session_id']
                MeetingSession.update_status(session_id, 'processing')
                logger.info(f"Updated session {session_id} to processing status (SDK upload ended)")
        except Exception as e:
            logger.error(f"Error updating session for SDK upload recording ended: {str(e)}")
        
        return {
            'success': True,
            'message': f'SDK upload recording ended processed for {upload_id}'
        }


# Synchronous wrappers for Django views

def create_bot_for_meeting_sync(meeting_url: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Synchronous wrapper for creating a bot to join a meeting
    """
    try:
        # Check if RECALL_API_KEY is set before creating service
        if not os.environ.get('RECALL_API_KEY'):
            logger.error("RECALL_API_KEY environment variable is not set!")
            return {
                'success': False,
                'error': 'RECALL_API_KEY not configured',
                'message': 'RECALL_API_KEY environment variable is required for bot recording. Please configure it in your environment.'
            }
        
        service = DesktopRecordingService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.create_bot_for_meeting(meeting_url, metadata))
            return result
        finally:
            loop.close()
            
    except ValueError as e:
        # Handle missing API key error specifically
        logger.error(f"Configuration error: {str(e)}")
        return {
            'success': False,
            'error': 'Configuration error',
            'message': str(e)
        }
    except Exception as e:
        logger.error(f"Recall AI Bot API exception: {str(e)}", exc_info=True)
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create bot'
        }


def get_bot_sync(bot_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for getting bot information"""
    try:
        service = DesktopRecordingService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.get_bot(bot_id))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in sync wrapper for get_bot: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to get bot information'
        }


def stop_bot_sync(bot_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for stopping a bot"""
    try:
        service = DesktopRecordingService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.stop_bot(bot_id))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in sync wrapper for stop_bot: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to stop bot'
        }


def handle_bot_webhook_sync(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for handling bot webhooks"""
    try:
        service = DesktopRecordingService()
        return service.handle_bot_webhook(event_type, payload)
    except Exception as e:
        logger.error(f"Error in sync wrapper for handle_bot_webhook: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to handle bot webhook'
        }
