"""Tests for Monthly Portfolio Analysis feature."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch
from aiosqlite import Connection

from src.core.database_state.portfolio_monthly_analysis_state import PortfolioMonthlyAnalysisState
from src.core.coordinators.portfolio.monthly_analysis_coordinator import MonthlyPortfolioAnalysisCoordinator
from src.core.di import DependencyContainer
from src.config import Config


@pytest.fixture
async def test_db():
    """Create test database connection."""
    import aiosqlite
    # Use in-memory database for testing
    db = await aiosqlite.connect(":memory:")
    yield db
    await db.close()


@pytest.fixture
async def portfolio_analysis_state(test_db):
    """Create portfolio analysis state with test database."""
    from src.core.database_state.base import DatabaseConnection

    # Create mock database connection wrapper
    mock_db_connection = Mock()
    mock_db_connection.connection = test_db

    # Initialize tables
    await test_db.executescript("""
        CREATE TABLE IF NOT EXISTS portfolio_analysis (
            id INTEGER PRIMARY KEY,
            analysis_date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            company_name TEXT,
            sector TEXT,
            industry TEXT,
            pe_ratio REAL,
            pb_ratio REAL,
            roe REAL,
            debt_to_equity REAL,
            current_ratio REAL,
            profit_margins REAL,
            revenue_growth REAL,
            earnings_growth REAL,
            dividend_yield REAL,
            market_cap REAL,
            recent_earnings TEXT,
            news_sentiment TEXT,
            industry_trends TEXT,
            recommendation TEXT NOT NULL CHECK (recommendation IN ('KEEP', 'SELL')),
            reasoning TEXT NOT NULL,
            confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
            analysis_sources TEXT,
            price_at_analysis REAL,
            next_review_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(symbol, analysis_date)
        );

        CREATE TABLE IF NOT EXISTS monthly_analysis_summary (
            id INTEGER PRIMARY KEY,
            analysis_month TEXT NOT NULL UNIQUE,
            total_stocks_analyzed INTEGER DEFAULT 0,
            keep_recommendations INTEGER DEFAULT 0,
            sell_recommendations INTEGER DEFAULT 0,
            portfolio_value_at_analysis REAL,
            market_conditions TEXT,
            analysis_duration_seconds REAL,
            perplexity_api_calls INTEGER DEFAULT 0,
            claude_analysis_tokens INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
    """)

    state = PortfolioMonthlyAnalysisState(mock_db_connection)
    await state.initialize()
    return state


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)
    return config


@pytest.fixture
def mock_task_service():
    """Create mock task service."""
    return AsyncMock()


@pytest.fixture
def mock_config_state():
    """Create mock configuration state."""
    return AsyncMock()


@pytest.fixture
def mock_kite_portfolio_service():
    """Create mock Kite portfolio service."""
    service = AsyncMock()
    service.get_portfolio_holdings_and_positions.return_value = {
        "holdings": [
            {
                "tradingsymbol": "RELIANCE",
                "quantity": 100,
                "average_price": 2500,
                "last_price": 2600,
                "pnl": 10000
            },
            {
                "tradingsymbol": "TCS",
                "quantity": 50,
                "average_price": 3500,
                "last_price": 3600,
                "pnl": 5000
            }
        ],
        "positions": {},
        "total_holdings": 2
    }
    return service


@pytest.fixture
def mock_perplexity_client():
    """Create mock Perplexity client."""
    client = AsyncMock()
    client.query.return_value = {
        "structured_data": {
            "pe_ratio": 25.5,
            "pb_ratio": 3.2,
            "roe": 15.8,
            "debt_to_equity": 0.5,
            "revenue_growth": 12.3,
            "company_name": "Test Company",
            "sector": "Technology",
            "industry": "Software"
        },
        "sources": ["source1", "source2"]
    }
    return client


@pytest.fixture
def mock_claude_sdk_client():
    """Create mock Claude SDK client."""
    client = AsyncMock()
    client.query.return_value = """
    {
        "recommendation": "KEEP",
        "reasoning": "Strong fundamentals and growth prospects",
        "confidence_score": 0.85,
        "key_factors": ["ROE above 15%", "Consistent growth"],
        "risks": ["Market volatility"],
        "time_horizon": "long"
    }
    """
    return client


class TestPortfolioMonthlyAnalysisState:
    """Test portfolio monthly analysis state operations."""

    @pytest.mark.asyncio
    async def test_store_analysis(self, portfolio_analysis_state):
        """Test storing portfolio analysis."""
        analysis_date = "2024-01-15"
        symbol = "TEST"

        analysis_id = await portfolio_analysis_state.store_analysis(
            analysis_date=analysis_date,
            symbol=symbol,
            company_name="Test Company",
            sector="Technology",
            recommendation="KEEP",
            reasoning="Strong fundamentals",
            confidence_score=0.85,
            fundamentals={"pe_ratio": 20.5, "roe": 15.0},
            price_at_analysis=150.0
        )

        assert analysis_id is not None

        # Verify the analysis was stored
        analyses = await portfolio_analysis_state.get_analysis(symbol=symbol)
        assert len(analyses) == 1
        assert analyses[0]["symbol"] == symbol
        assert analyses[0]["recommendation"] == "KEEP"
        assert analyses[0]["confidence_score"] == 0.85

    @pytest.mark.asyncio
    async def test_get_latest_analysis_for_symbol(self, portfolio_analysis_state):
        """Test getting latest analysis for a symbol."""
        symbol = "TEST"

        # Store multiple analyses
        await portfolio_analysis_state.store_analysis(
            analysis_date="2024-01-01",
            symbol=symbol,
            recommendation="KEEP",
            reasoning="Old analysis",
            confidence_score=0.7
        )

        await portfolio_analysis_state.store_analysis(
            analysis_date="2024-02-01",
            symbol=symbol,
            recommendation="SELL",
            reasoning="New analysis",
            confidence_score=0.9
        )

        # Get latest analysis
        latest = await portfolio_analysis_state.get_latest_analysis_for_symbol(symbol)

        assert latest is not None
        assert latest["recommendation"] == "SELL"
        assert latest["analysis_date"] == "2024-02-01"

    @pytest.mark.asyncio
    async def test_store_monthly_summary(self, portfolio_analysis_state):
        """Test storing monthly analysis summary."""
        analysis_month = "2024-01"

        summary_id = await portfolio_analysis_state.store_monthly_summary(
            analysis_month=analysis_month,
            total_stocks=10,
            keep_count=7,
            sell_count=3,
            portfolio_value=1000000.0,
            analysis_duration=300.5,
            perplexity_calls=30,
            claude_tokens=5000
        )

        assert summary_id is not None

        # Verify the summary was stored
        summaries = await portfolio_analysis_state.get_monthly_summary(
            analysis_month=analysis_month
        )
        assert len(summaries) == 1
        assert summaries[0]["total_stocks_analyzed"] == 10
        assert summaries[0]["keep_recommendations"] == 7
        assert summaries[0]["sell_recommendations"] == 3

    @pytest.mark.asyncio
    async def test_get_analysis_statistics(self, portfolio_analysis_state):
        """Test getting analysis statistics."""
        # Store test data
        await portfolio_analysis_state.store_analysis(
            analysis_date="2024-01-15",
            symbol="STOCK1",
            recommendation="KEEP",
            reasoning="Test",
            confidence_score=0.8
        )

        await portfolio_analysis_state.store_analysis(
            analysis_date="2024-01-15",
            symbol="STOCK2",
            recommendation="SELL",
            reasoning="Test",
            confidence_score=0.9
        )

        # Get statistics
        stats = await portfolio_analysis_state.get_analysis_statistics(
            start_date="2024-01-01",
            end_date="2024-01-31"
        )

        assert stats["total_analyses"] == 2
        assert stats["unique_symbols"] == 2
        assert stats["keep_recommendations"] == 1
        assert stats["sell_recommendations"] == 1
        assert stats["keep_percentage"] == 50.0


class TestMonthlyPortfolioAnalysisCoordinator:
    """Test monthly portfolio analysis coordinator."""

    @pytest.mark.asyncio
    async def test_coordinator_initialization(
        self,
        mock_config,
        portfolio_analysis_state,
        mock_config_state,
        mock_task_service,
        mock_perplexity_client,
        mock_claude_sdk_client
    ):
        """Test coordinator initialization."""
        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=portfolio_analysis_state,
            config_state=mock_config_state,
            task_service=mock_task_service,
            perplexity_client=mock_perplexity_client,
            claude_sdk_client=mock_claude_sdk_client
        )

        # Mock event bus
        coordinator.event_bus = AsyncMock()

        await coordinator.initialize()

        assert coordinator._initialized is True
        assert coordinator._initialization_complete is True

    @pytest.mark.asyncio
    async def test_trigger_monthly_analysis_success(
        self,
        mock_config,
        portfolio_analysis_state,
        mock_config_state,
        mock_task_service,
        mock_kite_portfolio_service,
        mock_perplexity_client,
        mock_claude_sdk_client
    ):
        """Test successful monthly analysis trigger."""
        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=portfolio_analysis_state,
            config_state=mock_config_state,
            task_service=mock_task_service,
            kite_portfolio_service=mock_kite_portfolio_service,
            perplexity_client=mock_perplexity_client,
            claude_sdk_client=mock_claude_sdk_client
        )

        # Mock event bus
        coordinator.event_bus = AsyncMock()
        await coordinator.initialize()

        # Trigger analysis
        result = await coordinator.trigger_monthly_analysis(
            analysis_date="2024-01-15"
        )

        # Verify result
        assert result["status"] == "completed"
        assert result["month"] == "2024-01"
        assert result["summary"]["total_stocks"] == 2
        assert result["summary"]["keep_recommendations"] >= 0
        assert result["summary"]["sell_recommendations"] >= 0

    @pytest.mark.asyncio
    async def test_trigger_monthly_analysis_no_holdings(
        self,
        mock_config,
        portfolio_analysis_state,
        mock_config_state,
        mock_task_service,
        mock_kite_portfolio_service,
        mock_perplexity_client,
        mock_claude_sdk_client
    ):
        """Test monthly analysis with no portfolio holdings."""
        # Mock empty portfolio
        mock_kite_portfolio_service.get_portfolio_holdings_and_positions.return_value = {
            "holdings": [],
            "positions": {},
            "total_holdings": 0
        }

        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=portfolio_analysis_state,
            config_state=mock_config_state,
            task_service=mock_task_service,
            kite_portfolio_service=mock_kite_portfolio_service,
            perplexity_client=mock_perplexity_client,
            claude_sdk_client=mock_claude_sdk_client
        )

        # Mock event bus
        coordinator.event_bus = AsyncMock()
        await coordinator.initialize()

        # Trigger analysis
        result = await coordinator.trigger_monthly_analysis()

        # Verify result
        assert result["status"] == "no_holdings"
        assert "No portfolio holdings found" in result["message"]

    @pytest.mark.asyncio
    async def test_trigger_monthly_analysis_already_completed(
        self,
        mock_config,
        portfolio_analysis_state,
        mock_config_state,
        mock_task_service,
        mock_kite_portfolio_service,
        mock_perplexity_client,
        mock_claude_sdk_client
    ):
        """Test monthly analysis when already completed for the month."""
        # Pre-store a monthly summary
        await portfolio_analysis_state.store_monthly_summary(
            analysis_month="2024-01",
            total_stocks=5,
            keep_count=3,
            sell_count=2
        )

        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=portfolio_analysis_state,
            config_state=mock_config_state,
            task_service=mock_task_service,
            kite_portfolio_service=mock_kite_portfolio_service,
            perplexity_client=mock_perplexity_client,
            claude_sdk_client=mock_claude_sdk_client
        )

        # Mock event bus
        coordinator.event_bus = AsyncMock()
        await coordinator.initialize()

        # Trigger analysis without force
        result = await coordinator.trigger_monthly_analysis(
            analysis_date="2024-01-15"
        )

        # Verify result
        assert result["status"] == "already_completed"
        assert result["month"] == "2024-01"

    @pytest.mark.asyncio
    async def test_get_analysis_history(
        self,
        mock_config,
        portfolio_analysis_state,
        mock_config_state,
        mock_task_service
    ):
        """Test getting analysis history."""
        # Store test data
        await portfolio_analysis_state.store_analysis(
            analysis_date="2024-01-15",
            symbol="STOCK1",
            recommendation="KEEP",
            reasoning="Test 1",
            confidence_score=0.8
        )

        await portfolio_analysis_state.store_analysis(
            analysis_date="2024-02-15",
            symbol="STOCK1",
            recommendation="SELL",
            reasoning="Test 2",
            confidence_score=0.9
        )

        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=portfolio_analysis_state,
            config_state=mock_config_state,
            task_service=mock_task_service
        )

        # Get history for symbol
        history = await coordinator.get_analysis_history(symbol="STOCK1")

        assert len(history) == 2
        assert history[0]["symbol"] == "STOCK1"
        assert history[0]["recommendation"] == "SELL"  # Latest first

    @pytest.mark.asyncio
    async def test_parse_claude_response(self, mock_config):
        """Test parsing Claude response."""
        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=AsyncMock(),
            config_state=AsyncMock(),
            task_service=AsyncMock()
        )

        # Test valid JSON response
        json_response = '{"recommendation": "KEEP", "reasoning": "Test", "confidence_score": 0.8}'
        parsed = coordinator._parse_claude_response(json_response, "TEST")

        assert parsed["recommendation"] == "KEEP"
        assert parsed["reasoning"] == "Test"
        assert parsed["confidence_score"] == 0.8

    @pytest.mark.asyncio
    async def test_parse_claude_response_invalid(self, mock_config):
        """Test parsing invalid Claude response."""
        coordinator = MonthlyPortfolioAnalysisCoordinator(
            config=mock_config,
            portfolio_analysis_state=AsyncMock(),
            config_state=AsyncMock(),
            task_service=AsyncMock()
        )

        # Test invalid response
        invalid_response = "This is not JSON"
        parsed = coordinator._parse_claude_response(invalid_response, "TEST")

        # Should return fallback response
        assert parsed["recommendation"] == "KEEP"
        assert "Error parsing response" in parsed["risks"][0]


@pytest.mark.asyncio
async def test_monthly_analysis_api_trigger(client):
    """Test monthly analysis trigger API endpoint."""
    # Mock the coordinator
    with patch('src.web.routes.portfolio.monthly_analysis.get_di_container') as mock_get_container:
        mock_container = AsyncMock()
        mock_coordinator = AsyncMock()
        mock_coordinator.trigger_monthly_analysis.return_value = {
            "status": "completed",
            "month": "2024-01",
            "summary": {"total_stocks": 5}
        }
        mock_container.get.return_value = mock_coordinator
        mock_get_container.return_value = mock_container

        # Make API request
        response = await client.post(
            "/api/portfolio/monthly-analysis/trigger",
            json={"analysis_date": "2024-01-15"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["month"] == "2024-01"


@pytest.mark.asyncio
async def test_monthly_analysis_api_history(client):
    """Test monthly analysis history API endpoint."""
    # Mock the coordinator
    with patch('src.web.routes.portfolio.monthly_analysis.get_di_container') as mock_get_container:
        mock_container = AsyncMock()
        mock_coordinator = AsyncMock()
        mock_coordinator.get_analysis_history.return_value = [
            {
                "id": 1,
                "symbol": "TEST",
                "recommendation": "KEEP",
                "analysis_date": "2024-01-15"
            }
        ]
        mock_container.get.return_value = mock_coordinator
        mock_get_container.return_value = mock_container

        # Make API request
        response = await client.get("/api/portfolio/monthly-analysis/history")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "TEST"
        assert data[0]["recommendation"] == "KEEP"


@pytest.mark.asyncio
async def test_monthly_analysis_api_recommendations(client):
    """Test current recommendations API endpoint."""
    # Mock the coordinator
    with patch('src.web.routes.portfolio.monthly_analysis.get_di_container') as mock_get_container:
        mock_container = AsyncMock()
        mock_coordinator = AsyncMock()
        mock_coordinator.get_analysis_history.return_value = [
            {
                "symbol": "STOCK1",
                "recommendation": "KEEP",
                "confidence_score": 0.8,
                "analysis_date": "2024-01-15"
            },
            {
                "symbol": "STOCK2",
                "recommendation": "SELL",
                "confidence_score": 0.9,
                "analysis_date": "2024-01-15"
            }
        ]
        mock_container.get.return_value = mock_coordinator
        mock_get_container.return_value = mock_container

        # Make API request
        response = await client.get("/api/portfolio/monthly-analysis/recommendations")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["total_stocks"] == 2
        assert data["keep_recommendations"] == 1
        assert data["sell_recommendations"] == 1
        assert len(data["recommendations"]) == 2