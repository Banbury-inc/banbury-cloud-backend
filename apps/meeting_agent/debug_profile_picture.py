"""
Debug script to check meeting agent profile picture configuration
Run this to verify if the profile picture URL is properly stored and retrieved
"""
import os
import sys
from pymongo import MongoClient

# Set up Django environment
sys.path.append('/home/mmills/Documents/banbury-cloud-backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

def check_profile_picture(username):
    """Check if profile picture is properly configured for a user"""
    
    print(f"\n{'='*60}")
    print(f"Checking profile picture configuration for: {username}")
    print(f"{'='*60}\n")
    
    # Connect to MongoDB
    uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
    client = MongoClient(uri)
    db = client["NeuraNet"]
    meeting_configs = db["meeting_agent_configs"]
    
    # Find config for user
    config = meeting_configs.find_one({"user_id": username})
    
    if not config:
        print(f"❌ No meeting agent config found for user: {username}")
        print(f"\n💡 The user needs to upload a profile picture in Settings > Meeting Agent")
        return
    
    print(f"✅ Config found for user: {username}")
    print(f"\nConfig details:")
    print(f"  - Config ID: {config.get('_id')}")
    print(f"  - Bot Name: {config.get('bot_name', 'NOT SET')}")
    print(f"  - Profile Picture URL: {config.get('profile_picture_url', 'NOT SET')}")
    print(f"  - Created At: {config.get('created_at')}")
    print(f"  - Updated At: {config.get('updated_at')}")
    
    profile_picture_url = config.get('profile_picture_url', '')
    
    if not profile_picture_url:
        print(f"\n⚠️  WARNING: Profile picture URL is empty!")
        print(f"   Please upload a profile picture in Settings > Meeting Agent tab")
        return
    
    print(f"\n✅ Profile picture URL is set: {profile_picture_url}")
    
    # Check if URL is accessible
    print(f"\n🔍 Checking if URL is publicly accessible...")
    try:
        import requests
        response = requests.head(profile_picture_url, timeout=5)
        if response.status_code == 200:
            print(f"✅ URL is publicly accessible (HTTP {response.status_code})")
            print(f"   Content-Type: {response.headers.get('Content-Type', 'Unknown')}")
            print(f"   Content-Length: {response.headers.get('Content-Length', 'Unknown')} bytes")
        elif response.status_code == 403:
            print(f"❌ URL is NOT publicly accessible (HTTP 403 Forbidden)")
            print(f"   The S3 file needs to be uploaded with public-read ACL")
            print(f"   Please re-upload the profile picture")
        else:
            print(f"⚠️  URL returned HTTP {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking URL accessibility: {str(e)}")
    
    # Check recent meeting sessions
    print(f"\n🔍 Checking recent meeting sessions...")
    meeting_sessions = db["meeting_sessions"]
    recent_sessions = list(meeting_sessions.find(
        {"user_id": username}
    ).sort("start_time", -1).limit(5))
    
    if not recent_sessions:
        print(f"   No meeting sessions found for this user")
    else:
        print(f"   Found {len(recent_sessions)} recent sessions:\n")
        for i, session in enumerate(recent_sessions, 1):
            metadata = session.get('metadata', {})
            has_profile_pic = bool(metadata.get('profilePictureUrl'))
            print(f"   {i}. Session ID: {session.get('_id')}")
            print(f"      Status: {session.get('status')}")
            print(f"      Start Time: {session.get('start_time')}")
            print(f"      Has Profile Picture in Metadata: {'✅ YES' if has_profile_pic else '❌ NO'}")
            if has_profile_pic:
                print(f"      Profile Picture URL: {metadata.get('profilePictureUrl')[:80]}...")
            print()
    
    print(f"{'='*60}")
    print(f"Diagnostic complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    # Replace with your username
    username = input("Enter username to check (e.g., mmills6060@gmail.com): ").strip()
    
    if not username:
        print("❌ Username is required")
        sys.exit(1)
    
    check_profile_picture(username)

