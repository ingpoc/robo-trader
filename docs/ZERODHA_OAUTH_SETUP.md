# Zerodha OAuth Setup Guide

This guide explains how to configure Zerodha API authentication with the proper redirect URLs for your robo-trader application.

## Overview

The application now supports OAuth authentication with Zerodha Kite Connect API using redirect URLs that automatically adapt to different deployment environments.

## Redirect URL Configuration

### Environment-Specific Redirect URLs

The application automatically selects the appropriate redirect URL based on the environment:

1. **Development**: `http://localhost:8000/api/auth/zerodha/callback`
2. **Docker**: `http://robo-trader-app:8000/api/auth/zerodha/callback`
3. **Production**: `https://your-domain.com/api/auth/zerodha/callback`

### Configuration Steps

#### 1. Zerodha Developer Console Setup

1. Go to [https://kite.trade/apps/](https://kite.trade/apps/)
2. Login with your Zerodha credentials
3. Create a new app or edit existing app
4. Set the redirect URL based on your environment:
   - For local development: `http://localhost:8000/api/auth/zerodha/callback`
   - For Docker deployment: `http://robo-trader-app:8000/api/auth/zerodha/callback`
   - For production: `https://your-domain.com/api/auth/zerodha/callback`
5. Save your API Key and API Secret

#### 2. Application Configuration

Update your environment configuration:

**`.env` file:**
```bash
ZERODHA_API_KEY=your_actual_api_key_here
ZERODHA_API_SECRET=your_actual_api_secret_here
```

**`config/config.json`:**
```json
{
  "integration": {
    "zerodha_api_key": "your_actual_api_key_here",
    "zerodha_api_secret": "your_actual_api_secret_here",
    "zerodha_redirect_urls": {
      "development": "http://localhost:8000/api/auth/zerodha/callback",
      "docker": "http://robo-trader-app:8000/api/auth/zerodha/callback",
      "production": "https://your-domain.com/api/auth/zerodha/callback"
    }
  }
}
```

## OAuth Flow

### 1. Initiate Authentication

```bash
curl -X GET "http://localhost:8000/api/auth/zerodha/login?user_id=your_user_id"
```

Response:
```json
{
  "success": true,
  "auth_url": "https://kite.zerodha.com/connect?api_key=your_key&redirect_url=...&state=random_state",
  "state": "random_state",
  "redirect_url": "http://localhost:8000/api/auth/zerodha/callback",
  "message": "Please visit the authorization URL to authenticate with Zerodha"
}
```

### 2. User Authorization

1. User visits the `auth_url` returned in step 1
2. Login to Zerodha and grant permissions
3. Zerodha redirects to your callback URL with `request_token` and `state`

### 3. Handle Callback

Zerodha redirects to: `http://localhost:8000/api/auth/zerodha/callback?request_token=abc&state=random_state`

The application automatically:
- Validates the state parameter (CSRF protection)
- Exchanges the request token for an access token
- Stores the token securely
- Returns success response

### 4. Check Authentication Status

```bash
curl -X GET "http://localhost:8000/api/auth/zerodha/status"
```

Response:
```json
{
  "authenticated": true,
  "user_id": "ZERODHA_USER_ID",
  "login_time": "2024-01-26T10:30:00Z",
  "expires_at": "2024-01-27T10:30:00Z",
  "expires_in_hours": 23.5,
  "message": "Active Zerodha authentication found"
}
```

## API Endpoints

### Authentication Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/zerodha/login` | GET | Initiate OAuth flow |
| `/api/auth/zerodha/callback` | GET | Handle OAuth callback |
| `/api/auth/zerodha/status` | GET | Check authentication status |
| `/api/auth/zerodha/logout` | POST | Logout and clear tokens |
| `/api/auth/zerodha/redirect-info` | GET | Get current redirect URL |
| `/api/auth/zerodha/callback-page` | GET | HTML callback page (optional) |

### Rate Limiting

All OAuth endpoints are rate-limited to 10 requests per minute (configurable via `RATE_LIMIT_AUTH` environment variable).

## Token Management

### Token Storage

- Tokens are stored securely in `data/zerodha_oauth_token.json`
- Automatic atomic file writes prevent corruption
- Tokens expire after 24 hours (Zerodha policy)
- Automatic cleanup of expired tokens

### Security Features

- **State Parameter**: CSRF protection using secure random state tokens
- **Checksum Validation**: SHA256 checksum for token exchange
- **Token Expiry**: Automatic checking and cleanup of expired tokens
- **Secure Storage**: Atomic file operations for token persistence

## Error Handling

### Common Errors

1. **Invalid State Parameter**: State doesn't match or is expired
2. **Token Exchange Failed**: Invalid credentials or network issues
3. **Configuration Missing**: API key or secret not configured
4. **Rate Limit Exceeded**: Too many authentication attempts

### Error Response Format

```json
{
  "success": false,
  "error": "OAuth authentication failed",
  "message": "Invalid or expired OAuth state parameter",
  "category": "security",
  "code": "OAUTH_STATE_INVALID"
}
```

## Docker Deployment

For Docker deployments, ensure:

1. Set environment variable: `ENVIRONMENT=docker`
2. Use container name in redirect URL: `http://robo-trader-app:8000/api/auth/zerodha/callback`
3. Configure Zerodha app with the Docker redirect URL

## Production Deployment

For production deployments:

1. Set environment variable: `ENVIRONMENT=production`
2. Use HTTPS redirect URL: `https://your-domain.com/api/auth/zerodha/callback`
3. Configure SSL/TLS certificates
4. Update Zerodha app with production redirect URL

## Troubleshooting

### Issues and Solutions

1. **"Invalid redirect URL" Error**
   - Check Zerodha app configuration matches exactly
   - Ensure no trailing slashes or extra characters
   - Verify protocol (http vs https) matches environment

2. **"State parameter invalid" Error**
   - OAuth flow timed out (states expire after 10 minutes)
   - Clear browser cookies and restart flow
   - Check if multiple tabs/windows are interfering

3. **"Token exchange failed" Error**
   - Verify API key and secret are correct
   - Check if Zerodha app is active
   - Ensure system time is synchronized

4. **Port 8000 not accessible**
   - Check if application is running
   - Verify firewall settings
   - For Docker, check port mapping in docker-compose.yml

### Debug Mode

Enable debug logging:
```bash
LOG_LEVEL=DEBUG
```

Check logs for detailed OAuth flow information:
```bash
tail -f logs/app.log | grep "OAuth"
```

## Integration with Existing Services

The OAuth service integrates with:

- **Event Bus**: Emits OAuth events for system monitoring
- **DI Container**: Registered as singleton service
- **Error Handling**: Uses existing `TradingError` patterns
- **Configuration**: Integrates with existing config system
- **Logging**: Structured logging with correlation IDs

## Security Best Practices

1. **Environment Variables**: Never commit API keys to version control
2. **HTTPS**: Use HTTPS in production environments
3. **Rate Limiting**: Configurable rate limits prevent abuse
4. **State Validation**: Always validate OAuth state parameters
5. **Token Storage**: Secure file storage with atomic writes
6. **Expiration**: Automatic cleanup of expired tokens
7. **Logging**: Log authentication events for monitoring

## Testing

### Local Testing

1. Start the application: `python -m src.web.app`
2. Navigate to: `http://localhost:8000/api/auth/zerodha/login`
3. Follow the OAuth flow
4. Verify token storage in `data/zerodha_oauth_token.json`

### Automated Testing

The OAuth service includes comprehensive error handling and validation for automated testing scenarios.

## Support

For issues with Zerodha OAuth integration:

1. Check Zerodha API documentation: https://kite.trade/docs/connect/v1/
2. Verify app configuration in Zerodha developer console
3. Check application logs for detailed error information
4. Ensure redirect URLs match exactly between Zerodha and application config