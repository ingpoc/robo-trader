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

    # Database Connection - singleton (database connection wrapper for legacy code)
    async def create_database():
        from .database_wrapper import DatabaseWrapper
        state_manager = await container.get("state_manager")
        return DatabaseWrapper(state_manager.db)

    container._register_singleton("database", create_database)

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
        from ..models.scheduler import TaskType

        state_manager = await container.get("state_manager")
        task_store = SchedulerTaskStore(state_manager.db.connection)

        task_service = SchedulerTaskService(task_store)
        await task_service.initialize()

        # Register RECOMMENDATION_GENERATION handler
        async def handle_recommendation_generation(task):
            """Handle portfolio intelligence analysis tasks with batch processing."""
            analyzer = await container.get("portfolio_intelligence_analyzer")

            # Get symbols to analyze (if None, get all portfolio stocks)
            symbols_to_analyze = task.payload.get("symbols")

            # If no specific symbols provided, get all stocks and create batch tasks
            if symbols_to_analyze is None:
                # Get all portfolio stocks
                portfolio_state = await container.get("portfolio_state")
                all_symbols = list(portfolio_state.portfolio.holdings.keys())

                # Create batch tasks for 3 stocks at a time to prevent turn limit exhaustion
                batch_size = 3
                task_service = await container.get("task_service")
                from ..models.scheduler import QueueName, TaskType

                tasks_created = 0
                for i in range(0, len(all_symbols), batch_size):
                    batch_symbols = all_symbols[i:i + batch_size]
                    await task_service.create_task(
                        queue_name=QueueName.AI_ANALYSIS,
                        task_type=TaskType.RECOMMENDATION_GENERATION,
                        payload={
                            "agent_name": task.payload["agent_name"],
                            "symbols": batch_symbols,
                            "batch_id": i // batch_size,
                            "total_batches": (len(all_symbols) + batch_size - 1) // batch_size
                        },
                        priority=7
                    )
                    tasks_created += 1

                logger.info(f"Created {tasks_created} batch tasks for {len(all_symbols)} symbols")
                return {
                    "status": "batched",
                    "tasks_created": tasks_created,
                    "total_symbols": len(all_symbols),
                    "batch_size": batch_size
                }

            # Process specific symbols (should be 2-3 max per task)
            return await analyzer.analyze_portfolio_intelligence(
                agent_name=task.payload["agent_name"],
                symbols=symbols_to_analyze,
                batch_info={
                    "batch_id": task.payload.get("batch_id"),
                    "total_batches": task.payload.get("total_batches")
                }
            )

        task_service.register_handler(TaskType.RECOMMENDATION_GENERATION, handle_recommendation_generation)
        logger.info("Registered RECOMMENDATION_GENERATION task handler")

        # Register FUNDAMENTALS_UPDATE handler
        async def handle_fundamentals_update(task):
            """Handle fundamentals update tasks."""
            try:
                # Get the symbols to update from payload
                symbols = task.payload.get("symbols", [])
                if not symbols:
                    return {"status": "skipped", "reason": "no_symbols"}

                logger.info(f"Processing fundamentals update for {len(symbols)} symbols")

                # Placeholder for actual fundamentals update logic
                # This would typically call a fundamental data service
                return {
                    "status": "completed",
                    "symbols_processed": len(symbols),
                    "symbols": symbols
                }
            except Exception as e:
                logger.error(f"Error in fundamentals update handler: {e}")
                raise

        task_service.register_handler(TaskType.FUNDAMENTALS_UPDATE, handle_fundamentals_update)
        logger.info("Registered FUNDAMENTALS_UPDATE task handler")

        # Register SYNC_ACCOUNT_BALANCES handler
        async def handle_sync_account_balances(task):
            """Handle account balance synchronization."""
            try:
                logger.info("Processing account balance synchronization")

                # Get portfolio service to sync balances
                portfolio_service = await container.get("portfolio_service")

                # Sync account balances from broker
                result = await portfolio_service.sync_account_balances()

                logger.info(f"Account balance sync completed: {result}")
                return {
                    "status": "completed",
                    "result": result
                }
            except Exception as e:
                logger.error(f"Error in account balance sync handler: {e}")
                raise

        task_service.register_handler(TaskType.SYNC_ACCOUNT_BALANCES, handle_sync_account_balances)
        logger.info("Registered SYNC_ACCOUNT_BALANCES task handler")

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
        sequential_queue_manager = await container.get("sequential_queue_manager")
        return BackgroundScheduler(
            task_service,
            event_bus,
            state_manager.db._connection_pool,
            container.config,
            execution_tracker,
            sequential_queue_manager
        )

    container._register_singleton("background_scheduler", create_background_scheduler)

    # Sequential Queue Manager - singleton for task execution
    async def create_sequential_queue_manager():
        from ..services.scheduler.queue_manager import SequentialQueueManager
        task_service = await container.get("task_service")
        return SequentialQueueManager(task_service)

    container._register_singleton("sequential_queue_manager", create_sequential_queue_manager)

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

    # Prompt Optimization Service
    async def create_prompt_optimization_service():
        from ..services.prompt_optimization_service import PromptOptimizationService
        database = await container.get("database")
        return PromptOptimizationService(database, container)

    container._register_singleton("prompt_optimization_service", create_prompt_optimization_service)
