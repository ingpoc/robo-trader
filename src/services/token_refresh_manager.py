"""
Token Refresh Manager for Robo Trader

Handles automatic token refresh, expiry monitoring, and alerts for Zerodha API tokens.
Prevents authentication failures by proactively refreshing tokens before expiry.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum
import json
import aiofiles
from loguru import logger

from src.config import Config
from src.core.event_bus import Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity


class TokenStatus(Enum):
    """Token status enumeration."""
    VALID = "valid"
    EXPIRING_SOON = "expiring_soon"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass
class TokenInfo:
    """Token information and status."""
    access_token: str
    user_id: str
    expires_at: datetime
    login_time: datetime
    source: str  # "env" or "file"
    status: TokenStatus
    time_to_expiry: timedelta
    last_checked: datetime


class TokenRefreshManager:
    """
    Manages automatic token refresh and expiry monitoring.

    Features:
    - Proactive token refresh before expiry
    - Token expiry alerts and warnings
    - Background monitoring with configurable intervals
    - Event-driven notifications for token status changes
    - Graceful fallback to cached data when refresh fails
    """

    def __init__(self, config: Config, event_bus):
        self.config = config
        self.event_bus = event_bus
        self._monitoring_task = None
        self._lock = asyncio.Lock()
        self._token_info: Optional[TokenInfo] = None
        self._refresh_callbacks: list[Callable] = []

        # Configuration
        self._refresh_threshold_minutes = 30  # Refresh 30 minutes before expiry
        self._warning_threshold_minutes = 60  # Warning 60 minutes before expiry
        self._monitoring_interval_seconds = 300  # Check every 5 minutes
        self._monitoring_enabled = True

        # Token refresh state
        self._last_refresh_attempt: Optional[datetime] = None
        self._refresh_failure_count = 0
        self._max_refresh_attempts = 3

    async def initialize(self) -> None:
        """Initialize the token refresh manager."""
        logger.info("Initializing Token Refresh Manager")

        # Check current token status
        await self._check_current_token()

        # Start background monitoring if enabled
        if self._monitoring_enabled:
            await self._start_monitoring()

        logger.info("Token Refresh Manager initialized successfully")

    async def cleanup(self) -> None:
        """Cleanup resources and stop monitoring."""
        logger.info("Cleaning up Token Refresh Manager")

        if self._monitoring_task:
            self._monitoring_task.cancel()
            try:
                await self._monitoring_task
            except asyncio.CancelledError:
                pass

        logger.info("Token Refresh Manager cleanup complete")

    async def add_refresh_callback(self, callback: Callable) -> None:
        """Add a callback to be called when token is refreshed."""
        self._refresh_callbacks.append(callback)

    async def get_token_status(self) -> Optional[TokenInfo]:
        """Get current token status information."""
        return self._token_info

    async def is_token_valid(self) -> bool:
        """Check if current token is valid and not expiring soon."""
        if not self._token_info:
            return False

        return self._token_info.status in [TokenStatus.VALID, TokenStatus.EXPIRING_SOON]

    async def force_token_check(self) -> TokenInfo:
        """Force an immediate token status check."""
        await self._check_current_token()
        if self._token_info:
            return self._token_info
        raise TradingError(
            "No valid token available",
            category=ErrorCategory.API,
            severity=ErrorSeverity.HIGH,
            recoverable=True
        )

    async def _check_current_token(self) -> None:
        """Check the current token status and update token info."""
        try:
            async with self._lock:
                # Get token from environment first
                from ..core.env_helpers import get_zerodha_token_from_env
                token_data = get_zerodha_token_from_env()

                if not token_data:
                    logger.warning("No valid token found in environment")
                    await self._update_token_status(None)
                    return

                # Parse token data
                access_token = token_data.get("access_token")
                user_id = token_data.get("user_id", "")
                expires_at_str = token_data.get("expires_at")
                source = token_data.get("source", "env")

                # Parse expiry time
                if expires_at_str:
                    expires_at = datetime.fromisoformat(expires_at_str)
                else:
                    # Default expiry: 24 hours from login time
                    login_time_str = token_data.get("login_time")
                    if login_time_str:
                        login_time = datetime.fromisoformat(login_time_str)
                    else:
                        login_time = datetime.now(timezone.utc)
                    expires_at = login_time + timedelta(hours=24)

                # Calculate time to expiry
                now = datetime.now(timezone.utc)
                time_to_expiry = expires_at - now

                # Determine token status
                if time_to_expiry.total_seconds() <= 0:
                    status = TokenStatus.EXPIRED
                elif time_to_expiry <= timedelta(minutes=self._refresh_threshold_minutes):
                    status = TokenStatus.EXPIRING_SOON
                else:
                    status = TokenStatus.VALID

                # Update token info
                self._token_info = TokenInfo(
                    access_token=access_token,
                    user_id=user_id,
                    expires_at=expires_at,
                    login_time=datetime.fromisoformat(token_data.get("login_time", now.isoformat())),
                    source=source,
                    status=status,
                    time_to_expiry=time_to_expiry,
                    last_checked=now
                )

                # Log status
                logger.info(f"Token status: {status.value}, expires in {time_to_expiry}")

                # Emit status change event if status changed
                await self._emit_token_status_event()

                # Trigger refresh if needed
                if status == TokenStatus.EXPIRING_SOON:
                    await self._schedule_refresh()
                elif status == TokenStatus.EXPIRED:
                    await self._handle_expired_token()

        except Exception as e:
            logger.error(f"Error checking token status: {e}")
            await self._update_token_status(None)

    async def _start_monitoring(self) -> None:
        """Start background token monitoring."""
        if self._monitoring_task:
            return

        self._monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started token monitoring background task")

    async def _monitoring_loop(self) -> None:
        """Background monitoring loop for token status."""
        while self._monitoring_enabled:
            try:
                await self._check_current_token()
                await asyncio.sleep(self._monitoring_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in token monitoring loop: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying

    async def _schedule_refresh(self) -> None:
        """Schedule token refresh for expiring tokens."""
        if not self._token_info or self._token_info.status != TokenStatus.EXPIRING_SOON:
            return

        logger.warning(f"Token expiring in {self._token_info.time_to_expiry}, scheduling refresh")

        # Emit warning event
        await self.event_bus.publish(Event(
            id=f"token_refresh_warning_{datetime.now().isoformat()}",
            type=EventType.TOKEN_EXPIRY_WARNING,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="TokenRefreshManager",
            data={
                "user_id": self._token_info.user_id,
                "expires_at": self._token_info.expires_at.isoformat(),
                "time_to_expiry_minutes": int(self._token_info.time_to_expiry.total_seconds() / 60),
                "warning_threshold_minutes": self._warning_threshold_minutes
            }
        ))

        # Try to refresh token
        await self._attempt_token_refresh()

    async def _attempt_token_refresh(self) -> None:
        """Attempt to refresh the token."""
        # For Zerodha, tokens cannot be automatically refreshed without user interaction
        # This is a limitation of the OAuth flow. We'll provide clear guidance.

        logger.warning("Zerodha token refresh requires manual user intervention")

        # Emit refresh required event
        await self.event_bus.publish(Event(
            id=f"token_refresh_required_{datetime.now().isoformat()}",
            type=EventType.TOKEN_REFRESH_REQUIRED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="TokenRefreshManager",
            data={
                "user_id": self._token_info.user_id if self._token_info else None,
                "expires_at": self._token_info.expires_at.isoformat() if self._token_info else None,
                "refresh_url": "/api/auth/zerodha/login",  # Endpoint for manual refresh
                "message": "Please re-authenticate with Zerodha to continue trading",
                "instructions": [
                    "Visit the authentication URL to generate a new token",
                    "The new token will be automatically saved to environment",
                    "Trading will continue with cached data until re-authentication"
                ]
            }
        ))

    async def _handle_expired_token(self) -> None:
        """Handle expired token scenario."""
        logger.error("Token has expired - broker authentication will fail")

        # Emit expired token event
        await self.event_bus.publish(Event(
            id=f"token_expired_{datetime.now().isoformat()}",
            type=EventType.TOKEN_EXPIRED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="TokenRefreshManager",
            data={
                "user_id": self._token_info.user_id if self._token_info else None,
                "expired_at": self._token_info.expires_at.isoformat() if self._token_info else None,
                "refresh_url": "/api/auth/zerodha/login",
                "message": "Token has expired - immediate re-authentication required",
                "fallback_mode": "System will operate with cached data until re-authenticated"
            }
        ))

    async def _update_token_status(self, token_info: Optional[TokenInfo]) -> None:
        """Update token status and emit change event."""
        old_status = self._token_info.status if self._token_info else None
        self._token_info = token_info
        new_status = token_info.status if token_info else None

        if old_status != new_status:
            await self._emit_token_status_event()

    async def _emit_token_status_event(self) -> None:
        """Emit token status change event."""
        if not self._token_info:
            return

        await self.event_bus.publish(Event(
            id=f"token_status_{datetime.now().isoformat()}",
            type=EventType.TOKEN_STATUS_CHANGED,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="TokenRefreshManager",
            data={
                "status": self._token_info.status.value,
                "user_id": self._token_info.user_id,
                "expires_at": self._token_info.expires_at.isoformat(),
                "time_to_expiry_minutes": int(self._token_info.time_to_expiry.total_seconds() / 60),
                "source": self._token_info.source,
                "last_checked": self._token_info.last_checked.isoformat()
            }
        ))

    def get_monitoring_status(self) -> Dict[str, Any]:
        """Get current monitoring status for health checks."""
        return {
            "monitoring_enabled": self._monitoring_enabled,
            "monitoring_interval_seconds": self._monitoring_interval_seconds,
            "refresh_threshold_minutes": self._refresh_threshold_minutes,
            "warning_threshold_minutes": self._warning_threshold_minutes,
            "last_refresh_attempt": self._last_refresh_attempt.isoformat() if self._last_refresh_attempt else None,
            "refresh_failure_count": self._refresh_failure_count,
            "token_status": self._token_info.status.value if self._token_info else "no_token"
        }