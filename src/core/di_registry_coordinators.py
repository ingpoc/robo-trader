"""
Coordinators Registration for Dependency Injection Container

Handles registration of all coordinator services:
- Session, Query, Task coordinators
- Status, Lifecycle, Broadcast coordinators
- Queue and Portfolio coordinators
- Claude Agent coordinator
- Orchestrator (main facade)
"""

import asyncio
import logging

from src.core.coordinators import (
    SessionCoordinator,
    QueryCoordinator,
    TaskCoordinator,
    StatusCoordinator,
    LifecycleCoordinator,
    BroadcastCoordinator,
    ClaudeAgentCoordinator,
)
from src.core.orchestrator import RoboTraderOrchestrator

logger = logging.getLogger(__name__)


async def register_coordinators(container: 'DependencyContainer') -> None:
    """Register all coordinators."""

    # Coordinators
    async def create_session_coordinator():
        session_coordinator = SessionCoordinator(container.config)
        broadcast_coordinator = await container.get("broadcast_coordinator")
        session_coordinator.set_broadcast_coordinator(broadcast_coordinator)
        return session_coordinator

    container._register_singleton("session_coordinator", create_session_coordinator)

    async def create_query_coordinator():
        session_coordinator = await container.get("session_coordinator")
        return QueryCoordinator(container.config, session_coordinator)

    container._register_singleton("query_coordinator", create_query_coordinator)

    async def create_task_coordinator():
        state_manager = await container.get("state_manager")
        event_bus = await container.get("event_bus")
        return TaskCoordinator(container.config, state_manager, event_bus)

    container._register_singleton("task_coordinator", create_task_coordinator)

    async def create_portfolio_coordinator():
        from src.core.coordinators.portfolio_coordinator import PortfolioCoordinator
        state_manager = await container.get("state_manager")
        return PortfolioCoordinator(container.config, state_manager)

    container._register_singleton("portfolio_coordinator", create_portfolio_coordinator)

    async def create_status_coordinator():
        state_manager = await container.get("state_manager")
        ai_planner = await container.get("ai_planner")
        background_scheduler = await container.get("background_scheduler")
        session_coordinator = await container.get("session_coordinator")
        broadcast_coordinator = await container.get("broadcast_coordinator")
        return StatusCoordinator(
            container.config,
            state_manager,
            ai_planner,
            background_scheduler,
            session_coordinator,
            broadcast_coordinator
        )

    container._register_singleton("status_coordinator", create_status_coordinator)

    async def create_lifecycle_coordinator():
        background_scheduler = await container.get("background_scheduler")
        return LifecycleCoordinator(container.config, background_scheduler)

    container._register_singleton("lifecycle_coordinator", create_lifecycle_coordinator)

    async def create_broadcast_coordinator():
        return BroadcastCoordinator(container.config)

    container._register_singleton("broadcast_coordinator", create_broadcast_coordinator)

    async def create_queue_coordinator():
        from src.core.coordinators.queue_coordinator import QueueCoordinator
        return QueueCoordinator(container.config, container)

    container._register_singleton("queue_coordinator", create_queue_coordinator)

    async def create_claude_agent_coordinator():
        event_bus = await container.get("event_bus")
        strategy_store = await container.get("claude_strategy_store")
        tool_executor = await container.get("tool_executor")
        response_validator = await container.get("response_validator")
        coordinator = ClaudeAgentCoordinator(container.config, event_bus, strategy_store, container)
        await coordinator.initialize()
        return coordinator

    container._register_singleton("claude_agent_coordinator", create_claude_agent_coordinator)


async def register_orchestrator(container: 'DependencyContainer') -> None:
    """Register orchestrator - created last due to dependencies."""

    async def create_orchestrator():
        logger.info("Creating orchestrator - getting coordinators...")
        session_coordinator = await container.get("session_coordinator")
        query_coordinator = await container.get("query_coordinator")
        task_coordinator = await container.get("task_coordinator")
        status_coordinator = await container.get("status_coordinator")
        lifecycle_coordinator = await container.get("lifecycle_coordinator")
        broadcast_coordinator = await container.get("broadcast_coordinator")

        logger.info("Creating orchestrator - getting legacy dependencies...")
        state_manager = await container.get("state_manager")
        ai_planner = await container.get("ai_planner")
        background_scheduler = await container.get("background_scheduler")
        conversation_manager = await container.get("conversation_manager")
        learning_engine = await container.get("learning_engine")

        logger.info("Creating orchestrator instance...")
        orchestrator = RoboTraderOrchestrator(container.config)

        orchestrator.session_coordinator = session_coordinator
        orchestrator.query_coordinator = query_coordinator
        orchestrator.task_coordinator = task_coordinator
        orchestrator.portfolio_coordinator = await container.get("portfolio_coordinator")
        orchestrator.status_coordinator = status_coordinator
        orchestrator.lifecycle_coordinator = lifecycle_coordinator
        orchestrator.broadcast_coordinator = broadcast_coordinator
        orchestrator.queue_coordinator = await container.get("queue_coordinator")

        orchestrator.state_manager = state_manager
        orchestrator.ai_planner = ai_planner
        orchestrator.background_scheduler = background_scheduler
        orchestrator.conversation_manager = conversation_manager
        orchestrator.learning_engine = learning_engine

        # Initialize all coordinators BEFORE initializing orchestrator
        logger.info("Initializing coordinators...")
        await asyncio.gather(
            session_coordinator.initialize(),
            query_coordinator.initialize(),
            task_coordinator.initialize(),
            status_coordinator.initialize(),
            lifecycle_coordinator.initialize(),
            broadcast_coordinator.initialize(),
        )

        # Initialize queue coordinator
        queue_coordinator = await container.get("queue_coordinator")
        await queue_coordinator.initialize()
        logger.info("All coordinators initialized successfully")

        # Now initialize the orchestrator (which depends on coordinators)
        logger.info("Initializing orchestrator...")
        await orchestrator.initialize()
        logger.info("Orchestrator initialized successfully")

        return orchestrator

    container._register_singleton("orchestrator", create_orchestrator)
