"""
Database connection wrapper for legacy code compatibility.

Provides a connect() method interface that works with aiosqlite connections
for code that expects the older database connection pattern.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import aiosqlite


class DatabaseWrapper:
    """
    Wrapper around DatabaseConnection to provide legacy-compatible interface.

    Provides a connect() method that returns the underlying aiosqlite connection
    for code that was written expecting the older database interface.
    """

    def __init__(self, db_connection):
        """
        Initialize wrapper with existing database connection.

        Args:
            db_connection: DatabaseConnection instance
        """
        self.db_connection = db_connection

    @property
    def backup_manager(self):
        """Get backup manager from underlying connection."""
        return self.db_connection.backup_manager if self.db_connection else None

    @property
    def connection(self):
        """Get direct database connection for queries."""
        return self.db_connection.connection if self.db_connection else None

    @asynccontextmanager
    async def connect(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """
        Provide connect() method interface for legacy code.

        Yields:
            aiosqlite.Connection: The underlying database connection
        """
        # Return the existing connection directly
        # DatabaseConnection already manages the connection pooling
        yield self.db_connection.connection
