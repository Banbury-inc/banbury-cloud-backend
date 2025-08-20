from django.db import models
from pymongo.mongo_client import MongoClient
from bson import ObjectId
from datetime import datetime
import json

# MongoDB connection
uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
client = MongoClient(uri)
db = client["NeuraNet"]
conversations_collection = db["conversations"]

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
