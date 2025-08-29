# X API Setup Guide - Fix for OAuth Issues

## Problem
The `/h` 404 error occurs when trying to connect X account due to missing environment variables and OAuth configuration issues.

## Solution Steps

### 1. Set Up X API Environment Variables

Add these variables to your backend `.env` file:

```bash
# X API Credentials (Required)
X_API_KEY=your_x_api_key_here
X_API_SECRET=your_x_api_secret_here
X_BEARER_TOKEN=your_x_bearer_token_here

# Frontend URL for OAuth redirects
FRONTEND_URL=http://localhost:3000
```

### 2. Get X API Credentials

1. Go to [X Developer Portal](https://developer.twitter.com/)
2. Create a new app or use existing one
3. Navigate to "Keys and Tokens"
4. Generate:
   - API Key and Secret
   - Bearer Token

### 3. Test the Setup

Run the test script to verify your credentials:

```bash
cd banbury-cloud-backend
python test_x_api.py
```

### 4. Restart Backend Server

After setting the environment variables, restart your backend server:

```bash
# Stop the current server (Ctrl+C)
# Then restart
python manage.py runserver 0.0.0.0:8080
```

## What Was Fixed

1. **Frontend OAuth Callback**: Now correctly points to backend OAuth endpoint
2. **Backend Redirect**: Now redirects to full frontend URL after OAuth completion
3. **OAuth Flow**: Properly configured with callback URL parameter

## Expected Flow

1. User clicks "Connect X Account" in settings
2. Frontend calls backend OAuth initiation with correct callback URL
3. User is redirected to X for authorization
4. X redirects back to backend OAuth callback
5. Backend processes OAuth and redirects to frontend settings page
6. User sees successful connection status

## Troubleshooting

If you still get errors:

1. Check that all environment variables are set
2. Verify X API credentials are valid
3. Ensure backend is running on port 8080
4. Ensure frontend is running on port 3000
5. Check browser console for any JavaScript errors
