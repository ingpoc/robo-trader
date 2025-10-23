"""Database utilities and connection management."""

import asyncpg
import logging
from typing import List, Dict, Any, Optional
from ..config import load_config

logger = logging.getLogger(__name__)

# Global connection pool
_db_pool = None

async def get_db_pool():
    """Get or create database connection pool."""
    global _db_pool
    if _db_pool is None:
        config = load_config()
        # Create connection pool using config
        _db_pool = await asyncpg.create_pool(
            host=config.database.host,
            port=config.database.port,
            user=config.database.user,
            password=config.database.password,
            database=config.database.name,
            min_size=5,
            max_size=20
        )
        logger.info("Database connection pool created")
    return _db_pool

async def execute_query(pool, query: str, *args, single: bool = False):
    """Execute a SELECT query."""
    async with pool.acquire() as conn:
        if single:
            return await conn.fetchrow(query, *args)
        else:
            return await conn.fetch(query, *args)

async def execute_update(pool, query: str, *args):
    """Execute an INSERT/UPDATE/DELETE query."""
    async with pool.acquire() as conn:
        return await conn.execute(query, *args)

async def close_db_pool():
    """Close the database connection pool."""
    global _db_pool
    if _db_pool:
        await _db_pool.close()
        _db_pool = None
        logger.info("Database connection pool closed")