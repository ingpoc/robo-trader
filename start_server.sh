#!/bin/bash

# Set OAuth token to bypass Claude CLI auth check
export ANTHROPIC_API_KEY=sk-ant-oat_TEST_TOKEN

# Start the server
PYTHONUNBUFFERED=1 \
ROBO_TRADER_PROJECT_ROOT=/Users/gurusharan/Documents/remote-claude/robo-trader \
ROBO_TRADER_API=http://localhost:8000 \
ROBO_TRADER_DB=/Users/gurusharan/Documents/remote-claude/robo-trader/state/robo_trader.db \
LOG_DIR=/Users/gurusharan/Documents/remote-claude/robo-trader/logs \
./venv/bin/python -m src.main --command web