#!/usr/bin/env python
"""Test Claude SDK initialization"""

import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from loguru import logger

async def test_claude_sdk():
    logger.info("Testing Claude SDK initialization...")

    try:
        # Minimal options
        options = ClaudeAgentOptions(
            allowed_tools=[],
            permission_mode="auto",
            mcp_servers={},
            hooks=[],
        )

        logger.info("Creating Claude SDK client...")
        client = ClaudeSDKClient(options=options)

        logger.info("Claude SDK client created successfully")
        return True

    except Exception as e:
        logger.error(f"Failed to initialize Claude SDK: {e}")
        logger.exception("Exception details:")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_claude_sdk())
    print(f"Test result: {'SUCCESS' if result else 'FAILED'}")