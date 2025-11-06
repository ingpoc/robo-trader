"""
Agents MCP Server

Combines all agent tools into a single MCP server for the orchestrator.
Uses closure-based dependency injection following Claude Agent SDK best practices.
"""


from claude_agent_sdk import create_sdk_mcp_server
from loguru import logger

from .alert_agent import create_alert_tools
from .educational_agent import create_educational_tools
from .execution_agent import create_execution_agent_tool
from .fundamental_screener import create_fundamental_screener_tool
from .market_monitor import create_market_monitor_tool
# Import tool implementations
from .portfolio_analyzer import create_portfolio_analyzer_tool
from .risk_manager import create_risk_manager_tool
from .strategy_agent import create_strategy_tools
from .technical_analyst import create_technical_analyst_tool


async def create_agents_mcp_server(config, state_manager):
    """
    Create the agents MCP server with all agent tools.

    Uses closure-based dependency injection to provide config and state_manager
    to all tools, following Claude Agent SDK best practices.
    """

    # Create tools with dependencies via closures
    portfolio_tool = create_portfolio_analyzer_tool(config, state_manager)
    technical_tool = create_technical_analyst_tool(config, state_manager)
    fundamental_tool = create_fundamental_screener_tool(config, state_manager)
    risk_tool = create_risk_manager_tool(config, state_manager)
    execution_tool = create_execution_agent_tool(config, state_manager)
    monitor_tool = create_market_monitor_tool(config, state_manager)

    # Educational tools
    educational_tools = create_educational_tools(config, state_manager)

    # Alert tools
    alert_tools = create_alert_tools(config, state_manager)

    # Strategy tools
    strategy_tools = create_strategy_tools(config, state_manager)

    # Combine all tools
    all_tools = [
        portfolio_tool,
        technical_tool,
        fundamental_tool,
        risk_tool,
        execution_tool,
        monitor_tool,
        *educational_tools,
        *alert_tools,
        *strategy_tools,
    ]

    logger.info(f"Created agents MCP server with {len(all_tools)} tools")

    return create_sdk_mcp_server(name="agents", version="1.0.0", tools=all_tools)
