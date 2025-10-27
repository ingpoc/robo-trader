# Claude Agent SDK Setup Guide for Robo Trader

## Understanding the Architecture

Your Robo Trader application is **SDK-ONLY** - it uses Claude Agent SDK exclusively for all AI functionality. This means:

- ✅ **NO direct Anthropic API key** needed in environment variables
- ✅ **NO `ANTHROPIC_API_KEY` environment variable** required
- ✅ **Subscription-based authentication** via Claude Code CLI
- ✅ **Secure authentication** using your Claude Pro subscription

This is a superior architecture because:
1. **Authentication managed by Claude Code** - No secrets in environment
2. **Subscription-based** - Charges go through your Claude account
3. **Tool execution** - SDK handles all tool management
4. **Session management** - Proper conversation management
5. **Error recovery** - Built-in retry logic

---

## How Claude Agent SDK Authentication Works

```
┌─────────────────────────────────────────────────────────┐
│           Your Robo Trader Application                   │
│   (src/services/claude_agent/sdk_auth.py)               │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Communicates with
                     ▼
┌─────────────────────────────────────────────────────────┐
│        Claude Agent SDK (claude-agent-sdk package)      │
│   - Handles tool execution                              │
│   - Manages conversation sessions                       │
│   - Implements error recovery                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ Uses credentials from
                     ▼
┌─────────────────────────────────────────────────────────┐
│       Claude Code CLI (installed separately)            │
│   - Stores your authentication token                    │
│   - Communicates with Anthropic servers                │
│   - Validates your Claude Pro subscription             │
└─────────────────────────────────────────────────────────┘
                     │
                     │ Connects to
                     ▼
┌─────────────────────────────────────────────────────────┐
│              Anthropic API (Cloud)                      │
│   - Claude models (claude-3-5-sonnet, etc.)            │
│   - Your Claude Pro subscription                        │
│   - API rate limits and usage tracking                 │
└─────────────────────────────────────────────────────────┘
```

**Key Point**: No API key ever appears in your code or environment variables!

---

## Setup Steps

### Step 1: Verify Prerequisites

```bash
# Check Python version (3.10+ required)
python --version
# Output should be: Python 3.10.x or higher

# Check pip is available
pip --version

# List installed packages related to Claude
pip list | grep -i claude
# Should show: claude-agent-sdk
```

### Step 2: Install Claude Code CLI

The Claude Agent SDK communicates with Claude Code CLI, which is your gateway to Anthropic's servers.

**On macOS**:
```bash
# Install using Homebrew (recommended)
brew install anthropic/brew/claude

# Or download directly from:
# https://docs.anthropic.com/claude/docs/desktop-setup
```

**On Linux**:
```bash
# Download from: https://docs.anthropic.com/claude/docs/desktop-setup
# Extract and add to PATH

curl -fsSL https://install.anthropic.com/linux/install.sh | bash
```

**On Windows**:
```powershell
# Download installer from:
# https://docs.anthropic.com/claude/docs/desktop-setup

# Or use Scoop (if installed):
scoop install claude
```

**Verify installation**:
```bash
claude --version
# Output should be: claude version X.Y.Z
```

### Step 3: Authenticate with Claude Code CLI

This is where you connect your Claude Pro subscription:

```bash
# Start authentication
claude auth login

# What happens next:
# 1. A browser window opens
# 2. You see: "Authorize Claude Code to access Anthropic API"
# 3. You log in with your Anthropic account
# 4. You confirm you have a Claude Pro subscription
# 5. You authorize the CLI to use your account
# 6. Browser closes and CLI shows: "Successfully authenticated"
```

**Verify authentication**:
```bash
# Test that CLI is authenticated
claude --print "test"

# Output should be something like:
# test
# (proves the CLI can communicate with Anthropic servers)
```

### Step 4: Verify .env Configuration

The `.env` file should **NOT** have `ANTHROPIC_API_KEY`:

```bash
# Check current .env
cat .env | grep ANTHROPIC_API_KEY
# Should output nothing (or just a comment)

# If it exists, remove it:
sed -i '' '/^ANTHROPIC_API_KEY=/d' .env

# Verify it's gone
grep -i anthropic .env
# Should only see comments about Claude Agent SDK
```

### Step 5: Start Robo Trader Application

Now that Claude Code is authenticated, the application can use it:

```bash
# Terminal 1: Start backend
python -m src.main --command web

# Expected output (within ~5 seconds):
# INFO | src.auth.claude_auth:validate_claude_sdk_auth
# ✓ Claude Agent SDK authenticated via Claude Code CLI (subscription)

# INFO | uvicorn
# Uvicorn running on http://0.0.0.0:8000
```

```bash
# Terminal 2: Start frontend (from ui/ directory)
cd ui
npm run dev

# Expected output:
# VITE v4.5.14 ready in 105 ms
# Local: http://localhost:3000/
```

---

## Troubleshooting

### Error: "Claude Agent SDK not authenticated - Claude Code CLI not available"

**Cause**: Claude Code CLI not installed or not authenticated.

**Fix**:
```bash
# Step 1: Verify CLI is installed
which claude
# If not found, install it (see Step 2 above)

# Step 2: Verify it's authenticated
claude --print "test"
# If this fails, run: claude auth login

# Step 3: Restart the application
python -m src.main --command web
```

### Error: "Claude CLI version check timed out"

**Cause**: Claude CLI is slow to respond (usually temporary).

**Fix**:
```bash
# Wait a few seconds and try again
sleep 3
python -m src.main --command web

# If it persists:
# 1. Check network connection
# 2. Verify CLI authentication: claude --print "test"
# 3. Try: claude auth login again
```

### Error: "ANTHROPIC_API_KEY found but not in OAuth format"

**Cause**: You have an `ANTHROPIC_API_KEY` in your environment but it's not a valid OAuth token.

**Fix**:
```bash
# Option 1: Remove it from .env
sed -i '' '/^ANTHROPIC_API_KEY=/d' .env

# Option 2: If you have an OAuth token (sk-ant-oat*), set it:
export ANTHROPIC_API_KEY="sk-ant-oat-your-token-here"

# But generally, just use Claude Code CLI (recommended)
unset ANTHROPIC_API_KEY
python -m src.main --command web
```

### Port 8000 Already in Use

**Cause**: Previous application instance still running.

**Fix**:
```bash
# Find the process
lsof -i :8000

# Kill it
kill -9 <PID>

# Or kill all Python processes (be careful!)
pkill -f "python -m src.main"

# Wait a moment for port to be released
sleep 2

# Try again
python -m src.main --command web
```

---

## How the Application Uses Claude Agent SDK

### 1. Initialization Phase

When the application starts:

```python
# src/auth/claude_auth.py
async def validate_claude_sdk_auth():
    # Check if Claude Code CLI is installed and authenticated
    cli_status = await check_claude_code_cli_auth()

    if cli_status["authenticated"]:
        logger.info("✓ Claude Agent SDK authenticated")
        return ClaudeAuthStatus(is_valid=True, ...)
```

### 2. Session Management

Once authenticated, the SDK manages your Claude conversation:

```python
# src/services/claude_agent/sdk_auth.py
async def create_sdk_session():
    # Creates a new session with Claude
    # - Prepares tools/capabilities
    # - Sets up error handling
    # - Ready for natural language queries
```

### 3. Tool Execution

When your trading system needs Claude analysis:

```python
# Inside services, when performing AI operations:
options = ClaudeAgentOptions(
    allowed_tools=["analyze_portfolio", "technical_analysis", ...],
    system_prompt="You are an expert trading assistant..."
)
sdk_client = ClaudeSDKClient(options=options)

# Send a query to Claude
await sdk_client.query("Analyze my portfolio and suggest trades")

# Receive response with tool calls
async for response in sdk_client.receive_response():
    # Process Claude's response and tool calls
    ...
```

---

## What Gets Charged to Your Account?

Your Claude Pro subscription includes:

- **API usage**: All Claude model calls made by Robo Trader
- **Tool execution**: Calls to analyze_portfolio, screening, etc.
- **Rate limits**: Standard Claude Pro rate limits apply
- **Monthly cost**: Single Claude Pro subscription fee (~$20/month)

**What you DON'T pay extra for**:
- SDK usage (included in Claude Pro)
- Claude Code CLI (free)
- Robo Trader code execution (runs on your machine)

---

## Architecture Diagram: SDK-Only Design

```
Robo Trader Application Flow
════════════════════════════════════════════════════════════

1. User Query
   └─> "What should I buy today?"

2. Application (src/web/app.py)
   └─> Orchestrator receives query

3. Query Processing
   ├─> Portfolio Service: Load current holdings
   ├─> Market Data Service: Fetch latest prices
   └─> Technical Analysis: Calculate indicators

4. Claude SDK Interface
   ├─> SessionCoordinator validates SDK auth
   │   └─> Checks: Is Claude Code CLI authenticated?
   ├─> Creates SDK session with tools
   │   └─> allowed_tools: [analyze_portfolio, screening, ...]
   └─> Sends query to Claude Agent SDK

5. Claude Agent SDK (Your Responsibility)
   ├─> Communicates with Claude Code CLI
   ├─> CLI retrieves auth token from local storage
   └─> Sends encrypted request to Anthropic servers

6. Anthropic Cloud (Claude Model)
   ├─> Receives request with your subscription
   ├─> Processes query: "Analyze portfolio..."
   ├─> Calls appropriate tools on trading data
   └─> Returns analysis with recommendations

7. SDK Response Handling
   ├─> Receive Claude's tool calls and reasoning
   ├─> Execute recommended actions
   │   ├─> Buy/Sell orders (paper trading)
   │   ├─> Risk calculations
   │   └─> Update portfolio
   └─> Stream response to user

8. Result Display
   └─> WebSocket updates to UI
       └─> User sees: "Buy 50 shares of TCS"
           with reasoning: "RSI oversold, MACD bullish"
```

---

## Key Differences: SDK vs Direct API

| Aspect | SDK (Your Setup) | Direct API |
|--------|------------------|------------|
| **Auth Storage** | Claude Code CLI | .env file (insecure) |
| **API Key Exposure** | Never | In environment |
| **Session Management** | SDK handles | Manual implementation |
| **Tool Execution** | Automatic | Manual serialization |
| **Error Recovery** | Built-in | Must implement |
| **Rate Limiting** | SDK manages | Must track manually |
| **Cost** | Claude Pro subscription | Pay-as-you-go |
| **Security** | ✅ High | ❌ Lower |
| **Complexity** | ✅ Simple | ❌ Complex |

---

## Common Questions

### Q: Will my API key ever be in the code?
**A**: No. The SDK-only design ensures your authentication is managed by Claude Code CLI, never in your application code.

### Q: Can I use a different authentication method?
**A**: You have two options:
1. **Claude Code CLI** (recommended) - Uses your Claude Pro subscription
2. **OAuth token** - If you have one, set `ANTHROPIC_API_KEY=sk-ant-oat-...` (advanced users)

### Q: What if I cancel my Claude Pro subscription?
**A**: The application will fail with authentication error on startup. You'd need to:
- Reactivate Claude Pro, or
- Get an OAuth token from Anthropic, or
- Implement a fallback non-AI mode

### Q: Can I run this in Docker?
**A**: Yes, but Claude Code CLI must be set up on the host machine first. See CONTAINER_NETWORKING.md for details.

### Q: Is my data sent to Anthropic?
**A**: Only the data you explicitly send to Claude (portfolio analysis, market screening queries). Your raw holdings data stays on your machine unless you ask Claude to analyze it.

### Q: What about privacy?
**A**: Your authentication is stored locally (in Claude Code CLI). Queries to Claude are sent to Anthropic servers per their privacy policy. No data is stored in Robo Trader's database for AI features.

---

## Verification Checklist

Before running the application, verify:

- [ ] `python --version` shows 3.10+
- [ ] `claude --version` shows version number
- [ ] `claude --print "test"` outputs "test" (proves auth works)
- [ ] `.env` does NOT have `ANTHROPIC_API_KEY` (or has only commented-out)
- [ ] All trading API keys are set (Zerodha, Perplexity, etc.)
- [ ] `python -m src.main --command web` starts without auth errors
- [ ] Frontend runs: `cd ui && npm run dev`
- [ ] Browser shows dashboard at http://localhost:3000
- [ ] WebSocket connects (check browser console)
- [ ] Portfolio data loads from database

---

## Next Steps

1. **Install Claude Code CLI** (if not already done)
   ```bash
   brew install anthropic/brew/claude  # macOS
   ```

2. **Authenticate**
   ```bash
   claude auth login
   # Complete browser auth flow
   ```

3. **Verify setup**
   ```bash
   claude --print "test"
   ```

4. **Start Robo Trader**
   ```bash
   # Terminal 1: Backend
   python -m src.main --command web

   # Terminal 2: Frontend
   cd ui && npm run dev
   ```

5. **Access dashboard**
   - Open http://localhost:3000
   - View portfolio and analytics
   - Run scans using Claude Agent

---

## Support Resources

- **Claude Agent SDK Docs**: https://github.com/anthropics/claude-agent-sdk-python
- **Claude Code CLI Setup**: https://docs.anthropic.com/claude/docs/desktop-setup
- **Robo Trader Architecture**: See `/documentation/ARCHITECTURE_PATTERNS.md`
- **Backend Guidelines**: See `src/CLAUDE.md`

---

## Summary

Your Robo Trader application is designed to work **exclusively with Claude Agent SDK**:

✅ **No API keys** needed in code
✅ **Subscription-based** authentication via Claude Code CLI
✅ **Secure** - Authentication managed by Anthropic's official tool
✅ **Simple** - Just run `claude auth login` once
✅ **Automatic** - SDK handles all AI interactions

The only manual step is: **`claude auth login`** once at setup time.

After that, your application uses your Claude Pro subscription to power all AI features through the SDK.

---

**Ready to run?** Follow the [Setup Steps](#setup-steps) above!
