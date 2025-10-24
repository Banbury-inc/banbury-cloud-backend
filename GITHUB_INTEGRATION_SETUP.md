# GitHub Integration Setup Guide

This guide will help you set up the GitHub integration for the Banbury backend.

## Prerequisites

- A GitHub account
- Backend server running
- Admin access to create a GitHub OAuth App

## Step 1: Create a GitHub OAuth App

1. Go to https://github.com/settings/developers
2. Click **"OAuth Apps"** in the sidebar
3. Click **"New OAuth App"**
4. Fill in the application details:
   - **Application name**: `Banbury AI Assistant` (or your preferred name)
   - **Homepage URL**: Your application homepage (e.g., `http://localhost:3000` for development)
   - **Application description**: Optional description of your app
   - **Authorization callback URL**: 
     - For local development: `http://localhost:8080/authentication/github/oauth_callback/`
     - For production: `https://your-backend-domain.com/authentication/github/oauth_callback/`
5. Click **"Register application"**

## Step 2: Get Your Credentials

After creating the app, you'll see:
1. **Client ID** - Copy this value
2. **Client Secret** - Click **"Generate a new client secret"** and copy the value
   - ⚠️ **Important**: Save the client secret immediately, you won't be able to see it again!

## Step 3: Configure Backend Environment Variables

Add the following variables to your backend environment (`.env` file or hosting platform):

```bash
# GitHub OAuth Credentials
GH_CLIENT_ID=your_client_id_here
GH_CLIENT_SECRET=your_client_secret_here

# Frontend URL for OAuth redirects
FRONTEND_URL=http://localhost:3000  # or your production URL
```

### For Production

If you're deploying to a platform like Heroku, Railway, Google Cloud Run, or similar:

1. Add the environment variables through your platform's dashboard or CLI
2. Update the authorization callback URL in your GitHub OAuth App settings to match your production backend URL
3. Ensure `FRONTEND_URL` points to your production frontend URL

## Step 4: Configure OAuth Scopes

The integration requests the following scopes by default (configured in `github_views.py`):

- **repo** - Full control of private repositories (includes read/write access)
- **read:org** - Read org and team membership, read org projects
- **user:email** - Access user email addresses (read-only)
- **gist** - Create and manage gists
- **notifications** - Access notifications

### Customizing Scopes

To modify the requested scopes, edit the `scopes` list in `/apps/authentication/github_views.py`:

```python
# Required GitHub OAuth scopes
scopes = [
    'repo',
    'read:org',
    'user:email',
    'gist',
    'notifications',
]
```

Available GitHub OAuth scopes: https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps

## Step 5: Test the Integration

### Frontend Testing

1. Start your frontend application
2. Navigate to Settings → Connections
3. Find the "GitHub Integration" section
4. Click **"Connect"**
5. You'll be redirected to GitHub to authorize the application
6. After authorizing, you'll be redirected back and see the connection status

### Backend Testing

You can test the backend endpoints directly:

```bash
# Set your JWT token
export JWT_TOKEN="your_jwt_token_here"

# Check connection status
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:8080/authentication/github/status/

# List repositories
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:8080/authentication/github/repos/

# Get a specific repository
curl -H "Authorization: Bearer $JWT_TOKEN" \
  http://localhost:8080/authentication/github/repos/owner/repo-name/
```

## Available Endpoints

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/authentication/github/status/` | Check connection status |
| POST | `/authentication/github/initiate_oauth/` | Start OAuth flow |
| GET | `/authentication/github/oauth_callback/` | OAuth callback handler |
| POST | `/authentication/github/disconnect/` | Disconnect GitHub account |

### API Proxy Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/authentication/github/repos/` | List user's repositories |
| GET | `/authentication/github/repos/{owner}/{repo}/` | Get repository details |
| GET | `/authentication/github/repos/{owner}/{repo}/issues/` | List repository issues |
| GET | `/authentication/github/repos/{owner}/{repo}/pulls/` | List pull requests |
| GET | `/authentication/github/repos/{owner}/{repo}/contents/` | Get file contents |
| POST | `/authentication/github/issues/create/` | Create an issue |
| GET | `/authentication/github/search/code/` | Search code |

## Security Best Practices

### 1. Token Storage

Tokens are stored in MongoDB in the user document:

```json
{
  "username": "user123",
  "github_credentials": {
    "access_token": "gho_...",
    "username": "github_username",
    "name": "User Name",
    "avatar_url": "https://...",
    "connected_at": "2023-10-24T..."
  }
}
```

**Recommendation**: Encrypt tokens before storing in production:

```python
# Add encryption when storing
from cryptography.fernet import Fernet

def encrypt_token(token, encryption_key):
    f = Fernet(encryption_key)
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token, encryption_key):
    f = Fernet(encryption_key)
    return f.decrypt(encrypted_token.encode()).decode()
```

### 2. Environment Variables

- Never commit `.env` files to version control
- Use secrets management services in production (AWS Secrets Manager, Google Secret Manager, etc.)
- Rotate client secrets periodically
- Use different OAuth apps for development and production

### 3. Rate Limiting

GitHub has rate limits for their API:
- **Authenticated requests**: 5,000 requests per hour
- **Search API**: 30 requests per minute
- **GraphQL API**: 5,000 points per hour

Consider implementing rate limiting on your backend to prevent exceeding these limits.

### 4. Webhook Security (Future Enhancement)

If you plan to add GitHub webhooks:
- Validate webhook signatures
- Use HTTPS only
- Implement replay attack prevention
- Store webhook secrets securely

## Troubleshooting

### Issue: "GitHub credentials not configured"

**Solution**: Ensure `GH_CLIENT_ID` and `GH_CLIENT_SECRET` are set in your environment variables.

```bash
# Check if variables are set
echo $GH_CLIENT_ID
echo $GH_CLIENT_SECRET
```

### Issue: "Invalid OAuth state"

**Solution**: This usually happens when:
1. The OAuth flow was initiated from a different server instance
2. The user document was cleared during OAuth flow
3. Browser cookies/session expired

Try initiating the OAuth flow again.

### Issue: OAuth callback not working

**Solution**: 
1. Verify the callback URL in your GitHub OAuth App settings matches your backend URL
2. Check that `/authentication/github/oauth_callback/` is in the middleware excluded paths
3. Ensure your backend is accessible from the internet (for production)

### Issue: API requests returning 401 Unauthorized

**Solution**:
1. Verify the user is connected (check connection status)
2. Ensure the access token is valid (GitHub tokens don't expire by default, but can be revoked)
3. Check if the required scopes are authorized

### Issue: Cannot access private repositories

**Solution**: Ensure the `repo` scope is included and the user has authorized it during OAuth flow.

## Production Deployment Checklist

- [ ] Create production GitHub OAuth App with production callback URL
- [ ] Set `GH_CLIENT_ID` and `GH_CLIENT_SECRET` environment variables
- [ ] Set `FRONTEND_URL` to production frontend URL
- [ ] Verify callback URL is accessible and HTTPS
- [ ] Test OAuth flow end-to-end
- [ ] Implement token encryption for stored credentials
- [ ] Set up monitoring for API rate limits
- [ ] Configure error logging and alerting
- [ ] Review and minimize requested OAuth scopes
- [ ] Document the integration for your team

## Additional Resources

- [GitHub OAuth Documentation](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps)
- [GitHub REST API Documentation](https://docs.github.com/en/rest)
- [GitHub API Rate Limiting](https://docs.github.com/en/rest/overview/resources-in-the-rest-api#rate-limiting)
- [OAuth Scopes for GitHub Apps](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/scopes-for-oauth-apps)

## Next Steps

After setting up the GitHub integration:

1. **Add GitHub Tools to AI Assistant** - Create tools that leverage the GitHub API for your AI assistant
2. **Implement Webhooks** - Set up webhooks to receive real-time updates from GitHub
3. **Add GraphQL Support** - Use GitHub's GraphQL API for more complex queries
4. **Create Custom Workflows** - Build automated workflows using the GitHub integration
5. **Add Team Features** - Extend support for GitHub Organizations and Teams

## Support

If you encounter issues not covered in this guide:
1. Check the backend logs for detailed error messages
2. Verify all environment variables are correctly set
3. Ensure your MongoDB connection is working
4. Test the OAuth flow in an incognito window to rule out browser cache issues

