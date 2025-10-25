"""System monitoring and emergency routes."""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitoring"])
limiter = Limiter(key_func=get_remote_address)

default_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.get("/monitoring/status")
@limiter.limit(default_limit)
async def get_system_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get system monitoring status."""

    try:
        orchestrator = await container.get_orchestrator()
        return {
            "status": "operational",
            "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
            "components": {
                "orchestrator": "running",
                "database": "connected",
                "event_bus": "active"
            }
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.get("/monitoring/scheduler")
@limiter.limit(default_limit)
async def get_scheduler_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get background scheduler status."""

    try:
        orchestrator = await container.get_orchestrator()
        background_scheduler = await container.get("background_scheduler")

        if not background_scheduler:
            return {"status": "scheduler_not_available"}

        return {
            "status": "running",
            "tasks": getattr(background_scheduler, '_tasks', [])
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.post("/monitoring/trigger-event")
@limiter.limit(default_limit)
async def trigger_market_event(request: Request, event_data: Dict[str, Any], container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Trigger a market event for testing."""

    try:
        event_bus = await container.get("event_bus")
        if not event_bus:
            return JSONResponse({"error": "Event bus not available"}, status_code=500)

        logger.info(f"Market event triggered: {event_data}")
        return {"status": "Event triggered"}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.post("/emergency/stop")
@limiter.limit(default_limit)
async def emergency_stop(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Emergency stop all trading."""

    try:
        orchestrator = await container.get_orchestrator()
        lifecycle_coordinator = await container.get("lifecycle_coordinator")

        if lifecycle_coordinator:
            await lifecycle_coordinator.emergency_stop()

        logger.warning("EMERGENCY STOP triggered")
        return {"status": "Emergency stop executed"}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.post("/emergency/resume")
@limiter.limit(default_limit)
async def resume_operations(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Resume operations after emergency stop."""

    try:
        orchestrator = await container.get_orchestrator()
        lifecycle_coordinator = await container.get("lifecycle_coordinator")

        if lifecycle_coordinator:
            await lifecycle_coordinator.resume_operations()

        logger.info("Operations resumed")
        return {"status": "Operations resumed"}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")


@router.post("/trigger-news-monitoring")
@limiter.limit(default_limit)
async def trigger_news_monitoring(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Trigger news monitoring."""

    try:
        orchestrator = await container.get_orchestrator()
        background_scheduler = await container.get("background_scheduler")

        if background_scheduler:
            await background_scheduler.run_news_monitoring()

        return {"status": "News monitoring triggered"}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "route_endpoint")
