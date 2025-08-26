#!/usr/bin/env python3
"""
Cleanup existing Browserbase sessions
"""
import os
import sys
import django

# Add the project root to the Python path
sys.path.append('/home/mmills/Documents/banbury-cloud-backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from browserbase import Browserbase

def cleanup_sessions():
    print("=== Cleaning up Browserbase Sessions ===")
    
    api_key = os.environ.get('BROWSERBASE_API_KEY')
    project_id = os.environ.get('BROWSERBASE_PROJECT_ID')
    
    if not api_key or not project_id:
        print("ERROR: API key or project ID not set")
        return
    
    bb = Browserbase(api_key=api_key)
    
    try:
        # List all sessions
        print("Listing all sessions...")
        sessions = bb.sessions.list()
        print(f"Found {len(sessions)} sessions")
        
        for session in sessions:
            print(f"Session {session.id}: status={getattr(session, 'status', 'unknown')}")
            
            # Terminate active sessions
            if getattr(session, 'status', None) in ['RUNNING', 'QUEUED']:
                try:
                    print(f"Terminating session {session.id}")
                    bb.sessions.delete(session.id)
                    print(f"Successfully terminated {session.id}")
                except Exception as e:
                    print(f"Failed to terminate {session.id}: {e}")
    
    except Exception as e:
        print(f"Error listing sessions: {e}")

if __name__ == "__main__":
    cleanup_sessions()

