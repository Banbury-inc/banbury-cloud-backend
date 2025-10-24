"""
Test script for Slack integration endpoints.
Run this script to verify all Slack endpoints are working correctly.
"""
import os
import sys
import requests
import json
from typing import Dict, Optional

# Configuration
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')
JWT_TOKEN = os.environ.get('JWT_TOKEN', '')  # Set your JWT token here

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.ENDC}\n")


def print_success(text: str):
    """Print a success message."""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text: str):
    """Print an error message."""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text: str):
    """Print an info message."""
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")


def make_request(
    method: str,
    endpoint: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None
) -> tuple[bool, any]:
    """Make an HTTP request to the backend."""
    url = f"{BACKEND_URL}{endpoint}"
    headers = {
        'Authorization': f'Bearer {JWT_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data, timeout=10)
        else:
            return False, f"Unsupported method: {method}"
        
        if response.status_code in [200, 201]:
            return True, response.json()
        else:
            return False, f"HTTP {response.status_code}: {response.text}"
            
    except Exception as e:
        return False, str(e)


def test_connection_status():
    """Test the Slack connection status endpoint."""
    print_header("Test 1: Connection Status")
    
    success, result = make_request('GET', '/authentication/slack/status/')
    
    if success:
        print_success("Connection status endpoint works!")
        connected = result.get('connected', False)
        
        if connected:
            print_info(f"Connected: Yes")
            print_info(f"Team: {result.get('teamName', 'N/A')}")
            print_info(f"User: {result.get('userName', 'N/A')}")
        else:
            print_info("Connected: No")
            print_info("Connect your Slack account in Settings to proceed with other tests.")
        
        return connected
    else:
        print_error(f"Failed: {result}")
        return False


def test_list_channels():
    """Test listing Slack channels."""
    print_header("Test 2: List Channels")
    
    success, result = make_request('GET', '/authentication/slack/channels/')
    
    if success:
        channels = result.get('channels', [])
        print_success(f"Found {len(channels)} channels!")
        
        if channels:
            print_info("Sample channels:")
            for channel in channels[:5]:  # Show first 5 channels
                print(f"  - #{channel.get('name')} (ID: {channel.get('id')})")
        
        return True, channels
    else:
        print_error(f"Failed: {result}")
        return False, []


def test_channel_history(channel_id: str):
    """Test getting channel history."""
    print_header("Test 3: Channel History")
    
    success, result = make_request(
        'GET',
        '/authentication/slack/channel_history/',
        params={'channel': channel_id, 'limit': '5'}
    )
    
    if success:
        messages = result.get('messages', [])
        print_success(f"Retrieved {len(messages)} messages!")
        
        if messages:
            print_info("Recent messages:")
            for msg in messages[:3]:  # Show first 3 messages
                text = msg.get('text', '')[:50]  # First 50 chars
                print(f"  - {text}...")
        
        return True
    else:
        print_error(f"Failed: {result}")
        return False


def test_send_message(channel_id: str):
    """Test sending a message to Slack."""
    print_header("Test 4: Send Message")
    
    # Ask user for confirmation
    print_info(f"This will send a test message to channel {channel_id}")
    response = input("Proceed? (y/n): ")
    
    if response.lower() != 'y':
        print_info("Skipped send message test")
        return False
    
    success, result = make_request(
        'POST',
        '/authentication/slack/send_message/',
        data={
            'channel': channel_id,
            'text': '🤖 Test message from Banbury AI - Slack integration is working!'
        }
    )
    
    if success:
        print_success("Message sent successfully!")
        ts = result.get('ts', 'N/A')
        print_info(f"Message timestamp: {ts}")
        return True, ts
    else:
        print_error(f"Failed: {result}")
        return False, None


def test_search_messages():
    """Test searching messages."""
    print_header("Test 5: Search Messages")
    
    query = input("Enter search query (or press Enter for 'test'): ").strip()
    if not query:
        query = "test"
    
    success, result = make_request(
        'GET',
        '/authentication/slack/search/',
        params={'query': query, 'count': '5'}
    )
    
    if success:
        messages = result.get('messages', [])
        total = result.get('total', 0)
        print_success(f"Found {total} total matches, showing {len(messages)}")
        
        if messages:
            print_info("Search results:")
            for msg in messages[:3]:  # Show first 3
                text = msg.get('text', '')[:50]
                print(f"  - {text}...")
        
        return True
    else:
        print_error(f"Failed: {result}")
        return False


def test_add_reaction(channel_id: str, message_ts: str):
    """Test adding a reaction to a message."""
    print_header("Test 6: Add Reaction")
    
    if not message_ts:
        print_info("Skipped: No message timestamp available")
        return False
    
    success, result = make_request(
        'POST',
        '/authentication/slack/add_reaction/',
        data={
            'channel': channel_id,
            'timestamp': message_ts,
            'name': 'white_check_mark'
        }
    )
    
    if success:
        print_success("Reaction added successfully! ✅")
        return True
    else:
        # Reaction already exists is ok
        if 'already_reacted' in str(result):
            print_success("Reaction already exists (ok)")
            return True
        print_error(f"Failed: {result}")
        return False


def test_disconnect():
    """Test disconnecting Slack account."""
    print_header("Test 7: Disconnect (Optional)")
    
    print_info("This will disconnect your Slack account")
    response = input("Proceed? (y/n): ")
    
    if response.lower() != 'y':
        print_info("Skipped disconnect test")
        return False
    
    success, result = make_request('POST', '/authentication/slack/disconnect/')
    
    if success:
        print_success("Disconnected successfully!")
        print_info("You can reconnect in Settings → Connections")
        return True
    else:
        print_error(f"Failed: {result}")
        return False


def main():
    """Run all tests."""
    print_header("Slack Integration Test Suite")
    
    # Check if JWT token is set
    if not JWT_TOKEN:
        print_error("JWT_TOKEN environment variable not set!")
        print_info("Set it with: export JWT_TOKEN='your_token_here'")
        print_info("Or pass it when running: JWT_TOKEN='your_token' python test_slack_integration.py")
        sys.exit(1)
    
    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Token: {JWT_TOKEN[:20]}...")
    
    # Test 1: Connection Status
    is_connected = test_connection_status()
    
    if not is_connected:
        print("\n" + Colors.WARNING + "⚠ Slack not connected. Please connect your account to run remaining tests." + Colors.ENDC)
        print_info("Go to Settings → Connections → Slack Integration → Connect")
        sys.exit(0)
    
    # Test 2: List Channels
    success, channels = test_list_channels()
    
    if not success or not channels:
        print_error("Cannot proceed without channels")
        sys.exit(1)
    
    # Get first public channel for testing
    test_channel = None
    for ch in channels:
        if ch.get('is_member', False):
            test_channel = ch
            break
    
    if not test_channel:
        print_error("No channels where bot is a member found")
        print_info("Invite the bot to a channel first: /invite @YourBotName")
        sys.exit(1)
    
    channel_id = test_channel['id']
    channel_name = test_channel['name']
    print_info(f"\nUsing channel for tests: #{channel_name} ({channel_id})")
    
    # Test 3: Channel History
    test_channel_history(channel_id)
    
    # Test 4: Send Message
    send_success, message_ts = test_send_message(channel_id)
    
    # Test 5: Search Messages
    test_search_messages()
    
    # Test 6: Add Reaction
    if send_success and message_ts:
        test_add_reaction(channel_id, message_ts)
    
    # Test 7: Disconnect (optional)
    # test_disconnect()
    
    # Summary
    print_header("Test Suite Complete")
    print_success("All tests completed!")
    print_info("Check your Slack channel to verify the test message and reaction.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTests cancelled by user")
        sys.exit(0)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

