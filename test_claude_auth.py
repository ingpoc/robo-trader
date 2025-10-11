#!/usr/bin/env python3
"""
Test script for Claude authentication
Run this to verify that Claude authentication is working properly.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from auth.claude_auth import validate_claude_api, get_claude_status


async def test_claude_auth():
    """Test Claude authentication functionality."""
    print("🧪 Testing Claude Authentication")
    print("=" * 40)

    try:
        # Test basic validation
        print("1. Testing basic authentication validation...")
        status = await validate_claude_api()

        print(f"   Status: {'✅ Valid' if status.is_valid else '❌ Invalid'}")
        print(f"   API Key Present: {status.api_key_present}")
        print(f"   Auth Method: {status.account_info.get('auth_method', 'unknown')}")

        if status.error:
            print(f"   Error: {status.error}")

        if status.rate_limit_info:
            print(f"   Rate Limit Info: {status.rate_limit_info}")

        # Test cached status
        print("\n2. Testing cached status...")
        cached_status = await get_claude_status()
        print(f"   Cached Status: {'✅ Valid' if cached_status.is_valid else '❌ Invalid'}")

        # Test CLI authentication details
        print("\n3. Testing CLI authentication details...")
        if 'cli_installed' in status.account_info:
            print(f"   CLI Installed: {status.account_info['cli_installed']}")
            if 'version' in status.account_info:
                print(f"   CLI Version: {status.account_info['version']}")
            if 'auth_method' in status.account_info:
                print(f"   Auth Method: {status.account_info['auth_method']}")

        print("\n" + "=" * 40)
        if status.is_valid:
            print("🎉 Claude authentication is working!")
            return True
        else:
            print("⚠️  Claude authentication failed.")
            print("   Please run './setup_claude_auth.sh' to configure authentication.")
            return False

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_claude_auth())
    sys.exit(0 if success else 1)