"""
MCP Server Registration for Dependency Injection Container

Registers Model Context Protocol (MCP) server and related services:
- Paper Trading MCP Server
- MCP Task Handlers
- MCP Integration Services
"""

import logging

logger = logging.getLogger(__name__)


async def register_mcp_services(container: 'DependencyContainer') -> None:
    """Register all MCP server and related services."""

    # Enhanced Paper Trading MCP Server with Progressive Discovery
    async def create_enhanced_paper_trading_mcp_server():
        from ..mcp.enhanced_paper_trading_server import create_enhanced_paper_trading_server

        # Initial discovery context
        discovery_context = {
            "workflow_stage": "research",
            "portfolio_value": 0.0,
            "trades_executed": 0,
            "current_positions": [],
            "active_strategies": [],
            "user_expertise_level": "intermediate"
        }

        server, discovery_manager = await create_enhanced_paper_trading_server(container, discovery_context)

        # Store both server and discovery manager
        return {
            "server": server,
            "discovery_manager": discovery_manager
        }

    container._register_singleton("enhanced_paper_trading_mcp_server", create_enhanced_paper_trading_mcp_server)

    # MCP Task Handlers Service
    async def create_mcp_task_handlers_service():
        from ..services.mcp_task_handlers import MCP_HANDLERS
        # Initialize handlers (they will get dependencies from container when needed)
        return {
            "handlers": MCP_HANDLERS,
            "initialized": True
        }

    container._register_singleton("mcp_task_handlers", create_mcp_task_handlers_service)

    # MCP Integration Service
    async def create_mcp_integration_service():
        from ..services.mcp_integration_service import MCPIntegrationService
        task_service = await container.get("task_service")
        workflow_manager = await container.get("workflow_sdk_manager")

        mcp_integration = MCPIntegrationService(
            task_service=task_service,
            workflow_manager=workflow_manager,
            container=container
        )
        await mcp_integration.initialize()
        return mcp_integration

    container._register_singleton("mcp_integration", create_mcp_integration_service)

    logger.info("MCP services registered successfully")