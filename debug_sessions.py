#!/usr/bin/env python3
"""
Debug script to test Browserbase session management
"""
import os
import sys
import django
import asyncio

# Add the project root to the Python path
sys.path.append('/home/mmills/Documents/banbury-cloud-backend')

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.browserbase.browser_controller_v2 import browser_controller

async def test_session():
    print("=== Testing Browserbase Session Management ===")
    
    # Test session creation simulation
    test_session_id = "test-session-123"
    test_connect_url = "wss://connect.usw2.browserbase.com?signingKey=test"
    
    print(f"1. Testing connection to session {test_session_id}")
    result = await browser_controller.connect_to_session(test_session_id, test_connect_url)
    print(f"   Connection result: {result}")
    
    print(f"2. Checking stored sessions:")
    print(f"   Sessions: {list(browser_controller.sessions.keys())}")
    
    if test_session_id in browser_controller.sessions:
        session_data = browser_controller.sessions[test_session_id]
        print(f"   Session data: {dict(session_data)}")
    
    print(f"3. Testing _ensure_connected")
    connected = await browser_controller._ensure_connected(test_session_id)
    print(f"   Connection status: {connected}")
    
    print(f"4. Testing navigation (will fail but shows debug)")
    nav_result = await browser_controller.navigate(test_session_id, "https://google.com")
    print(f"   Navigation result: {nav_result}")

if __name__ == "__main__":
    asyncio.run(test_session())

