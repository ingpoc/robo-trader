"""
Dependency Injection Container for Robo Trader

Provides centralized dependency management to eliminate global state
and improve testability and maintainability.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, Type, TypeVar, Generic
from contextlib import asynccontextmanager
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from ..config import Config
from .orchestrator import RoboTraderOrchestrator
from ..mcp.broker import ZerodhaBroker
from .database_state import DatabaseStateManager
from .background_scheduler import BackgroundScheduler
from .conversation_manager import ConversationManager
from .learning_engine import LearningEngine
from .ai_planner import AIPlanner
from .resource_manager import ResourceManager
from .event_bus import EventBus, initialize_event_bus
from .safety_layer import SafetyLayer
# Services imported locally to avoid circular imports
from .coordinators import (
    SessionCoordinator,
    QueryCoordinator,
    TaskCoordinator,
    StatusCoordinator,
    LifecycleCoordinator,
    BroadcastCoordinator,
    # ClaudeAgentCoordinator,  # Commented out to avoid circular imports
)

# Forward declarations for services to avoid import issues
PortfolioService = None
RiskService = None
ExecutionService = None
AnalyticsService = None
LearningService = None
LiveTradingService = None
MarketDataService = None
EnterpriseSecurityService = None
AdvancedMonitoringService = None
ScalabilityService = None
FeatureManagementService = None
EventRouterService = None
QueueCoordinator = None
ToolExecutor = None
ResponseValidator = None
ClaudeStrategyStore = None

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

        # Setup logging if not already configured
        from .logging_config import ensure_logging_setup
        ensure_logging_setup(config.logs_dir, 'INFO')

        # Register core services
        await self._register_core_services()

    async def _register_core_services(self) -> None:
        """Register all core services with the container."""

        # Resource Manager - singleton (initialized first for cleanup tracking)
        async def create_resource_manager():
            return ResourceManager()

        self._register_singleton("resource_manager", create_resource_manager)

        # Event Bus - singleton (foundation for all services)
        async def create_event_bus():
            return await initialize_event_bus(self.config)

        self._register_singleton("event_bus", create_event_bus)

        # Safety Layer - singleton (critical for all operations)
        async def create_safety_layer():
            event_bus = await self.get("event_bus")
            safety_layer = SafetyLayer(self.config, event_bus)
            await safety_layer.initialize()
            return safety_layer

        self._register_singleton("safety_layer", create_safety_layer)

        # State Manager - singleton (Database-backed only)
        async def create_state_manager():
            from .database_state import DatabaseStateManager
            logger.info("Creating DatabaseStateManager instance...")
            manager = DatabaseStateManager(self.config)
            logger.info("DatabaseStateManager instance created, starting initialization...")
            await manager.initialize()
            logger.info("DatabaseStateManager initialized successfully")
            return manager

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

        # Portfolio Service
        async def create_portfolio_service():
            event_bus = await self.get("event_bus")
            portfolio_service = PortfolioService(self.config, event_bus)
            await portfolio_service.initialize()
            return portfolio_service

        self._register_singleton("portfolio_service", create_portfolio_service)

        # Risk Service
        async def create_risk_service():
            event_bus = await self.get("event_bus")
            risk_service = RiskService(self.config, event_bus)
            await risk_service.initialize()
            return risk_service

        self._register_singleton("risk_service", create_risk_service)

        # Execution Service
        async def create_execution_service():
            event_bus = await self.get("event_bus")
            broker = await self.get("broker")
            execution_service = ExecutionService(self.config, event_bus, broker)
            await execution_service.initialize()
            return execution_service

        self._register_singleton("execution_service", create_execution_service)

        # Analytics Service
        async def create_analytics_service():
            event_bus = await self.get("event_bus")
            analytics_service = AnalyticsService(self.config, event_bus)
            await analytics_service.initialize()
            return analytics_service

        self._register_singleton("analytics_service", create_analytics_service)

        # Learning Service
        async def create_learning_service():
            event_bus = await self.get("event_bus")
            learning_service = LearningService(self.config, event_bus)
            await learning_service.initialize()
            return learning_service

        self._register_singleton("learning_service", create_learning_service)

        # Paper Trading Infrastructure
        async def create_paper_trading_store():
            from ..stores.paper_trading_store import PaperTradingStore
            import os
            # Use persistent path in /app/data for container environments
            persistent_dir = "/app/data"
            os.makedirs(persistent_dir, exist_ok=True)
            db_path = os.path.join(persistent_dir, "paper_trading.db")
            store = PaperTradingStore(db_path)
            await store.initialize()
            return store

        self._register_singleton("paper_trading_store", create_paper_trading_store)

        async def create_paper_trading_account_manager():
            from ..services.paper_trading.account_manager import PaperTradingAccountManager
            store = await self.get("paper_trading_store")
            manager = PaperTradingAccountManager(store)
            return manager

        self._register_singleton("paper_trading_account_manager", create_paper_trading_account_manager)

        async def create_paper_trade_executor():
            from ..services.paper_trading.trade_executor import PaperTradeExecutor
            store = await self.get("paper_trading_store")
            account_manager = await self.get("paper_trading_account_manager")
            executor = PaperTradeExecutor(store, account_manager)
            return executor

        self._register_singleton("paper_trade_executor", create_paper_trade_executor)

        # Claude Agent Services
        async def create_tool_executor():
            risk_config = self.config.risk.__dict__ if hasattr(self.config, 'risk') else {}
            return ToolExecutor(self, risk_config)

        self._register_singleton("tool_executor", create_tool_executor)

        async def create_response_validator():
            risk_config = self.config.risk.__dict__ if hasattr(self.config, 'risk') else {}
            return ResponseValidator(risk_config)

        self._register_singleton("response_validator", create_response_validator)

        async def create_claude_strategy_store():
            store = ClaudeStrategyStore(self.config)
            await store.initialize()
            return store
        # Claude SDK Authentication
        async def create_claude_sdk_auth():
            from ..services.claude_agent.sdk_auth import ClaudeSDKAuth
            sdk_auth = ClaudeSDKAuth(self)
            await sdk_auth.initialize()
            return sdk_auth

        self._register_singleton("claude_sdk_auth", create_claude_sdk_auth)
        # Claude Agent MCP Server
        async def create_claude_agent_mcp_server():
            from ..services.claude_agent.mcp_server import ClaudeAgentMCPServer
            mcp_server = ClaudeAgentMCPServer(self)
            await mcp_server.initialize()
            return mcp_server

        self._register_singleton("claude_agent_mcp_server", create_claude_agent_mcp_server)
        # Event Router Service
        async def create_event_router_service():
            from ..services.event_router_service import EventRouterService
            event_router_service = EventRouterService(self)
            await event_router_service.initialize()
            return event_router_service

        self._register_singleton("event_router_service", create_event_router_service)

        # Live Trading Service
        async def create_live_trading_service():
            event_bus = await self.get("event_bus")
            broker = await self.get("broker")
            live_trading_service = LiveTradingService(self.config, event_bus, broker)
            await live_trading_service.initialize()
            return live_trading_service

        self._register_singleton("live_trading_service", create_live_trading_service)

        # Market Data Service
        async def create_market_data_service():
            event_bus = await self.get("event_bus")
            broker = await self.get("broker")
            market_data_service = MarketDataService(self.config, event_bus, broker)
            await market_data_service.initialize()
            return market_data_service

        self._register_singleton("market_data_service", create_market_data_service)

        # Enterprise Security Service
        async def create_enterprise_security_service():
            event_bus = await self.get("event_bus")
            enterprise_security_service = EnterpriseSecurityService(self.config, event_bus)
            await enterprise_security_service.initialize()
            return enterprise_security_service

        self._register_singleton("enterprise_security_service", create_enterprise_security_service)

        # Advanced Monitoring Service
        async def create_advanced_monitoring_service():
            event_bus = await self.get("event_bus")
            advanced_monitoring_service = AdvancedMonitoringService(self.config, event_bus)
            await advanced_monitoring_service.initialize()
            return advanced_monitoring_service

        self._register_singleton("advanced_monitoring_service", create_advanced_monitoring_service)

        # Scalability Service
        async def create_scalability_service():
            event_bus = await self.get("event_bus")
            scalability_service = ScalabilityService(self.config, event_bus)
            await scalability_service.initialize()
            return scalability_service

        self._register_singleton("scalability_service", create_scalability_service)

        self._register_singleton("claude_strategy_store", create_claude_strategy_store)

        # Feature Management Service
        async def create_feature_management_service():
            event_bus = await self.get("event_bus")
            feature_service = FeatureManagementService(self.config, event_bus)
            await feature_service.initialize()
            
            # Set up service integrations
            background_scheduler = await self.get("background_scheduler")
            feature_service.set_background_scheduler(background_scheduler)
            
            # Get coordinators for integration
            if hasattr(self, '_singletons') and "claude_agent_coordinator" in self._singletons:
                agent_coordinator = await self.get("claude_agent_coordinator")
                feature_service.set_agent_coordinator(agent_coordinator)
            
            return feature_service

        self._register_singleton("feature_management_service", create_feature_management_service)

        # Coordinators
        async def create_session_coordinator():
            return SessionCoordinator(self.config)

        self._register_singleton("session_coordinator", create_session_coordinator)

        async def create_query_coordinator():
            session_coordinator = await self.get("session_coordinator")
            return QueryCoordinator(self.config, session_coordinator)

        self._register_singleton("query_coordinator", create_query_coordinator)

        async def create_task_coordinator():
            state_manager = await self.get("state_manager")
            return TaskCoordinator(self.config, state_manager)

        self._register_singleton("task_coordinator", create_task_coordinator)

        async def create_status_coordinator():
            state_manager = await self.get("state_manager")
            ai_planner = await self.get("ai_planner")
            background_scheduler = await self.get("background_scheduler")
            session_coordinator = await self.get("session_coordinator")
            return StatusCoordinator(
                self.config,
                state_manager,
                ai_planner,
                background_scheduler,
                session_coordinator
            )

        self._register_singleton("status_coordinator", create_status_coordinator)

        async def create_lifecycle_coordinator():
            background_scheduler = await self.get("background_scheduler")
            return LifecycleCoordinator(self.config, background_scheduler)

        self._register_singleton("lifecycle_coordinator", create_lifecycle_coordinator)

        async def create_broadcast_coordinator():
            return BroadcastCoordinator(self.config)

        self._register_singleton("broadcast_coordinator", create_broadcast_coordinator)

        async def create_queue_coordinator():
            return QueueCoordinator(self.config, self)

        self._register_singleton("queue_coordinator", create_queue_coordinator)

        async def create_claude_agent_coordinator():
            event_bus = await self.get("event_bus")
            strategy_store = await self.get("claude_strategy_store")
            tool_executor = await self.get("tool_executor")
            response_validator = await self.get("response_validator")
            coordinator = ClaudeAgentCoordinator(self.config, event_bus, strategy_store, self)
            await coordinator.initialize()
            return coordinator

        self._register_singleton("claude_agent_coordinator", create_claude_agent_coordinator)

        # Orchestrator - created last due to dependencies
        async def create_orchestrator():
            logger.info("Creating orchestrator - getting coordinators...")
            session_coordinator = await self.get("session_coordinator")
            query_coordinator = await self.get("query_coordinator")
            task_coordinator = await self.get("task_coordinator")
            status_coordinator = await self.get("status_coordinator")
            lifecycle_coordinator = await self.get("lifecycle_coordinator")
            broadcast_coordinator = await self.get("broadcast_coordinator")

            logger.info("Creating orchestrator - getting legacy dependencies...")
            state_manager = await self.get("state_manager")
            ai_planner = await self.get("ai_planner")
            background_scheduler = await self.get("background_scheduler")
            conversation_manager = await self.get("conversation_manager")
            learning_engine = await self.get("learning_engine")

            logger.info("Creating orchestrator instance...")
            orchestrator = RoboTraderOrchestrator(self.config)

            orchestrator.session_coordinator = session_coordinator
            orchestrator.query_coordinator = query_coordinator
            orchestrator.task_coordinator = task_coordinator
            orchestrator.status_coordinator = status_coordinator
            orchestrator.lifecycle_coordinator = lifecycle_coordinator
            orchestrator.broadcast_coordinator = broadcast_coordinator

            orchestrator.state_manager = state_manager
            orchestrator.ai_planner = ai_planner
            orchestrator.background_scheduler = background_scheduler
            orchestrator.conversation_manager = conversation_manager
            orchestrator.learning_engine = learning_engine

            logger.info("Orchestrator created (initialization deferred until first use)")
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

    async def get_broker(self) -> ZerodhaBroker:
        """Get the broker instance."""
        return await self.get("broker")

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
    async def get_queue_coordinator(self) -> QueueCoordinator:
        """Get the queue coordinator instance."""
        return await self.get("queue_coordinator")

    async def get_execution_service(self) -> ExecutionService:
        """Get the execution service instance."""
        return await self.get("execution_service")
    async def get_event_router_service(self) -> "EventRouterService":
        """Get the event router service instance."""
        return await self.get("event_router_service")

    async def get_live_trading_service(self) -> LiveTradingService:
        """Get the live trading service instance."""
        return await self.get("live_trading_service")

    async def get_market_data_service(self) -> MarketDataService:
        """Get the market data service instance."""
        return await self.get("market_data_service")

    async def get_enterprise_security_service(self) -> EnterpriseSecurityService:
        """Get the enterprise security service instance."""
        return await self.get("enterprise_security_service")

    async def get_advanced_monitoring_service(self) -> AdvancedMonitoringService:
        """Get the advanced monitoring service instance."""
        return await self.get("advanced_monitoring_service")

    async def get_scalability_service(self) -> ScalabilityService:
        """Get the scalability service instance."""
        return await self.get("scalability_service")

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
            "scalability_service", "advanced_monitoring_service", "enterprise_security_service",
            "market_data_service", "live_trading_service", "learning_service", "analytics_service",
            "execution_service", "risk_service", "portfolio_service", "feature_management_service",
            "safety_layer", "event_bus", "learning_engine", "conversation_manager",
            "background_scheduler", "ai_planner", "broker", "state_manager", "resource_manager"
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

    async def get_broker(self) -> ZerodhaBroker:
        """Get the broker instance."""
        if not self._container:
            raise RuntimeError("ServiceProvider not initialized. Use async context manager.")
        return await self._container.get_broker()

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

    async def get_queue_coordinator(self) -> QueueCoordinator:
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