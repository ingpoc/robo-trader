"""
Dependency Injection Container for Robo Trader

Provides centralized dependency management to eliminate global state
and improve testability and maintainability.
"""

import asyncio
from typing import Dict, Any, Optional, Type, TypeVar, Generic
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

from ..config import Config
from .orchestrator import RoboTraderOrchestrator
from ..mcp.broker import ZerodhaBroker
from .database_state import DatabaseStateManager
from .state import StateManager
from .state_coordinator import StateCoordinator
from .background_scheduler import BackgroundScheduler
from .conversation_manager import ConversationManager
from .learning_engine import LearningEngine
from .ai_planner import AIPlanner
from .resource_manager import ResourceManager

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

        # Register core services
        await self._register_core_services()

    async def _register_core_services(self) -> None:
        """Register all core services with the container."""

        # Resource Manager - singleton (initialized first for cleanup tracking)
        async def create_resource_manager():
            return ResourceManager()

        self._register_singleton("resource_manager", create_resource_manager)

        # State Manager - singleton
        async def create_state_manager():
            if self.config.database.enabled:
                # Use database-backed state manager
                from .database_state import DatabaseStateManager
                return DatabaseStateManager(self.config)
            elif hasattr(self.config, 'use_coordinator') and self.config.use_coordinator:
                # Use new StateCoordinator with focused stores
                return StateCoordinator(self.config.state_dir)
            else:
                # Use file-based state manager (legacy)
                return StateManager(self.config.state_dir)

        self._register_singleton("state_manager", create_state_manager)

        # Broker - singleton
        async def create_broker():
            return ZerodhaBroker(self.config)

        self._register_singleton("broker", create_broker)

        # AI Planner
        async def create_ai_planner():
            state_manager = await self.get("state_manager")
            return AIPlanner(self.config, state_manager)

        self._register_singleton("ai_planner", create_ai_planner)

        # Background Scheduler
        async def create_background_scheduler():
            state_manager = await self.get("state_manager")
            # Orchestrator will be injected later to avoid circular dependency
            return BackgroundScheduler(self.config, state_manager)

        self._register_singleton("background_scheduler", create_background_scheduler)

        # Conversation Manager
        async def create_conversation_manager():
            state_manager = await self.get("state_manager")
            return ConversationManager(self.config, state_manager)

        self._register_singleton("conversation_manager", create_conversation_manager)

        # Learning Engine
        async def create_learning_engine():
            state_manager = await self.get("state_manager")
            return LearningEngine(self.config, state_manager)

        self._register_singleton("learning_engine", create_learning_engine)

        # Orchestrator - created last due to dependencies
        async def create_orchestrator():
            state_manager = await self.get("state_manager")
            ai_planner = await self.get("ai_planner")
            background_scheduler = await self.get("background_scheduler")
            conversation_manager = await self.get("conversation_manager")
            learning_engine = await self.get("learning_engine")

            # Create orchestrator with injected dependencies
            orchestrator = RoboTraderOrchestrator(self.config)
            orchestrator.state_manager = state_manager
            orchestrator.ai_planner = ai_planner
            orchestrator.background_scheduler = background_scheduler
            orchestrator.conversation_manager = conversation_manager
            orchestrator.learning_engine = learning_engine

            # Initialize the orchestrator
            await orchestrator.initialize()

            return orchestrator

        self._register_singleton("orchestrator", create_orchestrator)

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
                self._singletons[name] = instance
                return instance

            raise ValueError(f"Service '{name}' not registered")

    async def get_orchestrator(self) -> RoboTraderOrchestrator:
        """Get the orchestrator instance."""
        return await self.get("orchestrator")

    async def get_broker(self) -> ZerodhaBroker:
        """Get the broker instance."""
        return await self.get("broker")

    async def get_state_manager(self) -> StateManager:
        """Get the state manager instance."""
        return await self.get("state_manager")

    async def get_resource_manager(self) -> ResourceManager:
        """Get the resource manager instance."""
        return await self.get("resource_manager")

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

        # Cleanup resource manager last
        try:
            resource_manager = self._singletons.get("resource_manager")
            if resource_manager:
                await resource_manager.cleanup()
        except Exception as e:
            logger.warning(f"Error during resource manager cleanup: {e}")

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

    async def get_broker(self) -> ZerodhaBroker:
        """Get the broker instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_broker()

    async def get_state_manager(self) -> StateManager:
        """Get the state manager instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_state_manager()


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