"""
Database Backup Manager

Handles automatic and manual database backups with rotation.
Ensures critical data (analysis, trades, portfolio state) is never lost.
"""

import asyncio
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from loguru import logger


class DatabaseBackupManager:
    """Manages database backups with automatic rotation."""

    def __init__(self, db_path: Path, backup_dir: Optional[Path] = None):
        """
        Initialize backup manager.

        Args:
            db_path: Path to main database file
            backup_dir: Directory for backups (default: db_path.parent / "backups")
        """
        self.db_path = db_path
        self.backup_dir = backup_dir or (db_path.parent / "backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self._backup_lock = asyncio.Lock()

    async def create_backup(self, label: str = "manual") -> Optional[Path]:
        """
        Create a database backup immediately.

        Args:
            label: Backup label (e.g., "manual", "hourly", "before_deploy")

        Returns:
            Path to backup file, or None if backup failed
        """
        async with self._backup_lock:
            try:
                if not self.db_path.exists():
                    logger.warning(
                        f"Database not found at {self.db_path}, skipping backup"
                    )
                    return None

                # Create backup filename with timestamp
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                backup_filename = f"{self.db_path.stem}_{label}_{timestamp}.db"
                backup_path = self.backup_dir / backup_filename

                # Copy database file
                shutil.copy2(self.db_path, backup_path)
                logger.info(f"Database backup created: {backup_path}")

                # Cleanup old backups
                await self._cleanup_old_backups(max_backups=7)

                return backup_path

            except Exception as e:
                logger.error(f"Failed to create database backup: {e}")
                return None

    async def _cleanup_old_backups(self, max_backups: int = 7) -> int:
        """
        Remove old backup files, keeping only the latest N backups.

        Args:
            max_backups: Maximum number of backups to keep

        Returns:
            Number of backups deleted
        """
        try:
            backup_files = sorted(
                self.backup_dir.glob(f"{self.db_path.stem}_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )

            deleted_count = 0
            for backup_file in backup_files[max_backups:]:
                try:
                    backup_file.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old backup: {backup_file}")
                except Exception as e:
                    logger.warning(f"Failed to delete backup {backup_file}: {e}")

            if deleted_count > 0:
                logger.info(f"Cleaned up {deleted_count} old backups")

            return deleted_count

        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}")
            return 0

    async def get_latest_backup(self) -> Optional[Path]:
        """
        Get the most recent backup file.

        Returns:
            Path to latest backup, or None if no backups exist
        """
        try:
            backup_files = sorted(
                self.backup_dir.glob(f"{self.db_path.stem}_*.db"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            return backup_files[0] if backup_files else None
        except Exception as e:
            logger.error(f"Error finding latest backup: {e}")
            return None

    async def get_backups(self, hours: int = 24) -> List[Path]:
        """
        Get recent backups created within the last N hours.

        Args:
            hours: Number of hours to look back

        Returns:
            List of backup files sorted by creation time (newest first)
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            cutoff_timestamp = cutoff_time.timestamp()

            backup_files = [
                p
                for p in self.backup_dir.glob(f"{self.db_path.stem}_*.db")
                if p.stat().st_mtime >= cutoff_timestamp
            ]

            return sorted(backup_files, key=lambda p: p.stat().st_mtime, reverse=True)
        except Exception as e:
            logger.error(f"Error getting backups: {e}")
            return []

    async def restore_backup(self, backup_path: Path) -> bool:
        """
        Restore database from a backup file.

        WARNING: This will overwrite the current database.

        Args:
            backup_path: Path to backup file to restore

        Returns:
            True if restore successful, False otherwise
        """
        async with self._backup_lock:
            try:
                if not backup_path.exists():
                    logger.error(f"Backup file not found: {backup_path}")
                    return False

                if not backup_path.suffix == ".db":
                    logger.error(f"Invalid backup file: {backup_path}")
                    return False

                # Create a backup of current database before restoring
                current_backup = await self.create_backup("before_restore")
                if not current_backup:
                    logger.warning("Could not backup current database before restore")

                # Restore from backup
                shutil.copy2(backup_path, self.db_path)
                logger.info(f"Database restored from backup: {backup_path}")

                if current_backup:
                    logger.info(f"Previous database saved as: {current_backup}")

                return True

            except Exception as e:
                logger.error(f"Failed to restore database from backup: {e}")
                return False

    def get_backup_stats(self) -> dict:
        """
        Get statistics about database and backups.

        Returns:
            Dictionary with backup stats
        """
        try:
            db_size = self.db_path.stat().st_size if self.db_path.exists() else 0
            backup_files = list(self.backup_dir.glob(f"{self.db_path.stem}_*.db"))

            total_backup_size = sum(b.stat().st_size for b in backup_files)

            return {
                "database_exists": self.db_path.exists(),
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "backup_count": len(backup_files),
                "total_backup_size_mb": round(total_backup_size / (1024 * 1024), 2),
                "backup_dir": str(self.backup_dir),
                "latest_backup": (
                    backup_files[0].name
                    if (
                        backup_files := sorted(
                            backup_files, key=lambda p: p.stat().st_mtime, reverse=True
                        )
                    )
                    else None
                ),
                "backups": [
                    b.name
                    for b in sorted(
                        backup_files, key=lambda p: p.stat().st_mtime, reverse=True
                    )
                ],
            }

        except Exception as e:
            logger.error(f"Error getting backup stats: {e}")
            return {}
