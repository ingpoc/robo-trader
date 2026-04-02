"""Emergency control routes kept after removing system health endpoints."""

import os
from typing import Dict

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from ..dependencies import get_container
from ..utils.error_handlers import handle_trading_error, handle_unexpected_error

router = APIRouter(prefix="/api", tags=["monitoring"])
limiter = Limiter(key_func=get_remote_address)

default_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.post("/emergency/stop")
@limiter.limit(default_limit)
async def emergency_stop(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Emergency stop all trading."""

    try:
        lifecycle_coordinator = await container.get("lifecycle_coordinator")

        if lifecycle_coordinator:
            await lifecycle_coordinator.emergency_stop()
            return {
                "status": "success",
                "message": "Emergency stop activated",
            }

        return {
            "status": "error",
            "message": "Lifecycle coordinator not available",
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "emergency_stop")


@router.post("/emergency/resume")
@limiter.limit(default_limit)
async def emergency_resume(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Resume trading after emergency stop."""

    try:
        lifecycle_coordinator = await container.get("lifecycle_coordinator")

        if lifecycle_coordinator:
            await lifecycle_coordinator.resume_trading()
            return {
                "status": "success",
                "message": "Trading resumed",
            }

        return {
            "status": "error",
            "message": "Lifecycle coordinator not available",
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "emergency_resume")
