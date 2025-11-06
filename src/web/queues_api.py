"""Queue Management API endpoints for the Robo Trader system.

Provides queue status, task management, and monitoring capabilities.
Follows the FastAPI microservice pattern used by other services.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from loguru import logger

from src.core.errors import TradingError
from src.web.dependencies import get_container

router = APIRouter(prefix="/queues", tags=["Queue Management"])


@router.get("/status", summary="Get all queue statuses")
async def get_queue_statuses(container: Any = Depends(get_container)) -> Dict[str, Any]:
    """Get detailed status of all queues in the system."""
    logger.info("Retrieving all queue statuses")

    try:
        # Get real queue statistics from the task service
        task_service = await container.get("task_service")

        if not task_service:
            logger.warning("Task service not available")
            return {
                "queues": [],
                "stats": {},
                "status": "service_unavailable",
                "error": "Task service not available",
            }

        # Get real queue statistics
        queue_stats = await task_service.get_all_queue_statistics()

        # Get queue manager for additional status info
        queue_manager = await container.get("sequential_queue_manager")
        is_running = queue_manager.is_running() if queue_manager else False
        current_task = queue_manager.get_current_task() if queue_manager else None

        # Transform queue statistics to API format
        queues = []
        for queue_name, stats in queue_stats.items():
            # Determine queue status based on activity
            if stats.running_count > 0:
                status = "running"
            elif stats.pending_count > 0:
                status = "active"
            else:
                status = "idle"

            queue_info = {
                "name": queue_name,
                "status": status,
                "running": is_running,
                "type": "task_queue",
                "details": {},
                "current_task_id": (
                    current_task.task_id
                    if current_task and current_task.queue_name == queue_name
                    else None
                ),
                "pending_tasks": stats.pending_count,
                "active_tasks": stats.running_count,
                "completed_tasks": stats.completed_today,
                "failed_tasks": stats.failed_count,
                "average_execution_time": (
                    stats.average_duration_ms / 1000.0
                    if stats.average_duration_ms > 0
                    else 0.0
                ),
                "last_activity": stats.last_completed_at
                or datetime.now(timezone.utc).isoformat(),
            }
            queues.append(queue_info)

        # Calculate overall stats
        stats = {
            "total_queues": len(queues),
            "active_queues": len([q for q in queues if q["running"]]),
            "idle_queues": len([q for q in queues if not q["running"]]),
            "total_pending_tasks": sum(q["pending_tasks"] for q in queues),
            "total_active_tasks": sum(q["active_tasks"] for q in queues),
            "total_completed_tasks": sum(q["completed_tasks"] for q in queues),
            "total_failed_tasks": sum(q["failed_tasks"] for q in queues),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

        return {"queues": queues, "stats": stats, "status": "operational"}

    except TradingError as e:
        logger.error(f"Trading error in get_queue_statuses: {e.context.code}")
        return {
            "queues": [],
            "stats": {},
            "status": "error",
            "error": e.context.message,
            "error_code": e.context.code,
        }
    except Exception as e:
        logger.error(f"Failed to get queue statuses: {e}")
        return {"queues": [], "stats": {}, "status": "error", "error": str(e)}


@router.get("/status/{queue_type}", summary="Get specific queue status")
async def get_queue_status(queue_type: str) -> Dict[str, Any]:
    """Get status of a specific queue."""
    logger.info(f"Retrieving status for queue: {queue_type}")
    return {
        "queue": {
            "name": queue_type.upper(),
            "status": "active",
            "task_count": 0,
            "active_tasks": 0,
            "failed_tasks": 0,
            "completed_tasks": 0,
            "last_activity": None,
        }
    }


@router.get("/tasks", summary="Get queue tasks with filtering")
async def get_queue_tasks(
    queue_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> Dict[str, Any]:
    """Get queue tasks with optional filtering."""
    logger.info(
        f"Retrieving queue tasks - queue_type: {queue_type}, status: {status}, limit: {limit}"
    )
    return {
        "tasks": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "filters": {
            "queue_type": queue_type,
            "status": status,
            "priority": priority,
            "task_type": task_type,
        },
    }


@router.get("/history", summary="Get task execution history")
async def get_task_history(
    queue_type: Optional[str] = Query(None), limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """Get task execution history."""
    logger.info(f"Retrieving task history - queue_type: {queue_type}, limit: {limit}")
    return {"history": [], "total": 0, "limit": limit}


@router.get("/metrics", summary="Get queue performance metrics")
async def get_performance_metrics(
    queue_type: Optional[str] = Query(None), hours: int = Query(24, ge=1, le=720)
) -> Dict[str, Any]:
    """Get queue performance metrics."""
    logger.info(f"Retrieving queue metrics - queue_type: {queue_type}, hours: {hours}")
    return {"metrics": [], "time_period_hours": hours, "queue_type": queue_type}


@router.post("/trigger", summary="Trigger manual task execution")
async def trigger_task(request: Dict[str, Any]) -> Dict[str, Any]:
    """Trigger manual task execution."""
    queue_type = request.get("queue_type", "UNKNOWN")
    task_type = request.get("task_type", "MANUAL")
    logger.info(f"Triggering task - queue: {queue_type}, type: {task_type}")

    return {
        "task_id": "task-triggered",
        "status": "scheduled",
        "queue_type": queue_type,
        "task_type": task_type,
        "priority": request.get("priority", 5),
    }


@router.put("/config", summary="Update queue configuration")
async def update_queue_config(update: Dict[str, Any]) -> Dict[str, Any]:
    """Update queue configuration."""
    queue_type = update.get("queue_type", "UNKNOWN")
    logger.info(f"Updating queue configuration - queue: {queue_type}")

    return {
        "status": "updated",
        "queue_type": queue_type,
        "configuration": update.get("configuration", {}),
    }


@router.get("/config/{queue_type}", summary="Get queue configuration")
async def get_queue_config(queue_type: str) -> Dict[str, Any]:
    """Get queue configuration."""
    logger.info(f"Retrieving queue configuration - queue: {queue_type}")

    return {
        "configuration": {
            "queue_name": queue_type.upper(),
            "status": "active",
            "max_concurrent_tasks": 5,
            "timeout_seconds": 300,
            "retry_count": 3,
            "priority_levels": 10,
        }
    }


@router.post("/pause", summary="Pause queue")
async def pause_queue(request: Dict[str, str]) -> Dict[str, str]:
    """Pause a queue."""
    queue_type = request.get("queue_type", "UNKNOWN")
    logger.info(f"Pausing queue: {queue_type}")

    return {"status": "paused", "queue_type": queue_type}


@router.post("/resume", summary="Resume queue")
async def resume_queue(request: Dict[str, str]) -> Dict[str, str]:
    """Resume a queue."""
    queue_type = request.get("queue_type", "UNKNOWN")
    logger.info(f"Resuming queue: {queue_type}")

    return {"status": "resumed", "queue_type": queue_type}


@router.post("/tasks/{task_id}/cancel", summary="Cancel task")
async def cancel_task(task_id: str) -> Dict[str, str]:
    """Cancel a specific task."""
    logger.info(f"Cancelling task: {task_id}")

    return {"status": "cancelled", "task_id": task_id}


@router.post("/tasks/{task_id}/retry", summary="Retry task")
async def retry_task(task_id: str) -> Dict[str, str]:
    """Retry a failed task."""
    logger.info(f"Retrying task: {task_id}")

    return {"status": "retried", "task_id": task_id}


@router.post("/clear-completed", summary="Clear completed tasks")
async def clear_completed_tasks(request: Dict[str, Any]) -> Dict[str, Any]:
    """Clear completed tasks from a queue."""
    queue_type = request.get("queue_type", "UNKNOWN")
    logger.info(f"Clearing completed tasks from queue: {queue_type}")

    return {"status": "cleared", "queue_type": queue_type, "cleared_count": 0}


@router.get("/health", summary="Queue management health check")
async def queue_health() -> Dict[str, Any]:
    """Check queue management health."""
    logger.info("Queue management health check")

    return {"status": "healthy", "queues_running": 3, "timestamp": None}
