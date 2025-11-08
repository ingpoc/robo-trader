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

            # Get symbols to analyze (if None, get stocks with oldest analysis)
            symbols_to_analyze = task.payload.get("symbols")

            # If no specific symbols provided, select 2-3 stocks with oldest analysis
            if symbols_to_analyze is None:
                # Get stocks with oldest analysis (priority: no analysis > oldest analysis)
                from ..services.portfolio_intelligence_analyzer import PortfolioIntelligenceAnalyzer
                symbols_to_analyze = await analyzer._get_stocks_with_updates()

                # Select only 2-3 stocks with oldest/first analysis
                # This prevents processing all 81 stocks at once
                symbols_to_analyze = symbols_to_analyze[:3]

                logger.info(f"Selected {len(symbols_to_analyze)} stocks for analysis: {symbols_to_analyze}")

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

        # Register CLAUDE_MORNING_PREP handler
        async def handle_claude_morning_prep(task):
            """Handle morning market preparation with AI analysis."""
            try:
                logger.info("Processing Claude morning prep routine")

                symbols = task.payload.get("symbols", [])
                if not symbols:
                    logger.warning("No symbols provided for morning prep")
                    return {"status": "skipped", "reason": "no_symbols"}

                # Get portfolio intelligence analyzer
                analyzer = await container.get("portfolio_intelligence_analyzer")

                # Run morning analysis on portfolio symbols (batched)
                # Process in smaller batches to avoid turn limit exhaustion
                batch_size = 3
                results = []

                for i in range(0, len(symbols), batch_size):
                    batch_symbols = symbols[i:i + batch_size]
                    logger.info(f"Morning prep batch {i//batch_size + 1}: analyzing {len(batch_symbols)} symbols")

                    result = await analyzer.analyze_portfolio_intelligence(
                        agent_name="morning_prep",
                        symbols=batch_symbols,
                        batch_info={
                            "batch_id": i // batch_size,
                            "total_batches": (len(symbols) + batch_size - 1) // batch_size,
                            "routine": "morning_prep"
                        }
                    )
                    results.append(result)

                logger.info(f"Morning prep completed: processed {len(symbols)} symbols in {len(results)} batches")
                return {
                    "status": "completed",
                    "symbols_processed": len(symbols),
                    "batches": len(results)
                }
            except Exception as e:
                logger.error(f"Error in morning prep handler: {e}")
                raise

        task_service.register_handler(TaskType.CLAUDE_MORNING_PREP, handle_claude_morning_prep)
        logger.info("Registered CLAUDE_MORNING_PREP task handler")

        # Register CLAUDE_EVENING_REVIEW handler
        async def handle_claude_evening_review(task):
            """Handle evening market close review with AI analysis."""
            try:
                logger.info("Processing Claude evening review routine")

                # Get portfolio intelligence analyzer
                analyzer = await container.get("portfolio_intelligence_analyzer")

                # Run evening review on all positions
                result = await analyzer.analyze_portfolio_intelligence(
                    agent_name="evening_review",
                    symbols=None,  # Will analyze all positions
                    batch_info={"routine": "evening_review"}
                )

                logger.info(f"Evening review completed")
                return {
                    "status": "completed",
                    "analysis": result
                }
            except Exception as e:
                logger.error(f"Error in evening review handler: {e}")
                raise

        task_service.register_handler(TaskType.CLAUDE_EVENING_REVIEW, handle_claude_evening_review)
        logger.info("Registered CLAUDE_EVENING_REVIEW task handler")

        # Register CLAUDE_NEWS_ANALYSIS handler
        async def handle_claude_news_analysis(task):
            """Handle AI-powered news analysis for a specific symbol."""
            try:
                symbol = task.payload.get("symbol")
                if not symbol:
                    return {"status": "skipped", "reason": "no_symbol"}

                logger.info(f"Processing Claude news analysis for {symbol}")

                # Get portfolio intelligence analyzer
                analyzer = await container.get("portfolio_intelligence_analyzer")

                # Analyze news impact for the symbol
                result = await analyzer.analyze_portfolio_intelligence(
                    agent_name="news_analysis",
                    symbols=[symbol],
                    batch_info={
                        "trigger": "news",
                        "trigger_type": task.payload.get("trigger")
                    }
                )

                logger.info(f"News analysis completed for {symbol}")
                return {
                    "status": "completed",
                    "symbol": symbol,
                    "analysis": result
                }
            except Exception as e:
                logger.error(f"Error in news analysis handler for {task.payload.get('symbol')}: {e}")
                raise

        task_service.register_handler(TaskType.CLAUDE_NEWS_ANALYSIS, handle_claude_news_analysis)
        logger.info("Registered CLAUDE_NEWS_ANALYSIS task handler")

        # Register CLAUDE_EARNINGS_REVIEW handler
        async def handle_claude_earnings_review(task):
            """Handle AI-powered earnings review for a specific symbol."""
            try:
                symbol = task.payload.get("symbol")
                if not symbol:
                    return {"status": "skipped", "reason": "no_symbol"}

                logger.info(f"Processing Claude earnings review for {symbol}")

                # Get portfolio intelligence analyzer
                analyzer = await container.get("portfolio_intelligence_analyzer")

                # Analyze earnings data for the symbol
                result = await analyzer.analyze_portfolio_intelligence(
                    agent_name="earnings_review",
                    symbols=[symbol],
                    batch_info={
                        "trigger": "earnings",
                        "trigger_type": task.payload.get("trigger")
                    }
                )

                logger.info(f"Earnings review completed for {symbol}")
                return {
                    "status": "completed",
                    "symbol": symbol,
                    "analysis": result
                }
            except Exception as e:
                logger.error(f"Error in earnings review handler for {task.payload.get('symbol')}: {e}")
                raise

        task_service.register_handler(TaskType.CLAUDE_EARNINGS_REVIEW, handle_claude_earnings_review)
        logger.info("Registered CLAUDE_EARNINGS_REVIEW task handler")

        # Register CLAUDE_FUNDAMENTAL_ANALYSIS handler
        async def handle_claude_fundamental_analysis(task):
            """Handle AI-powered fundamental analysis for a specific symbol."""
            try:
                symbol = task.payload.get("symbol")
                if not symbol:
                    return {"status": "skipped", "reason": "no_symbol"}

                logger.info(f"Processing Claude fundamental analysis for {symbol}")

                # Get portfolio intelligence analyzer
                analyzer = await container.get("portfolio_intelligence_analyzer")

                # Analyze fundamentals for the symbol
                result = await analyzer.analyze_portfolio_intelligence(
                    agent_name="fundamental_analysis",
                    symbols=[symbol],
                    batch_info={
                        "trigger": "fundamentals",
                        "trigger_type": task.payload.get("trigger")
                    }
                )

                logger.info(f"Fundamental analysis completed for {symbol}")
                return {
                    "status": "completed",
                    "symbol": symbol,
                    "analysis": result
                }
            except Exception as e:
                logger.error(f"Error in fundamental analysis handler for {task.payload.get('symbol')}: {e}")
                raise

        task_service.register_handler(TaskType.CLAUDE_FUNDAMENTAL_ANALYSIS, handle_claude_fundamental_analysis)
        logger.info("Registered CLAUDE_FUNDAMENTAL_ANALYSIS task handler")

        # Register VALIDATE_PORTFOLIO_RISKS handler
        async def handle_validate_portfolio_risks(task):
            """Handle portfolio risk validation."""
            try:
                logger.info("Processing portfolio risk validation")

                # Get portfolio service for risk calculations
                portfolio_service = await container.get("portfolio_service")

                # Validate current portfolio risk levels
                risk_assessment = await portfolio_service.validate_portfolio_risks()

                logger.info(f"Portfolio risk validation completed: {risk_assessment}")
                return {
                    "status": "completed",
                    "risk_assessment": risk_assessment
                }
            except Exception as e:
                logger.error(f"Error in portfolio risk validation handler: {e}")
                raise

        task_service.register_handler(TaskType.VALIDATE_PORTFOLIO_RISKS, handle_validate_portfolio_risks)
        logger.info("Registered VALIDATE_PORTFOLIO_RISKS task handler")

        # Register NEWS_MONITORING handler (CRITICAL FIX)
        async def handle_news_monitoring(task):
            """Handle news monitoring tasks for multiple symbols."""
            try:
                # Get the symbols to monitor from payload
                symbols = task.payload.get("symbols", [])
                if not symbols:
                    return {"status": "skipped", "reason": "no_symbols"}

                logger.info(f"Processing news monitoring for {len(symbols)} symbols: {symbols}")

                # Get fundamental executor for news processing
                from ..core.background_scheduler.executors.fundamental_executor import FundamentalExecutor
                fundamental_executor = await container.get("fundamental_executor")

                # Process news for each symbol
                results = await fundamental_executor.execute_market_news_analysis(symbols, {"source": "news_monitoring_task"})

                logger.info(f"News monitoring completed for {len(symbols)} symbols")
                return {
                    "status": "completed",
                    "symbols_processed": len(symbols),
                    "results": results
                }
            except Exception as e:
                logger.error(f"Error in news monitoring handler: {e}")
                raise

        task_service.register_handler(TaskType.NEWS_MONITORING, handle_news_monitoring)
        logger.info("Registered NEWS_MONITORING task handler")

        # Register EARNINGS_CHECK handler (MISSING)
        async def handle_earnings_check(task):
            """Handle earnings check tasks for multiple symbols."""
            try:
                # Get the symbols to check from payload
                symbols = task.payload.get("symbols", [])
                if not symbols:
                    return {"status": "skipped", "reason": "no_symbols"}

                logger.info(f"Processing earnings check for {len(symbols)} symbols: {symbols}")

                # Get fundamental executor for earnings processing
                from ..core.background_scheduler.executors.fundamental_executor import FundamentalExecutor
                fundamental_executor = await container.get("fundamental_executor")

                # Check earnings data for each symbol
                results = await fundamental_executor.execute_earnings_fundamentals(symbols, {"source": "earnings_check_task"})

                logger.info(f"Earnings check completed for {len(symbols)} symbols")
                return {
                    "status": "completed",
                    "symbols_processed": len(symbols),
                    "results": results
                }
            except Exception as e:
                logger.error(f"Error in earnings check handler: {e}")
                raise

        task_service.register_handler(TaskType.EARNINGS_CHECK, handle_earnings_check)
        logger.info("Registered EARNINGS_CHECK task handler")

        # Register EARNINGS_SCHEDULER handler (MISSING)
        async def handle_earnings_scheduler(task):
            """Handle earnings scheduler tasks for upcoming earnings."""
            try:
                logger.info("Processing earnings scheduler task")

                # Get fundamental executor for earnings scheduling
                from ..core.background_scheduler.executors.fundamental_executor import FundamentalExecutor
                fundamental_executor = await container.get("fundamental_executor")

                # Schedule earnings monitoring for portfolio symbols
                # Get all portfolio symbols for earnings monitoring
                from ..services.portfolio_service import PortfolioService
                portfolio_service = await container.get("portfolio_service")
                portfolio = await portfolio_service.get_portfolio()

                if portfolio and hasattr(portfolio, 'holdings'):
                    symbols = list(portfolio.holdings.keys())[:10]  # Limit to top 10 for scheduler
                    results = await fundamental_executor.execute_earnings_fundamentals(symbols, {"source": "earnings_scheduler_task"})
                else:
                    results = {"message": "No portfolio available for earnings scheduling"}

                logger.info(f"Earnings scheduler completed: {results}")
                return {
                    "status": "completed",
                    "results": results
                }
            except Exception as e:
                logger.error(f"Error in earnings scheduler handler: {e}")
                raise

        task_service.register_handler(TaskType.EARNINGS_SCHEDULER, handle_earnings_scheduler)
        logger.info("Registered EARNINGS_SCHEDULER task handler")

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
