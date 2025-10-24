# Slack Integration Setup Guide

This guide will help you set up the Slack integration for the Banbury backend.

## Prerequisites

- A Slack workspace (free or paid)
- Admin access to create a Slack app
- Backend server running

## Step 1: Create a Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"**
3. Choose **"From scratch"**
4. Enter app name (e.g., "Banbury AI Assistant")
5. Select your workspace
6. Click **"Create App"**

## Step 2: Configure OAuth & Permissions

### Add Redirect URLs

1. Go to **"OAuth & Permissions"** in the sidebar
2. Under **"Redirect URLs"**, add your callback URL:
   - For local development: `http://localhost:8000/authentication/slack/oauth_callback/`
   - For production: `https://your-backend-domain.com/authentication/slack/oauth_callback/`
3. Click **"Add"** and then **"Save URLs"**

### Configure Bot Token Scopes

Scroll down to **"Scopes"** > **"Bot Token Scopes"** and add the following scopes:

- `channels:history` - View messages in public channels
- `channels:read` - View basic information about public channels
- `chat:write` - Send messages as the app
- `groups:history` - View messages in private channels
- `groups:read` - View basic information about private channels
- `reactions:write` - Add emoji reactions
- `search:read` - Search workspace messages
- `users:read` - View users in the workspace
- `channels:manage` - Manage channel properties (for topic updates)

## Step 3: Get Your Credentials

1. Go to **"Basic Information"** in the sidebar
2. Under **"App Credentials"**, find:
   - **Client ID**
   - **Client Secret**
3. Copy these values - you'll need them for your environment variables

## Step 4: Configure Backend Environment Variables

Add the following variables to your backend environment (`.env` file or hosting platform):

```bash
# Slack OAuth Credentials
SLACK_CLIENT_ID=your_client_id_here
SLACK_CLIENT_SECRET=your_client_secret_here

# Frontend URL for OAuth redirects
FRONTEND_URL=http://localhost:3000  # or your production URL
```

### For Production

If you're deploying to a platform like Heroku, Railway, or similar:

```bash
heroku config:set SLACK_CLIENT_ID=your_client_id_here
heroku config:set SLACK_CLIENT_SECRET=your_client_secret_here
heroku config:set FRONTEND_URL=https://your-frontend-domain.com
```

## Step 5: Install the App to Your Workspace

1. Go to **"Install App"** in the sidebar
2. Click **"Install to Workspace"**
3. Review the permissions
4. Click **"Allow"**

This step is optional but helpful for testing - it gives your app access to your workspace.

## Step 6: Test the Integration

### Backend Server

1. Start your backend server:
   ```bash
   python manage.py runserver
   ```

2. The following endpoints should now be available:
   - `GET /authentication/slack/status/` - Check connection status
   - `POST /authentication/slack/initiate_oauth/` - Start OAuth flow
   - `GET /authentication/slack/oauth_callback/` - OAuth callback
   - `POST /authentication/slack/disconnect/` - Disconnect account

### Frontend

1. Start your frontend server:
   ```bash
   npm run dev
   ```

2. Navigate to **Settings → Connections**
3. Find the **Slack Integration** section
4. Click **"Connect"**
5. You should be redirected to Slack for authorization
6. After authorizing, you should be redirected back to your frontend

## Step 7: Verify Database Storage

After connecting, verify that the credentials are stored in MongoDB:

```bash
# Connect to MongoDB
mongo "mongodb+srv://your-connection-string"

# Switch to database
use NeuraNet

# Find your user
db.users.findOne(
  { "username": "your_username" },
  { "slack_credentials": 1 }
)
```

You should see a document with:
```json
{
  "slack_credentials": {
    "access_token": "xoxb-...",
    "team_id": "T123456",
    "team_name": "Your Team Name",
    "user_id": "U123456",
    "user_name": "your_slack_username",
    "connected_at": "2024-01-01T00:00:00.000Z",
    "scope": "..."
  }
}
```

## Step 8: Test API Endpoints

Use curl or Postman to test the endpoints:

```bash
# Get your JWT token first
TOKEN="your_jwt_token_here"

# Test connection status
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/authentication/slack/status/

# List channels
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/authentication/slack/channels/

# Send a message
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"channel": "C1234567890", "text": "Hello from Banbury!"}' \
  http://localhost:8000/authentication/slack/send_message/
```

## Troubleshooting

### Error: "Slack credentials not configured"

**Solution:** Make sure `SLACK_CLIENT_ID` and `SLACK_CLIENT_SECRET` are set in your environment variables and restart your backend server.

### Error: "invalid_redirect_uri"

**Solution:** 
1. Check that your redirect URI in the Slack app matches exactly what you're using
2. Make sure there are no trailing slashes mismatches
3. Verify the protocol (http vs https) matches

### Error: "Slack not connected"

**Solution:** User needs to connect their Slack account first:
1. Go to Settings → Connections
2. Click "Connect" under Slack Integration
3. Authorize the app

### OAuth callback fails silently

**Solution:**
1. Check that the callback URL is not blocked by CORS
2. Verify the middleware allows `/authentication/slack/oauth_callback/` without authentication
3. Check browser console for errors

### Messages not sending

**Solution:**
1. Verify the bot is a member of the channel (for private channels)
2. Check that the channel ID is correct (starts with 'C' for public, 'G' for private)
3. Ensure the `chat:write` scope is granted

## Security Best Practices

### 1. Token Encryption

Consider encrypting the Slack access tokens before storing in MongoDB:

```python
from cryptography.fernet import Fernet

# Generate a key (store this securely, not in code)
encryption_key = Fernet.generate_key()
cipher = Fernet(encryption_key)

# Encrypt token before storing
encrypted_token = cipher.encrypt(access_token.encode()).decode()

# Decrypt when needed
decrypted_token = cipher.decrypt(encrypted_token.encode()).decode()
```

### 2. Token Rotation

Slack tokens don't expire by default, but you should:
- Store `connected_at` timestamp
- Prompt users to reconnect periodically (e.g., every 90 days)
- Implement token refresh logic if using user tokens

### 3. Rate Limiting

Implement rate limiting for Slack API calls:

```python
from django.core.cache import cache
from django.http import JsonResponse

def check_rate_limit(user_id, endpoint):
    cache_key = f"slack_rate_limit:{user_id}:{endpoint}"
    requests = cache.get(cache_key, 0)
    
    if requests >= 50:  # 50 requests per minute
        return False, "Rate limit exceeded"
    
    cache.set(cache_key, requests + 1, 60)  # 60 seconds TTL
    return True, None
```

### 4. Scope Validation

Only request the minimum scopes needed:
- Start with read-only scopes
- Add write scopes only when users need them
- Document why each scope is required

## Advanced Configuration

### Multiple Workspaces

To support multiple Slack workspaces per user:

```python
# Store as array in MongoDB
"slack_connections": [
    {
        "team_id": "T123456",
        "team_name": "Workspace 1",
        "access_token": "xoxb-...",
        ...
    },
    {
        "team_id": "T789012",
        "team_name": "Workspace 2",
        "access_token": "xoxb-...",
        ...
    }
]
```

### Webhook Events

To receive real-time updates from Slack:

1. Enable **Event Subscriptions** in your Slack app
2. Add your request URL: `https://your-backend.com/slack/events/`
3. Subscribe to events like `message.channels`, `reaction_added`, etc.
4. Implement the events endpoint to handle webhooks

### Interactive Components

For buttons and interactive messages:

1. Enable **Interactivity & Shortcuts**
2. Add request URL: `https://your-backend.com/slack/interactions/`
3. Implement handler for interactive payloads

## Production Deployment Checklist

- [ ] Environment variables configured on production server
- [ ] Slack app redirect URLs include production domain
- [ ] HTTPS enabled for OAuth callbacks
- [ ] MongoDB connection secured with authentication
- [ ] Token encryption implemented
- [ ] Rate limiting configured
- [ ] Error logging and monitoring set up
- [ ] Backup strategy for user credentials
- [ ] CORS properly configured for frontend
- [ ] Health check endpoint responds correctly

## API Reference

See the main `SLACK_INTEGRATION_README.md` in the frontend directory for detailed API endpoint documentation.

## Support

For issues or questions:
1. Check Slack API documentation: https://api.slack.com/docs
2. Review this setup guide
3. Check application logs for errors
4. Test each endpoint independently
5. Contact the development team

## Additional Resources

- [Slack API Documentation](https://api.slack.com/docs)
- [Slack OAuth Guide](https://api.slack.com/authentication/oauth-v2)
- [Slack Scopes Reference](https://api.slack.com/scopes)
- [Slack API Rate Limits](https://api.slack.com/docs/rate-limits)

