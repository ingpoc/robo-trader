"""
Trade Lifecycle Store

Tracks the full lifecycle of a trade decision:
  research_decision -> intended_order -> submitted_order -> fill_or_reject

Each stage is a timestamped row for complete audit trail and divergence analysis.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)


class TradeLifecycleStore:
    """Async store for trade lifecycle events."""

    def __init__(self, db_connection):
        self.db_connection = db_connection
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the store schema."""
        await self.initialize_schema()

    async def initialize_schema(self) -> None:
        """Create the trade_lifecycle table."""
        async with self._lock:
            db = self.db_connection
            await db.execute("""
                CREATE TABLE IF NOT EXISTS trade_lifecycle (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_ref_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    stage TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    data_json TEXT,
                    created_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_lifecycle_ref
                ON trade_lifecycle(trade_ref_id, stage)
            """)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_lifecycle_symbol
                ON trade_lifecycle(symbol, timestamp DESC)
            """)
            await db.commit()
            logger.info("Trade lifecycle schema initialized")

    async def record_stage(
        self,
        trade_ref_id: str,
        symbol: str,
        stage: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Record a lifecycle stage for a trade.

        Stages:
        - research_decision: Feature extraction + scoring completed
        - intended_order: System decided to place an order
        - submitted_order: Order submitted to execution
        - filled: Order filled
        - rejected: Order rejected
        - blocked: Order blocked by guard (stale data, risk limit, etc.)
        """
        async with self._lock:
            try:
                db = self.db_connection
                now = datetime.now(timezone.utc).isoformat()
                await db.execute(
                    """INSERT INTO trade_lifecycle
                       (trade_ref_id, symbol, stage, timestamp, data_json, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (trade_ref_id, symbol, stage, now, json.dumps(data or {}), now),
                )
                await db.commit()
                return True
            except Exception as e:
                logger.error(f"Failed to record lifecycle stage: {e}")
                return False

    async def get_lifecycle(self, trade_ref_id: str) -> List[Dict[str, Any]]:
        """Get all lifecycle stages for a trade reference."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT trade_ref_id, symbol, stage, timestamp, data_json
                       FROM trade_lifecycle
                       WHERE trade_ref_id = ?
                       ORDER BY timestamp ASC""",
                    (trade_ref_id,),
                )
                rows = await cursor.fetchall()
                return [
                    {
                        "trade_ref_id": r[0],
                        "symbol": r[1],
                        "stage": r[2],
                        "timestamp": r[3],
                        "data": json.loads(r[4]) if r[4] else {},
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.error(f"Failed to get lifecycle for {trade_ref_id}: {e}")
                return []

    async def get_recent_by_symbol(
        self, symbol: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get recent lifecycle events for a symbol."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT trade_ref_id, symbol, stage, timestamp, data_json
                       FROM trade_lifecycle
                       WHERE symbol = ?
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (symbol, limit),
                )
                rows = await cursor.fetchall()
                return [
                    {
                        "trade_ref_id": r[0],
                        "symbol": r[1],
                        "stage": r[2],
                        "timestamp": r[3],
                        "data": json.loads(r[4]) if r[4] else {},
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.error(f"Failed to get lifecycle for {symbol}: {e}")
                return []

    async def get_blocked_trades(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent blocked trades for divergence analysis."""
        async with self._lock:
            try:
                db = self.db_connection
                cursor = await db.execute(
                    """SELECT trade_ref_id, symbol, stage, timestamp, data_json
                       FROM trade_lifecycle
                       WHERE stage = 'blocked'
                       ORDER BY timestamp DESC
                       LIMIT ?""",
                    (limit,),
                )
                rows = await cursor.fetchall()
                return [
                    {
                        "trade_ref_id": r[0],
                        "symbol": r[1],
                        "stage": r[2],
                        "timestamp": r[3],
                        "data": json.loads(r[4]) if r[4] else {},
                    }
                    for r in rows
                ]
            except Exception as e:
                logger.error(f"Failed to get blocked trades: {e}")
                return []
