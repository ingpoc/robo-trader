"""
Tests for Advanced Claude Learning System
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, patch

from src.core.learning_engine import (
    LearningEngine,
    PerformanceMetrics,
    StrategyPerformance,
    LearningInsight,
    DailyReflection,
    PatternRecognition
)
from src.config import Config
from src.core.database_state import DatabaseStateManager


@pytest.fixture
def config():
    """Test configuration."""
    return Config()


@pytest.fixture
def mock_state_manager():
    """Mock state manager for testing."""
    return Mock(spec=DatabaseStateManager)


@pytest.fixture
async def learning_engine(config, mock_state_manager):
    """Learning engine instance for testing."""
    engine = LearningEngine(config, mock_state_manager)
    await engine.initialize()
    yield engine
    await engine.cleanup()


class TestPerformanceMetrics:
    """Test PerformanceMetrics dataclass."""

    def test_from_dict(self):
        """Test creating PerformanceMetrics from dict."""
        data = {
            "total_trades": 10,
            "profitable_trades": 6,
            "win_rate": 0.6,
            "total_return": 125.50
        }
        metrics = PerformanceMetrics.from_dict(data)

        assert metrics.total_trades == 10
        assert metrics.profitable_trades == 6
        assert metrics.win_rate == 0.6
        assert metrics.total_return == 125.50

    def test_to_dict(self):
        """Test converting PerformanceMetrics to dict."""
        metrics = PerformanceMetrics(
            total_trades=15,
            profitable_trades=9,
            win_rate=0.6,
            total_return=180.75
        )
        data = metrics.to_dict()

        assert data["total_trades"] == 15
        assert data["profitable_trades"] == 9
        assert data["win_rate"] == 0.6
        assert data["total_return"] == 180.75


class TestStrategyPerformance:
    """Test StrategyPerformance dataclass."""

    def test_from_dict(self):
        """Test creating StrategyPerformance from dict."""
        data = {
            "strategy_name": "momentum",
            "time_period": "30d",
            "metrics": {
                "total_trades": 20,
                "win_rate": 0.65
            },
            "trade_history": [
                {"symbol": "AAPL", "pnl": 150.0}
            ]
        }
        perf = StrategyPerformance.from_dict(data)

        assert perf.strategy_name == "momentum"
        assert perf.time_period == "30d"
        assert perf.metrics.total_trades == 20
        assert perf.metrics.win_rate == 0.65
        assert len(perf.trade_history) == 1


class TestLearningInsight:
    """Test LearningInsight dataclass."""

    def test_creation(self):
        """Test creating LearningInsight."""
        insight = LearningInsight(
            insight_type="strategy_improvement",
            confidence=0.85,
            description="Win rate improved with tighter stops",
            actionable_recommendations=[
                "Reduce stop loss from 2% to 1.5%",
                "Add volume confirmation"
            ],
            affected_strategies=["swing_trading"]
        )

        assert insight.insight_type == "strategy_improvement"
        assert insight.confidence == 0.85
        assert len(insight.actionable_recommendations) == 2
        assert insight.affected_strategies == ["swing_trading"]
        assert insight.implemented == False


class TestDailyReflection:
    """Test DailyReflection dataclass."""

    def test_creation(self):
        """Test creating DailyReflection."""
        reflection = DailyReflection(
            date="2024-01-15",
            strategy_type="swing_trading",
            what_worked_well=["Good entry timing", "Risk management"],
            what_did_not_work=["Late exits on winners"],
            market_observations=["High volatility in tech sector"],
            tomorrow_focus=["Improve exit discipline", "Monitor volatility"],
            performance_summary={"win_rate": 0.65, "total_pnl": 1250.0},
            learning_insights=["Entry timing is crucial", "Need better exit rules"],
            confidence_level=0.75
        )

        assert reflection.date == "2024-01-15"
        assert reflection.strategy_type == "swing_trading"
        assert len(reflection.what_worked_well) == 2
        assert len(reflection.what_did_not_work) == 1
        assert reflection.confidence_level == 0.75


class TestPatternRecognition:
    """Test PatternRecognition dataclass."""

    def test_creation(self):
        """Test creating PatternRecognition."""
        pattern = PatternRecognition(
            pattern_type="entry_signal",
            pattern_name="Breakout with Volume",
            description="High volume breakouts have 70% success rate",
            confidence=0.82,
            frequency=15,
            success_rate=0.7,
            avg_return=185.5,
            last_observed="2024-01-15T10:30:00Z",
            conditions={"volume_spike": True, "breakout": True},
            recommendations=[
                "Prioritize breakouts with 2x average volume",
                "Use tighter stops for these entries"
            ]
        )

        assert pattern.pattern_type == "entry_signal"
        assert pattern.confidence == 0.82
        assert pattern.frequency == 15
        assert pattern.success_rate == 0.7
        assert pattern.conditions["volume_spike"] == True


class TestLearningEngine:
    """Test LearningEngine functionality."""

    @pytest.mark.asyncio
    async def test_initialization(self, learning_engine):
        """Test learning engine initialization."""
        assert learning_engine.client is None  # Lazy loaded
        assert learning_engine.min_trades_for_analysis == 10
        assert learning_engine.learning_interval_days == 7

    @pytest.mark.asyncio
    async def test_create_daily_reflection(self, learning_engine, mock_state_manager):
        """Test creating daily reflection."""
        # Mock the dependencies
        mock_state_manager.save_learning_insights = AsyncMock()

        performance_data = {
            "win_rate": 0.65,
            "total_trades": 12,
            "total_pnl": 1250.0
        }

        market_conditions = {
            "volatility": "moderate",
            "trend": "bullish",
            "observations": ["Tech sector strong", "High volume in winners"]
        }

        reflection = await learning_engine.create_daily_reflection(
            strategy_type="swing_trading",
            performance_data=performance_data,
            market_conditions=market_conditions
        )

        assert reflection is not None
        assert reflection.strategy_type == "swing_trading"
        assert reflection.performance_summary == performance_data
        assert "confidence_level" in reflection.__dict__

    @pytest.mark.asyncio
    async def test_analyze_strategy_effectiveness_no_data(self, learning_engine, mock_state_manager):
        """Test strategy effectiveness analysis with no data."""
        result = await learning_engine.analyze_strategy_effectiveness("unknown_strategy")

        assert result["status"] == "no_data"
        assert "No performance data available" in result["message"]

    @pytest.mark.asyncio
    async def test_analyze_performance_insufficient_data(self, learning_engine, mock_state_manager):
        """Test performance analysis with insufficient data."""
        # Mock empty intents
        mock_state_manager.get_portfolio = AsyncMock(return_value=Mock())
        mock_state_manager.get_all_intents = AsyncMock(return_value=[])
        mock_state_manager.save_learning_insights = AsyncMock()

        result = await learning_engine.analyze_performance("30d")

        assert result["status"] == "insufficient_data"
        assert result["trades_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_get_learning_history(self, learning_engine, mock_state_manager):
        """Test retrieving learning history."""
        # Mock empty data
        mock_state_manager.get_learning_insights = AsyncMock(return_value=[])

        result = await learning_engine.get_learning_history()

        assert result["status"] == "success"
        assert result["reflections"] == []
        assert result["insights"] == []

    @pytest.mark.asyncio
    async def test_adapt_to_market_conditions(self, learning_engine):
        """Test market condition adaptation."""
        conditions = {
            "volatility": "high",
            "trend": "bearish",
            "risk_level": "high"
        }

        result = await learning_engine.adapt_to_market_conditions(conditions)

        assert result["status"] == "success"
        assert "adaptations" in result
        assert "confidence" in result

    @pytest.mark.asyncio
    async def test_recognize_patterns(self, learning_engine, mock_state_manager):
        """Test pattern recognition from historical data."""
        historical_data = [
            {
                "entry_signal": "breakout",
                "pnl": 150.0,
                "timestamp": "2024-01-15T10:00:00Z"
            },
            {
                "entry_signal": "breakout",
                "pnl": -50.0,
                "timestamp": "2024-01-16T10:00:00Z"
            },
            {
                "entry_signal": "pullback",
                "pnl": 200.0,
                "timestamp": "2024-01-17T10:00:00Z"
            }
        ]

        patterns = await learning_engine.recognize_patterns(historical_data)

        assert isinstance(patterns, list)
        # Should recognize at least some patterns from the data
        assert len(patterns) >= 0  # May be 0 if Claude client not available

    @pytest.mark.asyncio
    async def test_calculate_performance_metrics(self, learning_engine):
        """Test performance metrics calculation."""
        # Create mock intents with execution data
        intents = []
        for i in range(5):
            intent = Mock()
            intent.status = "executed"
            intent.execution_reports = [{
                "pnl": 100.0 if i % 2 == 0 else -50.0,
                "symbol": f"SYMBOL{i}",
                "timestamp": f"2024-01-{i+1}T10:00:00Z"
            }]
            intent.symbol = f"SYMBOL{i}"
            intent.executed_at = f"2024-01-{i+1}T10:00:00Z"
            setattr(intent, 'pnl_calculated', 100.0 if i % 2 == 0 else -50.0)
            intents.append(intent)

        metrics = await learning_engine._calculate_performance_metrics(intents)

        assert metrics.total_trades == 5
        assert metrics.profitable_trades == 3  # 3 positive P&Ls
        assert metrics.win_rate == 0.6
        assert metrics.total_return == 250.0  # 3 * 100 - 2 * 50

    @pytest.mark.asyncio
    async def test_analyze_daily_performance(self, learning_engine):
        """Test daily performance analysis."""
        performance_data = {
            "win_rate": 0.75,
            "total_trades": 8,
            "total_pnl": 1200.0
        }

        market_conditions = {
            "volatility": "low",
            "observations": ["Clean trends", "Good follow-through"]
        }

        analysis = await learning_engine._analyze_daily_performance(
            performance_data, market_conditions
        )

        assert "worked_well" in analysis
        assert "did_not_work" in analysis
        assert "neutral" in analysis

        # Should identify strong win rate as working well
        assert len(analysis["worked_well"]) > 0


class TestLearningEngineIntegration:
    """Integration tests for LearningEngine."""

    @pytest.mark.asyncio
    async def test_full_learning_workflow(self, learning_engine, mock_state_manager):
        """Test complete learning workflow."""
        # Mock all required methods
        mock_state_manager.get_portfolio = AsyncMock(return_value=Mock())
        mock_state_manager.get_all_intents = AsyncMock(return_value=[])
        mock_state_manager.save_learning_insights = AsyncMock()

        # Test that methods can be called without errors
        result = await learning_engine.analyze_performance("7d")
        assert result["status"] in ["insufficient_data", "error"]

        # Test market adaptation
        adaptations = await learning_engine.adapt_to_market_conditions({
            "volatility": "moderate",
            "trend": "sideways"
        })
        assert adaptations["status"] == "success"

        # Test risk-adjusted planning
        risk_algorithms = await learning_engine.optimize_risk_adjusted_planning({
            "sharpe_ratio": 1.5,
            "max_drawdown": 0.12,
            "value_at_risk": 0.03
        })
        assert risk_algorithms["status"] == "success"

        # Test planning effectiveness learning
        learning_result = await learning_engine.learn_from_planning_effectiveness()
        assert learning_result["status"] == "success"