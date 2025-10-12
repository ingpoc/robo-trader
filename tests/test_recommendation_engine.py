"""
Test Recommendation Engine

Tests for the AI-powered recommendation engine functionality.
"""

import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

from src.config import Config
from src.core.database_state import DatabaseStateManager
from src.services.recommendation_service import RecommendationEngine, RecommendationResult, RecommendationFactors
from src.services.fundamental_service import FundamentalService
from src.services.risk_service import RiskService
from src.core.state_models import FundamentalAnalysis, Recommendation


class TestRecommendationEngine:
    """Test cases for the recommendation engine."""

    @pytest.fixture
    async def setup_engine(self):
        """Set up test fixtures."""
        config = Config()
        state_manager = Mock(spec=DatabaseStateManager)
        fundamental_service = Mock(spec=FundamentalService)
        risk_service = Mock(spec=RiskService)

        # Mock fundamental data
        fundamental_data = FundamentalAnalysis(
            symbol="TEST",
            analysis_date=datetime.now(timezone.utc).isoformat(),
            pe_ratio=15.5,
            pb_ratio=2.1,
            roe=18.5,
            roa=8.2,
            debt_to_equity=0.8,
            revenue_growth=12.5,
            earnings_growth=15.2,
            overall_score=75.0,
            recommendation="BUY"
        )

        fundamental_service.fetch_fundamentals_batch = AsyncMock(return_value={"TEST": fundamental_data})
        state_manager.get_fundamental_analysis = AsyncMock(return_value=[fundamental_data])

        # Mock news data
        state_manager.get_news_for_symbol = AsyncMock(return_value=[
            {"sentiment": "positive", "title": "Good earnings", "content": "Company reported strong earnings"}
        ])

        engine = RecommendationEngine(config, state_manager, fundamental_service, risk_service)
        return engine, state_manager, fundamental_service, risk_service

    @pytest.mark.asyncio
    async def test_weighted_scoring(self, setup_engine):
        """Test weighted scoring algorithm."""
        engine, _, _, _ = setup_engine

        factors = RecommendationFactors(
            fundamental_score=80.0,
            valuation_score=70.0,
            growth_score=75.0,
            risk_score=20.0,  # Lower risk = better
            qualitative_score=65.0
        )

        score = engine._calculate_weighted_score(factors)

        # Should be a weighted average
        expected_score = (
            80.0 * 0.35 +  # fundamental
            70.0 * 0.25 +  # valuation
            75.0 * 0.20 +  # growth
            (100 - 20.0) * 0.15 +  # risk (inverted)
            65.0 * 0.05    # qualitative
        )

        assert abs(score - expected_score) < 0.1

    @pytest.mark.asyncio
    async def test_recommendation_thresholds(self, setup_engine):
        """Test BUY/HOLD/SELL recommendation logic."""
        engine, _, _, _ = setup_engine

        factors = RecommendationFactors(fundamental_score=75.0, risk_score=25.0, growth_score=70.0)

        # Test BUY conditions
        buy_score = 78.0
        assert engine._determine_recommendation_type(factors, buy_score) == "BUY"

        # Test SELL conditions
        sell_score = 42.0
        assert engine._determine_recommendation_type(factors, sell_score) == "SELL"

        # Test HOLD conditions
        hold_score = 55.0
        assert engine._determine_recommendation_type(factors, hold_score) == "HOLD"

    @pytest.mark.asyncio
    async def test_confidence_levels(self, setup_engine):
        """Test confidence level calculation."""
        engine, _, _, _ = setup_engine

        assert engine._calculate_confidence_level(85.0) == "HIGH"
        assert engine._calculate_confidence_level(70.0) == "MEDIUM"
        assert engine._calculate_confidence_level(50.0) == "LOW"

    @pytest.mark.asyncio
    async def test_valuation_scoring(self, setup_engine):
        """Test valuation score calculation."""
        engine, _, _, _ = setup_engine

        # Mock fundamental data
        fundamental_data = FundamentalAnalysis(
            symbol="TEST",
            analysis_date=datetime.now(timezone.utc).isoformat(),
            pe_ratio=18.0,  # Reasonable P/E
            pb_ratio=2.5,   # Reasonable P/B
        )

        score = await engine._calculate_valuation_score("TEST", fundamental_data)
        assert score is not None
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_growth_scoring(self, setup_engine):
        """Test growth score calculation."""
        engine, _, _, _ = setup_engine

        fundamental_data = FundamentalAnalysis(
            symbol="TEST",
            analysis_date=datetime.now(timezone.utc).isoformat(),
            revenue_growth=15.0,
            earnings_growth=18.0
        )

        score = await engine._calculate_growth_score("TEST", fundamental_data)
        assert score is not None
        assert 0 <= score <= 100

    @pytest.mark.asyncio
    async def test_target_price_calculation(self, setup_engine):
        """Test target price and stop loss calculation."""
        engine, _, _, _ = setup_engine

        # Mock current price
        with patch.object(engine, '_get_current_price', return_value=100.0):
            target, stop = await engine._calculate_target_prices("TEST", "BUY", RecommendationFactors())

            assert target is not None
            assert stop is not None
            assert target > 100.0  # Target should be above current price for BUY
            assert stop < 100.0    # Stop should be below current price for BUY

    @pytest.mark.asyncio
    async def test_recommendation_storage(self, setup_engine):
        """Test recommendation storage in database."""
        engine, state_manager, _, _ = setup_engine

        # Mock database save
        state_manager.save_recommendation = AsyncMock(return_value=123)

        result = RecommendationResult(
            symbol="TEST",
            recommendation_type="BUY",
            confidence_level="HIGH",
            overall_score=78.5,
            factors=RecommendationFactors(fundamental_score=80.0),
            target_price=110.0,
            stop_loss=95.0,
            reasoning="Strong fundamentals",
            risk_level="MEDIUM",
            time_horizon="MEDIUM_TERM"
        )

        recommendation_id = await engine.store_recommendation(result)

        assert recommendation_id == 123
        state_manager.save_recommendation.assert_called_once()

    @pytest.mark.asyncio
    async def test_bulk_recommendations(self, setup_engine):
        """Test bulk recommendation generation."""
        engine, state_manager, fundamental_service, _ = setup_engine

        # Mock bulk fundamental data
        fundamental_service.fetch_fundamentals_batch = AsyncMock(return_value={
            "TEST1": FundamentalAnalysis(
                symbol="TEST1",
                analysis_date=datetime.now(timezone.utc).isoformat(),
                overall_score=75.0,
                recommendation="BUY"
            ),
            "TEST2": FundamentalAnalysis(
                symbol="TEST2",
                analysis_date=datetime.now(timezone.utc).isoformat(),
                overall_score=45.0,
                recommendation="HOLD"
            )
        })

        # Mock save method
        state_manager.save_recommendation = AsyncMock(return_value=123)

        symbols = ["TEST1", "TEST2"]
        recommendations = await engine.generate_bulk_recommendations(symbols)

        assert len(recommendations) == 2
        assert "TEST1" in recommendations
        assert "TEST2" in recommendations

    @pytest.mark.asyncio
    async def test_claude_analysis_fallback(self, setup_engine):
        """Test fallback to rule-based analysis when Claude is unavailable."""
        engine, _, _, _ = setup_engine

        # Ensure Claude is not available
        engine.claude_client = None

        result = await engine.generate_recommendation("TEST")

        assert result is not None
        assert result.recommendation_type in ["BUY", "HOLD", "SELL"]
        assert result.confidence_level in ["HIGH", "MEDIUM", "LOW"]

    @pytest.mark.asyncio
    async def test_insufficient_data_handling(self, setup_engine):
        """Test handling of insufficient data."""
        engine, state_manager, fundamental_service, _ = setup_engine

        # Mock no fundamental data
        fundamental_service.fetch_fundamentals_batch = AsyncMock(return_value={})

        result = await engine.generate_recommendation("TEST")

        # Should still return a result with rule-based analysis
        assert result is not None


if __name__ == "__main__":
    # Run basic functionality test
    async def test_basic_functionality():
        print("Testing basic recommendation engine functionality...")

        config = Config()
        state_manager = Mock(spec=DatabaseStateManager)
        fundamental_service = Mock(spec=FundamentalService)
        risk_service = Mock(spec=RiskService)

        # Create engine
        engine = RecommendationEngine(config, state_manager, fundamental_service, risk_service)

        # Test weighted scoring
        factors = RecommendationFactors(
            fundamental_score=80.0,
            valuation_score=75.0,
            growth_score=70.0,
            risk_score=25.0,
            qualitative_score=60.0
        )

        score = engine._calculate_weighted_score(factors)
        print(f"Weighted score: {score:.2f}")

        # Test recommendation logic
        recommendation = engine._determine_recommendation_type(factors, score)
        confidence = engine._calculate_confidence_level(score)

        print(f"Recommendation: {recommendation}")
        print(f"Confidence: {confidence}")

        print("Basic functionality test completed successfully!")

    asyncio.run(test_basic_functionality())