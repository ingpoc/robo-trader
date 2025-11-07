"""
Dependency Injection Container for Robo Trader

Provides centralized dependency management to eliminate global state
and improve testability and maintainability.

The main DI container delegates to modular registries for organization:
- di_registry_core.py - Core infrastructure services
- di_registry_services.py - Domain-specific services
- di_registry_paper_trading.py - Paper trading services
- di_registry_sdk.py - Claude SDK and AI services
- di_registry_coordinators.py - All coordinators and orchestrator
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Type, TypeVar
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)

from src.config import Config
from .database_state import DatabaseStateManager
from .event_bus import EventBus
from .orchestrator import RoboTraderOrchestrator
from .resource_manager import ResourceManager
from .safety_layer import SafetyLayer

# Type annotations for convenience methods
from src.services.portfolio_service import PortfolioService
from src.services.risk_service import RiskService
from src.services.execution_service import ExecutionService
from src.services.analytics_service import AnalyticsService
from src.services.learning_service import LearningService
from src.services.market_data_service import MarketDataService

# Import registries
from .di_registry_core import register_core_services
from .di_registry_services import register_domain_services
from .di_registry_paper_trading import register_paper_trading_services
from .di_registry_sdk import register_sdk_services
from .di_registry_mcp import register_mcp_services
from .di_registry_coordinators import register_coordinators, register_orchestrator

T = TypeVar('T')
class DependencyContainer:
    """
    Centralized dependency injection container.

    Manages singleton instances and provides dependency resolution.
    """

    def __init__(self):
        self._instances: Dict[str, Any] = {}
        self._factories: Dict[str, callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = asyncio.Lock()

    async def initialize(self, config: Config) -> None:
        """Initialize the container with configuration."""
        self.config = config

        # Setup logging if not already configured (don't clear logs - already cleared in app.py)
        from .logging_config import ensure_logging_setup
        # Use LOG_LEVEL from environment (set by CLI flag or .env)
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        ensure_logging_setup(config.logs_dir, log_level, clear_logs=False)

        # Register all services through modular registries
        await register_core_services(self)
        await register_domain_services(self)

        # Paper trading must be after domain services (depends on market_data_service)
        await register_paper_trading_services(self)

        # SDK services must be after core services
        await register_sdk_services(self)

        # MCP services must be after SDK services (depends on SDK client manager)
        await register_mcp_services(self)

        # Coordinators must be after all services
        await register_coordinators(self)

        # Orchestrator must be last (depends on all coordinators)
        await register_orchestrator(self)
    def _register_singleton(self, name: str, factory: callable) -> None:
        """Register a singleton service."""
        self._factories[name] = factory

    async def get(self, name: str) -> Any:
        """Get a service instance."""
        async with self._lock:
            if name in self._singletons:
                return self._singletons[name]

        if name in self._factories:
            instance = await self._factories[name]()

            async with self._lock:
                if name not in self._singletons:
                    self._singletons[name] = instance
                    return instance
                else:
                    return self._singletons[name]

        raise ValueError(f"Service '{name}' not registered")

    async def get_orchestrator(self) -> RoboTraderOrchestrator:
        """Get the orchestrator instance."""
        return await self.get("orchestrator")

    async def get_state_manager(self) -> DatabaseStateManager:
        """Get the state manager instance."""
        return await self.get("state_manager")

    async def get_resource_manager(self) -> ResourceManager:
        """Get the resource manager instance."""
        return await self.get("resource_manager")
    async def get_claude_sdk_auth(self):
        """Get the Claude SDK authentication instance."""
        return await self.get("claude_sdk_auth")

    async def get_event_bus(self) -> EventBus:
        """Get the event bus instance."""
        return await self.get("event_bus")

    async def get_safety_layer(self) -> SafetyLayer:
        """Get the safety layer instance."""
        return await self.get("safety_layer")
    async def get_claude_agent_mcp_server(self):
        """Get the Claude Agent MCP server instance."""
        return await self.get("claude_agent_mcp_server")

    async def get_portfolio_service(self) -> PortfolioService:
        """Get the portfolio service instance."""
        return await self.get("portfolio_service")

    async def get_risk_service(self) -> RiskService:
        """Get the risk service instance."""
        return await self.get("risk_service")
    # async def get_queue_coordinator(self) -> QueueCoordinator:  # Not implemented
        """Get the queue coordinator instance."""
        return await self.get("queue_coordinator")

    async def get_execution_service(self) -> ExecutionService:
        """Get the execution service instance."""
        return await self.get("execution_service")
    async def get_event_router_service(self) -> "EventRouterService":
        """Get the event router service instance."""
        return await self.get("event_router_service")

    async def get_market_data_service(self) -> MarketDataService:
        """Get the market data service instance."""
        return await self.get("market_data_service")

    async def get_analytics_service(self) -> AnalyticsService:
        """Get the analytics service instance."""
        return await self.get("analytics_service")

    async def get_learning_service(self) -> LearningService:
        """Get the learning service instance."""
        return await self.get("learning_service")
    async def cleanup(self) -> None:
        """Cleanup all services."""
        logger.info("Cleaning up dependency container")

        # Get orchestrator and call its cleanup
        try:
            orchestrator = self._singletons.get("orchestrator")
            if orchestrator:
                await orchestrator.end_session()
        except Exception as e:
            logger.warning(f"Error during orchestrator cleanup: {e}")

        # Get broker and call its cleanup
        try:
            broker = self._singletons.get("broker")
            if broker:
                pass
        except Exception as e:
            logger.warning(f"Error during broker cleanup: {e}")

        # Cleanup services in reverse order
        services_to_cleanup = [
            "market_data_service", "learning_service", "analytics_service",
            "execution_service", "risk_service", "portfolio_service", "feature_management_service",
            "strategy_evolution_engine", "event_router_service",
            "safety_layer", "event_bus", "learning_engine", "conversation_manager",
            "background_scheduler", "ai_planner", "state_manager", "resource_manager"
        ]

        for service_name in services_to_cleanup:
            try:
                service = self._singletons.get(service_name)
                if service and hasattr(service, 'close'):
                    await service.close()
            except Exception as e:
                logger.warning(f"Error during {service_name} cleanup: {e}")

        # Clear all instances
        self._singletons.clear()
        logger.info("Dependency container cleanup complete")
@asynccontextmanager
async def dependency_container(config: Config):
    """
    Context manager for dependency injection container.

    Provides proper resource management and eliminates global state.
    Usage:
        async with dependency_container(config) as container:
            orchestrator = await container.get_orchestrator()
            # Use services...
    """
    container = DependencyContainer()
    try:
        await container.initialize(config)
        yield container
    finally:
        await container.cleanup()
class ServiceProvider:
    """
    Service provider for accessing services without global state.

    Use this instead of global functions for better testability and maintainability.
    """

    def __init__(self, config: Config):
        self.config = config
        self._container: Optional[DependencyContainer] = None

    async def __aenter__(self):
        self._container = DependencyContainer()
        await self._container.initialize(self.config)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._container:
            await self._container.cleanup()
            self._container = None

    async def get_orchestrator(self) -> RoboTraderOrchestrator:
        """Get the orchestrator instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_orchestrator()

    async def get_state_manager(self) -> DatabaseStateManager:
        """Get the state manager instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_state_manager()

    async def get_claude_sdk_auth(self):
        """Get the Claude SDK authentication instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_claude_sdk_auth()
    async def get_event_bus(self) -> EventBus:
        """Get the event bus instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_event_bus()

    async def get_safety_layer(self) -> SafetyLayer:
        """Get the safety layer instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_safety_layer()
    async def get_claude_agent_mcp_server(self):
        """Get the Claude Agent MCP server instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_claude_agent_mcp_server()

    async def get_portfolio_service(self) -> PortfolioService:
        """Get the portfolio service instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_portfolio_service()

    async def get_risk_service(self) -> RiskService:
        """Get the risk service instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_risk_service()

    # async def get_queue_coordinator(self) -> QueueCoordinator:  # Not implemented
        """Get the queue coordinator instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_queue_coordinator()

    async def get_execution_service(self) -> ExecutionService:
        """Get the execution service instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_execution_service()
    async def get_event_router_service(self) -> "EventRouterService":
        """Get the event router service instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_event_router_service()

    async def get_analytics_service(self) -> AnalyticsService:
        """Get the analytics service instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_analytics_service()

    async def get_learning_service(self) -> LearningService:
        """Get the learning service instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_learning_service()
# Global container instance for backward compatibility
_global_container: Optional[DependencyContainer] = None
async def get_container() -> Optional[DependencyContainer]:
    """Get the global container instance."""
    global _global_container
    return _global_container
async def set_container(container: DependencyContainer) -> None:
    """Set the global container instance."""
    global _global_container
    _global_container = container
# Legacy functions for backward compatibility (deprecated)
# These will be removed in a future version
async def initialize_container(config: Config) -> DependencyContainer:
    """DEPRECATED: Use ServiceProvider or dependency_container context manager instead."""
    global _global_container
    if _global_container:
        logger.warning("Container already initialized, returning existing instance")
        return _global_container

    container = DependencyContainer()
    await container.initialize(config)
    _global_container = container
    return container
async def cleanup_container():
    """DEPRECATED: Cleanup is now handled by context managers."""
    global _global_container
    if _global_container:
        await _global_container.cleanup()
        _global_container = None
# Import logger at the end to avoid circular imports
from loguru import logger

# Add missing imports for the new services
import os
import base64
from cryptography.fernet import Fernet