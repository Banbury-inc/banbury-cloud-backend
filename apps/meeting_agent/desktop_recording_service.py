"""
Desktop Recording Service for Recall AI Desktop SDK

This service handles:
- Creating upload tokens for desktop recordings
- Processing webhooks from the Desktop SDK
- Managing desktop recording sessions
- Fallback to S3 pre-signed URLs when Recall SDK is unavailable
"""

import os
import logging
import httpx
import asyncio
import json
import uuid
import boto3
from botocore.exceptions import ClientError
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# S3 Configuration for fallback uploads
S3_BUCKET_NAME = os.environ.get('AWS_S3_BUCKET_NAME')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


class S3UploadTokenService:
    """Fallback service for generating S3 pre-signed URLs for desktop recording uploads"""
    
    def __init__(self):
        self.s3_client = None
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY and S3_BUCKET_NAME:
            self.s3_client = boto3.client(
                's3',
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_REGION
            )
    
    def create_upload_token(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a pre-signed S3 URL for uploading desktop recordings
        
        This is used as a fallback when the Recall AI Desktop SDK is not available.
        
        Args:
            metadata: Optional metadata to associate with the recording
            
        Returns:
            dict: Contains upload_token (pre-signed URL), token_id, and expires_at
        """
        try:
            if not self.s3_client:
                return {
                    'success': False,
                    'error': 'S3 not configured',
                    'message': 'AWS S3 credentials are not configured for fallback upload'
                }
            
            # Generate unique token ID and S3 key
            token_id = str(uuid.uuid4())
            user_id = metadata.get('user_id', 'unknown') if metadata else 'unknown'
            timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
            
            # Create S3 key for the recording
            s3_key = f"desktop-recordings/{user_id}/{token_id}/recording_{timestamp}.webm"
            
            # Generate pre-signed URL for upload (valid for 2 hours)
            expires_in = 7200  # 2 hours
            expires_at = (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat() + 'Z'
            
            presigned_url = self.s3_client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': S3_BUCKET_NAME,
                    'Key': s3_key,
                    'ContentType': 'video/webm'
                },
                ExpiresIn=expires_in
            )
            
            logger.info(f"Created S3 fallback upload token: {token_id} for user: {user_id}")
            
            # Store token metadata for later use (when upload completes)
            self._store_token_metadata(token_id, s3_key, metadata)
            
            return {
                'success': True,
                'upload_token': presigned_url,
                'token_id': token_id,
                'expires_at': expires_at,
                's3_key': s3_key,
                'upload_type': 's3_fallback',
                'message': 'S3 upload token created (Recall AI Desktop SDK not available)'
            }
            
        except ClientError as e:
            logger.error(f"S3 error creating upload token: {str(e)}")
            return {
                'success': False,
                'error': f'S3 error: {str(e)}',
                'message': 'Failed to create S3 upload token'
            }
        except Exception as e:
            logger.error(f"Error creating S3 upload token: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create upload token'
            }
    
    def _store_token_metadata(self, token_id: str, s3_key: str, metadata: Optional[Dict[str, Any]]) -> None:
        """Store token metadata in MongoDB for later retrieval"""
        try:
            from pymongo.mongo_client import MongoClient
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            tokens_collection = db["desktop_upload_tokens"]
            
            token_doc = {
                'token_id': token_id,
                's3_key': s3_key,
                'metadata': metadata or {},
                'created_at': datetime.utcnow(),
                'status': 'pending',
                'upload_type': 's3_fallback'
            }
            
            tokens_collection.insert_one(token_doc)
            logger.info(f"Stored upload token metadata: {token_id}")
            
        except Exception as e:
            logger.error(f"Error storing token metadata: {str(e)}")


class DesktopRecordingService:
    """Service for managing Recall AI Desktop Recording SDK operations"""
    
    def __init__(self):
        self.api_key = os.environ.get('RECALL_API_KEY')
        self.base_url = os.environ.get('RECALL_API_URL', 'https://us-west-2.recall.ai/api/v1')
        
        if not self.api_key:
            logger.error("RECALL_API_KEY environment variable is not set!")
            raise ValueError("RECALL_API_KEY is required for Desktop Recording integration")
        
        self.headers = {
            'Authorization': f'Token {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    async def create_upload_token(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create an upload token for desktop recording
        
        The upload token is used by the Desktop SDK to upload recordings
        directly to Recall AI's storage.
        
        Args:
            metadata: Optional metadata to associate with the recording
            
        Returns:
            dict: Contains upload_token and token_id on success
        """
        try:
            payload = {}
            
            if metadata:
                payload['metadata'] = metadata
            
            logger.info("Creating desktop upload token")
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f'{self.base_url}/desktop/upload-tokens/',
                    json=payload,
                    headers=self.headers
                )
                
                logger.info(f"Upload token API response status: {response.status_code}")
                
                if response.status_code in [200, 201]:
                    token_data = response.json()
                    logger.info(f"Successfully created upload token: {token_data.get('id', 'unknown')}")
                    return {
                        'success': True,
                        'upload_token': token_data.get('token'),
                        'token_id': token_data.get('id'),
                        'expires_at': token_data.get('expires_at'),
                        'message': 'Upload token created successfully'
                    }
                else:
                    error_text = response.text
                    logger.error(f"Upload token API error: {response.status_code} - {error_text}")
                    
                    try:
                        error_json = response.json()
                        error_details = json.dumps(error_json, indent=2)
                    except:
                        error_details = error_text
                    
                    return {
                        'success': False,
                        'error': f'API error: {response.status_code}',
                        'details': error_details,
                        'message': f'Failed to create upload token: {response.status_code}'
                    }
                    
        except httpx.TimeoutException as e:
            logger.error(f"Timeout creating upload token: {str(e)}")
            return {
                'success': False,
                'error': 'timeout',
                'message': 'Request timed out while creating upload token'
            }
        except Exception as e:
            logger.error(f"Error creating upload token: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create upload token due to unexpected error'
            }
    
    async def get_sdk_upload(self, upload_id: str) -> Dict[str, Any]:
        """
        Get information about an SDK upload
        
        Args:
            upload_id: The SDK upload ID
            
        Returns:
            dict: Upload information from Recall AI
        """
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f'{self.base_url}/desktop/sdk-uploads/{upload_id}/',
                    headers=self.headers
                )
                
                if response.status_code == 200:
                    upload_data = response.json()
                    return {
                        'success': True,
                        'upload_data': upload_data
                    }
                else:
                    logger.error(f"Error fetching SDK upload {upload_id}: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': f'API error: {response.status_code}',
                        'message': 'Failed to fetch SDK upload information'
                    }
                    
        except Exception as e:
            logger.error(f"Error fetching SDK upload {upload_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to fetch SDK upload information'
            }
    
    async def create_async_transcript_for_upload(self, upload_id: str, language: str = 'en') -> Dict[str, Any]:
        """
        Create an async transcript for an SDK upload
        
        Args:
            upload_id: The SDK upload ID
            language: Language code for transcription (default: 'en')
            
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
            
            logger.info(f"Creating async transcript for SDK upload: {upload_id}")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f'{self.base_url}/desktop/sdk-uploads/{upload_id}/create-transcript/',
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
            logger.error(f"Error creating async transcript for upload {upload_id}: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create async transcript due to unexpected error'
            }
    
    def handle_sdk_webhook(self, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle webhook events from the Desktop SDK
        
        Args:
            event_type: The type of webhook event
            payload: The webhook payload
            
        Returns:
            dict: Processing result
        """
        try:
            logger.info(f"Processing SDK webhook event: {event_type}")
            logger.info(f"Payload: {json.dumps(payload, indent=2)}")
            
            if event_type == 'sdk_upload.complete':
                return self._handle_upload_complete(payload)
            elif event_type == 'sdk_upload.failed':
                return self._handle_upload_failed(payload)
            elif event_type == 'transcript.complete':
                return self._handle_transcript_complete(payload)
            else:
                logger.warning(f"Unknown SDK webhook event type: {event_type}")
                return {
                    'success': True,
                    'message': f'Unhandled event type: {event_type}'
                }
                
        except Exception as e:
            logger.error(f"Error processing SDK webhook: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to process SDK webhook'
            }
    
    def _handle_upload_complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sdk_upload.complete webhook event"""
        upload_id = payload.get('data', {}).get('id')
        recording_id = payload.get('data', {}).get('recording_id')
        
        logger.info(f"SDK upload complete - upload_id: {upload_id}, recording_id: {recording_id}")
        
        # Create a meeting session for this desktop recording
        from .models import MeetingSession
        
        try:
            metadata = payload.get('data', {}).get('metadata', {})
            user_id = metadata.get('user_id', 'unknown')
            username = metadata.get('username', 'unknown')
            
            session_data = {
                'user_id': user_id,
                'username': username,
                'platform': metadata.get('platform', 'desktop'),
                'meeting_url': f'desktop://recording/{upload_id}',
                'start_time': datetime.utcnow(),
                'status': 'completed',
                'recording_type': 'desktop_sdk',
                'sdk_upload_id': upload_id,
                'recording_id': recording_id,
                'metadata': metadata
            }
            
            session = MeetingSession.create_session(session_data)
            
            if session.get('success'):
                logger.info(f"Created meeting session for desktop recording: {session.get('session_id')}")
                
                # Trigger async transcription
                if metadata.get('transcription_enabled', True):
                    asyncio.create_task(self._trigger_transcription(upload_id, session.get('session_id')))
                
                return {
                    'success': True,
                    'session_id': session.get('session_id'),
                    'message': 'Desktop recording session created'
                }
            else:
                logger.error(f"Failed to create session: {session.get('error')}")
                return {
                    'success': False,
                    'error': session.get('error'),
                    'message': 'Failed to create meeting session'
                }
                
        except Exception as e:
            logger.error(f"Error creating session for desktop recording: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to create meeting session'
            }
    
    def _handle_upload_failed(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle sdk_upload.failed webhook event"""
        upload_id = payload.get('data', {}).get('id')
        error = payload.get('data', {}).get('error', 'Unknown error')
        
        logger.error(f"SDK upload failed - upload_id: {upload_id}, error: {error}")
        
        return {
            'success': True,
            'message': f'Recorded upload failure for {upload_id}'
        }
    
    def _handle_transcript_complete(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Handle transcript.complete webhook event"""
        transcript_id = payload.get('data', {}).get('id')
        upload_id = payload.get('data', {}).get('sdk_upload_id')
        
        logger.info(f"Transcript complete - transcript_id: {transcript_id}, upload_id: {upload_id}")
        
        # Update the session with transcript data
        from .models import MeetingSession
        
        try:
            # Find session by SDK upload ID
            session = MeetingSession.find_by_sdk_upload_id(upload_id)
            if session:
                MeetingSession.set_transcript_id(session['session_id'], transcript_id)
                logger.info(f"Updated session {session['session_id']} with transcript {transcript_id}")
        except Exception as e:
            logger.error(f"Error updating session with transcript: {str(e)}")
        
        return {
            'success': True,
            'message': 'Transcript complete processed'
        }
    
    async def _trigger_transcription(self, upload_id: str, session_id: str) -> None:
        """Trigger async transcription for a completed upload"""
        try:
            result = await self.create_async_transcript_for_upload(upload_id)
            if result['success']:
                logger.info(f"Transcription triggered for session {session_id}")
            else:
                logger.error(f"Failed to trigger transcription for session {session_id}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error triggering transcription: {str(e)}")


# Synchronous wrappers for Django views

def create_upload_token_sync(metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Synchronous wrapper for creating upload token
    
    First tries Recall AI Desktop SDK, then falls back to S3 pre-signed URL
    """
    recall_error = None
    
    # Try Recall AI Desktop SDK first
    try:
        service = DesktopRecordingService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.create_upload_token(metadata))
            if result.get('success'):
                return result
            else:
                recall_error = result.get('error', 'Unknown error')
                logger.warning(f"Recall AI Desktop SDK failed: {recall_error}, trying S3 fallback")
        finally:
            loop.close()
            
    except Exception as e:
        recall_error = str(e)
        logger.warning(f"Recall AI Desktop SDK exception: {recall_error}, trying S3 fallback")
    
    # Fallback to S3 pre-signed URL
    try:
        logger.info("Using S3 fallback for desktop upload token")
        s3_service = S3UploadTokenService()
        result = s3_service.create_upload_token(metadata)
        
        if result.get('success'):
            logger.info("S3 fallback upload token created successfully")
            return result
        else:
            # Both Recall AI and S3 failed
            logger.error(f"S3 fallback also failed: {result.get('error')}")
            return {
                'success': False,
                'error': f"Recall AI: {recall_error}; S3: {result.get('error')}",
                'message': 'Failed to create upload token (both Recall AI and S3 fallback failed)'
            }
            
    except Exception as e:
        logger.error(f"S3 fallback exception: {str(e)}")
        return {
            'success': False,
            'error': f"Recall AI: {recall_error}; S3: {str(e)}",
            'message': 'Failed to create upload token'
        }


def get_sdk_upload_sync(upload_id: str) -> Dict[str, Any]:
    """Synchronous wrapper for getting SDK upload"""
    try:
        service = DesktopRecordingService()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(service.get_sdk_upload(upload_id))
            return result
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Error in sync wrapper for get_sdk_upload: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to get SDK upload'
        }


def handle_sdk_webhook_sync(event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Synchronous wrapper for handling SDK webhooks"""
    try:
        service = DesktopRecordingService()
        return service.handle_sdk_webhook(event_type, payload)
    except Exception as e:
        logger.error(f"Error in sync wrapper for handle_sdk_webhook: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to handle SDK webhook'
        }
