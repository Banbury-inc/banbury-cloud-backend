"""
Recall AI Service for creating and managing meeting bots
"""
import os
import logging
import httpx
import asyncio
import json
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RecallAIService:
    """Service for interacting with Recall AI API"""
    
    def __init__(self):
        self.api_key = os.environ.get('RECALL_API_KEY')
        self.base_url = os.environ.get('RECALL_API_URL', 'https://us-west-2.recall.ai/api/v1')
        
        if not self.api_key:
            logger.error("RECALL_API_KEY environment variable is not set!")
            raise ValueError("RECALL_API_KEY is required for Recall AI integration")
        
        self.headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def create_bot(self, meeting_url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new Recall AI bot for a meeting
        
        Args:
            meeting_url (str): The meeting URL to join
            metadata (dict): Bot configuration metadata
            
        Returns:
            dict: Bot creation response from Recall AI
        """
        try:
            if not metadata:
                metadata = {}
                
            # Extract settings from metadata
            bot_name = metadata.get('bot_name', 'Meeting Recorder')
            recording_mode = metadata.get('recording_mode', 'speaker_view')
            transcription_enabled = metadata.get('transcription_enabled', True)
            language = metadata.get('language', 'en')
            
            # Build comprehensive payload with transcription enabled in recording_config
            payload = {
                'meeting_url': meeting_url,
                'bot_name': bot_name,
                'automatic_leave': {
                    'waiting_room_timeout': 1200,  # 20 minutes
                    'noone_joined_timeout': 1200,  # 20 minutes  
                    'everyone_left_timeout': 30    # 30 seconds
                }
            }
            
            # Configure recording with transcription enabled
            recording_config = {
                'video_mixed_layout': recording_mode or 'speaker_view',
                'video_mixed_mp4': {},
                'participant_events': {},
                'meeting_metadata': {}
            }
            
            # Enable transcription in recording_config if requested
            if transcription_enabled:
                # Add transcription configuration to recording_config
                recording_config['transcript'] = {
                    'provider': {
                        'recallai_streaming': {
                            'prioritize_accuracy': True  # Use accurate mode for better quality
                        }
                    }
                }
                logger.info(f"Transcription enabled in recording_config with provider: recallai_streaming (accurate mode)")
            else:
                logger.info("Transcription disabled in recording_config")
            
            payload['recording_config'] = recording_config
            logger.info(f"Recording mode configured: {recording_mode or 'speaker_view'}")
            
            logger.info(f"Creating Recall bot for meeting: {meeting_url}")
            logger.info(f"Final bot configuration: {json.dumps(payload, indent=2, default=str)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f'{self.base_url}/bot/',
                    json=payload,
                    headers=self.headers
                )
                
                # Log response for debugging
                logger.info(f"Recall API response status: {response.status_code}")
                logger.info(f"Recall API response headers: {dict(response.headers)}")
                
                if response.status_code == 201:
                    bot_data = response.json()
                    logger.info(f"Successfully created Recall bot: {bot_data.get('id')}")
                    
                    # Log transcription configuration in response
                    if 'transcription' in bot_data:
                        logger.info(f"Bot transcription config: {bot_data['transcription']}")
                    if 'real_time_transcription' in bot_data:
                        logger.info(f"Bot real-time transcription config: {bot_data['real_time_transcription']}")
                    
                    return {
                        'success': True,
                        'bot_id': bot_data.get('id'),
                        'bot_data': bot_data,
                        'message': 'Bot created successfully'
                    }
                else:
                    error_text = response.text
                    logger.error(f"Recall API error: {response.status_code} - {error_text}")
                    logger.error(f"Request payload was: {payload}")
                    
                    # Try to parse error details for better user feedback
                    try:
                        error_json = response.json()
                        error_details = []
                        for field, errors in error_json.items():
                            if isinstance(errors, list):
                                error_details.append(f"{field}: {', '.join(errors)}")
                            else:
                                error_details.append(f"{field}: {errors}")
                        formatted_error = "; ".join(error_details)
                    except:
                        formatted_error = error_text
                    
                    return {
                        'success': False,
                        'error': f'Recall API error: {response.status_code}',
                        'details': formatted_error,
                        'message': f'Failed to create bot: {formatted_error}'
                    }
                    
        except httpx.TimeoutException as e:
            logger.error(f"Timeout creating Recall bot: {str(e)}")
            return {
                'success': False,
                'error': 'timeout',
                'message': 'Request timed out while creating bot'
            }
        except Exception as e:
            logger.error(f"Error creating Recall bot: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create bot due to unexpected error'
            }
    
    async def get_bot(self, bot_id: str) -> Dict[str, Any]:
        """
        Get information about a specific bot
        
        Args:
            bot_id (str): The bot ID
            
        Returns:
            dict: Bot information from Recall AI
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f'{self.base_url}/bot/{bot_id}/',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    bot_data = response.json()
                    return {
                        'success': True,
                        'bot_data': bot_data
                    }
                else:
                    logger.error(f"Error fetching bot {bot_id}: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': f'API error: {response.status_code}',
                        'message': 'Failed to fetch bot information'
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching bot {bot_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to fetch bot information'
            }
    
    async def stop_bot(self, bot_id: str) -> Dict[str, Any]:
        """
        Stop a running bot
        
        Note: Recall AI doesn't allow deleting bots that have joined meetings.
        The bot will leave automatically based on automatic_leave settings.
        
        Args:
            bot_id (str): The bot ID to stop
            
        Returns:
            dict: Response from Recall AI
        """
        try:
            # First check the bot status
            bot_info = await self.get_bot(bot_id)
            if not bot_info['success']:
                return {
                    'success': False,
                    'message': 'Could not get bot status'
                }
            
            bot_data = bot_info['bot_data']
            bot_status = bot_data.get('status_changes', [])
            current_status = bot_status[-1].get('code') if bot_status else 'unknown'
            
            logger.info(f"Bot {bot_id} current status: {current_status}")
            
            # Try to delete the bot (only works for scheduled bots that haven't joined)
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.delete(
                    f'{self.base_url}/bot/{bot_id}/',
                    headers=self.headers
                )
                
                if response.status_code in [200, 204]:
                    logger.info(f"Successfully deleted bot: {bot_id}")
                    return {
                        'success': True,
                        'message': 'Bot deleted successfully'
                    }
                elif response.status_code == 405:
                    # Expected for bots that have joined meetings
                    logger.info(f"Bot {bot_id} cannot be deleted (already joined meeting). It will leave automatically.")
                    return {
                        'success': True,
                        'message': 'Bot will leave automatically (cannot delete active bots)',
                        'note': 'Active bots leave based on automatic_leave settings'
                    }
                else:
                    error_text = response.text
                    logger.error(f"Error stopping bot {bot_id}: {response.status_code} - {error_text}")
                    
                    # Parse error for better handling
                    try:
                        error_json = response.json()
                        if error_json.get('code') == 'cannot_delete_bot':
                            return {
                                'success': True,
                                'message': 'Bot will leave automatically (cannot delete active bots)',
                                'note': error_json.get('detail', 'Active bots leave based on automatic_leave settings')
                            }
                    except:
                        pass
                    
                    return {
                        'success': False,
                        'error': f'API error: {response.status_code}',
                        'message': 'Failed to stop bot'
                    }
                    
        except Exception as e:
            logger.error(f"Error stopping bot {bot_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to stop bot'
            }
    
    async def create_async_transcript(self, recording_id: str, language: str = 'en') -> Dict[str, Any]:
        """
        Create an async transcript for a recording
        
        Args:
            recording_id (str): The recording ID from Recall AI
            language (str): Language code for transcription (default: 'en')
            
        Returns:
            dict: Transcript creation response from Recall AI
        """
        try:
            payload = {
                'provider': {
                    'recallai_async': {
                        'language_code': language
                    }
                }
            }
            
            logger.info(f"Creating async transcript for recording: {recording_id}")
            logger.info(f"Transcript config: {json.dumps(payload, indent=2)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f'{self.base_url}/recording/{recording_id}/create_transcript/',
                    json=payload,
                    headers=self.headers
                )
                
                logger.info(f"Transcript API response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    transcript_data = response.json()
                    logger.info(f"Successfully created async transcript: {transcript_data.get('id')}")
                    return {
                        'success': True,
                        'transcript_id': transcript_data.get('id'),
                        'transcript_data': transcript_data,
                        'message': 'Async transcript created successfully'
                    }
                else:
                    error_text = response.text
                    logger.error(f"Transcript API error: {response.status_code} - {error_text}")
                    return {
                        'success': False,
                        'error': f'Transcript API error: {response.status_code}',
                        'details': error_text,
                        'message': f'Failed to create transcript: {error_text}'
                    }
                    
        except Exception as e:
            logger.error(f"Error creating async transcript for recording {recording_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create async transcript due to unexpected error'
            }
    
    async def get_transcript(self, transcript_id: str) -> Dict[str, Any]:
        """
        Get transcript data by ID
        
        Args:
            transcript_id (str): The transcript ID
            
        Returns:
            dict: Transcript data from Recall AI
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f'{self.base_url}/transcript/{transcript_id}/',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    transcript_data = response.json()
                    return {
                        'success': True,
                        'transcript_data': transcript_data
                    }
                else:
                    logger.error(f"Error fetching transcript {transcript_id}: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': f'API error: {response.status_code}',
                        'message': 'Failed to fetch transcript'
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching transcript {transcript_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to fetch transcript'
            }

    async def list_bots(self, limit: int = 50) -> Dict[str, Any]:
        """
        List all bots for the account
        
        Args:
            limit (int): Maximum number of bots to return
            
        Returns:
            dict: List of bots from Recall AI
        """
        try:
            params = {'limit': limit}
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f'{self.base_url}/bot/',
                    headers=self.headers,
                    params=params
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        'success': True,
                        'bots': data.get('results', []),
                        'total': data.get('count', 0)
                    }
                else:
                    logger.error(f"Error listing bots: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': f'API error: {response.status_code}',
                        'message': 'Failed to list bots'
                    }
                    
        except Exception as e:
            logger.error(f"Error listing bots: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to list bots'
            }


def create_recall_bot_sync(meeting_url: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Synchronous wrapper for creating a Recall bot
    This is needed for Django views which are not async
    """
    try:
        service = RecallAIService()
        
        # Run the async function in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.create_bot(meeting_url, metadata))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in sync wrapper for create_bot: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create bot'
        }


def get_recall_bot_sync(bot_id: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for getting bot information
    """
    try:
        service = RecallAIService()
        
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


def stop_recall_bot_sync(bot_id: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for stopping a bot
    """
    try:
        service = RecallAIService()
        
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


def create_async_transcript_sync(recording_id: str, language: str = 'en') -> Dict[str, Any]:
    """
    Synchronous wrapper for creating async transcript
    """
    try:
        service = RecallAIService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.create_async_transcript(recording_id, language))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in sync wrapper for create_async_transcript: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to create async transcript'
        }


def get_transcript_sync(transcript_id: str) -> Dict[str, Any]:
    """
    Synchronous wrapper for getting transcript
    """
    try:
        service = RecallAIService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.get_transcript(transcript_id))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in sync wrapper for get_transcript: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to get transcript'
        }
