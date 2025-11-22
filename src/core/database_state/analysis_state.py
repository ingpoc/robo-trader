"""
Analysis and recommendation state management for Robo Trader.

Manages fundamental analysis, recommendations, market conditions, and performance tracking.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from loguru import logger

from src.core.state_models import FundamentalAnalysis, Recommendation, MarketConditions, AnalysisPerformance
from .base import DatabaseConnection


class AnalysisStateManager:
    """
    Manages analysis data and recommendations.

    Responsibilities:
    - Save/retrieve fundamental analysis
    - Save/retrieve trading recommendations
    - Track recommendation outcomes
    - Save market conditions
    - Track analysis performance metrics
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db
        self._lock = asyncio.Lock()

    async def save_fundamental_analysis(self, analysis: FundamentalAnalysis) -> int:
        """Save fundamental analysis to database."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db.connection.execute("""
                INSERT OR REPLACE INTO fundamental_analysis
                (symbol, analysis_date, pe_ratio, pb_ratio, roe, roa, debt_to_equity,
                 current_ratio, profit_margins, revenue_growth, earnings_growth,
                 dividend_yield, market_cap, sector_pe, industry_rank, overall_score,
                 recommendation, analysis_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.symbol, analysis.analysis_date,
                analysis.pe_ratio, analysis.pb_ratio, analysis.roe, analysis.roa,
                analysis.debt_to_equity, analysis.current_ratio,
                analysis.profit_margins, analysis.revenue_growth, analysis.earnings_growth,
                analysis.dividend_yield, analysis.market_cap,
                analysis.sector_pe, analysis.industry_rank, analysis.overall_score,
                analysis.recommendation,
                json.dumps(analysis.analysis_data) if analysis.analysis_data else None,
                now, now
            ))
            await self.db.connection.commit()
            return cursor.lastrowid

    async def get_fundamental_analysis(
        self,
        symbol: str,
        limit: int = 1
    ) -> List[FundamentalAnalysis]:
        """Get fundamental analysis for symbol."""
        async with self._lock:
            analyses = []
            async with self.db.connection.execute("""
                SELECT * FROM fundamental_analysis
                WHERE symbol = ?
                ORDER BY analysis_date DESC
                LIMIT ?
            """, (symbol, limit)) as cursor:
                async for row in cursor:
                    analyses.append(FundamentalAnalysis(
                        symbol=row[1],
                        analysis_date=row[2],
                        pe_ratio=row[3],
                        pb_ratio=row[4],
                        roe=row[5],
                        roa=row[6],
                        debt_to_equity=row[7],
                        current_ratio=row[8],
                        profit_margins=row[9],
                        revenue_growth=row[10],
                        earnings_growth=row[11],
                        dividend_yield=row[12],
                        market_cap=row[13],
                        sector_pe=row[14],
                        industry_rank=row[15],
                        overall_score=row[16],
                        recommendation=row[17],
                        analysis_data=json.loads(row[18]) if row[18] else None
                    ))
            return analyses

    async def save_recommendation(self, recommendation: Recommendation) -> int:
        """Save trading recommendation."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db.connection.execute("""
                INSERT INTO recommendations
                (symbol, recommendation_type, confidence_score, target_price, stop_loss,
                 quantity, reasoning, analysis_type, time_horizon, risk_level,
                 potential_impact, alternative_suggestions, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                recommendation.symbol,
                recommendation.recommendation_type,
                recommendation.confidence_score,
                recommendation.target_price,
                recommendation.stop_loss,
                recommendation.quantity,
                recommendation.reasoning,
                recommendation.analysis_type,
                recommendation.time_horizon,
                recommendation.risk_level,
                recommendation.potential_impact,
                json.dumps(recommendation.alternative_suggestions or []),
                now
            ))
            await self.db.connection.commit()
            return cursor.lastrowid

    async def get_recommendations(
        self,
        symbol: Optional[str] = None,
        limit: int = 20
    ) -> List[Recommendation]:
        """Get trading recommendations."""
        async with self._lock:
            recommendations = []
            query = "SELECT * FROM recommendations"
            params = []

            if symbol:
                query += " WHERE symbol = ?"
                params.append(symbol)

            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            async with self.db.connection.execute(query, tuple(params)) as cursor:
                async for row in cursor:
                    recommendations.append(Recommendation(
                        symbol=row[1],
                        recommendation_type=row[2],
                        confidence_score=row[3],
                        target_price=row[4],
                        stop_loss=row[5],
                        quantity=row[6],
                        reasoning=row[7],
                        analysis_type=row[8],
                        time_horizon=row[9],
                        risk_level=row[10],
                        potential_impact=row[11],
                        alternative_suggestions=json.loads(row[12]) if row[12] else []
                    ))
            return recommendations

    async def save_market_conditions(self, conditions: MarketConditions) -> int:
        """Save market conditions snapshot."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db.connection.execute("""
                INSERT OR REPLACE INTO market_conditions
                (date, vix_index, nifty_50_level, market_sentiment, interest_rates,
                 inflation_rate, gdp_growth, sector_performance, global_events, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                conditions.date,
                conditions.vix_index,
                conditions.nifty_50_level,
                conditions.market_sentiment,
                conditions.interest_rates,
                conditions.inflation_rate,
                conditions.gdp_growth,
                json.dumps(conditions.sector_performance or {}),
                json.dumps(conditions.global_events or []),
                now
            ))
            await self.db.connection.commit()
            return cursor.lastrowid

    async def save_analysis_performance(self, performance: AnalysisPerformance) -> int:
        """Save analysis performance metrics."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db.connection.execute("""
                INSERT INTO analysis_performance
                (symbol, recommendation_id, prediction_date, execution_date,
                 predicted_direction, actual_direction, predicted_return, actual_return,
                 accuracy_score, model_version, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                performance.symbol,
                performance.recommendation_id,
                performance.prediction_date,
                performance.execution_date,
                performance.predicted_direction,
                performance.actual_direction,
                performance.predicted_return,
                performance.actual_return,
                performance.accuracy_score,
                performance.model_version,
                now
            ))
            await self.db.connection.commit()
            return cursor.lastrowid

    async def get_last_analysis_timestamp(self, symbol: str) -> Optional[str]:
        """Get timestamp of last comprehensive analysis for stock.

        Args:
            symbol: Stock symbol

        Returns:
            ISO format timestamp of last analysis, or None if never analyzed
        """
        async with self._lock:
            async with self.db.connection.execute("""
                SELECT MAX(created_at) FROM recommendations
                WHERE symbol = ? AND analysis_type = 'comprehensive'
            """, (symbol,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] else None

    async def get_last_recommendation_timestamp(self, symbol: str) -> Optional[str]:
        """Get timestamp of last recommendation for stock.

        Args:
            symbol: Stock symbol

        Returns:
            ISO format timestamp of last recommendation, or None if no recommendations
        """
        async with self._lock:
            async with self.db.connection.execute("""
                SELECT MAX(created_at) FROM recommendations
                WHERE symbol = ?
                ORDER BY created_at DESC
                LIMIT 1
            """, (symbol,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row and row[0] else None

    async def get_stocks_needing_analysis(
        self,
        symbols: List[str],
        hours: int = 24
    ) -> List[str]:
        """Get stocks needing analysis (unanalyzed or older than N hours).

        Args:
            symbols: List of portfolio symbols
            hours: Minimum hours since last analysis (default 24)

        Returns:
            List of symbols needing analysis, prioritized by:
            1. Never analyzed (NULL timestamp)
            2. Oldest analysis (oldest timestamp first)
            3. Skipped if analyzed within hours
        """
        async with self._lock:
            if not symbols:
                return []

            # Calculate cutoff time
            from datetime import timedelta
            cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

            # Parameterized query with placeholders
            placeholders = ",".join("?" * len(symbols))
            query = f"""
                SELECT DISTINCT r.symbol
                FROM (
                    SELECT symbol, MAX(created_at) as last_analysis
                    FROM recommendations
                    WHERE symbol IN ({placeholders}) AND analysis_type = 'comprehensive'
                    GROUP BY symbol
                ) r
                RIGHT JOIN (
                    SELECT ? as symbol
                    UNION ALL
                    {' UNION ALL '.join([f"SELECT ?" for _ in range(len(symbols)-1)])}
                ) all_symbols ON r.symbol = all_symbols.symbol
                WHERE r.symbol IS NULL OR r.last_analysis < ?
                ORDER BY r.last_analysis ASC
            """

            # Build parameters: symbols for IN clause + all symbols again + cutoff time
            params = list(symbols) + symbols + [cutoff_time]

            stocks = []
            async with self.db.connection.execute(query, params) as cursor:
                async for row in cursor:
                    stocks.append(row[0])

            return stocks

    async def initialize_screening_tables(self) -> None:
        """Initialize screening and planning tables if they don't exist."""
        async with self._lock:
            await self.db.connection.executescript("""
                -- Screening Results Table
                CREATE TABLE IF NOT EXISTS screening_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    screening_type TEXT NOT NULL,
                    results_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Trading Plans Table
                CREATE TABLE IF NOT EXISTS trading_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_type TEXT NOT NULL,
                    plan_date TEXT NOT NULL,
                    plan_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_screening_results_type
                    ON screening_results(screening_type);
                CREATE INDEX IF NOT EXISTS idx_trading_plans_date
                    ON trading_plans(plan_date);
            """)
            await self.db.connection.commit()

    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> bool:
        """
        Update screening results in database.

        Args:
            results: Screening results dictionary

        Returns:
            True if successful, False otherwise
        """
        if results is None:
            return False

        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()
                screening_type = results.get("type", "default")

                # Upsert screening results
                await self.db.connection.execute("""
                    INSERT INTO screening_results (screening_type, results_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?)
                    ON CONFLICT(screening_type) DO UPDATE SET
                        results_data = excluded.results_data,
                        updated_at = excluded.updated_at
                """, (screening_type, json.dumps(results), now, now))
                await self.db.connection.commit()
                logger.debug(f"Updated screening results for type: {screening_type}")
                return True
            except Exception as e:
                logger.error(f"Failed to update screening results: {e}")
                return False

    async def get_screening_results(self, screening_type: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get screening results from database.

        Args:
            screening_type: Type of screening to retrieve

        Returns:
            Screening results dictionary or None
        """
        async with self._lock:
            try:
                async with self.db.connection.execute("""
                    SELECT results_data FROM screening_results
                    WHERE screening_type = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (screening_type,)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return json.loads(row[0])
                return None
            except Exception as e:
                logger.error(f"Failed to get screening results: {e}")
                return None

    async def save_daily_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Save daily trading plan to database.

        Args:
            plan: Daily plan dictionary

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()
                plan_date = plan.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))

                await self.db.connection.execute("""
                    INSERT INTO trading_plans (plan_type, plan_date, plan_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, ("daily", plan_date, json.dumps(plan), now, now))
                await self.db.connection.commit()
                logger.debug(f"Saved daily plan for date: {plan_date}")
                return True
            except Exception as e:
                logger.error(f"Failed to save daily plan: {e}")
                return False

    async def load_weekly_plan(self) -> Optional[Dict[str, Any]]:
        """
        Load current week's trading plan from database.

        Returns:
            Weekly plan dictionary or None
        """
        async with self._lock:
            try:
                # Get start of current week (Monday)
                from datetime import timedelta
                today = datetime.now(timezone.utc).date()
                week_start = today - timedelta(days=today.weekday())

                async with self.db.connection.execute("""
                    SELECT plan_data FROM trading_plans
                    WHERE plan_type = 'weekly' AND plan_date >= ?
                    ORDER BY plan_date DESC
                    LIMIT 1
                """, (week_start.isoformat(),)) as cursor:
                    row = await cursor.fetchone()
                    if row and row[0]:
                        return json.loads(row[0])
                return None
            except Exception as e:
                logger.error(f"Failed to load weekly plan: {e}")
                return None

    async def save_weekly_plan(self, plan: Dict[str, Any]) -> bool:
        """
        Save weekly trading plan to database.

        Args:
            plan: Weekly plan dictionary

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()
                # Get start of current week (Monday)
                from datetime import timedelta
                today = datetime.now(timezone.utc).date()
                week_start = today - timedelta(days=today.weekday())
                plan_date = plan.get("date", week_start.isoformat())

                await self.db.connection.execute("""
                    INSERT INTO trading_plans (plan_type, plan_date, plan_data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """, ("weekly", plan_date, json.dumps(plan), now, now))
                await self.db.connection.commit()
                logger.debug(f"Saved weekly plan for week starting: {plan_date}")
                return True
            except Exception as e:
                logger.error(f"Failed to save weekly plan: {e}")
                return False
