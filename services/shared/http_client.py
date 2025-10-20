"""
Shared HTTP Client Factory
Manages a single persistent httpx.AsyncClient instance for all services
"""

import logging
from typing import Optional

import httpx


logger = logging.getLogger(__name__)

_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client"""
    global _http_client

    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=10.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
        logger.info("✅ Shared HTTP client created")

    return _http_client


async def close_http_client() -> None:
    """Close shared HTTP client"""
    global _http_client

    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("HTTP client closed")
