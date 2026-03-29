"""
Paper Trading Services Registration for Dependency Injection Container

Handles registration of paper trading infrastructure:
- Paper trading stores and accounts
- Price monitoring and execution
- Performance calculation
"""

import logging
import aiosqlite
from pathlib import Path

logger = logging.getLogger(__name__)


async def register_paper_trading_services(container: 'DependencyContainer') -> None:
    """Register all paper trading services."""

    # Paper Trading Infrastructure
    async def create_paper_trading_store():
        from src.stores.paper_trading_store import PaperTradingStore
        db_path = container.config.state_dir / "robo_trader.db"
        connection = await aiosqlite.connect(str(db_path))
        store = PaperTradingStore(connection)
        await store.initialize()
        return store

    container._register_singleton("paper_trading_store", create_paper_trading_store)

    # Paper Trading Price Monitor
    async def create_paper_trading_price_monitor():
        from src.services.paper_trading.price_monitor import PaperTradingPriceMonitor
        event_bus = await container.get("event_bus")
        store = await container.get("paper_trading_store")
        broadcast_coordinator = await container.get("broadcast_coordinator")
        price_monitor = PaperTradingPriceMonitor(event_bus, store, broadcast_coordinator)
        await price_monitor.initialize()
        logger.info("PaperTradingPriceMonitor initialized - real-time WebSocket updates enabled")
        return price_monitor

    container._register_singleton("paper_trading_price_monitor", create_paper_trading_price_monitor)

    # Paper Trading Account Manager
    async def create_paper_trading_account_manager():
        from src.services.paper_trading.account_manager import PaperTradingAccountManager
        store = await container.get("paper_trading_store")
        market_data_service = await container.get("market_data_service")
        price_monitor = await container.get("paper_trading_price_monitor")
        manager = PaperTradingAccountManager(store, market_data_service, price_monitor)
        logger.info("PaperTradingAccountManager created with Zerodha MarketDataService and PriceMonitor")
        return manager

    container._register_singleton("paper_trading_account_manager", create_paper_trading_account_manager)

    # Paper Trade Executor
    async def create_paper_trade_executor():
        from src.services.paper_trading.trade_executor import PaperTradeExecutor
        store = await container.get("paper_trading_store")
        account_manager = await container.get("paper_trading_account_manager")
        market_data_service = await container.get("market_data_service")
        executor = PaperTradeExecutor(store, account_manager, market_data_service)
        logger.info("PaperTradeExecutor created with MarketDataService for Phase 3 real-time execution prices")
        return executor

    container._register_singleton("paper_trade_executor", create_paper_trade_executor)

    # Paper Trading Execution Service
    async def create_paper_trading_execution_service():
        from src.services.paper_trading_execution_service import PaperTradingExecutionService
        trade_executor = await container.get("paper_trade_executor")
        account_manager = await container.get("paper_trading_account_manager")
        store = await container.get("paper_trading_store")
        execution_service = PaperTradingExecutionService(
            trade_executor=trade_executor,
            account_manager=account_manager,
            store=store,
        )
        await execution_service.initialize()
        return execution_service

    container._register_singleton("paper_trading_execution_service", create_paper_trading_execution_service)

    async def create_agent_artifact_service():
        from src.services.claude_agent.agent_artifact_service import AgentArtifactService

        return AgentArtifactService(container)

    container._register_singleton("agent_artifact_service", create_agent_artifact_service)

    # Performance Calculator (paper trading metrics)
    async def create_performance_calculator():
        from src.services.paper_trading.performance_calculator import PerformanceCalculator
        return PerformanceCalculator()

    container._register_singleton("performance_calculator", create_performance_calculator)

    # Zerodha OAuth Service
    async def create_zerodha_oauth_service():
        from src.services.zerodha_oauth_service import ZerodhaOAuthService
        event_bus = await container.get("event_bus")
        oauth_service = ZerodhaOAuthService(container.config, event_bus)
        await oauth_service.initialize()
        logger.info("Zerodha OAuth Service initialized")
        return oauth_service

    container._register_singleton("zerodha_oauth_service", create_zerodha_oauth_service)

    # Real-Time Trading State
    async def create_real_time_trading_state():
        from src.core.database_state.real_time_trading_state import RealTimeTradingState
        state_manager = await container.get("state_manager")
        state = RealTimeTradingState(state_manager.db)
        await state.initialize()
        logger.info("RealTimeTradingState initialized with enhanced schema")
        return state

    container._register_singleton("real_time_trading_state", create_real_time_trading_state)

    # Token Storage Service
    async def create_token_storage_service():
        from src.services.token_storage_service import TokenStorageService
        encryption_key = container.config.encryption_key
        token_storage = TokenStorageService(encryption_key)
        logger.info("TokenStorageService initialized with encryption")
        return token_storage

    container._register_singleton("token_storage_service", create_token_storage_service)

    # Kite Portfolio Service
    async def create_kite_portfolio_service():
        from src.services.kite_portfolio_service import KitePortfolioService
        kite_config = container.config.kite_connect or {}

        if not kite_config.get("api_key"):
            logger.warning("Kite Connect API key not configured. Portfolio import will be disabled.")
            return None

        kite_service = KitePortfolioService(kite_config)
        await kite_service.initialize()
        logger.info("KitePortfolioService initialized for portfolio import")
        return kite_service

    container._register_singleton("kite_portfolio_service", create_kite_portfolio_service)

    # WebSocket Trading Manager
    async def create_websocket_trading_manager():
        from src.web.websocket_trading_manager import WebSocketTradingManager, get_websocket_trading_manager
        real_time_state = await container.get("real_time_trading_state")
        manager = await get_websocket_trading_manager(real_time_state)
        logger.info("WebSocketTradingManager initialized for real-time broadcasting")
        return manager

    container._register_singleton("websocket_trading_manager", create_websocket_trading_manager)

    # Research Ledger Store (structured feature extraction persistence)
    async def create_research_ledger_store():
        from src.stores.research_ledger_store import ResearchLedgerStore
        db_path = container.config.state_dir / "robo_trader.db"
        connection = await aiosqlite.connect(str(db_path))
        store = ResearchLedgerStore(connection)
        await store.initialize()
        logger.info("ResearchLedgerStore initialized")
        return store

    container._register_singleton("research_ledger_store", create_research_ledger_store)

    async def create_paper_trading_learning_store():
        from src.stores.paper_trading_learning_store import PaperTradingLearningStore

        paper_store = await container.get("paper_trading_store")
        store = PaperTradingLearningStore(paper_store.db_connection)
        await store.initialize()
        logger.info("PaperTradingLearningStore initialized")
        return store

    container._register_singleton("paper_trading_learning_store", create_paper_trading_learning_store)

    async def create_paper_trading_learning_service():
        from src.services.paper_trading_learning_service import PaperTradingLearningService

        learning_store = await container.get("paper_trading_learning_store")
        paper_store = await container.get("paper_trading_store")
        return PaperTradingLearningService(learning_store, paper_store)

    container._register_singleton("paper_trading_learning_service", create_paper_trading_learning_service)

    async def create_paper_trading_improvement_service():
        from src.services.paper_trading_improvement_service import PaperTradingImprovementService

        learning_service = await container.get("paper_trading_learning_service")
        learning_store = await container.get("paper_trading_learning_store")
        paper_store = await container.get("paper_trading_store")
        return PaperTradingImprovementService(learning_service, learning_store, paper_store)

    container._register_singleton("paper_trading_improvement_service", create_paper_trading_improvement_service)

    async def create_ai_market_research_service():
        from src.services.ai_market_research_service import AIMarketResearchService

        runtime_client = await container.get("codex_runtime_client")
        runtime_config = container.config.ai_runtime
        return AIMarketResearchService(
            runtime_client,
            default_model=runtime_config.codex_model,
            reasoning=runtime_config.codex_reasoning_light,
            timeout_seconds=float(runtime_config.timeout_seconds),
            discovery_timeout_seconds=max(float(runtime_config.timeout_seconds), 300.0),
        )

    container._register_singleton("ai_market_research_service", create_ai_market_research_service)
    container._register_singleton("claude_market_research_service", create_ai_market_research_service)

    # Feature Extractor (LLM-powered structured feature extraction)
    async def create_feature_extractor():
        from src.services.recommendation_engine.feature_extractor import FeatureExtractor
        runtime_client = await container.get("codex_runtime_client")
        runtime_config = container.config.ai_runtime
        extractor = FeatureExtractor(
            runtime_client=runtime_client,
            model=runtime_config.codex_model,
            reasoning=runtime_config.codex_reasoning_light,
            working_directory=str(container.config.project_dir),
        )
        await extractor.initialize()
        logger.info("FeatureExtractor initialized with Codex runtime")
        return extractor

    container._register_singleton("feature_extractor", create_feature_extractor)

    # Deterministic Scorer (auditable scoring from extracted features)
    async def create_deterministic_scorer():
        from src.services.recommendation_engine.deterministic_scorer import DeterministicScorer
        return DeterministicScorer()

    container._register_singleton("deterministic_scorer", create_deterministic_scorer)

    # Stock Discovery Service (PT-002: Autonomous Stock Discovery)
    async def create_stock_discovery_service():
        from src.services.paper_trading.stock_discovery import StockDiscoveryService

        # Get dependencies
        state_manager = await container.get("state_manager")
        event_bus = await container.get("event_bus")
        config = container.config
        market_research_service = await container.get("ai_market_research_service")
        feature_extractor = await container.get("feature_extractor")
        deterministic_scorer = await container.get("deterministic_scorer")
        learning_service = await container.get("paper_trading_learning_service")
        account_manager = await container.get("paper_trading_account_manager")

        # Create and initialize service
        discovery_service = StockDiscoveryService(
            state_manager=state_manager,
            market_research_service=market_research_service,
            event_bus=event_bus,
            config=config,
            feature_extractor=feature_extractor,
            deterministic_scorer=deterministic_scorer,
            learning_service=learning_service,
            account_manager=account_manager,
        )
        await discovery_service.initialize()

        logger.info("StockDiscoveryService initialized for autonomous stock discovery")
        return discovery_service

    container._register_singleton("stock_discovery_service", create_stock_discovery_service)
