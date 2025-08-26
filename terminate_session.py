#!/usr/bin/env python3
"""
Terminate a specific Browserbase session
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

def terminate_session():
    print("=== Terminating Browserbase Session ===")
    
    api_key = os.environ.get('BROWSERBASE_API_KEY')
    session_id = "74b824ed-b872-4d68-a7a3-0b7be8acc628"  # The running session
    
    bb = Browserbase(api_key=api_key)
    
    try:
        # Check what methods are available
        print(f"Available methods on sessions: {[m for m in dir(bb.sessions) if not m.startswith('_')]}")
        
        # Try different termination methods
        methods_to_try = ['terminate', 'stop', 'close', 'end', 'kill']
        for method in methods_to_try:
            if hasattr(bb.sessions, method):
                try:
                    print(f"Trying {method}({session_id})")
                    result = getattr(bb.sessions, method)(session_id)
                    print(f"Success with {method}: {result}")
                    break
                except Exception as e:
                    print(f"Failed with {method}: {e}")
    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    terminate_session()

