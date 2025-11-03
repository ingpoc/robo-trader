#!/usr/bin/env python
"""Test if importing the service module causes SDK issues"""
import asyncio

# First, test SDK before importing service
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

print("Testing SDK before service import...")

async def test_before():
    opts = ClaudeAgentOptions(
        allowed_tools=[],
        system_prompt="You are a test. Respond: {\"result\": \"ok\"}",
        max_turns=1
    )
    client = ClaudeSDKClient(options=opts)
    async with client:
        await client.query("Test")
        response_text = ""
        async for response in client.receive_response():
            if hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
        print(f"Before import: {response_text[:100]}")

asyncio.run(test_before())

# Now import the service
print("\nImporting service module...")
from src.services.paper_trading_execution_service import PaperTradingExecutionService

# Test SDK after importing service
print("\nTesting SDK after service import...")

async def test_after():
    opts = ClaudeAgentOptions(
        allowed_tools=[],
        system_prompt="You are a test. Respond: {\"result\": \"ok\"}",
        max_turns=1
    )
    client = ClaudeSDKClient(options=opts)
    async with client:
        await client.query("Test")
        response_text = ""
        async for response in client.receive_response():
            if hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text
        print(f"After import: {response_text[:100]}")

asyncio.run(test_after())

# Now actually test the service
print("\nTesting service...")

async def test_service():
    service = PaperTradingExecutionService(None)
    await service.initialize()
    try:
        result = await service.execute_buy_trade(
            account_id='test',
            symbol='AAPL',
            quantity=10
        )
        print(f"Service result: {result['trade_id']}")
    except Exception as e:
        print(f"Service error: {e}")
    await service.cleanup()

asyncio.run(test_service())
