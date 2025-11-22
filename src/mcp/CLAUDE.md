# MCP Directory Guidelines

> **Scope**: Applies to `src/mcp/` directory. Read `src/CLAUDE.md` and `src/core/CLAUDE.md` for context.
> **Last Updated**: 2025-11-22 | **Status**: Active | **Tier**: Reference

## Purpose

The `mcp/` directory contains Model Context Protocol (MCP) server implementations. MCP servers expose tools that Claude agents can use to interact with the trading system.

## Architecture Pattern

### In-Process SDK MCP Servers

This directory uses **in-process SDK MCP servers** (not external subprocess servers) for better performance and integration.

### MCP Server Pattern

MCP servers expose tools using the `@tool` decorator from Claude Agent SDK:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any

@tool("get_portfolio", "Get current portfolio positions", {})
async def get_portfolio(args: dict[str, Any]) -> dict[str, Any]:
    """Get portfolio positions."""
    # Tool implementation
    portfolio_data = await portfolio_service.get_portfolio()
    return {
        "content": [{
            "type": "text",
            "text": json.dumps(portfolio_data, indent=2)
        }]
    }

@tool("place_order", "Place a trading order", {
    "symbol": str,
    "quantity": float,
    "order_type": str
})
async def place_order(args: dict[str, Any]) -> dict[str, Any]:
    """Place trading order."""
    # Tool implementation
    result = await trading_service.place_order(
        symbol=args["symbol"],
        quantity=args["quantity"],
        order_type=args["order_type"]
    )
    return {
        "content": [{
            "type": "text",
            "text": f"Order placed: {result['order_id']}"
        }]
    }

# Create MCP server
broker_mcp_server = create_sdk_mcp_server(
    name="broker",
    version="1.0.0",
    tools=[get_portfolio, place_order]
)
```

## Files

### `broker.py`

MCP server for broker/trading operations:
- `get_portfolio` - Get portfolio positions
- `place_order` - Place trading orders
- `get_quotes` - Get market quotes
- Other broker-related tools

## Rules

### ✅ DO

- ✅ Use `@tool` decorator for tool definitions
- ✅ Use `create_sdk_mcp_server` for server creation
- ✅ Provide clear tool descriptions
- ✅ Include parameter schemas in tool definitions
- ✅ Handle errors gracefully in tools
- ✅ Return structured tool responses
- ✅ Max 350 lines per MCP server file

### ❌ DON'T

- ❌ Use external subprocess MCP servers (use SDK servers)
- ❌ Skip tool descriptions
- ❌ Make tools blocking
- ❌ Expose sensitive operations without validation
- ❌ Return unstructured responses
- ❌ Exceed file size limits

## Tool Definition Pattern

Each tool should follow this pattern:

```python
from claude_agent_sdk import tool
from typing import Any

@tool(
    "tool_name",
    "Clear description of what the tool does",
    {
        "param1": str,      # Parameter type
        "param2": float,    # Parameter type
        "param3": bool     # Optional parameter
    }
)
async def tool_function(args: dict[str, Any]) -> dict[str, Any]:
    """
    Tool function implementation.
    
    Args:
        args: Dictionary with tool arguments
        
    Returns:
        Dictionary with content and optional is_error flag
    """
    try:
        # Validate arguments
        param1 = args.get("param1")
        if not param1:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: param1 is required"
                }],
                "is_error": True
            }
        
        # Perform operation
        result = await some_service.operation(param1)
        
        # Return result
        return {
            "content": [{
                "type": "text",
                "text": json.dumps(result, indent=2)
            }]
        }
    
    except Exception as e:
        # Return error
        return {
            "content": [{
                "type": "text",
                "text": f"Error: {str(e)}"
            }],
            "is_error": True
        }
```

## MCP Server Registration

MCP servers are registered with `ClaudeAgentOptions`:

```python
from claude_agent_sdk import ClaudeAgentOptions
from src.mcp.broker import broker_mcp_server

options = ClaudeAgentOptions(
    mcp_servers={"broker": broker_mcp_server},
    allowed_tools=[
        "mcp__broker__get_portfolio",
        "mcp__broker__place_order"
    ]
)
```

## Tool Naming Convention

Tools follow this naming convention:
- **Pattern**: `mcp__{server_name}__{tool_name}`
- **Example**: `mcp__broker__get_portfolio`
- **Usage**: Tools are referenced by their full name in `allowed_tools`

## Error Handling

Tools should handle errors gracefully:

```python
@tool("risky_operation", "Perform risky operation", {"param": str})
async def risky_operation(args: dict[str, Any]) -> dict[str, Any]:
    """Tool with error handling."""
    try:
        result = await risky_service.operation(args["param"])
        return {
            "content": [{"type": "text", "text": f"Success: {result}"}]
        }
    except ValidationError as e:
        return {
            "content": [{"type": "text", "text": f"Validation error: {e}"}],
            "is_error": True
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }
```

## Best Practices

1. **Clear Descriptions**: Provide clear, concise tool descriptions
2. **Parameter Validation**: Validate all tool parameters
3. **Error Handling**: Return structured errors with `is_error` flag
4. **Async Operations**: Keep tools async (don't block)
5. **Security**: Validate operations before execution
6. **Structured Responses**: Return JSON-formatted responses
7. **Tool Grouping**: Group related tools in same MCP server

## Dependencies

MCP servers typically depend on:
- `claude_agent_sdk` - For tool decorators and server creation
- Domain services - For business logic execution
- `EventBus` - For event emission (optional)

