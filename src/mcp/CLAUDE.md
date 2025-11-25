# MCP Servers - src/mcp/

## Purpose
In-process SDK MCP servers exposing tools for Claude agents.

## Tool Pattern
```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool("tool_name", "Tool description", {
    "param1": str,
    "param2": float
})
async def tool_function(args: dict[str, Any]) -> dict[str, Any]:
    try:
        param1 = args.get("param1")
        if not param1:
            return {
                "content": [{"type": "text", "text": "Error: param1 required"}],
                "is_error": True
            }
        result = await service.operation(param1)
        return {
            "content": [{"type": "text", "text": json.dumps(result)}]
        }
    except Exception as e:
        return {
            "content": [{"type": "text", "text": f"Error: {e}"}],
            "is_error": True
        }

# Create server
broker = create_sdk_mcp_server(
    name="broker",
    version="1.0.0",
    tools=[tool_function]
)
```

## Registration
```python
from claude_agent_sdk import ClaudeAgentOptions
from src.mcp.broker import broker

options = ClaudeAgentOptions(
    mcp_servers={"broker": broker},
    allowed_tools=["mcp__broker__tool_name"]
)
```

## Rules
| Rule | Requirement |
|------|-------------|
| Server type | In-process SDK ONLY (not subprocess) |
| Tool decorator | @tool("name", "desc", {...params}) |
| Validation | Always validate parameters |
| Errors | Return is_error: True + message |
| Responses | Structured JSON content |
| Async | All tools MUST be async |
| Max size | 350 lines per MCP server file |

