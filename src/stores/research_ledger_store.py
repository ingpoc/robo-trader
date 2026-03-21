"""
Research Ledger Store

Persists structured feature extraction results for audit, replay, and evaluation.
Follows PaperTradingStore pattern with asyncio.Lock().
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

import aiosqlite

logger = logging.getLogger(__name__)


class ResearchLedgerStore:
    """Async store for research ledger entries."""

    def __init__(self, db_connection):
        """Initialize store with database connection."""
        self.db_connection = db_connection
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the store schema."""
        await self.initialize_schema()

    async def initialize_schema(self) -> None:
        """Create the research_ledger table if it doesn't exist."""
        async with self._lock:
            db = self.db_connection
            await db.execute("""
                CREATE TABLE IF NOT EXISTS research_ledger (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    score REAL,
                    action TEXT,
                    feature_confidence REAL,
                    sources_json TEXT,
                    extraction_model TEXT,
                    extraction_duration_ms INTEGER,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_research_ledger_symbol
                ON research_ledger(symbol, timestamp DESC)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_research_ledger_action
                ON research_ledger(action, timestamp DESC)
            """)
            await db.commit()
            logger.info("Research ledger schema initialized")

    async def store_entry(self, entry_dict: Dict[str, Any]) -> bool:
        """
        Store a research ledger entry.

        Args:
            entry_dict: Output of ResearchLedgerEntry.to_store_dict()
        """
        async with self._lock:
            try:
                db = self.db_connection
                await db.execute(
                    """INSERT OR REPLACE INTO research_ledger
                       (id, symbol, timestamp, features_json, score, action,
                        feature_confidence, sources_json, extraction_model,
                        extraction_duration_ms, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        entry_dict["id"],
                        entry_dict["symbol"],
                        entry_dict["timestamp"],
                        entry_dict["features_json"],
                        entry_dict.get("score"),
                        entry_dict.get("action"),
                        entry_dict.get("feature_confidence"),
                        json.dumps(entry_dict.get("sources", [])),
                        entry_dict.get("extraction_model"),
                        entry_dict.get("extraction_duration_ms"),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to store research ledger entry: {e}")
                return False

    async def get_latest(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get the most recent research ledger entry for a symbol."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT id, symbol, timestamp, features_json, score, action,
                              feature_confidence, sources_json, extraction_model
                       FROM research_ledger
                       WHERE symbol = ?
                       ORDER BY timestamp DESC LIMIT 1""",
                    (symbol,),
                )
                row = await cursor.fetchone()
                if row:
                    return _row_to_dict(row)
                return None
            except Exception as e:
                logger.error(f"Failed to get latest entry for {symbol}: {e}")
                return None

    async def get_history(
        self, symbol: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent research ledger entries for a symbol."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT id, symbol, timestamp, features_json, score, action,
                              feature_confidence, sources_json, extraction_model
                       FROM research_ledger
                       WHERE symbol = ?
                       ORDER BY timestamp DESC LIMIT ?""",
                    (symbol, limit),
                )
                rows = await cursor.fetchall()
                return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to get history for {symbol}: {e}")
                return []

    async def get_all_latest(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get the most recent entry for each symbol."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT r.id, r.symbol, r.timestamp, r.features_json, r.score,
                              r.action, r.feature_confidence, r.sources_json, r.extraction_model
                       FROM research_ledger r
                       INNER JOIN (
                           SELECT symbol, MAX(timestamp) as max_ts
                           FROM research_ledger
                           GROUP BY symbol
                       ) latest ON r.symbol = latest.symbol AND r.timestamp = latest.max_ts
                       ORDER BY r.score DESC
                       LIMIT ?""",
                    (limit,),
                )
                rows = await cursor.fetchall()
                return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to get all latest entries: {e}")
                return []

    async def get_buy_candidates(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent BUY-action entries, ordered by score."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT id, symbol, timestamp, features_json, score, action,
                              feature_confidence, sources_json, extraction_model
                       FROM research_ledger
                       WHERE action = 'BUY'
                       ORDER BY score DESC, timestamp DESC
                       LIMIT ?""",
                    (limit,),
                )
                rows = await cursor.fetchall()
                return [_row_to_dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to get buy candidates: {e}")
                return []


def _row_to_dict(row) -> Dict[str, Any]:
    """Convert a database row to a dict."""
    return {
        "id": row[0],
        "symbol": row[1],
        "timestamp": row[2],
        "features": json.loads(row[3]) if row[3] else {},
        "score": row[4],
        "action": row[5],
        "feature_confidence": row[6],
        "sources": json.loads(row[7]) if row[7] else [],
        "extraction_model": row[8],
    }
