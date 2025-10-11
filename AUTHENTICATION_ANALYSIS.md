# Claude Agent SDK Authentication Analysis

## Executive Summary

**Status**: ✓ Your robo-trader application is **already configured** to support Claude subscription authentication via Claude Code CLI.

**Action Required**: Authenticate the Claude CLI to use your Claude subscription instead of an API key.

**Impact**: No code changes needed for basic functionality. Updated authentication validation for accurate status reporting.

---

## Key Findings

### 1. Claude Agent SDK Does NOT Use ANTHROPIC_API_KEY

**Critical Discovery**: The Python `claude-agent-sdk` does NOT make direct API calls to Anthropic. Instead, it:

1. Spawns the `claude` CLI command (Node.js application)
2. Communicates with the CLI via stdin/stdout
3. The CLI handles authentication using your Claude subscription
4. No API key is passed or used by the SDK

**Evidence**:
- SDK documentation shows no API key parameter in `ClaudeAgentOptions`
- SDK requires Claude Code CLI to be installed (`@anthropic-ai/claude-code`)
- Error handling includes `CLINotFoundError` for missing CLI

### 2. Your Application Already Supports CLI Authentication

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/src/auth/claude_auth.py`

The `validate_claude_api()` function (lines 47-156) already includes:
- CLI authentication check via `check_claude_code_cli_auth()` (lines 66-90)
- Test execution: `claude --print test` to verify auth
- Rate limit detection from CLI output
- Fallback to API key validation if CLI not authenticated

**However**: The validation logic was backward - it checked CLI as fallback, when CLI should be primary.

### 3. SDK Client Initialization is Correct

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/src/core/orchestrator.py`

Lines 132-140 show `ClaudeAgentOptions` created without API key:

```python
self.options = ClaudeAgentOptions(
    allowed_tools=allowed_tools,
    permission_mode=self.config.permission_mode,
    mcp_servers=mcp_servers_dict,
    hooks=hooks,
    system_prompt=self._get_system_prompt(),
    cwd=self.config.project_dir,
    max_turns=self.config.max_turns,
)
```

**This is correct**. The SDK doesn't accept an API key parameter because it uses the CLI.

---

## Changes Made

### 1. Updated `.env.example`

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/.env.example`

**Changes**:
- Documented two authentication methods clearly
- Made ANTHROPIC_API_KEY optional and commented out
- Added instructions for `claude auth login`
- Clarified that SDK uses CLI authentication

**Before**:
```bash
# ===== REQUIRED: Claude AI API Key =====
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

**After**:
```bash
# ===== Claude AI Authentication =====
# METHOD 1 (RECOMMENDED): Claude Subscription via Claude Code CLI
#   - Use your existing Claude Pro/Team subscription
#   - Authenticate once: Run `claude auth login` in terminal
#   - No API key needed, no additional cost
# ...
# ANTHROPIC_API_KEY=sk-ant-api03-your-key-here  # (optional)
```

### 2. Fixed Authentication Validation

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/src/auth/claude_auth.py`

**Changes**:
- Prioritize CLI authentication check (now primary, not fallback)
- Warn if API key is set (since SDK won't use it)
- Return proper error messages guiding to `claude auth login`
- Mark API key validation as informational only

**Key Logic**:
```python
# Check CLI first (primary method)
cli_status = await check_claude_code_cli_auth()
if cli_status["authenticated"]:
    return ClaudeAuthStatus(is_valid=True, ...)

# If API key is set, warn that it's not used
if api_key:
    logger.warning("SDK uses CLI, not API key...")
    return ClaudeAuthStatus(is_valid=False, error="Run: claude auth login")

# No authentication found
return ClaudeAuthStatus(is_valid=False, error="Run: claude auth login")
```

### 3. Updated Error Messages

Changed error messages to guide users to correct authentication method:

- Old: "Set ANTHROPIC_API_KEY environment variable"
- New: "Run: claude auth login to authenticate with Claude subscription"

### 4. Fixed `.gitignore`

Removed `.env.example` from gitignore so it can be committed to repository as documentation.

### 5. Created Documentation

**Files Created**:
1. `CLAUDE_AUTH_SETUP.md` - Step-by-step setup guide
2. `test_claude_cli_auth.py` - Automated authentication test script
3. `AUTHENTICATION_ANALYSIS.md` - This technical analysis

---

## How to Use Your Claude Subscription

### Quick Start

```bash
# Step 1: Authenticate CLI (one-time setup)
claude auth login

# Step 2: Verify authentication
claude --print "Hello, test"

# Step 3: Remove or comment out API key in .env
# ANTHROPIC_API_KEY=...  (comment this out)

# Step 4: Start the application
cd /Users/gurusharan/Documents/remote-claude/robo-trader
uvicorn src.web.app:app --reload --host 0.0.0.0 --port 8000

# Step 5: Verify in logs
# Look for: "✓ Claude Agent SDK will use Claude Code CLI auth via subscription"
```

### Running the Test Script

```bash
cd /Users/gurusharan/Documents/remote-claude/robo-trader
python test_claude_cli_auth.py
```

The test script will:
1. Check if Claude CLI is installed
2. Verify CLI authentication status
3. Check API key configuration
4. Test full authentication flow
5. Verify SDK can be imported
6. Provide actionable next steps

---

## Technical Details

### Authentication Flow

```
┌─────────────────────────────────────┐
│  Robo Trader Application            │
│  (Python FastAPI)                   │
└──────────────┬──────────────────────┘
               │
               │ import claude_agent_sdk
               ▼
┌─────────────────────────────────────┐
│  Claude Agent SDK                   │
│  (Python library)                   │
└──────────────┬──────────────────────┘
               │
               │ subprocess.run(['claude', ...])
               ▼
┌─────────────────────────────────────┐
│  Claude Code CLI                    │
│  (Node.js command: claude)          │
└──────────────┬──────────────────────┘
               │
               │ Uses stored session token
               ▼
┌─────────────────────────────────────┐
│  Claude API                         │
│  (Authenticated via subscription)   │
└─────────────────────────────────────┘
```

### Authentication Storage

Claude CLI stores authentication in:
- macOS/Linux: `~/.config/claude/` (or similar)
- Authentication persists across terminal sessions
- Tokens refreshed automatically by CLI

### Rate Limits

**Claude Subscription Limits**:
- **Claude Pro**: Weekly usage limits
- **Claude Team**: Higher limits based on plan
- Limits reset automatically at scheduled time

**Detection**:
```python
cli_status = await check_claude_code_cli_auth()
rate_limit_info = cli_status.get('rate_limit_info', {})

if rate_limit_info.get('limited'):
    print(f"Rate limited: {rate_limit_info['type']}")
    print(f"Resets at: {rate_limit_info.get('resets_at')}")
```

---

## Environment Variables

### Required: None (for CLI auth)

When using Claude subscription, no environment variables are required.

### Optional: ANTHROPIC_API_KEY

Only set if you want to validate API key availability (not used by SDK):

```bash
# .env file
# ANTHROPIC_API_KEY=sk-ant-api03-...  (optional, not used by SDK)
```

**Note**: Even if set, the SDK will NOT use this key. It's only validated for informational purposes.

---

## Comparison: API Key vs Subscription

| Feature | Claude Subscription (CLI) | API Key |
|---------|---------------------------|---------|
| **Authentication Method** | `claude auth login` (browser) | Environment variable |
| **Used by SDK** | ✓ Yes (automatic) | ✗ No (SDK doesn't support) |
| **Cost Model** | Included in subscription | Pay-per-token |
| **Rate Limits** | Weekly/daily subscription limits | Token-based rate limits |
| **Setup Complexity** | One-time browser auth | Get key from console |
| **Best For** | Development, personal use | Production APIs, automation |
| **Requires** | Active Claude Pro/Team | API access enabled |
| **Session Persistence** | Automatic (stored by CLI) | Must be in environment |

---

## Verification Checklist

After setup, verify:

- [ ] Claude CLI installed: `claude --version`
- [ ] CLI authenticated: `claude --print "test"`
- [ ] Test script passes: `python test_claude_cli_auth.py`
- [ ] Application starts without errors
- [ ] Logs show: "Claude Agent SDK will use Claude Code CLI auth"
- [ ] Status endpoint shows: `"auth_method": "claude_code_cli_subscription"`
- [ ] Can query AI: Test through web UI

---

## Common Issues & Solutions

### Issue: "Claude Code CLI not authenticated"

**Cause**: CLI not authenticated or session expired

**Solution**:
```bash
claude auth login
# Complete browser authentication
# Restart application
```

### Issue: "command not found: claude"

**Cause**: CLI not installed or not in PATH

**Solution**:
```bash
npm install -g @anthropic-ai/claude-code
# Or add to PATH: export PATH="$PATH:~/.nvm/versions/node/v23.7.0/bin"
```

### Issue: Rate limit errors

**Cause**: Subscription usage limit reached

**Solution**:
- Wait for automatic reset (check `resets_at` in rate_limit_info)
- Upgrade to Claude Team for higher limits
- Use API key for high-volume usage

### Issue: API key warnings in logs

**Cause**: ANTHROPIC_API_KEY is set but not used

**Solution**:
```bash
# Edit .env file
# Comment out or remove:
# ANTHROPIC_API_KEY=...
```

---

## Files Modified

### Changed Files

1. `/Users/gurusharan/Documents/remote-claude/robo-trader/.env.example`
   - Documented authentication methods
   - Made API key optional
   - Added CLI auth instructions

2. `/Users/gurusharan/Documents/remote-claude/robo-trader/src/auth/claude_auth.py`
   - Prioritized CLI authentication
   - Fixed validation logic
   - Updated error messages
   - Added warnings for unused API key

3. `/Users/gurusharan/Documents/remote-claude/robo-trader/.gitignore`
   - Removed `.env.example` (now tracked for documentation)

### Created Files

1. `CLAUDE_AUTH_SETUP.md` - User-facing setup guide
2. `test_claude_cli_auth.py` - Automated test script
3. `AUTHENTICATION_ANALYSIS.md` - This technical analysis

### Unchanged Files (Already Correct)

1. `/Users/gurusharan/Documents/remote-claude/robo-trader/src/core/orchestrator.py`
   - SDK initialization is correct (no API key passed)
   - No changes needed

2. `/Users/gurusharan/Documents/remote-claude/robo-trader/requirements.txt`
   - SDK already specified: `claude-agent-sdk>=0.0.23`
   - No changes needed

---

## Next Steps

### Immediate Actions

1. **Authenticate CLI**:
   ```bash
   claude auth login
   ```

2. **Run Test Script**:
   ```bash
   python test_claude_cli_auth.py
   ```

3. **Update .env**:
   ```bash
   # Comment out or remove ANTHROPIC_API_KEY
   vim .env
   ```

4. **Start Application**:
   ```bash
   uvicorn src.web.app:app --reload
   ```

5. **Verify in Browser**:
   - http://localhost:8000/api/system/status
   - Check `claude_status.auth_method` = "claude_code_cli_subscription"

### Optional Enhancements

1. **Add health check endpoint** that tests actual SDK query
2. **Add UI indicator** showing current auth method
3. **Add rate limit warning** in UI when approaching limits
4. **Add auto-retry logic** when rate limited
5. **Add fallback to API key** if subscription temporarily unavailable

---

## SDK Version Information

**Current Installation**:
- Package: `claude-agent-sdk`
- Version: `0.1.0`
- Location: `/Users/gurusharan/.pyenv/versions/3.12.0/lib/python3.12/site-packages`
- Dependencies: `anyio`, `mcp`

**Minimum Requirements** (per docs):
- Python 3.10+
- Node.js (for Claude CLI)
- Claude Code 2.0.0+

**Your Environment**:
- Python: 3.12.0 ✓
- Node.js: v23.7.0 ✓
- Claude CLI: Installed ✓

---

## Conclusion

Your robo-trader application is **already architectured correctly** for Claude subscription authentication. The SDK integration requires no code changes to support CLI authentication.

The updates made were primarily:
1. **Documentation** - Clarifying the two authentication methods
2. **Validation Logic** - Fixing priority order (CLI first, not API key)
3. **Error Messages** - Guiding users to correct authentication
4. **Testing Tools** - Automated verification of setup

**To start using your Claude subscription right now**:
```bash
claude auth login  # One-time setup
python test_claude_cli_auth.py  # Verify
# Remove ANTHROPIC_API_KEY from .env
uvicorn src.web.app:app --reload  # Start app
```

That's it. No code changes required for the core functionality.
