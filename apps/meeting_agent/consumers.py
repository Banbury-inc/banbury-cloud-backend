"""
WebSocket Consumer for Live Transcription

This consumer handles WebSocket connections for real-time transcription
streaming during meeting recordings.
"""

import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class TranscriptionConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for live transcription updates.
    
    Clients connect to receive real-time transcription segments
    during an active recording session.
    """
    
    async def connect(self):
        """Handle WebSocket connection"""
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        self.group_name = f'transcription_{self.session_id}'
        
        if not self.session_id:
            logger.warning("WebSocket connection attempt without session_id")
            await self.close()
            return
        
        # Join the session's transcription group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        
        logger.info(f"WebSocket connected for session {self.session_id}")
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'session_id': self.session_id,
            'message': 'Connected to live transcription'
        }))
        
        # Send any existing live transcript segments
        await self.send_existing_segments()
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection"""
        if hasattr(self, 'group_name'):
            # Leave the transcription group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            logger.info(f"WebSocket disconnected for session {self.session_id}")
    
    async def receive(self, text_data):
        """Handle incoming WebSocket messages"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type', '')
            
            if message_type == 'ping':
                # Respond to ping with pong
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
            elif message_type == 'request_segments':
                # Client requesting all current segments
                await self.send_existing_segments()
            else:
                logger.debug(f"Unknown message type: {message_type}")
                
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON received: {text_data}")
    
    async def transcription_segment(self, event):
        """
        Handle transcription segment broadcasts from the webhook handler.
        
        This method is called when a segment is sent to the group via:
        channel_layer.group_send(group_name, {'type': 'transcription_segment', ...})
        """
        segment = event.get('segment', {})
        session_id = event.get('session_id')
        
        # Send segment to WebSocket client
        await self.send(text_data=json.dumps({
            'type': 'transcription_segment',
            'segment': segment,
            'session_id': session_id
        }))
    
    async def recording_status(self, event):
        """
        Handle recording status updates.
        
        Sent when recording starts, stops, or status changes.
        """
        await self.send(text_data=json.dumps({
            'type': 'recording_status',
            'status': event.get('status'),
            'session_id': event.get('session_id'),
            'message': event.get('message', '')
        }))
    
    async def send_existing_segments(self):
        """Send any existing live transcript segments for this session"""
        try:
            from .models import MeetingSession
            from asgiref.sync import sync_to_async
            
            @sync_to_async
            def get_segments():
                return MeetingSession.get_live_transcript_segments(self.session_id)
            
            segments = await get_segments()
            
            if segments:
                await self.send(text_data=json.dumps({
                    'type': 'existing_segments',
                    'segments': segments,
                    'session_id': self.session_id
                }))
                
        except Exception as e:
            logger.warning(f"Could not fetch existing segments for {self.session_id}: {e}")
