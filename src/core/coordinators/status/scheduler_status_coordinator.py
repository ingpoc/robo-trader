"""
Scheduler Status Coordinator

Focused coordinator for scheduler status aggregation.
Uses QueueStateRepository as single source of truth.

Phase 2: Refactored to use repository layer instead of dual sources.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.config import Config
from src.models.scheduler import QueueName
from src.models.dto import QueueStatusDTO
from ...background_scheduler import BackgroundScheduler
from ..base_coordinator import BaseCoordinator


class SchedulerStatusCoordinator(BaseCoordinator):
    """
    Coordinates scheduler status aggregation.

    Phase 2 Update:
    - Uses QueueStateRepository as single source of truth
    - No more dual sources (executor status vs queue statistics)
    - Returns unified QueueStatusDTO objects

    Responsibilities:
    - Get scheduler status information from repository
    - Aggregate queue data into scheduler view
    - Provide consistent schema via DTOs
    """

    def __init__(
        self,
        config: Config,
        background_scheduler: BackgroundScheduler,
        queue_state_repository=None
    ):
        """Initialize coordinator with repository dependency.

        Args:
            config: Application configuration
            background_scheduler: Background scheduler instance
            queue_state_repository: QueueStateRepository (single source of truth)
        """
        super().__init__(config)
        self.background_scheduler = background_scheduler
        self.queue_state_repository = queue_state_repository

    async def initialize(self) -> None:
        """Initialize scheduler status coordinator."""
        self._log_info("Initializing SchedulerStatusCoordinator (Phase 2 - with repository)")
        self._initialized = True

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status information from repository.

        Phase 2: Uses QueueStateRepository as single source of truth.
        No more mixing executor status and queue statistics.

        Returns:
            Dictionary with scheduler status and queue information
        """
        try:
            # Get background scheduler status
            scheduler_status = await self.background_scheduler.get_scheduler_status()

            schedulers = []

            # Get queue statuses from repository (single source of truth)
            if self.queue_state_repository:
                try:
                    # Efficient: Single query for all queues
                    all_queue_states = await self.queue_state_repository.get_all_statuses()
                except Exception as e:
                    self._log_error(f"Could not get queue statuses from repository: {e}")
                    all_queue_states = {}
            else:
                self._log_warning("QueueStateRepository not available")
                all_queue_states = {}

            # Create scheduler entries for each queue
            queue_definitions = [
                (QueueName.PORTFOLIO_SYNC, "Portfolio Sync", "Portfolio and account synchronization"),
                (QueueName.DATA_FETCHER, "Data Fetcher", "Market data and news fetching"),
                (QueueName.AI_ANALYSIS, "AI Analysis", "Claude AI analysis and recommendations"),
                (QueueName.PORTFOLIO_ANALYSIS, "Portfolio Analysis", "Portfolio performance analysis"),
                (QueueName.PAPER_TRADING_RESEARCH, "Paper Trading Research", "Research for paper trading"),
                (QueueName.PAPER_TRADING_EXECUTION, "Paper Trading Execution", "Paper trade execution")
            ]

            for queue_enum, display_name, description in queue_definitions:
                queue_name = queue_enum.value

                # Get queue state from repository
                queue_state = all_queue_states.get(queue_name)

                if queue_state:
                    # Build scheduler entry from queue state
                    scheduler = {
                        "scheduler_id": queue_name,
                        "name": display_name,
                        "description": description,
                        "status": queue_state.status.value,
                        "event_driven": True,
                        "queue_name": queue_name,
                        "uptime_seconds": 86400,  # Placeholder
                        "jobs_processed": queue_state.completed_tasks,
                        "jobs_failed": queue_state.failed_tasks,
                        "active_jobs": queue_state.running_tasks,
                        "completed_jobs": queue_state.completed_tasks,
                        "last_run_time": queue_state.last_activity_ts or datetime.now(timezone.utc).isoformat(),
                        "current_task": self._build_current_task_info(queue_state),
                        "jobs": self._build_jobs_list(queue_state)
                    }
                else:
                    # Fallback if queue not in repository (shouldn't happen)
                    scheduler = {
                        "scheduler_id": queue_name,
                        "name": display_name,
                        "description": description,
                        "status": "idle",
                        "event_driven": True,
                        "queue_name": queue_name,
                        "uptime_seconds": 0,
                        "jobs_processed": 0,
                        "jobs_failed": 0,
                        "active_jobs": 0,
                        "completed_jobs": 0,
                        "last_run_time": datetime.now(timezone.utc).isoformat(),
                        "current_task": None,
                        "jobs": []
                    }

                schedulers.append(scheduler)

            # Calculate overall status
            if schedulers:
                running_schedulers = [s for s in schedulers if s.get("status") == "running"]
                overall_status = "healthy" if running_schedulers else "idle"
            else:
                overall_status = "stopped"

            return {
                "status": overall_status,
                "lastRun": scheduler_status.get("last_run_time", "unknown") if scheduler_status else "unknown",
                "activeJobs": sum(s.get("active_jobs", 0) for s in schedulers),
                "completedJobs": sum(s.get("completed_jobs", 0) for s in schedulers),
                "schedulers": schedulers,
                "totalSchedulers": len(schedulers),
                "runningSchedulers": len([s for s in schedulers if s.get("status") == "running"])
            }
        except Exception as e:
            self._log_error(f"Failed to get scheduler status: {e}")
            import traceback
            self._log_error(f"Traceback: {traceback.format_exc()}")
            return {
                "status": "error",
                "lastRun": "unknown",
                "activeJobs": 0,
                "completedJobs": 0,
                "schedulers": [],
                "totalSchedulers": 0,
                "runningSchedulers": 0,
                "error": str(e)
            }

    def _build_current_task_info(self, queue_state) -> Optional[Dict[str, Any]]:
        """Build current task information from queue state.

        Args:
            queue_state: QueueState from repository

        Returns:
            Current task dictionary or None
        """
        if not queue_state.current_task_id:
            return None

        return {
            "task_id": queue_state.current_task_id,
            "task_type": queue_state.current_task_type,
            "queue_name": queue_state.name,
            "started_at": queue_state.current_task_started_at,
            "status": "running"
        }

    def _build_jobs_list(self, queue_state) -> list:
        """Build jobs list from queue state.

        Args:
            queue_state: QueueState from repository

        Returns:
            List of job dictionaries
        """
        jobs = []

        # Add current task as a job if present
        if queue_state.current_task_id:
            job = {
                "job_id": queue_state.current_task_id,
                "name": queue_state.current_task_type,
                "status": "running",
                "last_run": queue_state.current_task_started_at,
                "next_run": None,
                "execution_count": 1,
                "average_duration_ms": int(queue_state.avg_duration_ms)
            }
            jobs.append(job)

        return jobs

    async def cleanup(self) -> None:
        """Cleanup scheduler status coordinator resources."""
        self._log_info("SchedulerStatusCoordinator cleanup complete")
