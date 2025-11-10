"""Base repository pattern with common database operations.

Provides reusable patterns for all repositories:
- Connection management
- Error handling
- Logging
- Transaction support
"""

import logging
from typing import Optional, List, Dict, Any, TypeVar, Generic
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from ..core.database_state.base import DatabaseConnection

logger = logging.getLogger(__name__)

T = TypeVar('T')


class BaseRepository(Generic[T]):
    """Base repository with common database operations.

    Provides:
    - Async database connection management
    - Standard CRUD patterns
    - Error handling and logging
    - Transaction support

    Subclasses should implement domain-specific query methods.
    """

    def __init__(self, database: DatabaseConnection):
        """Initialize repository with database connection.

        Args:
            database: DatabaseConnection instance for async queries
        """
        self.db = database
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize repository resources.

        Override in subclasses for custom initialization (e.g., creating tables).
        """
        if self._initialized:
            logger.debug(f"{self.__class__.__name__} already initialized")
            return

        logger.info(f"Initializing {self.__class__.__name__}")
        self._initialized = True

    async def cleanup(self) -> None:
        """Cleanup repository resources.

        Override in subclasses for custom cleanup.
        """
        logger.debug(f"Cleaning up {self.__class__.__name__}")
        self._initialized = False

    @asynccontextmanager
    async def transaction(self):
        """Context manager for database transactions.

        Usage:
            async with repo.transaction():
                await repo.update(...)
                await repo.update(...)
                # Commits on success, rolls back on exception
        """
        async with self.db.connection.execute("BEGIN"):
            try:
                yield
                await self.db.connection.commit()
            except Exception:
                await self.db.connection.rollback()
                raise

    async def _execute(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute a query with error handling.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Cursor result

        Raises:
            Exception: If query fails
        """
        try:
            cursor = await self.db.connection.execute(query, params or {})
            await self.db.connection.commit()
            return cursor
        except Exception as e:
            logger.error(f"Query execution failed: {e}\nQuery: {query}\nParams: {params}")
            raise

    async def _fetch_one(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Fetch single row as dictionary.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Row as dictionary or None if not found
        """
        try:
            cursor = await self.db.connection.execute(query, params or {})
            row = await cursor.fetchone()

            if row is None:
                return None

            # Convert row to dictionary
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        except Exception as e:
            logger.error(f"Fetch one failed: {e}\nQuery: {query}\nParams: {params}")
            raise

    async def _fetch_all(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Fetch all rows as list of dictionaries.

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            List of rows as dictionaries
        """
        try:
            cursor = await self.db.connection.execute(query, params or {})
            rows = await cursor.fetchall()

            if not rows:
                return []

            # Convert rows to dictionaries
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Fetch all failed: {e}\nQuery: {query}\nParams: {params}")
            raise

    async def _scalar(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        default: Any = None
    ) -> Any:
        """Fetch single scalar value.

        Args:
            query: SQL query string (should return single column)
            params: Query parameters
            default: Default value if no result

        Returns:
            Scalar value or default
        """
        try:
            cursor = await self.db.connection.execute(query, params or {})
            row = await cursor.fetchone()

            if row is None or row[0] is None:
                return default

            return row[0]
        except Exception as e:
            logger.error(f"Scalar query failed: {e}\nQuery: {query}\nParams: {params}")
            raise

    def _get_today_start(self) -> datetime:
        """Get start of today in UTC.

        Returns:
            Datetime representing start of today (00:00:00 UTC)
        """
        now = datetime.now(timezone.utc)
        return now.replace(hour=0, minute=0, second=0, microsecond=0)

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format.

        Returns:
            ISO formatted timestamp string
        """
        return datetime.now(timezone.utc).isoformat()

    def _log_query(self, operation: str, query: str, params: Optional[Dict] = None) -> None:
        """Log query execution for debugging.

        Args:
            operation: Description of operation (e.g., "get_queue_status")
            query: SQL query
            params: Query parameters
        """
        logger.debug(
            f"{self.__class__.__name__}.{operation}\n"
            f"Query: {query}\n"
            f"Params: {params}"
        )
