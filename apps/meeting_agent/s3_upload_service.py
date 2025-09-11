"""
Service for automatically uploading meeting assets to S3 when meetings are completed
"""
import logging
import requests
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from pymongo.mongo_client import MongoClient
from bson import ObjectId

logger = logging.getLogger(__name__)

# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
meeting_sessions_collection = db["meeting_sessions"]

# S3 Configuration
S3_BUCKET_NAME = os.environ.get('AWS_S3_BUCKET_NAME')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
AWS_REGION = os.environ.get('AWS_REGION', 'us-east-1')


class MeetingS3UploadService:
    """Service for uploading meeting assets to S3"""
    
    def __init__(self):
        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=AWS_ACCESS_KEY_ID,
            aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
            region_name=AWS_REGION
        )
    
    def upload_meeting_assets(self, session_id: str) -> Dict[str, Any]:
        """
        Upload meeting video and transcript to S3
        
        Args:
            session_id: The meeting session ID
            
        Returns:
            Dict with upload results
        """
        try:
            logger.info(f"Starting S3 upload for session: {session_id}")
            
            # Get session data
            session = meeting_sessions_collection.find_one({"session_id": session_id})
            if not session:
                return {
                    "success": False,
                    "error": f"Session {session_id} not found"
                }
            
            user_id_str = session.get('user_id')
            if not user_id_str:
                return {
                    "success": False,
                    "error": "No user_id found for session"
                }
            
            # Look up user in database to get ObjectId
            users_collection = db['users']
            user = users_collection.find_one({"username": user_id_str})
            if not user:
                # Try alternative lookups
                user = users_collection.find_one({"email": user_id_str})
                if not user:
                    user = users_collection.find_one({"_id": user_id_str})
                    if not user:
                        logger.error(f"User {user_id_str} not found in database with any lookup method")
                        return {
                            "success": False,
                            "error": f"User {user_id_str} not found in database"
                        }
            
            user_id = user["_id"]  # This is already an ObjectId
            logger.info(f"Found user {user_id_str} with ObjectId {user_id}")
            
            results = {
                "video_upload": None,
                "transcript_upload": None,
                "success": False,
                "errors": []
            }
            
            # Debug: Log session data structure
            logger.info(f"Session data for {session_id}: {json.dumps(session, indent=2, default=str)}")
            
            # Extract URLs from session data
            video_url = (session.get('recall_bot', {}).get('video_url') or 
                        session.get('recall_bot_data', {}).get('video_url') or 
                        session.get('recording_url') or
                        session.get('video_url'))
            
            transcript_url = (session.get('recall_bot', {}).get('transcript_url') or 
                            session.get('recall_bot_data', {}).get('transcript_url') or
                            session.get('transcription_url') or
                            session.get('transcript_url'))
            
            audio_url = (session.get('recall_bot', {}).get('audio_url') or 
                        session.get('recall_bot_data', {}).get('audio_url') or 
                        session.get('audio_url'))
            
            logger.info(f"URLs for session {session_id}: video={bool(video_url)}, transcript={bool(transcript_url)}, audio={bool(audio_url)}")
            
            # Create file records directly in database
            logger.info(f"Creating file records for session {session_id} with user_id {user_id}")
            files_created = self._create_meeting_file_records(session_id, user_id, user_id_str, session, video_url, transcript_url, audio_url)
            logger.info(f"File records creation result: {files_created} files created")
            
            # Update session with file creation status
            s3_update = {
                "s3_upload_completed": True,
                "s3_upload_timestamp": datetime.utcnow(),
                "video_uploaded": bool(video_url),
                "transcript_uploaded": bool(transcript_url),
                "audio_uploaded": bool(audio_url)
            }
            
            meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": s3_update}
            )
            
            logger.info(f"File records created for session {session_id}: {files_created}")
            
            return {
                "success": True,
                "files_created": files_created,
                "video_url": video_url,
                "transcript_url": transcript_url,
                "audio_url": audio_url
            }
            
        except Exception as e:
            logger.error(f"Error uploading meeting assets for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _upload_video_to_s3(self, session_id: str, video_url: str, user_id: str) -> Dict[str, Any]:
        """Create S3 file with Recall AI video URL as content"""
        try:
            # Check if video_url is valid
            if not video_url or video_url.strip() == "":
                return {
                    "success": False,
                    "error": "Video URL is empty or invalid"
                }
            
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            s3_key = f"{user_id}/meetings/{session_id}/recording_{timestamp}.txt"
            
            # Create file content with the video URL
            file_content = f"Meeting Recording URL\n\n{video_url}\n\nThis file contains the direct link to the meeting recording from Recall AI.\nClick the link above to view the video."
            
            logger.info(f"Creating S3 file for video: {s3_key}")
            
            # Create a file with the video URL as content
            self.s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'original-url': video_url,
                    'file-type': 'recall-ai-video-link',
                    'session-id': session_id,
                    'meeting-asset': 'video'
                }
            )
            
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "original_url": video_url,
                "file_size": len(file_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Error creating video file for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _upload_transcript_to_s3(self, session_id: str, transcript_url: Optional[str], 
                                transcript_text: Optional[str], user_id: str) -> Dict[str, Any]:
        """Upload transcript to S3 - create files with URLs or content"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            
            if transcript_url and transcript_url.strip():
                # Create file with transcript URL as content
                file_extension = "json" if transcript_url.endswith('.json') else "txt"
                s3_key = f"{user_id}/meetings/{session_id}/transcript_{timestamp}.{file_extension}"
                
                # Create file content with the transcript URL
                file_content = f"Meeting Transcript URL\n\n{transcript_url}\n\nThis file contains the direct link to the meeting transcript from Recall AI.\nClick the link above to view the transcript."
                
                logger.info(f"Creating S3 file for transcript: {s3_key}")
                
                # Create a file with the transcript URL as content
                self.s3_client.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=file_content.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'original-url': transcript_url,
                        'file-type': 'recall-ai-transcript-link',
                        'session-id': session_id,
                        'meeting-asset': 'transcript'
                    }
                )
                
                s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                
                return {
                    "success": True,
                    "s3_url": s3_url,
                    "s3_key": s3_key,
                    "original_url": transcript_url,
                    "file_size": len(file_content.encode('utf-8'))
                }
                
            elif transcript_text and transcript_text.strip():
                # Store actual transcript text content
                s3_key = f"{user_id}/meetings/{session_id}/transcript_{timestamp}.txt"
                
                logger.info(f"Uploading transcript text to S3: {s3_key}")
                
                self.s3_client.put_object(
                    Bucket=S3_BUCKET_NAME,
                    Key=s3_key,
                    Body=transcript_text.encode('utf-8'),
                    ContentType='text/plain',
                    Metadata={
                        'file-type': 'transcript-text',
                        'session-id': session_id,
                        'meeting-asset': 'transcript'
                    }
                )
                
                s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
                
                return {
                    "success": True,
                    "s3_url": s3_url,
                    "s3_key": s3_key,
                    "file_size": len(transcript_text.encode('utf-8'))
                }
            else:
                return {
                    "success": False,
                    "error": "No transcript content available"
                }
            
        except Exception as e:
            logger.error(f"Error uploading transcript for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _upload_audio_to_s3(self, session_id: str, audio_url: str, user_id: str) -> Dict[str, Any]:
        """Create S3 file with Recall AI audio URL as content"""
        try:
            # Check if audio_url is valid
            if not audio_url or audio_url.strip() == "":
                return {
                    "success": False,
                    "error": "Audio URL is empty or invalid"
                }
            
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            s3_key = f"{user_id}/meetings/{session_id}/audio_{timestamp}.txt"
            
            # Create file content with the audio URL
            file_content = f"Meeting Audio URL\n\n{audio_url}\n\nThis file contains the direct link to the meeting audio from Recall AI.\nClick the link above to listen to the audio."
            
            logger.info(f"Creating S3 file for audio: {s3_key}")
            
            # Create a file with the audio URL as content
            self.s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=file_content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'original-url': audio_url,
                    'file-type': 'recall-ai-audio-link',
                    'session-id': session_id,
                    'meeting-asset': 'audio'
                }
            )
            
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "original_url": audio_url,
                "file_size": len(file_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Error creating audio file for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _create_meeting_file_records(self, session_id: str, user_id: ObjectId, user_id_str: str, session: Dict, video_url: str, transcript_url: str, audio_url: str) -> int:
        """Create file records in database pointing to Recall AI URLs"""
        try:
            # Use the existing MongoDB connection
            files_collection = db['files']
            
            meeting_title = session.get('title', f'Meeting {session_id[:8]}')
            meeting_date = session.get('created_at', datetime.utcnow())
            current_time = datetime.utcnow()
            files_created = 0
            
            # Create video file record
            logger.info(f"Checking video_url: {video_url}")
            if video_url and video_url.strip():
                video_file_record = {
                    "file_name": f"{meeting_title} - Recording.mp4",
                    "file_path": f"meetings/{session_id}/recording.mp4",
                    "file_size": 0,  # We don't know the actual size
                    "s3_url": video_url,  # Point directly to Recall AI URL
                    "s3_key": f"meetings/{user_id_str}/{session_id}/recording.mp4",
                    "content_type": "video/mp4",
                    "user_id": user_id,
                    "date_uploaded": current_time,
                    "date_modified": current_time,
                    "file_type": "meeting_recording",
                    "original_device": "meeting-agent",
                    "meeting_session_id": session_id,
                    "original_url": video_url,
                    "metadata": {
                        "meeting_asset": "video",
                        "session_id": session_id,
                        "meeting_title": meeting_title,
                        "recall_ai_url": video_url
                    }
                }
                # Insert the file record (MongoDB will generate _id automatically)
                files_collection.insert_one(video_file_record)
                files_created += 1
                logger.info(f"Created video file record for session {session_id}")
            
            # Create transcript file record
            logger.info(f"Checking transcript_url: {transcript_url}")
            if transcript_url and transcript_url.strip():
                transcript_file_record = {
                    "file_name": f"{meeting_title} - Transcript.json",
                    "file_path": f"meetings/{user_id_str}/{session_id}/transcript.json",
                    "file_size": 0,  # We don't know the actual size
                    "s3_url": transcript_url,  # Point directly to Recall AI URL
                    "s3_key": f"meetings/{user_id_str}/{session_id}/transcript.json",
                    "content_type": "application/json",
                    "user_id": user_id,
                    "date_uploaded": current_time,
                    "date_modified": current_time,
                    "file_type": "meeting_transcript",
                    "original_device": "web-editor",
                    "meeting_session_id": session_id,
                    "original_url": transcript_url,
                    "metadata": {
                        "meeting_asset": "transcript",
                        "session_id": session_id,
                        "meeting_title": meeting_title,
                        "recall_ai_url": transcript_url
                    }
                }
                # Insert the file record (MongoDB will generate _id automatically)
                files_collection.insert_one(transcript_file_record)
                files_created += 1
                logger.info(f"Created transcript file record for session {session_id}")
            
            # Create audio file record
            logger.info(f"Checking audio_url: {audio_url}")
            if audio_url and audio_url.strip():
                audio_file_record = {
                    "file_name": f"{meeting_title} - Audio.mp3",
                    "file_path": f"meetings/{user_id_str}/{session_id}/audio.mp3",
                    "file_size": 0,  # We don't know the actual size
                    "s3_url": audio_url,  # Point directly to Recall AI URL
                    "s3_key": f"meetings/{user_id_str}/{session_id}/audio.mp3",
                    "content_type": "audio/mpeg",
                    "user_id": user_id,
                    "date_uploaded": current_time,
                    "date_modified": current_time,
                    "file_type": "meeting_audio",
                    "original_device": "meeting-agent",
                    "meeting_session_id": session_id,
                    "original_url": audio_url,
                    "metadata": {
                        "meeting_asset": "audio",
                        "session_id": session_id,
                        "meeting_title": meeting_title,
                        "recall_ai_url": audio_url
                    }
                }
                # Insert the file record (MongoDB will generate _id automatically)
                files_collection.insert_one(audio_file_record)
                files_created += 1
                logger.info(f"Created audio file record for session {session_id}")
            
            return files_created
            
        except Exception as e:
            logger.error(f"Error creating meeting file records: {str(e)}")
            return 0

    def _register_meeting_files_in_db(self, session_id: str, user_id: ObjectId, user_id_str: str, results: Dict[str, Any]) -> None:
        """Register meeting files in the database for LeftPanel visibility"""
        try:
            # Use the existing MongoDB connection
            files_collection = db['files']
            
            # Get session info for file naming
            meeting_sessions_collection = db['meeting_sessions']
            session = meeting_sessions_collection.find_one({"session_id": session_id})
            if not session:
                logger.error(f"Session {session_id} not found for file registration")
                return
            
            meeting_title = session.get('title', f'Meeting {session_id[:8]}')
            meeting_date = session.get('created_at', datetime.utcnow())
            
            # Register video file
            if results.get("video_upload", {}).get("success"):
                video_result = results["video_upload"]
                video_file_record = {
                    "file_name": f"{meeting_title} - Recording.txt",
                    "file_path": f"meetings/{user_id_str}/{session_id}/recording.txt",
                    "file_size": video_result.get("file_size", 0),
                    "s3_url": video_result["s3_url"],
                    "s3_key": video_result["s3_key"],
                    "content_type": "text/plain",
                    "user_id": user_id,
                    "date_uploaded": datetime.utcnow(),
                    "date_modified": datetime.utcnow(),
                    "file_type": "meeting_recording",
                    "original_device": "meeting-agent",
                    "meeting_session_id": session_id,
                    "original_url": video_result.get("original_url"),
                    "metadata": {
                        "meeting_asset": "video",
                        "session_id": session_id,
                        "meeting_title": meeting_title
                    }
                }
                # Insert the file record (MongoDB will generate _id automatically)
                files_collection.insert_one(video_file_record)
                logger.info(f"Registered video file for session {session_id}")
            
            # Register transcript file
            if results.get("transcript_upload", {}).get("success"):
                transcript_result = results["transcript_upload"]
                transcript_file_record = {
                    "file_name": f"{meeting_title} - Transcript.txt",
                    "file_path": f"meetings/{user_id_str}/{session_id}/transcript.txt",
                    "file_size": transcript_result.get("file_size", 0),
                    "s3_url": transcript_result["s3_url"],
                    "s3_key": transcript_result["s3_key"],
                    "content_type": "text/plain",
                    "user_id": user_id,
                    "date_uploaded": datetime.utcnow(),
                    "date_modified": datetime.utcnow(),
                    "file_type": "meeting_transcript",
                    "original_device": "meeting-agent",
                    "meeting_session_id": session_id,
                    "original_url": transcript_result.get("original_url"),
                    "metadata": {
                        "meeting_asset": "transcript",
                        "session_id": session_id,
                        "meeting_title": meeting_title
                    }
                }
                # Insert the file record (MongoDB will generate _id automatically)
                files_collection.insert_one(transcript_file_record)
                logger.info(f"Registered transcript file for session {session_id}")
            
            # Register audio file
            if results.get("audio_upload", {}).get("success"):
                audio_result = results["audio_upload"]
                audio_file_record = {
                    "file_name": f"{meeting_title} - Audio.txt",
                    "file_path": f"meetings/{user_id_str}/{session_id}/audio.txt",
                    "file_size": audio_result.get("file_size", 0),
                    "s3_url": audio_result["s3_url"],
                    "s3_key": audio_result["s3_key"],
                    "content_type": "text/plain",
                    "user_id": user_id,
                    "date_uploaded": datetime.utcnow(),
                    "date_modified": datetime.utcnow(),
                    "file_type": "meeting_audio",
                    "original_device": "meeting-agent",
                    "meeting_session_id": session_id,
                    "original_url": audio_result.get("original_url"),
                    "metadata": {
                        "meeting_asset": "audio",
                        "session_id": session_id,
                        "meeting_title": meeting_title
                    }
                }
                # Insert the file record (MongoDB will generate _id automatically)
                files_collection.insert_one(audio_file_record)
                logger.info(f"Registered audio file for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error registering meeting files in database: {str(e)}")


# Global instance
s3_upload_service = MeetingS3UploadService()


def trigger_s3_upload_for_completed_meeting(session_id: str) -> Dict[str, Any]:
    """
    Trigger S3 upload for a completed meeting session
    This function should be called when a meeting status changes to 'completed'
    """
    try:
        logger.info(f"Triggering S3 upload for completed meeting: {session_id}")
        result = s3_upload_service.upload_meeting_assets(session_id)
        
        if result["success"]:
            logger.info(f"S3 upload successful for session {session_id}")
        else:
            logger.error(f"S3 upload failed for session {session_id}: {result.get('errors', [])}")
        
        return result
        
    except Exception as e:
        logger.error(f"Error triggering S3 upload for session {session_id}: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }
