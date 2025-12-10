"""Tests for Morning Autonomous Trading Session (PT-003)."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.coordinators.paper_trading.morning_session_coordinator import (
    MorningSessionCoordinator,
    MorningSessionResult
)
from src.core.event_bus import EventBus
from src.core.di import DependencyContainer as DIContainer
from src.core.errors import TradingError


@pytest.fixture
async def mock_container():
    """Create a mock DI container with all required services."""
    container = MagicMock(spec=DIContainer)

    # Mock all required services
    container.get = AsyncMock()

    # Create mock service instances
    mock_execution_service = AsyncMock()
    mock_safeguards = AsyncMock()
    mock_decision_logger = AsyncMock()
    mock_kite_service = AsyncMock()
    mock_perplexity_service = AsyncMock()
    mock_stock_discovery = AsyncMock()
    mock_paper_trading_state = AsyncMock()
    mock_task_service = AsyncMock()

    # Configure container.get to return appropriate mocks
    service_mapping = {
        "paper_trading_execution": mock_execution_service,
        "autonomous_trading_safeguards": mock_safeguards,
        "decision_logger": mock_decision_logger,
        "kite_connect_service": mock_kite_service,
        "perplexity_service": mock_perplexity_service,
        "stock_discovery": mock_stock_discovery,
        "paper_trading_state": mock_paper_trading_state,
        "task_service": mock_task_service
    }

    async def get_service(service_name):
        if service_name in service_mapping:
            return service_mapping[service_name]
        raise ValueError(f"Unknown service: {service_name}")

    container.get.side_effect = get_service

    return container, {
        "execution": mock_execution_service,
        "safeguards": mock_safeguards,
        "logger": mock_decision_logger,
        "kite": mock_kite_service,
        "perplexity": mock_perplexity_service,
        "stock_discovery": mock_stock_discovery,
        "paper_trading_state": mock_paper_trading_state,
        "task_service": mock_task_service
    }


@pytest.fixture
async def coordinator(mock_container):
    """Create a MorningSessionCoordinator instance with mocked dependencies."""
    container, services = mock_container
    from src.config import Config
    config = Config()
    event_bus = EventBus(config)

    config = {"session": {"timeout": 180}}
    coordinator = MorningSessionCoordinator(config, event_bus, container)

    # Mock the initialized services
    coordinator.execution_service = services["execution"]
    coordinator.safeguards = services["safeguards"]
    coordinator.decision_logger = services["logger"]
    coordinator.kite_service = services["kite"]
    coordinator.perplexity_service = services["perplexity"]
    coordinator.stock_discovery = services["stock_discovery"]

    coordinator._initialized = True

    return coordinator, services


class TestMorningSessionCoordinator:
    """Test cases for MorningSessionCoordinator."""

    @pytest.mark.asyncio
    async def test_initialize_success(self, mock_container):
        """Test successful initialization of coordinator."""
        container, services = mock_container
        from src.config import Config
    config = Config()
    event_bus = EventBus(config)
        config = {"session": {}}

        coordinator = MorningSessionCoordinator(config, event_bus, container)

        # Initialize coordinator
        await coordinator.initialize()

        # Verify services were set
        assert coordinator.execution_service == services["execution"]
        assert coordinator.safeguards == services["safeguards"]
        assert coordinator.decision_logger == services["logger"]
        assert coordinator.kite_service == services["kite"]
        assert coordinator.perplexity_service == services["perplexity"]
        assert coordinator.stock_discovery == services["stock_discovery"]
        assert coordinator._initialized is True

    @pytest.mark.asyncio
    async def test_run_morning_session_success(self, coordinator):
        """Test successful morning session execution."""
        coordinator, services = coordinator

        # Mock pre-market scan results
        pre_market_stocks = [
            {"symbol": "AAPL", "price": 150.0, "change": 2.5, "volume": 10000},
            {"symbol": "GOOGL", "price": 2500.0, "change": -1.0, "volume": 5000},
            {"symbol": "MSFT", "price": 300.0, "change": 0.5, "volume": 8000}
        ]
        services["stock_discovery"].get_watchlist.return_value = pre_market_stocks
        services["kite_service"].get_pre_market_data.return_value = {
            "last_price": 150.0,
            "change": 2.5,
            "volume": 10000
        }

        # Mock research results
        services["perplexity_service"].research_stock.return_value = {
            "sentiment": "positive",
            "analysis": "Strong technical indicators",
            "recommendation": "BUY"
        }

        # Mock AI analysis task
        task_id = "task_123"
        services["task_service"].create_task.return_value = task_id
        services["task_service"].get_task.return_value = {
            "status": "completed",
            "result": {
                "trade_ideas": [
                    {
                        "symbol": "AAPL",
                        "action": "BUY",
                        "quantity": 10,
                        "price": 150.0,
                        "confidence": 0.8,
                        "rationale": "Strong momentum"
                    }
                ]
            }
        }

        # Mock safeguards approval
        services["safeguards"].can_execute_trade.return_value = True
        services["safeguards"].get_remaining_daily_trades.return_value = 4

        # Mock trade execution
        services["execution"].execute_buy_trade.return_value = {
            "success": True,
            "trade_id": "trade_123",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 10,
            "price": 150.0,
            "status": "COMPLETED",
            "amount": 1500.0
        }

        # Mock paper trading state
        services["paper_trading_state"].store_morning_session.return_value = True

        # Run morning session
        result = await coordinator.run_morning_session(trigger="test")

        # Verify results
        assert isinstance(result, MorningSessionResult)
        assert result.success is True
        assert result.pre_market_scanned == 3
        assert result.stocks_researched == 3
        assert result.trade_ideas_generated == 1
        assert result.trades_executed == 1
        assert result.total_amount_invested == 1500.0
        assert result.decisions_logged > 0
        assert result.error_message is None

        # Verify service calls
        services["stock_discovery"].get_watchlist.assert_called_once_with(limit=20)
        services["perplexity_service"].research_stock.assert_called()
        services["task_service"].create_task.assert_called_once()
        services["safeguards"].can_execute_trade.assert_called()
        services["execution"].execute_buy_trade.assert_called_once()
        services["paper_trading_state"].store_morning_session.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_morning_session_no_stocks(self, coordinator):
        """Test morning session with no stocks to scan."""
        coordinator, services = coordinator

        # Mock empty watchlist
        services["stock_discovery"].get_watchlist.return_value = []

        # Mock paper trading state
        services["paper_trading_state"].store_morning_session.return_value = True

        # Run morning session
        result = await coordinator.run_morning_session(trigger="test")

        # Verify results
        assert result.success is True
        assert result.pre_market_scanned == 0
        assert result.stocks_researched == 0
        assert result.trade_ideas_generated == 0
        assert result.trades_executed == 0
        assert result.total_amount_invested == 0.0

    @pytest.mark.asyncio
    async def test_run_morning_session_safeguard_rejection(self, coordinator):
        """Test morning session with trades rejected by safeguards."""
        coordinator, services = coordinator

        # Mock pre-market scan
        services["stock_discovery"].get_watchlist.return_value = [
            {"symbol": "AAPL", "price": 150.0, "change": 2.5, "volume": 10000}
        ]
        services["kite_service"].get_pre_market_data.return_value = {
            "last_price": 150.0,
            "change": 2.5,
            "volume": 10000
        }

        # Mock research
        services["perplexity_service"].research_stock.return_value = {
            "sentiment": "positive",
            "analysis": "Strong technical indicators"
        }

        # Mock AI analysis with trade idea
        task_id = "task_123"
        services["task_service"].create_task.return_value = task_id
        services["task_service"].get_task.return_value = {
            "status": "completed",
            "result": {
                "trade_ideas": [
                    {
                        "symbol": "AAPL",
                        "action": "BUY",
                        "quantity": 10,
                        "price": 150.0,
                        "confidence": 0.8
                    }
                ]
            }
        }

        # Mock safeguard rejection
        services["safeguards"].can_execute_trade.return_value = False

        # Mock paper trading state
        services["paper_trading_state"].store_morning_session.return_value = True

        # Run morning session
        result = await coordinator.run_morning_session(trigger="test")

        # Verify results
        assert result.success is True
        assert result.trade_ideas_generated == 1
        assert result.trades_executed == 0
        assert result.total_amount_invested == 0.0

        # Verify safeguard rejection was logged
        services["logger"].log_decision.assert_called_with(
            decision_type="SAFEGUARD_REJECT",
            symbol="AAPL",
            reasoning="Trade rejected by safeguards",
            confidence=1.0,
            context={"trade_idea": {"symbol": "AAPL", "action": "BUY", "quantity": 10, "price": 150.0, "confidence": 0.8}}
        )

    @pytest.mark.asyncio
    async def test_run_morning_session_already_active(self, coordinator):
        """Test error when session is already active."""
        coordinator, services = coordinator

        # Set session as active
        coordinator._session_active = True

        # Try to run session
        with pytest.raises(TradingError) as exc_info:
            await coordinator.run_morning_session()

        assert "Morning session already in progress" in str(exc_info.value)
        assert exc_info.value.context.category.value == "system"
        assert exc_info.value.context.severity.value == "medium"

    @pytest.mark.asyncio
    async def test_run_morning_session_not_initialized(self, mock_container):
        """Test error when coordinator is not initialized."""
        container, services = mock_container
        from src.config import Config
    config = Config()
    event_bus = EventBus(config)
        config = {"session": {}}

        coordinator = MorningSessionCoordinator(config, event_bus, container)
        # Don't initialize

        # Try to run session
        with pytest.raises(TradingError) as exc_info:
            await coordinator.run_morning_session()

        assert "MorningSessionCoordinator not initialized" in str(exc_info.value)
        assert exc_info.value.context.category.value == "system"
        assert exc_info.value.context.severity.value == "critical"

    @pytest.mark.asyncio
    async def test_run_morning_session_execution_failure(self, coordinator):
        """Test handling of trade execution failure."""
        coordinator, services = coordinator

        # Mock pre-market scan
        services["stock_discovery"].get_watchlist.return_value = [
            {"symbol": "AAPL", "price": 150.0, "change": 2.5, "volume": 10000}
        ]
        services["kite_service"].get_pre_market_data.return_value = {
            "last_price": 150.0,
            "change": 2.5,
            "volume": 10000
        }

        # Mock research
        services["perplexity_service"].research_stock.return_value = {
            "sentiment": "positive",
            "analysis": "Strong technical indicators"
        }

        # Mock AI analysis
        task_id = "task_123"
        services["task_service"].create_task.return_value = task_id
        services["task_service"].get_task.return_value = {
            "status": "completed",
            "result": {
                "trade_ideas": [
                    {
                        "symbol": "AAPL",
                        "action": "BUY",
                        "quantity": 10,
                        "price": 150.0,
                        "confidence": 0.8
                    }
                ]
            }
        }

        # Mock safeguard approval
        services["safeguards"].can_execute_trade.return_value = True

        # Mock execution failure
        services["execution"].execute_buy_trade.side_effect = TradingError(
            "Insufficient balance",
            category="trading",
            severity="high"
        )

        # Mock paper trading state
        services["paper_trading_state"].store_morning_session.return_value = True

        # Run morning session
        result = await coordinator.run_morning_session(trigger="test")

        # Verify results - session should still succeed despite execution failure
        assert result.success is True
        assert result.trade_ideas_generated == 1
        assert result.trades_executed == 0  # No trades executed due to failure

        # Verify failure was logged
        services["logger"].log_decision.assert_called_with(
            decision_type="EXECUTION_FAILED",
            symbol="AAPL",
            reasoning="Execution failed: Insufficient balance",
            confidence=1.0,
            context={"trade_idea": {"symbol": "AAPL", "action": "BUY", "quantity": 10, "price": 150.0, "confidence": 0.8}}
        )

    @pytest.mark.asyncio
    async def test_cleanup(self, coordinator):
        """Test coordinator cleanup."""
        coordinator, services = coordinator

        # Set session as active
        coordinator._session_active = True

        # Cleanup
        await coordinator.cleanup()

        # Verify session flag is reset
        assert coordinator._session_active is False

    @pytest.mark.asyncio
    async def test_handle_market_open_event(self, coordinator):
        """Test handling of market open event."""
        coordinator, services = coordinator

        # Mock event
        event = MagicMock()
        event.type = "MARKET_OPEN"

        # Mock coordinator methods
        coordinator.run_morning_session = AsyncMock()

        # Handle event
        await coordinator.handle_event(event)

        # Verify session was triggered
        coordinator.run_morning_session.assert_called_once_with(trigger="market_open")

    @pytest.mark.asyncio
    async def test_handle_other_event(self, coordinator):
        """Test handling of non-market-open events."""
        coordinator, services = coordinator

        # Mock event
        event = MagicMock()
        event.type = "OTHER_EVENT"

        # Mock coordinator methods
        coordinator.run_morning_session = AsyncMock()

        # Handle event
        await coordinator.handle_event(event)

        # Verify session was NOT triggered
        coordinator.run_morning_session.assert_not_called()