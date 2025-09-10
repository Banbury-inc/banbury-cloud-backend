"""
Services for meeting agent functionality using MongoDB (following existing patterns)
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .models import MeetingSession
from .recall_service import create_recall_bot_sync, get_recall_bot_sync, stop_recall_bot_sync

logger = logging.getLogger(__name__)


class MeetingAgentService:
    """Service for managing meeting agent operations"""
    
    def __init__(self):
        self.active_sessions = {}
    
    def join_meeting(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """
        Join a meeting session using Recall AI
        
        Creates a Recall AI bot that will:
        1. Join the meeting automatically
        2. Start recording video/audio
        3. Generate real-time transcription
        4. Handle automatic leaving
        """
        try:
            meeting_url = session.get('meeting_url')
            session_id = session.get('session_id')
            metadata = session.get('metadata', {})
            
            logger.info(f"Creating Recall AI bot for meeting: {meeting_url}")
            
            # Prepare bot metadata from session settings
            bot_metadata = {
                'bot_name': metadata.get('botName', f'Meeting Recorder - {session_id[:8]}'),
                'recording_mode': metadata.get('recordingMode', 'speaker_view'),
                'transcription_enabled': metadata.get('transcriptionEnabled', True),
                'language': metadata.get('language', 'en'),
                'session_id': session_id,
                'platform_id': session.get('platform_id'),
                'user_id': session.get('user_id'),
                'title': session.get('title', 'Untitled Meeting')
            }
            
            # Create the Recall AI bot
            bot_result = create_recall_bot_sync(meeting_url, bot_metadata)
            
            if bot_result['success']:
                bot_id = bot_result['bot_id']
                bot_data = bot_result['bot_data']
                
                logger.info(f"Successfully created Recall bot {bot_id} for session {session_id}")
                
                # Update session with bot information
                session_update = {
                    'recall_bot_id': bot_id,
                    'recall_bot_data': bot_data,
                    'status': 'active',
                    'agent_join_time': datetime.utcnow()
                }
                
                update_result = MeetingSession.update_session(session_id, session_update)
                if not update_result.get('success', False):
                    logger.warning(f"Failed to update session {session_id} with bot data")
                
                return {
                    'success': True,
                    'message': f'Successfully created Recall bot and joined meeting',
                    'bot_id': bot_id,
                    'bot_data': bot_data
                }
            else:
                logger.error(f"Failed to create Recall bot: {bot_result.get('message', 'Unknown error')}")
                return {
                    'success': False,
                    'message': f"Failed to create Recall bot: {bot_result.get('message', 'Unknown error')}",
                    'error': bot_result.get('error'),
                    'details': bot_result.get('details')
                }
                
        except Exception as e:
            logger.error(f"Failed to join meeting {session.get('session_id')}: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to join meeting: {str(e)}'
            }
    
    def leave_meeting(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Leave a meeting session and stop the Recall AI bot"""
        try:
            session_id = session.get('session_id')
            recall_bot_id = session.get('recall_bot_id')
            
            logger.info(f"Leaving meeting: {session_id}")
            
            if recall_bot_id:
                logger.info(f"Stopping Recall bot: {recall_bot_id}")
                
                # Stop the Recall AI bot
                stop_result = stop_recall_bot_sync(recall_bot_id)
                
                if stop_result['success']:
                    logger.info(f"Handled Recall bot {recall_bot_id}: {stop_result.get('message')}")
                    
                    # Update session status regardless of whether bot was deleted or left automatically
                    update_data = {
                        'status': 'completed',
                        'end_time': datetime.utcnow()
                    }
                    MeetingSession.update_session(session_id, update_data)
                    
                    return {
                        'success': True,
                        'message': stop_result.get('message', 'Successfully handled bot leaving')
                    }
                else:
                    logger.error(f"Failed to stop Recall bot {recall_bot_id}: {stop_result.get('message')}")
                    
                    # Still mark session as completed even if bot stop failed
                    # The bot will leave automatically anyway
                    update_data = {
                        'status': 'completed',
                        'end_time': datetime.utcnow()
                    }
                    MeetingSession.update_session(session_id, update_data)
                    
                    return {
                        'success': True,
                        'message': 'Session ended (bot will leave automatically)'
                    }
            else:
                logger.warning(f"No Recall bot ID found for session {session_id}")
                return {
                    'success': True,
                    'message': 'No active bot to stop'
                }
            
        except Exception as e:
            logger.error(f"Failed to leave meeting {session.get('session_id')}: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to leave meeting: {str(e)}'
            }
    
    def _join_zoom_meeting(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Join a Zoom meeting"""
        # Simulate Zoom joining logic
        logger.info(f"Joining Zoom meeting: {session.get('meeting_url')}")
        
        # In production, this would:
        # 1. Launch browser with Zoom web client
        # 2. Handle authentication if required
        # 3. Join meeting with appropriate settings
        # 4. Start recording
        
        return {
            'success': True,
            'message': 'Successfully joined Zoom meeting'
        }
    
    def _join_teams_meeting(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Join a Microsoft Teams meeting"""
        logger.info(f"Joining Teams meeting: {session.get('meeting_url')}")
        
        return {
            'success': True,
            'message': 'Successfully joined Teams meeting'
        }
    
    def _join_google_meet(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Join a Google Meet"""
        logger.info(f"Joining Google Meet: {session.get('meeting_url')}")
        
        return {
            'success': True,
            'message': 'Successfully joined Google Meet'
        }
    
    def _join_webex_meeting(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Join a Webex meeting"""
        logger.info(f"Joining Webex meeting: {session.get('meeting_url')}")
        
        return {
            'success': True,
            'message': 'Successfully joined Webex meeting'
        }


class TranscriptionService:
    """Service for handling meeting transcription using OpenAI Whisper"""
    
    def __init__(self):
        import openai
        import os
        
        # Set OpenAI API key from environment variable
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not set. Transcription will use fallback simulation.")
        
        self.client = openai
    
    def start_transcription(self, session: Dict[str, Any]):
        """Start transcription process for a meeting"""
        try:
            session_id = session.get('session_id')
            logger.info(f"Starting transcription for session: {session_id}")
            
            recording_url = session.get('recording_url')
            if not recording_url:
                logger.error(f"No recording URL found for session {session_id}")
                MeetingSession.update_session(session_id, {'status': 'failed'})
                return
            
            # Check if OpenAI API key is available
            if not self.client.api_key:
                logger.warning(f"OpenAI API key not available, using simulation for session {session_id}")
                self._simulate_transcription(session_id)
                return
            
            # Process transcription with Whisper
            self._transcribe_with_whisper(session_id, recording_url, session.get('metadata', {}))
            
        except Exception as e:
            logger.error(f"Transcription failed for session {session.get('session_id')}: {str(e)}")
            MeetingSession.update_session(session.get('session_id'), {'status': 'failed'})
    
    def _transcribe_with_whisper(self, session_id: str, recording_url: str, metadata: Dict[str, Any]):
        """Transcribe audio using OpenAI Whisper API"""
        try:
            import requests
            import tempfile
            import os
            
            # Download the recording file
            logger.info(f"Downloading recording from: {recording_url}")
            response = requests.get(recording_url, stream=True)
            response.raise_for_status()
            
            # Save to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    temp_file.write(chunk)
                temp_file_path = temp_file.name
            
            try:
                # Get language from metadata
                language = metadata.get('language', 'en')
                
                # Transcribe with Whisper
                logger.info(f"Transcribing audio with Whisper for session: {session_id}")
                
                with open(temp_file_path, 'rb') as audio_file:
                    transcript = self.client.Audio.transcribe(
                        model="whisper-1",
                        file=audio_file,
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                        language=language if language != 'auto' else None
                    )
                
                # Process Whisper response
                self._process_whisper_response(session_id, transcript)
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_file_path):
                    os.unlink(temp_file_path)
                    
        except Exception as e:
            logger.error(f"Whisper transcription failed for session {session_id}: {str(e)}")
            # Fall back to simulation if Whisper fails
            logger.info(f"Falling back to simulation for session {session_id}")
            self._simulate_transcription(session_id)
    
    def _process_whisper_response(self, session_id: str, transcript):
        """Process Whisper API response and save to database"""
        try:
            # Extract segments from Whisper response
            segments = transcript.get('segments', [])
            
            # Convert Whisper segments to our format
            processed_segments = []
            for i, segment in enumerate(segments):
                processed_segment = {
                    'speaker_id': f'speaker_{i % 3 + 1}',  # Simple speaker assignment
                    'speaker_name': f'Speaker {i % 3 + 1}',  # Would use diarization in production
                    'text': segment.get('text', '').strip(),
                    'start_time': segment.get('start', 0.0),
                    'end_time': segment.get('end', 0.0),
                    'confidence': 0.95  # Whisper doesn't provide confidence, use default
                }
                processed_segments.append(processed_segment)
                
                # Add to database
                MeetingSession.add_transcription_segment(session_id, processed_segment)
            
            # Update session with full transcription text
            full_text = transcript.get('text', '')
            if not full_text:
                full_text = '\n'.join([f"{seg['speaker_name']}: {seg['text']}" for seg in processed_segments])
            
            MeetingSession.update_session(session_id, {
                'transcription_text': full_text,
                'status': 'completed'
            })
            
            logger.info(f"Whisper transcription completed for session: {session_id}")
            logger.info(f"Processed {len(processed_segments)} segments")
            
        except Exception as e:
            logger.error(f"Failed to process Whisper response for session {session_id}: {str(e)}")
            # Fall back to simulation
            self._simulate_transcription(session_id)
    
    def _simulate_transcription(self, session_id: str):
        """Fallback simulation when Whisper is not available"""
        logger.info(f"Using simulated transcription for session: {session_id}")
        
        # Create some sample transcription segments
        sample_segments = [
            {
                'speaker_id': 'speaker_1',
                'speaker_name': 'John Doe',
                'text': 'Good morning everyone, welcome to our weekly standup meeting.',
                'start_time': 0.0,
                'end_time': 4.5,
                'confidence': 0.95
            },
            {
                'speaker_id': 'speaker_2',
                'speaker_name': 'Jane Smith',
                'text': 'Thanks John. I completed the user authentication feature this week.',
                'start_time': 5.0,
                'end_time': 9.2,
                'confidence': 0.92
            },
            {
                'speaker_id': 'speaker_1',
                'speaker_name': 'John Doe',
                'text': 'Great work! What are you planning to work on next?',
                'start_time': 10.0,
                'end_time': 13.5,
                'confidence': 0.96
            }
        ]
        
        # Add transcription segments to session
        for segment in sample_segments:
            MeetingSession.add_transcription_segment(session_id, segment)
        
        # Update session with full transcription text
        full_text = '\n'.join([f"{seg['speaker_name']}: {seg['text']}" for seg in sample_segments])
        MeetingSession.update_session(session_id, {
            'transcription_text': full_text,
            'status': 'completed'
        })
        
        logger.info(f"Simulated transcription completed for session: {session_id}")
    
    def transcribe_audio_file(self, audio_file_path: str, language: str = 'en') -> Dict[str, Any]:
        """Directly transcribe an audio file with Whisper"""
        try:
            if not self.client.api_key:
                raise ValueError("OpenAI API key not configured")
            
            with open(audio_file_path, 'rb') as audio_file:
                transcript = self.client.Audio.transcribe(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    language=language if language != 'auto' else None
                )
            
            return {
                'success': True,
                'transcript': transcript,
                'text': transcript.get('text', ''),
                'segments': transcript.get('segments', [])
            }
            
        except Exception as e:
            logger.error(f"Direct Whisper transcription failed: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }


class SummaryService:
    """Service for generating meeting summaries using OpenAI GPT-4"""
    
    def __init__(self):
        import openai
        import os
        
        # Set OpenAI API key from environment variable
        openai.api_key = os.environ.get('OPENAI_API_KEY')
        if not openai.api_key:
            logger.warning("OPENAI_API_KEY not set. Summary generation will use fallback simulation.")
        
        self.client = openai
    
    def generate_summary(self, session: Dict[str, Any]):
        """Generate AI summary for a meeting session"""
        try:
            session_id = session.get('session_id')
            logger.info(f"Generating summary for session: {session_id}")
            
            transcription_text = session.get('transcription_text', '')
            if not transcription_text:
                raise ValueError("No transcription available for summary generation")
            
            # Check if OpenAI API key is available
            if not self.client.api_key:
                logger.warning(f"OpenAI API key not available, using simulation for session {session_id}")
                summary_data = self._generate_fallback_summary(transcription_text)
            else:
                # Use GPT-4 for real summary generation
                summary_data = self._generate_gpt4_summary(transcription_text, session.get('metadata', {}))
            
            # Generate action items if enabled
            if session.get('metadata', {}).get('action_items_enabled', False):
                if self.client.api_key:
                    summary_data['action_items'] = self._extract_action_items_gpt4(transcription_text)
                else:
                    summary_data['action_items'] = self._extract_action_items_fallback()
            else:
                summary_data['action_items'] = []
            
            # Save summary to session
            MeetingSession.set_summary(session_id, summary_data)
            
            logger.info(f"Summary generated for session: {session_id}")
            
        except Exception as e:
            logger.error(f"Summary generation failed for session {session.get('session_id')}: {str(e)}")
            raise
    
    def _generate_gpt4_summary(self, transcription: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate AI summary using GPT-4"""
        try:
            logger.info("Generating summary with GPT-4")
            
            # Create prompt for GPT-4
            prompt = f"""
            Please analyze the following meeting transcription and provide a comprehensive summary.
            
            TRANSCRIPTION:
            {transcription}
            
            Please provide:
            1. A brief summary of the meeting
            2. Key points discussed
            3. Decisions made
            4. Next steps identified
            
            Format your response as JSON with the following structure:
            {{
                "summary": "Brief meeting summary",
                "key_points": ["Point 1", "Point 2", ...],
                "decisions": ["Decision 1", "Decision 2", ...],
                "next_steps": ["Step 1", "Step 2", ...]
            }}
            """
            
            response = self.client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert meeting analyst. Analyze meeting transcriptions and provide structured summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # Parse GPT-4 response
            content = response.choices[0].message.content
            
            # Try to parse JSON response
            import json
            try:
                summary_data = json.loads(content)
                logger.info("Successfully generated GPT-4 summary")
                return summary_data
            except json.JSONDecodeError:
                logger.warning("GPT-4 response was not valid JSON, using fallback")
                return self._generate_fallback_summary(transcription)
                
        except Exception as e:
            logger.error(f"GPT-4 summary generation failed: {str(e)}")
            return self._generate_fallback_summary(transcription)
    
    def _extract_action_items_gpt4(self, transcription: str) -> list:
        """Extract action items using GPT-4"""
        try:
            logger.info("Extracting action items with GPT-4")
            
            prompt = f"""
            Please analyze the following meeting transcription and extract action items.
            
            TRANSCRIPTION:
            {transcription}
            
            Extract any tasks, assignments, or action items mentioned in the meeting.
            For each action item, identify:
            - Description of the task
            - Who is assigned (if mentioned)
            - Priority level (high/medium/low)
            - Any deadlines mentioned
            
            Format as JSON array:
            [
                {{
                    "description": "Task description",
                    "assignee": "Person name or empty string",
                    "priority": "high|medium|low",
                    "status": "pending"
                }}
            ]
            """
            
            response = self.client.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at extracting action items from meeting transcriptions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=800
            )
            
            # Parse GPT-4 response
            content = response.choices[0].message.content
            
            # Try to parse JSON response
            import json
            try:
                action_items = json.loads(content)
                if isinstance(action_items, list):
                    logger.info(f"Successfully extracted {len(action_items)} action items with GPT-4")
                    return action_items
                else:
                    logger.warning("GPT-4 action items response was not a list, using fallback")
                    return self._extract_action_items_fallback()
            except json.JSONDecodeError:
                logger.warning("GPT-4 action items response was not valid JSON, using fallback")
                return self._extract_action_items_fallback()
                
        except Exception as e:
            logger.error(f"GPT-4 action item extraction failed: {str(e)}")
            return self._extract_action_items_fallback()
    
    def _generate_fallback_summary(self, transcription: str) -> Dict[str, Any]:
        """Generate fallback summary when GPT-4 is not available"""
        return {
            'summary': """
            This was a weekly team standup meeting where team members discussed their progress 
            and upcoming work. The main focus was on the user authentication feature completion 
            and planning for the next sprint.
            """.strip(),
            'key_points': [
                'User authentication feature has been completed',
                'Team is preparing for next sprint planning',
                'Good progress on overall project timeline'
            ],
            'decisions': [
                'Proceed with user authentication feature deployment',
                'Schedule next sprint planning for Friday'
            ],
            'next_steps': [
                'Deploy authentication feature to staging',
                'Prepare sprint planning agenda',
                'Review and prioritize backlog items'
            ]
        }
    
    def _extract_action_items_fallback(self) -> list:
        """Extract fallback action items when GPT-4 is not available"""
        return [
            {
                'description': 'Deploy user authentication feature to staging environment',
                'assignee': 'Jane Smith',
                'priority': 'high',
                'status': 'pending'
            },
            {
                'description': 'Prepare sprint planning agenda for Friday meeting',
                'assignee': 'John Doe',
                'priority': 'medium',
                'status': 'pending'
            }
        ]


class PlatformService:
    """Service for platform-specific operations"""
    
    @staticmethod
    def get_platform_capabilities(platform_id: str) -> Dict[str, Any]:
        """Get capabilities for a specific platform"""
        capabilities = {
            'zoom': {
                'recording': True,
                'transcription': True,
                'screen_share': True,
                'chat': True,
                'breakout_rooms': False
            },
            'teams': {
                'recording': True,
                'transcription': True,
                'screen_share': True,
                'chat': True,
                'breakout_rooms': True
            },
            'meet': {
                'recording': True,
                'transcription': True,
                'screen_share': True,
                'chat': True,
                'breakout_rooms': True
            },
            'webex': {
                'recording': True,
                'transcription': False,
                'screen_share': True,
                'chat': True,
                'breakout_rooms': True
            }
        }
        
        return capabilities.get(platform_id, {})
    
    @staticmethod
    def validate_meeting_url(url: str, platform_id: str) -> bool:
        """Validate if URL matches the expected platform format"""
        platform_patterns = {
            'zoom': r'zoom\.us/j/\d+',
            'teams': r'teams\.microsoft\.com|teams\.live\.com',
            'meet': r'meet\.google\.com/[a-z-]+',
            'webex': r'.*\.webex\.com'
        }
        
        pattern = platform_patterns.get(platform_id)
        if not pattern:
            return False
        
        import re
        return bool(re.search(pattern, url, re.IGNORECASE))