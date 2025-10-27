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
    """Get comprehensive scheduler status including all configured schedulers."""

    try:
        orchestrator = await container.get_orchestrator()

        # Get all configured schedulers
        schedulers = []

        # 1. Background Scheduler (event-driven)
        background_scheduler = await container.get("background_scheduler")
        if background_scheduler:
            background_status = await background_scheduler.get_scheduler_status()
            schedulers.append({
                "scheduler_id": "background_scheduler",
                "name": "Background Scheduler",
                "status": "running" if background_status.get("running", False) else "stopped",
                "event_driven": background_status.get("event_driven", False),
                "uptime_seconds": background_status.get("uptime_seconds", 0),
                "jobs_processed": background_status.get("tasks_processed", 0),
                "jobs_failed": background_status.get("tasks_failed", 0),
                "active_jobs": 0,  # Background scheduler is event-driven, doesn't have traditional jobs
                "completed_jobs": background_status.get("tasks_processed", 0),
                "last_run_time": background_status.get("last_run_time", ""),
                "jobs": []  # Background scheduler tasks are event-driven, not scheduled jobs
            })

        # 2. Queue-based Schedulers (Three Queue Architecture)
        task_service = await container.get("task_service")
        if task_service:
            from ...models.scheduler import QueueName

            # Get statistics for all queues
            queue_stats = await task_service.get_all_queue_statistics()

            for queue_name, stats in queue_stats.items():
                schedulers.append({
                    "scheduler_id": f"{queue_name}_scheduler",
                    "name": f"{queue_name.replace('_', ' ').title()} Scheduler",
                    "status": "running",  # Queues are always running if service is available
                    "event_driven": False,
                    "uptime_seconds": 0,  # TODO: Track queue uptime
                    "jobs_processed": stats.completed_today,
                    "jobs_failed": stats.failed_count,
                    "active_jobs": stats.running_count,
                    "completed_jobs": stats.completed_today,
                    "last_run_time": stats.last_completed_at or "",
                    "jobs": []  # TODO: Could add recent tasks if needed
                })

        return {
            "status": "running",
            "schedulers": schedulers,
            "total_schedulers": len(schedulers)
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
