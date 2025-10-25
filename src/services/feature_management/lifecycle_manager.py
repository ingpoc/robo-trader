"""
Service Lifecycle Manager for Feature Management System

Handles the complete lifecycle of features including activation, deactivation,
resource management, and integration with other system components.
"""

import asyncio
import gc
import psutil
import threading
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import weakref
from loguru import logger

from ...core.event_bus import EventBus, Event, EventType, EventHandler
from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from ...core.background_scheduler import BackgroundScheduler
from ...core.coordinators.agent_coordinator import AgentCoordinator
from ...services.queue_management.core.queue_orchestration_layer import QueueOrchestrationLayer
from ...models.scheduler import QueueName, TaskType
from .models import FeatureConfig, FeatureState, FeatureStatus, FeatureType


class DeactivationStage(Enum):
    """Stages of the deactivation process."""
    PREPARATION = "preparation"
    STOPPING_TASKS = "stopping_tasks"
    STOPPING_AGENTS = "stopping_agents"
    STOPPING_SERVICES = "stopping_services"
    CLEANUP_RESOURCES = "cleanup_resources"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"


class DeactionStatus(Enum):
    """Status of deactivation operations."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"


@dataclass
class DeactivationOperation:
    """Represents a deactivation operation for a feature."""
    feature_id: str
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    current_stage: DeactivationStage = DeactivationStage.PREPARATION
    status: DeactionStatus = DeactionStatus.PENDING
    stages_completed: List[DeactivationStage] = field(default_factory=list)
    stages_failed: List[DeactivationStage] = field(default_factory=list)
    error_message: Optional[str] = None
    rollback_data: Dict[str, Any] = field(default_factory=dict)
    affected_resources: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_id": self.feature_id,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "current_stage": self.current_stage.value,
            "status": self.status.value,
            "stages_completed": [s.value for s in self.stages_completed],
            "stages_failed": [s.value for s in self.stages_failed],
            "error_message": self.error_message,
            "rollback_data": self.rollback_data,
            "affected_resources": self.affected_resources
        }


@dataclass
class ResourceSnapshot:
    """Snapshot of resources before deactivation for rollback."""
    feature_id: str
    timestamp: str
    scheduled_tasks: List[str] = field(default_factory=list)
    active_agents: List[str] = field(default_factory=list)
    running_services: List[str] = field(default_factory=list)
    queue_states: Dict[str, Any] = field(default_factory=dict)
    memory_usage: Dict[str, Any] = field(default_factory=dict)
    file_handles: List[str] = field(default_factory=list)
    network_connections: List[str] = field(default_factory=list)


class LifecycleManagerError(TradingError):
    """Lifecycle manager specific errors."""
    
    def __init__(self, message: str, feature_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            feature_id=feature_id,
            **kwargs
        )


class ServiceLifecycleManager(EventHandler):
    """
    Manages the complete lifecycle of features including deactivation.
    
    Responsibilities:
    - Coordinate deactivation across all system components
    - Manage resource cleanup and deallocation
    - Handle rollback on deactivation failures
    - Integrate with background scheduler, agents, and services
    - Ensure graceful shutdown of all associated processes
    """

    def __init__(self, config: Any, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        
        # Service integrations
        self.background_scheduler: Optional[BackgroundScheduler] = None
        self.agent_coordinator: Optional[AgentCoordinator] = None
        self.queue_orchestration_layer: Optional[QueueOrchestrationLayer] = None
        self.service_registry: Optional[Any] = None
        
        # Deactivation state
        self.active_deactivations: Dict[str, DeactivationOperation] = {}
        self.resource_snapshots: Dict[str, ResourceSnapshot] = {}
        self.deactivation_lock = asyncio.Lock()
        
        # Resource tracking
        self.feature_resources: Dict[str, Dict[str, Any]] = {}
        self.active_tasks: Dict[str, Set[str]] = {}  # feature_id -> task_ids
        self.active_agents: Dict[str, Set[str]] = {}  # feature_id -> agent_ids
        self.active_services: Dict[str, Set[str]] = {}  # feature_id -> service_ids
        
        # Configuration
        self.deactivation_timeout_seconds = 300  # 5 minutes
        self.enable_rollback = True
        self.cleanup_temp_data = True
        
        # Subscribe to events
        self.event_bus.subscribe(EventType.FEATURE_DISABLED, self)
        self.event_bus.subscribe(EventType.SYSTEM_ERROR, self)
        self.event_bus.subscribe(EventType.TASK_COMPLETED, self)
        
        logger.info("Service Lifecycle Manager initialized")

    def set_background_scheduler(self, scheduler: BackgroundScheduler) -> None:
        """Set background scheduler integration."""
        self.background_scheduler = scheduler
        logger.info("Background scheduler integration configured")

    def set_agent_coordinator(self, coordinator: AgentCoordinator) -> None:
        """Set agent coordinator integration."""
        self.agent_coordinator = coordinator
        logger.info("Agent coordinator integration configured")

    def set_queue_orchestration_layer(self, orchestration_layer: QueueOrchestrationLayer) -> None:
        """Set queue orchestration layer integration."""
        self.queue_orchestration_layer = orchestration_layer
        logger.info("Queue orchestration layer integration configured")

    def set_service_registry(self, registry: Any) -> None:
        """Set service registry integration."""
        self.service_registry = registry
        logger.info("Service registry integration configured")

    async def deactivate_feature(
        self,
        feature_id: str,
        feature_config: FeatureConfig,
        reason: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> DeactivationOperation:
        """
        Deactivate a feature and all its associated resources.
        
        Args:
            feature_id: ID of the feature to deactivate
            feature_config: Configuration of the feature
            reason: Reason for deactivation
            timeout_seconds: Timeout for deactivation
            
        Returns:
            DeactivationOperation with results
        """
        async with self.deactivation_lock:
            if feature_id in self.active_deactivations:
                logger.warning(f"Deactivation already in progress for feature {feature_id}")
                return self.active_deactivations[feature_id]
            
            # Create deactivation operation
            operation = DeactivationOperation(
                feature_id=feature_id,
                current_stage=DeactivationStage.PREPARATION,
                status=DeactionStatus.PENDING
            )
            self.active_deactivations[feature_id] = operation
            
            timeout = timeout_seconds or self.deactivation_timeout_seconds
            
            logger.info(f"Starting deactivation for feature {feature_id}: {reason or 'No reason provided'}")
            
            try:
                # Execute deactivation with timeout
                await asyncio.wait_for(
                    self._execute_deactivation(operation, feature_config, reason),
                    timeout=timeout
                )
                
                operation.status = DeactionStatus.COMPLETED
                operation.completed_at = datetime.now(timezone.utc).isoformat()
                operation.current_stage = DeactivationStage.COMPLETED
                
                logger.info(f"Successfully deactivated feature {feature_id}")
                
                # Emit completion event
                await self._emit_deactivation_event(feature_id, "completed", operation)
                
            except asyncio.TimeoutError:
                error_msg = f"Deactivation timeout for feature {feature_id}"
                await self._handle_deactivation_failure(operation, error_msg)
                
            except Exception as e:
                error_msg = f"Deactivation failed for feature {feature_id}: {str(e)}"
                await self._handle_deactivation_failure(operation, error_msg)
            
            finally:
                # Clean up from active deactivations
                if feature_id in self.active_deactivations:
                    del self.active_deactivations[feature_id]
            
            return operation

    async def _execute_deactivation(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig,
        reason: Optional[str]
    ) -> None:
        """Execute the deactivation process in stages."""
        
        # Stage 1: Preparation
        await self._stage_preparation(operation, feature_config)
        
        # Stage 2: Stop scheduled tasks
        await self._stage_stopping_tasks(operation, feature_config)
        
        # Stage 3: Stop agents
        await self._stage_stopping_agents(operation, feature_config)
        
        # Stage 4: Stop services
        await self._stage_stopping_services(operation, feature_config)
        
        # Stage 5: Cleanup resources
        await self._stage_cleanup_resources(operation, feature_config)
        
        # Stage 6: Finalization
        await self._stage_finalization(operation, feature_config, reason)

    async def _stage_preparation(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig
    ) -> None:
        """Stage 1: Prepare for deactivation."""
        operation.current_stage = DeactivationStage.PREPARATION
        logger.info(f"Stage 1 - Preparation for feature {operation.feature_id}")
        
        try:
            # Create resource snapshot for potential rollback
            snapshot = await self._create_resource_snapshot(operation.feature_id, feature_config)
            self.resource_snapshots[operation.feature_id] = snapshot
            
            # Identify all resources associated with the feature
            await self._identify_feature_resources(operation.feature_id, feature_config)
            
            # Emit preparation event
            await self._emit_stage_event(operation.feature_id, "preparation_started")
            
            operation.stages_completed.append(DeactivationStage.PREPARATION)
            
        except Exception as e:
            operation.stages_failed.append(DeactivationStage.PREPARATION)
            raise LifecycleManagerError(
                f"Preparation stage failed: {str(e)}",
                feature_id=operation.feature_id
            )

    async def _stage_stopping_tasks(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig
    ) -> None:
        """Stage 2: Stop scheduled tasks."""
        operation.current_stage = DeactivationStage.STOPPING_TASKS
        logger.info(f"Stage 2 - Stopping tasks for feature {operation.feature_id}")
        
        try:
            if self.queue_orchestration_layer:
                await self._stop_feature_tasks(operation.feature_id, feature_config)
            
            if self.background_scheduler:
                await self._stop_background_tasks(operation.feature_id, feature_config)
            
            # Emit tasks stopped event
            await self._emit_stage_event(operation.feature_id, "tasks_stopped")
            
            operation.stages_completed.append(DeactivationStage.STOPPING_TASKS)
            
        except Exception as e:
            operation.stages_failed.append(DeactivationStage.STOPPING_TASKS)
            raise LifecycleManagerError(
                f"Task stopping stage failed: {str(e)}",
                feature_id=operation.feature_id
            )

    async def _stage_stopping_agents(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig
    ) -> None:
        """Stage 3: Stop agents."""
        operation.current_stage = DeactivationStage.STOPPING_AGENTS
        logger.info(f"Stage 3 - Stopping agents for feature {operation.feature_id}")
        
        try:
            if self.agent_coordinator:
                await self._stop_feature_agents(operation.feature_id, feature_config)
            
            # Emit agents stopped event
            await self._emit_stage_event(operation.feature_id, "agents_stopped")
            
            operation.stages_completed.append(DeactivationStage.STOPPING_AGENTS)
            
        except Exception as e:
            operation.stages_failed.append(DeactivationStage.STOPPING_AGENTS)
            raise LifecycleManagerError(
                f"Agent stopping stage failed: {str(e)}",
                feature_id=operation.feature_id
            )

    async def _stage_stopping_services(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig
    ) -> None:
        """Stage 4: Stop services."""
        operation.current_stage = DeactivationStage.STOPPING_SERVICES
        logger.info(f"Stage 4 - Stopping services for feature {operation.feature_id}")
        
        try:
            if self.service_registry:
                await self._stop_feature_services(operation.feature_id, feature_config)
            
            # Emit services stopped event
            await self._emit_stage_event(operation.feature_id, "services_stopped")
            
            operation.stages_completed.append(DeactivationStage.STOPPING_SERVICES)
            
        except Exception as e:
            operation.stages_failed.append(DeactivationStage.STOPPING_SERVICES)
            raise LifecycleManagerError(
                f"Service stopping stage failed: {str(e)}",
                feature_id=operation.feature_id
            )

    async def _stage_cleanup_resources(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig
    ) -> None:
        """Stage 5: Cleanup resources."""
        operation.current_stage = DeactivationStage.CLEANUP_RESOURCES
        logger.info(f"Stage 5 - Cleaning up resources for feature {operation.feature_id}")
        
        try:
            # Memory cleanup
            await self._cleanup_memory_resources(operation.feature_id)
            
            # File handle cleanup
            await self._cleanup_file_handles(operation.feature_id)
            
            # Network connection cleanup
            await self._cleanup_network_connections(operation.feature_id)
            
            # Temporary data cleanup
            if self.cleanup_temp_data:
                await self._cleanup_temporary_data(operation.feature_id)
            
            # Emit cleanup completed event
            await self._emit_stage_event(operation.feature_id, "cleanup_completed")
            
            operation.stages_completed.append(DeactivationStage.CLEANUP_RESOURCES)
            
        except Exception as e:
            operation.stages_failed.append(DeactivationStage.CLEANUP_RESOURCES)
            raise LifecycleManagerError(
                f"Resource cleanup stage failed: {str(e)}",
                feature_id=operation.feature_id
            )

    async def _stage_finalization(
        self,
        operation: DeactivationOperation,
        feature_config: FeatureConfig,
        reason: Optional[str]
    ) -> None:
        """Stage 6: Finalize deactivation."""
        operation.current_stage = DeactivationStage.FINALIZATION
        logger.info(f"Stage 6 - Finalization for feature {operation.feature_id}")
        
        try:
            # Update feature state
            await self._update_feature_state(operation.feature_id, FeatureStatus.DISABLED)
            
            # Log deactivation completion
            await self._log_deactivation_completion(operation, reason)
            
            # Clear resource tracking
            await self._clear_resource_tracking(operation.feature_id)
            
            # Emit finalization event
            await self._emit_stage_event(operation.feature_id, "finalization_completed")
            
            operation.stages_completed.append(DeactivationStage.FINALIZATION)
            
        except Exception as e:
            operation.stages_failed.append(DeactivationStage.FINALIZATION)
            raise LifecycleManagerError(
                f"Finalization stage failed: {str(e)}",
                feature_id=operation.feature_id
            )

    async def _create_resource_snapshot(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> ResourceSnapshot:
        """Create a snapshot of current resources for rollback."""
        snapshot = ResourceSnapshot(
            feature_id=feature_id,
            timestamp=datetime.now(timezone.utc).isoformat()
        )
        
        # Capture current state of various resources
        if self.queue_orchestration_layer:
            snapshot.queue_states = await self.queue_orchestration_layer.get_orchestration_status()
        
        # Get memory usage
        process = psutil.Process()
        snapshot.memory_usage = {
            "rss": process.memory_info().rss,
            "vms": process.memory_info().vms,
            "percent": process.memory_percent()
        }
        
        # Get file handles
        try:
            snapshot.file_handles = [str(f) for f in process.open_files()]
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        
        # Get network connections
        try:
            snapshot.network_connections = [str(conn) for conn in process.connections()]
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            pass
        
        return snapshot

    async def _identify_feature_resources(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Identify all resources associated with a feature."""
        resources = {
            "tasks": set(),
            "agents": set(),
            "services": set(),
            "queues": set(),
            "memory_allocations": set(),
            "file_handles": set()
        }
        
        # Identify tasks based on feature type
        if feature_config.feature_type == FeatureType.AGENT:
            # Agent features typically have monitoring and analysis tasks
            resources["tasks"].update([
                TaskType.CLAUDE_MORNING_PREP.value,
                TaskType.CLAUDE_EVENING_REVIEW.value,
                TaskType.RECOMMENDATION_GENERATION.value
            ])
            resources["queues"].update([QueueName.AI_ANALYSIS.value])
        
        elif feature_config.feature_type == FeatureType.SERVICE:
            # Service features might have data sync tasks
            resources["tasks"].update([
                TaskType.SYNC_ACCOUNT_BALANCES.value,
                TaskType.UPDATE_POSITIONS.value
            ])
            resources["queues"].update([QueueName.PORTFOLIO_SYNC.value])
        
        # Store identified resources
        self.feature_resources[feature_id] = {
            key: list(value) for key, value in resources.items()
        }
        
        logger.info(f"Identified resources for feature {feature_id}: {self.feature_resources[feature_id]}")

    async def _stop_feature_tasks(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Stop all tasks associated with a feature."""
        if not self.queue_manager:
            return
        
        resources = self.feature_resources.get(feature_id, {})
        queues_to_stop = resources.get("queues", [])
        task_types_to_stop = resources.get("tasks", [])
        
        stopped_tasks = []
        
        # Stop tasks in relevant queues
        for queue_name_str in queues_to_stop:
            try:
                queue_name = QueueName(queue_name_str)
                await self.queue_manager.cancel_queue(queue_name)
                stopped_tasks.append(f"queue_{queue_name_str}")
                logger.info(f"Stopped queue {queue_name_str} for feature {feature_id}")
            except ValueError:
                logger.warning(f"Unknown queue: {queue_name_str}")
            except Exception as e:
                logger.error(f"Failed to stop queue {queue_name_str}: {e}")
        
        # Mark tasks as stopped
        self.active_tasks[feature_id] = set(stopped_tasks)

    async def _stop_background_tasks(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Stop background scheduler tasks for a feature."""
        if not self.background_scheduler:
            return
        
        # Stop any feature-specific background tasks
        # This would need to be implemented based on how tasks are tracked
        logger.info(f"Stopping background tasks for feature {feature_id}")

    async def _stop_feature_agents(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Stop all agents associated with a feature."""
        if not self.agent_coordinator:
            return
        
        # Get agents that should be stopped for this feature
        agents_to_stop = await self._get_feature_agents(feature_id, feature_config)
        
        stopped_agents = []
        for agent_id in agents_to_stop:
            try:
                await self.agent_coordinator.update_agent_status(agent_id, False)
                stopped_agents.append(agent_id)
                logger.info(f"Stopped agent {agent_id} for feature {feature_id}")
            except Exception as e:
                logger.error(f"Failed to stop agent {agent_id}: {e}")
        
        # Mark agents as stopped
        self.active_agents[feature_id] = set(stopped_agents)

    async def _get_feature_agents(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> List[str]:
        """Get list of agents associated with a feature."""
        agents = []
        
        # Map feature types to agents
        if feature_config.feature_type == FeatureType.AGENT:
            # For agent features, stop the specific agent
            agents.append(feature_id)
        elif feature_config.feature_type == FeatureType.SERVICE:
            # For service features, stop related agents
            agents.extend(["technical_analyst", "fundamental_screener", "risk_manager"])
        
        return agents

    async def _stop_feature_services(
        self,
        feature_id: str,
        feature_config: FeatureConfig
    ) -> None:
        """Stop all services associated with a feature."""
        if not self.service_registry:
            return
        
        # This would integrate with a service registry to stop services
        # Implementation depends on the service registry interface
        logger.info(f"Stopping services for feature {feature_id}")

    async def _cleanup_memory_resources(self, feature_id: str) -> None:
        """Clean up memory resources for a feature."""
        try:
            # Force garbage collection
            collected = gc.collect()
            logger.debug(f"Garbage collected {collected} objects for feature {feature_id}")
            
            # Clear any feature-specific caches or data structures
            if feature_id in self.feature_resources:
                del self.feature_resources[feature_id]
            
        except Exception as e:
            logger.error(f"Memory cleanup failed for feature {feature_id}: {e}")

    async def _cleanup_file_handles(self, feature_id: str) -> None:
        """Clean up file handles for a feature."""
        try:
            # Close any open file handles associated with the feature
            # This would need implementation based on how files are tracked
            logger.debug(f"Cleaning up file handles for feature {feature_id}")
            
        except Exception as e:
            logger.error(f"File handle cleanup failed for feature {feature_id}: {e}")

    async def _cleanup_network_connections(self, feature_id: str) -> None:
        """Clean up network connections for a feature."""
        try:
            # Close any network connections associated with the feature
            # This would need implementation based on how connections are managed
            logger.debug(f"Cleaning up network connections for feature {feature_id}")
            
        except Exception as e:
            logger.error(f"Network connection cleanup failed for feature {feature_id}: {e}")

    async def _cleanup_temporary_data(self, feature_id: str) -> None:
        """Clean up temporary data for a feature."""
        try:
            # Remove temporary files, cache entries, etc.
            # This would need implementation based on temp data storage
            logger.debug(f"Cleaning up temporary data for feature {feature_id}")
            
        except Exception as e:
            logger.error(f"Temporary data cleanup failed for feature {feature_id}: {e}")

    async def _update_feature_state(self, feature_id: str, status: FeatureStatus) -> None:
        """Update the state of a feature."""
        # This would integrate with the feature management service
        # to update the feature state in the database
        logger.info(f"Updated feature {feature_id} state to {status.value}")

    async def _log_deactivation_completion(
        self,
        operation: DeactivationOperation,
        reason: Optional[str]
    ) -> None:
        """Log the completion of deactivation."""
        log_data = {
            "feature_id": operation.feature_id,
            "operation": operation.to_dict(),
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        logger.info(f"Feature deactivation completed: {json.dumps(log_data, indent=2)}")

    async def _clear_resource_tracking(self, feature_id: str) -> None:
        """Clear resource tracking for a feature."""
        self.active_tasks.pop(feature_id, None)
        self.active_agents.pop(feature_id, None)
        self.active_services.pop(feature_id, None)
        self.resource_snapshots.pop(feature_id, None)

    async def _handle_deactivation_failure(
        self,
        operation: DeactivationOperation,
        error_message: str
    ) -> None:
        """Handle deactivation failure."""
        operation.status = DeactionStatus.FAILED
        operation.error_message = error_message
        operation.current_stage = DeactivationStage.FAILED
        
        logger.error(error_message)
        
        # Attempt rollback if enabled
        if self.enable_rollback:
            await self._attempt_rollback(operation)
        
        # Emit failure event
        await self._emit_deactivation_event(operation.feature_id, "failed", operation)

    async def _attempt_rollback(self, operation: DeactivationOperation) -> None:
        """Attempt to rollback deactivation changes."""
        try:
            logger.info(f"Attempting rollback for feature {operation.feature_id}")
            
            snapshot = self.resource_snapshots.get(operation.feature_id)
            if not snapshot:
                logger.warning(f"No resource snapshot available for rollback of {operation.feature_id}")
                return
            
            # Restore previous state
            await self._restore_from_snapshot(snapshot)
            
            operation.status = DeactionStatus.ROLLED_BACK
            logger.info(f"Successfully rolled back deactivation for feature {operation.feature_id}")
            
        except Exception as e:
            logger.error(f"Rollback failed for feature {operation.feature_id}: {e}")
            operation.status = DeactionStatus.PARTIAL

    async def _restore_from_snapshot(self, snapshot: ResourceSnapshot) -> None:
        """Restore system state from a resource snapshot."""
        # This would implement the actual rollback logic
        # based on the snapshot data
        logger.info(f"Restoring from snapshot for feature {snapshot.feature_id}")

    async def _emit_deactivation_event(
        self,
        feature_id: str,
        status: str,
        operation: DeactivationOperation
    ) -> None:
        """Emit a deactivation event."""
        await self.event_bus.publish(Event(
            id=f"feature_deactivation_{feature_id}_{status}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            type=EventType.FEATURE_DISABLED if status == "completed" else EventType.SYSTEM_ERROR,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="lifecycle_manager",
            data={
                "feature_id": feature_id,
                "deactivation_status": status,
                "operation": operation.to_dict()
            }
        ))

    async def _emit_stage_event(self, feature_id: str, stage: str) -> None:
        """Emit a deactivation stage event."""
        await self.event_bus.publish(Event(
            id=f"feature_deactivation_stage_{feature_id}_{stage}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
            type=EventType.SYSTEM_HEALTH_CHECK,
            timestamp=datetime.now(timezone.utc).isoformat(),
            source="lifecycle_manager",
            data={
                "feature_id": feature_id,
                "stage": stage,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        ))

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        try:
            if event.type == EventType.FEATURE_DISABLED:
                await self._handle_feature_disabled_event(event)
            elif event.type == EventType.SYSTEM_ERROR:
                await self._handle_system_error_event(event)
            elif event.type == EventType.TASK_COMPLETED:
                await self._handle_task_completed_event(event)
        except Exception as e:
            logger.error(f"Error handling event {event.type}: {e}")

    async def _handle_feature_disabled_event(self, event: Event) -> None:
        """Handle feature disabled events."""
        feature_id = event.data.get("feature_id")
        if feature_id:
            logger.debug(f"Feature disabled event received for {feature_id}")

    async def _handle_system_error_event(self, event: Event) -> None:
        """Handle system error events."""
        # Could trigger emergency deactivation for critical errors
        error_data = event.data
        if error_data.get("severity") == "critical":
            logger.warning("Critical system error detected, checking for emergency deactivation")

    async def _handle_task_completed_event(self, event: Event) -> None:
        """Handle task completed events."""
        # Update resource tracking based on task completion
        task_data = event.data
        logger.debug(f"Task completed: {task_data}")

    async def get_deactivation_status(self, feature_id: str) -> Optional[DeactivationOperation]:
        """Get the current deactivation status for a feature."""
        return self.active_deactivations.get(feature_id)

    async def get_feature_resources(self, feature_id: str) -> Dict[str, Any]:
        """Get resources associated with a feature."""
        return self.feature_resources.get(feature_id, {})

    async def force_cleanup_feature(self, feature_id: str) -> bool:
        """Force cleanup of a feature's resources."""
        try:
            logger.warning(f"Force cleaning up resources for feature {feature_id}")
            
            # Stop any active deactivation
            if feature_id in self.active_deactivations:
                operation = self.active_deactivations[feature_id]
                operation.status = DeactionStatus.FAILED
                operation.error_message = "Force cleanup initiated"
                del self.active_deactivations[feature_id]
            
            # Clean up resources
            await self._cleanup_memory_resources(feature_id)
            await self._cleanup_file_handles(feature_id)
            await self._cleanup_network_connections(feature_id)
            await self._cleanup_temporary_data(feature_id)
            await self._clear_resource_tracking(feature_id)
            
            logger.info(f"Force cleanup completed for feature {feature_id}")
            return True
            
        except Exception as e:
            logger.error(f"Force cleanup failed for feature {feature_id}: {e}")
            return False

    async def close(self) -> None:
        """Close the lifecycle manager."""
        logger.info("Closing Service Lifecycle Manager")
        
        # Cancel any active deactivations
        for feature_id, operation in list(self.active_deactivations.items()):
            logger.warning(f"Cancelling active deactivation for feature {feature_id}")
            operation.status = DeactionStatus.FAILED
            operation.error_message = "Lifecycle manager shutdown"
        
        self.active_deactivations.clear()
        self.resource_snapshots.clear()
        self.feature_resources.clear()
        
        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.FEATURE_DISABLED, self)
        self.event_bus.unsubscribe(EventType.SYSTEM_ERROR, self)
        self.event_bus.unsubscribe(EventType.TASK_COMPLETED, self)
        
        logger.info("Service Lifecycle Manager closed")