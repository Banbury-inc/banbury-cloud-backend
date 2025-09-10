"""
MongoDB Connection Manager

This module provides a centralized MongoDB connection manager that ensures
only one connection is created and properly manages connection pooling.
"""

import threading
from typing import Optional
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from django.conf import settings
import os

class MongoDBManager:
    """
    Singleton MongoDB connection manager.
    
    This class ensures that only one MongoDB connection is created throughout
    the application lifecycle and provides proper connection pooling and cleanup.
    """
    
    _instance = None
    _lock = threading.Lock()
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MongoDBManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, '_initialized'):
            self._initialized = True
            self._setup_connection()
    
    def _setup_connection(self):
        """Initialize MongoDB connection with proper settings."""
        # Get MongoDB URI from environment or use default
        self._uri = os.getenv(
            'MONGODB_URI',
            "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        )
        
        # Get SSL settings from environment (useful for production vs development)
        self._ssl_strict = os.getenv('MONGODB_SSL_STRICT', 'false').lower() == 'true'
        
        # Connection will be established on first use (lazy initialization)
        self._client = None
        self._db = None
    
    def get_client(self) -> MongoClient:
        """
        Get MongoDB client with proper connection pooling.
        
        Returns:
            MongoClient: Configured MongoDB client
        """
        if self._client is None:
            with self._lock:
                if self._client is None:
                    # Base connection options
                    connection_options = {
                        'maxPoolSize': 50,  # Maximum number of connections in the pool
                        'minPoolSize': 5,   # Minimum number of connections in the pool
                        'maxIdleTimeMS': 30000,  # Close connections after 30 seconds of inactivity
                        'waitQueueTimeoutMS': 5000,  # Wait 5 seconds for an available connection
                        'serverSelectionTimeoutMS': 5000,  # 5 second timeout for server selection
                        'socketTimeoutMS': 20000,  # 20 second socket timeout
                        'connectTimeoutMS': 20000,  # 20 second connection timeout
                        'retryWrites': True,
                        'w': 'majority'
                    }
                    
                    # Add SSL options based on environment
                    # For MongoDB Atlas, use minimal TLS configuration in development
                    if self._ssl_strict:
                        # Production SSL settings
                        connection_options.update({
                            'tls': True,
                            'tlsAllowInvalidCertificates': False,
                            'tlsAllowInvalidHostnames': False
                        })
                    # For development, let pymongo auto-detect TLS from the URI
                    # MongoDB Atlas URIs with mongodb+srv:// automatically enable TLS
                    
                    self._client = MongoClient(self._uri, **connection_options)
        return self._client
    
    def get_database(self, db_name: str = "NeuraNet") -> Database:
        """
        Get MongoDB database.
        
        Args:
            db_name: Name of the database (default: "NeuraNet")
            
        Returns:
            Database: MongoDB database instance
        """
        client = self.get_client()
        return client[db_name]
    
    def get_collection(self, collection_name: str, db_name: str = "NeuraNet") -> Collection:
        """
        Get MongoDB collection.
        
        Args:
            collection_name: Name of the collection
            db_name: Name of the database (default: "NeuraNet")
            
        Returns:
            Collection: MongoDB collection instance
        """
        db = self.get_database(db_name)
        return db[collection_name]
    
    def close_connection(self):
        """Close MongoDB connection and cleanup resources."""
        if self._client is not None:
            with self._lock:
                if self._client is not None:
                    self._client.close()
                    self._client = None
                    self._db = None
    
    def health_check(self) -> bool:
        """
        Perform a health check on the MongoDB connection.
        
        Returns:
            bool: True if connection is healthy, False otherwise
        """
        try:
            client = self.get_client()
            # Ping the server
            client.admin.command('ping')
            return True
        except Exception as e:
            print(f"MongoDB health check failed: {e}")
            return False
    
    def get_connection_info(self) -> dict:
        """
        Get information about current MongoDB connections.
        
        Returns:
            dict: Connection information
        """
        try:
            client = self.get_client()
            server_info = client.server_info()
            return {
                "connected": True,
                "server_version": server_info.get("version"),
                "max_pool_size": client.options.pool_options.max_pool_size,
                "min_pool_size": client.options.pool_options.min_pool_size,
            }
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }

# Global instance
mongodb_manager = MongoDBManager()

# Convenience functions for backward compatibility
def get_mongodb_client() -> MongoClient:
    """Get MongoDB client instance."""
    return mongodb_manager.get_client()

def get_mongodb_database(db_name: str = "NeuraNet") -> Database:
    """Get MongoDB database instance."""
    return mongodb_manager.get_database(db_name)

def get_mongodb_collection(collection_name: str, db_name: str = "NeuraNet") -> Collection:
    """Get MongoDB collection instance."""
    return mongodb_manager.get_collection(collection_name, db_name)

def close_mongodb_connection():
    """Close MongoDB connection."""
    mongodb_manager.close_connection()

def mongodb_health_check() -> bool:
    """Perform MongoDB health check."""
    return mongodb_manager.health_check()
