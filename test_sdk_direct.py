#!/usr/bin/env python
"""Test Claude Agent SDK integration without importing project code"""
import asyncio
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

SYSTEM_PROMPT = """You are a paper trading engine for Indian markets.

You do NOT have external tools. Make price assumptions.

Respond ONLY with JSON (no markdown, no explanation):
{"decision": "APPROVE", "reason": "Valid", "trade_price": 250, "required_amount": 2500}
"""

async def main():
    opts = ClaudeAgentOptions(
        allowed_tools=[],
        system_prompt=SYSTEM_PROMPT,
        max_turns=1,
        disallowed_tools=["WebSearch", "WebFetch", "Bash", "Read", "Write"]
    )

    client = ClaudeSDKClient(options=opts)
    async with client:
        await client.query("Validate: AAPL, 10 shares. Return JSON.")

        response_text = ""
        async for response in client.receive_response():
            if hasattr(response, 'content'):
                for block in response.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

        print(f'Response: {response_text}')

        # Try parsing
        import json
        import re
        markdown_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if markdown_match:
            json_str = markdown_match.group(1)
            result = json.loads(json_str)
            print(f'Parsed: {result}')
        else:
            print('No markdown match')

if __name__ == "__main__":
    asyncio.run(main())
