"""
Shadow-Live Mode

Runs feature extraction + scoring in real-time but does NOT execute trades.
Records what the system *would* have done for comparison against actual market outcomes.

This is the proving ground before enabling autonomous execution.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class ShadowLiveService:
    """
    Shadow-live mode: generates signals without execution.

    Records decisions to a shadow ledger for later comparison with actual
    market outcomes. This validates the strategy without risking capital.
    """

    def __init__(self, research_ledger_store, trade_lifecycle_store, db_connection=None):
        self.ledger_store = research_ledger_store
        self.lifecycle_store = trade_lifecycle_store
        self.db_connection = db_connection
        self._lock = asyncio.Lock()
        self._running = False

    async def initialize(self) -> None:
        """Initialize shadow live schema."""
        if self.db_connection:
            async with self._lock:
                await self.db_connection.execute("""
                    CREATE TABLE IF NOT EXISTS shadow_decisions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        symbol TEXT NOT NULL,
                        decision_timestamp TEXT NOT NULL,
                        action TEXT NOT NULL,
                        score REAL,
                        entry_price REAL,
                        expected_stop REAL,
                        expected_target REAL,
                        feature_confidence REAL,
                        outcome_checked BOOLEAN DEFAULT 0,
                        outcome_price REAL,
                        outcome_pnl_pct REAL,
                        outcome_timestamp TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                await self.db_connection.execute("""
                    CREATE INDEX IF NOT EXISTS idx_shadow_symbol
                    ON shadow_decisions(symbol, decision_timestamp DESC)
                """)
                await self.db_connection.commit()
        logger.info("ShadowLiveService initialized")

    async def record_shadow_decision(
        self,
        symbol: str,
        action: str,
        score: float,
        entry_price: float,
        stop_loss_pct: float = 8.0,
        take_profit_pct: float = 15.0,
        feature_confidence: float = 0.0,
    ) -> bool:
        """Record a shadow decision (what we would have done)."""
        if not self.db_connection:
            logger.warning("No DB connection for shadow decisions")
            return False

        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()
                stop = entry_price * (1 - stop_loss_pct / 100)
                target = entry_price * (1 + take_profit_pct / 100)

                await self.db_connection.execute(
                    """INSERT INTO shadow_decisions
                       (symbol, decision_timestamp, action, score, entry_price,
                        expected_stop, expected_target, feature_confidence, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, now, action, score, entry_price, stop, target, feature_confidence, now),
                )
                await self.db_connection.commit()
                logger.info(f"Shadow decision: {action} {symbol} @ {entry_price}, score={score}")
                return True
            except Exception as e:
                logger.error(f"Failed to record shadow decision: {e}")
                return False

    async def check_outcomes(
        self,
        current_prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        """
        Check outcomes of unchecked shadow decisions against current prices.

        Returns list of resolved decisions with outcome data.
        """
        if not self.db_connection:
            return []

        resolved = []
        async with self._lock:
            try:
                cursor = await self.db_connection.execute(
                    """SELECT id, symbol, action, entry_price, expected_stop,
                              expected_target, score, feature_confidence
                       FROM shadow_decisions
                       WHERE outcome_checked = 0 AND action = 'BUY'"""
                )
                rows = await cursor.fetchall()

                now = datetime.now(timezone.utc).isoformat()
                for row in rows:
                    id_, symbol, action, entry, stop, target, score, confidence = row
                    current = current_prices.get(symbol)
                    if current is None:
                        continue

                    # Check if stop or target hit
                    if current <= stop or current >= target:
                        pnl_pct = ((current - entry) / entry) * 100 if entry else 0

                        await self.db_connection.execute(
                            """UPDATE shadow_decisions
                               SET outcome_checked = 1, outcome_price = ?,
                                   outcome_pnl_pct = ?, outcome_timestamp = ?
                               WHERE id = ?""",
                            (current, pnl_pct, now, id_),
                        )

                        resolved.append({
                            "symbol": symbol,
                            "action": action,
                            "entry_price": entry,
                            "outcome_price": current,
                            "pnl_pct": round(pnl_pct, 2),
                            "score": score,
                            "result": "win" if pnl_pct > 0 else "loss",
                        })

                await self.db_connection.commit()
            except Exception as e:
                logger.error(f"Failed to check shadow outcomes: {e}")

        return resolved

    async def get_shadow_report(self, days: int = 7) -> Dict[str, Any]:
        """Get a summary of shadow-live performance."""
        if not self.db_connection:
            return {"error": "No DB connection"}

        async with self._lock:
            try:
                # Total decisions
                cursor = await self.db_connection.execute(
                    "SELECT COUNT(*) FROM shadow_decisions WHERE action = 'BUY'"
                )
                total = (await cursor.fetchone())[0]

                # Resolved decisions
                cursor = await self.db_connection.execute(
                    "SELECT COUNT(*), AVG(outcome_pnl_pct) FROM shadow_decisions WHERE outcome_checked = 1"
                )
                row = await cursor.fetchone()
                resolved_count = row[0]
                avg_pnl = row[1] or 0.0

                # Win/loss
                cursor = await self.db_connection.execute(
                    "SELECT COUNT(*) FROM shadow_decisions WHERE outcome_checked = 1 AND outcome_pnl_pct > 0"
                )
                wins = (await cursor.fetchone())[0]

                return {
                    "total_shadow_decisions": total,
                    "resolved": resolved_count,
                    "pending": total - resolved_count,
                    "wins": wins,
                    "losses": resolved_count - wins,
                    "win_rate_pct": round(wins / resolved_count * 100, 1) if resolved_count else 0,
                    "avg_pnl_pct": round(avg_pnl, 2),
                }
            except Exception as e:
                logger.error(f"Failed to get shadow report: {e}")
                return {"error": str(e)}
