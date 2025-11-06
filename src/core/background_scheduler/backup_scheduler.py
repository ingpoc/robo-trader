"""
Database Backup Scheduler

Manages periodic automatic database backups based on configuration.
Runs as a background task to ensure backups happen without blocking main operations.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from src.config import Config
from src.core.database_state.backup_manager import DatabaseBackupManager


class BackupScheduler:
    """Manages periodic database backups."""

    def __init__(self, backup_manager: DatabaseBackupManager, config: Config):
        """
        Initialize backup scheduler.

        Args:
            backup_manager: Database backup manager instance
            config: Application configuration with backup settings
        """
        self.backup_manager = backup_manager
        self.config = config
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_backup_time: Optional[datetime] = None

    async def start(self) -> None:
        """Start the backup scheduler task."""
        if self._running:
            logger.warning("Backup scheduler already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._backup_loop())
        logger.info("Backup scheduler started")

    async def stop(self) -> None:
        """Stop the backup scheduler task."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Backup scheduler stopped")

    async def _backup_loop(self) -> None:
        """Main backup loop - runs periodically."""
        # Skip if backups are disabled
        if not self.config.database.backup_enabled:
            logger.info("Database backups disabled in configuration")
            return

        try:
            backup_interval_hours = self.config.database.backup_interval_hours
            backup_interval_seconds = backup_interval_hours * 3600

            logger.info(
                f"Backup scheduler configured: every {backup_interval_hours} hours"
            )

            while self._running:
                try:
                    # Check if it's time for a backup
                    now = datetime.now(timezone.utc)

                    if self._last_backup_time is None:
                        # First run - do a backup immediately
                        logger.info("First backup run - creating backup now")
                        await self.backup_manager.create_backup(label="periodic")
                        self._last_backup_time = now
                    else:
                        # Check if interval has passed since last backup
                        time_since_last = (now - self._last_backup_time).total_seconds()

                        if time_since_last >= backup_interval_seconds:
                            logger.info(
                                f"Backup interval reached ({time_since_last:.0f}s >= {backup_interval_seconds}s), "
                                "creating backup"
                            )
                            await self.backup_manager.create_backup(label="periodic")
                            self._last_backup_time = now

                    # Sleep for a short interval before checking again (check every 60 seconds)
                    await asyncio.sleep(60)

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"Error in backup scheduler loop: {e}")
                    # Continue running even on error
                    await asyncio.sleep(300)  # Wait 5 minutes before retrying

        except Exception as e:
            logger.error(f"Backup scheduler fatal error: {e}")
            self._running = False

    async def get_backup_stats(self) -> dict:
        """Get backup statistics."""
        return self.backup_manager.get_backup_stats()

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running
