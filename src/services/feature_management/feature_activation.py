"""
Feature Activation Operations

Handles enabling, disabling, and bulk activation of features with
dependency resolution and lifecycle management.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, Optional

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
from src.services.feature_management.models import (BulkFeatureUpdate,
                                                    FeatureConfig,
                                                    FeatureState,
                                                    FeatureStatus, FeatureType)
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


class FeatureActivation:
    """
    Handles feature activation operations.

    Responsibilities:
    - Enable/disable features
    - Manage activation dependencies
    - Bulk activation operations
    - Integration with lifecycle management
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
        error_recovery: ErrorRecoveryManager,
        event_broadcasting: EventBroadcastingService,
        lock: asyncio.Lock,
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
        self.error_recovery = error_recovery
        self.event_broadcasting = event_broadcasting
        self._lock = lock

    async def enable_feature(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
        cascade: bool = True,
    ) -> bool:
        """Enable a feature and its dependencies."""
        async with self._lock:
            try:
                # Check if feature exists
                if feature_id not in self.features:
                    raise FeatureManagementError(
                        f"Feature {feature_id} not found", feature_id=feature_id
                    )

                # Check if already enabled
                current_state = self.states.get(feature_id)
                if current_state and current_state.enabled:
                    logger.info(f"Feature {feature_id} is already enabled")
                    return True

                # Resolve enable order
                resolution = await self.dependency_resolver.resolve_enable_order(
                    [feature_id], include_dependencies=cascade
                )

                if not resolution.success:
                    raise FeatureManagementError(
                        f"Dependency resolution failed: {resolution.warnings}",
                        feature_id=feature_id,
                        details=resolution.to_dict(),
                    )

                # Enable features in resolved order
                for fid in resolution.resolved_order:
                    await self._enable_feature_internal(
                        fid,
                        reason=(
                            f"Cascade from {feature_id}"
                            if fid != feature_id
                            else reason
                        ),
                        requested_by=requested_by,
                    )

                logger.info(
                    f"Enabled feature {feature_id} with {len(resolution.resolved_order)-1} dependencies"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to enable feature {feature_id}: {e}")
                raise

    async def disable_feature(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
        cascade: bool = True,
    ) -> bool:
        """Disable a feature and its dependents."""
        async with self._lock:
            try:
                # Check if feature exists
                if feature_id not in self.features:
                    raise FeatureManagementError(
                        f"Feature {feature_id} not found", feature_id=feature_id
                    )

                # Check if already disabled
                current_state = self.states.get(feature_id)
                if current_state and not current_state.enabled:
                    logger.info(f"Feature {feature_id} is already disabled")
                    return True

                # Resolve disable order
                resolution = await self.dependency_resolver.resolve_disable_order(
                    [feature_id], cascade=cascade
                )

                if not resolution.success:
                    raise FeatureManagementError(
                        f"Dependency resolution failed: {resolution.warnings}",
                        feature_id=feature_id,
                        details=resolution.to_dict(),
                    )

                # Disable features in resolved order
                for fid in resolution.resolved_order:
                    await self._disable_feature_internal(
                        fid,
                        reason=(
                            f"Cascade from {feature_id}"
                            if fid != feature_id
                            else reason
                        ),
                        requested_by=requested_by,
                    )

                logger.info(
                    f"Disabled feature {feature_id} with {len(resolution.resolved_order)-1} dependents"
                )
                return True

            except Exception as e:
                logger.error(f"Failed to disable feature {feature_id}: {e}")
                raise

    async def _enable_feature_internal(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
    ) -> None:
        """Internal method to enable a single feature."""
        try:
            # Get or create state
            state = self.states.get(feature_id)
            if not state:
                state = FeatureState(
                    feature_id=feature_id, status=FeatureStatus.DISABLED, enabled=False
                )
                self.states[feature_id] = state

            old_state = state.to_dict()

            # Mark as enabled
            state.mark_enabled()

            # Update in database
            await self.database.update_feature_state(state)

            # Log action
            await self.database.log_feature_action(
                feature_id,
                "enable",
                old_state=old_state,
                new_state=state.to_dict(),
                reason=reason,
                requested_by=requested_by,
            )

            # Emit event
            await self.event_bus.publish(
                Event(
                    id=f"feature_enabled_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.FEATURE_ENABLED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={
                        "action": "feature_enabled",
                        "feature_id": feature_id,
                        "reason": reason,
                        "requested_by": requested_by,
                    },
                )
            )

            # Integrate with other services
            await self._integrate_feature_enable(feature_id)

            logger.debug(f"Enabled feature: {feature_id}")

        except Exception as e:
            logger.error(f"Failed to enable feature {feature_id}: {e}")
            raise

    async def _disable_feature_internal(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
    ) -> None:
        """Internal method to disable a single feature."""
        try:
            # Get feature config
            config = self.features.get(feature_id)
            if not config:
                raise FeatureManagementError(
                    f"Feature configuration not found: {feature_id}",
                    feature_id=feature_id,
                )

            # Broadcast deactivation started
            await self.event_broadcasting.broadcast_feature_deactivation_started(
                feature_id, config, reason
            )

            # Get state
            state = self.states.get(feature_id)
            if not state:
                logger.warning(
                    f"Feature {feature_id} state not found, creating disabled state"
                )
                state = FeatureState(
                    feature_id=feature_id, status=FeatureStatus.DISABLED, enabled=False
                )
                self.states[feature_id] = state

            old_state = state.to_dict()
            start_time = datetime.now(timezone.utc)

            try:
                # Execute deactivation through lifecycle manager
                deactivation_result = await self.lifecycle_manager.deactivate_feature(
                    feature_id, config, reason
                )

                if deactivation_result.status.value != "completed":
                    # Handle deactivation failure
                    await self.error_recovery.handle_error(
                        feature_id,
                        "deactivation",
                        "lifecycle_manager",
                        Exception(
                            deactivation_result.error_message or "Deactivation failed"
                        ),
                        {"config": config.to_dict(), "reason": reason},
                    )

                    await self.event_broadcasting.broadcast_feature_deactivation_failed(
                        feature_id,
                        deactivation_result.error_message or "Unknown error",
                        deactivation_result.current_stage.value,
                        len(deactivation_result.stages_completed) > 0,
                    )

                    raise FeatureManagementError(
                        f"Feature deactivation failed: {deactivation_result.error_message}",
                        feature_id=feature_id,
                    )

                # Mark as disabled in state
                state.mark_disabled()

                # Update in database
                await self.database.update_feature_state(state)

                # Calculate duration
                duration_ms = int(
                    (datetime.now(timezone.utc) - start_time).total_seconds() * 1000
                )

                # Get resource cleanup metrics
                resources_cleaned = {
                    "stages_completed": len(deactivation_result.stages_completed),
                    "rollback_data_size": len(str(deactivation_result.rollback_data)),
                }

                # Broadcast successful completion
                await self.event_broadcasting.broadcast_feature_deactivation_completed(
                    feature_id, duration_ms, resources_cleaned
                )

            except Exception as e:
                # Broadcast failure
                await self.event_broadcasting.broadcast_feature_deactivation_failed(
                    feature_id, str(e), "unknown", False
                )
                raise

            # Log action
            await self.database.log_feature_action(
                feature_id,
                "disable",
                old_state=old_state,
                new_state=state.to_dict(),
                reason=reason,
                requested_by=requested_by,
            )

            # Emit event
            await self.event_bus.publish(
                Event(
                    id=f"feature_disabled_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.FEATURE_DISABLED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={
                        "action": "feature_disabled",
                        "feature_id": feature_id,
                        "reason": reason,
                        "requested_by": requested_by,
                    },
                )
            )

            logger.info(f"Disabled feature: {feature_id}")

        except Exception as e:
            logger.error(f"Failed to disable feature {feature_id}: {e}")

            # Handle error through recovery system
            await self.error_recovery.handle_error(
                feature_id,
                "disable_feature",
                "state_update",
                e,
                {"reason": reason, "requested_by": requested_by},
            )

            raise

    async def bulk_update_features(
        self, bulk_update: BulkFeatureUpdate
    ) -> Dict[str, Any]:
        """Perform bulk feature updates."""
        results = {"success": True, "updated": [], "failed": [], "errors": []}

        try:
            if bulk_update.strategy == "atomic":
                await self._bulk_update_atomic(bulk_update, results)
            elif bulk_update.strategy == "sequential":
                await self._bulk_update_sequential(bulk_update, results)
            elif bulk_update.strategy == "best_effort":
                await self._bulk_update_best_effort(bulk_update, results)
            else:
                raise FeatureManagementError(
                    f"Unknown bulk update strategy: {bulk_update.strategy}"
                )

            logger.info(
                f"Bulk update completed: {len(results['updated'])} updated, {len(results['failed'])} failed"
            )

        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))

        return results

    async def _bulk_update_atomic(
        self, bulk_update: BulkFeatureUpdate, results: Dict[str, Any]
    ) -> None:
        """Atomic bulk update - all succeed or all fail."""
        # Validate all updates first
        for update in bulk_update.updates:
            if update.feature_id not in self.features:
                raise FeatureManagementError(f"Feature {update.feature_id} not found")

        # Apply all updates
        for update in bulk_update.updates:
            try:
                if update.enabled:
                    await self.enable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade,
                    )
                else:
                    await self.disable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade,
                    )

                results["updated"].append(update.feature_id)

            except Exception as e:
                results["failed"].append(update.feature_id)
                results["errors"].append(f"{update.feature_id}: {str(e)}")
                raise

    async def _bulk_update_sequential(
        self, bulk_update: BulkFeatureUpdate, results: Dict[str, Any]
    ) -> None:
        """Sequential bulk update - stop on first failure."""
        for update in bulk_update.updates:
            try:
                if update.enabled:
                    await self.enable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade,
                    )
                else:
                    await self.disable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade,
                    )

                results["updated"].append(update.feature_id)

            except Exception as e:
                results["failed"].append(update.feature_id)
                results["errors"].append(f"{update.feature_id}: {str(e)}")
                break

    async def _bulk_update_best_effort(
        self, bulk_update: BulkFeatureUpdate, results: Dict[str, Any]
    ) -> None:
        """Best effort bulk update - continue on failures."""
        for update in bulk_update.updates:
            try:
                if update.enabled:
                    await self.enable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade,
                    )
                else:
                    await self.disable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade,
                    )

                results["updated"].append(update.feature_id)

            except Exception as e:
                results["failed"].append(update.feature_id)
                results["errors"].append(f"{update.feature_id}: {str(e)}")

    async def _integrate_feature_enable(self, feature_id: str) -> None:
        """Integrate feature enable with other services."""
        try:
            config = self.features[feature_id]

            # Start background scheduler tasks
            if (
                config.feature_type == FeatureType.AGENT
                and self.scheduler_integration.background_scheduler
            ):
                await self.scheduler_integration.register_feature_tasks(
                    feature_id,
                    config,
                    self.scheduler_integration._get_expected_task_types(config),
                )

            # Register with service registry
            if (
                config.feature_type == FeatureType.SERVICE
                and self.service_integration.service_registry
            ):
                service_ids = [f"{config.feature_type}_{feature_id}"]
                await self.service_integration.register_feature_services(
                    feature_id, config, service_ids
                )

            # Notify agent coordinator
            if (
                config.feature_type == FeatureType.AGENT
                and self.agent_integration.agent_coordinator
            ):
                agent_ids = [feature_id]
                await self.agent_integration.register_feature_agents(
                    feature_id, config, agent_ids
                )

        except Exception as e:
            logger.error(f"Failed to integrate feature enable {feature_id}: {e}")
            await self.error_recovery.handle_error(
                feature_id,
                "enable_feature",
                "service_integration",
                e,
                {"feature_type": config.feature_type.value},
            )
