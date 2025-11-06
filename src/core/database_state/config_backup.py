"""Configuration backup and restore functionality."""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

from .base import DatabaseConnection


class ConfigBackupManager:
    """Manages configuration backups and restore operations."""

    def __init__(self, db_connection: DatabaseConnection, backup_dir: Path):
        """
        Initialize backup manager.

        Args:
            db_connection: Database connection instance
            backup_dir: Directory for backup files
        """
        self.db = db_connection
        self.backup_dir = backup_dir
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def create_backup(self, backup_type: str, identifier: str = "all") -> None:
        """
        Create a configuration backup.

        Args:
            backup_type: Type of backup (full, background_tasks, ai_agents, etc.)
            identifier: Identifier for the backup
        """
        async with self._lock:
            try:
                backup_data = await self._collect_backup_data(backup_type)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_file = (
                    self.backup_dir
                    / f"config_{backup_type}_{identifier}_{timestamp}.json"
                )

                # Write to file
                backup_file.write_text(json.dumps(backup_data, indent=2))

                # Store in database
                await self.db.connection.execute(
                    """
                    INSERT INTO configuration_backups (backup_type, backup_data, backup_file, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        backup_type,
                        json.dumps(backup_data),
                        str(backup_file),
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
                await self.db.connection.commit()

                logger.info(f"Created backup: {backup_file}")

            except Exception as e:
                logger.error(f"Failed to create backup for {backup_type}: {e}")

    async def _collect_backup_data(self, backup_type: str) -> Dict[str, Any]:
        """
        Collect data for backup.

        Args:
            backup_type: Type of backup

        Returns:
            Backup data dict
        """
        if backup_type == "background_tasks":
            cursor = await self.db.connection.execute(
                "SELECT * FROM background_tasks_config"
            )
        elif backup_type == "ai_agents":
            cursor = await self.db.connection.execute("SELECT * FROM ai_agents_config")
        elif backup_type == "global_settings":
            cursor = await self.db.connection.execute(
                "SELECT * FROM global_settings_config"
            )
        elif backup_type == "ai_prompts":
            cursor = await self.db.connection.execute("SELECT * FROM ai_prompts_config")
        else:  # Full backup
            return {
                "background_tasks": await self._get_table_data(
                    "background_tasks_config"
                ),
                "ai_agents": await self._get_table_data("ai_agents_config"),
                "global_settings": await self._get_table_data("global_settings_config"),
                "ai_prompts": await self._get_table_data("ai_prompts_config"),
            }

        rows = await cursor.fetchall()
        return {backup_type: [dict(row) for row in rows]}

    async def _get_table_data(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all data from a table."""
        cursor = await self.db.connection.execute(f"SELECT * FROM {table_name}")
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def get_backup_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get backup history.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup records
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """
                    SELECT id, backup_type, backup_file, created_at, created_by
                    FROM configuration_backups
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,),
                )
                rows = await cursor.fetchall()

                return [
                    {
                        "id": row[0],
                        "type": row[1],
                        "file": row[2],
                        "created_at": row[3],
                        "created_by": row[4],
                    }
                    for row in rows
                ]
            except Exception as e:
                logger.error(f"Failed to get backup history: {e}")
                return []

    async def restore_from_backup(self, backup_id: int) -> bool:
        """
        Restore configuration from backup.

        Args:
            backup_id: ID of the backup to restore

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT backup_type, backup_data FROM configuration_backups WHERE id = ?",
                    (backup_id,),
                )
                row = await cursor.fetchone()

                if not row:
                    logger.error(f"Backup {backup_id} not found")
                    return False

                backup_type = row[0]
                backup_data = json.loads(row[1])

                await self._restore_data(backup_type, backup_data)
                logger.info(f"Restored configuration from backup {backup_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to restore from backup {backup_id}: {e}")
                return False

    async def _restore_data(
        self, backup_type: str, backup_data: Dict[str, Any]
    ) -> None:
        """Restore data from backup."""
        if backup_type == "full":
            if "background_tasks" in backup_data:
                await self._restore_table(
                    "background_tasks_config", backup_data["background_tasks"]
                )
            if "ai_agents" in backup_data:
                await self._restore_table("ai_agents_config", backup_data["ai_agents"])
            if "global_settings" in backup_data:
                await self._restore_table(
                    "global_settings_config", backup_data["global_settings"]
                )
            if "ai_prompts" in backup_data:
                await self._restore_table(
                    "ai_prompts_config", backup_data["ai_prompts"]
                )
        else:
            table_map = {
                "background_tasks": "background_tasks_config",
                "ai_agents": "ai_agents_config",
                "global_settings": "global_settings_config",
                "ai_prompts": "ai_prompts_config",
            }
            if backup_type in table_map:
                await self._restore_table(
                    table_map[backup_type], backup_data.get(backup_type, [])
                )

    async def _restore_table(self, table_name: str, data: List[Dict[str, Any]]) -> None:
        """Restore data to a table."""
        # Clear existing data
        await self.db.connection.execute(f"DELETE FROM {table_name}")

        # Insert backup data
        if data and len(data) > 0:
            columns = list(data[0].keys())
            placeholders = ", ".join(["?" for _ in columns])
            column_names = ", ".join(columns)

            for row in data:
                values = [row[col] for col in columns]
                await self.db.connection.execute(
                    f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})",
                    values,
                )

        await self.db.connection.commit()
