"""
News and earnings data management for Robo Trader.

Consolidated manager for news items, earnings reports, and fetch tracking.
"""

import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from loguru import logger

from .base import DatabaseConnection


class NewsEarningsStateManager:
    """
    Manages news and earnings data with database persistence.

    Responsibilities:
    - Save/retrieve news items
    - Save/retrieve earnings reports
    - Track last fetch times per symbol
    - Query upcoming earnings
    """

    def __init__(self, db: DatabaseConnection):
        self.db = db
        self._lock = asyncio.Lock()

    async def save_news_item(
        self,
        symbol: str,
        title: str,
        summary: str,
        content: Optional[str] = None,
        source: Optional[str] = None,
        sentiment: str = "neutral",
        relevance_score: float = 0.5,
        published_at: Optional[str] = None,
        citations: Optional[List] = None
    ) -> None:
        """Save news item to database."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            published = published_at or now

            async with self.db.connection.execute("""
                INSERT INTO news_items
                (symbol, title, summary, content, source, sentiment, relevance_score,
                 published_at, fetched_at, citations, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (symbol, title, summary, content, source, sentiment, relevance_score,
                  published, now, json.dumps(citations or []), now)):
                await self.db.connection.commit()

    async def save_earnings_report(
        self,
        symbol: str,
        fiscal_period: str,
        report_date: str,
        **kwargs
    ) -> None:
        """Save earnings report to database."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            async with self.db.connection.execute("""
                INSERT OR REPLACE INTO earnings_reports
                (symbol, fiscal_period, fiscal_year, fiscal_quarter, report_date,
                 eps_actual, eps_estimated, revenue_actual, revenue_estimated,
                 surprise_pct, guidance, next_earnings_date, fetched_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                symbol, fiscal_period,
                kwargs.get('fiscal_year'), kwargs.get('fiscal_quarter'),
                report_date,
                kwargs.get('eps_actual'), kwargs.get('eps_estimated'),
                kwargs.get('revenue_actual'), kwargs.get('revenue_estimated'),
                kwargs.get('surprise_pct'), kwargs.get('guidance'),
                kwargs.get('next_earnings_date'), now, now
            )):
                await self.db.connection.commit()

    async def get_news_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Get recent news for symbol."""
        async with self._lock:
            news_items = []
            async with self.db.connection.execute("""
                SELECT * FROM news_items
                WHERE symbol = ?
                ORDER BY published_at DESC
                LIMIT ?
            """, (symbol, limit)) as cursor:
                async for row in cursor:
                    news_items.append({
                        "id": row[0],
                        "symbol": row[1],
                        "title": row[2],
                        "summary": row[3],
                        "content": row[4],
                        "source": row[5],
                        "sentiment": row[6],
                        "relevance_score": row[7],
                        "published_at": row[8],
                        "fetched_at": row[9],
                        "citations": json.loads(row[10]) if row[10] else [],
                        "created_at": row[11]
                    })
            return news_items

    async def get_earnings_for_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get earnings reports for symbol."""
        async with self._lock:
            earnings = []
            async with self.db.connection.execute("""
                SELECT * FROM earnings_reports
                WHERE symbol = ?
                ORDER BY report_date DESC
                LIMIT ?
            """, (symbol, limit)) as cursor:
                async for row in cursor:
                    earnings.append({
                        "id": row[0],
                        "symbol": row[1],
                        "fiscal_period": row[2],
                        "fiscal_year": row[3],
                        "fiscal_quarter": row[4],
                        "report_date": row[5],
                        "eps_actual": row[6],
                        "eps_estimated": row[7],
                        "revenue_actual": row[8],
                        "revenue_estimated": row[9],
                        "surprise_pct": row[10],
                        "guidance": row[11],
                        "next_earnings_date": row[12],
                        "fetched_at": row[13],
                        "created_at": row[14]
                    })
            return earnings

    async def get_upcoming_earnings(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming earnings in next N days."""
        async with self._lock:
            cutoff = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()
            earnings = []
            async with self.db.connection.execute("""
                SELECT * FROM earnings_reports
                WHERE next_earnings_date IS NOT NULL
                AND next_earnings_date <= ?
                ORDER BY next_earnings_date ASC
            """, (cutoff,)) as cursor:
                async for row in cursor:
                    earnings.append({
                        "symbol": row[1],
                        "next_earnings_date": row[12],
                        "last_eps": row[6],
                        "last_revenue": row[8]
                    })
            return earnings

    async def update_last_news_fetch(
        self,
        symbol: str,
        fetch_time: Optional[str] = None
    ) -> None:
        """Update last news fetch timestamp for symbol."""
        async with self._lock:
            now = fetch_time or datetime.now(timezone.utc).isoformat()
            async with self.db.connection.execute("""
                INSERT OR REPLACE INTO news_fetch_tracking
                (symbol, last_news_fetch, created_at, updated_at)
                VALUES (?, ?, ?, ?)
            """, (symbol, now, now, now)):
                await self.db.connection.commit()

    async def get_last_news_fetch(self, symbol: str) -> Optional[str]:
        """Get last news fetch timestamp for symbol."""
        async with self._lock:
            async with self.db.connection.execute("""
                SELECT last_news_fetch FROM news_fetch_tracking WHERE symbol = ?
            """, (symbol,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else None
