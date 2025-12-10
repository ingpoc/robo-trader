"""
Tests for Evening Performance Review (PT-004)

Tests the evening session coordinator functionality including:
- Daily performance calculation
- Trading insights generation
- Strategy performance analysis
- Watchlist preparation
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from src.core.coordinators.paper_trading.evening_session_coordinator import EveningSessionCoordinator
from src.core.event_bus import EventBus, Event, EventType
from src.core.di import DependencyContainer
from src.config import Config
from src.services.perplexity_service import PerplexityService
from src.services.kite_connect_service import KiteConnectService
from src.services.autonomous_trading_safeguards import AutonomousTradingSafeguards
from src.core.database_state.paper_trading_state import PaperTradingState
from src.core.database_state.real_time_trading_state import RealTimeTradingState


@pytest.fixture
def config():
    """Create a test configuration."""
    return Config(
        KITE_API_KEY="test_key",
        KITE_API_SECRET="test_secret",
        KITE_ACCESS_TOKEN="test_token",
        PERPLEXITY_API_KEY="test_perplexity_key",
        STATE_DIR="/tmp/test_state"
    )


@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def container(config, event_bus):
    """Create a dependency container with mocked services."""
    container = DependencyContainer()
    container.config = config

    # Mock services
    container._services = {
        "perplexity_service": AsyncMock(spec=PerplexityService),
        "kite_connect_service": AsyncMock(spec=KiteConnectService),
        "autonomous_trading_safeguards": AsyncMock(spec=AutonomousTradingSafeguards),
        "state_manager": AsyncMock(),
    }

    # Mock state managers
    state_manager = Mock()
    state_manager.paper_trading = AsyncMock(spec=PaperTradingState)
    state_manager.real_time_trading = AsyncMock(spec=RealTimeTradingState)
    container._services["state_manager"] = state_manager

    # Event bus
    container._services["event_bus"] = event_bus

    return container


@pytest.fixture
async def evening_coordinator(config, event_bus, container):
    """Create an evening session coordinator for testing."""
    coordinator = EveningSessionCoordinator(config, event_bus, container)
    await coordinator.initialize()
    return coordinator


@pytest.mark.asyncio
async def test_evening_coordinator_initialization(evening_coordinator):
    """Test that evening session coordinator initializes correctly."""
    assert evening_coordinator._initialized
    assert evening_coordinator.perplexity is not None
    assert evening_coordinator.kite_service is not None
    assert evening_coordinator.safeguards is not None


@pytest.mark.asyncio
async def test_run_evening_review_success(evening_coordinator, container):
    """Test successful execution of evening review."""
    # Setup mock data
    review_date = "2025-01-15"

    # Mock performance metrics
    performance_metrics = {
        "trades_reviewed": [
            {
                "id": "trade_1",
                "symbol": "RELIANCE",
                "side": "BUY",
                "quantity": 100,
                "entry_price": 2500,
                "exit_price": 2550,
                "strategy_tag": "momentum",
                "status": "CLOSED"
            }
        ],
        "daily_pnl": 5000.0,
        "daily_pnl_percent": 0.5,
        "open_positions_count": 2,
        "closed_positions_count": 3,
        "win_rate": 66.7,
        "strategy_performance": {
            "momentum": {
                "trades": 2,
                "winning_trades": 2,
                "total_pnl": 8000.0,
                "win_rate": 100.0
            }
        }
    }

    # Setup state manager mocks
    state_manager = await container.get("state_manager")
    state_manager.paper_trading.calculate_daily_performance_metrics.return_value = performance_metrics
    state_manager.paper_trading.get_open_trades.return_value = []
    state_manager.paper_trading.store_evening_performance_review.return_value = True
    state_manager.news_earnings_state.get_recent_news.return_value = None
    state_manager.paper_trading.get_discovery_watchlist.return_value = []

    # Mock Perplexity response
    perplexity_response = {
        "content": """
        1. Strong momentum strategy performance with 100% win rate
        2. Consider position size optimization
        3. Market conditions favorable for trend following
        4. Risk management effective - no large losses
        5. Continue momentum focus tomorrow
        """
    }
    evening_coordinator.perplexity.query_perplexity.return_value = perplexity_response

    # Run the evening review
    result = await evening_coordinator.run_evening_review(
        trigger_source="MANUAL",
        review_date=review_date
    )

    # Verify results
    assert result["success"] is True
    assert result["review_date"] == review_date
    assert result["daily_pnl"] == 5000.0
    assert result["win_rate"] == 66.7
    assert len(result["trading_insights"]) > 0
    assert "momentum" in result["strategy_performance"]

    # Verify state was stored
    state_manager.paper_trading.store_evening_performance_review.assert_called_once()

    # Verify event was published
    assert event_bus.events_published


@pytest.mark.asyncio
async def test_run_evening_review_with_no_trades(evening_coordinator, container):
    """Test evening review when no trades were executed."""
    review_date = "2025-01-15"

    # Mock empty performance metrics
    performance_metrics = {
        "trades_reviewed": [],
        "daily_pnl": 0.0,
        "daily_pnl_percent": 0.0,
        "open_positions_count": 0,
        "closed_positions_count": 0,
        "win_rate": 0.0,
        "strategy_performance": {}
    }

    # Setup state manager mocks
    state_manager = await container.get("state_manager")
    state_manager.paper_trading.calculate_daily_performance_metrics.return_value = performance_metrics
    state_manager.paper_trading.get_open_trades.return_value = []
    state_manager.paper_trading.store_evening_performance_review.return_value = True

    # Mock Perplexity to return simple response
    evening_coordinator.perplexity.query_perplexity.return_value = {
        "content": "No trading activity today"
    }

    # Run the evening review
    result = await evening_coordinator.run_evening_review(review_date=review_date)

    # Verify results
    assert result["success"] is True
    assert result["review_date"] == review_date
    assert result["daily_pnl"] == 0.0
    assert result["trades_reviewed"] == []


@pytest.mark.asyncio
async def test_generate_trading_insights(evening_coordinator):
    """Test trading insights generation."""
    performance_metrics = {
        "daily_pnl": 10000.0,
        "daily_pnl_percent": 1.0,
        "win_rate": 75.0,
        "trades_reviewed": [{"symbol": "TCS"}],
        "strategy_performance": {
            "momentum": {"trades": 2, "total_pnl": 8000.0}
        }
    }

    # Mock Perplexity response
    evening_coordinator.perplexity.query_perplexity.return_value = {
        "content": """
        1. Excellent win rate of 75% indicates strong strategy
        2. Momentum strategy highly effective
        3. Risk management working well
        """
    }

    insights = await evening_coordinator._generate_trading_insights(
        performance_metrics,
        []
    )

    assert len(insights) == 3
    assert "Excellent win rate" in insights[0]
    assert "momentum strategy" in insights[1].lower()


@pytest.mark.asyncio
async def test_analyze_strategy_performance(evening_coordinator):
    """Test strategy performance analysis."""
    strategy_performance = {
        "momentum": {
            "trades": 5,
            "winning_trades": 4,
            "total_pnl": 10000.0,
            "win_rate": 80.0
        },
        "mean_reversion": {
            "trades": 3,
            "winning_trades": 1,
            "total_pnl": -2000.0,
            "win_rate": 33.3
        },
        "breakout": {
            "trades": 2,
            "winning_trades": 1,
            "total_pnl": 500.0,
            "win_rate": 50.0
        }
    }

    analysis = await evening_coordinator._analyze_strategy_performance(strategy_performance)

    assert "top_strategies" in analysis
    assert "underperforming_strategies" in analysis
    assert "recommendations" in analysis

    # Check momentum is identified as top performer
    assert any(s["strategy"] == "momentum" for s in analysis["top_strategies"])

    # Check mean reversion is underperforming
    assert any(s["strategy"] == "mean_reversion" for s in analysis["underperforming_strategies"])

    # Check recommendations are generated
    assert len(analysis["recommendations"]) > 0


@pytest.mark.asyncio
async def test_prepare_next_day_watchlist(evening_coordinator, container):
    """Test next day watchlist preparation."""
    performance_metrics = {
        "trades_reviewed": [
            {"symbol": "RELIANCE", "status": "CLOSED"},
            {"symbol": "TCS", "status": "OPEN"}
        ]
    }

    # Setup state manager mocks
    state_manager = await container.get("state_manager")
    state_manager.paper_trading.get_open_trades.return_value = [
        {"symbol": "TCS", "status": "OPEN"},
        {"symbol": "INFY", "status": "OPEN"}
    ]
    state_manager.paper_trading.get_discovery_watchlist.return_value = [
        {"symbol": "HDFC", "recommendation": "BUY"},
        {"symbol": "ICICI", "recommendation": "WATCH"}
    ]

    watchlist = await evening_coordinator._prepare_next_day_watchlist(
        performance_metrics,
        []
    )

    assert len(watchlist) > 0
    watch_symbols = [item["symbol"] for item in watchlist]

    # Check that traded symbols are included
    assert "RELIANCE" in watch_symbols
    assert "TCS" in watch_symbols
    assert "INFY" in watch_symbols

    # Check that BUY recommendations are included
    assert "HDFC" in watch_symbols


@pytest.mark.asyncio
async def test_compile_market_observations(evening_coordinator, container):
    """Test market observations compilation."""
    # Setup state manager mocks
    state_manager = await container.get("state_manager")

    # Mock news data
    mock_cursor = AsyncMock()
    mock_cursor.fetchall.return_value = [
        (1, "RELIANCE", "Positive earnings", "Summary", "Source", "positive", 0.8),
        (2, "TCS", "Negative guidance", "Summary", "Source", "negative", 0.9),
        (3, "INFY", "Neutral outlook", "Summary", "Source", "neutral", 0.6)
    ]
    state_manager.news_earnings_state.get_recent_news.return_value = mock_cursor

    observations = await evening_coordinator._compile_market_observations()

    assert "market_sentiment" in observations
    assert "volatility" in observations
    assert "key_events" in observations
    assert len(observations["key_events"]) == 3


@pytest.mark.asyncio
async def test_generate_learning_insights(evening_coordinator):
    """Test learning insights generation."""
    performance_metrics = {
        "daily_pnl": 5000.0,
        "win_rate": 75.0
    }

    trading_insights = [
        "Momentum strategy working well",
        "Risk management effective"
    ]

    strategy_analysis = {
        "top_strategies": [{"strategy": "momentum"}],
        "underperforming_strategies": []
    }

    learnings = await evening_coordinator._generate_learning_insights(
        performance_metrics,
        trading_insights,
        strategy_analysis
    )

    assert len(learnings) > 0
    assert any("Strong performance" in learning for learning in learnings)


@pytest.mark.asyncio
async def test_update_safeguards(evening_coordinator):
    """Test updating trading safeguards."""
    performance_metrics = {
        "daily_pnl": 3000.0
    }

    await evening_coordinator._update_safeguards(performance_metrics)

    # Verify safeguards were updated
    evening_coordinator.safeguards.update_daily_pnl.assert_called_once_with(3000.0)


@pytest.mark.asyncio
async def test_get_running_sessions(evening_coordinator):
    """Test getting list of running sessions."""
    # Initially no running sessions
    sessions = await evening_coordinator.get_running_sessions()
    assert len(sessions) == 0

    # Start a mock session
    session_id = "test_session_123"
    evening_coordinator._running_sessions[session_id] = {
        "start_time": datetime.now(timezone.utc),
        "status": "running",
        "review_date": "2025-01-15"
    }

    # Check session is listed
    sessions = await evening_coordinator.get_running_sessions()
    assert len(sessions) == 1
    assert sessions[0]["session_id"] == session_id
    assert sessions[0]["status"] == "running"


@pytest.mark.asyncio
async def test_cleanup(evening_coordinator):
    """Test coordinator cleanup."""
    # Add a running session
    evening_coordinator._running_sessions["test"] = {"data": "test"}

    # Run cleanup
    await evening_coordinator.cleanup()

    # Verify sessions are cleared
    assert len(evening_coordinator._running_sessions) == 0


@pytest.mark.asyncio
async def test_run_evening_review_error_handling(evening_coordinator, container):
    """Test error handling in evening review."""
    # Setup state manager to raise an error
    state_manager = await container.get("state_manager")
    state_manager.paper_trading.calculate_daily_performance_metrics.side_effect = Exception("Database error")

    # Run the evening review
    with pytest.raises(Exception) as exc_info:
        await evening_coordinator.run_evening_review()

    assert "Database error" in str(exc_info.value)


@pytest.mark.asyncio
async def test_format_strategy_performance(evening_coordinator):
    """Test strategy performance formatting."""
    strategy_performance = {
        "momentum": {"total_pnl": 5000.0, "win_rate": 75.0, "trades": 4},
        "mean_reversion": {"total_pnl": -1000.0, "win_rate": 40.0, "trades": 5}
    }

    formatted = evening_coordinator._format_strategy_performance(strategy_performance)

    assert "momentum: ₹5000.00 (75.0% win rate, 4 trades)" in formatted
    assert "mean_reversion: ₹-1000.00 (40.0% win rate, 5 trades)" in formatted