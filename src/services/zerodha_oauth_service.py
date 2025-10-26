"""
Zerodha OAuth Service for Robo Trader

Handles OAuth authentication flow with Zerodha Kite Connect API,
including redirect URL configuration, token management, and secure storage.
"""

import asyncio
import json
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from urllib.parse import urlencode, urlparse, parse_qs
import aiofiles
import httpx
from loguru import logger

from src.config import Config
from src.core.event_bus import Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity


class ZerodhaOAuthService:
    """Service for handling Zerodha OAuth authentication flow."""

    def __init__(self, config: Config, event_bus):
        self.config = config
        self.event_bus = event_bus
        self._redirect_urls = {
            "development": "http://localhost:8000/api/auth/zerodha/callback",
            "docker": "http://robo-trader-app:8000/api/auth/zerodha/callback",
            "production": "https://your-domain.com/api/auth/zerodha/callback"
        }
        self._oauth_states = {}  # Temporary storage for OAuth state validation
        self._base_url = "https://kite.zerodha.com/connect"
        self._token_file = "data/zerodha_oauth_token.json"

    async def initialize(self) -> None:
        """Initialize the OAuth service."""
        logger.info("Initializing Zerodha OAuth service")

        # Create data directory if it doesn't exist
        import os
        os.makedirs("data", exist_ok=True)

        # Validate configuration
        await self._validate_config()

        logger.info("Zerodha OAuth service initialized successfully")

    async def _validate_config(self) -> None:
        """Validate OAuth configuration."""
        api_key = getattr(self.config.integration, 'zerodha_api_key', None)
        if not api_key:
            raise TradingError(
                "Zerodha API key not configured",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

        api_secret = getattr(self.config.integration, 'zerodha_api_secret', None)
        if not api_secret:
            raise TradingError(
                "Zerodha API secret not configured",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    def get_redirect_url(self) -> str:
        """Get the appropriate redirect URL for current environment."""
        environment = self.config.environment

        if environment not in self._redirect_urls:
            logger.warning(f"Unknown environment '{environment}', using development redirect URL")
            return self._redirect_urls["development"]

        redirect_url = self._redirect_urls[environment]
        logger.info(f"Using redirect URL for {environment}: {redirect_url}")
        return redirect_url

    async def generate_auth_url(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Generate Zerodha OAuth authorization URL.

        Args:
            user_id: Optional user identifier for tracking

        Returns:
            Dict containing auth URL and state parameter
        """
        try:
            # Generate secure state parameter for CSRF protection
            state = secrets.token_urlsafe(32)

            # Store state with timestamp for validation
            self._oauth_states[state] = {
                "created_at": datetime.now(timezone.utc),
                "user_id": user_id or "anonymous",
                "redirect_url": self.get_redirect_url()
            }

            # Clean old states (older than 10 minutes)
            await self._cleanup_old_states()

            # Build authorization URL parameters
            params = {
                "api_key": getattr(self.config.integration, 'zerodha_api_key'),
                "redirect_url": self.get_redirect_url(),
                "state": state
            }

            auth_url = f"{self._base_url}?{urlencode(params)}"

            # Emit OAuth initiation event
            await self._emit_oauth_event(
                "oauth_initiated",
                {
                    "state": state,
                    "user_id": user_id,
                    "redirect_url": self.get_redirect_url(),
                    "auth_url": auth_url
                }
            )

            logger.info(f"Generated Zerodha auth URL for user {user_id}")

            return {
                "auth_url": auth_url,
                "state": state,
                "redirect_url": self.get_redirect_url()
            }

        except Exception as e:
            logger.error(f"Failed to generate auth URL: {e}")
            raise TradingError(
                f"Failed to generate authorization URL: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    async def handle_callback(self, request_token: str, state: str) -> Dict[str, Any]:
        """
        Handle OAuth callback from Zerodha.

        Args:
            request_token: Request token from Zerodha callback
            state: State parameter for CSRF validation

        Returns:
            Dict containing access token and user info
        """
        try:
            # Validate state parameter
            if not await self._validate_state(state):
                raise TradingError(
                    "Invalid or expired OAuth state parameter",
                    category=ErrorCategory.SECURITY,
                    severity=ErrorSeverity.HIGH,
                    recoverable=False
                )

            # Exchange request token for access token
            access_token_data = await self._exchange_request_token(request_token)

            # Store tokens securely
            await self._store_tokens(access_token_data, state)

            # Clean up state
            if state in self._oauth_states:
                del self._oauth_states[state]

            # Emit success event
            await self._emit_oauth_event(
                "oauth_success",
                {
                    "user_id": access_token_data.get("user_id"),
                    "login_time": access_token_data.get("login_time")
                }
            )

            logger.info(f"Successfully authenticated Zerodha user: {access_token_data.get('user_id')}")

            return {
                "success": True,
                "user_id": access_token_data.get("user_id"),
                "access_token": access_token_data.get("access_token"),
                "login_time": access_token_data.get("login_time"),
                "expires_at": access_token_data.get("expires_at")
            }

        except TradingError:
            raise
        except Exception as e:
            logger.error(f"OAuth callback handling failed: {e}")

            # Emit error event
            await self._emit_oauth_event(
                "oauth_error",
                {
                    "state": state,
                    "error": str(e),
                    "request_token": request_token[:10] + "..." if request_token else None
                }
            )

            raise TradingError(
                f"OAuth authentication failed: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=60
            )

    async def _validate_state(self, state: str) -> bool:
        """Validate OAuth state parameter."""
        if state not in self._oauth_states:
            logger.warning(f"Invalid state parameter: {state}")
            return False

        state_data = self._oauth_states[state]
        created_at = state_data["created_at"]

        # Check if state is not older than 10 minutes
        if datetime.now(timezone.utc) - created_at > timedelta(minutes=10):
            logger.warning(f"Expired state parameter: {state}")
            del self._oauth_states[state]
            return False

        return True

    async def _exchange_request_token(self, request_token: str) -> Dict[str, Any]:
        """Exchange request token for access token."""
        try:
            async with httpx.AsyncClient() as client:
                checksum = self._generate_checksum(request_token)

                data = {
                    "request_token": request_token,
                    "api_key": getattr(self.config.integration, 'zerodha_api_key'),
                    "checksum": checksum
                }

                response = await client.post(
                    "https://kite.zerodha.com/api/token/access_token",
                    data=data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    timeout=30.0
                )

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"Token exchange failed: {response.status_code} - {error_text}")
                    raise TradingError(
                        f"Token exchange failed: {response.status_code}",
                        category=ErrorCategory.API,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True
                    )

                token_data = response.json()

                # Add expiry information
                login_time = datetime.now(timezone.utc)
                expires_at = login_time + timedelta(hours=24)  # Zerodha tokens last 24 hours

                return {
                    "access_token": token_data.get("access_token"),
                    "request_token": request_token,
                    "user_id": token_data.get("user_id"),
                    "login_time": login_time.isoformat(),
                    "expires_at": expires_at.isoformat()
                }

        except httpx.RequestError as e:
            logger.error(f"HTTP request failed during token exchange: {e}")
            raise TradingError(
                "Failed to connect to Zerodha API",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30
            )

    def _generate_checksum(self, request_token: str) -> str:
        """Generate checksum for token exchange."""
        api_secret = getattr(self.config.integration, 'zerodha_api_secret')
        api_key = getattr(self.config.integration, 'zerodha_api_key')
        checksum_string = f"{request_token}{api_key}{api_secret}"
        return hashlib.sha256(checksum_string.encode()).hexdigest()

    async def _store_tokens(self, token_data: Dict[str, Any], state: str) -> None:
        """Store OAuth tokens securely."""
        try:
            # Add storage metadata
            token_data["stored_at"] = datetime.now(timezone.utc).isoformat()
            token_data["oauth_state"] = state

            # Atomic write to file
            temp_file = f"{self._token_file}.tmp"
            async with aiofiles.open(temp_file, 'w') as f:
                await f.write(json.dumps(token_data, indent=2))

            import os
            os.replace(temp_file, self._token_file)

            logger.info(f"Stored OAuth token for user: {token_data.get('user_id')}")

        except Exception as e:
            logger.error(f"Failed to store OAuth tokens: {e}")
            raise TradingError(
                "Failed to store authentication tokens",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    async def get_stored_token(self) -> Optional[Dict[str, Any]]:
        """Retrieve stored OAuth token if valid."""
        try:
            if not await self._token_file_exists():
                return None

            async with aiofiles.open(self._token_file, 'r') as f:
                content = await f.read()
                token_data = json.loads(content)

            # Check if token is expired
            expires_at = datetime.fromisoformat(token_data["expires_at"])
            if datetime.now(timezone.utc) >= expires_at:
                logger.info("Stored OAuth token has expired")
                await self._delete_token_file()
                return None

            return token_data

        except Exception as e:
            logger.error(f"Failed to retrieve stored token: {e}")
            return None

    async def _token_file_exists(self) -> bool:
        """Check if token file exists."""
        import os
        return os.path.exists(self._token_file)

    async def _delete_token_file(self) -> None:
        """Delete stored token file."""
        try:
            import os
            if os.path.exists(self._token_file):
                os.remove(self._token_file)
                logger.info("Deleted expired OAuth token file")
        except Exception as e:
            logger.error(f"Failed to delete token file: {e}")

    async def _cleanup_old_states(self) -> None:
        """Clean up expired OAuth states."""
        current_time = datetime.now(timezone.utc)
        expired_states = []

        for state, data in self._oauth_states.items():
            if current_time - data["created_at"] > timedelta(minutes=10):
                expired_states.append(state)

        for state in expired_states:
            del self._oauth_states[state]

        if expired_states:
            logger.info(f"Cleaned up {len(expired_states)} expired OAuth states")

    async def _emit_oauth_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit OAuth-related event."""
        try:
            event = Event(
                id=f"oauth_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{secrets.token_hex(4)}",
                type=EventType.SYSTEM_ERROR if event_type == "oauth_error" else EventType.SYSTEM_HEALTH_CHECK,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="ZerodhaOAuthService",
                data={
                    "event_type": event_type,
                    "provider": "zerodha",
                    **data
                }
            )
            await self.event_bus.emit(event)
        except Exception as e:
            logger.error(f"Failed to emit OAuth event: {e}")

    async def logout(self) -> None:
        """Logout and clear stored tokens."""
        try:
            await self._delete_token_file()

            # Emit logout event
            await self._emit_oauth_event("oauth_logout", {"timestamp": datetime.now(timezone.utc).isoformat()})

            logger.info("Zerodha OAuth logout completed")

        except Exception as e:
            logger.error(f"Logout failed: {e}")
            raise TradingError(
                "Failed to logout from Zerodha",
                category=ErrorCategory.RESOURCE,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )