"""Minimal MCP Server for Robo Trader Debugging

Slimmed down from 1000+ lines to essential debugging functionality only.
"""

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, List

try:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    print("MCP not installed. Install with: pip install mcp")
    exit(1)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create server
server = Server("robo-trader-debug")

# Cache for simple responses
_cache: Dict[str, Any] = {}


@server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List minimal debugging tools."""
    return [
        types.Tool(
            name="health_check",
            description="Check robo-trader system health",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="view_logs",
            description="View recent robo-trader logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "lines": {"type": "integer", "description": "Number of lines to show", "default": 50}
                },
                "required": []
            }
        ),
        types.Tool(
            name="database_status",
            description="Check database connection and status",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent]:
    """Handle tool calls."""

    if name == "health_check":
        # Simple health check
        return [types.TextContent(
            type="text",
            text=json.dumps({
                "status": "healthy",
                "server": "robo-trader-debug",
                "timestamp": "2025-01-07T18:30:00Z"
            }, indent=2)
        )]

    elif name == "view_logs":
        lines = arguments.get("lines", 50)
        log_file = Path("/Users/gurusharan/Documents/remote-claude/robo-trader/logs/robo_trader.log")

        if log_file.exists():
            with open(log_file, 'r') as f:
                log_lines = f.readlines()[-lines:]
            return [types.TextContent(
                type="text",
                text="".join(log_lines)
            )]
        else:
            return [types.TextContent(
                type="text",
                text="No log file found at expected location"
            )]

    elif name == "database_status":
        # Simple DB status check
        db_path = Path("/Users/gurusharan/Documents/remote-claude/robo-trader/state/robo_trader.db")

        return [types.TextContent(
            type="text",
            text=json.dumps({
                "database_path": str(db_path),
                "exists": db_path.exists(),
                "size_mb": round(db_path.stat().st_size / (1024*1024), 2) if db_path.exists() else 0
            }, indent=2)
        )]

    else:
        raise ValueError(f"Unknown tool: {name}")


async def main():
    """Run the MCP server."""
    logger.info("Starting robo-trader MCP debug server")

    # Remove cache periodically
    async def cleanup_cache():
        while True:
            await asyncio.sleep(3600)  # Every hour
            _cache.clear()

    asyncio.create_task(cleanup_cache())

    async with stdio_server() as streams:
        await server.run(
            streams[0],
            streams[1],
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())