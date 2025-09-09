from pymongo.mongo_client import MongoClient
from bson import ObjectId
from datetime import datetime, date
import uuid
import os

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
            
            return {
                "success": result.modified_count > 0,
                "message": "Configuration updated successfully"
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