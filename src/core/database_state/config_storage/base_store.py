"""Base configuration store with common functionality."""

import asyncio
from typing import TYPE_CHECKING
from loguru import logger

if TYPE_CHECKING:
    from ..base import DatabaseConnection


class BaseConfigStore:
    """Base class for configuration stores with shared database access."""

    def __init__(self, db_connection: 'DatabaseConnection'):
        """
        Initialize base configuration store.

        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        self._lock = asyncio.Lock()

    def _log_error(self, operation: str, error: Exception) -> None:
        """
        Log error with store context.

        Args:
            operation: Operation that failed
            error: Exception that occurred
        """
        store_name = self.__class__.__name__
        logger.error(f"{store_name}.{operation} failed: {error}")
