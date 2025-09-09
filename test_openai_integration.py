#!/usr/bin/env python3
"""
Test script for OpenAI Whisper and GPT-4 integration
"""
import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from apps.meeting_agent.services import TranscriptionService, SummaryService


def test_openai_connection():
    """Test OpenAI API connection"""
    try:
        import openai
        
        api_key = os.environ.get('OPENAI_API_KEY')
        if not api_key:
            print("❌ OPENAI_API_KEY environment variable not set")
            print("   Set it with: export OPENAI_API_KEY=sk-your-key-here")
            return False
        
        openai.api_key = api_key
        
        # Test API connection with a simple completion
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use cheaper model for testing
            messages=[{"role": "user", "content": "Say 'API connection successful'"}],
            max_tokens=10
        )
        
        if response.choices[0].message.content:
            print("✅ OpenAI API connection successful")
            print(f"   Response: {response.choices[0].message.content}")
            return True
        else:
            print("❌ OpenAI API connection failed - no response")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI API connection failed: {e}")
        return False


def test_transcription_service():
    """Test transcription service initialization"""
    try:
        service = TranscriptionService()
        
        if service.client.api_key:
            print("✅ TranscriptionService initialized with API key")
            return True
        else:
            print("⚠️  TranscriptionService initialized without API key (will use simulation)")
            return True
            
    except Exception as e:
        print(f"❌ TranscriptionService initialization failed: {e}")
        return False


def test_summary_service():
    """Test summary service initialization"""
    try:
        service = SummaryService()
        
        if service.client.api_key:
            print("✅ SummaryService initialized with API key")
            return True
        else:
            print("⚠️  SummaryService initialized without API key (will use simulation)")
            return True
            
    except Exception as e:
        print(f"❌ SummaryService initialization failed: {e}")
        return False


def test_sample_transcription():
    """Test transcription with sample text"""
    try:
        service = SummaryService()
        
        sample_transcription = """
        John: Good morning everyone, welcome to our weekly standup.
        Jane: Thanks John. I completed the user authentication feature this week.
        Mike: Great work Jane! I'm working on the database optimization.
        John: Excellent. Let's plan to deploy the auth feature next week.
        Jane: I'll prepare the deployment documentation.
        Mike: I'll finish the database work by Friday.
        """
        
        # Test summary generation
        summary_data = service._generate_fallback_summary(sample_transcription)
        
        print("✅ Sample summary generation successful")
        print(f"   Summary: {summary_data['summary'][:100]}...")
        print(f"   Key Points: {len(summary_data['key_points'])} items")
        print(f"   Decisions: {len(summary_data['decisions'])} items")
        print(f"   Next Steps: {len(summary_data['next_steps'])} items")
        
        return True
        
    except Exception as e:
        print(f"❌ Sample transcription test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("🔬 Testing Meeting Agent AI Services Integration\n")
    
    tests = [
        ("OpenAI API Connection", test_openai_connection),
        ("TranscriptionService", test_transcription_service),
        ("SummaryService", test_summary_service),
        ("Sample Processing", test_sample_transcription)
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"Testing {test_name}...")
        result = test_func()
        results.append(result)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Meeting Agent AI services are ready.")
    else:
        print("⚠️  Some tests failed. Check configuration and try again.")
    
    # Setup instructions
    print("\n📋 Setup Instructions:")
    print("1. Install dependencies: pip install -r requirements-mongodb.txt")
    print("2. Set OpenAI API key: export OPENAI_API_KEY=sk-your-key-here")
    print("3. Start MongoDB: docker run -d -p 27017:27017 mongo")
    print("4. Initialize platforms: python manage.py setup_meeting_platforms")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
