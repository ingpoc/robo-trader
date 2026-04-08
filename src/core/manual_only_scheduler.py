"""Manual-only scheduler boundary for the active Robo Trader runtime.

This preserves compatibility for legacy scheduler call sites while making the
runtime explicitly manual-first and token-silent unless an operator triggers a
workflow directly.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger


class ManualOnlyScheduler:
    """Compatibility shim that disables autonomous scheduling."""

    def __init__(self, db_connection: Optional[Any] = None) -> None:
        self._db_connection = db_connection

    async def initialize(self) -> None:
        """Clear leftover non-terminal queue entries from legacy runtime flows."""
        if self._db_connection is None:
            return

        try:
            cursor = await self._db_connection.execute(
                "SELECT COUNT(*) FROM queue_tasks WHERE status IN ('pending', 'running')"
            )
            row = await cursor.fetchone()
            pending_or_running = int(row[0]) if row else 0
        except sqlite3.OperationalError as exc:
            if "no such table: queue_tasks" in str(exc).lower():
                logger.info(
                    "Manual-only runtime found no legacy queue_tasks table; "
                    "startup cleanup was skipped."
                )
                return
            raise

        if pending_or_running == 0:
            return

        await self._db_connection.execute(
            "DELETE FROM queue_tasks WHERE status IN ('pending', 'running')"
        )
        await self._db_connection.commit()

        logger.warning(
            f"Manual-only runtime cleared {pending_or_running} non-terminal "
            "legacy queue task(s) at startup."
        )

    async def start(self) -> List[Any]:
        logger.info(
            "Manual-only runtime: ignoring background scheduler start request; "
            "automatic execution is disabled."
        )
        return []

    async def stop(self) -> None:
        logger.info("Manual-only runtime: background scheduler stop request acknowledged.")

    async def trigger_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        logger.warning(
            "Manual-only runtime: ignoring automatic scheduler event '%s' with data %s.",
            event_type,
            event_data,
        )

    async def get_scheduler_status(self) -> Dict[str, Any]:
        checked_at = datetime.now(timezone.utc).isoformat()
        return {
            "status": "manual_only",
            "running": False,
            "active_jobs": 0,
            "completed_jobs": 0,
            "last_run_time": None,
            "mode": "manual_only",
            "checked_at": checked_at,
            "message": (
                "Legacy background schedulers are removed from the active runtime. "
                "AI and queue execution remain operator-triggered only."
            ),
        }
