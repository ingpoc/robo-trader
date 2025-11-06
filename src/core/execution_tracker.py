"""
Execution Tracker Service

Tracks detailed execution information for all schedulers and processors,
including success/failure status, symbols processed, and execution timing.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from loguru import logger


class ExecutionTracker:
    """Tracks detailed execution information for schedulers and processors."""

    def __init__(self, db_connection):
        """Initialize execution tracker with database connection."""
        self.db = db_connection
        self._lock = asyncio.Lock()
        self._max_history = 100  # Keep last 100 executions

    async def initialize(self) -> None:
        """Initialize the execution tracker database table."""
        async with self._lock:
            await self.db.execute(
                """
                CREATE TABLE IF NOT EXISTS execution_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_name TEXT NOT NULL,
                    task_id TEXT,
                    execution_type TEXT NOT NULL DEFAULT 'scheduled', -- 'manual' or 'scheduled'
                    user TEXT NOT NULL DEFAULT 'system',
                    timestamp TEXT NOT NULL,
                    symbols TEXT, -- JSON array of symbols
                    symbol_count INTEGER DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'completed', -- 'completed', 'failed', 'running'
                    error_message TEXT,
                    execution_time_seconds REAL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Create index for performance
            await self.db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_execution_history_timestamp
                ON execution_history(timestamp DESC)
            """
            )

            await self.db.commit()
            logger.info("Execution tracker initialized")

    async def record_execution(
        self,
        task_name: str,
        task_id: str = "",
        execution_type: str = "scheduled",
        user: str = "system",
        symbols: List[str] = None,
        status: str = "completed",
        error_message: str = None,
        execution_time: float = None,
    ) -> None:
        """Record a detailed execution."""
        async with self._lock:
            try:
                # Prepare data
                symbols_json = json.dumps(symbols) if symbols else None
                symbol_count = len(symbols) if symbols else 0

                await self.db.execute(
                    """
                    INSERT INTO execution_history
                    (task_name, task_id, execution_type, user, timestamp, symbols,
                     symbol_count, status, error_message, execution_time_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        task_name,
                        task_id,
                        execution_type,
                        user,
                        datetime.now(timezone.utc).isoformat(),
                        symbols_json,
                        symbol_count,
                        status,
                        error_message,
                        execution_time,
                    ),
                )

                # Clean up old records (keep only recent ones)
                await self.db.execute(
                    """
                    DELETE FROM execution_history
                    WHERE id NOT IN (
                        SELECT id FROM execution_history
                        ORDER BY timestamp DESC
                        LIMIT ?
                    )
                """,
                    (self._max_history,),
                )

                await self.db.commit()

                symbol_info = f"{symbol_count} symbols" if symbols else "no symbols"
                logger.info(
                    f"📊 EXECUTION TRACKER: Recorded {execution_type} execution: {task_name} ({task_id or 'no-id'}) by {user} - {symbol_info}, status: {status}, time: {execution_time:.2f}s"
                    if execution_time
                    else f"📊 EXECUTION TRACKER: Recorded {execution_type} execution: {task_name} ({task_id or 'no-id'}) by {user} - {symbol_info}, status: {status}"
                )
                logger.info(
                    f"📊 EXECUTION TRACKER: Database insert completed for {task_name}"
                )

            except Exception as e:
                logger.error(f"Failed to record execution: {e}")

    async def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent execution history."""
        async with self._lock:
            try:
                cursor = await self.db.execute(
                    """
                    SELECT task_name, task_id, execution_type, user, timestamp,
                           symbols, symbol_count, status, error_message, execution_time_seconds
                    FROM execution_history
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (limit,),
                )

                rows = await cursor.fetchall()
                executions = []

                for row in rows:
                    symbols = json.loads(row[5]) if row[5] else []
                    executions.append(
                        {
                            "task_name": row[0],
                            "task_id": row[1],
                            "execution_type": row[2],
                            "user": row[3],
                            "timestamp": row[4],
                            "symbols": symbols,
                            "symbol_count": row[6],
                            "status": row[7],
                            "error_message": row[8],
                            "execution_time_seconds": row[9],
                        }
                    )

                return executions

            except Exception as e:
                logger.error(f"Failed to get execution history: {e}")
                return []

    async def get_executions_by_task(
        self, task_name: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get execution history for a specific task."""
        async with self._lock:
            try:
                cursor = await self.db.execute(
                    """
                    SELECT task_name, task_id, execution_type, user, timestamp,
                           symbols, symbol_count, status, error_message, execution_time_seconds
                    FROM execution_history
                    WHERE task_name = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (task_name, limit),
                )

                rows = await cursor.fetchall()
                executions = []

                for row in rows:
                    symbols = json.loads(row[5]) if row[5] else []
                    executions.append(
                        {
                            "task_name": row[0],
                            "task_id": row[1],
                            "execution_type": row[2],
                            "user": row[3],
                            "timestamp": row[4],
                            "symbols": symbols,
                            "symbol_count": row[6],
                            "status": row[7],
                            "error_message": row[8],
                            "execution_time_seconds": row[9],
                        }
                    )

                return executions

            except Exception as e:
                logger.error(f"Failed to get executions for task {task_name}: {e}")
                return []

    async def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        async with self._lock:
            try:
                # Get total counts
                cursor = await self.db.execute(
                    """
                    SELECT
                        COUNT(*) as total_executions,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as successful_executions,
                        COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed_executions,
                        COUNT(CASE WHEN execution_type = 'manual' THEN 1 END) as manual_executions,
                        COUNT(CASE WHEN execution_type = 'scheduled' THEN 1 END) as scheduled_executions,
                        SUM(symbol_count) as total_symbols_processed,
                        AVG(execution_time_seconds) as avg_execution_time
                    FROM execution_history
                """
                )

                row = await cursor.fetchone()

                # Get recent executions by task
                cursor = await self.db.execute(
                    """
                    SELECT task_name, COUNT(*) as count
                    FROM execution_history
                    WHERE timestamp > datetime('now', '-24 hours')
                    GROUP BY task_name
                    ORDER BY count DESC
                """
                )

                recent_by_task = await cursor.fetchall()

                return {
                    "total_executions": row[0],
                    "successful_executions": row[1],
                    "failed_executions": row[2],
                    "manual_executions": row[3],
                    "scheduled_executions": row[4],
                    "total_symbols_processed": row[5] or 0,
                    "average_execution_time": row[6] or 0,
                    "recent_executions_by_task": dict(recent_by_task),
                }

            except Exception as e:
                logger.error(f"Failed to get execution stats: {e}")
                return {}
