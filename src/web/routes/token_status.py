"""
Token Status API Routes

Provides endpoints for monitoring token status, expiry warnings,
and manual token refresh operations.
"""

from datetime import datetime, timezone
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from loguru import logger

from src.core.di import DependencyContainer
from src.web.dependencies import get_container

router = APIRouter(prefix="/api/tokens", tags=["tokens"])


@router.get("/status")
async def get_token_status(container: DependencyContainer = Depends(get_container)) -> JSONResponse:
    """
    Get current token status and monitoring information.

    Returns:
        Token status including expiry, warnings, and refresh requirements
    """
    try:
        token_manager = await container.get("token_refresh_manager")
        token_info = await token_manager.get_token_status()
        monitoring_status = token_manager.get_monitoring_status()

        response_data = {
            "token_info": {
                "status": token_info.status.value if token_info else "no_token",
                "user_id": token_info.user_id if token_info else None,
                "expires_at": token_info.expires_at.isoformat() if token_info else None,
                "time_to_expiry_minutes": int(token_info.time_to_expiry.total_seconds() / 60) if token_info else None,
                "source": token_info.source if token_info else None,
                "last_checked": token_info.last_checked.isoformat() if token_info else None
            },
            "monitoring": monitoring_status,
            "recommendations": _get_token_recommendations(token_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "message": "Token status retrieved successfully"
            }
        )

    except Exception as e:
        logger.error(f"Failed to get token status: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve token status"
            }
        )


@router.post("/check")
async def force_token_check(container: DependencyContainer = Depends(get_container)) -> JSONResponse:
    """
    Force an immediate token status check.

    Returns:
        Updated token status after manual check
    """
    try:
        token_manager = await container.get("token_refresh_manager")
        token_info = await token_manager.force_token_check()

        response_data = {
            "token_info": {
                "status": token_info.status.value,
                "user_id": token_info.user_id,
                "expires_at": token_info.expires_at.isoformat(),
                "time_to_expiry_minutes": int(token_info.time_to_expiry.total_seconds() / 60),
                "source": token_info.source,
                "last_checked": token_info.last_checked.isoformat()
            },
            "recommendations": _get_token_recommendations(token_info),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "message": "Token check completed successfully"
            }
        )

    except Exception as e:
        logger.error(f"Failed to force token check: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to perform token check"
            }
        )


@router.get("/health")
async def get_token_health(container: DependencyContainer = Depends(get_container)) -> JSONResponse:
    """
    Get token health status for system health monitoring.

    Returns:
        Simplified health status for monitoring systems
    """
    try:
        token_manager = await container.get("token_refresh_manager")
        token_info = await token_manager.get_token_status()
        monitoring_status = token_manager.get_monitoring_status()

        # Determine health status
        if not token_info:
            health_status = "unhealthy"
            health_message = "No token available"
        elif token_info.status.value == "expired":
            health_status = "unhealthy"
            health_message = "Token expired"
        elif token_info.status.value == "expiring_soon":
            health_status = "degraded"
            health_message = f"Token expiring in {int(token_info.time_to_expiry.total_seconds() / 60)} minutes"
        else:
            health_status = "healthy"
            health_message = "Token valid"

        # Check monitoring status
        if monitoring_status["refresh_failure_count"] >= 3:
            health_status = "degraded"
            health_message += " (multiple refresh failures)"

        response_data = {
            "status": health_status,
            "message": health_message,
            "details": {
                "token_status": token_info.status.value if token_info else "no_token",
                "time_to_expiry_minutes": int(token_info.time_to_expiry.total_seconds() / 60) if token_info else None,
                "monitoring_enabled": monitoring_status["monitoring_enabled"],
                "last_refresh_attempt": monitoring_status["last_refresh_attempt"],
                "refresh_failure_count": monitoring_status["refresh_failure_count"]
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "data": response_data,
                "message": f"Token health: {health_message}"
            }
        )

    except Exception as e:
        logger.error(f"Failed to get token health: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Failed to retrieve token health"
            }
        )


def _get_token_recommendations(token_info) -> list[str]:
    """Get token-related recommendations based on current status."""
    recommendations = []

    if not token_info:
        recommendations.append("No token available - please authenticate with Zerodha")
        recommendations.append("Visit /api/auth/zerodha/login to start OAuth flow")
        return recommendations

    if token_info.status.value == "expired":
        recommendations.append("Token has expired - immediate re-authentication required")
        recommendations.append("Visit /api/auth/zerodha/login to generate new token")
        recommendations.append("System will operate with cached data until re-authenticated")

    elif token_info.status.value == "expiring_soon":
        minutes_to_expiry = int(token_info.time_to_expiry.total_seconds() / 60)
        if minutes_to_expiry < 60:
            recommendations.append(f"Token expires in {minutes_to_expiry} minutes - immediate refresh recommended")
        else:
            recommendations.append(f"Token expires in {minutes_to_expiry} minutes - plan for refresh")
        recommendations.append("Visit /api/auth/zerodha/login to generate new token")

    elif token_info.status.value == "valid":
        recommendations.append("Token is valid and active")
        minutes_to_expiry = int(token_info.time_to_expiry.total_seconds() / 60)
        if minutes_to_expiry < 180:  # Less than 3 hours
            recommendations.append(f"Token expires in {minutes_to_expiry} minutes - consider refresh soon")

    elif token_info.status.value == "error":
        recommendations.append("Token validation failed - check configuration")
        recommendations.append("Verify ZERODHA_API_KEY and ZERODHA_ACCESS_TOKEN environment variables")
        recommendations.append("Visit /api/auth/zerodha/login to re-authenticate")

    return recommendations