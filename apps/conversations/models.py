from django.db import models
from bson import ObjectId
from datetime import datetime
import json
from core.mongodb_manager import get_mongodb_collection

# MongoDB collections using centralized manager
conversations_collection = get_mongodb_collection("conversations")
memories_collection = get_mongodb_collection("memories")

class Conversation:
    """Model for storing conversations in MongoDB"""
    
    @staticmethod
    def save_conversation(username, title, messages, metadata=None):
        """
        Save a conversation to MongoDB
        
        Args:
            username (str): The username of the conversation owner
            title (str): The title of the conversation
            messages (list): List of message objects
            metadata (dict): Optional metadata about the conversation
            
        Returns:
            dict: Result of the save operation
        """
        try:
            conversation_data = {
                "username": username,
                "title": title,
                "messages": messages,
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = conversations_collection.insert_one(conversation_data)
            
            return {
                "success": True,
                "conversation_id": str(result.inserted_id),
                "message": "Conversation saved successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_conversations(username, limit=50, offset=0):
        """
        Get conversations for a user
        
        Args:
            username (str): The username to get conversations for
            limit (int): Maximum number of conversations to return
            offset (int): Number of conversations to skip
            
        Returns:
            dict: List of conversations
        """
        try:
            conversations = list(conversations_collection.find(
                {"username": username}
            ).sort("updated_at", -1).skip(offset).limit(limit))
            
            # Convert ObjectId to string for JSON serialization
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
                if "created_at" in conv and hasattr(conv["created_at"], "isoformat"):
                    conv["created_at"] = conv["created_at"].isoformat()
                if "updated_at" in conv and hasattr(conv["updated_at"], "isoformat"):
                    conv["updated_at"] = conv["updated_at"].isoformat()
            
            return {
                "success": True,
                "conversations": conversations
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_conversation(conversation_id, username):
        """
        Get a specific conversation
        
        Args:
            conversation_id (str): The ID of the conversation
            username (str): The username for verification
            
        Returns:
            dict: The conversation data
        """
        try:
            conversation = conversations_collection.find_one({
                "_id": ObjectId(conversation_id),
                "username": username
            })
            
            if not conversation:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            # Convert ObjectId to string for JSON serialization
            conversation["_id"] = str(conversation["_id"])
            if "created_at" in conversation and hasattr(conversation["created_at"], "isoformat"):
                conversation["created_at"] = conversation["created_at"].isoformat()
            if "updated_at" in conversation and hasattr(conversation["updated_at"], "isoformat"):
                conversation["updated_at"] = conversation["updated_at"].isoformat()
            
            return {
                "success": True,
                "conversation": conversation
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_conversation(conversation_id, username):
        """
        Delete a conversation
        
        Args:
            conversation_id (str): The ID of the conversation
            username (str): The username for verification
            
        Returns:
            dict: Result of the delete operation
        """
        try:
            result = conversations_collection.delete_one({
                "_id": ObjectId(conversation_id),
                "username": username
            })
            
            if result.deleted_count == 0:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            return {
                "success": True,
                "message": "Conversation deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def delete_all_conversations(username):
        """
        Delete all conversations for a user
        
        Args:
            username (str): The username to delete conversations for
            
        Returns:
            dict: Result of the delete operation
        """
        try:
            result = conversations_collection.delete_many({
                "username": username
            })
            
            return {
                "success": True,
                "deleted_count": result.deleted_count,
                "message": f"Deleted {result.deleted_count} conversations"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def update_conversation_title(conversation_id, username, new_title):
        """
        Update the title of a conversation
        
        Args:
            conversation_id (str): The ID of the conversation
            username (str): The username for verification
            new_title (str): The new title
            
        Returns:
            dict: Result of the update operation
        """
        try:
            result = conversations_collection.update_one(
                {
                    "_id": ObjectId(conversation_id),
                    "username": username
                },
                {
                    "$set": {
                        "title": new_title,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count == 0:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            return {
                "success": True,
                "message": "Conversation title updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def update_conversation(conversation_id, username, title, messages, metadata=None):
        """
        Update an entire conversation
        
        Args:
            conversation_id (str): The ID of the conversation
            username (str): The username for verification
            title (str): The new title
            messages (list): The new messages
            metadata (dict): Optional metadata
            
        Returns:
            dict: Result of the update operation
        """
        try:
            result = conversations_collection.update_one(
                {
                    "_id": ObjectId(conversation_id),
                    "username": username
                },
                {
                    "$set": {
                        "title": title,
                        "messages": messages,
                        "metadata": metadata or {},
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count == 0:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            return {
                "success": True,
                "message": "Conversation updated successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_all_conversations_admin(limit=50, offset=0, days=30, username_filter=""):
        """
        Get all conversations across all users for admin analytics

        Args:
            limit (int): Maximum number of conversations to return
            offset (int): Number of conversations to skip
            days (int): Number of days to look back
            username_filter (str): Filter by specific username (optional)

        Returns:
            dict: List of conversations with analytics data
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Build match criteria
            match_criteria = {
                "created_at": {"$gte": cutoff_date}
            }
            
            # Add username filter if provided
            if username_filter:
                match_criteria["username"] = {"$regex": username_filter, "$options": "i"}

            # Get conversations with basic analytics
            pipeline = [
                {
                    "$match": match_criteria
                },
                {
                    "$addFields": {
                        "message_count": {"$size": "$messages"},
                        "last_message_at": {
                            "$max": {
                                "$map": {
                                    "input": "$messages",
                                    "as": "msg",
                                    "in": "$$msg.timestamp"
                                }
                            }
                        }
                    }
                },
                {
                    "$sort": {"created_at": -1}
                },
                {
                    "$skip": offset
                },
                {
                    "$limit": limit
                }
            ]
            
            conversations = list(conversations_collection.aggregate(pipeline))
            
            # Get summary statistics
            summary_pipeline = [
                {
                    "$match": match_criteria
                },
                {
                    "$group": {
                        "_id": None,
                        "total_conversations": {"$sum": 1},
                        "unique_users": {"$addToSet": "$username"},
                        "total_messages": {
                            "$sum": {"$size": "$messages"}
                        },
                        "avg_messages_per_conversation": {
                            "$avg": {"$size": "$messages"}
                        }
                    }
                },
                {
                    "$addFields": {
                        "unique_user_count": {"$size": "$unique_users"}
                    }
                }
            ]
            
            summary_result = list(conversations_collection.aggregate(summary_pipeline))
            summary = summary_result[0] if summary_result else {
                "total_conversations": 0,
                "unique_user_count": 0,
                "total_messages": 0,
                "avg_messages_per_conversation": 0
            }
            
            # Convert ObjectId to string for JSON serialization and extract model information
            for conv in conversations:
                conv["_id"] = str(conv["_id"])
                if "created_at" in conv and hasattr(conv["created_at"], "isoformat"):
                    conv["created_at"] = conv["created_at"].isoformat()
                if "updated_at" in conv and hasattr(conv["updated_at"], "isoformat"):
                    conv["updated_at"] = conv["updated_at"].isoformat()
                
                # Extract model information from metadata
                model_id = None
                model_provider = None
                if conv.get("metadata") and isinstance(conv["metadata"], dict):
                    tool_prefs = conv["metadata"].get("toolPreferences")
                    if tool_prefs and isinstance(tool_prefs, dict):
                        model_id = tool_prefs.get("model_id")
                        model_provider = tool_prefs.get("model_provider")
                
                conv["model_id"] = model_id
                conv["model_provider"] = model_provider
            
            return {
                "success": True,
                "conversations": conversations,
                "summary": {
                    "total_conversations": summary.get("total_conversations", 0),
                    "unique_users": summary.get("unique_user_count", 0),
                    "total_messages": summary.get("total_messages", 0),
                    "avg_messages_per_conversation": round(summary.get("avg_messages_per_conversation", 0), 1),
                    "period_days": days
                }
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_conversation_admin(conversation_id):
        """
        Get a specific conversation for admin (without username check)
        
        Args:
            conversation_id (str): The ID of the conversation
            
        Returns:
            dict: The conversation data
        """
        try:
            conversation = conversations_collection.find_one({
                "_id": ObjectId(conversation_id)
            })
            
            if not conversation:
                return {
                    "success": False,
                    "error": "Conversation not found"
                }
            
            # Convert ObjectId to string for JSON serialization
            conversation["_id"] = str(conversation["_id"])
            if "created_at" in conversation and hasattr(conversation["created_at"], "isoformat"):
                conversation["created_at"] = conversation["created_at"].isoformat()
            if "updated_at" in conversation and hasattr(conversation["updated_at"], "isoformat"):
                conversation["updated_at"] = conversation["updated_at"].isoformat()
            
            return {
                "success": True,
                "conversation": conversation
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    @staticmethod
    def get_conversation_users_admin(days=30):
        """
        Get list of users who have conversations for admin analytics

        Args:
            days (int): Number of days to look back

        Returns:
            dict: List of unique usernames with conversations
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)

            # Get unique usernames with conversations in the specified period
            pipeline = [
                {
                    "$match": {
                        "created_at": {"$gte": cutoff_date}
                    }
                },
                {
                    "$group": {
                        "_id": "$username"
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]

            result = list(conversations_collection.aggregate(pipeline))
            users = [item["_id"] for item in result]

            return {
                "success": True,
                "users": users
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

class Memory:
    """Model for storing AI memories in MongoDB"""
    
    @staticmethod
    def store_memory(username, content, memory_type="general", session_id="default", metadata=None):
        """
        Store a memory in MongoDB
        
        Args:
            username (str): The username of the memory owner
            content (str): The content to remember
            memory_type (str): Type of memory (e.g., 'preference', 'fact', 'context')
            session_id (str): Session ID for memory isolation
            metadata (dict): Optional metadata about the memory
            
        Returns:
            dict: Result of the store operation
        """
        try:
            memory_data = {
                "username": username,
                "content": content,
                "type": memory_type,
                "session_id": session_id,
                "metadata": metadata or {},
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            result = memories_collection.insert_one(memory_data)
            
            return {
                "success": True,
                "memory_id": str(result.inserted_id),
                "message": "Memory stored successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def search_memories(username, query, session_id="default", limit=10, memory_type=None):
        """
        Search memories for a user
        
        Args:
            username (str): The username to search memories for
            query (str): Search query
            session_id (str): Session ID for memory isolation
            limit (int): Maximum number of memories to return
            memory_type (str): Optional filter by memory type
            
        Returns:
            dict: List of relevant memories
        """
        try:
            # Build search filter
            search_filter = {
                "username": username,
                "session_id": session_id
            }
            
            if memory_type:
                search_filter["type"] = memory_type
            
            # Get all memories for the user and session
            memories = list(memories_collection.find(search_filter).sort("created_at", -1))
            
            # Simple keyword search (case-insensitive)
            query_lower = query.lower()
            relevant_memories = []
            
            for memory in memories:
                if query_lower in memory["content"].lower():
                    relevant_memories.append(memory)
                    if len(relevant_memories) >= limit:
                        break
            
            # Convert ObjectId to string for JSON serialization
            for memory in relevant_memories:
                memory["_id"] = str(memory["_id"])
                if "created_at" in memory and hasattr(memory["created_at"], "isoformat"):
                    memory["created_at"] = memory["created_at"].isoformat()
                if "updated_at" in memory and hasattr(memory["updated_at"], "isoformat"):
                    memory["updated_at"] = memory["updated_at"].isoformat()
            
            return {
                "success": True,
                "memories": relevant_memories,
                "count": len(relevant_memories)
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def get_memories(username, session_id="default", limit=50, offset=0, memory_type=None):
        """
        Get memories for a user
        
        Args:
            username (str): The username to get memories for
            session_id (str): Session ID for memory isolation
            limit (int): Maximum number of memories to return
            offset (int): Number of memories to skip
            memory_type (str): Optional filter by memory type
            
        Returns:
            dict: List of memories
        """
        try:
            # Build filter
            search_filter = {
                "username": username,
                "session_id": session_id
            }
            
            if memory_type:
                search_filter["type"] = memory_type
            
            memories = list(memories_collection.find(search_filter).sort("created_at", -1).skip(offset).limit(limit))
            
            # Convert ObjectId to string for JSON serialization
            for memory in memories:
                memory["_id"] = str(memory["_id"])
                if "created_at" in memory and hasattr(memory["created_at"], "isoformat"):
                    memory["created_at"] = memory["created_at"].isoformat()
                if "updated_at" in memory and hasattr(memory["updated_at"], "isoformat"):
                    memory["updated_at"] = memory["updated_at"].isoformat()
            
            return {
                "success": True,
                "memories": memories
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_memory(memory_id, username):
        """
        Delete a memory
        
        Args:
            memory_id (str): The ID of the memory
            username (str): The username for verification
            
        Returns:
            dict: Result of the delete operation
        """
        try:
            result = memories_collection.delete_one({
                "_id": ObjectId(memory_id),
                "username": username
            })
            
            if result.deleted_count == 0:
                return {
                    "success": False,
                    "error": "Memory not found"
                }
            
            return {
                "success": True,
                "message": "Memory deleted successfully"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def delete_memories_by_session(username, session_id):
        """
        Delete all memories for a specific session
        
        Args:
            username (str): The username for verification
            session_id (str): The session ID to delete memories for
            
        Returns:
            dict: Result of the delete operation
        """
        try:
            result = memories_collection.delete_many({
                "username": username,
                "session_id": session_id
            })
            
            return {
                "success": True,
                "message": f"Deleted {result.deleted_count} memories for session {session_id}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def cleanup_old_memories(username, days_to_keep=30):
        """
        Clean up old memories for a user
        
        Args:
            username (str): The username to clean up memories for
            days_to_keep (int): Number of days to keep memories
            
        Returns:
            dict: Result of the cleanup operation
        """
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
            
            result = memories_collection.delete_many({
                "username": username,
                "created_at": {"$lt": cutoff_date}
            })
            
            return {
                "success": True,
                "message": f"Deleted {result.deleted_count} old memories"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
