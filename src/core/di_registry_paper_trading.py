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
        execution_service = PaperTradingExecutionService()
        await execution_service.initialize()
        return execution_service

    container._register_singleton("paper_trading_execution_service", create_paper_trading_execution_service)

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
        db_path = container.config.state_dir / "robo_trader.db"
        state = RealTimeTradingState(str(db_path))
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

    # Kite Connect Service
    async def create_kite_connect_service():
        from src.services.kite_connect_service import KiteConnectService
        real_time_state = await container.get("real_time_trading_state")
        kite_config = container.config.kite_connect or {}
        kite_service = KiteConnectService(kite_config, real_time_state)
        logger.info("KiteConnectService initialized with real-time capabilities")
        return kite_service

    container._register_singleton("kite_connect_service", create_kite_connect_service)

    # WebSocket Trading Manager
    async def create_websocket_trading_manager():
        from src.web.websocket_trading_manager import WebSocketTradingManager, get_websocket_trading_manager
        real_time_state = await container.get("real_time_trading_state")
        manager = await get_websocket_trading_manager(real_time_state)
        logger.info("WebSocketTradingManager initialized for real-time broadcasting")
        return manager

    container._register_singleton("websocket_trading_manager", create_websocket_trading_manager)
