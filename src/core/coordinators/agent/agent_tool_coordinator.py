"""
Agent Tool Coordinator

Focused coordinator for Claude agent MCP tool setup.
Extracted from ClaudeAgentCoordinator for single responsibility.
"""

import json
import logging
from typing import Any, Dict, List

from claude_agent_sdk import ClaudeAgentOptions, create_sdk_mcp_server, tool

from src.config import Config
from src.services.claude_agent.tool_executor import ToolExecutor

from ..base_coordinator import BaseCoordinator

logger = logging.getLogger(__name__)


class AgentToolCoordinator(BaseCoordinator):
    """
    Coordinates Claude agent MCP tool setup.

    Responsibilities:
    - Create MCP server with trading tools
    - Configure SDK options
    - Manage tool definitions
    """

    def __init__(self, config: Config, tool_executor: ToolExecutor):
        super().__init__(config)
        self.tool_executor = tool_executor
        self.mcp_server = None
        self._tools: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize agent tool coordinator."""
        self._log_info("Initializing AgentToolCoordinator")

        # Create MCP tools
        self._create_tools()

        # Create MCP server
        self.mcp_server = create_sdk_mcp_server(
            name="trading_tools", version="1.0.0", tools=self._tools
        )

        self._initialized = True

    def _create_tools(self) -> None:
        """Create all trading tools with @tool decorators."""
        tool_executor = self.tool_executor

        @tool(
            "execute_trade",
            "Execute a paper trade (buy/sell equity or option)",
            {
                "symbol": str,
                "action": str,
                "quantity": int,
                "entry_price": float,
                "strategy_rationale": str,
                "stop_loss": float,
                "target_price": float,
            },
        )
        async def execute_trade_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("execute_trade", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Trade execution failed: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool(
            "close_position",
            "Close an open trading position",
            {"trade_id": str, "exit_price": float, "reason": str},
        )
        async def close_position_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("close_position", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Position close failed: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool("check_balance", "Get current account balance and buying power", {})
        async def check_balance_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("check_balance", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Balance check failed: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool(
            "get_market_data", "Get current market data for a symbol", {"symbol": str}
        )
        async def get_market_data_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("get_market_data", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Market data fetch failed: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool("analyze_portfolio", "Analyze current portfolio composition and risk", {})
        async def analyze_portfolio_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("analyze_portfolio", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {"type": "text", "text": f"Portfolio analysis failed: {str(e)}"}
                    ],
                    "is_error": True,
                }

        @tool("get_open_positions", "Get all currently open trading positions", {})
        async def get_open_positions_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("get_open_positions", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Open positions fetch failed: {str(e)}",
                        }
                    ],
                    "is_error": True,
                }

        @tool("calculate_risk_metrics", "Calculate portfolio risk metrics", {})
        async def calculate_risk_metrics_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await tool_executor.execute("calculate_risk_metrics", args)
                return {"content": [{"type": "text", "text": json.dumps(result)}]}
            except Exception as e:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Risk metrics calculation failed: {str(e)}",
                        }
                    ],
                    "is_error": True,
                }

        # Collect all tools
        self._tools = [
            execute_trade_tool,
            close_position_tool,
            check_balance_tool,
            get_market_data_tool,
            analyze_portfolio_tool,
            get_open_positions_tool,
            calculate_risk_metrics_tool,
        ]

    def get_mcp_server(self):
        """Get MCP server instance."""
        return self.mcp_server

    def get_sdk_options(self) -> ClaudeAgentOptions:
        """Get configured SDK options."""
        return ClaudeAgentOptions(
            mcp_servers={"trading": self.mcp_server},
            allowed_tools=[
                "mcp__trading__execute_trade",
                "mcp__trading__close_position",
                "mcp__trading__check_balance",
                "mcp__trading__get_market_data",
                "mcp__trading__analyze_portfolio",
                "mcp__trading__get_open_positions",
                "mcp__trading__calculate_risk_metrics",
            ],
            max_turns=50,
            system_prompt_optimization=True,
        )

    async def cleanup(self) -> None:
        """Cleanup agent tool coordinator resources."""
        self._log_info("AgentToolCoordinator cleanup complete")
        self.mcp_server = None
        self._tools = []
