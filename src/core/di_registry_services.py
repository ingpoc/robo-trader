"""
Domain Services Registration for Dependency Injection Container

Handles registration of business logic services:
- Portfolio, Risk, Execution services
- Analytics, Learning, Strategy services
- Market Data, Paper Trading services
- Event routing and feature management
"""

import logging
from src.services.portfolio_service import PortfolioService
from src.services.risk_service import RiskService
from src.services.execution_service import ExecutionService
from src.services.analytics_service import AnalyticsService
from src.services.learning_service import LearningService
from src.services.strategy_evolution_engine import StrategyEvolutionEngine
from src.services.market_data_service import MarketDataService
from src.services.feature_management.service import FeatureManagementService
from src.services.event_router_service import EventRouterService

logger = logging.getLogger(__name__)


async def register_domain_services(container: 'DependencyContainer') -> None:
    """Register all domain-specific services."""

    # Portfolio Service
    async def create_portfolio_service():
        event_bus = await container.get("event_bus")
        portfolio_service = PortfolioService(container.config, event_bus)
        await portfolio_service.initialize()
        return portfolio_service

    container._register_singleton("portfolio_service", create_portfolio_service)

    # Risk Service
    async def create_risk_service():
        event_bus = await container.get("event_bus")
        risk_service = RiskService(container.config, event_bus)
        await risk_service.initialize()
        return risk_service

    container._register_singleton("risk_service", create_risk_service)

    # Execution Service
    async def create_execution_service():
        event_bus = await container.get("event_bus")
        execution_service = ExecutionService(container.config, event_bus)
        await execution_service.initialize()
        return execution_service

    container._register_singleton("execution_service", create_execution_service)

    # Analytics Service
    async def create_analytics_service():
        event_bus = await container.get("event_bus")
        analytics_service = AnalyticsService(container.config, event_bus)
        await analytics_service.initialize()
        return analytics_service

    container._register_singleton("analytics_service", create_analytics_service)

    # Market Data Service (real-time price tracking)
    async def create_market_data_service():
        event_bus = await container.get("event_bus")
        market_data_service = MarketDataService(container.config, event_bus, broker=None)
        await market_data_service.initialize()
        return market_data_service

    container._register_singleton("market_data_service", create_market_data_service)

    # Learning Service
    async def create_learning_service():
        event_bus = await container.get("event_bus")
        learning_service = LearningService(container.config, event_bus)
        await learning_service.initialize()
        return learning_service

    container._register_singleton("learning_service", create_learning_service)

    # Strategy Evolution Engine
    async def create_strategy_evolution_engine():
        event_bus = await container.get("event_bus")
        engine = StrategyEvolutionEngine(container.config, event_bus)
        await engine.initialize()
        return engine

    container._register_singleton("strategy_evolution_engine", create_strategy_evolution_engine)

    # Feature Management Service
    async def create_feature_management_service():
        event_bus = await container.get("event_bus")
        feature_service = FeatureManagementService(container.config, event_bus)
        await feature_service.initialize()

        background_scheduler = await container.get("background_scheduler")
        feature_service.set_background_scheduler(background_scheduler)

        if hasattr(container, '_singletons') and "claude_agent_coordinator" in container._singletons:
            agent_coordinator = await container.get("claude_agent_coordinator")
            feature_service.set_agent_coordinator(agent_coordinator)

        return feature_service

    container._register_singleton("feature_management_service", create_feature_management_service)

    # Event Router Service
    async def create_event_router_service():
        event_router_service = EventRouterService(container)
        await event_router_service.initialize()
        return event_router_service

    container._register_singleton("event_router_service", create_event_router_service)
