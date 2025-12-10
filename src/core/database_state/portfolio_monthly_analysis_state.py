"""Portfolio Monthly Analysis State Management.

Manages monthly portfolio analysis data with proper locking.
Handles storage of analysis results for user's real portfolio.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from loguru import logger

from src.core.database_state.base import BaseState


class PortfolioMonthlyAnalysisState(BaseState):
    """
    Manages monthly portfolio analysis workflow data.

    Handles:
    - Monthly analysis of user's real portfolio stocks
    - Storage of fundamentals fetched from Perplexity API
    - Claude's KEEP/SELL recommendations
    - Analysis history and summaries
    """

    def __init__(self, db_connection):
        super().__init__(db_connection)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize portfolio analysis state (tables created in base.py)."""
        async with self._lock:
            logger.info("Portfolio Monthly Analysis State initialized")

    async def store_analysis(
        self,
        analysis_date: str,
        symbol: str,
        company_name: Optional[str] = None,
        sector: Optional[str] = None,
        industry: Optional[str] = None,
        fundamentals: Optional[Dict[str, Any]] = None,
        recent_earnings: Optional[Dict[str, Any]] = None,
        news_sentiment: Optional[Dict[str, Any]] = None,
        industry_trends: Optional[Dict[str, Any]] = None,
        recommendation: str = "KEEP",
        reasoning: str = "",
        confidence_score: float = 0.0,
        analysis_sources: Optional[List[str]] = None,
        price_at_analysis: Optional[float] = None,
        next_review_date: Optional[str] = None
    ) -> int:
        """
        Store portfolio analysis for a stock.

        Args:
            analysis_date: Date of analysis (YYYY-MM-DD)
            symbol: Stock symbol
            company_name: Company name
            sector: Sector
            industry: Industry
            fundamentals: Dictionary with fundamental metrics
            recent_earnings: Recent earnings data
            news_sentiment: News sentiment analysis
            industry_trends: Industry trends analysis
            recommendation: KEEP or SELL
            reasoning: Detailed reasoning for recommendation
            confidence_score: Confidence score (0-1)
            analysis_sources: List of sources used
            price_at_analysis: Price at time of analysis
            next_review_date: Next review date

        Returns:
            ID of inserted/updated record
        """
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            # Extract fundamentals if provided
            pe_ratio = fundamentals.get("pe_ratio") if fundamentals else None
            pb_ratio = fundamentals.get("pb_ratio") if fundamentals else None
            roe = fundamentals.get("roe") if fundamentals else None
            debt_to_equity = fundamentals.get("debt_to_equity") if fundamentals else None
            current_ratio = fundamentals.get("current_ratio") if fundamentals else None
            profit_margins = fundamentals.get("profit_margins") if fundamentals else None
            revenue_growth = fundamentals.get("revenue_growth") if fundamentals else None
            earnings_growth = fundamentals.get("earnings_growth") if fundamentals else None
            dividend_yield = fundamentals.get("dividend_yield") if fundamentals else None
            market_cap = fundamentals.get("market_cap") if fundamentals else None

            cursor = await self.db.connection.execute("""
                INSERT OR REPLACE INTO portfolio_analysis (
                    analysis_date, symbol, company_name, sector, industry,
                    pe_ratio, pb_ratio, roe, debt_to_equity, current_ratio,
                    profit_margins, revenue_growth, earnings_growth, dividend_yield, market_cap,
                    recent_earnings, news_sentiment, industry_trends,
                    recommendation, reasoning, confidence_score,
                    analysis_sources, price_at_analysis, next_review_date,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_date, symbol, company_name, sector, industry,
                pe_ratio, pb_ratio, roe, debt_to_equity, current_ratio,
                profit_margins, revenue_growth, earnings_growth, dividend_yield, market_cap,
                json.dumps(recent_earnings) if recent_earnings else None,
                json.dumps(news_sentiment) if news_sentiment else None,
                json.dumps(industry_trends) if industry_trends else None,
                recommendation, reasoning, confidence_score,
                json.dumps(analysis_sources) if analysis_sources else None,
                price_at_analysis, next_review_date,
                now, now
            ))

            await self.db.connection.commit()
            return cursor.lastrowid

    async def get_analysis(
        self,
        symbol: Optional[str] = None,
        analysis_date: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get portfolio analysis records.

        Args:
            symbol: Filter by symbol (optional)
            analysis_date: Filter by date (optional)
            limit: Maximum number of records to return

        Returns:
            List of analysis records
        """
        async with self._lock:
            query = "SELECT * FROM portfolio_analysis WHERE 1=1"
            params = []

            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)

            if analysis_date:
                query += " AND analysis_date = ?"
                params.append(analysis_date)

            query += " ORDER BY analysis_date DESC, symbol"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = await self.db.connection.execute(query, params)
            rows = await cursor.fetchall()

            # Convert to dict and parse JSON fields
            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in rows:
                record = dict(zip(columns, row))
                # Parse JSON fields
                for field in ["recent_earnings", "news_sentiment", "industry_trends", "analysis_sources"]:
                    if record[field]:
                        record[field] = json.loads(record[field])
                results.append(record)

            return results

    async def get_latest_analysis_for_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent analysis for a symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Latest analysis record or None
        """
        async with self._lock:
            cursor = await self.db.connection.execute("""
                SELECT * FROM portfolio_analysis
                WHERE symbol = ?
                ORDER BY analysis_date DESC
                LIMIT 1
            """, (symbol,))

            row = await cursor.fetchone()
            if not row:
                return None

            # Convert to dict and parse JSON fields
            columns = [desc[0] for desc in cursor.description]
            record = dict(zip(columns, row))

            # Parse JSON fields
            for field in ["recent_earnings", "news_sentiment", "industry_trends", "analysis_sources"]:
                if record[field]:
                    record[field] = json.loads(record[field])

            return record

    async def store_monthly_summary(
        self,
        analysis_month: str,
        total_stocks: int,
        keep_count: int,
        sell_count: int,
        portfolio_value: Optional[float] = None,
        market_conditions: Optional[Dict[str, Any]] = None,
        analysis_duration: Optional[float] = None,
        perplexity_calls: int = 0,
        claude_tokens: int = 0
    ) -> int:
        """
        Store monthly analysis summary.

        Args:
            analysis_month: Month in YYYY-MM format
            total_stocks: Total number of stocks analyzed
            keep_count: Number of KEEP recommendations
            sell_count: Number of SELL recommendations
            portfolio_value: Portfolio value at time of analysis
            market_conditions: Market conditions snapshot
            analysis_duration: Duration of analysis in seconds
            perplexity_calls: Number of Perplexity API calls made
            claude_tokens: Number of Claude tokens used

        Returns:
            ID of inserted/updated record
        """
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db.connection.execute("""
                INSERT OR REPLACE INTO monthly_analysis_summary (
                    analysis_month, total_stocks_analyzed, keep_recommendations,
                    sell_recommendations, portfolio_value_at_analysis,
                    market_conditions, analysis_duration_seconds,
                    perplexity_api_calls, claude_analysis_tokens,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis_month, total_stocks, keep_count, sell_count,
                portfolio_value,
                json.dumps(market_conditions) if market_conditions else None,
                analysis_duration, perplexity_calls, claude_tokens,
                now, now
            ))

            await self.db.connection.commit()
            return cursor.lastrowid

    async def get_monthly_summary(
        self,
        analysis_month: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get monthly analysis summaries.

        Args:
            analysis_month: Filter by month (optional)
            limit: Maximum number of records to return

        Returns:
            List of monthly summaries
        """
        async with self._lock:
            query = "SELECT * FROM monthly_analysis_summary WHERE 1=1"
            params = []

            if analysis_month:
                query += " AND analysis_month = ?"
                params.append(analysis_month)

            query += " ORDER BY analysis_month DESC"

            if limit:
                query += " LIMIT ?"
                params.append(limit)

            cursor = await self.db.connection.execute(query, params)
            rows = await cursor.fetchall()

            # Convert to dict and parse JSON fields
            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in rows:
                record = dict(zip(columns, row))
                # Parse JSON fields
                if record["market_conditions"]:
                    record["market_conditions"] = json.loads(record["market_conditions"])
                results.append(record)

            return results

    async def get_analysis_statistics(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get analysis statistics for a date range.

        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)

        Returns:
            Dictionary with analysis statistics
        """
        async with self._lock:
            query = """
                SELECT
                    COUNT(*) as total_analyses,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    COUNT(DISTINCT analysis_date) as analysis_days,
                    SUM(CASE WHEN recommendation = 'KEEP' THEN 1 ELSE 0 END) as keep_count,
                    SUM(CASE WHEN recommendation = 'SELL' THEN 1 ELSE 0 END) as sell_count,
                    AVG(confidence_score) as avg_confidence,
                    MIN(analysis_date) as first_analysis,
                    MAX(analysis_date) as last_analysis
                FROM portfolio_analysis
                WHERE 1=1
            """
            params = []

            if start_date:
                query += " AND analysis_date >= ?"
                params.append(start_date)

            if end_date:
                query += " AND analysis_date <= ?"
                params.append(end_date)

            cursor = await self.db.connection.execute(query, params)
            row = await cursor.fetchone()

            if row:
                return {
                    "total_analyses": row[0],
                    "unique_symbols": row[1],
                    "analysis_days": row[2],
                    "keep_recommendations": row[3],
                    "sell_recommendations": row[4],
                    "avg_confidence": row[5],
                    "first_analysis": row[6],
                    "last_analysis": row[7],
                    "keep_percentage": (row[3] / row[0] * 100) if row[0] > 0 else 0
                }

            return {
                "total_analyses": 0,
                "unique_symbols": 0,
                "analysis_days": 0,
                "keep_recommendations": 0,
                "sell_recommendations": 0,
                "avg_confidence": 0,
                "first_analysis": None,
                "last_analysis": None,
                "keep_percentage": 0
            }