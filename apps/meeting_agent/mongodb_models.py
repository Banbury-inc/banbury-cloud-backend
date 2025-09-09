"""
MongoDB models using PyMongo for meeting agent functionality
"""
from pymongo import MongoClient
from django.conf import settings
import uuid
import os
from datetime import datetime, date
from typing import Dict, Any, List, Optional

# MongoDB connection
def get_mongodb_client():
    """Get MongoDB client connection"""
    mongodb_uri = os.environ.get('MONGODB_URI')
    if mongodb_uri:
        client = MongoClient(mongodb_uri)
    else:
        host = os.environ.get('MONGODB_HOST', 'localhost')
        port = int(os.environ.get('MONGODB_PORT', 27017))
        username = os.environ.get('MONGODB_USERNAME')
        password = os.environ.get('MONGODB_PASSWORD')
        
        if username and password:
            client = MongoClient(host, port, username=username, password=password)
        else:
            client = MongoClient(host, port)
    
    return client

def get_meeting_db():
    """Get meeting database"""
    client = get_mongodb_client()
    db_name = os.environ.get('MONGODB_DB', 'banbury_meetings')
    return client[db_name]


class MeetingPlatformManager:
    """Manager for meeting platforms collection"""
    
    def __init__(self):
        self.db = get_meeting_db()
        self.collection = self.db.meeting_platforms
        
        # Create indexes
        try:
            self.collection.create_index("platform_id", unique=True)
            self.collection.create_index("supported")
        except Exception:
            pass  # Indexes may already exist
    
    def create(self, platform_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new platform"""
        platform_data['created_at'] = datetime.utcnow()
        result = self.collection.insert_one(platform_data)
        platform_data['_id'] = result.inserted_id
        return platform_data
    
    def get_by_id(self, platform_id: str) -> Optional[Dict[str, Any]]:
        """Get platform by ID"""
        return self.collection.find_one({"platform_id": platform_id})
    
    def get_all(self) -> List[Dict[str, Any]]:
        """Get all platforms"""
        return list(self.collection.find())
    
    def get_supported(self) -> List[Dict[str, Any]]:
        """Get all supported platforms"""
        return list(self.collection.find({"supported": True}))
    
    def update(self, platform_id: str, update_data: Dict[str, Any]) -> bool:
        """Update platform"""
        result = self.collection.update_one(
            {"platform_id": platform_id},
            {"$set": update_data}
        )
        return result.modified_count > 0


class MeetingSessionManager:
    """Manager for meeting sessions collection"""
    
    def __init__(self):
        self.db = get_meeting_db()
        self.collection = self.db.meeting_sessions
        
        # Create indexes
        try:
            self.collection.create_index("session_id", unique=True)
            self.collection.create_index("user_id")
            self.collection.create_index("username")
            self.collection.create_index("status")
            self.collection.create_index("start_time")
            self.collection.create_index([("user_id", 1), ("start_time", -1)])
            self.collection.create_index([("status", 1), ("start_time", 1)])
        except Exception:
            pass  # Indexes may already exist
    
    def create(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session"""
        if 'session_id' not in session_data:
            session_data['session_id'] = str(uuid.uuid4())
        
        session_data['created_at'] = datetime.utcnow()
        session_data['updated_at'] = datetime.utcnow()
        
        # Initialize empty arrays for embedded documents
        session_data.setdefault('participants', [])
        session_data.setdefault('transcription_segments', [])
        session_data.setdefault('metadata', {})
        
        result = self.collection.insert_one(session_data)
        session_data['_id'] = result.inserted_id
        return session_data
    
    def get_by_id(self, session_id: str, user_id: str = None) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        query = {"session_id": session_id}
        if user_id:
            query["user_id"] = user_id
        return self.collection.find_one(query)
    
    def get_by_user(self, user_id: str, status: str = None, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get sessions by user"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        
        return list(self.collection.find(query)
                   .sort("start_time", -1)
                   .skip(offset)
                   .limit(limit))
    
    def count_by_user(self, user_id: str, status: str = None) -> int:
        """Count sessions by user"""
        query = {"user_id": user_id}
        if status:
            query["status"] = status
        return self.collection.count_documents(query)
    
    def update(self, session_id: str, update_data: Dict[str, Any]) -> bool:
        """Update session"""
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {"session_id": session_id},
            {"$set": update_data}
        )
        return result.modified_count > 0
    
    def delete(self, session_id: str, user_id: str) -> bool:
        """Delete session"""
        result = self.collection.delete_one({
            "session_id": session_id,
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    def add_participant(self, session_id: str, participant_data: Dict[str, Any]) -> bool:
        """Add participant to session"""
        participant_data['participant_id'] = str(uuid.uuid4())
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"participants": participant_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    def add_transcription_segment(self, session_id: str, segment_data: Dict[str, Any]) -> bool:
        """Add transcription segment to session"""
        segment_data['segment_id'] = str(uuid.uuid4())
        segment_data['created_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$push": {"transcription_segments": segment_data},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        return result.modified_count > 0
    
    def set_summary(self, session_id: str, summary_data: Dict[str, Any]) -> bool:
        """Set summary for session"""
        summary_data['summary_id'] = str(uuid.uuid4())
        summary_data['generated_at'] = datetime.utcnow()
        
        # Initialize action items if not present
        if 'action_items' not in summary_data:
            summary_data['action_items'] = []
        
        # Add IDs to action items
        for item in summary_data['action_items']:
            if 'action_id' not in item:
                item['action_id'] = str(uuid.uuid4())
                item['created_at'] = datetime.utcnow()
                item['updated_at'] = datetime.utcnow()
        
        result = self.collection.update_one(
            {"session_id": session_id},
            {
                "$set": {
                    "summary": summary_data,
                    "updated_at": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
    def get_active_count(self) -> int:
        """Get count of active sessions"""
        return self.collection.count_documents({
            "status": {"$in": ["active", "recording", "joining"]}
        })
    
    def get_today_count(self) -> int:
        """Get count of sessions started today"""
        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = datetime.combine(date.today(), datetime.max.time())
        
        return self.collection.count_documents({
            "start_time": {"$gte": today_start, "$lte": today_end}
        })


class MeetingAgentConfigManager:
    """Manager for meeting agent configurations collection"""
    
    def __init__(self):
        self.db = get_meeting_db()
        self.collection = self.db.meeting_agent_configs
        
        # Create indexes
        try:
            self.collection.create_index("user_id", unique=True)
            self.collection.create_index("username")
        except Exception:
            pass
    
    def get_or_create(self, user_id: str, username: str) -> Dict[str, Any]:
        """Get or create config for user"""
        config = self.collection.find_one({"user_id": user_id})
        
        if not config:
            config = {
                'user_id': user_id,
                'username': username,
                'name': 'Meeting Agent',
                'default_settings': {
                    'recording_enabled': True,
                    'transcription_enabled': True,
                    'summary_enabled': True,
                    'action_items_enabled': True,
                    'language': 'en',
                    'quality': 'high',
                    'auto_join': False,
                    'auto_leave': True,
                    'max_duration': 120
                },
                'notification_settings': {
                    'email_notifications': True,
                    'slack_notifications': False,
                    'webhook_notifications': False,
                    'summary_delivery': 'immediate'
                },
                'api_credentials': {},
                'webhook_url': '',
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            }
            result = self.collection.insert_one(config)
            config['_id'] = result.inserted_id
        
        return config
    
    def update(self, user_id: str, update_data: Dict[str, Any]) -> bool:
        """Update config"""
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
        return result.modified_count > 0


class MeetingAgentStatusManager:
    """Manager for meeting agent status collection"""
    
    def __init__(self):
        self.db = get_meeting_db()
        self.collection = self.db.meeting_agent_status
    
    def get_or_create(self) -> Dict[str, Any]:
        """Get or create global status"""
        status = self.collection.find_one({"status_id": "global_status"})
        
        if not status:
            status = {
                'status_id': 'global_status',
                'is_online': True,
                'active_connections': 0,
                'total_meetings_today': 0,
                'total_recording_time': 0,
                'last_activity': None,
                'system_health': 'healthy',
                'updated_at': datetime.utcnow()
            }
            result = self.collection.insert_one(status)
            status['_id'] = result.inserted_id
        
        return status
    
    def update(self, update_data: Dict[str, Any]) -> bool:
        """Update status"""
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {"status_id": "global_status"},
            {"$set": update_data}
        )
        return result.modified_count > 0


# Manager instances
meeting_platforms = MeetingPlatformManager()
meeting_sessions = MeetingSessionManager()
meeting_configs = MeetingAgentConfigManager()
meeting_status = MeetingAgentStatusManager()


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
            'platform_id': 'zoom',
            'name': 'Zoom',
            'icon': '🎥',
            'supported': True,
            'auth_required': True
        },
        {
            'platform_id': 'teams',
            'name': 'Microsoft Teams',
            'icon': '💼',
            'supported': True,
            'auth_required': True
        },
        {
            'platform_id': 'meet',
            'name': 'Google Meet',
            'icon': '📞',
            'supported': True,
            'auth_required': True
        },
        {
            'platform_id': 'webex',
            'name': 'Cisco Webex',
            'icon': '🎦',
            'supported': False,  # Coming soon
            'auth_required': True
        }
    ]
    
    for platform_data in platforms:
        try:
            existing = meeting_platforms.get_by_id(platform_data['platform_id'])
            if not existing:
                meeting_platforms.create(platform_data)
                print(f"Created platform: {platform_data['name']}")
            else:
                # Update existing platform
                update_data = {k: v for k, v in platform_data.items() if k != 'platform_id'}
                meeting_platforms.update(platform_data['platform_id'], update_data)
                print(f"Updated platform: {platform_data['name']}")
        except Exception as e:
            print(f"Error creating/updating platform {platform_data['platform_id']}: {e}")


def get_duration_minutes(duration_seconds):
    """Convert duration from seconds to minutes"""
    if duration_seconds:
        return duration_seconds // 60
    return 0
