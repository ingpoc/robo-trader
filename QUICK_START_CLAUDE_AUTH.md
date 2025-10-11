# Quick Start: Claude Subscription Authentication

## TL;DR - 3 Commands to Switch to Claude Subscription

```bash
# 1. Authenticate with your Claude subscription
claude auth login

# 2. Test authentication
python test_claude_cli_auth.py

# 3. Start the app (no API key needed!)
uvicorn src.web.app:app --reload
```

That's it! Your robo-trader will now use your Claude subscription instead of an API key.

---

## What Just Happened?

### Before
```
App → ANTHROPIC_API_KEY → Anthropic API → Pay per token
```

### After
```
App → Claude CLI → Your Claude Subscription → Included in subscription
```

**No additional cost** - uses your existing Claude Pro/Team subscription.

---

## Verification

### Check in Terminal
```bash
# Should see this in application logs:
✓ Claude Agent SDK will use Claude Code CLI auth via subscription
Claude API authenticated successfully via claude_code_cli_subscription
```

### Check in Browser
Visit: http://localhost:8000/api/system/status

Look for:
```json
{
  "claude_status": {
    "is_valid": true,
    "account_info": {
      "auth_method": "claude_code_cli_subscription"
    }
  }
}
```

---

## Update Your .env File

Edit `/Users/gurusharan/Documents/remote-claude/robo-trader/.env`:

```bash
# Comment out or remove the API key line
# ANTHROPIC_API_KEY=sk-ant-api03-...

# That's it! CLI auth works without any environment variables
```

---

## Troubleshooting (One-Liners)

**CLI not found?**
```bash
npm install -g @anthropic-ai/claude-code
```

**Auth failed?**
```bash
claude auth login
```

**Want to test?**
```bash
claude --print "Hello, test authentication"
```

**Rate limited?**
```bash
# Wait for reset or check status:
python test_claude_cli_auth.py
```

---

## Why This Works

The Python Agent SDK doesn't use API keys. It talks to the `claude` CLI command, which handles authentication via your browser session. Once you run `claude auth login`, the CLI stores your session and the SDK uses it automatically.

**No code changes needed** - your app was already set up to support this!

---

## Files You Can Read for Details

- **Setup Guide**: `CLAUDE_AUTH_SETUP.md` (step-by-step instructions)
- **Technical Analysis**: `AUTHENTICATION_ANALYSIS.md` (how it works)
- **Test Script**: `test_claude_cli_auth.py` (automated verification)

---

## What About Rate Limits?

Claude subscriptions have usage limits:
- **Claude Pro**: Weekly limits
- **Claude Team**: Higher limits

The app automatically detects and reports rate limits. They reset automatically.

---

## Can I Still Use an API Key?

The SDK doesn't support API keys - it only works with CLI authentication. If you need API key access, you'd need to use the direct Anthropic client (not the Agent SDK).

**For this app: Use Claude subscription via CLI auth** ✓

---

## One More Time: The Complete Setup

```bash
# Navigate to project
cd /Users/gurusharan/Documents/remote-claude/robo-trader

# Authenticate (opens browser)
claude auth login

# Edit .env (remove/comment API key)
# ANTHROPIC_API_KEY=...  # Comment this out

# Test everything
python test_claude_cli_auth.py

# Start the app
uvicorn src.web.app:app --reload

# Visit in browser
# http://localhost:8000
```

**Done!** 🎉

---

## Questions?

- Claude CLI docs: https://docs.claude.com/en/docs/claude-code
- Your subscription: https://claude.ai/settings
- Test authentication: `python test_claude_cli_auth.py`

---

**Key Takeaway**: You already have everything you need. Just run `claude auth login` and your app will use your Claude subscription automatically.
