"""
Service for automatically uploading meeting assets to S3 when meetings are completed
"""
import logging
import requests
import os
from typing import Dict, Any, Optional
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from pymongo.mongo_client import MongoClient

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
            
            user_id = session.get('user_id')
            if not user_id:
                return {
                    "success": False,
                    "error": "No user_id found for session"
                }
            
            results = {
                "video_upload": None,
                "transcript_upload": None,
                "success": False,
                "errors": []
            }
            
            # Upload video if available
            video_url = session.get('recall_bot', {}).get('video_url') or session.get('recording_url')
            if video_url:
                logger.info(f"Uploading video for session {session_id}")
                video_result = self._upload_video_to_s3(session_id, video_url, user_id)
                results["video_upload"] = video_result
                if not video_result["success"]:
                    results["errors"].append(f"Video upload failed: {video_result['error']}")
            else:
                logger.info(f"No video URL found for session {session_id}")
            
            # Upload transcript if available
            transcript_url = session.get('recall_bot', {}).get('transcript_url')
            transcript_text = session.get('transcription_text')
            if transcript_url or transcript_text:
                logger.info(f"Uploading transcript for session {session_id}")
                transcript_result = self._upload_transcript_to_s3(session_id, transcript_url, transcript_text, user_id)
                results["transcript_upload"] = transcript_result
                if not transcript_result["success"]:
                    results["errors"].append(f"Transcript upload failed: {transcript_result['error']}")
            else:
                logger.info(f"No transcript found for session {session_id}")
            
            # Determine overall success
            has_any_success = (
                (results["video_upload"] and results["video_upload"]["success"]) or
                (results["transcript_upload"] and results["transcript_upload"]["success"])
            )
            
            results["success"] = has_any_success
            
            if results["success"]:
                # Update session with S3 URLs
                s3_update = {}
                if results["video_upload"] and results["video_upload"]["success"]:
                    s3_update["s3_video_url"] = results["video_upload"]["s3_url"]
                if results["transcript_upload"] and results["transcript_upload"]["success"]:
                    s3_update["s3_transcript_url"] = results["transcript_upload"]["s3_url"]
                
                s3_update["s3_upload_completed"] = True
                s3_update["s3_upload_timestamp"] = datetime.utcnow()
                
                meeting_sessions_collection.update_one(
                    {"session_id": session_id},
                    {"$set": s3_update}
                )
                
                logger.info(f"S3 upload completed for session {session_id}")
            else:
                logger.error(f"S3 upload failed for session {session_id}: {results['errors']}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error uploading meeting assets for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _upload_video_to_s3(self, session_id: str, video_url: str, user_id: str) -> Dict[str, Any]:
        """Upload video file to S3"""
        try:
            # Download video from URL
            logger.info(f"Downloading video from: {video_url}")
            response = requests.get(video_url, stream=True)
            response.raise_for_status()
            
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            s3_key = f"{user_id}/meetings/{session_id}/recording_{timestamp}.mp4"
            
            # Upload to S3
            logger.info(f"Uploading video to S3: {s3_key}")
            self.s3_client.upload_fileobj(
                response.raw,
                S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={
                    'ContentType': 'video/mp4'
                }
            )
            
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "file_size": response.headers.get('content-length', 0)
            }
            
        except Exception as e:
            logger.error(f"Error uploading video for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _upload_transcript_to_s3(self, session_id: str, transcript_url: Optional[str], 
                                transcript_text: Optional[str], user_id: str) -> Dict[str, Any]:
        """Upload transcript to S3"""
        try:
            transcript_content = None
            file_extension = "txt"
            
            if transcript_url:
                # Download transcript from URL
                logger.info(f"Downloading transcript from: {transcript_url}")
                response = requests.get(transcript_url)
                response.raise_for_status()
                transcript_content = response.text
                file_extension = "json" if transcript_url.endswith('.json') else "txt"
            elif transcript_text:
                # Use existing transcript text
                transcript_content = transcript_text
                file_extension = "txt"
            else:
                return {
                    "success": False,
                    "error": "No transcript content available"
                }
            
            # Generate S3 key
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            s3_key = f"{user_id}/meetings/{session_id}/transcript_{timestamp}.{file_extension}"
            
            # Upload to S3
            logger.info(f"Uploading transcript to S3: {s3_key}")
            self.s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=transcript_content.encode('utf-8'),
                ContentType='text/plain' if file_extension == 'txt' else 'application/json'
            )
            
            s3_url = f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{s3_key}"
            
            return {
                "success": True,
                "s3_url": s3_url,
                "s3_key": s3_key,
                "file_size": len(transcript_content.encode('utf-8'))
            }
            
        except Exception as e:
            logger.error(f"Error uploading transcript for session {session_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }


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
