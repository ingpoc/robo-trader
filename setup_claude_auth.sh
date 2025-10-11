#!/bin/bash
# Setup Claude Authentication for Robo Trader
# This script helps configure Claude Code OAuth token for authentication

echo "🤖 Robo Trader - Claude Authentication Setup"
echo "=========================================="
echo ""

# Check if token is already set
if [ ! -z "$CLAUDE_CODE_OAUTH_TOKEN" ]; then
    echo "✅ CLAUDE_CODE_OAUTH_TOKEN is already set in environment"
    echo "Current token: ${CLAUDE_CODE_OAUTH_TOKEN:0:20}..."
    echo ""
    read -p "Do you want to update it? (y/N): " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing token."
        exit 0
    fi
fi

echo "📝 You need a Claude Code OAuth token to authenticate with Claude."
echo "   This token is valid for 1 year and should be kept secure."
echo ""
echo "🔗 Get your token from: https://console.anthropic.com/"
echo "   (Go to Account Settings → API Keys → Create OAuth Token)"
echo ""

# Check if we should use the provided token or prompt for one
if [ -n "$1" ]; then
    token="$1"
    echo "🔑 Using provided token..."
else
    # Prompt for token
    read -p "Enter your CLAUDE_CODE_OAUTH_TOKEN: " -s token
    echo ""
fi

if [ -z "$token" ]; then
    echo "❌ No token provided. Exiting."
    exit 1
fi

# Validate token format (should start with sk-ant-oat01-)
if [[ ! $token =~ ^sk-ant-oat01- ]]; then
    echo "❌ Invalid token format. Token should start with 'sk-ant-oat01-'"
    exit 1
fi

echo "✅ Token format looks valid"
echo ""

# Try to set up the token using Claude CLI
echo "🔧 Setting up token with Claude CLI..."
export CLAUDE_CODE_OAUTH_TOKEN="$token"

# Use claude setup-token if available, otherwise fall back to env var
if command -v claude &> /dev/null; then
    echo "📡 Running 'claude setup-token'..."
    # Note: This might be interactive, but we'll try it
    echo "$token" | claude setup-token 2>/dev/null || {
        echo "⚠️  Interactive setup failed, using environment variable approach..."
    }
else
    echo "⚠️  Claude CLI not found, using environment variable approach..."
fi

# Create or update .env file
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
    echo "📄 Creating .env file..."
    touch "$ENV_FILE"
fi

# Check if token is already in .env file
if grep -q "CLAUDE_CODE_OAUTH_TOKEN" "$ENV_FILE"; then
    # Update existing line
    sed -i.bak "s/CLAUDE_CODE_OAUTH_TOKEN=.*/CLAUDE_CODE_OAUTH_TOKEN=$token/" "$ENV_FILE"
    rm "${ENV_FILE}.bak" 2>/dev/null
    echo "🔄 Updated CLAUDE_CODE_OAUTH_TOKEN in .env file"
else
    # Add new line
    echo "CLAUDE_CODE_OAUTH_TOKEN=$token" >> "$ENV_FILE"
    echo "➕ Added CLAUDE_CODE_OAUTH_TOKEN to .env file"
fi

# Set the token in current session
export CLAUDE_CODE_OAUTH_TOKEN="$token"
echo "🔧 Exported CLAUDE_CODE_OAUTH_TOKEN in current session"
echo ""

# Test the authentication
echo "🧪 Testing Claude authentication..."
python -c "
import asyncio
import sys
import os
sys.path.append('src')
from auth.claude_auth import validate_claude_api

async def test_auth():
    try:
        status = await validate_claude_api()
        if status.is_valid:
            print('✅ Authentication successful!')
            print(f'   Method: {status.account_info.get(\"auth_method\", \"unknown\")}')
            return True
        else:
            print('❌ Authentication failed!')
            print(f'   Error: {status.error}')
            return False
    except Exception as e:
        print(f'❌ Test failed: {e}')
        return False

result = asyncio.run(test_auth())
sys.exit(0 if result else 1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎉 Setup complete! Claude authentication is working."
    echo ""
    echo "📋 Next steps:"
    echo "   1. Run './restart_server.sh' to start the application"
    echo "   2. Check the dashboard for Claude status"
    echo ""
    echo "🔒 Security notes:"
    echo "   • Keep your .env file secure and never commit it"
    echo "   • The token is valid for 1 year"
    echo "   • Rotate tokens regularly for security"
else
    echo ""
    echo "⚠️  Authentication test failed. Please check your token and try again."
    echo "   You can still proceed, but Claude features may not work."
fi

echo ""
echo "💡 To use the token in new terminal sessions, run:"
echo "   source .env  # or: export \$(cat .env | xargs)"