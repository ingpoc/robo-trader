#!/bin/bash
# MCP Server Startup Script for robo-trader-dev

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to script directory
cd "$SCRIPT_DIR"

# Set environment variables
export PYTHONUNBUFFERED=1
export ROBO_TRADER_PROJECT_ROOT="${ROBO_TRADER_PROJECT_ROOT:-/Users/gurusharan/Documents/remote-claude/robo-trader}"
export ROBO_TRADER_API="${ROBO_TRADER_API:-http://localhost:8000}"
export ROBO_TRADER_DB="${ROBO_TRADER_DB:-$ROBO_TRADER_PROJECT_ROOT/state/robo_trader.db}"
export LOG_DIR="${LOG_DIR:-$ROBO_TRADER_PROJECT_ROOT/logs}"

# Load .env file if it exists (needed for Perplexity API keys)
if [ -f "$ROBO_TRADER_PROJECT_ROOT/.env" ]; then
    echo "Loading environment variables from .env file..."
    set -a
    . "$ROBO_TRADER_PROJECT_ROOT/.env"
    echo "Loaded environment from .env: PERPLEXITY_API_KEY_1=${PERPLEXITY_API_KEY_1:0:15}..."
else
    echo "Warning: .env file not found at $ROBO_TRADER_PROJECT_ROOT/.env"
fi

# Execute the MCP server using robotrader_mcp venv Python
exec "$SCRIPT_DIR/venv/bin/python" -m src.server "$@"
