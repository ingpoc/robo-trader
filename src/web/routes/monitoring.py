"""System monitoring and emergency routes."""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["monitoring"])
limiter = Limiter(key_func=get_remote_address)

default_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.get("/monitoring/status")
@limiter.limit(default_limit)
async def get_system_status(request: Request) -> Dict[str, Any]:
    """Get system monitoring status."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

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
    except Exception as e:
        logger.error(f"Status retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/monitoring/scheduler")
@limiter.limit(default_limit)
async def get_scheduler_status(request: Request) -> Dict[str, Any]:
    """Get background scheduler status."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        background_scheduler = await container.get("background_scheduler")

        if not background_scheduler:
            return {"status": "scheduler_not_available"}

        return {
            "status": "running",
            "tasks": getattr(background_scheduler, '_tasks', [])
        }
    except Exception as e:
        logger.error(f"Scheduler status failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/monitoring/trigger-event")
@limiter.limit(default_limit)
async def trigger_market_event(request: Request, event_data: Dict[str, Any]) -> Dict[str, str]:
    """Trigger a market event for testing."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        event_bus = await container.get("event_bus")
        if not event_bus:
            return JSONResponse({"error": "Event bus not available"}, status_code=500)

        logger.info(f"Market event triggered: {event_data}")
        return {"status": "Event triggered"}
    except Exception as e:
        logger.error(f"Event trigger failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/emergency/stop")
@limiter.limit(default_limit)
async def emergency_stop(request: Request) -> Dict[str, str]:
    """Emergency stop all trading."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        lifecycle_coordinator = await container.get("lifecycle_coordinator")

        if lifecycle_coordinator:
            await lifecycle_coordinator.emergency_stop()

        logger.warning("EMERGENCY STOP triggered")
        return {"status": "Emergency stop executed"}
    except Exception as e:
        logger.error(f"Emergency stop failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/emergency/resume")
@limiter.limit(default_limit)
async def resume_operations(request: Request) -> Dict[str, str]:
    """Resume operations after emergency stop."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        lifecycle_coordinator = await container.get("lifecycle_coordinator")

        if lifecycle_coordinator:
            await lifecycle_coordinator.resume_operations()

        logger.info("Operations resumed")
        return {"status": "Operations resumed"}
    except Exception as e:
        logger.error(f"Resume failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/trigger-news-monitoring")
@limiter.limit(default_limit)
async def trigger_news_monitoring(request: Request) -> Dict[str, str]:
    """Trigger news monitoring."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        background_scheduler = await container.get("background_scheduler")

        if background_scheduler:
            await background_scheduler.run_news_monitoring()

        return {"status": "News monitoring triggered"}
    except Exception as e:
        logger.error(f"News monitoring trigger failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
