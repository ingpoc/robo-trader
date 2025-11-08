"""
Scheduler Status Coordinator

Focused coordinator for scheduler status aggregation.
Extracted from SystemStatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone, timedelta
from typing import Dict, Any

from src.config import Config
from src.models.scheduler import QueueName
from ...background_scheduler import BackgroundScheduler
from ..base_coordinator import BaseCoordinator


class SchedulerStatusCoordinator(BaseCoordinator):
    """
    Coordinates scheduler status aggregation.
    
    Responsibilities:
    - Get scheduler status information
    """

    def __init__(
        self,
        config: Config,
        background_scheduler: BackgroundScheduler,
        queue_manager=None
    ):
        super().__init__(config)
        self.background_scheduler = background_scheduler
        self.queue_manager = queue_manager

    async def initialize(self) -> None:
        """Initialize scheduler status coordinator."""
        self._log_info("Initializing SchedulerStatusCoordinator")
        self._initialized = True

    async def get_scheduler_status(self) -> Dict[str, Any]:
        """Get scheduler status information from real queue data."""
        try:
            # Get background scheduler status
            scheduler_status = await self.background_scheduler.get_scheduler_status()

            schedulers = []

            # Get real queue status from queue manager if available
            queue_status = {}
            executors_status = {}
            if self.queue_manager:
                try:
                    queue_status = await self.queue_manager.get_status()
                    # Extract executor status (which contains the actual queue data)
                    executors_status = queue_status.get("executors", {})
                except Exception as e:
                    self._log_warning(f"Could not get queue manager status: {e}")

            # Create scheduler entries for each queue
            queue_names = [
                (QueueName.PORTFOLIO_SYNC, "Portfolio Sync", "Portfolio and account synchronization"),
                (QueueName.DATA_FETCHER, "Data Fetcher", "Market data and news fetching"),
                (QueueName.AI_ANALYSIS, "AI Analysis", "Claude AI analysis and recommendations"),
                (QueueName.PORTFOLIO_ANALYSIS, "Portfolio Analysis", "Portfolio performance analysis"),
                (QueueName.PAPER_TRADING_RESEARCH, "Paper Trading Research", "Research for paper trading"),
                (QueueName.PAPER_TRADING_EXECUTION, "Paper Trading Execution", "Paper trade execution")
            ]

            for queue_name, display_name, description in queue_names:
                queue_key = queue_name.value
                # Get executor data for this queue
                queue_data = executors_status.get(queue_key, {})

                # Determine status based on queue data
                is_running = queue_data.get("is_running", False)
                current_task = queue_data.get("current_task")

                scheduler = {
                    "scheduler_id": queue_key,
                    "name": display_name,
                    "description": description,
                    "status": "running" if is_running else "idle",
                    "event_driven": True,
                    "queue_name": queue_key,
                    "uptime_seconds": 86400,  # Placeholder - could be calculated
                    "jobs_processed": queue_data.get("total_processed", 0),
                    "jobs_failed": queue_data.get("total_failed", 0),
                    "active_jobs": 1 if current_task else 0,
                    "completed_jobs": queue_data.get("total_completed", 0),
                    "last_run_time": queue_data.get("last_processed_at", datetime.now(timezone.utc).isoformat()),
                    "current_task": current_task,
                    "jobs": []
                }

                # Add current task as a job if present
                if current_task:
                    job = {
                        "job_id": current_task.get("task_id", "unknown"),
                        "name": current_task.get("task_type", "unknown"),
                        "status": current_task.get("status", "unknown"),
                        "last_run": current_task.get("started_at", datetime.now(timezone.utc).isoformat()),
                        "next_run": None,
                        "execution_count": 1,
                        "average_duration_ms": current_task.get("duration_ms", 0)
                    }
                    scheduler["jobs"].append(job)

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
                "runningSchedulers": len([s for s in schedulers if s.get("status") == "running"]),
                "queueStatus": queue_status
            }
        except Exception as e:
            self._log_error(f"Failed to get scheduler status: {e}")
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

    async def cleanup(self) -> None:
        """Cleanup scheduler status coordinator resources."""
        self._log_info("SchedulerStatusCoordinator cleanup complete")

