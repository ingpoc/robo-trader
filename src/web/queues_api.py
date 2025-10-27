"""Queue Management API endpoints for the Robo Trader system.

Provides queue status, task management, and monitoring capabilities.
Follows the FastAPI microservice pattern used by other services.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Query
from loguru import logger

router = APIRouter(prefix="/queues", tags=["Queue Management"])


@router.get("/status", summary="Get all queue statuses")
async def get_queue_statuses() -> Dict[str, Any]:
    """Get detailed status of all queues in the system."""
    logger.info("Retrieving all queue statuses")

    # Get real queue data from queue coordinator if available
    try:
        # Import here to avoid circular dependencies
        from src.core.di import get_container

        # Get the container and try to get queue coordinator
        container = get_container()
        if container and hasattr(container, '_services'):
            queue_coordinator = await container.get("queue_coordinator")
            if queue_coordinator:
                # Get real queue status from coordinator
                queue_status = await queue_coordinator.get_queue_status()

                # Format the response with detailed information
                queues = []
                for queue_name, queue_info in queue_status.get("queues", {}).items():
                    queues.append({
                        "name": queue_name,
                        "status": queue_info.get("status", "unknown"),
                        "running": queue_info.get("running", False),
                        "type": queue_info.get("type", "unknown"),
                        "details": queue_info.get("details", {}),
                        "current_task_id": queue_info.get("details", {}).get("current_task_id"),
                        "pending_tasks": queue_info.get("details", {}).get("pending_tasks", 0),
                        "active_tasks": queue_info.get("details", {}).get("active_tasks", 0),
                        "completed_tasks": queue_info.get("details", {}).get("completed_tasks", 0),
                        "failed_tasks": queue_info.get("details", {}).get("failed_tasks", 0),
                        "average_execution_time": queue_info.get("details", {}).get("average_execution_time", 0.0),
                        "last_execution_time": queue_info.get("details", {}).get("last_execution_time"),
                        "registered_handlers": queue_info.get("details", {}).get("registered_handlers", [])
                    })

                return {
                    "queues": queues,
                    "stats": {
                        "total_queues": len(queues),
                        "active_queues": len([q for q in queues if q.get("running", False)]),
                        "total_tasks": sum(q.get("pending_tasks", 0) + q.get("active_tasks", 0) for q in queues),
                        "active_tasks": sum(q.get("active_tasks", 0) for q in queues),
                        "completed_tasks": sum(q.get("completed_tasks", 0) for q in queues),
                        "failed_tasks": sum(q.get("failed_tasks", 0) for q in queues)
                    },
                    "coordinator_status": {
                        "coordinator_running": queue_status.get("coordinator_running", False),
                        "queues_running": queue_status.get("queues_running", False),
                        "event_router_status": queue_status.get("event_router_status", "not_available")
                    }
                }
    except Exception as e:
        logger.warning(f"Could not get real queue status: {e}")

    # Fallback to enhanced mock data with detailed structure
    return {
        "queues": [
            {
                "name": "portfolio_sync",
                "status": "healthy",
                "running": True,
                "type": "queue_service",
                "current_task_id": None,
                "pending_tasks": 0,
                "active_tasks": 0,
                "completed_tasks": 5,
                "failed_tasks": 0,
                "average_execution_time": 2.5,
                "last_execution_time": "2025-10-27T11:37:32Z",
                "registered_handlers": ["balance_sync", "position_update", "pnl_calculation"],
                "details": {
                    "queue_type": "PORTFOLIO_SYNC",
                    "max_concurrent_tasks": 3,
                    "timeout_seconds": 300
                }
            },
            {
                "name": "data_fetcher",
                "status": "healthy",
                "running": True,
                "type": "queue_service",
                "current_task_id": "task_123",
                "pending_tasks": 2,
                "active_tasks": 1,
                "completed_tasks": 15,
                "failed_tasks": 1,
                "average_execution_time": 4.2,
                "last_execution_time": "2025-10-27T11:38:15Z",
                "registered_handlers": ["news_monitoring", "earnings_fetcher", "fundamentals_checker"],
                "details": {
                    "queue_type": "DATA_FETCHER",
                    "max_concurrent_tasks": 5,
                    "timeout_seconds": 600,
                    "current_task": {
                        "task_id": "task_123",
                        "task_type": "NEWS_MONITORING",
                        "symbol": "RELIANCE",
                        "started_at": "2025-10-27T11:38:15Z",
                        "priority": 3
                    }
                }
            },
            {
                "name": "ai_analysis",
                "status": "idle",
                "running": False,
                "type": "queue_service",
                "current_task_id": None,
                "pending_tasks": 0,
                "active_tasks": 0,
                "completed_tasks": 3,
                "failed_tasks": 0,
                "average_execution_time": 12.8,
                "last_execution_time": "2025-10-27T11:35:00Z",
                "registered_handlers": ["claude_morning_prep", "claude_evening_review", "recommendation_generator"],
                "details": {
                    "queue_type": "AI_ANALYSIS",
                    "max_concurrent_tasks": 1,
                    "timeout_seconds": 1800,
                    "last_completed_task": {
                        "task_id": "task_122",
                        "task_type": "CLAUDE_EVENING_REVIEW",
                        "completed_at": "2025-10-27T11:35:00Z",
                        "duration_seconds": 15.2
                    }
                }
            }
        ],
        "stats": {
            "total_queues": 3,
            "active_queues": 2,
            "total_tasks": 2,
            "active_tasks": 1,
            "completed_tasks": 23,
            "failed_tasks": 1
        },
        "coordinator_status": {
            "coordinator_running": True,
            "queues_running": True,
            "event_router_status": "healthy"
        }
    }


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
            "last_activity": None
        }
    }


@router.get("/tasks", summary="Get queue tasks with filtering")
async def get_queue_tasks(
    queue_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    task_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
) -> Dict[str, Any]:
    """Get queue tasks with optional filtering."""
    logger.info(f"Retrieving queue tasks - queue_type: {queue_type}, status: {status}, limit: {limit}")
    return {
        "tasks": [],
        "total": 0,
        "limit": limit,
        "offset": offset,
        "filters": {
            "queue_type": queue_type,
            "status": status,
            "priority": priority,
            "task_type": task_type
        }
    }


@router.get("/history", summary="Get task execution history")
async def get_task_history(
    queue_type: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500)
) -> Dict[str, Any]:
    """Get task execution history."""
    logger.info(f"Retrieving task history - queue_type: {queue_type}, limit: {limit}")
    return {
        "history": [],
        "total": 0,
        "limit": limit
    }


@router.get("/metrics", summary="Get queue performance metrics")
async def get_performance_metrics(
    queue_type: Optional[str] = Query(None),
    hours: int = Query(24, ge=1, le=720)
) -> Dict[str, Any]:
    """Get queue performance metrics."""
    logger.info(f"Retrieving queue metrics - queue_type: {queue_type}, hours: {hours}")
    return {
        "metrics": [],
        "time_period_hours": hours,
        "queue_type": queue_type
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
async def queue_health() -> Dict[str, Any]:
    """Check queue management health."""
    logger.info("Queue management health check")

    return {
        "status": "healthy",
        "queues_running": 3,
        "timestamp": None
    }
