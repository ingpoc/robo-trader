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
        Generate Zerodha OAuth authorization URL using KiteConnect library.

        Args:
            user_id: Optional user identifier for tracking

        Returns:
            Dict containing auth URL and state parameter
        """
        try:
            # Use KiteConnect library for proper login URL generation
            import asyncio
            from urllib.parse import quote
            
            api_key = getattr(self.config.integration, 'zerodha_api_key')
            if not api_key:
                raise TradingError(
                    "Zerodha API key not configured",
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.HIGH,
                    recoverable=False
                )
            
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

            # Build authorization URL per PyKiteConnect documentation format
            # Format: https://kite.zerodha.com/connect/login?api_key={api_key}&redirect_url={redirect_url_encoded}
            redirect_url = self.get_redirect_url()
            redirect_url_encoded = quote(redirect_url, safe='')
            
            # Build URL with state parameter
            auth_url = f"https://kite.zerodha.com/connect/login?api_key={api_key}&redirect_url={redirect_url_encoded}&state={state}"

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

    async def handle_callback(self, request_token: str, state: Optional[str] = None) -> Dict[str, Any]:
        """
        Handle OAuth callback from Zerodha.

        Args:
            request_token: Request token from Zerodha callback
            state: State parameter for CSRF validation (optional - Zerodha may not always send it)

        Returns:
            Dict containing access token and user info
        """
        try:
            # Validate state parameter if provided
            # Note: Zerodha may not always send the state parameter back,
            # so we make it optional but still validate if present
            if state:
                if not await self._validate_state(state):
                    logger.warning(f"State parameter validation failed: {state}")
                    # Don't fail hard - Zerodha's request token is still valid
                    # Just log the warning and continue
                else:
                    logger.info(f"State parameter validated successfully: {state[:10]}...")
            else:
                logger.warning("No state parameter received from Zerodha callback - continuing without CSRF validation")

            # Exchange request token for access token
            access_token_data = await self._exchange_request_token(request_token)

            # Store tokens securely
            await self._store_tokens(access_token_data, state)

            # Clean up state if it was provided
            if state and state in self._oauth_states:
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
        """Exchange request token for access token using KiteConnect library."""
        try:
            # Import KiteConnect - run in executor since it's synchronous
            import asyncio
            from kiteconnect import KiteConnect
            
            api_key = getattr(self.config.integration, 'zerodha_api_key', '').strip()
            api_secret = getattr(self.config.integration, 'zerodha_api_secret', '').strip()
            
            if not api_key or not api_secret:
                raise TradingError(
                    "Zerodha API key or secret not configured",
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.HIGH,
                    recoverable=False
                )
            
            # Run synchronous KiteConnect operations in executor
            loop = asyncio.get_event_loop()
            
            def exchange_token():
                """Synchronous token exchange using KiteConnect."""
                try:
                    # Validate inputs
                    if not request_token or not request_token.strip():
                        raise ValueError("Request token is empty")
                    
                    request_token_clean = request_token.strip()
                    
                    # Verify API secret matches what's expected (common issue: wrong secret in .env)
                    # The API secret must match EXACTLY what's registered in Zerodha Kite Connect app
                    logger.info(f"Token exchange parameters:")
                    logger.info(f"  API Key: {api_key[:10]}... (length: {len(api_key)})")
                    logger.info(f"  Request Token: {request_token_clean[:20]}... (length: {len(request_token_clean)})")
                    logger.info(f"  API Secret: {'*' * min(8, len(api_secret))}... (length: {len(api_secret)})")
                    
                    # Calculate checksum manually for debugging
                    import hashlib
                    checksum_input = api_key + request_token_clean + api_secret
                    checksum = hashlib.sha256(checksum_input.encode('utf-8')).hexdigest()
                    logger.info(f"  Calculated checksum: {checksum[:32]}...")
                    
                    kite = KiteConnect(api_key=api_key)
                    
                    # Use generate_session() as per PyKiteConnect documentation
                    # NOTE: If this fails with "Invalid checksum", verify:
                    # 1. API secret in .env matches Zerodha Kite Connect app settings EXACTLY
                    # 2. API key matches the one used in auth URL
                    # 3. Request token is not expired (tokens expire after ~2 minutes)
                    # 4. Checksum calculation: checksum = sha256(api_key + request_token + api_secret)

                    logger.info(f"Calling kite.generate_session with:")
                    logger.info(f"  Request token: {request_token_clean[:10]}...")
                    logger.info(f"  API key: {api_key[:10]}...")

                    data = kite.generate_session(request_token=request_token_clean, api_secret=api_secret)
                    logger.info(f"generate_session succeeded. User: {data.get('user_id')}")
                    return data
                except Exception as e:
                    logger.error(f"generate_session failed: {type(e).__name__}: {str(e)}")
                    logger.error(f"  API Key length: {len(api_key) if api_key else 0}")
                    logger.error(f"  Request Token length: {len(request_token) if request_token else 0}")
                    logger.error(f"  API Secret length: {len(api_secret) if api_secret else 0}")
                    logger.error(f"  ⚠️  IMPORTANT: If checksum error persists, verify:")
                    logger.error(f"     1. API secret in .env matches Zerodha Kite Connect app EXACTLY")
                    logger.error(f"     2. API key matches the one used in auth URL")
                    logger.error(f"     3. Request token is fresh (not expired - tokens expire after ~2 minutes)")
                    # Re-raise to be caught by outer handler
                    raise
            
            # Execute in thread pool to avoid blocking
            token_data = await loop.run_in_executor(None, exchange_token)

            # Add expiry information
            login_time = datetime.now(timezone.utc)
            expires_at = login_time + timedelta(hours=24)  # Zerodha tokens last 24 hours

            logger.info(f"Successfully exchanged request token for access token. User: {token_data.get('user_id')}")

            return {
                "access_token": token_data.get("access_token"),
                "request_token": request_token,
                "user_id": token_data.get("user_id"),
                "login_time": login_time.isoformat(),
                "expires_at": expires_at.isoformat()
            }

        except ImportError as e:
            logger.error(f"kiteconnect library not installed: {e}")
            raise TradingError(
                "kiteconnect library not installed. Install with: pip install kiteconnect>=4.3.0",
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
                details=str(e)
            )
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            logger.error(f"Token exchange failed: {error_type}: {error_msg}")
            
            # Check if it's a KiteConnect exception
            try:
                from kiteconnect import KiteException
                if isinstance(e, KiteException):
                    logger.error(f"KiteConnect API error: {e.message if hasattr(e, 'message') else error_msg}")
                    error_msg = e.message if hasattr(e, 'message') else error_msg
            except ImportError:
                pass
            
            # Check if it's a known Zerodha error
            if "invalid" in error_msg.lower() or "expired" in error_msg.lower() or "session" in error_msg.lower() or "checksum" in error_msg.lower():
                raise TradingError(
                    f"OAuth session invalid or expired: {error_msg}",
                    category=ErrorCategory.API,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True,
                    retry_after_seconds=60
                )
            
            raise TradingError(
                f"Failed to exchange request token: {error_msg}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30
            )

    async def _store_tokens(self, token_data: Dict[str, Any], state: str) -> None:
        """Store OAuth tokens securely. Saves to both ENV file and token file."""
        try:
            # Add storage metadata
            token_data["stored_at"] = datetime.now(timezone.utc).isoformat()
            token_data["oauth_state"] = state

            # Save to ENV file first (primary storage)
            from ..core.env_helpers import save_zerodha_token_to_env
            env_saved = await save_zerodha_token_to_env(token_data)
            if env_saved:
                logger.info(f"Saved OAuth token to .env file for user: {token_data.get('user_id')}")
            else:
                logger.warning("Failed to save token to .env file, saving to token file only")

            # Also save to token file (backup)
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
        """Retrieve stored OAuth token if valid. Checks ENV first, then file."""
        try:
            # First check ENV variables
            from ..core.env_helpers import get_zerodha_token_from_env
            env_token = get_zerodha_token_from_env()
            if env_token:
                logger.info("Found Zerodha OAuth token in ENV variable")
                return env_token
            
            # Fallback to token file
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

            logger.info("Found Zerodha OAuth token in file")
            return token_data

        except Exception as e:
            logger.error(f"Failed to retrieve stored token: {e}")
            return None

    async def _token_file_exists(self) -> bool:
        """Check if token file exists."""
        import os
        return os.path.exists(self._token_file)

    async def _delete_token_file(self) -> None:
        """Delete stored token file and ENV variables."""
        try:
            # Remove from ENV file
            from ..core.env_helpers import remove_zerodha_token_from_env
            await remove_zerodha_token_from_env()
            
            # Remove token file
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
            await self.event_bus.publish(event)
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