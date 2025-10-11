# Claude Authentication Setup Guide

This guide explains how to authenticate robo-trader with your Claude subscription instead of using an API key.

## Authentication Architecture

The robo-trader uses the **Claude Agent SDK**, which communicates with the **Claude Code CLI**. The CLI handles authentication automatically using your Claude subscription.

```
robo-trader app
    ↓ uses
claude_agent_sdk (Python)
    ↓ communicates with
claude CLI (Node.js command)
    ↓ authenticated via
Your Claude Pro/Team subscription
```

**Key Point**: The SDK does NOT use `ANTHROPIC_API_KEY`. It uses the `claude` CLI command, which authenticates via your browser session.

## Prerequisites

1. **Claude Subscription**: Claude Pro or Claude Team subscription
2. **Claude CLI Installed**: Already installed at `/Users/gurusharan/.nvm/versions/node/v23.7.0/bin/claude`
3. **Python SDK Installed**: Already installed (version 0.1.0)

## Setup Steps

### Step 1: Authenticate Claude CLI

Run this command in your terminal:

```bash
claude auth login
```

This will:
1. Open your browser to the Claude authentication page
2. Ask you to sign in with your Claude account
3. Store authentication credentials locally
4. Return confirmation when complete

### Step 2: Verify Authentication

Test that authentication worked:

```bash
claude --print "Hello, test authentication"
```

If you see a response from Claude, authentication is working.

### Step 3: Remove or Comment Out API Key

Edit your `.env` file:

```bash
# Option 1: Comment out the API key
# ANTHROPIC_API_KEY=sk-ant-api03-...

# Option 2: Remove the line entirely
# (Just delete the ANTHROPIC_API_KEY line)
```

### Step 4: Start the Application

```bash
cd /Users/gurusharan/Documents/remote-claude/robo-trader
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000
```

You should see in the logs:

```
✓ Claude Agent SDK will use Claude Code CLI auth via subscription
Orchestrator initialized successfully
```

## Verification

### Check Authentication Status

The application logs will show authentication details on startup. Look for:

```
✓ Claude Agent SDK will use Claude Code CLI auth via subscription
Claude API authenticated successfully via claude_code_cli_subscription
```

### Check via API Endpoint

Visit: http://localhost:8000/api/system/status

Look for the `claude_status` section:

```json
{
  "claude_status": {
    "is_valid": true,
    "api_key_present": false,
    "account_info": {
      "auth_method": "claude_code_cli_subscription",
      "subscription": "active",
      "note": "SDK uses CLI authentication (API key not required)"
    },
    "status": "connected"
  }
}
```

## Troubleshooting

### Error: "Claude Code CLI not authenticated"

**Solution**: Run `claude auth login` and complete the browser authentication flow.

### Error: "claude: command not found"

**Solution**: Your Node.js environment might not be initialized. Try:

```bash
source ~/.zshrc  # or ~/.bashrc
which claude
```

If still not found, reinstall:

```bash
npm install -g @anthropic-ai/claude-code
```

### Authentication Timeout

The CLI check has a 10-second timeout. If it takes longer:

1. Check your internet connection
2. Try authenticating manually: `claude auth login`
3. Verify with a test query: `claude --print "test"`

### Rate Limits

Claude subscriptions have usage limits:
- **Claude Pro**: Weekly usage limits
- **Claude Team**: Higher limits based on plan

If rate limited, the application will detect this and show:

```json
{
  "rate_limit_info": {
    "limited": true,
    "type": "weekly",
    "resets_at": "12:00 AM"
  }
}
```

The application will continue to work once limits reset.

## Authentication Methods Comparison

| Feature | Claude CLI (Subscription) | API Key |
|---------|---------------------------|---------|
| **Cost** | Included in subscription | Pay-per-use |
| **Setup** | `claude auth login` | Get from console.anthropic.com |
| **Used by SDK** | ✓ Yes | ✗ No |
| **Rate Limits** | Subscription limits | Token-based limits |
| **Best For** | Personal use, development | Production APIs, automation |

## Important Notes

1. **API Key is NOT Used by SDK**: Even if you set `ANTHROPIC_API_KEY`, the Claude Agent SDK will NOT use it. The SDK only communicates with the Claude CLI.

2. **Subscription Required**: You must have an active Claude Pro or Team subscription for CLI authentication to work.

3. **Session Persistence**: CLI authentication persists across terminal sessions. You only need to run `claude auth login` once.

4. **No Environment Variables Needed**: When using CLI authentication, you don't need to set any environment variables for Claude.

5. **Works in Virtual Environments**: CLI authentication works regardless of Python virtual environment, since it's a system-level Node.js command.

## Advanced: Using Both Methods

If you want to use API key for other purposes (e.g., direct Anthropic client calls for testing):

```python
from anthropic import Anthropic

api_key = os.getenv("ANTHROPIC_API_KEY")
if api_key:
    client = Anthropic(api_key=api_key)
```

But remember: The robo-trader's SDK integration will still use CLI authentication, not the API key.

## Files Modified

This setup involved updating:

1. `/Users/gurusharan/Documents/remote-claude/robo-trader/.env.example` - Documentation of auth methods
2. `/Users/gurusharan/Documents/remote-claude/robo-trader/src/auth/claude_auth.py` - Authentication validation logic
3. This guide: `CLAUDE_AUTH_SETUP.md`

## Next Steps

After authentication is working:

1. Test basic queries through the web UI
2. Monitor logs for rate limit warnings
3. If you hit subscription limits, consider:
   - Waiting for limit reset
   - Upgrading to Claude Team
   - Using an API key for high-volume usage

## Support

For authentication issues:
- Claude CLI issues: https://docs.claude.com/en/docs/claude-code
- Subscription: https://claude.ai/settings
- API Keys: https://console.anthropic.com/
