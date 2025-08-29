# X API Integration Setup

This document explains how to set up X (Twitter) API integration for the Banbury backend.

## Prerequisites

1. X Developer Account with API access
2. X API v2 access (Basic or higher)
3. OAuth 1.0a credentials for posting tweets

## Environment Variables

Add the following environment variables to your `.env` file:

```bash
# X API Credentials
X_API_KEY=your_x_api_key_here
X_API_SECRET=your_x_api_secret_here
X_BEARER_TOKEN=your_x_bearer_token_here

# For posting tweets (OAuth 1.0a)
X_ACCESS_TOKEN=your_x_access_token_here
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret_here
```

## Getting X API Credentials

1. Go to [X Developer Portal](https://developer.twitter.com/)
2. Create a new app or use an existing one
3. Navigate to "Keys and Tokens"
4. Generate the following:
   - API Key and Secret
   - Bearer Token (for read-only operations)
   - Access Token and Secret (for posting tweets)

## API Endpoints

The following endpoints are available:

### GET /authentication/x_api/user_info/
Get user information by username or user ID
- Parameters: `username` or `user_id`

### GET /authentication/x_api/user_tweets/
Get recent tweets from a user
- Parameters: `username` or `user_id`, `max_results`, `exclude_retweets`, `exclude_replies`

### GET /authentication/x_api/search_tweets/
Search for tweets
- Parameters: `query`, `max_results`, `language`, `result_type`

### GET /authentication/x_api/trending_topics/
Get trending topics for a location
- Parameters: `woeid`, `count`

### POST /authentication/x_api/post_tweet/
Post a new tweet
- Body: `text`, `reply_to_tweet_id`, `media_ids`

## Frontend Integration

The X API tools are available in the LangGraph agent and can be enabled/disabled via tool preferences:

```typescript
// Enable X API tools
const toolPreferences = {
  x_api: true,
  // ... other preferences
};
```

## Security Notes

- X API access is disabled by default for security
- Users must explicitly enable X API tools in their preferences
- All API calls are proxied through the backend for security
- Rate limiting is handled at the backend level

## Rate Limits

X API has the following rate limits:
- User lookup: 300 requests per 15 minutes
- Tweet lookup: 300 requests per 15 minutes
- Search: 180 requests per 15 minutes
- Post tweet: 300 requests per 3 hours

The backend implements appropriate rate limiting and error handling.
