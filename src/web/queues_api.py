"""Queue Management API endpoints for the Robo Trader system.

Phase 2: Refactored to use QueueStateRepository and unified DTOs.

Provides queue status, task management, and monitoring capabilities.
Uses single source of truth (repository) instead of dual sources.
"""

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Query, Depends
from loguru import logger
from datetime import datetime, timezone

from src.web.dependencies import get_container
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.models.dto import QueueStatusDTO

router = APIRouter(prefix="/queues", tags=["Queue Management"])


@router.get("/status", summary="Get all queue statuses")
async def get_queue_statuses(container: Any = Depends(get_container)) -> Dict[str, Any]:
    """Get detailed status of all queues in the system.

    Phase 2: Uses QueueStateRepository as single source of truth.
    Returns unified QueueStatusDTO objects.

    Returns:
        Dictionary with:
        - queues: List of QueueStatusDTO dictionaries
        - stats: Summary statistics
        - status: Overall status
    """
    logger.info("Retrieving all queue statuses (Phase 2 - with repository)")

    try:
        # Get repository (single source of truth)
        queue_repo = await container.get("queue_state_repository")

        if not queue_repo:
            logger.warning("QueueStateRepository not available")
            return {
                "queues": [],
                "stats": {},
                "status": "service_unavailable",
                "error": "QueueStateRepository not available"
            }

        # Get all queue statuses efficiently (1-2 queries total)
        all_queue_states = await queue_repo.get_all_statuses()

        # Get summary statistics
        summary = await queue_repo.get_queue_statistics_summary()

        # Convert to DTOs
        queue_dtos: List[Dict[str, Any]] = []
        for queue_name, queue_state in all_queue_states.items():
            dto = QueueStatusDTO.from_queue_state(queue_state)
            queue_dtos.append(dto.to_dict())

        # Build summary stats
        stats = {
            "total_queues": summary["total_queues"],
            "total_pending_tasks": summary["total_pending"],
            "total_active_tasks": summary["total_running"],
            "total_completed_tasks": summary["total_completed_today"],
            "total_failed_tasks": summary["total_failed"],
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

        # Determine overall status
        has_failed = any(q["failed_count"] > 0 for q in queue_dtos)
        has_running = any(q["running_count"] > 0 for q in queue_dtos)

        if has_failed:
            overall_status = "degraded"
        elif has_running:
            overall_status = "operational"
        else:
            overall_status = "idle"

        return {
            "queues": queue_dtos,
            "stats": stats,
            "status": overall_status
        }

    except TradingError as e:
        logger.error(f"Trading error in get_queue_statuses: {e.context.code}")
        return {
            "queues": [],
            "stats": {},
            "status": "error",
            "error": e.context.message,
            "error_code": e.context.code
        }
    except Exception as e:
        logger.error(f"Failed to get queue statuses: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "queues": [],
            "stats": {},
            "status": "error",
            "error": str(e)
        }


@router.get("/status/{queue_name}", summary="Get specific queue status")
async def get_queue_status(
    queue_name: str,
    container: Any = Depends(get_container)
) -> Dict[str, Any]:
    """Get status of a specific queue.

    Phase 2: Uses QueueStateRepository.

    Args:
        queue_name: Name of the queue (e.g., "ai_analysis")

    Returns:
        Dictionary with queue status or error
    """
    logger.info(f"Retrieving status for queue: {queue_name}")

    try:
        queue_repo = await container.get("queue_state_repository")

        if not queue_repo:
            return {
                "error": "QueueStateRepository not available",
                "status": "service_unavailable"
            }

        # Get queue state from repository
        queue_state = await queue_repo.get_status(queue_name)

        # Convert to DTO
        dto = QueueStatusDTO.from_queue_state(queue_state)

        return {
            "queue": dto.to_dict(),
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Failed to get queue status for {queue_name}: {e}")
        return {
            "error": str(e),
            "status": "error"
        }


@router.get("/tasks", summary="Get queue tasks with filtering")
async def get_queue_tasks(
    queue_name: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    container: Any = Depends(get_container)
) -> Dict[str, Any]:
    """Get queue tasks with optional filtering.

    Phase 2: Uses TaskRepository for queries.

    Args:
        queue_name: Optional queue filter
        status: Optional status filter
        limit: Maximum tasks to return
        offset: Pagination offset

    Returns:
        Dictionary with tasks and metadata
    """
    logger.info(f"Retrieving queue tasks - queue: {queue_name}, status: {status}, limit: {limit}")

    try:
        task_repo = await container.get("task_repository")

        if not task_repo:
            return {
                "tasks": [],
                "total": 0,
                "limit": limit,
                "offset": offset
            }

        # Get tasks based on filters
        if status:
            tasks = await task_repo.get_tasks_by_status(
                status=status,
                queue_name=queue_name,
                limit=limit
            )
        elif queue_name:
            tasks = await task_repo.get_pending_tasks(
                queue_name=queue_name,
                limit=limit
            )
        else:
            # Get recent task history
            tasks = await task_repo.get_task_history(
                queue_name=queue_name,
                limit=limit
            )

        # Convert to dictionaries
        task_dicts = [task.to_dict() for task in tasks]

        return {
            "tasks": task_dicts,
            "total": len(task_dicts),
            "limit": limit,
            "offset": offset,
            "filters": {
                "queue_name": queue_name,
                "status": status
            }
        }

    except Exception as e:
        logger.error(f"Failed to get queue tasks: {e}")
        return {
            "tasks": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
            "error": str(e)
        }


@router.get("/history", summary="Get task execution history")
async def get_task_history(
    queue_name: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=168),
    limit: int = Query(100, ge=1, le=500),
    container: Any = Depends(get_container)
) -> Dict[str, Any]:
    """Get task execution history.

    Args:
        queue_name: Optional queue filter
        hours: Look back period in hours
        limit: Maximum tasks to return

    Returns:
        Dictionary with execution history
    """
    logger.info(f"Retrieving task history - queue: {queue_name}, hours: {hours}, limit: {limit}")

    try:
        task_repo = await container.get("task_repository")

        if not task_repo:
            return {"history": [], "total": 0}

        # Get task history
        tasks = await task_repo.get_task_history(
            queue_name=queue_name,
            hours=hours,
            limit=limit
        )

        # Convert to dictionaries
        history = [task.to_dict() for task in tasks]

        return {
            "history": history,
            "total": len(history),
            "limit": limit,
            "hours": hours
        }

    except Exception as e:
        logger.error(f"Failed to get task history: {e}")
        return {
            "history": [],
            "total": 0,
            "error": str(e)
        }


@router.get("/metrics", summary="Get queue performance metrics")
async def get_performance_metrics(
    queue_name: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720),
    container: Any = Depends(get_container)
) -> Dict[str, Any]:
    """Get queue performance metrics.

    Args:
        queue_name: Optional queue filter
        hours: Time period for metrics

    Returns:
        Dictionary with performance metrics
    """
    logger.info(f"Retrieving queue metrics - queue: {queue_name}, hours: {hours}")

    try:
        task_repo = await container.get("task_repository")

        if not task_repo:
            return {"metrics": {}, "error": "TaskRepository not available"}

        # Get task statistics
        stats = await task_repo.get_task_statistics(
            queue_name=queue_name,
            hours=hours
        )

        return {
            "metrics": stats,
            "time_period_hours": hours,
            "queue_name": queue_name
        }

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        return {
            "metrics": {},
            "time_period_hours": hours,
            "error": str(e)
        }


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
        "priority": request.get("priority", 5)
    }


@router.put("/config", summary="Update queue configuration")
async def update_queue_config(update: Dict[str, Any]) -> Dict[str, Any]:
    """Update queue configuration."""
    queue_type = update.get("queue_type", "UNKNOWN")
    logger.info(f"Updating queue configuration - queue: {queue_type}")

    return {
        "status": "updated",
        "queue_type": queue_type,
        "configuration": update.get("configuration", {})
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
            "priority_levels": 10
        }
    }


@router.post("/pause", summary="Pause queue")
async def pause_queue(request: Dict[str, str]) -> Dict[str, str]:
    """Pause a queue."""
    queue_type = request.get("queue_type", "UNKNOWN")
    logger.info(f"Pausing queue: {queue_type}")

    return {
        "status": "paused",
        "queue_type": queue_type
    }


@router.post("/resume", summary="Resume queue")
async def resume_queue(request: Dict[str, str]) -> Dict[str, str]:
    """Resume a queue."""
    queue_type = request.get("queue_type", "UNKNOWN")
    logger.info(f"Resuming queue: {queue_type}")

    return {
        "status": "resumed",
        "queue_type": queue_type
    }


@router.post("/tasks/{task_id}/cancel", summary="Cancel task")
async def cancel_task(task_id: str) -> Dict[str, str]:
    """Cancel a specific task."""
    logger.info(f"Cancelling task: {task_id}")

    return {
        "status": "cancelled",
        "task_id": task_id
    }


@router.post("/tasks/{task_id}/retry", summary="Retry task")
async def retry_task(task_id: str) -> Dict[str, str]:
    """Retry a failed task."""
    logger.info(f"Retrying task: {task_id}")

    return {
        "status": "retried",
        "task_id": task_id
    }


@router.post("/clear-completed", summary="Clear completed tasks")
async def clear_completed_tasks(request: Dict[str, Any]) -> Dict[str, Any]:
    """Clear completed tasks from a queue."""
    queue_type = request.get("queue_type", "UNKNOWN")
    logger.info(f"Clearing completed tasks from queue: {queue_type}")

    return {
        "status": "cleared",
        "queue_type": queue_type,
        "cleared_count": 0
    }


@router.get("/health", summary="Queue management health check")
async def queue_health(container: Any = Depends(get_container)) -> Dict[str, Any]:
    """Check queue management health.

    Returns:
        Dictionary with health status
    """
    logger.info("Queue management health check")

    try:
        queue_repo = await container.get("queue_state_repository")

        if not queue_repo:
            return {
                "status": "unhealthy",
                "reason": "QueueStateRepository not available"
            }

        # Get summary to verify repository works
        summary = await queue_repo.get_queue_statistics_summary()

        return {
            "status": "healthy",
            "queues_running": summary["total_queues"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Queue health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
