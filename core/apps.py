"""
Django app configuration for MongoDB connection management.
"""

from django.apps import AppConfig
from django.db.models.signals import pre_delete
from django.core.signals import request_finished
import atexit
import signal
import sys


class CoreConfig(AppConfig):
    """Core app configuration with MongoDB cleanup handlers."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    
    def ready(self):
        """Set up connection cleanup handlers when Django starts."""
        # Import here to avoid circular imports
        from .mongodb_manager import mongodb_manager
        
        # Register cleanup functions
        self._register_cleanup_handlers()
    
    def _register_cleanup_handlers(self):
        """Register various cleanup handlers for MongoDB connections."""
        from .mongodb_manager import mongodb_manager
        
        # Register cleanup on process exit
        atexit.register(self._cleanup_mongodb)
        
        # Register cleanup on signals (SIGTERM, SIGINT)
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Connect to Django's request finished signal for periodic cleanup
        request_finished.connect(self._on_request_finished)
    
    def _cleanup_mongodb(self):
        """Clean up MongoDB connections."""
        try:
            from .mongodb_manager import mongodb_manager
            mongodb_manager.close_connection()
            print("MongoDB connections closed successfully")
        except Exception as e:
            print(f"Error closing MongoDB connections: {e}")
    
    def _signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown."""
        print(f"Received signal {signum}, closing MongoDB connections...")
        self._cleanup_mongodb()
        sys.exit(0)
    
    def _on_request_finished(self, sender, **kwargs):
        """
        Handle request finished signal for connection health checks.
        
        Note: This doesn't close connections but could be used for
        periodic health checks if needed.
        """
        # Could add periodic health checks here if needed
        pass
