#!/bin/bash

# Launch Chrome with robo-trader-testing profile for agent testing
# Usage: ./launch-test-chrome.sh [URL]
# Default URL: http://localhost:3001/paper-trading

URL="${1:-http://localhost:3001/paper-trading}"
PROFILE_DIR="$HOME/Library/Application Support/Google/Chrome/robo-trader-testing"

if [ ! -d "$PROFILE_DIR" ]; then
    echo "Error: robo-trader-testing profile not found at:"
    echo "  $PROFILE_DIR"
    echo ""
    echo "Create it first with:"
    echo "  cp -r \"$HOME/Library/Application Support/Google/Chrome/Default\" \"$PROFILE_DIR\""
    exit 1
fi

echo "Launching Chrome with robo-trader-testing profile..."
echo "URL: $URL"
echo ""

# Start Chrome in background with:
# - robo-trader-testing profile (has login + extensions)
# - Navigate to URL
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
    --profile-directory="robo-trader-testing" \
    --no-first-run \
    "$URL" \
    > /dev/null 2>&1 &

CHROME_PID=$!
echo "Chrome started (PID: $CHROME_PID)"
echo ""
echo "Profile has:"
echo "  ✓ Your login sessions"
echo "  ✓ All your extensions"
echo "  ✓ Bookmarks & settings"
echo ""

wait $CHROME_PID
