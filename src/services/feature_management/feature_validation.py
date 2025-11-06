"""
Feature Validation and Monitoring

Handles feature dependency validation, health checking,
and monitoring operations.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.core.event_bus import Event, EventBus, EventType
from src.services.feature_management.agent_integration import \
    AgentManagementIntegration
from src.services.feature_management.database import FeatureDatabase
from src.services.feature_management.dependency_resolver import \
    DependencyResolver
from src.services.feature_management.error_recovery import ErrorRecoveryManager
from src.services.feature_management.event_broadcasting import \
    EventBroadcastingService
from src.services.feature_management.lifecycle_manager import \
    ServiceLifecycleManager
from src.services.feature_management.models import (DependencyResolutionResult,
                                                    FeatureConfig,
                                                    FeatureState)
from src.services.feature_management.resource_cleanup import \
    ResourceCleanupManager
from src.services.feature_management.scheduler_integration import \
    BackgroundSchedulerIntegration
from src.services.feature_management.service_integration import \
    ServiceManagementIntegration


class FeatureManagementError(TradingError):
    """Feature management specific errors."""

    def __init__(self, message: str, feature_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.MEDIUM,
            feature_id=feature_id,
            **kwargs,
        )


class FeatureValidation:
    """
    Handles feature validation and monitoring.

    Responsibilities:
    - Dependency validation
    - Health checking
    - Resource monitoring
    - Error history tracking
    """

    def __init__(
        self,
        database: FeatureDatabase,
        event_bus: EventBus,
        features: Dict[str, FeatureConfig],
        states: Dict[str, FeatureState],
        dependency_resolver: DependencyResolver,
        lifecycle_manager: ServiceLifecycleManager,
        scheduler_integration: BackgroundSchedulerIntegration,
        agent_integration: AgentManagementIntegration,
        service_integration: ServiceManagementIntegration,
        resource_cleanup: ResourceCleanupManager,
        error_recovery: ErrorRecoveryManager,
        event_broadcasting: EventBroadcastingService,
    ):
        self.database = database
        self.event_bus = event_bus
        self.features = features
        self.states = states
        self.dependency_resolver = dependency_resolver
        self.lifecycle_manager = lifecycle_manager
        self.scheduler_integration = scheduler_integration
        self.agent_integration = agent_integration
        self.service_integration = service_integration
        self.resource_cleanup = resource_cleanup
        self.error_recovery = error_recovery
        self.event_broadcasting = event_broadcasting

    async def get_feature_dependencies(self, feature_id: str) -> List[Dict[str, Any]]:
        """Get dependencies for a feature."""
        if feature_id not in self.features:
            raise FeatureManagementError(f"Feature {feature_id} not found")

        dependencies = []
        for dep in self.features[feature_id].dependencies:
            dep_state = self.states.get(dep.feature_id)
            dependencies.append(
                {
                    "feature_id": dep.feature_id,
                    "type": dep.dependency_type.value,
                    "optional": dep.optional,
                    "version_constraint": dep.version_constraint,
                    "current_state": dep_state.status.value if dep_state else "unknown",
                    "enabled": dep_state.enabled if dep_state else False,
                }
            )

        return dependencies

    async def get_feature_dependents(self, feature_id: str) -> List[Dict[str, Any]]:
        """Get dependents for a feature."""
        if feature_id not in self.features:
            raise FeatureManagementError(f"Feature {feature_id} not found")

        dependents = []
        for dependent in self.dependency_resolver.graph.get_dependents(feature_id):
            dep_state = self.states.get(dependent)
            dependents.append(
                {
                    "feature_id": dependent,
                    "current_state": dep_state.status.value if dep_state else "unknown",
                    "enabled": dep_state.enabled if dep_state else False,
                }
            )

        return dependents

    async def validate_feature_dependencies(self, feature_id: str) -> List[str]:
        """Validate feature dependencies."""
        if feature_id not in self.features:
            raise FeatureManagementError(f"Feature {feature_id} not found")

        return await self.dependency_resolver.validate_feature_state(feature_id)

    async def get_dependency_resolution(
        self, feature_ids: List[str], operation: str
    ) -> DependencyResolutionResult:
        """Get dependency resolution for features."""
        try:
            if operation == "enable":
                return await self.dependency_resolver.resolve_enable_order(feature_ids)
            elif operation == "disable":
                return await self.dependency_resolver.resolve_disable_order(feature_ids)
            else:
                raise FeatureManagementError(f"Unknown operation: {operation}")
        except Exception as e:
            logger.error(f"Failed to get dependency resolution: {e}")
            raise

    async def check_feature_health(self, feature_id: str) -> None:
        """Check health of a specific feature."""
        try:
            config = self.features.get(feature_id)
            state = self.states.get(feature_id)

            if not config or not state:
                return

            # Simple health check based on configuration
            health_status = "healthy"

            # Check error count
            if state.error_count > config.max_retries:
                health_status = "unhealthy"

            # Update health status
            if state.health_status != health_status:
                state.update_health(health_status)
                await self.database.update_feature_state(state)

                # Emit health change event
                await self.event_bus.publish(
                    Event(
                        id=f"feature_health_change_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                        type=EventType.SYSTEM_HEALTH_CHECK,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source="feature_management_service",
                        data={
                            "feature_id": feature_id,
                            "health_status": health_status,
                            "error_count": state.error_count,
                        },
                    )
                )

        except Exception as e:
            logger.error(f"Failed to check feature health {feature_id}: {e}")

    async def get_deactivation_status(self, feature_id: str) -> Dict[str, Any]:
        """Get the current deactivation status for a feature."""
        status = {
            "lifecycle_manager": await self.lifecycle_manager.get_deactivation_status(
                feature_id
            ),
            "scheduler_integration": await self.scheduler_integration.get_integration_status(),
            "agent_integration": await self.agent_integration.get_integration_status(),
            "service_integration": await self.service_integration.get_integration_status(),
            "resource_cleanup": await self.resource_cleanup.get_system_resource_summary(),
            "error_recovery": await self.error_recovery.get_recovery_statistics(),
            "event_broadcasting": await self.event_broadcasting.get_broadcasting_statistics(),
        }

        return status

    async def get_feature_resources(self, feature_id: str) -> Dict[str, Any]:
        """Get all resources associated with a feature."""
        resources = {
            "lifecycle_manager": await self.lifecycle_manager.get_feature_resources(
                feature_id
            ),
            "scheduler_tasks": await self.scheduler_integration.get_feature_task_info(
                feature_id
            ),
            "agent_info": await self.agent_integration.get_feature_agent_info(
                feature_id
            ),
            "service_info": await self.service_integration.get_feature_service_info(
                feature_id
            ),
            "connection_info": await self.service_integration.get_feature_connection_info(
                feature_id
            ),
            "resource_summary": await self.resource_cleanup.get_feature_resource_summary(
                feature_id
            ),
        }

        return resources

    async def get_error_history(
        self, feature_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get error history for a feature or all features."""
        errors = await self.error_recovery.get_error_history(feature_id, limit=limit)
        return [error.to_dict() for error in errors]

    async def get_event_history(
        self, feature_id: Optional[str] = None, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get event history for a feature or all features."""
        events = await self.event_broadcasting.get_event_history(
            feature_id, limit=limit
        )
        return [event.to_dict() for event in events]

    async def force_cleanup_feature(self, feature_id: str) -> bool:
        """Force cleanup of a feature's resources."""
        try:
            logger.warning(f"Force cleaning up feature {feature_id}")

            # Force cleanup through all components
            lifecycle_success = await self.lifecycle_manager.force_cleanup_feature(
                feature_id
            )
            scheduler_success = True
            agent_success = await self.agent_integration.force_stop_agent(feature_id)
            service_success = await self.service_integration.force_stop_service(
                feature_id
            )
            resource_success = await self.resource_cleanup.force_cleanup_feature(
                feature_id
            )

            success = (
                lifecycle_success
                and agent_success
                and service_success
                and resource_success
            )

            if success:
                logger.info(f"Successfully force cleaned up feature {feature_id}")
            else:
                logger.error(f"Partial success force cleaning up feature {feature_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to force cleanup feature {feature_id}: {e}")
            return False
