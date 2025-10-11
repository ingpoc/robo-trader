#!/usr/bin/env python3
"""
Test script to verify Claude CLI authentication for robo-trader.

This script tests:
1. Claude CLI installation
2. CLI authentication status
3. SDK connectivity via CLI
4. Current authentication method being used

Run: python test_claude_cli_auth.py
"""

import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from auth.claude_auth import validate_claude_api, check_claude_code_cli_auth


async def test_cli_installation():
    """Test if Claude CLI is installed and accessible."""
    print("=" * 60)
    print("TEST 1: Claude CLI Installation")
    print("=" * 60)

    import subprocess
    try:
        result = subprocess.run(
            ["claude", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            print(f"✓ Claude CLI installed: {result.stdout.strip()}")
            return True
        else:
            print(f"✗ Claude CLI not responding: {result.stderr}")
            return False
    except FileNotFoundError:
        print("✗ Claude CLI not found in PATH")
        print("  Install with: npm install -g @anthropic-ai/claude-code")
        return False
    except Exception as e:
        print(f"✗ Error checking CLI: {e}")
        return False


async def test_cli_authentication():
    """Test Claude CLI authentication status."""
    print("\n" + "=" * 60)
    print("TEST 2: Claude CLI Authentication")
    print("=" * 60)

    cli_status = await check_claude_code_cli_auth()

    print(f"CLI Installed: {cli_status['cli_installed']}")
    print(f"Authenticated: {cli_status['authenticated']}")

    if cli_status['authenticated']:
        print(f"✓ Auth Method: {cli_status.get('auth_method', 'unknown')}")
        print(f"  Version: {cli_status.get('version', 'unknown')}")

        rate_limit = cli_status.get('rate_limit_info', {})
        if rate_limit.get('limited'):
            print(f"  ⚠ Rate Limited: {rate_limit.get('type')} limit reached")
            if 'resets_at' in rate_limit:
                print(f"    Resets at: {rate_limit['resets_at']}")
        else:
            print("  ✓ No rate limits detected")

        return True
    else:
        print("✗ Not authenticated")
        print("\n  To authenticate:")
        print("  1. Run: claude auth login")
        print("  2. Complete browser authentication")
        print("  3. Re-run this test")
        return False


async def test_api_key_presence():
    """Check if ANTHROPIC_API_KEY is set."""
    print("\n" + "=" * 60)
    print("TEST 3: API Key Configuration")
    print("=" * 60)

    api_key = os.getenv("ANTHROPIC_API_KEY")

    if api_key:
        masked_key = f"{api_key[:10]}...{api_key[-4:]}" if len(api_key) > 14 else "***"
        print(f"⚠ ANTHROPIC_API_KEY is set: {masked_key}")
        print("  Note: Claude Agent SDK does NOT use this API key")
        print("  The SDK uses Claude CLI authentication instead")
        print("  You can remove or comment out ANTHROPIC_API_KEY in .env")
        return "present_but_unused"
    else:
        print("✓ ANTHROPIC_API_KEY not set (correct for CLI auth)")
        return "not_set"


async def test_full_authentication():
    """Test the full authentication flow used by robo-trader."""
    print("\n" + "=" * 60)
    print("TEST 4: Full Authentication Validation")
    print("=" * 60)

    status = await validate_claude_api()

    print(f"Valid: {status.is_valid}")
    print(f"Auth Method: {status.account_info.get('auth_method', 'unknown')}")

    if status.is_valid:
        print("✓ Authentication PASSED")
        print(f"  Status: {status.to_dict()['status']}")

        if status.account_info.get('subscription'):
            print(f"  Subscription: {status.account_info['subscription']}")

        if status.rate_limit_info:
            print(f"  Rate Limits: {status.rate_limit_info}")

        return True
    else:
        print("✗ Authentication FAILED")
        print(f"  Error: {status.error}")
        return False


async def test_sdk_import():
    """Test if Claude Agent SDK can be imported."""
    print("\n" + "=" * 60)
    print("TEST 5: SDK Import")
    print("=" * 60)

    try:
        from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
        print("✓ Claude Agent SDK imported successfully")
        print("  SDK will use Claude CLI for authentication")
        return True
    except ImportError as e:
        print(f"✗ Failed to import SDK: {e}")
        print("  Install with: pip install claude-agent-sdk")
        return False


async def main():
    """Run all tests."""
    print("\n" + "#" * 60)
    print("#  Claude CLI Authentication Test Suite")
    print("#  for Robo Trader Application")
    print("#" * 60 + "\n")

    results = {}

    results['cli_installed'] = await test_cli_installation()
    results['cli_authenticated'] = await test_cli_authentication()
    results['api_key_status'] = await test_api_key_presence()
    results['full_auth'] = await test_full_authentication()
    results['sdk_import'] = await test_sdk_import()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    all_pass = (
        results['cli_installed'] and
        results['cli_authenticated'] and
        results['full_auth'] and
        results['sdk_import']
    )

    if all_pass:
        print("\n✓ ALL TESTS PASSED")
        print("\nYour robo-trader is ready to use Claude subscription!")
        print("\nNext steps:")
        print("1. Start the application: uvicorn src.web.app:app --reload")
        print("2. Check authentication status: http://localhost:8000/api/system/status")
        print("3. Start trading!")
    else:
        print("\n✗ SOME TESTS FAILED")
        print("\nAction required:")

        if not results['cli_installed']:
            print("- Install Claude CLI: npm install -g @anthropic-ai/claude-code")

        if not results['cli_authenticated']:
            print("- Authenticate: claude auth login")

        if not results['sdk_import']:
            print("- Install SDK: pip install claude-agent-sdk")

    print("\n" + "=" * 60)

    return 0 if all_pass else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
