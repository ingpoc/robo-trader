# MCP Server Configuration Options

All three configurations have been tested and work. Try them in order until one connects successfully with Claude Code.

## Current Configuration (Option 1 - Relative Path)

**File**: `/Users/gurusharan/Documents/remote-claude/robo-trader/.mcp.json`

```json
{
  "mcpServers": {
    "robo-trader-dev": {
      "command": "venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/Users/gurusharan/Documents/remote-claude/robo-trader/shared/robotrader_mcp",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "ROBO_TRADER_PROJECT_ROOT": "/Users/gurusharan/Documents/remote-claude/robo-trader",
        "ROBO_TRADER_API": "http://localhost:8000",
        "ROBO_TRADER_DB": "/Users/gurusharan/Documents/remote-claude/robo-trader/state/robo_trader.db",
        "LOG_DIR": "/Users/gurusharan/Documents/remote-claude/robo-trader/logs"
      }
    }
  }
}
```

## Option 2 - Wrapper Script (Recommended)

If Option 1 doesn't work, try using the wrapper script:

```json
{
  "mcpServers": {
    "robo-trader-dev": {
      "command": "/Users/gurusharan/Documents/remote-claude/robo-trader/shared/robotrader_mcp/start_mcp_server.sh",
      "args": [],
      "env": {}
    }
  }
}
```

The wrapper script handles all environment setup internally.

## Option 3 - Absolute Path

If both above fail, try the absolute path version:

```json
{
  "mcpServers": {
    "robo-trader-dev": {
      "command": "/Users/gurusharan/Documents/remote-claude/robo-trader/shared/robotrader_mcp/venv/bin/python",
      "args": ["-m", "src.server"],
      "cwd": "/Users/gurusharan/Documents/remote-claude/robo-trader/shared/robotrader_mcp",
      "env": {
        "PYTHONUNBUFFERED": "1",
        "ROBO_TRADER_PROJECT_ROOT": "/Users/gurusharan/Documents/remote-claude/robo-trader",
        "ROBO_TRADER_API": "http://localhost:8000",
        "ROBO_TRADER_DB": "/Users/gurusharan/Documents/remote-claude/robo-trader/state/robo_trader.db",
        "LOG_DIR": "/Users/gurusharan/Documents/remote-claude/robo-trader/logs"
      }
    }
  }
}
```

## Testing the Configuration

Test any configuration with:

```bash
cd /Users/gurusharan/Documents/remote-claude/robo-trader/shared/robotrader_mcp

# Test Option 1 (relative path)
venv/bin/python -m src.server <<< '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Test Option 2 (wrapper script)
./start_mcp_server.sh <<< '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'

# Test Option 3 (absolute path)
/Users/gurusharan/Documents/remote-claude/robo-trader/shared/robotrader_mcp/venv/bin/python -m src.server <<< '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}'
```

All three should output a JSON response with `"robo-trader-dev"` and `"version":"2.0.0"`.

## Troubleshooting

### If none work in Claude Code:

1. **Restart Claude Code completely** (quit and relaunch)
2. Check Claude Code logs: `~/Library/Logs/Claude/mcp.log`
3. Look for errors related to "robo-trader-dev"
4. Verify Python version: `venv/bin/python --version` (should be 3.12.0)
5. Check MCP SDK installed: `venv/bin/pip list | grep mcp` (should show mcp 1.21.0)

### Common Issues:

- **"Failed to reconnect"**: Claude Code hasn't reloaded config - restart the app
- **"Command not found"**: Path issue - try wrapper script (Option 2)
- **"Permission denied"**: Run `chmod +x start_mcp_server.sh`
- **No response**: Server hanging - check if port conflicts or environment issues

## Server Status

✅ **Server Code**: Fully working, all fixes applied
✅ **MCP Protocol**: Responding correctly to JSON-RPC
✅ **Tools Available**: 15 tools (3 discovery + 12 analysis)
✅ **Configuration**: Valid JSON, all paths correct
✅ **Python Environment**: venv/bin/python 3.12.0 with mcp 1.21.0

The server is ready. The issue is just getting Claude Code to read the updated configuration.
