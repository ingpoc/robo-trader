"""Zerodha OAuth authentication routes.

Handles OAuth flow with Zerodha Kite Connect API including
authorization URL generation, callback handling, and token management.
"""

import logging
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from src.core.event_bus import EventType
from src.web.dependencies import get_container
from src.web.utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth/zerodha", tags=["zerodha-auth"])
limiter = Limiter(key_func=get_remote_address)

auth_limit = os.getenv("RATE_LIMIT_AUTH", "10/minute")


@router.get("/login")
@limiter.limit(auth_limit)
async def initiate_zerodha_auth(
    request: Request,
    user_id: Optional[str] = None,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Initiate Zerodha OAuth authentication flow.

    Returns authorization URL and state parameter for CSRF protection.
    """
    try:
        oauth_service = await container.get("zerodha_oauth_service")

        # Generate authorization URL
        auth_data = await oauth_service.generate_auth_url(user_id=user_id)

        logger.info(f"Initiated Zerodha OAuth flow for user: {user_id}")

        return {
            "success": True,
            "auth_url": auth_data["auth_url"],
            "state": auth_data["state"],
            "redirect_url": auth_data["redirect_url"],
            "message": "Please visit the authorization URL to authenticate with Zerodha"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "initiate_zerodha_auth")


@router.get("/callback")
@limiter.limit(auth_limit)
async def zerodha_oauth_callback(
    request: Request,
    request_token: str = Query(..., description="Request token from Zerodha"),
    state: Optional[str] = Query(None, description="State parameter for CSRF validation (optional)"),
    status: Optional[str] = Query(None, description="Optional status parameter"),
    container: DependencyContainer = Depends(get_container)
) -> JSONResponse:
    """
    Handle OAuth callback from Zerodha.

    This endpoint receives the callback after user authorization.
    It validates the state parameter (if provided) and exchanges the request token for an access token.
    """
    try:
        # Check for error status
        if status == "error":
            logger.error(f"Zerodha OAuth error callback received: {request_token}")
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "OAuth authorization failed",
                    "message": "Please check your Zerodha app configuration and try again"
                }
            )

        oauth_service = await container.get("zerodha_oauth_service")

        # Handle the OAuth callback (state is optional - Zerodha may not always send it)
        result = await oauth_service.handle_callback(request_token, state)

        logger.info("Zerodha OAuth authentication successful")

        # Automatically trigger portfolio scan after successful authentication
        try:
            logger.info("Auto-triggering portfolio scan after OAuth success...")
            orchestrator = await container.get_orchestrator()
            if orchestrator:
                # Run portfolio scan in background
                scan_result = await orchestrator.run_portfolio_scan()
                logger.info(f"Portfolio scan completed after OAuth: {scan_result.get('source', 'unknown')}")
            else:
                logger.warning("Orchestrator not available for auto portfolio scan")
        except Exception as e:
            logger.error(f"Failed to auto-trigger portfolio scan after OAuth: {e}", exc_info=True)
            # Don't fail the OAuth callback if portfolio scan fails

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "Successfully authenticated with Zerodha. Portfolio scan initiated automatically.",
                "user_id": result["user_id"],
                "login_time": result["login_time"],
                "expires_at": result["expires_at"],
                "portfolio_scan_triggered": True
            }
        )

    except TradingError as e:
        logger.error(f"Zerodha OAuth callback error: {e}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": e.context.message if hasattr(e, 'context') else "OAuth authentication failed",
                "message": "Please try the authentication process again"
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error in OAuth callback: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Internal server error during OAuth callback",
                "message": "Please try again or contact support"
            }
        )


@router.get("/status")
@limiter.limit(auth_limit)
async def get_zerodha_auth_status(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Get current Zerodha authentication status.

    Returns information about stored tokens and their validity.
    """
    try:
        oauth_service = await container.get("zerodha_oauth_service")

        # Check for stored valid token
        token_data = await oauth_service.get_stored_token()

        if not token_data:
            return {
                "authenticated": False,
                "message": "No active Zerodha authentication found"
            }

        # Calculate remaining time
        from datetime import datetime, timezone
        expires_at = datetime.fromisoformat(token_data["expires_at"])
        remaining_time = expires_at - datetime.now(timezone.utc)

        return {
            "authenticated": True,
            "user_id": token_data["user_id"],
            "login_time": token_data["login_time"],
            "expires_at": token_data["expires_at"],
            "expires_in_hours": remaining_time.total_seconds() / 3600,
            "message": "Active Zerodha authentication found"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_zerodha_auth_status")


@router.post("/logout")
@limiter.limit(auth_limit)
async def logout_zerodha(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Logout from Zerodha and clear stored tokens.
    """
    try:
        oauth_service = await container.get("zerodha_oauth_service")

        # Logout and clear tokens
        await oauth_service.logout()

        logger.info("Zerodha OAuth logout successful")

        return {
            "success": True,
            "message": "Successfully logged out from Zerodha"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "logout_zerodha")


@router.get("/redirect-info")
@limiter.limit(auth_limit)
async def get_redirect_info(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Get redirect URL information for current environment.

    Useful for frontend to understand which redirect URL will be used.
    """
    try:
        oauth_service = await container.get("zerodha_oauth_service")

        redirect_url = oauth_service.get_redirect_url()

        return {
            "environment": oauth_service.config.environment,
            "redirect_url": redirect_url,
            "message": "Redirect URL for current environment"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_redirect_info")


# HTML callback page for user-friendly error handling
@router.get("/callback-page")
async def oauth_callback_page(
    request: Request,
    request_token: Optional[str] = None,
    state: Optional[str] = None,
    status: Optional[str] = None
) -> str:
    """
    HTML page for OAuth callback handling.

    This provides a user-friendly interface for OAuth results.
    """
    try:
        if status == "error" or not request_token:
            return """
            <!DOCTYPE html>
            <html>
            <head>
                <title>Authentication Failed</title>
                <style>
                    body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                    .error { color: #e74c3c; }
                    .success { color: #27ae60; }
                </style>
            </head>
            <body>
                <h1 class="error">Authentication Failed</h1>
                <p>Could not authenticate with Zerodha. Please try again.</p>
                <p>If the problem persists, check your app configuration in Zerodha developer console.</p>
                <script>
                    setTimeout(() => {
                        window.close();
                    }, 5000);
                </script>
            </body>
            </html>
            """

        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Authentication Successful</title>
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .success { color: #27ae60; }
            </style>
        </head>
        <body>
            <h1 class="success">Authentication Successful!</h1>
            <p>You have successfully authenticated with Zerodha.</p>
            <p>You can close this window and return to the application.</p>
            <script>
                setTimeout(() => {
                    window.close();
                }, 3000);
            </script>
        </body>
        </html>
        """

    except Exception as e:
        logger.error(f"Error generating callback page: {e}")
        return "<html><body><h1>Error</h1><p>An unexpected error occurred.</p></body></html>"