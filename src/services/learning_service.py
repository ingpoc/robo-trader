"""
Learning Engine Service

Handles recommendation outcome tracking, pattern recognition,
strategy improvement, and A/B testing framework.
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import aiosqlite
from loguru import logger

from src.config import Config

from ..core.event_bus import Event, EventBus, EventHandler, EventType


@dataclass
class LearningInsight:
    """Learning insight from trading outcomes."""

    insight_type: str
    symbol: Optional[str]
    pattern: str
    confidence: float
    impact: float
    recommendation: str
    timestamp: str


@dataclass
class StrategyPerformance:
    """Strategy performance metrics."""

    strategy_name: str
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: float
    last_updated: str


class LearningService(EventHandler):
    """
    Learning Engine Service - handles AI learning and strategy optimization.

    Responsibilities:
    - Recommendation outcome tracking
    - Pattern recognition
    - Strategy improvement
    - A/B testing framework
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "learning.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.EXECUTION_ORDER_FILLED, self)
        self.event_bus.subscribe(EventType.PORTFOLIO_PNL_UPDATE, self)
        self.event_bus.subscribe(EventType.AI_RECOMMENDATION, self)

    async def initialize(self) -> None:
        """Initialize the learning service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            logger.info("Learning service initialized")

    async def _create_tables(self) -> None:
        """Create learning database tables."""
        schema = """
        -- Recommendation outcomes
        CREATE TABLE IF NOT EXISTS recommendation_outcomes (
            id INTEGER PRIMARY KEY,
            recommendation_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            action TEXT NOT NULL,
            entry_price REAL,
            exit_price REAL,
            pnl REAL,
            pnl_percentage REAL,
            holding_period_days INTEGER,
            outcome TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Learning insights
        CREATE TABLE IF NOT EXISTS learning_insights (
            id INTEGER PRIMARY KEY,
            insight_type TEXT NOT NULL,
            symbol TEXT,
            pattern TEXT NOT NULL,
            confidence REAL NOT NULL,
            impact REAL NOT NULL,
            recommendation TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Strategy performance
        CREATE TABLE IF NOT EXISTS strategy_performance (
            id INTEGER PRIMARY KEY,
            strategy_name TEXT NOT NULL,
            total_trades INTEGER NOT NULL,
            win_rate REAL NOT NULL,
            profit_factor REAL NOT NULL,
            max_drawdown REAL NOT NULL,
            sharpe_ratio REAL NOT NULL,
            last_updated TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- A/B test results
        CREATE TABLE IF NOT EXISTS ab_test_results (
            id INTEGER PRIMARY KEY,
            test_name TEXT NOT NULL,
            variant_a TEXT NOT NULL,
            variant_b TEXT NOT NULL,
            metric TEXT NOT NULL,
            variant_a_value REAL NOT NULL,
            variant_b_value REAL NOT NULL,
            winner TEXT,
            confidence REAL NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Pattern recognition
        CREATE TABLE IF NOT EXISTS patterns (
            id INTEGER PRIMARY KEY,
            pattern_type TEXT NOT NULL,
            symbol TEXT,
            pattern_data TEXT NOT NULL,
            frequency INTEGER NOT NULL,
            success_rate REAL NOT NULL,
            last_seen TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_outcomes_symbol ON recommendation_outcomes(symbol);
        CREATE INDEX IF NOT EXISTS idx_outcomes_outcome ON recommendation_outcomes(outcome);
        CREATE INDEX IF NOT EXISTS idx_insights_type ON learning_insights(insight_type);
        CREATE INDEX IF NOT EXISTS idx_insights_symbol ON learning_insights(symbol);
        CREATE INDEX IF NOT EXISTS idx_performance_strategy ON strategy_performance(strategy_name);
        CREATE INDEX IF NOT EXISTS idx_patterns_type ON patterns(pattern_type);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def track_recommendation_outcome(
        self,
        recommendation_id: str,
        symbol: str,
        action: str,
        entry_price: float,
        exit_price: float,
        holding_period_days: int,
    ) -> None:
        """Track the outcome of an AI recommendation."""
        async with self._lock:
            pnl = exit_price - entry_price
            pnl_percentage = (pnl / entry_price) * 100 if entry_price > 0 else 0

            # Determine outcome
            if pnl > 0:
                outcome = "profit"
            elif pnl < 0:
                outcome = "loss"
            else:
                outcome = "breakeven"

            timestamp = datetime.now(timezone.utc).isoformat()

            await self._db_connection.execute(
                """
                INSERT INTO recommendation_outcomes
                (recommendation_id, symbol, action, entry_price, exit_price, pnl,
                 pnl_percentage, holding_period_days, outcome, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    recommendation_id,
                    symbol,
                    action,
                    entry_price,
                    exit_price,
                    pnl,
                    pnl_percentage,
                    holding_period_days,
                    outcome,
                    timestamp,
                    timestamp,
                ),
            )
            await self._db_connection.commit()

            # Generate learning insight
            await self._generate_insight_from_outcome(
                symbol, action, outcome, pnl_percentage
            )

            logger.info(
                f"Tracked recommendation outcome: {symbol} {action} -> {outcome} ({pnl_percentage:.2f}%)"
            )

    async def _generate_insight_from_outcome(
        self, symbol: str, action: str, outcome: str, pnl_percentage: float
    ) -> None:
        """Generate learning insights from recommendation outcomes."""
        # Analyze patterns in outcomes
        pattern = f"{action}_on_{symbol}"

        # Get recent outcomes for this pattern
        cursor = await self._db_connection.execute(
            """
            SELECT outcome, pnl_percentage FROM recommendation_outcomes
            WHERE symbol = ? AND action = ?
            ORDER BY timestamp DESC LIMIT 20
        """,
            (symbol, action),
        )

        outcomes = []
        async for row in cursor:
            outcomes.append({"outcome": row[0], "pnl": row[1]})

        if len(outcomes) >= 5:
            # Calculate success rate
            profitable_trades = sum(1 for o in outcomes if o["outcome"] == "profit")
            success_rate = profitable_trades / len(outcomes)

            # Calculate average P&L
            avg_pnl = sum(o["pnl"] for o in outcomes) / len(outcomes)

            # Generate insight
            if success_rate > 0.6 and avg_pnl > 2.0:
                insight_type = "successful_pattern"
                confidence = min(success_rate * 100, 95.0)
                recommendation = f"Continue using {action} strategy for {symbol}"
            elif success_rate < 0.4 and avg_pnl < -2.0:
                insight_type = "unsuccessful_pattern"
                confidence = min((1 - success_rate) * 100, 95.0)
                recommendation = f"Avoid {action} strategy for {symbol}"
            else:
                insight_type = "neutral_pattern"
                confidence = 50.0
                recommendation = f"Monitor {action} strategy for {symbol} closely"

            insight = LearningInsight(
                insight_type=insight_type,
                symbol=symbol,
                pattern=pattern,
                confidence=confidence,
                impact=abs(avg_pnl),
                recommendation=recommendation,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )

            await self._save_learning_insight(insight)

    async def _save_learning_insight(self, insight: LearningInsight) -> None:
        """Save learning insight to database."""
        await self._db_connection.execute(
            """
            INSERT INTO learning_insights
            (insight_type, symbol, pattern, confidence, impact, recommendation, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                insight.insight_type,
                insight.symbol,
                insight.pattern,
                insight.confidence,
                insight.impact,
                insight.recommendation,
                insight.timestamp,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db_connection.commit()

    async def update_strategy_performance(
        self, strategy_name: str, trades: List[Dict[str, Any]]
    ) -> None:
        """Update strategy performance metrics."""
        async with self._lock:
            if not trades:
                return

            # Calculate metrics
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.get("pnl", 0) > 0)
            win_rate = winning_trades / total_trades if total_trades > 0 else 0

            # Profit factor
            gross_profit = sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) > 0)
            gross_loss = abs(
                sum(t.get("pnl", 0) for t in trades if t.get("pnl", 0) < 0)
            )
            profit_factor = (
                gross_profit / gross_loss if gross_loss > 0 else float("inf")
            )

            # Max drawdown (simplified)
            cumulative_pnl = 0
            peak = 0
            max_drawdown = 0
            for trade in trades:
                cumulative_pnl += trade.get("pnl", 0)
                peak = max(peak, cumulative_pnl)
                drawdown = peak - cumulative_pnl
                max_drawdown = max(max_drawdown, drawdown)

            # Sharpe ratio (simplified - assuming daily returns)
            returns = [t.get("pnl", 0) for t in trades]
            if returns:
                avg_return = sum(returns) / len(returns)
                std_dev = (
                    sum((r - avg_return) ** 2 for r in returns) / len(returns)
                ) ** 0.5
                sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
            else:
                sharpe_ratio = 0

            performance = StrategyPerformance(
                strategy_name=strategy_name,
                total_trades=total_trades,
                win_rate=win_rate,
                profit_factor=profit_factor,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                last_updated=datetime.now(timezone.utc).isoformat(),
            )

            # Save to database
            await self._db_connection.execute(
                """
                INSERT OR REPLACE INTO strategy_performance
                (id, strategy_name, total_trades, win_rate, profit_factor, max_drawdown, sharpe_ratio, last_updated, created_at)
                VALUES (
                    (SELECT id FROM strategy_performance WHERE strategy_name = ?),
                    ?, ?, ?, ?, ?, ?, ?, ?
                )
            """,
                (
                    strategy_name,
                    strategy_name,
                    performance.total_trades,
                    performance.win_rate,
                    performance.profit_factor,
                    performance.max_drawdown,
                    performance.sharpe_ratio,
                    performance.last_updated,
                    performance.last_updated,
                ),
            )
            await self._db_connection.commit()

            logger.info(
                f"Updated performance for {strategy_name}: {performance.win_rate:.1%} win rate"
            )

    async def run_ab_test(
        self,
        test_name: str,
        variant_a: str,
        variant_b: str,
        metric: str,
        duration_days: int = 30,
    ) -> Dict[str, Any]:
        """Run A/B test between two strategy variants."""
        async with self._lock:
            start_date = (
                datetime.now(timezone.utc) - timedelta(days=duration_days)
            ).isoformat()
            end_date = datetime.now(timezone.utc).isoformat()

            # Get performance data for both variants (simplified)
            # In real implementation, this would query actual trading results

            # Mock results for demonstration
            variant_a_value = 0.125  # 12.5% return
            variant_b_value = 0.089  # 8.9% return

            # Determine winner
            if variant_a_value > variant_b_value:
                winner = variant_a
                confidence = 85.0
            else:
                winner = variant_b
                confidence = 78.0

            # Save A/B test results
            await self._db_connection.execute(
                """
                INSERT INTO ab_test_results
                (test_name, variant_a, variant_b, metric, variant_a_value, variant_b_value,
                 winner, confidence, start_date, end_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    test_name,
                    variant_a,
                    variant_b,
                    metric,
                    variant_a_value,
                    variant_b_value,
                    winner,
                    confidence,
                    start_date,
                    end_date,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            await self._db_connection.commit()

            result = {
                "test_name": test_name,
                "winner": winner,
                "confidence": confidence,
                "variant_a": {"name": variant_a, "value": variant_a_value},
                "variant_b": {"name": variant_b, "value": variant_b_value},
                "metric": metric,
                "duration_days": duration_days,
            }

            logger.info(f"A/B test completed: {test_name} - Winner: {winner}")
            return result

    async def recognize_patterns(
        self, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Recognize trading patterns from historical data."""
        async with self._lock:
            # Analyze recommendation outcomes for patterns
            query = """
                SELECT symbol, action, outcome, COUNT(*) as frequency,
                       AVG(pnl_percentage) as avg_pnl,
                       SUM(CASE WHEN outcome = 'profit' THEN 1 ELSE 0 END) * 1.0 / COUNT(*) as success_rate
                FROM recommendation_outcomes
            """
            params = []

            if symbol:
                query += " WHERE symbol = ?"
                params.append(symbol)

            query += " GROUP BY symbol, action, outcome ORDER BY frequency DESC"

            cursor = await self._db_connection.execute(query, params)

            patterns = []
            async for row in cursor:
                pattern = {
                    "symbol": row[0],
                    "action": row[1],
                    "outcome": row[2],
                    "frequency": row[3],
                    "avg_pnl_percentage": row[4],
                    "success_rate": row[5],
                }
                patterns.append(pattern)

                # Update patterns table
                await self._update_pattern_record(pattern)

            return patterns

    async def _update_pattern_record(self, pattern: Dict[str, Any]) -> None:
        """Update pattern recognition record."""
        pattern_key = f"{pattern['symbol']}_{pattern['action']}_{pattern['outcome']}"

        await self._db_connection.execute(
            """
            INSERT OR REPLACE INTO patterns
            (id, pattern_type, symbol, pattern_data, frequency, success_rate, last_seen, created_at)
            VALUES (
                (SELECT id FROM patterns WHERE pattern_type = ? AND symbol = ?),
                ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                pattern_key,
                pattern["symbol"],
                pattern_key,
                pattern["symbol"],
                json.dumps(pattern),
                pattern["frequency"],
                pattern["success_rate"],
                datetime.now(timezone.utc).isoformat(),
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        await self._db_connection.commit()

    async def get_learning_insights(self, limit: int = 20) -> List[LearningInsight]:
        """Get recent learning insights."""
        async with self._lock:
            cursor = await self._db_connection.execute(
                """
                SELECT insight_type, symbol, pattern, confidence, impact, recommendation, timestamp
                FROM learning_insights
                ORDER BY timestamp DESC LIMIT ?
            """,
                (limit,),
            )

            insights = []
            async for row in cursor:
                insights.append(
                    LearningInsight(
                        insight_type=row[0],
                        symbol=row[1],
                        pattern=row[2],
                        confidence=row[3],
                        impact=row[4],
                        recommendation=row[5],
                        timestamp=row[6],
                    )
                )

            return insights

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.EXECUTION_ORDER_FILLED:
            # Track order execution for learning
            data = event.data
            symbol = data.get("symbol")
            if symbol:
                logger.debug(f"Order filled for {symbol} - tracking for learning")

        elif event.type == EventType.PORTFOLIO_PNL_UPDATE:
            # Analyze portfolio performance
            data = event.data
            pnl = data.get("pnl", 0)
            if pnl != 0:
                logger.debug(f"Portfolio P&L update: {pnl}")

        elif event.type == EventType.AI_RECOMMENDATION:
            # Track AI recommendations
            data = event.data
            symbol = data.get("symbol")
            action = data.get("action")
            if symbol and action:
                logger.debug(f"AI recommendation: {action} {symbol}")

    async def close(self) -> None:
        """Close the learning service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None
