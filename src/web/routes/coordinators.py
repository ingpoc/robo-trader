"""Coordinator Status API endpoints - Real-time coordinator health monitoring."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from ..dependencies import get_container

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/coordinators", tags=["coordinators"])
limiter = Limiter(key_func=get_remote_address)

# Load rate limits from environment
default_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.get("/status")
@limiter.limit(default_limit)
async def get_coordinator_status(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Get initialization status of all key coordinators.

    Returns health status, initialization state, and error details for each coordinator.
    Used by MCP server for real-time debugging and deployment verification.
    """

    try:
        # List of coordinator keys to check
        coordinator_keys = [
            "portfolio_analysis_coordinator",
            "task_coordinator",
            "broadcast_coordinator",
            "queue_coordinator",
            "session_coordinator",
            "query_coordinator",
            "lifecycle_coordinator",
            "status_coordinator"
        ]

        statuses = {}
        overall_health = "healthy"
        failed_coordinators = []

        # Check each coordinator
        for key in coordinator_keys:
            try:
                coordinator = await container.get(key)

                # Check if coordinator has status tracking methods
                if coordinator and hasattr(coordinator, 'is_ready') and hasattr(coordinator, 'get_initialization_status'):
                    is_ready, error_msg = coordinator.get_initialization_status()

                    status_entry = {
                        "initialized": is_ready,
                        "ready": is_ready,
                        "error": error_msg,
                        "last_checked": datetime.now(timezone.utc).isoformat()
                    }

                    statuses[key] = status_entry

                    if not is_ready:
                        overall_health = "degraded"
                        if error_msg:
                            failed_coordinators.append({
                                "coordinator": key,
                                "error": error_msg
                            })
                else:
                    # Coordinator exists but doesn't have status tracking
                    statuses[key] = {
                        "initialized": True,
                        "ready": True,
                        "error": None,
                        "last_checked": datetime.now(timezone.utc).isoformat(),
                        "note": "No status tracking available"
                    }

            except ValueError as e:
                # Coordinator not registered (optional coordinators)
                logger.debug(f"Coordinator {key} not registered: {e}")
                continue

            except Exception as e:
                # Coordinator retrieval failed (critical)
                error_str = str(e)
                statuses[key] = {
                    "initialized": False,
                    "ready": False,
                    "error": error_str,
                    "last_checked": datetime.now(timezone.utc).isoformat()
                }
                overall_health = "critical"
                failed_coordinators.append({
                    "coordinator": key,
                    "error": error_str
                })

        # Determine overall health based on critical coordinators
        critical_coordinators = [
            "portfolio_analysis_coordinator",
            "task_coordinator",
            "queue_coordinator"
        ]

        for critical in critical_coordinators:
            if critical in [f['coordinator'] for f in failed_coordinators]:
                overall_health = "critical"
                break

        return {
            "success": True,
            "overall_health": overall_health,
            "summary": {
                "total_coordinators": len(statuses),
                "healthy": sum(1 for s in statuses.values() if s.get('initialized')),
                "degraded": sum(1 for s in statuses.values() if not s.get('initialized') and s.get('error')),
                "failed": len(failed_coordinators)
            },
            "coordinators": statuses,
            "failed_coordinators": failed_coordinators if failed_coordinators else None,
            "critical_notes": _generate_critical_notes(overall_health, failed_coordinators),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except TradingError as e:
        logger.error(f"Trading error in coordinator status: {e}")
        raise

    except Exception as e:
        logger.exception(f"Failed to get coordinator status: {e}")
        raise TradingError(
            f"Failed to retrieve coordinator status: {str(e)}",
            category="SYSTEM",
            recoverable=True
        )


def _generate_critical_notes(health: str, failed_coordinators: list) -> Optional[list]:
    """Generate critical notes based on overall health."""

    if health == "healthy":
        return None

    notes = []

    if health == "critical":
        notes.append("CRITICAL: One or more critical coordinators failed to initialize")

    # Add specific recommendations
    critical_mapping = {
        "portfolio_analysis_coordinator": "Portfolio analysis disabled - background monitoring of stocks will not occur",
        "task_coordinator": "Task coordination disabled - background task execution will not work",
        "queue_coordinator": "Queue management disabled - task queuing system unavailable"
    }

    for failed in failed_coordinators:
        coordinator_name = failed['coordinator']
        if coordinator_name in critical_mapping:
            notes.append(f"{coordinator_name}: {critical_mapping[coordinator_name]}")

    return notes if notes else None
