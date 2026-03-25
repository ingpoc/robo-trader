# Agent Testing Setup - Chrome Profile

## Overview

**Profile**: `robo-trader-testing`

Pre-configured Chrome profile for **autonomous agent testing** (when you're not at the machine).

**Includes:**

- ✓ Clone of your Default profile (login sessions intact)
- ✓ All your extensions
- ✓ Remote debugging pre-enabled (no dialog clicks needed)
- ✓ Ready for agents to test without manual intervention

## How It Works

**Normal Interactive Testing (You're Present)**

```
Chrome → chrome://inspect/#remote-debugging (click Allow)
       → Browser shows permission dialog each time
       → Agent can then test
```

**Autonomous Agent Testing (You're NOT Present)**

```
Agent launches: ./.claude/scripts/launch-test-chrome.sh
       ↓
Chrome starts with robo-trader-testing profile
       ↓
Remote debugging enabled automatically (no dialog)
       ↓
Agent tests via chrome-devtools-mcp --autoConnect
```

## For Agents: How to Use

### Option 1: GUI Chrome (Interactive Testing)

```bash
./.claude/scripts/launch-test-chrome.sh http://localhost:3001/paper-trading
```

Best for: Debugging, visual inspection, interactive testing.

### Option 2: Headless Chrome (Autonomous Testing) ⭐ Recommended

```bash
./.claude/scripts/launch-test-chrome-headless.sh http://localhost:3001/paper-trading
```

Then use MCP with the current auto-connect configuration:

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": [
        "chrome-devtools-mcp@latest",
        "--autoConnect"
      ]
    }
  }
}
```

Best for: Autonomous agents (no display needed, efficient, no dialogs).

**Why headless?**

- No GUI overhead
- Debugging port exposed on 9222 for manual attach/debugging
- No permission dialogs
- Efficient background execution
- Perfect for agent-only environments

## Profile Features

| Feature | Status | Notes |
|---------|--------|-------|
| Login Sessions | ✓ Cloned from Default | All your account access preserved |
| Extensions | ✓ Cloned from Default | All installed extensions available |
| Remote Debugging | ✓ Pre-enabled | No `chrome://inspect` dialog needed |
| Cookies/Cache | ✓ Cloned from Default | Your browsing state ready |
| Credentials | ✓ Cloned from Default | Saved passwords, autofill data available |

## When to Use Each Profile

| Scenario | Profile | Launch Method |
|----------|---------|----------------|
| You're at the machine, interactive | Default | Manual Chrome launch |
| Agent testing (you're away) | robo-trader-testing | `.launch-test-chrome.sh` or MCP auto-launch |
| Fresh session needed | Create new profile | `--profile-directory=new-name` |

## Technical Details

**Location:**

```
~/Library/Application Support/Google/Chrome/robo-trader-testing/
```

**Remote Debugging Enabled Via:**

- Preferences file: `devtools.remote_debugging_allowed = true`
- Command-line flag: `--remote-debugging-port=9222`
- Profile-based: No permission dialog on subsequent launches

**How Agents Access:**

```python
# Chrome DevTools MCP auto-connect
# MCP attaches to the running test profile automatically when available
```

## Updating Profile

If you update extensions, login, or settings in your Default profile and want agents to use the latest:

```bash
# 1. Stop Chrome
pkill -9 "Google Chrome"

# 2. Delete old test profile
rm -rf ~/Library/Application\ Support/Google/Chrome/robo-trader-testing

# 3. Re-create from updated Default
./.claude/scripts/setup-test-profile.sh
```

(Script to be created when needed)

## Troubleshooting

**Chrome doesn't start:**

```bash
ps aux | grep "Google Chrome"  # Check if already running
kill -9 <PID>                  # Stop existing Chrome
./.claude/scripts/launch-test-chrome.sh  # Try again
```

**Profile not found:**

- Verify path: `~/Library/Application Support/Google/Chrome/robo-trader-testing/`
- Re-run setup if deleted

**Extensions missing:**

- Profile was copied when extensions were installed
- If you later install new extensions, re-clone profile from Default

**Remote debugging not working:**

- Verify Preferences file has: `"devtools": { "remote_debugging_allowed": true }`
- Check Chrome is launched with `--remote-debugging-port=9222`
- Use DevTools at `http://localhost:9222` for manual verification
