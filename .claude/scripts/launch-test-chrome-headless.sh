#!/bin/bash

# Launch Chrome in headless mode with robo-trader-testing profile for autonomous agent testing
# Usage: ./launch-test-chrome-headless.sh [URL]
# Default URL: http://localhost:3001/paper-trading
#
# This script launches Chrome in headless (no GUI) mode with remote debugging enabled.
# Ideal for autonomous testing where no display is needed.
# The debugging port will be available at: http://127.0.0.1:9222

URL="${1:-http://localhost:3001/paper-trading}"
HEADLESS_DATA_DIR="$HOME/.chrome-headless-test"

echo "Launching Chrome in headless mode with robo-trader-testing profile..."
echo "URL: $URL"
echo "Data Dir: $HEADLESS_DATA_DIR"
echo "Debug Port: http://127.0.0.1:9222"
echo ""

# Start Chrome in headless mode with:
# - Headless mode (no GUI)
# - Remote debugging port exposed
# - robo-trader-testing profile (has login + extensions)
# - Navigate to URL
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --user-data-dir="$HEADLESS_DATA_DIR" \
    --profile-directory="robo-trader-testing" \
    --no-first-run \
    --headless=new \
    --remote-debugging-port=9222 \
    "$URL" \
    > /tmp/chrome-headless.log 2>&1 &

CHROME_PID=$!
echo "Chrome headless started (PID: $CHROME_PID)"
echo ""
echo "Testing debugging port connectivity..."
sleep 3

# Test if debugging port is responding
if curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
    echo "✓ Debugging port responding on http://127.0.0.1:9222"
    curl -s http://127.0.0.1:9222/json/version | python3 -m json.tool 2>/dev/null | grep -E "Browser|Protocol-Version"
    echo ""
    echo "Ready for MCP connections. Prefer chrome-devtools-mcp --autoConnect; 9222 is available for manual attach/debugging."
else
    echo "✗ Debugging port not responding. Check logs:"
    tail -20 /tmp/chrome-headless.log
fi

echo ""
echo "To test with agents:"
echo "  - Use the global Codex/Claude MCP config with --autoConnect"
echo "  - Reload Claude Code (/reload-plugins)"
echo "  - Use chrome-devtools MCP tools"
echo ""
echo "To stop: kill $CHROME_PID"
