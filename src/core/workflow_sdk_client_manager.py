"""
Workflow-Specific SDK Client Manager.

Manages separate Claude SDK clients for different workflows to ensure
proper isolation and specialized configuration per workflow.

Workflows:
- portfolio_analysis: For portfolio analysis and optimization
- paper_trading: For paper trading operations and market research
"""

import asyncio
import logging
from typing import Dict, Optional, Any
from datetime import datetime

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from .claude_sdk_client_manager import ClaudeSDKClientManager, ClientHealthStatus
from ..core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class WorkflowSDKClientManager:
    """
    Manager for workflow-specific Claude SDK clients.

    Provides isolated client management for different workflows:
    - Portfolio Analysis: Clients optimized for data analysis and optimization
    - Paper Trading: Clients optimized for market research and trading decisions

    Each workflow gets its own client with specialized configuration.
    """

    def __init__(self):
        """Initialize workflow SDK client manager."""
        self._base_manager: Optional[ClaudeSDKClientManager] = None
        self._workflow_clients: Dict[str, ClaudeSDKClient] = {}
        self._workflow_options: Dict[str, ClaudeAgentOptions] = {}
        self._workflow_health: Dict[str, ClientHealthStatus] = {}
        self._workflow_locks: Dict[str, asyncio.Lock] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the workflow client manager."""
        if self._initialized:
            return

        logger.info("Initializing Workflow SDK Client Manager")

        # Get base client manager instance
        self._base_manager = await ClaudeSDKClientManager.get_instance()

        # Initialize workflow-specific configurations
        await self._initialize_workflow_configurations()

        self._initialized = True
        logger.info("Workflow SDK Client Manager initialized successfully")

    async def _initialize_workflow_configurations(self) -> None:
        """Initialize workflow-specific client configurations."""

        # Portfolio Analysis Workflow Configuration
        portfolio_options = ClaudeAgentOptions(
            name="Portfolio Analysis Agent",
            instructions="""You are a specialized portfolio analysis agent focused on:
1. Analyzing existing portfolio holdings
2. Optimizing data quality through prompt improvements
3. Generating investment recommendations based on comprehensive analysis
4. Evaluating data sources and improving prompt templates

Your primary goal is to enhance portfolio analysis quality through iterative
prompt optimization and thorough data evaluation.""",
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            timeout=60.0
        )

        # Paper Trading Workflow Configuration
        paper_trading_options = ClaudeAgentOptions(
            name="Paper Trading Agent",
            instructions="""You are an independent paper trading agent focused on:
1. Market research using Perplexity API and other sources
2. Making trading decisions based on real market data
3. Managing a paper trading portfolio with risk management
4. Evaluating strategy performance and evolving trading approaches

Your primary goal is to generate profitable trading decisions through
thorough market research and disciplined risk management.""",
            model="claude-3-5-sonnet-20241022",
            max_tokens=4000,
            timeout=60.0
        )

        self._workflow_options = {
            "portfolio_analysis": portfolio_options,
            "paper_trading": paper_trading_options
        }

        # Initialize locks and health tracking
        for workflow in self._workflow_options.keys():
            self._workflow_locks[workflow] = asyncio.Lock()
            self._workflow_health[workflow] = ClientHealthStatus()

    async def get_workflow_client(self, workflow_name: str) -> ClaudeSDKClient:
        """
        Get a client for a specific workflow.

        Args:
            workflow_name: Name of workflow ('portfolio_analysis', 'paper_trading')

        Returns:
            ClaudeSDKClient configured for the workflow

        Raises:
            TradingError: If workflow is not supported or client creation fails
        """
        if not self._initialized:
            await self.initialize()

        if workflow_name not in self._workflow_options:
            raise TradingError(
                f"Unsupported workflow: {workflow_name}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
                details={"supported_workflows": list(self._workflow_options.keys())}
            )

        # Ensure lock exists for this workflow
        if workflow_name not in self._workflow_locks:
            self._workflow_locks[workflow_name] = asyncio.Lock()

        async with self._workflow_locks[workflow_name]:
            # Return existing client if healthy
            if workflow_name in self._workflow_clients and self._workflow_clients[workflow_name]:
                health = self._workflow_health[workflow_name]
                if health.is_healthy:
                    logger.debug(f"Reusing existing {workflow_name} client")
                    return self._workflow_clients[workflow_name]
                else:
                    logger.warning(f"{workflow_name} client unhealthy, recreating")

            # Create new client for workflow
            try:
                logger.info(f"Creating new {workflow_name} SDK client")
                options = self._workflow_options[workflow_name]

                # Use base manager to create client
                client = await self._base_manager.get_client(workflow_name, options)

                # Store client and update health
                self._workflow_clients[workflow_name] = client
                self._workflow_health[workflow_name].is_healthy = True
                self._workflow_health[workflow_name].last_check = datetime.utcnow()

                logger.info(f"Successfully created {workflow_name} SDK client")
                return client

            except Exception as e:
                logger.error(f"Failed to create {workflow_name} client: {e}")
                self._workflow_health[workflow_name].is_healthy = False
                self._workflow_health[workflow_name].last_error = str(e)

                raise TradingError(
                    f"Failed to create {workflow_name} SDK client: {e}",
                    category=ErrorCategory.API,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True,
                    retry_after_seconds=30
                )

    async def health_check_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """
        Perform health check for a workflow client.

        Args:
            workflow_name: Name of workflow to check

        Returns:
            Health status dictionary
        """
        if workflow_name not in self._workflow_health:
            return {
                "workflow": workflow_name,
                "status": "unknown",
                "message": "Workflow not configured"
            }

        health = self._workflow_health[workflow_name]

        # Basic health check based on last activity
        is_healthy = health.is_healthy
        last_activity = health.last_query_time or health.last_check

        if last_activity:
            time_since_activity = (datetime.utcnow() - last_activity).total_seconds()
            if time_since_activity > 300:  # 5 minutes
                is_healthy = False

        return {
            "workflow": workflow_name,
            "status": "healthy" if is_healthy else "unhealthy",
            "last_activity": last_activity.isoformat() if last_activity else None,
            "total_queries": health.total_queries,
            "error_count": health.total_errors,
            "last_error": health.last_error
        }

    async def get_all_workflow_health(self) -> Dict[str, Dict[str, Any]]:
        """Get health status for all configured workflows."""
        health_status = {}

        for workflow_name in self._workflow_options.keys():
            health_status[workflow_name] = await self.health_check_workflow(workflow_name)

        return health_status

    async def reset_workflow_client(self, workflow_name: str) -> bool:
        """
        Reset a workflow client (useful after errors or for testing).

        Args:
            workflow_name: Name of workflow to reset

        Returns:
            True if successful, False otherwise
        """
        if workflow_name not in self._workflow_options:
            return False

        try:
            if workflow_name in self._workflow_locks:
                async with self._workflow_locks[workflow_name]:
                    self._workflow_clients[workflow_name] = None
                    self._workflow_health[workflow_name] = ClientHealthStatus()

            logger.info(f"Reset {workflow_name} workflow client")
            return True

        except Exception as e:
            logger.error(f"Failed to reset {workflow_name} client: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup all workflow clients."""
        logger.info("Cleaning up workflow SDK clients")

        for workflow_name in self._workflow_clients.keys():
            try:
                # Reset client health
                if workflow_name in self._workflow_health:
                    self._workflow_health[workflow_name].is_healthy = False

                # Clear client reference
                self._workflow_clients[workflow_name] = None

                logger.debug(f"Cleaned up {workflow_name} client")

            except Exception as e:
                logger.error(f"Error cleaning up {workflow_name} client: {e}")

        self._initialized = False
        logger.info("Workflow SDK client cleanup complete")


# Global instance for workflow client manager
_workflow_manager: Optional[WorkflowSDKClientManager] = None
_workflow_manager_lock = asyncio.Lock()


async def get_workflow_sdk_manager() -> WorkflowSDKClientManager:
    """Get the global workflow SDK client manager instance."""
    global _workflow_manager

    if _workflow_manager is None:
        async with _workflow_manager_lock:
            if _workflow_manager is None:
                _workflow_manager = WorkflowSDKClientManager()
                await _workflow_manager.initialize()

    return _workflow_manager