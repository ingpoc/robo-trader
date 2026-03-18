"""System monitoring and emergency routes."""

import logging
import os
from datetime import datetime, timezone
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


def _derive_overall_status(components: Dict[str, Dict[str, Any]]) -> str:
    """Collapse component statuses into one truthful summary."""
    statuses = [str(component.get("status", "unknown")).lower() for component in components.values()]

    if any(status == "error" for status in statuses):
        return "error"
    if any(status in {"degraded", "starting", "inactive", "stopped", "blocked"} for status in statuses):
        return "degraded"
    if any(status in {"healthy", "running", "connected", "active"} for status in statuses):
        return "healthy"
    return "idle"


def _component_blockers(components: Dict[str, Dict[str, Any]]) -> list[str]:
    """Convert non-healthy component states into operator-facing blockers."""
    blockers: list[str] = []
    for name, component in components.items():
        status = str(component.get("status", "unknown")).lower()
        if status in {"healthy", "connected", "active", "idle"}:
            continue

        summary = component.get("summary") or component.get("error") or f"{name.replace('_', ' ').title()} is {status}."
        blockers.append(str(summary))

    return blockers


@router.get("/monitoring/status")
@limiter.limit(default_limit)
async def get_system_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get real system monitoring status for mounted core components."""

    try:
        orchestrator = await container.get_orchestrator()
        state_manager = await container.get("state_manager")
        event_bus = await container.get("event_bus")
        background_scheduler = await container.get("background_scheduler")

        from ..app import initialization_status

        connection_manager = getattr(request.app.state, "connection_manager", None)
        orchestrator_init_task = getattr(request.app.state, "orchestrator_init_task", None)

        initialization_errors = initialization_status.get("initialization_errors", [])
        orchestrator_initialized = bool(initialization_status.get("orchestrator_initialized"))
        bootstrap_completed = bool(initialization_status.get("bootstrap_completed"))
        init_task_running = bool(orchestrator_init_task and not orchestrator_init_task.done())

        session_coordinator = getattr(orchestrator, "session_coordinator", None)
        claude_connected = False
        claude_authenticated = False
        if session_coordinator:
            try:
                lifecycle_coordinator = getattr(session_coordinator, "lifecycle_coordinator", None)
                if lifecycle_coordinator is not None:
                    claude_connected = bool(lifecycle_coordinator.is_connected())
                claude_authenticated = bool(session_coordinator.is_authenticated())
            except Exception:
                logger.debug("Failed to inspect Claude session status for monitoring summary", exc_info=True)

        if initialization_errors:
            orchestrator_component = {
                "status": "error",
                "summary": initialization_status.get("last_error") or "Orchestrator initialization failed.",
                "initialized": False,
                "bootstrap_completed": bootstrap_completed,
                "claude_authenticated": claude_authenticated,
                "claude_connected": claude_connected,
            }
        elif init_task_running:
            orchestrator_component = {
                "status": "starting",
                "summary": "Orchestrator initialization is still in progress.",
                "initialized": False,
                "bootstrap_completed": bootstrap_completed,
                "claude_authenticated": claude_authenticated,
                "claude_connected": claude_connected,
            }
        elif orchestrator_initialized:
            orchestrator_component = {
                "status": "healthy",
                "summary": "Orchestrator initialization completed successfully.",
                "initialized": True,
                "bootstrap_completed": bootstrap_completed,
                "claude_authenticated": claude_authenticated,
                "claude_connected": claude_connected,
            }
        else:
            orchestrator_component = {
                "status": "inactive",
                "summary": "Orchestrator has not been initialized.",
                "initialized": False,
                "bootstrap_completed": bootstrap_completed,
                "claude_authenticated": claude_authenticated,
                "claude_connected": claude_connected,
            }

        database_component = {
            "status": "error",
            "connection_state": "disconnected",
            "connections": 0,
            "portfolioLoaded": False,
            "summary": "Database connection is unavailable.",
        }
        if state_manager is not None:
            db_connection = getattr(getattr(state_manager, "db", None), "_connection_pool", None)
            if db_connection is not None:
                cursor = await db_connection.execute("SELECT 1")
                try:
                    await cursor.fetchone()
                finally:
                    await cursor.close()

                portfolio = await state_manager.get_portfolio()
                database_component = {
                    "status": "healthy",
                    "connection_state": "connected",
                    "connections": 1,
                    "portfolioLoaded": portfolio is not None,
                    "summary": "Database connection is active.",
                }
            else:
                database_component["summary"] = "Database connection pool is not initialized."

        scheduler_component = {
            "status": "error",
            "running": False,
            "ready": False,
            "summary": "Background scheduler is unavailable.",
        }
        if background_scheduler is not None:
            scheduler_status = await background_scheduler.get_scheduler_status()
            init_complete, init_error = background_scheduler.get_initialization_status()

            if init_error:
                scheduler_component = {
                    "status": "error",
                    "running": bool(scheduler_status.get("running")),
                    "ready": False,
                    "summary": f"Background scheduler failed initialization: {init_error}",
                    **scheduler_status,
                }
            elif scheduler_status.get("running") and background_scheduler.is_ready():
                scheduler_component = {
                    "status": "healthy",
                    "running": True,
                    "ready": True,
                    "summary": "Background scheduler is running.",
                    **scheduler_status,
                }
            elif init_complete and not scheduler_status.get("running"):
                scheduler_component = {
                    "status": "degraded",
                    "running": False,
                    "ready": True,
                    "summary": "Background scheduler initialized but is not running.",
                    **scheduler_status,
                }
            elif scheduler_status.get("event_driven") and not scheduler_status.get("running") and not init_task_running:
                scheduler_component = {
                    "status": "idle",
                    "running": False,
                    "ready": False,
                    "summary": "Background scheduler is intentionally idle; the active paper-trading workflow is event-driven.",
                    **scheduler_status,
                }
            else:
                scheduler_component = {
                    "status": "starting" if init_task_running else "inactive",
                    "running": bool(scheduler_status.get("running")),
                    "ready": False,
                    "summary": "Background scheduler has not completed startup.",
                    **scheduler_status,
                }

        websocket_clients = 0
        websocket_component = {
            "status": "idle",
            "clients": 0,
            "summary": "No WebSocket clients are currently connected.",
        }
        if connection_manager is not None:
            websocket_clients = await connection_manager.get_connection_count()
            websocket_component = {
                "status": "healthy" if websocket_clients > 0 else "idle",
                "clients": websocket_clients,
                "summary": (
                    f"{websocket_clients} WebSocket client(s) connected."
                    if websocket_clients > 0
                    else "No WebSocket clients are currently connected."
                ),
            }

        event_bus_component = {
            "status": "healthy" if event_bus is not None else "error",
            "summary": "Event bus is active." if event_bus is not None else "Event bus is unavailable.",
        }

        components = {
            "orchestrator": orchestrator_component,
            "database": database_component,
            "event_bus": event_bus_component,
            "background_scheduler": scheduler_component,
            "websocket": websocket_component,
        }

        return {
            "status": _derive_overall_status(components),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": components,
            "initialization": initialization_status,
            "blockers": _component_blockers(components),
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
            init_complete, init_error = background_scheduler.get_initialization_status()
            if init_error:
                background_state = "error"
            elif background_status.get("running", False):
                background_state = "running"
            elif background_status.get("event_driven", False) and not init_complete:
                background_state = "idle"
            elif init_complete:
                background_state = "idle"
            else:
                background_state = "stopped"
            schedulers.append({
                "scheduler_id": "background_scheduler",
                "name": "Background Scheduler",
                "status": background_state,
                "event_driven": background_status.get("event_driven", False),
                "uptime_seconds": background_status.get("uptime_seconds", 0),
                "jobs_processed": background_status.get("tasks_processed", 0),
                "jobs_failed": background_status.get("tasks_failed", 0),
                "active_jobs": 0,  # Background scheduler is event-driven, doesn't have traditional jobs
                "completed_jobs": background_status.get("tasks_processed", 0),
                "last_run_time": background_status.get("last_run_time", ""),
                "execution_history": background_status.get("execution_history", []),
                "total_executions": background_status.get("total_executions", 0),
                "jobs": []  # Background scheduler tasks are event-driven, not scheduled jobs
            })

        # 2. Queue-based Schedulers (Three Queue Architecture)
        task_service = await container.get("task_service")
        if task_service:
            from ...models.scheduler import QueueName

            # Get statistics for all queues
            queue_stats = await task_service.get_all_queue_statistics()

            for queue_name, stats in queue_stats.items():
                # Calculate success rate (backend should own this calculation)
                total_jobs = stats.completed_today + stats.failed_count
                success_rate = ((stats.completed_today / total_jobs) * 100) if total_jobs > 0 else 100.0

                schedulers.append({
                    "scheduler_id": f"{queue_name}_scheduler",
                    "name": f"{queue_name.replace('_', ' ').title()} Scheduler",
                    "status": "running",  # Queues are always running if service is available
                    "event_driven": False,
                    "uptime_seconds": 0,  # TODO: Track queue uptime (Phase 3)
                    "jobs_processed": stats.completed_today,
                    "jobs_failed": stats.failed_count,
                    "success_rate": round(success_rate, 1),  # Pre-calculated success rate
                    "active_jobs": stats.running_count,
                    "completed_jobs": stats.completed_today,
                    "last_run_time": stats.last_completed_at or "",
                    "jobs": []  # TODO: Could add recent tasks if needed (Phase 3)
                })

        # Add execution history for each processor type from execution tracker
        try:
            execution_tracker = await container.get("execution_tracker")
            if execution_tracker:
                # Get recent executions
                all_executions = await execution_tracker.get_execution_history(50)

                # Group executions by task_name
                executions_by_task = {}
                for execution in all_executions:
                    task_name = execution["task_name"]
                    if task_name not in executions_by_task:
                        executions_by_task[task_name] = []
                    executions_by_task[task_name].append(execution)

                # Add execution history to relevant schedulers
                for scheduler in schedulers:
                    scheduler_id = scheduler["scheduler_id"]

                    # Map scheduler IDs to task names in execution_history
                    processor_mapping = {
                        "portfolio_sync_scheduler": "portfolio_sync",
                        "data_fetcher_scheduler": ["earnings_processor", "news_processor", "fundamental_analyzer"],
                        "ai_analysis_scheduler": "ai_analysis_scheduler",
                        "portfolio_analysis_scheduler": "portfolio_analyzer",
                        "paper_trading_research_scheduler": "paper_trading_research_scheduler",
                        "paper_trading_execution_scheduler": "paper_trading_execution_scheduler"
                    }

                    if scheduler_id in processor_mapping:
                        processor_names = processor_mapping[scheduler_id]
                        if isinstance(processor_names, str):
                            processor_names = [processor_names]

                        # Collect executions for this scheduler's processors
                        scheduler_executions = []
                        for processor_name in processor_names:
                            if processor_name in executions_by_task:
                                scheduler_executions.extend(executions_by_task[processor_name])

                        # Sort by timestamp (most recent first) and limit to 10
                        scheduler_executions.sort(key=lambda x: x["timestamp"], reverse=True)
                        scheduler["execution_history"] = scheduler_executions[:10]
                        scheduler["total_executions"] = len(scheduler_executions)

        except Exception as e:
            logger.warning(f"Failed to add execution history to schedulers: {e}")

        return {
            "status": "running",
            "schedulers": schedulers,
            "total_schedulers": len(schedulers)
        }
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
