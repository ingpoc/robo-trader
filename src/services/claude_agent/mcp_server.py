"""
Claude Agent MCP Server

Implements MCP server pattern for tool execution instead of custom implementation.
Provides standardized tool execution interface with proper SDK patterns.
"""

import logging
import json
from typing import Dict, Any, Optional, List, TYPE_CHECKING
from datetime import datetime

from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from .tool_executor import ToolExecutor

if TYPE_CHECKING:
    from ...core.di import DependencyContainer

logger = logging.getLogger(__name__)


class ClaudeAgentMCPServer:
    """
    MCP Server implementation for Claude Agent tool execution.

    Implements Progressive Discovery Pattern (Anthropic's research):
    - Minimal tool definitions upfront (name only)
    - Full schemas loaded on-demand via search_tools()
    - Token-optimized responses (no JSON indentation)

    Provides standardized MCP interface for:
    - Tool discovery and execution
    - Resource access
    - Proper error handling and validation
    - SDK-compliant patterns
    """

    # Minimal tool registry - name only (Progressive Discovery Pattern)
    # Full definitions loaded on-demand to save tokens
    TOOL_BRIEF = {
        "execute_trade": "Trade stock",
        "close_position": "Close position",
        "check_balance": "Get balance",
        "get_strategy_learnings": "Past learnings",
        "get_monthly_performance": "Month stats",
        "analyze_position": "Analyze stock",
        "search_tools": "Find tools"  # Meta-tool for progressive discovery
    }

    def __init__(self, container: "DependencyContainer"):
        """Initialize MCP server."""
        self.container = container
        self.tool_executor: Optional[ToolExecutor] = None
        self._initialized = False
        self._tools: Dict[str, Dict[str, Any]] = {}  # Full schemas (lazy loaded)
        self._resources: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize MCP server and register tools."""
        if self._initialized:
            return

        self._log_info("Initializing ClaudeAgentMCPServer")

        try:
            # Initialize tool executor
            risk_config = {}  # Get from config if needed
            self.tool_executor = ToolExecutor(self.container, risk_config)
            await self.tool_executor.register_handlers()

            # Register MCP tools
            await self._register_tools()

            # Register MCP resources
            await self._register_resources()

            self._initialized = True
            self._log_info("ClaudeAgentMCPServer initialized successfully")

        except Exception as e:
            self._log_error(f"Failed to initialize ClaudeAgentMCPServer: {e}")
            raise TradingError(
                f"MCP server initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def _register_tools(self) -> None:
        """
        Register available tools with MCP (full schemas for internal use).

        Progressive Discovery Pattern:
        - Full schemas stored here but NOT sent to agent upfront
        - Agent uses search_tools() to discover tools on-demand
        - Massive token savings (~95% reduction in tool definitions)
        """
        self._tools = {
            "search_tools": {
                "name": "search_tools",
                "description": "Find tools by name/purpose. Use before calling tools.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search term"},
                        "detail": {"type": "string", "enum": ["brief", "full"], "default": "brief"}
                    },
                    "required": []
                }
            },
            "execute_trade": {
                "name": "execute_trade",
                "description": "Execute paper trade",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "action": {"type": "string", "enum": ["buy", "sell"]},
                        "quantity": {"type": "integer", "minimum": 1},
                        "entry_price": {"type": "number", "minimum": 0},
                        "strategy_rationale": {"type": "string"},
                        "stop_loss": {"type": "number"},
                        "target_price": {"type": "number"},
                        "account_id": {"type": "string"},
                        "claude_session_id": {"type": "string"}
                    },
                    "required": ["symbol", "action", "quantity", "entry_price", "strategy_rationale"]
                }
            },
            "close_position": {
                "name": "close_position",
                "description": "Close position",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "trade_id": {"type": "string"},
                        "exit_price": {"type": "number", "minimum": 0},
                        "reason": {"type": "string"}
                    },
                    "required": ["trade_id", "exit_price", "reason"]
                }
            },
            "check_balance": {
                "name": "check_balance",
                "description": "Get balance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_id": {"type": "string"}
                    },
                    "required": []
                }
            },
            "get_strategy_learnings": {
                "name": "get_strategy_learnings",
                "description": "Get learnings",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer", "default": 5}
                    },
                    "required": []
                }
            },
            "get_monthly_performance": {
                "name": "get_monthly_performance",
                "description": "Month stats",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "account_type": {"type": "string", "enum": ["swing", "options"]}
                    },
                    "required": ["account_type"]
                }
            },
            "analyze_position": {
                "name": "analyze_position",
                "description": "Analyze stock",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "trade_id": {"type": "string"}
                    },
                    "required": ["symbol"]
                }
            }
        }

        self._log_info(f"Registered {len(self._tools)} MCP tools (progressive discovery enabled)")

    async def _register_resources(self) -> None:
        """Register available resources with MCP."""
        self._resources = {
            "portfolio_status": {
                "uri": "claude://portfolio/status",
                "name": "Portfolio Status",
                "description": "Current portfolio status and positions",
                "mime_type": "application/json"
            },
            "trading_history": {
                "uri": "claude://trading/history",
                "name": "Trading History",
                "description": "Recent trading history and performance",
                "mime_type": "application/json"
            },
            "market_context": {
                "uri": "claude://market/context",
                "name": "Market Context",
                "description": "Current market conditions and context",
                "mime_type": "application/json"
            },
            "strategy_learnings": {
                "uri": "claude://strategy/learnings",
                "name": "Strategy Learnings",
                "description": "Strategy performance data and effectiveness metrics for optimization",
                "mime_type": "application/json"
            },
            "monthly_performance": {
                "uri": "claude://performance/monthly",
                "name": "Monthly Performance",
                "description": "Monthly trading performance summary and metrics",
                "mime_type": "application/json"
            }
        }

        self._log_info(f"Registered {len(self._resources)} MCP resources")

    # MCP Tool Methods

    async def list_tools(self, minimal: bool = True) -> List[Dict[str, Any]]:
        """
        List available tools (MCP method).

        Progressive Discovery Pattern:
        - minimal=True (default): Returns only name + brief description (~30 tokens total)
        - minimal=False: Returns full schemas (~600 tokens) - use sparingly

        Agent should use search_tools() to get full schema for specific tools.
        """
        if not self._initialized:
            await self.initialize()

        if minimal:
            # Progressive discovery: minimal definitions save ~95% tokens
            return [
                {"name": name, "description": brief}
                for name, brief in self.TOOL_BRIEF.items()
            ]
        else:
            return list(self._tools.values())

    async def search_tools(self, query: str = "", detail: str = "brief") -> List[Dict[str, Any]]:
        """
        Progressive tool discovery (Anthropic's research pattern).

        Args:
            query: Search term to filter tools (empty = all tools)
            detail: "brief" for name+description, "full" for complete schema

        Returns:
            Matching tools with requested detail level

        Token savings: ~570 tokens/session vs upfront dump
        """
        if not self._initialized:
            await self.initialize()

        # Filter tools by query
        if query:
            matches = [
                name for name, brief in self.TOOL_BRIEF.items()
                if query.lower() in name.lower() or query.lower() in brief.lower()
            ]
        else:
            matches = list(self.TOOL_BRIEF.keys())

        # Return with requested detail level
        if detail == "full":
            return [self._tools[name] for name in matches if name in self._tools]
        else:
            return [{"name": name, "description": self.TOOL_BRIEF.get(name, "")} for name in matches]

    async def call_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a tool call (MCP method).

        Token Optimization:
        - No JSON indentation (saves ~15% tokens per response)
        - Compact separators for minimal whitespace
        - search_tools handled internally for progressive discovery
        """
        if not self._initialized or not self.tool_executor:
            raise TradingError(
                "MCP server not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

        # Handle search_tools internally (progressive discovery)
        if tool_name == "search_tools":
            query = tool_input.get("query", "")
            detail = tool_input.get("detail", "brief")
            results = await self.search_tools(query, detail)
            return {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(results, separators=(',', ':'))  # Compact JSON
                    }
                ]
            }

        if tool_name not in self._tools:
            raise TradingError(
                f"Tool not found: {tool_name}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

        try:
            # Execute tool using ToolExecutor
            result = await self.tool_executor.execute(tool_name, tool_input)

            # Format result for MCP - COMPACT JSON (no indent, saves ~15% tokens)
            if result.get("success"):
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result.get("output", {}), separators=(',', ':'))
                        }
                    ]
                }
            else:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: {result.get('error', 'Unknown')}"  # Shorter error
                        }
                    ],
                    "isError": True
                }

        except Exception as e:
            self._log_error(f"Tool execution error for {tool_name}: {e}")
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: {tool_name}: {str(e)}"  # Shorter error
                    }
                ],
                "isError": True
            }

    # MCP Resource Methods

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available resources (MCP method)."""
        if not self._initialized:
            await self.initialize()

        return [
            {
                "uri": resource["uri"],
                "name": resource["name"],
                "description": resource["description"],
                "mimeType": resource["mime_type"]
            }
            for resource in self._resources.values()
        ]

    async def read_resource(self, uri: str) -> Dict[str, Any]:
        """Read a resource (MCP method)."""
        if not self._initialized:
            await self.initialize()

        if uri not in [r["uri"] for r in self._resources.values()]:
            raise TradingError(
                f"Resource not found: {uri}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

        try:
            # Get resource data based on URI
            if uri == "claude://portfolio/status":
                data = await self._get_portfolio_status()
            elif uri == "claude://trading/history":
                data = await self._get_trading_history()
            elif uri == "claude://market/context":
                data = await self._get_market_context()
            else:
                raise TradingError(f"Unknown resource URI: {uri}")

            # Token optimization: compact JSON (no indent)
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(data, separators=(',', ':'), default=str)
                    }
                ]
            }

        except Exception as e:
            self._log_error(f"Resource read error for {uri}: {e}")
            raise TradingError(
                f"Failed to read resource {uri}: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    # Resource Data Methods

    async def _get_portfolio_status(self) -> Dict[str, Any]:
        """Get current portfolio status."""
        try:
            account_manager = await self.container.get("paper_trading_account_manager")
            account = await account_manager.get_account("paper_swing_main")

            if not account:
                return {"error": "Account not found"}

            balance = await account_manager.get_account_balance("paper_swing_main")

            return {
                "account_id": account.account_id,
                "balance": balance,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log_error(f"Failed to get portfolio status: {e}")
            return {"error": str(e)}

    async def _get_trading_history(self) -> Dict[str, Any]:
        """Get recent trading history."""
        try:
            store = await self.container.get("paper_trading_store")
            # This would need to be implemented in the store
            # For now, return mock data
            return {
                "recent_trades": [],
                "total_trades": 0,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log_error(f"Failed to get trading history: {e}")
            return {"error": str(e)}

    async def _get_market_context(self) -> Dict[str, Any]:
        """Get current market context."""
        try:
            # This would integrate with market data services
            return {
                "market_status": "open",
                "volatility": "moderate",
                "key_indices": {},
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self._log_error(f"Failed to get market context: {e}")
            return {"error": str(e)}

    # Utility Methods

    def is_initialized(self) -> bool:
        """Check if MCP server is initialized."""
        return self._initialized

    async def cleanup(self) -> None:
        """Cleanup MCP server resources."""
        if not self._initialized:
            return

        self._log_info("Cleaning up ClaudeAgentMCPServer")
        self.tool_executor = None
        self._tools.clear()
        self._resources.clear()
        self._initialized = False

    def _log_info(self, message: str) -> None:
        """Log info message with service name."""
        logger.info(f"[ClaudeAgentMCPServer] {message}")

    def _log_error(self, message: str, exc_info: bool = False) -> None:
        """Log error message with service name."""
        logger.error(f"[ClaudeAgentMCPServer] {message}", exc_info=exc_info)

    def _log_warning(self, message: str) -> None:
        """Log warning message with service name."""
        logger.warning(f"[ClaudeAgentMCPServer] {message}")

    def _log_debug(self, message: str) -> None:
        """Log debug message with service name."""
        logger.debug(f"[ClaudeAgentMCPServer] {message}")