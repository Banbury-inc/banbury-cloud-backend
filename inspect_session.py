#!/usr/bin/env python3
"""
Inspect the Browserbase session object
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

def inspect_session():
    print("=== Inspecting Browserbase Session Object ===")
    
    api_key = os.environ.get('BROWSERBASE_API_KEY')
    project_id = os.environ.get('BROWSERBASE_PROJECT_ID')
    
    if not api_key or not project_id:
        print("ERROR: API key or project ID not set")
        return
    
    bb = Browserbase(api_key=api_key)
    
    print(f"Creating session with project {project_id}")
    session = bb.sessions.create(
        project_id=project_id,
        keep_alive=True
    )
    
    print(f"Session created: {session.id}")
    print(f"Session type: {type(session)}")
    print(f"Session attributes: {dir(session)}")
    print(f"Session dict: {session.__dict__ if hasattr(session, '__dict__') else 'No __dict__'}")
    
    # Try to access common attributes
    for attr in ['id', 'connection_url', 'connect_url', 'ws_url', 'websocket_url', 'debugger_url', 'debug_url']:
        try:
            value = getattr(session, attr, 'NOT_FOUND')
            print(f"session.{attr}: {value}")
        except Exception as e:
            print(f"session.{attr}: ERROR - {e}")

if __name__ == "__main__":
    inspect_session()

