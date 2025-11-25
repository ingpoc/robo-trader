"""
Agents MCP Server

Combines all agent tools into a single MCP server for the orchestrator.
Uses closure-based dependency injection following Claude Agent SDK best practices.
"""

from claude_agent_sdk import create_sdk_mcp_server, tool
from typing import Dict, Any
import json
from loguru import logger

# Import tool implementations
from .portfolio_analyzer import create_portfolio_analyzer_tool
from .technical_analyst import create_technical_analyst_tool
from .fundamental_screener import create_fundamental_screener_tool
from .risk_manager import create_risk_manager_tool
from .execution_agent import create_execution_agent_tool
from .market_monitor import create_market_monitor_tool
from .educational_agent import create_educational_tools
from .alert_agent import create_alert_tools
from .strategy_agent import create_strategy_tools


async def create_agents_mcp_server(
    config,
    state_manager,
    kite_service=None,
    indicators_service=None,
    fundamental_service=None
):
    """
    Create the agents MCP server with all agent tools.
    
    Uses closure-based dependency injection to provide config and state_manager
    to all tools, following Claude Agent SDK best practices.
    
    Args:
        config: Configuration object
        state_manager: Database state manager
        kite_service: Optional KiteConnectService for real market data
        indicators_service: Optional TechnicalIndicatorsService for indicator calculations
        fundamental_service: Optional FundamentalService for fundamental data
    """
    
    # Create tools with dependencies via closures
    portfolio_tool = create_portfolio_analyzer_tool(config, state_manager)
    technical_tool = create_technical_analyst_tool(config, state_manager, kite_service, indicators_service)
    fundamental_tool = create_fundamental_screener_tool(config, state_manager, fundamental_service)
    risk_tool = create_risk_manager_tool(config, state_manager)
    execution_tool = create_execution_agent_tool(config, state_manager, kite_service)
    monitor_tool = create_market_monitor_tool(config, state_manager, kite_service)
    
    # Educational tools
    educational_tools = create_educational_tools(config, state_manager)
    
    # Alert tools
    alert_tools = create_alert_tools(config, state_manager)
    
    # Strategy tools (with services for real market data)
    strategy_tools = create_strategy_tools(
        config,
        state_manager,
        kite_service=kite_service,
        indicators_service=indicators_service,
        fundamental_service=fundamental_service
    )
    
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
    
    return create_sdk_mcp_server(
        name="agents",
        version="1.0.0",
        tools=all_tools
    )