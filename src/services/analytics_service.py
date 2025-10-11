"""
Analytics Service

Handles technical analysis calculations, fundamental screening,
performance attribution, and backtesting engine.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import json
import aiosqlite
from loguru import logger

from ..config import Config
from ..core.event_bus import EventBus, Event, EventType, EventHandler


@dataclass
class TechnicalAnalysis:
    """Technical analysis result."""
    symbol: str
    timestamp: str
    indicators: Dict[str, float]
    signals: List[str]
    trend: str
    support_levels: List[float]
    resistance_levels: List[float]


@dataclass
class ScreeningResult:
    """Stock screening result."""
    symbol: str
    score: float
    criteria: Dict[str, Any]
    rank: int
    timestamp: str


class AnalyticsService(EventHandler):
    """
    Analytics Service - handles all analytical operations.

    Responsibilities:
    - Technical analysis calculations
    - Fundamental screening
    - Performance attribution
    - Backtesting engine
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "analytics.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)
        self.event_bus.subscribe(EventType.AI_ANALYSIS_COMPLETE, self)

    async def initialize(self) -> None:
        """Initialize the analytics service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            logger.info("Analytics service initialized")

    async def _create_tables(self) -> None:
        """Create analytics database tables."""
        schema = """
        -- Technical analysis results
        CREATE TABLE IF NOT EXISTS technical_analysis (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            indicators TEXT NOT NULL,
            signals TEXT NOT NULL,
            trend TEXT NOT NULL,
            support_levels TEXT,
            resistance_levels TEXT,
            created_at TEXT NOT NULL
        );

        -- Screening results
        CREATE TABLE IF NOT EXISTS screening_results (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            score REAL NOT NULL,
            criteria TEXT NOT NULL,
            rank INTEGER,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Performance metrics
        CREATE TABLE IF NOT EXISTS performance_metrics (
            id INTEGER PRIMARY KEY,
            symbol TEXT,
            metric_name TEXT NOT NULL,
            value REAL NOT NULL,
            period TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Backtest results
        CREATE TABLE IF NOT EXISTS backtest_results (
            id INTEGER PRIMARY KEY,
            strategy_name TEXT NOT NULL,
            parameters TEXT NOT NULL,
            results TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_technical_symbol ON technical_analysis(symbol);
        CREATE INDEX IF NOT EXISTS idx_technical_timestamp ON technical_analysis(timestamp);
        CREATE INDEX IF NOT EXISTS idx_screening_symbol ON screening_results(symbol);
        CREATE INDEX IF NOT EXISTS idx_screening_score ON screening_results(score);
        CREATE INDEX IF NOT EXISTS idx_performance_symbol ON performance_metrics(symbol);
        CREATE INDEX IF NOT EXISTS idx_performance_metric ON performance_metrics(metric_name);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def perform_technical_analysis(self, symbol: str, price_data: List[Dict[str, Any]]) -> TechnicalAnalysis:
        """Perform technical analysis on price data."""
        async with self._lock:
            # Simple technical analysis - in real implementation this would be more sophisticated
            if not price_data:
                return TechnicalAnalysis(
                    symbol=symbol,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    indicators={},
                    signals=[],
                    trend="unknown",
                    support_levels=[],
                    resistance_levels=[]
                )

            # Calculate basic indicators
            prices = [d.get('close', d.get('price', 0)) for d in price_data[-20:]]  # Last 20 periods

            if len(prices) < 2:
                sma_20 = prices[0] if prices else 0
                rsi = 50.0
            else:
                sma_20 = sum(prices) / len(prices)

                # Simple RSI calculation
                gains = [max(0, prices[i] - prices[i-1]) for i in range(1, len(prices))]
                losses = [max(0, prices[i-1] - prices[i]) for i in range(1, len(prices))]

                if losses:
                    avg_gain = sum(gains) / len(gains) if gains else 0
                    avg_loss = sum(losses) / len(losses)
                    rs = avg_gain / avg_loss if avg_loss > 0 else 0
                    rsi = 100 - (100 / (1 + rs))
                else:
                    rsi = 100.0

            indicators = {
                "sma_20": sma_20,
                "rsi": rsi,
                "current_price": prices[-1] if prices else 0
            }

            # Generate signals
            signals = []
            current_price = prices[-1] if prices else 0

            if current_price > sma_20 * 1.02:  # 2% above SMA
                signals.append("bullish_trend")
            elif current_price < sma_20 * 0.98:  # 2% below SMA
                signals.append("bearish_trend")

            if rsi > 70:
                signals.append("overbought")
            elif rsi < 30:
                signals.append("oversold")

            # Determine trend
            if current_price > sma_20:
                trend = "bullish"
            else:
                trend = "bearish"

            # Simple support/resistance (placeholder)
            support_levels = [current_price * 0.95, current_price * 0.90]
            resistance_levels = [current_price * 1.05, current_price * 1.10]

            analysis = TechnicalAnalysis(
                symbol=symbol,
                timestamp=datetime.now(timezone.utc).isoformat(),
                indicators=indicators,
                signals=signals,
                trend=trend,
                support_levels=support_levels,
                resistance_levels=resistance_levels
            )

            # Save to database
            await self._save_technical_analysis(analysis)

            return analysis

    async def _save_technical_analysis(self, analysis: TechnicalAnalysis) -> None:
        """Save technical analysis to database."""
        await self._db_connection.execute("""
            INSERT INTO technical_analysis
            (symbol, timestamp, indicators, signals, trend, support_levels, resistance_levels, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.symbol,
            analysis.timestamp,
            json.dumps(analysis.indicators),
            json.dumps(analysis.signals),
            analysis.trend,
            json.dumps(analysis.support_levels),
            json.dumps(analysis.resistance_levels),
            datetime.now(timezone.utc).isoformat()
        ))
        await self._db_connection.commit()

    async def perform_fundamental_screening(self, criteria: Dict[str, Any]) -> List[ScreeningResult]:
        """Perform fundamental screening based on criteria."""
        async with self._lock:
            # Placeholder implementation - in real system this would query financial databases
            # For demo, return mock results

            mock_stocks = [
                {"symbol": "RELIANCE", "pe_ratio": 25.5, "market_cap": 1500000, "roe": 12.5},
                {"symbol": "TCS", "pe_ratio": 28.3, "market_cap": 1200000, "roe": 15.2},
                {"symbol": "HDFC", "pe_ratio": 22.1, "market_cap": 800000, "roe": 18.1},
                {"symbol": "INFY", "pe_ratio": 24.7, "market_cap": 600000, "roe": 14.8},
            ]

            results = []
            for i, stock in enumerate(mock_stocks):
                # Simple scoring based on criteria
                score = 0.0

                if "pe_ratio_max" in criteria and stock["pe_ratio"] <= criteria["pe_ratio_max"]:
                    score += 25
                if "market_cap_min" in criteria and stock["market_cap"] >= criteria["market_cap_min"]:
                    score += 25
                if "roe_min" in criteria and stock["roe"] >= criteria["roe_min"]:
                    score += 25
                if "div_yield_min" in criteria:
                    score += 25  # Placeholder

                if score > 0:
                    result = ScreeningResult(
                        symbol=stock["symbol"],
                        score=score,
                        criteria=stock,
                        rank=i + 1,
                        timestamp=datetime.now(timezone.utc).isoformat()
                    )
                    results.append(result)
                    await self._save_screening_result(result)

            # Sort by score descending
            results.sort(key=lambda x: x.score, reverse=True)

            return results

    async def _save_screening_result(self, result: ScreeningResult) -> None:
        """Save screening result to database."""
        await self._db_connection.execute("""
            INSERT INTO screening_results
            (symbol, score, criteria, rank, timestamp, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            result.symbol,
            result.score,
            json.dumps(result.criteria),
            result.rank,
            result.timestamp,
            datetime.now(timezone.utc).isoformat()
        ))
        await self._db_connection.commit()

    async def calculate_performance_metrics(self, symbol: Optional[str] = None, period: str = "1M") -> Dict[str, Any]:
        """Calculate performance metrics."""
        async with self._lock:
            # Placeholder implementation
            metrics = {
                "total_return": 0.125,  # 12.5%
                "volatility": 0.18,
                "sharpe_ratio": 1.45,
                "max_drawdown": -0.08,
                "win_rate": 0.62,
                "period": period
            }

            if symbol:
                metrics["symbol"] = symbol

            # Save metrics
            await self._save_performance_metrics(symbol, metrics, period)

            return metrics

    async def _save_performance_metrics(self, symbol: Optional[str], metrics: Dict[str, Any], period: str) -> None:
        """Save performance metrics to database."""
        timestamp = datetime.now(timezone.utc).isoformat()

        for metric_name, value in metrics.items():
            if metric_name not in ["symbol", "period"]:
                await self._db_connection.execute("""
                    INSERT INTO performance_metrics
                    (symbol, metric_name, value, period, timestamp, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (symbol, metric_name, value, period, timestamp, timestamp))

        await self._db_connection.commit()

    async def run_backtest(self, strategy_name: str, parameters: Dict[str, Any],
                          start_date: str, end_date: str) -> Dict[str, Any]:
        """Run backtesting for a strategy."""
        async with self._lock:
            # Placeholder backtest implementation
            results = {
                "total_return": 0.45,  # 45%
                "annualized_return": 0.18,
                "volatility": 0.22,
                "sharpe_ratio": 1.8,
                "max_drawdown": -0.12,
                "total_trades": 156,
                "win_rate": 0.58,
                "profit_factor": 1.35
            }

            # Save backtest results
            await self._db_connection.execute("""
                INSERT INTO backtest_results
                (strategy_name, parameters, results, start_date, end_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                strategy_name,
                json.dumps(parameters),
                json.dumps(results),
                start_date,
                end_date,
                datetime.now(timezone.utc).isoformat()
            ))
            await self._db_connection.commit()

            logger.info(f"Backtest completed for {strategy_name}: {results['total_return']:.1%} return")
            return results

    async def get_technical_analysis(self, symbol: str, limit: int = 10) -> List[TechnicalAnalysis]:
        """Get recent technical analysis for a symbol."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT symbol, timestamp, indicators, signals, trend, support_levels, resistance_levels
                FROM technical_analysis
                WHERE symbol = ?
                ORDER BY timestamp DESC LIMIT ?
            """, (symbol, limit))

            results = []
            async for row in cursor:
                results.append(TechnicalAnalysis(
                    symbol=row[0],
                    timestamp=row[1],
                    indicators=json.loads(row[2]),
                    signals=json.loads(row[3]),
                    trend=row[4],
                    support_levels=json.loads(row[5]) if row[5] else [],
                    resistance_levels=json.loads(row[6]) if row[6] else []
                ))

            return results

    async def get_screening_results(self, limit: int = 50) -> List[ScreeningResult]:
        """Get recent screening results."""
        async with self._lock:
            cursor = await self._db_connection.execute("""
                SELECT symbol, score, criteria, rank, timestamp
                FROM screening_results
                ORDER BY score DESC, timestamp DESC LIMIT ?
            """, (limit,))

            results = []
            async for row in cursor:
                results.append(ScreeningResult(
                    symbol=row[0],
                    score=row[1],
                    criteria=json.loads(row[2]),
                    rank=row[3],
                    timestamp=row[4]
                ))

            return results

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.MARKET_PRICE_UPDATE:
            # Trigger technical analysis update
            data = event.data
            prices = data.get("prices", {})
            for symbol in prices.keys():
                # In real implementation, would fetch price history and analyze
                pass

        elif event.type == EventType.AI_ANALYSIS_COMPLETE:
            # Store AI analysis results
            data = event.data
            symbol = data.get("symbol")
            analysis = data.get("analysis", {})

            if symbol and analysis:
                await self._db_connection.execute("""
                    INSERT INTO technical_analysis
                    (symbol, timestamp, indicators, signals, trend, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    symbol,
                    datetime.now(timezone.utc).isoformat(),
                    json.dumps(analysis.get("indicators", {})),
                    json.dumps(analysis.get("signals", [])),
                    analysis.get("trend", "unknown"),
                    datetime.now(timezone.utc).isoformat()
                ))
                await self._db_connection.commit()

    async def close(self) -> None:
        """Close the analytics service."""
        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None