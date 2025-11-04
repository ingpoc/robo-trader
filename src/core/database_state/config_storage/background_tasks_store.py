"""Background tasks configuration store."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger

from .base_store import BaseConfigStore


class BackgroundTasksStore(BaseConfigStore):
    """Manages background tasks configuration in database."""

    async def get(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Get background task configuration by name.

        Args:
            task_name: Name of the background task

        Returns:
            Task configuration dict or None if not found
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM background_tasks_config WHERE task_name = ?",
                    (task_name,)
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "task_name": row["task_name"],
                        "enabled": bool(row["enabled"]),
                        "frequency": row["frequency_seconds"],
                        "frequency_unit": row["frequency_unit"],
                        "use_claude": bool(row["use_claude"]),
                        "priority": row["priority"],
                    }
                return None
            except Exception as e:
                self._log_error(f"get({task_name})", e)
                return None

    async def get_all(self) -> Dict[str, Any]:
        """
        Get all background tasks configuration.

        Returns:
            Dict with all background tasks configuration
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM background_tasks_config ORDER BY priority DESC, task_name"
                )
                rows = await cursor.fetchall()

                background_tasks = {}
                for row in rows:
                    background_tasks[row[1]] = {
                        "enabled": bool(row[2]),
                        "frequency": row[3],
                        "frequencyUnit": row[4],
                        "useClaude": bool(row[5]),
                        "priority": row[6]
                    }

                return {"background_tasks": background_tasks}
            except Exception as e:
                self._log_error("get_all", e)
                return {"background_tasks": {}}

    async def update(self, task_name: str, config_data: Dict[str, Any]) -> bool:
        """
        Update background task configuration.

        Args:
            task_name: Name of the background task
            config_data: Configuration data to update

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                # Convert frequency to seconds
                frequency_seconds = config_data.get("frequency", 3600)
                frequency_unit = config_data.get("frequency_unit", "seconds")

                if frequency_unit == "minutes":
                    frequency_seconds = frequency_seconds * 60
                elif frequency_unit == "hours":
                    frequency_seconds = frequency_seconds * 3600
                elif frequency_unit == "days":
                    frequency_seconds = frequency_seconds * 86400

                now = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """
                    INSERT OR REPLACE INTO background_tasks_config
                    (task_name, enabled, frequency_seconds, frequency_unit, use_claude, priority, updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, COALESCE(
                        (SELECT created_at FROM background_tasks_config WHERE task_name = ?), ?
                    ))
                    """,
                    (
                        task_name,
                        config_data.get("enabled", False),
                        frequency_seconds,
                        frequency_unit,
                        config_data.get("use_claude", True),
                        config_data.get("priority", "medium"),
                        now,
                        task_name,
                        now
                    )
                )

                await self.db.connection.commit()
                logger.info(f"Updated background task configuration for {task_name}")
                return True

            except Exception as e:
                self._log_error(f"update({task_name})", e)
                return False
