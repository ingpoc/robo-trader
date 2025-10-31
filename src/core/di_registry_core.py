"""
Core Service Registration for Dependency Injection Container

Handles registration of fundamental infrastructure services:
- Configuration
- Resource Management
- Event Bus
- Safety Layer
- State Management
- Task Processing
"""

import asyncio
import logging
from typing import Callable

from src.config import Config
from .event_bus import initialize_event_bus
from .safety_layer import SafetyLayer
from .database_state import DatabaseStateManager
from .background_scheduler import BackgroundScheduler
from .resource_manager import ResourceManager

logger = logging.getLogger(__name__)


async def register_core_services(container: 'DependencyContainer') -> None:
    """Register all core infrastructure services."""

    # Config - singleton (access to configuration)
    async def create_config():
        return container.config

    container._register_singleton("config", create_config)

    # Resource Manager - singleton (initialized first for cleanup tracking)
    async def create_resource_manager():
        return ResourceManager()

    container._register_singleton("resource_manager", create_resource_manager)

    # Event Bus - singleton (foundation for all services)
    async def create_event_bus():
        return await initialize_event_bus(container.config)

    container._register_singleton("event_bus", create_event_bus)

    # Safety Layer - singleton (critical for all operations)
    async def create_safety_layer():
        event_bus = await container.get("event_bus")
        safety_layer = SafetyLayer(container.config, event_bus)
        await safety_layer.initialize()
        return safety_layer

    container._register_singleton("safety_layer", create_safety_layer)

    # State Manager - singleton (Database-backed only)
    async def create_state_manager():
        from .database_state import DatabaseStateManager
        logger.info("Creating DatabaseStateManager instance...")
        manager = DatabaseStateManager(container.config)
        logger.info("DatabaseStateManager instance created, starting initialization...")
        await manager.initialize()
        logger.info("DatabaseStateManager initialized successfully")
        return manager

    container._register_singleton("state_manager", create_state_manager)

    # Configuration State - singleton (Database-backed configuration)
    async def create_configuration_state():
        from .database_state.configuration_state import ConfigurationState
        state_manager = await container.get("state_manager")
        config_state = ConfigurationState(state_manager.db)
        await config_state.initialize()
        return config_state

    container._register_singleton("configuration_state", create_configuration_state)

    # AI Planner
    async def create_ai_planner():
        from .ai_planner import AIPlanner
        state_manager = await container.get("state_manager")
        return AIPlanner(container.config, state_manager)

    container._register_singleton("ai_planner", create_ai_planner)

    # Task Service
    async def create_task_service():
        from ..stores.scheduler_task_store import SchedulerTaskStore
        from ..services.scheduler.task_service import SchedulerTaskService

        state_manager = await container.get("state_manager")
        task_store = SchedulerTaskStore(state_manager.db.connection)

        task_service = SchedulerTaskService(task_store)
        await task_service.initialize()
        return task_service

    # Execution Tracker Service
    async def create_execution_tracker():
        from src.core.execution_tracker import ExecutionTracker
        state_manager = await container.get("state_manager")
        execution_tracker = ExecutionTracker(state_manager.db.connection)
        await execution_tracker.initialize()
        return execution_tracker

    container._register_singleton("execution_tracker", create_execution_tracker)

    container._register_singleton("task_service", create_task_service)

    # Background Scheduler
    async def create_background_scheduler():
        task_service = await container.get("task_service")
        event_bus = await container.get("event_bus")
        state_manager = await container.get("state_manager")
        execution_tracker = await container.get("execution_tracker")
        return BackgroundScheduler(
            task_service,
            event_bus,
            state_manager.db._connection_pool,
            container.config,
            execution_tracker
        )

    container._register_singleton("background_scheduler", create_background_scheduler)

    # Fundamental Executor
    async def create_fundamental_executor():
        from src.core.background_scheduler.clients.perplexity_client import PerplexityClient
        from src.core.background_scheduler.executors.fundamental_executor import FundamentalExecutor
        from src.core.background_scheduler.stores.fundamental_store import FundamentalStore

        configuration_state = await container.get("configuration_state")
        execution_tracker = await container.get("execution_tracker")
        perplexity_client = PerplexityClient(configuration_state=configuration_state)
        state_manager = await container.get("state_manager")
        fundamental_store = FundamentalStore(state_manager.db.connection)
        event_bus = await container.get("event_bus")

        return FundamentalExecutor(
            perplexity_client,
            state_manager.db.connection,
            event_bus,
            execution_tracker
        )

    container._register_singleton("fundamental_executor", create_fundamental_executor)

    # Conversation Manager
    async def create_conversation_manager():
        from .conversation_manager import ConversationManager
        state_manager = await container.get("state_manager")
        return ConversationManager(container.config, state_manager, container)

    container._register_singleton("conversation_manager", create_conversation_manager)

    # Learning Engine
    async def create_learning_engine():
        from .learning_engine import LearningEngine
        state_manager = await container.get("state_manager")
        return LearningEngine(container.config, state_manager)

    container._register_singleton("learning_engine", create_learning_engine)
