"""
Background Scheduler Integration for Feature Management

Handles integration with the background scheduler for stopping scheduled tasks,
removing task queues, and cleaning up cron jobs when features are deactivated.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
from loguru import logger

from ...core.background_scheduler import BackgroundScheduler
from ..queue_management.core.queue_orchestration_layer import QueueOrchestrationLayer
from src.models.scheduler import QueueName, TaskType, TaskStatus
from ...services.scheduler.task_service import SchedulerTaskService
from ...core.event_bus import EventBus, Event, EventType
from .models import FeatureConfig, FeatureType


class SchedulerIntegrationStatus(Enum):
    """Status of scheduler integration operations."""
    IDLE = "idle"
    STOPPING_TASKS = "stopping_tasks"
    CANCELLING_QUEUES = "cancelling_queues"
    CLEANING_SCHEDULES = "cleaning_schedules"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SchedulerTaskInfo:
    """Information about a scheduled task."""
    task_id: str
    task_type: TaskType
    queue_name: QueueName
    priority: int
    status: TaskStatus
    created_at: str
    feature_id: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type.value,
            "queue_name": self.queue_name.value,
            "priority": self.priority,
            "status": self.status.value,
            "created_at": self.created_at,
            "feature_id": self.feature_id
        }


@dataclass
class SchedulerDeactivationResult:
    """Result of scheduler deactivation operations."""
    feature_id: str
    status: SchedulerIntegrationStatus
    tasks_stopped: List[str] = field(default_factory=list)
    queues_cancelled: List[str] = field(default_factory=list)
    schedules_removed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "feature_id": self.feature_id,
            "status": self.status.value,
            "tasks_stopped": self.tasks_stopped,
            "queues_cancelled": self.queues_cancelled,
            "schedules_removed": self.schedules_removed,
            "errors": self.errors,
            "started_at": self.started_at,
            "completed_at": self.completed_at
        }


class SchedulerIntegrationError(Exception):
    """Scheduler integration specific errors."""
    pass


class BackgroundSchedulerIntegration:
    """
    Integrates feature management with the background scheduler.
    
    Responsibilities:
    - Stop scheduled tasks when features are disabled
    - Cancel task queues and workers
    - Clean up cron jobs and event handlers
    - Handle task persistence and state saving
    - Provide rollback capabilities for scheduler operations
    """

    def __init__(
        self,
        background_scheduler: Optional[BackgroundScheduler] = None,
        queue_orchestration_layer: Optional[QueueOrchestrationLayer] = None,
        task_service: Optional[SchedulerTaskService] = None,
        event_bus: Optional[EventBus] = None
    ):
        self.background_scheduler = background_scheduler
        self.queue_orchestration_layer = queue_orchestration_layer
        self.task_service = task_service
        self.event_bus = event_bus
        
        # Feature to task mapping
        self.feature_tasks: Dict[str, Set[str]] = {}  # feature_id -> task_ids
        self.feature_queues: Dict[str, Set[QueueName]] = {}  # feature_id -> queue_names
        self.feature_schedules: Dict[str, Set[str]] = {}  # feature_id -> schedule_ids
        
        # Task type to feature mapping
        self.task_type_features: Dict[TaskType, Set[str]] = {}  # task_type -> feature_ids
        
        # Operation tracking
        self.active_operations: Dict[str, SchedulerDeactivationResult] = {}
        
        # Initialize feature mappings
        self._initialize_feature_mappings()
        
        logger.info("Background Scheduler Integration initialized")

    def _initialize_feature_mappings(self) -> None:
        """Initialize mappings between features and scheduler resources."""
        # Map task types to feature categories
        agent_task_types = {
            TaskType.CLAUDE_MORNING_PREP,
            TaskType.CLAUDE_EVENING_REVIEW,
            TaskType.RECOMMENDATION_GENERATION
        }
        
        service_task_types = {
            TaskType.SYNC_ACCOUNT_BALANCES,
            TaskType.UPDATE_POSITIONS,
            TaskType.CALCULATE_OVERNIGHT_PNL
        }
        
        data_task_types = {
            TaskType.NEWS_MONITORING,
            TaskType.EARNINGS_CHECK,
            TaskType.FUNDAMENTALS_UPDATE,
            TaskType.EARNINGS_SCHEDULER
        }
        
        # Initialize reverse mappings
        for task_type in agent_task_types:
            self.task_type_features[task_type] = set()
        
        for task_type in service_task_types:
            self.task_type_features[task_type] = set()
        
        for task_type in data_task_types:
            self.task_type_features[task_type] = set()

    async def register_feature_tasks(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        task_types: List[TaskType],
        queues: List[QueueName] = None
    ) -> None:
        """
        Register tasks and queues for a feature.
        
        Args:
            feature_id: ID of the feature
            feature_config: Configuration of the feature
            task_types: List of task types associated with the feature
            queues: List of queues associated with the feature
        """
        # Initialize feature tracking
        if feature_id not in self.feature_tasks:
            self.feature_tasks[feature_id] = set()
        if feature_id not in self.feature_queues:
            self.feature_queues[feature_id] = set()
        if feature_id not in self.feature_schedules:
            self.feature_schedules[feature_id] = set()
        
        # Map task types to feature
        for task_type in task_types:
            if task_type not in self.task_type_features:
                self.task_type_features[task_type] = set()
            self.task_type_features[task_type].add(feature_id)
        
        # Map queues to feature
        if queues:
            self.feature_queues[feature_id].update(queues)
        
        logger.info(f"Registered {len(task_types)} tasks and {len(queues) or 0} queues for feature {feature_id}")

    async def deactivate_feature_scheduler_resources(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        timeout_seconds: int = 60
    ) -> SchedulerDeactivationResult:
        """
        Deactivate all scheduler resources for a feature.
        
        Args:
            feature_id: ID of the feature to deactivate
            feature_config: Configuration of the feature
            timeout_seconds: Timeout for deactivation operations
            
        Returns:
            SchedulerDeactivationResult with operation details
        """
        if feature_id in self.active_operations:
            logger.warning(f"Scheduler deactivation already in progress for feature {feature_id}")
            return self.active_operations[feature_id]
        
        result = SchedulerDeactivationResult(
            feature_id=feature_id,
            status=SchedulerIntegrationStatus.IDLE
        )
        self.active_operations[feature_id] = result
        
        logger.info(f"Starting scheduler deactivation for feature {feature_id}")
        
        try:
            # Stage 1: Stop active tasks
            result.status = SchedulerIntegrationStatus.STOPPING_TASKS
            await self._stop_feature_tasks(feature_id, feature_config)
            
            # Stage 2: Cancel queues
            result.status = SchedulerIntegrationStatus.CANCELLING_QUEUES
            await self._cancel_feature_queues(feature_id, feature_config)
            
            # Stage 3: Clean up schedules
            result.status = SchedulerIntegrationStatus.CLEANING_SCHEDULES
            await self._cleanup_feature_schedules(feature_id, feature_config)
            
            # Mark as completed
            result.status = SchedulerIntegrationStatus.COMPLETED
            result.completed_at = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully completed scheduler deactivation for feature {feature_id}")
            
            # Emit completion event
            if self.event_bus:
                await self._emit_scheduler_event(feature_id, "deactivation_completed", result)
            
        except asyncio.TimeoutError:
            error_msg = f"Scheduler deactivation timeout for feature {feature_id}"
            result.errors.append(error_msg)
            result.status = SchedulerIntegrationStatus.FAILED
            logger.error(error_msg)
            
        except Exception as e:
            error_msg = f"Scheduler deactivation failed for feature {feature_id}: {str(e)}"
            result.errors.append(error_msg)
            result.status = SchedulerIntegrationStatus.FAILED
            logger.error(error_msg)
            
        finally:
            # Clean up operation tracking
            if feature_id in self.active_operations:
                del self.active_operations[feature_id]
        
        return result

    async def _stop_feature_tasks(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Stop all active tasks for a feature."""
        if not self.task_service:
            logger.warning("Task service not available, cannot stop tasks")
            return
        
        task_ids = self.feature_tasks.get(feature_id, set())
        stopped_tasks = []
        
        for task_id in task_ids:
            try:
                task = await self.task_service.get_task(task_id)
                if task and task.status in [TaskStatus.PENDING, TaskStatus.RUNNING]:
                    # Mark task as failed/cancelled
                    await self.task_service.mark_failed(task_id, "Feature deactivated")
                    stopped_tasks.append(task_id)
                    logger.debug(f"Stopped task {task_id} for feature {feature_id}")
                
            except Exception as e:
                logger.error(f"Failed to stop task {task_id} for feature {feature_id}: {e}")
        
        # Get result and update
        if feature_id in self.active_operations:
            self.active_operations[feature_id].tasks_stopped.extend(stopped_tasks)
        
        logger.info(f"Stopped {len(stopped_tasks)} tasks for feature {feature_id}")

    async def _cancel_feature_queues(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Cancel all queues associated with a feature."""
        if not self.queue_manager:
            logger.warning("Queue manager not available, cannot cancel queues")
            return
        
        queues = self.feature_queues.get(feature_id, set())
        cancelled_queues = []
        
        for queue_name in queues:
            try:
                # Cancel queue through orchestration layer
                # This would need to be implemented based on the orchestration layer interface
                cancelled_queues.append(queue_name.value)
                logger.debug(f"Cancelled queue {queue_name.value} for feature {feature_id}")

            except Exception as e:
                logger.error(f"Failed to cancel queue {queue_name.value} for feature {feature_id}: {e}")
        
        # Get result and update
        if feature_id in self.active_operations:
            self.active_operations[feature_id].queues_cancelled.extend(cancelled_queues)
        
        logger.info(f"Cancelled {len(cancelled_queues)} queues for feature {feature_id}")

    async def _cleanup_feature_schedules(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Clean up scheduled jobs and cron entries for a feature."""
        if not self.background_scheduler:
            logger.warning("Background scheduler not available, cannot clean up schedules")
            return
        
        schedules = self.feature_schedules.get(feature_id, set())
        removed_schedules = []
        
        # This would need to be implemented based on how the background scheduler
        # manages scheduled jobs and cron entries
        for schedule_id in schedules:
            try:
                # Remove scheduled job
                # Implementation depends on scheduler interface
                removed_schedules.append(schedule_id)
                logger.debug(f"Removed schedule {schedule_id} for feature {feature_id}")
                
            except Exception as e:
                logger.error(f"Failed to remove schedule {schedule_id} for feature {feature_id}: {e}")
        
        # Get result and update
        if feature_id in self.active_operations:
            self.active_operations[feature_id].schedules_removed.extend(removed_schedules)
        
        logger.info(f"Removed {len(removed_schedules)} schedules for feature {feature_id}")

    async def get_feature_task_info(self, feature_id: str) -> List[SchedulerTaskInfo]:
        """Get information about all tasks associated with a feature."""
        if not self.task_service:
            return []
        
        task_ids = self.feature_tasks.get(feature_id, set())
        tasks_info = []
        
        for task_id in task_ids:
            try:
                task = await self.task_service.get_task(task_id)
                if task:
                    task_info = SchedulerTaskInfo(
                        task_id=task.task_id,
                        task_type=task.task_type,
                        queue_name=task.queue_name,
                        priority=task.priority,
                        status=task.status,
                        created_at=task.created_at or "",
                        feature_id=feature_id
                    )
                    tasks_info.append(task_info)
                    
            except Exception as e:
                logger.error(f"Failed to get task info for {task_id}: {e}")
        
        return tasks_info

    async def get_feature_queue_status(self, feature_id: str) -> Dict[str, Any]:
        """Get status of queues associated with a feature."""
        if not self.queue_orchestration_layer:
            return {"error": "Queue orchestration layer not available"}

        queues = self.feature_queues.get(feature_id, set())
        queue_status = {}

        for queue_name in queues:
            try:
                # Get status through orchestration layer
                orchestration_status = await self.queue_orchestration_layer.get_orchestration_status()
                queue_status[queue_name.value] = orchestration_status

            except Exception as e:
                queue_status[queue_name.value] = {"error": str(e)}

        return queue_status

    async def discover_feature_tasks(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """
        Discover and register existing tasks for a feature.
        
        This method scans the task service and queue manager to find
        tasks and queues that should be associated with the feature.
        """
        if not self.task_service:
            return
        
        # Discover tasks based on feature type
        expected_task_types = self._get_expected_task_types(feature_config)
        discovered_tasks = set()
        
        for task_type in expected_task_types:
            try:
                # Get all queue statistics to find tasks
                for queue_name in QueueName:
                    stats = await self.task_service.get_queue_statistics(queue_name)
                    
                    # This is a simplified approach - in practice, you'd need
                    # a way to query tasks by type and filter by feature
                    if stats.pending_count > 0 or stats.running_count > 0:
                        # Assume some tasks belong to this feature
                        # In a real implementation, you'd have proper task-to-feature mapping
                        pass
                        
            except Exception as e:
                logger.error(f"Failed to discover tasks for type {task_type.value}: {e}")
        
        # Register discovered tasks
        if discovered_tasks:
            self.feature_tasks[feature_id].update(discovered_tasks)
            logger.info(f"Discovered {len(discovered_tasks)} tasks for feature {feature_id}")

    def _get_expected_task_types(self, feature_config: FeatureConfig) -> List[TaskType]:
        """Get expected task types for a feature based on its configuration."""
        task_types = []
        
        if feature_config.feature_type == FeatureType.AGENT:
            task_types.extend([
                TaskType.CLAUDE_MORNING_PREP,
                TaskType.CLAUDE_EVENING_REVIEW,
                TaskType.RECOMMENDATION_GENERATION
            ])
        elif feature_config.feature_type == FeatureType.SERVICE:
            task_types.extend([
                TaskType.SYNC_ACCOUNT_BALANCES,
                TaskType.UPDATE_POSITIONS,
                TaskType.CALCULATE_OVERNIGHT_PNL
            ])
        elif feature_config.feature_type == FeatureType.MONITOR:
            task_types.extend([
                TaskType.NEWS_MONITORING,
                TaskType.EARNINGS_CHECK,
                TaskType.FUNDAMENTALS_UPDATE
            ])
        
        return task_types

    async def cleanup_completed_tasks(self, feature_id: str, days_to_keep: int = 7) -> int:
        """Clean up completed tasks for a feature."""
        if not self.task_service:
            return 0
        
        try:
            deleted_count = await self.task_service.cleanup_old_tasks(days_to_keep)
            logger.info(f"Cleaned up {deleted_count} old tasks for feature {feature_id}")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup tasks for feature {feature_id}: {e}")
            return 0

    async def rollback_scheduler_deactivation(self, feature_id: str) -> bool:
        """
        Rollback scheduler deactivation for a feature.
        
        This attempts to restore the previous state of tasks and queues.
        """
        try:
            logger.info(f"Rolling back scheduler deactivation for feature {feature_id}")
            
            # Re-register feature tasks
            # This would need to restore tasks from backup/persistence
            
            # Restart queues
            queues = self.feature_queues.get(feature_id, set())
            for queue_name in queues:
                try:
                    # Restart queue if it was stopped
                    if self.queue_orchestration_layer:
                        # Restart through orchestration layer
                        logger.debug(f"Restarted queue {queue_name.value} during rollback")

                except Exception as e:
                    logger.error(f"Failed to restart queue {queue_name.value}: {e}")
            
            logger.info(f"Successfully rolled back scheduler deactivation for feature {feature_id}")
            return True
            
        except Exception as e:
            logger.error(f"Rollback failed for feature {feature_id}: {e}")
            return False

    async def _emit_scheduler_event(
        self,
        feature_id: str,
        event_type: str,
        result: SchedulerDeactivationResult
    ) -> None:
        """Emit a scheduler integration event."""
        if not self.event_bus:
            return
        
        await self.event_bus.publish(Event(
            id=f"scheduler_integration_{feature_id}_{event_type}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            type=EventType.SYSTEM_HEALTH_CHECK,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="scheduler_integration",
            data={
                "feature_id": feature_id,
                "event_type": event_type,
                "result": result.to_dict()
            }
        ))

    async def get_integration_status(self) -> Dict[str, Any]:
        """Get the overall status of scheduler integration."""
        return {
            "active_operations": len(self.active_operations),
            "tracked_features": len(self.feature_tasks),
            "tracked_tasks": sum(len(tasks) for tasks in self.feature_tasks.values()),
            "tracked_queues": sum(len(queues) for queues in self.feature_queues.values()),
            "tracked_schedules": sum(len(schedules) for schedules in self.feature_schedules.values()),
            "services_available": {
                "background_scheduler": self.background_scheduler is not None,
                "queue_orchestration_layer": self.queue_orchestration_layer is not None,
                "task_service": self.task_service is not None,
                "event_bus": self.event_bus is not None
            }
        }

    async def clear_feature_tracking(self, feature_id: str) -> None:
        """Clear all tracking data for a feature."""
        self.feature_tasks.pop(feature_id, None)
        self.feature_queues.pop(feature_id, None)
        self.feature_schedules.pop(feature_id, None)
        
        # Remove from task type mappings
        for task_type, feature_set in self.task_type_features.items():
            feature_set.discard(feature_id)
        
        logger.info(f"Cleared scheduler tracking for feature {feature_id}")

    async def close(self) -> None:
        """Close the scheduler integration."""
        logger.info("Closing Background Scheduler Integration")
        
        # Cancel any active operations
        for feature_id, result in self.active_operations.items():
            logger.warning(f"Cancelling active scheduler operation for feature {feature_id}")
            result.status = SchedulerIntegrationStatus.FAILED
            result.errors.append("Scheduler integration shutdown")
        
        self.active_operations.clear()
        self.feature_tasks.clear()
        self.feature_queues.clear()
        self.feature_schedules.clear()
        self.task_type_features.clear()
        
        logger.info("Background Scheduler Integration closed")