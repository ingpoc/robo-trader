"""
Broker MCP integration for Robo Trader.

Handles broker connections and portfolio data fetching using Zerodha Kite Connect API.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from loguru import logger

from src.config import Config
from src.core.errors import ErrorCategory, ErrorSeverity, TradingError


class BrokerClient:
    """Real broker client for Zerodha Kite Connect API integration."""

    def __init__(self, config: Config):
        self.config = config
        self._authenticated = False
        self._kite_client = None
        self._oauth_service = None
        self._lock = asyncio.Lock()
        self._token_file = "data/zerodha_oauth_token.json"

    def is_authenticated(self) -> bool:
        """Check if broker is authenticated."""
        return self._authenticated and self._kite_client is not None

    async def authenticate(self) -> bool:
        """Authenticate with broker using stored OAuth token."""
        try:
            async with self._lock:
                # Check if already authenticated
                if self._authenticated and self._kite_client:
                    return True

                # Try to get stored token
                token_data = await self._get_stored_token()
                if not token_data:
                    logger.warning(
                        "No valid OAuth token found for broker authentication"
                    )
                    return False

                # Initialize Kite client with access token
                await self._initialize_kite_client(token_data["access_token"])

                logger.info(
                    f"Successfully authenticated with Zerodha for user: {token_data.get('user_id')}"
                )
                return True

        except Exception as e:
            logger.error(f"Broker authentication failed: {e}")
            self._authenticated = False
            self._kite_client = None
            return False

    async def _initialize_kite_client(self, access_token: str):
        """Initialize Kite Connect client with access token."""
        try:
            # Import kiteconnect here to avoid import errors if not installed
            from kiteconnect import KiteConnect

            api_key = getattr(self.config.integration, "zerodha_api_key", None)
            if not api_key:
                raise TradingError(
                    "Zerodha API key not configured",
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.HIGH,
                    recoverable=False,
                )

            # Initialize Kite Connect client
            self._kite_client = KiteConnect(api_key=api_key)
            self._kite_client.set_access_token(access_token)
            self._authenticated = True

        except ImportError as e:
            raise TradingError(
                "kiteconnect library not installed. Install with: pip install kiteconnect>=4.3.0",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
                details=str(e),
            )
        except Exception as e:
            raise TradingError(
                f"Failed to initialize Kite client: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30,
            )

    async def _get_stored_token(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored OAuth token if valid. Checks ENV first, then file."""
        try:
            # First, check ENV variables for token
            from ..core.env_helpers import get_zerodha_token_from_env

            env_token = get_zerodha_token_from_env()
            if env_token:
                logger.info("Using Zerodha OAuth token from ENV variable")
                return env_token

            # Fallback to token file
            import json
            import os

            import aiofiles

            if not os.path.exists(self._token_file):
                return None

            async with aiofiles.open(self._token_file, "r") as f:
                content = await f.read()
                token_data = json.loads(content)

            # Check if token is expired
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(timezone.utc) >= expires_at:
                logger.info("Stored OAuth token has expired")
                await self._delete_token_file()
                return None

            logger.info("Using Zerodha OAuth token from file")
            return token_data

        except Exception as e:
            logger.error(f"Failed to retrieve stored token: {e}")
            return None

    async def _delete_token_file(self) -> None:
        """Delete stored token file."""
        try:
            import os

            if os.path.exists(self._token_file):
                os.remove(self._token_file)
                logger.info("Deleted expired OAuth token file")
        except Exception as e:
            logger.error(f"Failed to delete token file: {e}")

    @property
    def kite(self):
        """Get Kite Connect client instance."""
        if not self._authenticated or not self._kite_client:
            raise AttributeError("Broker not authenticated. Call authenticate() first.")
        return self._kite_client

    async def holdings(self) -> list:
        """Get holdings from Kite API with proper error handling."""
        try:
            if not self.is_authenticated():
                if not await self.authenticate():
                    raise TradingError(
                        "Failed to authenticate with broker",
                        category=ErrorCategory.API,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        retry_after_seconds=60,
                    )

            holdings = self.kite.holdings()
            logger.info(f"Successfully fetched {len(holdings)} holdings from Zerodha")
            return holdings

        except Exception as e:
            logger.error(f"Error fetching holdings: {e}")

            # Handle authentication errors
            if "403" in str(e) or "unauthorised" in str(e).lower():
                self._authenticated = False
                self._kite_client = None
                await self._delete_token_file()

            raise TradingError(
                f"Failed to fetch holdings: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30,
            )

    async def positions(self) -> dict:
        """Get positions from Kite API with proper error handling."""
        try:
            if not self.is_authenticated():
                if not await self.authenticate():
                    raise TradingError(
                        "Failed to authenticate with broker",
                        category=ErrorCategory.API,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        retry_after_seconds=60,
                    )

            positions = self.kite.positions()
            logger.info("Successfully fetched positions from Zerodha")
            return positions

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")

            # Handle authentication errors
            if "403" in str(e) or "unauthorised" in str(e).lower():
                self._authenticated = False
                self._kite_client = None
                await self._delete_token_file()

            raise TradingError(
                f"Failed to fetch positions: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30,
            )

    async def margins(self) -> dict:
        """Get margins from Kite API with proper error handling."""
        try:
            if not self.is_authenticated():
                if not await self.authenticate():
                    raise TradingError(
                        "Failed to authenticate with broker",
                        category=ErrorCategory.API,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        retry_after_seconds=60,
                    )

            margins = self.kite.margins()
            logger.info("Successfully fetched margins from Zerodha")
            return margins

        except Exception as e:
            logger.error(f"Error fetching margins: {e}")

            # Handle authentication errors
            if "403" in str(e) or "unauthorised" in str(e).lower():
                self._authenticated = False
                self._kite_client = None
                await self._delete_token_file()

            raise TradingError(
                f"Failed to fetch margins: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30,
            )

    async def quote(self, symbol: str) -> dict:
        """Get quote data for a symbol from Kite API."""
        try:
            if not self.is_authenticated():
                if not await self.authenticate():
                    raise TradingError(
                        "Failed to authenticate with broker",
                        category=ErrorCategory.API,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                        retry_after_seconds=60,
                    )

            quotes = self.kite.quote(symbol)
            logger.info(f"Successfully fetched quote for {symbol} from Zerodha")
            return quotes

        except Exception as e:
            logger.error(f"Error fetching quote for {symbol}: {e}")

            # Handle authentication errors
            if "403" in str(e) or "unauthorised" in str(e).lower():
                self._authenticated = False
                self._kite_client = None
                await self._delete_token_file()

            raise TradingError(
                f"Failed to fetch quote for {symbol}: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30,
            )


async def get_broker(config: Config) -> Optional[BrokerClient]:
    """
    Get broker client instance.

    Args:
        config: Application configuration

    Returns:
        Broker client instance or None if not available
    """
    try:
        broker = BrokerClient(config)
        if await broker.authenticate():
            logger.info("Broker client initialized successfully")
            return broker
        else:
            logger.warning("Broker authentication failed")
            return None
    except Exception as e:
        logger.error(f"Failed to initialize broker: {e}")
        return None
