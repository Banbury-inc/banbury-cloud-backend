# Recall AI Integration Setup Guide

## Environment Variables Required

Add these to your environment variables (`.env` or system environment):

```bash
# Recall AI API Configuration
RECALL_API_KEY=your_recall_api_key_here
RECALL_API_URL=https://us-west-2.recall.ai/api/v1

# For webhooks (optional)
RECALL_WEBHOOK_URL=https://your-domain.com/api/meeting-agent/webhooks/recall/
```

## Getting Your Recall AI API Key

1. Sign up at [Recall AI](https://recall.ai)
2. Navigate to your dashboard
3. Go to API Keys section
4. Generate a new API key
5. Copy the key and add it to your environment variables

## Installation

Make sure you have the required Python packages:

```bash
pip install httpx  # For async HTTP requests
```

## Testing the Integration

### Quick API Test
```bash
cd /path/to/banbury-cloud-backend
export RECALL_API_KEY=your_actual_api_key
python test_recall_integration.py
```

### Full Integration Test
1. Set your `RECALL_API_KEY` environment variable
2. Restart your Django server (important!)
3. Use the MeetingAgent frontend to join a meeting
4. Check the logs for Recall bot creation

### Common Fixes for API Errors

**Error: `"recall" is not a valid choice`**
- Fixed: Use `meeting_captions` as transcription provider

**Error: `destination_url may not be null`**  
- Fixed: Only include `real_time_transcription` if webhook URL is set

**Error: `Not a valid string` for metadata**
- Fixed: Send metadata as string instead of dict

## API Endpoints

The following new endpoints are available:

- `POST /api/meeting-agent/recall-bot/create/` - Create a new bot
- `GET /api/meeting-agent/recall-bot/{bot_id}/` - Get bot information  
- `POST /api/meeting-agent/recall-bot/{bot_id}/stop/` - Stop a bot

## How It Works

1. **Join Meeting**: When you click "Join Meeting", the system:
   - Creates a session in MongoDB
   - Calls Recall AI to create a bot
   - Stores the bot ID in the session
   - Returns success with bot ID

2. **Bot Joins Meeting**: Recall AI bot automatically:
   - Joins the meeting URL provided
   - Starts recording video/audio
   - Begins real-time transcription
   - Handles authentication if needed

3. **Monitoring**: The frontend:
   - Shows bot status in real-time
   - Displays recording indicators
   - Provides bot management controls

4. **Leave Meeting**: When stopping:
   - Calls Recall AI to stop the bot
   - Updates session status to completed
   - Bot leaves meeting and processes recordings

## Troubleshooting

### "RECALL_API_KEY is required"
- Make sure your API key is set in environment variables
- Restart your Django server after setting the key

### "Timeout creating Recall bot"
- Check your internet connection
- Verify the Recall AI service is accessible
- Try a different meeting URL

### "Invalid meeting URL"
- Ensure the meeting URL is valid and accessible
- Check that the platform is supported by Recall AI
- Test the URL manually first

## Supported Platforms

Recall AI supports:
- Zoom meetings
- Google Meet
- Microsoft Teams
- Webex (limited)

## Monitoring Bot Status

The system provides real-time bot status updates:
- `joining` - Bot is connecting to meeting
- `active` - Bot has joined successfully  
- `recording` - Bot is recording the meeting
- `leaving` - Bot is disconnecting
- `completed` - Bot finished and recordings are processing
- `failed` - Something went wrong

## Recording and Transcription

When the bot completes a meeting:
- Video recording is available via `video_url`
- Audio recording is available via `audio_url`  
- Transcription is available via `transcript_url`
- Chat messages are available via `chat_messages_url`

These URLs are automatically populated in the session data and accessible through the frontend.
