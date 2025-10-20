"""
Database Connection Management
Handles PostgreSQL connection pooling and management for all services
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
from asyncpg import Pool


logger = logging.getLogger(__name__)

_pool: Optional[Pool] = None
_pool_lock = asyncio.Lock()


async def get_db_pool(
    database_url: str, min_size: int = 10, max_size: int = 20
) -> Pool:
    """Get or create database connection pool (thread-safe with locking)"""
    global _pool

    if _pool is not None:
        return _pool

    async with _pool_lock:
        if _pool is not None:
            return _pool

        try:
            _pool = await asyncpg.create_pool(
                database_url,
                min_size=min_size,
                max_size=max_size,
                command_timeout=60,
            )

            logger.info(f"✅ Database pool created (min: {min_size}, max: {max_size})")
            return _pool
        except Exception as e:
            logger.error(f"❌ Failed to create database pool: {e}")
            raise


@asynccontextmanager
async def get_db_connection(pool: Pool):
    """Get single connection from pool with proper cleanup"""
    connection = None
    try:
        connection = await pool.acquire()
        yield connection
    except Exception as e:
        logger.error(f"Failed to acquire database connection: {e}")
        raise
    finally:
        if connection is not None:
            await pool.release(connection)


async def close_db_pool() -> None:
    """Close database connection pool"""
    global _pool

    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("Database pool closed")


async def execute_query(pool: Pool, query: str, *args):
    """Execute a single query"""
    async with pool.acquire() as connection:
        return await connection.fetch(query, *args)


async def execute_update(pool: Pool, query: str, *args):
    """Execute an update/insert/delete query"""
    async with pool.acquire() as connection:
        return await connection.execute(query, *args)


async def check_db_health(pool: Pool) -> bool:
    """Check if database is healthy"""
    try:
        async with pool.acquire() as connection:
            await connection.fetchval("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False
