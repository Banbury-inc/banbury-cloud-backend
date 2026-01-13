from pymongo.mongo_client import MongoClient
from bson import ObjectId
from datetime import datetime, date
import uuid
import os
import logging

logger = logging.getLogger(__name__)

# MongoDB connection - following the existing pattern
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]

# Meeting Agent Collections
meeting_platforms_collection = db["meeting_platforms"]
meeting_sessions_collection = db["meeting_sessions"]
meeting_configs_collection = db["meeting_agent_configs"]
meeting_status_collection = db["meeting_agent_status"]


class MeetingPlatform:
    """Model for meeting platforms"""
    
    @staticmethod
    def get_all():
        """Get all meeting platforms"""
        try:
            platforms = list(meeting_platforms_collection.find())
            for platform in platforms:
                platform["_id"] = str(platform["_id"])
            return {
                "success": True,
                "platforms": platforms
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_by_id(platform_id):
        """Get platform by ID"""
        try:
            platform = meeting_platforms_collection.find_one({"platform_id": platform_id})
            if platform:
                platform["_id"] = str(platform["_id"])
                return {
                    "success": True,
                    "platform": platform
                }
            return {
                "success": False,
                "error": "Platform not found"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def create_platform(platform_data):
        """Create a new platform"""
        try:
            platform_data["created_at"] = datetime.utcnow()
            result = meeting_platforms_collection.insert_one(platform_data)
            return {
                "success": True,
                "platform_id": str(result.inserted_id),
                "message": "Platform created successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def update_platform(platform_id, update_data):
        """Update platform"""
        try:
            result = meeting_platforms_collection.update_one(
                {"platform_id": platform_id},
                {"$set": update_data}
            )
            return {
                "success": result.modified_count > 0,
                "message": "Platform updated successfully" if result.modified_count > 0 else "No changes made"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class MeetingSession:
    """Model for meeting sessions"""
    
    @staticmethod
    def create_session(session_data):
        """Create a new meeting session"""
        try:
            session_data["session_id"] = str(uuid.uuid4())
            session_data["created_at"] = datetime.utcnow()
            session_data["updated_at"] = datetime.utcnow()
            session_data.setdefault("participants", [])
            session_data.setdefault("transcription_segments", [])
            session_data.setdefault("metadata", {})
            session_data.setdefault("s3_upload", {
                "video_uploaded": False,
                "transcript_uploaded": False,
                "audio_uploaded": False,
                "upload_attempted": False,
                "last_upload_attempt": None,
                "upload_errors": []
            })
            
            result = meeting_sessions_collection.insert_one(session_data)
            
            return {
                "success": True,
                "session_id": session_data["session_id"],
                "message": "Session created successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_session(session_id, user_id=None):
        """Get session by ID"""
        try:
            query = {"session_id": session_id}
            if user_id:
                query["user_id"] = user_id
                
            session = meeting_sessions_collection.find_one(query)
            
            if not session:
                return {
                    "success": False,
                    "error": "Session not found"
                }
            
            session["_id"] = str(session["_id"])
            if "created_at" in session and hasattr(session["created_at"], "isoformat"):
                session["created_at"] = session["created_at"].isoformat()
            if "updated_at" in session and hasattr(session["updated_at"], "isoformat"):
                session["updated_at"] = session["updated_at"].isoformat()
            
            return {
                "success": True,
                "session": session
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_user_sessions(user_id, status=None, limit=50, offset=0):
        """Get sessions for a user"""
        try:
            query = {"user_id": user_id}
            if status:
                query["status"] = status
            
            sessions = list(meeting_sessions_collection.find(query)
                          .sort("start_time", -1)
                          .skip(offset)
                          .limit(limit))
            
            total = meeting_sessions_collection.count_documents(query)
            
            # Convert ObjectIds to strings
            for session in sessions:
                session["_id"] = str(session["_id"])
                if "created_at" in session and hasattr(session["created_at"], "isoformat"):
                    session["created_at"] = session["created_at"].isoformat()
                if "updated_at" in session and hasattr(session["updated_at"], "isoformat"):
                    session["updated_at"] = session["updated_at"].isoformat()
            
            return {
                "success": True,
                "sessions": sessions,
                "total": total,
                "has_more": offset + limit < total
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_all_sessions():
        """Get all sessions (for webhook processing)"""
        try:
            sessions = list(meeting_sessions_collection.find().sort("start_time", -1))
            
            # Convert ObjectIds to strings
            for session in sessions:
                session["_id"] = str(session["_id"])
                if "created_at" in session and hasattr(session["created_at"], "isoformat"):
                    session["created_at"] = session["created_at"].isoformat()
                if "updated_at" in session and hasattr(session["updated_at"], "isoformat"):
                    session["updated_at"] = session["updated_at"].isoformat()
            
            return {
                "success": True,
                "sessions": sessions
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def update_session(session_id, update_data):
        """Update session"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Session updated successfully" if result.modified_count > 0 else "No changes made"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_session(session_id, user_id):
        """Delete session"""
        try:
            result = meeting_sessions_collection.delete_one({
                "session_id": session_id,
                "user_id": user_id
            })
            
            return {
                "success": result.deleted_count > 0,
                "message": "Session deleted successfully" if result.deleted_count > 0 else "Session not found"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def add_participant(session_id, participant_data):
        """Add participant to session"""
        try:
            participant_data["participant_id"] = str(uuid.uuid4())
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"participants": participant_data},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Participant added successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def add_transcription_segment(session_id, segment_data):
        """Add transcription segment to session"""
        try:
            segment_data["segment_id"] = str(uuid.uuid4())
            segment_data["created_at"] = datetime.utcnow()
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"transcription_segments": segment_data},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Transcription segment added successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def set_summary(session_id, summary_data):
        """Set summary for session"""
        try:
            summary_data["summary_id"] = str(uuid.uuid4())
            summary_data["generated_at"] = datetime.utcnow()
            
            # Initialize action items if not present
            if "action_items" not in summary_data:
                summary_data["action_items"] = []
            
            # Add IDs to action items
            for item in summary_data["action_items"]:
                if "action_id" not in item:
                    item["action_id"] = str(uuid.uuid4())
                    item["created_at"] = datetime.utcnow()
                    item["updated_at"] = datetime.utcnow()
            
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "summary": summary_data,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Summary set successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_active_count():
        """Get count of active sessions"""
        try:
            count = meeting_sessions_collection.count_documents({
                "status": {"$in": ["active", "recording", "joining"]}
            })
            return {
                "success": True,
                "count": count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_today_count():
        """Get count of sessions started today"""
        try:
            today_start = datetime.combine(date.today(), datetime.min.time())
            today_end = datetime.combine(date.today(), datetime.max.time())
            
            count = meeting_sessions_collection.count_documents({
                "start_time": {"$gte": today_start, "$lte": today_end}
            })
            
            return {
                "success": True,
                "count": count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_sessions_needing_s3_upload(limit=50):
        """Get sessions that need S3 upload"""
        try:
            # Find sessions that are completed but haven't been uploaded to S3
            query = {
                "status": {"$in": ["completed", "ended"]},
                "$or": [
                    {"s3_upload.video_uploaded": False},
                    {"s3_upload.transcript_uploaded": False},
                    {"s3_upload.audio_uploaded": False}
                ]
            }
            
            sessions = list(meeting_sessions_collection.find(query)
                          .sort("updated_at", -1)
                          .limit(limit))
            
            # Convert ObjectIds to strings
            for session in sessions:
                session["_id"] = str(session["_id"])
                if "created_at" in session and hasattr(session["created_at"], "isoformat"):
                    session["created_at"] = session["created_at"].isoformat()
                if "updated_at" in session and hasattr(session["updated_at"], "isoformat"):
                    session["updated_at"] = session["updated_at"].isoformat()
            
            return {
                "success": True,
                "sessions": sessions,
                "count": len(sessions)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def update_s3_upload_status(session_id, upload_data):
        """Update S3 upload status for a session"""
        try:
            update_data = {
                "s3_upload": upload_data,
                "updated_at": datetime.utcnow()
            }
            
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": update_data}
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "S3 upload status updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def find_by_sdk_upload_id(sdk_upload_id):
        """Find a session by SDK upload ID (for desktop recordings)"""
        try:
            session = meeting_sessions_collection.find_one({"sdk_upload_id": sdk_upload_id})
            
            if not session:
                return None
            
            session["_id"] = str(session["_id"])
            if "created_at" in session and hasattr(session["created_at"], "isoformat"):
                session["created_at"] = session["created_at"].isoformat()
            if "updated_at" in session and hasattr(session["updated_at"], "isoformat"):
                session["updated_at"] = session["updated_at"].isoformat()
            
            return session
        except Exception as e:
            logger.error(f"Error finding session by SDK upload ID: {str(e)}")
            return None
    
    @staticmethod
    def set_transcript_id(session_id, transcript_id):
        """Set the transcript ID for a session"""
        try:
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "transcript_id": transcript_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Transcript ID set successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def mark_s3_upload_attempted(session_id, error_message=None):
        """Mark that S3 upload was attempted for a session"""
        try:
            update_data = {
                "s3_upload.upload_attempted": True,
                "s3_upload.last_upload_attempt": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            if error_message:
                update_data["$push"] = {"s3_upload.upload_errors": {
                    "error": error_message,
                    "timestamp": datetime.utcnow()
                }}
            
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": update_data} if not error_message else {"$set": update_data, "$push": update_data["$push"]}
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "S3 upload attempt marked"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def find_by_bot_id(bot_id):
        """Find a session by Recall AI bot ID"""
        try:
            # Try different field locations for bot_id
            session = meeting_sessions_collection.find_one({
                "$or": [
                    {"recall_bot_id": bot_id},
                    {"bot_id": bot_id},
                    {"metadata.bot_id": bot_id},
                    {"recall_bot.id": bot_id}
                ]
            })
            
            if not session:
                return None
            
            session["_id"] = str(session["_id"])
            if "created_at" in session and hasattr(session["created_at"], "isoformat"):
                session["created_at"] = session["created_at"].isoformat()
            if "updated_at" in session and hasattr(session["updated_at"], "isoformat"):
                session["updated_at"] = session["updated_at"].isoformat()
            
            return session
        except Exception as e:
            logger.error(f"Error finding session by bot ID {bot_id}: {str(e)}")
            return None
    
    @staticmethod
    def update_status(session_id, status):
        """Update session status"""
        try:
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "status": status,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": f"Status updated to {status}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def set_recording_id(session_id, recording_id):
        """Set the recording ID for a session"""
        try:
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "recording_id": recording_id,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Recording ID set successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def add_live_transcript_segment(session_id, segment):
        """Add a live transcript segment during real-time transcription"""
        try:
            segment["added_at"] = datetime.utcnow().isoformat()
            
            result = meeting_sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"live_transcript_segments": segment},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Live transcript segment added"
            }
        except Exception as e:
            logger.error(f"Error adding live transcript segment: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_live_transcript_segments(session_id):
        """Get all live transcript segments for a session"""
        try:
            session = meeting_sessions_collection.find_one(
                {"session_id": session_id},
                {"live_transcript_segments": 1}
            )
            
            if session and "live_transcript_segments" in session:
                return session["live_transcript_segments"]
            
            return []
        except Exception as e:
            logger.error(f"Error getting live transcript segments: {str(e)}")
            return []


class MeetingAgentConfig:
    """Model for meeting agent configuration"""
    
    @staticmethod
    def get_or_create_config(user_id, username):
        """Get or create config for user"""
        try:
            config = meeting_configs_collection.find_one({"user_id": user_id})
            
            if not config:
                config = {
                    "user_id": user_id,
                    "username": username,
                    "name": "Meeting Agent",
                    "bot_name": "Meeting Recorder",
                    "profile_picture_url": "",
                    "default_settings": {
                        "recording_enabled": True,
                        "transcription_enabled": True,
                        "summary_enabled": True,
                        "action_items_enabled": True,
                        "language": "en",
                        "quality": "high",
                        "auto_join": False,
                        "auto_leave": True,
                        "max_duration": 120
                    },
                    "notification_settings": {
                        "email_notifications": True,
                        "slack_notifications": False,
                        "webhook_notifications": False,
                        "summary_delivery": "immediate"
                    },
                    "api_credentials": {},
                    "webhook_url": "",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                result = meeting_configs_collection.insert_one(config)
                config["_id"] = str(result.inserted_id)
            else:
                config["_id"] = str(config["_id"])
                
                # Ensure new fields exist in old configs (migration logic)
                needs_update = False
                updates = {}
                
                if "bot_name" not in config:
                    updates["bot_name"] = "Meeting Recorder"
                    needs_update = True
                    
                if "profile_picture_url" not in config:
                    updates["profile_picture_url"] = ""
                    needs_update = True
                
                # Update existing config with missing fields
                if needs_update:
                    meeting_configs_collection.update_one(
                        {"user_id": user_id},
                        {"$set": updates}
                    )
                    config.update(updates)
            
            return {
                "success": True,
                "config": config
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def update_config(user_id, update_data):
        """Update config"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = meeting_configs_collection.update_one(
                {"user_id": user_id},
                {"$set": update_data}
            )
            
            # Consider it successful if the document was matched (even if not modified)
            # This handles cases where values are the same
            return {
                "success": result.matched_count > 0,
                "message": "Configuration updated successfully" if result.matched_count > 0 else "Configuration not found"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


class MeetingAgentStatus:
    """Model for meeting agent status"""
    
    @staticmethod
    def get_or_create_status():
        """Get or create global status"""
        try:
            status = meeting_status_collection.find_one({"status_id": "global_status"})
            
            if not status:
                status = {
                    "status_id": "global_status",
                    "is_online": True,
                    "active_connections": 0,
                    "total_meetings_today": 0,
                    "total_recording_time": 0,
                    "last_activity": None,
                    "system_health": "healthy",
                    "updated_at": datetime.utcnow()
                }
                result = meeting_status_collection.insert_one(status)
                status["_id"] = str(result.inserted_id)
            else:
                status["_id"] = str(status["_id"])
            
            return {
                "success": True,
                "status": status
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def update_status(update_data):
        """Update status"""
        try:
            update_data["updated_at"] = datetime.utcnow()
            result = meeting_status_collection.update_one(
                {"status_id": "global_status"},
                {"$set": update_data}
            )
            
            return {
                "success": result.modified_count > 0,
                "message": "Status updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# Helper functions
def get_user_id_from_django_user(user):
    """Convert Django User to string ID"""
    return str(user.id)


def get_username_from_django_user(user):
    """Get username from Django User"""
    return user.username


def initialize_meeting_platforms():
    """Initialize default meeting platforms"""
    platforms = [
        {
            "platform_id": "zoom",
            "name": "Zoom",
            "icon": "🎥",
            "supported": True,
            "auth_required": True
        },
        {
            "platform_id": "teams",
            "name": "Microsoft Teams",
            "icon": "💼",
            "supported": True,
            "auth_required": True
        },
        {
            "platform_id": "meet",
            "name": "Google Meet",
            "icon": "📞",
            "supported": True,
            "auth_required": True
        },
        {
            "platform_id": "webex",
            "name": "Cisco Webex",
            "icon": "🎦",
            "supported": False,  # Coming soon
            "auth_required": True
        }
    ]
    
    for platform_data in platforms:
        try:
            existing = MeetingPlatform.get_by_id(platform_data["platform_id"])
            if not existing["success"]:
                result = MeetingPlatform.create_platform(platform_data)
                print(f"Created platform: {platform_data['name']} - {result['message']}")
            else:
                # Update existing platform
                update_data = {k: v for k, v in platform_data.items() if k != "platform_id"}
                result = MeetingPlatform.update_platform(platform_data["platform_id"], update_data)
                print(f"Updated platform: {platform_data['name']} - {result['message']}")
        except Exception as e:
            print(f"Error creating/updating platform {platform_data['platform_id']}: {e}")


def get_duration_minutes(duration_seconds):
    """Convert duration from seconds to minutes"""
    if duration_seconds:
        return duration_seconds // 60
    return 0