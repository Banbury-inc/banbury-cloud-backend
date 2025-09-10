#!/usr/bin/env python3
"""
Test script for Recall AI integration
Run this to test if your Recall AI API key works
"""
import os
import asyncio
import json
from apps.meeting_agent.recall_service import RecallAIService

async def test_recall_api():
    """Test the Recall AI integration"""
    
    # Check if API key is set
    api_key = os.environ.get('RECALL_API_KEY')
    if not api_key:
        print("❌ RECALL_API_KEY environment variable is not set!")
        print("   Set it with: export RECALL_API_KEY=your_api_key_here")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...")
    
    try:
        # Initialize service
        service = RecallAIService()
        print("✅ RecallAIService initialized successfully")
        
        # Test with a sample meeting URL (this won't actually join, just test API)
        test_meeting_url = "https://zoom.us/j/123456789"
        test_metadata = {
            'bot_name': 'Test Bot',
            'recording_mode': 'speaker_view',
            'session_id': 'test-session-123'
        }
        
        print(f"🧪 Testing bot creation with URL: {test_meeting_url}")
        
        # Create bot (this will fail but should give us proper error info)
        result = await service.create_bot(test_meeting_url, test_metadata)
        
        if result['success']:
            print("✅ Bot created successfully!")
            print(f"   Bot ID: {result['bot_id']}")
            
            # Test getting bot info
            bot_result = await service.get_bot(result['bot_id'])
            if bot_result['success']:
                print("✅ Bot info retrieved successfully")
                bot_data = bot_result['bot_data']
                print(f"   Bot status: {bot_data.get('status', 'unknown')}")
            else:
                print(f"❌ Failed to get bot info: {bot_result.get('message')}")
            
            # Test stopping bot
            stop_result = await service.stop_bot(result['bot_id'])
            if stop_result['success']:
                print("✅ Bot stopped successfully")
            else:
                print(f"❌ Failed to stop bot: {stop_result.get('message')}")
                
        else:
            print(f"❌ Bot creation failed: {result.get('message')}")
            print(f"   Error details: {result.get('details')}")
            
            # Check for specific error types
            if 'authentication' in result.get('message', '').lower():
                print("💡 This looks like an authentication error. Check your API key.")
            elif 'invalid meeting url' in result.get('details', '').lower():
                print("💡 This is expected for the test URL. Your API key works!")
                return True
            
        return result['success']
        
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
        return False

def test_minimal_bot_creation():
    """Test minimal bot creation payload"""
    print("\n🧪 Testing minimal bot creation payload...")
    
    minimal_payload = {
        'meeting_url': 'https://zoom.us/j/123456789',
        'bot_name': 'Test Bot',
        'automatic_leave': {
            'waiting_room_timeout': 1200,
            'noone_joined_timeout': 1200,
            'everyone_left_timeout': 30
        }
    }
    
    print(f"Minimal payload: {json.dumps(minimal_payload, indent=2)}")
    print("📝 Note: transcription_options are NOT allowed in bot creation")
    print("   Transcription is configured via Recall AI dashboard settings")
    
    # This is what we should be sending to Recall AI
    return minimal_payload

if __name__ == "__main__":
    print("🚀 Testing Recall AI Integration")
    print("=" * 50)
    
    # Test minimal payload first
    test_minimal_bot_creation()
    
    # Test actual API call
    print("\n🔗 Testing actual API call...")
    success = asyncio.run(test_recall_api())
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Recall AI integration test PASSED!")
        print("   Your bot should now be able to join meetings.")
    else:
        print("❌ Recall AI integration test FAILED!")
        print("   Check the error messages above for debugging.")
        
    print("\nNext steps:")
    print("1. Make sure RECALL_API_KEY is set in your environment")
    print("2. Restart your Django server")  
    print("3. Try joining a real meeting through the frontend")
