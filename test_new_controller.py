#!/usr/bin/env python3
"""
Test the new Browserbase controller with SDK
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

from apps.browserbase.browser_controller_v3 import browser_controller

async def test_new_controller():
    print("=== Testing New Browserbase Controller ===")
    
    project_id = os.environ.get('BROWSERBASE_PROJECT_ID')
    if not project_id:
        print("ERROR: BROWSERBASE_PROJECT_ID not set")
        return
    
    print(f"Using project ID: {project_id}")
    
    # Test session creation
    print("\n1. Creating new session with SDK...")
    result = await browser_controller.create_and_connect_session(project_id)
    print(f"Result: {result}")
    
    if result.get('success'):
        session_id = result['id']
        print(f"\n2. Session created: {session_id}")
        
        # Test navigation
        print(f"\n3. Testing navigation...")
        nav_result = await browser_controller.navigate(session_id, "https://www.google.com")
        print(f"Navigation result: {nav_result}")
        
        # Test get content
        if nav_result.get('success'):
            print(f"\n4. Getting page content...")
            content_result = await browser_controller.get_content(session_id)
            print(f"Content result: {content_result.get('success', False)}")
            if content_result.get('success'):
                content = content_result.get('content', {})
                print(f"Page title: {content.get('title', 'N/A')}")
                print(f"Page URL: {content.get('url', 'N/A')}")
        
        # Clean up
        print(f"\n5. Closing session...")
        await browser_controller.close_session(session_id)
    
    await browser_controller.stop()

if __name__ == "__main__":
    asyncio.run(test_new_controller())

