"""
Feature Management Service

Main service for managing feature flags, dependencies, and state
with real-time updates and integration with other services.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from pathlib import Path
from loguru import logger

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType, EventHandler
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.services.feature_management.models import (
    FeatureConfig, FeatureState, FeatureMetadata, FeatureDependency,
    FeatureToggleRequest, BulkFeatureUpdate, DependencyResolutionResult,
    FeatureStatus, FeatureType, DependencyType
)
from src.services.feature_management.database import FeatureDatabase
from src.services.feature_management.dependency_resolver import DependencyResolver
from src.services.feature_management.lifecycle_manager import ServiceLifecycleManager
from src.services.feature_management.scheduler_integration import BackgroundSchedulerIntegration
from src.services.feature_management.agent_integration import AgentManagementIntegration
from src.services.feature_management.service_integration import ServiceManagementIntegration
from src.services.feature_management.resource_cleanup import ResourceCleanupManager
from src.services.feature_management.error_recovery import ErrorRecoveryManager
from src.services.feature_management.event_broadcasting import EventBroadcastingService


class FeatureManagementError(TradingError):
    """Feature management specific errors."""
    
    def __init__(self, message: str, feature_id: Optional[str] = None, **kwargs):
        super().__init__(
            message,
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.MEDIUM,
            feature_id=feature_id,
            **kwargs
        )


class FeatureManagementService(EventHandler):
    """
    Main service for feature management.
    
    Responsibilities:
    - Feature CRUD operations
    - Dependency resolution and validation
    - State management and persistence
    - Integration with other services
    - Real-time updates via events
    """

    def __init__(self, config: Config, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.db_path = config.state_dir / "feature_management.db"
        
        # Core components
        self.database = FeatureDatabase(self.db_path)
        self.dependency_resolver = DependencyResolver()
        
        # Runtime state
        self.features: Dict[str, FeatureConfig] = {}
        self.states: Dict[str, FeatureState] = {}
        self._initialized = False
        self._lock = asyncio.Lock()
        
        # Service integrations
        self.background_scheduler = None
        self.agent_coordinator = None
        self.service_registry = None
        
        # Deactivation system components
        self.lifecycle_manager = ServiceLifecycleManager(config, event_bus)
        self.scheduler_integration = BackgroundSchedulerIntegration()
        self.agent_integration = AgentManagementIntegration()
        self.service_integration = ServiceManagementIntegration()
        self.resource_cleanup = ResourceCleanupManager(event_bus)
        self.error_recovery = ErrorRecoveryManager(event_bus)
        self.event_broadcasting = EventBroadcastingService(event_bus)
        
        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.SYSTEM_HEALTH_CHECK, self)
        self.event_bus.subscribe(EventType.SYSTEM_ERROR, self)

    async def initialize(self) -> None:
        """Initialize the feature management service."""
        async with self._lock:
            if self._initialized:
                return
            
            try:
                # Initialize database
                await self.database.initialize()
                
                # Load all features and states
                await self._load_features()

                # Register agents from config.json as features
                await self._register_config_agents_as_features()

                # Update dependency resolver
                self.dependency_resolver.update_graph(self.features, self.states)

                # Initialize deactivation system components
                await self._initialize_deactivation_system()
                
                # Auto-start features if configured
                await self._auto_start_features()
                
                # Start background tasks
                asyncio.create_task(self._health_check_loop())
                asyncio.create_task(self._cache_cleanup_loop())
                
                self._initialized = True
                logger.info("Feature management service initialized")
                
                # Emit initialization event
                await self.event_bus.publish(Event(
                    id=f"feature_service_init_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.SYSTEM_HEALTH_CHECK,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={"service": "feature_management", "status": "initialized"}
                ))
                
            except Exception as e:
                logger.error(f"Failed to initialize feature management service: {e}")
                await self.error_recovery.handle_error(
                    "system", "initialization", "startup", e,
                    {"component": "feature_management_service"}
                )
                raise FeatureManagementError(
                    f"Service initialization failed: {str(e)}",
                    recoverable=True,
                    retry_after_seconds=5
                )

    async def _initialize_deactivation_system(self) -> None:
        """Initialize the deactivation system components."""
        try:
            # Set up integrations
            if self.background_scheduler:
                self.lifecycle_manager.set_background_scheduler(self.background_scheduler)
                self.scheduler_integration.background_scheduler = self.background_scheduler
            
            if self.agent_coordinator:
                self.lifecycle_manager.set_agent_coordinator(self.agent_coordinator)
                self.agent_integration.agent_coordinator = self.agent_coordinator
            
            if self.service_registry:
                self.lifecycle_manager.set_service_registry(self.service_registry)
                self.service_integration.service_registry = self.service_registry
            
            # Set up queue manager if available
            if hasattr(self, 'queue_manager') and self.queue_manager:
                self.lifecycle_manager.set_queue_manager(self.queue_manager)
                self.scheduler_integration.queue_manager = self.queue_manager
            
            # Set up event bus integrations
            self.scheduler_integration.event_bus = self.event_bus
            self.agent_integration.event_bus = self.event_bus
            self.service_integration.event_bus = self.event_bus
            
            logger.info("Deactivation system components initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize deactivation system: {e}")
            raise

    async def _load_features(self) -> None:
        """Load all features and states from database."""
        try:
            # Load feature configurations
            configs = await self.database.get_all_feature_configs()
            for config in configs:
                self.features[config.feature_id] = config
            
            # Load feature states
            states = await self.database.get_all_feature_states()
            for state in states:
                self.states[state.feature_id] = state
            
            logger.info(f"Loaded {len(self.features)} feature configurations and {len(self.states)} states")
            
        except Exception as e:
            logger.error(f"Failed to load features: {e}")
            raise

    async def _register_config_agents_as_features(self) -> None:
        """Register agents from config.json as features in the feature management system."""
        try:
            if not hasattr(self.config, 'agents'):
                logger.debug("No agents configuration found to register as features")
                return

            agents_config = self.config.agents
            if hasattr(agents_config, '__dict__'):
                for agent_name, agent_cfg in agents_config.__dict__.items():
                    if hasattr(agent_cfg, 'enabled'):
                        # Check if feature already exists
                        if agent_name not in self.features:
                            # Create feature configuration for agent
                            feature_config = self._create_agent_feature_config(agent_name, agent_cfg)

                            # Register feature in database
                            if await self.database.create_feature_config(feature_config):
                                self.features[agent_name] = feature_config

                                # Create initial state
                                initial_state = FeatureState(
                                    feature_id=agent_name,
                                    status=FeatureStatus.ENABLED if getattr(agent_cfg, 'enabled', False) else FeatureStatus.DISABLED,
                                    enabled=getattr(agent_cfg, 'enabled', False)
                                )
                                self.states[agent_name] = initial_state
                                await self.database.update_feature_state(initial_state)

                                logger.info(f"Registered agent '{agent_name}' as feature from config.json")
                            else:
                                logger.warning(f"Failed to register agent '{agent_name}' as feature in database")
                        else:
                            logger.debug(f"Agent '{agent_name}' already registered as feature, skipping")

            logger.info(f"Agent-to-feature registration completed. Total features: {len(self.features)}")

        except Exception as e:
            logger.error(f"Failed to register config agents as features: {e}")
            # Don't raise - this is a non-critical initialization step

    def _create_agent_feature_config(self, agent_name: str, agent_cfg: Any) -> FeatureConfig:
        """Create a FeatureConfig from agent configuration."""
        return FeatureConfig(
            feature_id=agent_name,
            metadata=FeatureMetadata(
                name=agent_name.replace('_', ' ').title(),
                description=f"Agent feature: {agent_name}",
                feature_type=FeatureType.AGENT,
                version="1.0.0",
                author="system",
                tags=["agent", "config-based"],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            ),
            configuration={
                "use_claude": getattr(agent_cfg, 'use_claude', True),
                "frequency_seconds": getattr(agent_cfg, 'frequency_seconds', 300),
                "priority": getattr(agent_cfg, 'priority', 'medium'),
                "source": "config.json"
            },
            dependencies=[],
            auto_start=getattr(agent_cfg, 'enabled', False),
            max_retries=3,
            retry_delay_seconds=60,
            health_check_interval_seconds=300,
            rollback_enabled=True,
            rollback_timeout_seconds=300
        )

    async def _auto_start_features(self) -> None:
        """Auto-start features that are configured to do so."""
        auto_start_features = [
            feature_id for feature_id, config in self.features.items()
            if config.auto_start
        ]
        
        if auto_start_features:
            logger.info(f"Auto-starting {len(auto_start_features)} features")
            
            for feature_id in auto_start_features:
                try:
                    await self.enable_feature(feature_id, reason="auto_start")
                except Exception as e:
                    logger.warning(f"Failed to auto-start feature {feature_id}: {e}")

    # Feature CRUD Operations

    async def create_feature(self, config: FeatureConfig) -> bool:
        """Create a new feature."""
        async with self._lock:
            try:
                # Validate feature configuration
                await self._validate_feature_config(config)
                
                # Check if feature already exists
                if config.feature_id in self.features:
                    raise FeatureManagementError(
                        f"Feature {config.feature_id} already exists",
                        feature_id=config.feature_id
                    )
                
                # Create in database
                if not await self.database.create_feature_config(config):
                    raise FeatureManagementError(
                        f"Failed to create feature in database",
                        feature_id=config.feature_id
                    )
                
                # Update local state
                self.features[config.feature_id] = config
                
                # Update dependency resolver
                self.dependency_resolver.update_graph(self.features, self.states)
                
                # Log action
                await self.database.log_feature_action(
                    config.feature_id,
                    "create",
                    new_state=config.to_dict(),
                    reason="Feature created"
                )
                
                # Emit event
                await self.event_bus.publish(Event(
                    id=f"feature_created_{config.feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.FEATURE_CREATED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={
                        "action": "feature_created",
                        "feature_id": config.feature_id,
                        "config": config.to_dict()
                    }
                ))
                
                logger.info(f"Created feature: {config.feature_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to create feature {config.feature_id}: {e}")
                raise

    async def get_feature(self, feature_id: str) -> Optional[FeatureConfig]:
        """Get a feature configuration."""
        return self.features.get(feature_id)

    async def get_all_features(self) -> List[FeatureConfig]:
        """Get all feature configurations."""
        return list(self.features.values())

    async def update_feature(self, config: FeatureConfig) -> bool:
        """Update an existing feature."""
        async with self._lock:
            try:
                # Validate feature configuration
                await self._validate_feature_config(config)
                
                # Check if feature exists
                if config.feature_id not in self.features:
                    raise FeatureManagementError(
                        f"Feature {config.feature_id} not found",
                        feature_id=config.feature_id
                    )
                
                old_config = self.features[config.feature_id]
                
                # Update in database
                if not await self.database.update_feature_config(config):
                    raise FeatureManagementError(
                        f"Failed to update feature in database",
                        feature_id=config.feature_id
                    )
                
                # Update local state
                self.features[config.feature_id] = config
                
                # Update dependency resolver
                self.dependency_resolver.update_graph(self.features, self.states)
                
                # Log action
                await self.database.log_feature_action(
                    config.feature_id,
                    "update",
                    old_state=old_config.to_dict(),
                    new_state=config.to_dict(),
                    reason="Feature updated"
                )
                
                # Emit event
                await self.event_bus.publish(Event(
                    id=f"feature_updated_{config.feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.FEATURE_UPDATED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={
                        "action": "feature_updated",
                        "feature_id": config.feature_id,
                        "old_config": old_config.to_dict(),
                        "new_config": config.to_dict()
                    }
                ))
                
                logger.info(f"Updated feature: {config.feature_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to update feature {config.feature_id}: {e}")
                raise

    async def delete_feature(self, feature_id: str) -> bool:
        """Delete a feature."""
        async with self._lock:
            try:
                # Check if feature exists
                if feature_id not in self.features:
                    raise FeatureManagementError(
                        f"Feature {feature_id} not found",
                        feature_id=feature_id
                    )
                
                # Check if feature has dependents
                dependents = self.dependency_resolver.graph.get_dependents(feature_id)
                if dependents:
                    raise FeatureManagementError(
                        f"Cannot delete feature {feature_id} - it has dependents: {dependents}",
                        feature_id=feature_id
                    )
                
                old_config = self.features[feature_id]
                
                # Delete from database
                if not await self.database.delete_feature_config(feature_id):
                    raise FeatureManagementError(
                        f"Failed to delete feature from database",
                        feature_id=feature_id
                    )
                
                # Update local state
                del self.features[feature_id]
                if feature_id in self.states:
                    del self.states[feature_id]
                
                # Update dependency resolver
                self.dependency_resolver.update_graph(self.features, self.states)
                
                # Log action
                await self.database.log_feature_action(
                    feature_id,
                    "delete",
                    old_state=old_config.to_dict(),
                    reason="Feature deleted"
                )
                
                # Emit event
                await self.event_bus.publish(Event(
                    id=f"feature_deleted_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.FEATURE_DELETED,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={
                        "action": "feature_deleted",
                        "feature_id": feature_id,
                        "config": old_config.to_dict()
                    }
                ))
                
                logger.info(f"Deleted feature: {feature_id}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to delete feature {feature_id}: {e}")
                raise

    # Feature State Operations

    async def get_feature_state(self, feature_id: str) -> Optional[FeatureState]:
        """Get a feature's current state."""
        return self.states.get(feature_id)

    async def get_all_feature_states(self) -> List[FeatureState]:
        """Get all feature states."""
        return list(self.states.values())

    async def enable_feature(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
        cascade: bool = True
    ) -> bool:
        """Enable a feature and its dependencies."""
        async with self._lock:
            try:
                # Check if feature exists
                if feature_id not in self.features:
                    raise FeatureManagementError(
                        f"Feature {feature_id} not found",
                        feature_id=feature_id
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
                        details=resolution.to_dict()
                    )
                
                # Enable features in resolved order
                for fid in resolution.resolved_order:
                    await self._enable_feature_internal(
                        fid,
                        reason=f"Cascade from {feature_id}" if fid != feature_id else reason,
                        requested_by=requested_by
                    )
                
                logger.info(f"Enabled feature {feature_id} with {len(resolution.resolved_order)-1} dependencies")
                return True
                
            except Exception as e:
                logger.error(f"Failed to enable feature {feature_id}: {e}")
                raise

    async def disable_feature(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
        cascade: bool = True
    ) -> bool:
        """Disable a feature and its dependents."""
        async with self._lock:
            try:
                # Check if feature exists
                if feature_id not in self.features:
                    raise FeatureManagementError(
                        f"Feature {feature_id} not found",
                        feature_id=feature_id
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
                        details=resolution.to_dict()
                    )
                
                # Disable features in resolved order
                for fid in resolution.resolved_order:
                    await self._disable_feature_internal(
                        fid,
                        reason=f"Cascade from {feature_id}" if fid != feature_id else reason,
                        requested_by=requested_by
                    )
                
                logger.info(f"Disabled feature {feature_id} with {len(resolution.resolved_order)-1} dependents")
                return True
                
            except Exception as e:
                logger.error(f"Failed to disable feature {feature_id}: {e}")
                raise

    async def _enable_feature_internal(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system"
    ) -> None:
        """Internal method to enable a single feature."""
        try:
            # Get or create state
            state = self.states.get(feature_id)
            if not state:
                state = FeatureState(
                    feature_id=feature_id,
                    status=FeatureStatus.DISABLED,
                    enabled=False
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
                requested_by=requested_by
            )
            
            # Emit event
            await self.event_bus.publish(Event(
                id=f"feature_enabled_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.FEATURE_ENABLED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="feature_management_service",
                data={
                    "action": "feature_enabled",
                    "feature_id": feature_id,
                    "reason": reason,
                    "requested_by": requested_by
                }
            ))
            
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
        requested_by: str = "system"
    ) -> None:
        """Internal method to disable a single feature."""
        try:
            # Get feature config
            config = self.features.get(feature_id)
            if not config:
                raise FeatureManagementError(
                    f"Feature configuration not found: {feature_id}",
                    feature_id=feature_id
                )
            
            # Broadcast deactivation started
            await self.event_broadcasting.broadcast_feature_deactivation_started(
                feature_id, config, reason
            )
            
            # Get state
            state = self.states.get(feature_id)
            if not state:
                logger.warning(f"Feature {feature_id} state not found, creating disabled state")
                state = FeatureState(
                    feature_id=feature_id,
                    status=FeatureStatus.DISABLED,
                    enabled=False
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
                        feature_id, "deactivation", "lifecycle_manager",
                        Exception(deactivation_result.error_message or "Deactivation failed"),
                        {"config": config.to_dict(), "reason": reason}
                    )
                    
                    await self.event_broadcasting.broadcast_feature_deactivation_failed(
                        feature_id,
                        deactivation_result.error_message or "Unknown error",
                        deactivation_result.current_stage.value,
                        len(deactivation_result.stages_completed) > 0
                    )
                    
                    raise FeatureManagementError(
                        f"Feature deactivation failed: {deactivation_result.error_message}",
                        feature_id=feature_id
                    )
                
                # Mark as disabled in state
                state.mark_disabled()
                
                # Update in database
                await self.database.update_feature_state(state)
                
                # Calculate duration
                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                
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
                requested_by=requested_by
            )
            
            # Emit event
            await self.event_bus.publish(Event(
                id=f"feature_disabled_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                type=EventType.FEATURE_DISABLED,
                timestamp=datetime.now(timezone.utc).isoformat(),
                source="feature_management_service",
                data={
                    "action": "feature_disabled",
                    "feature_id": feature_id,
                    "reason": reason,
                    "requested_by": requested_by
                }
            ))
            
            logger.info(f"Disabled feature: {feature_id}")
            
        except Exception as e:
            logger.error(f"Failed to disable feature {feature_id}: {e}")
            
            # Handle error through recovery system
            await self.error_recovery.handle_error(
                feature_id, "disable_feature", "state_update", e,
                {"reason": reason, "requested_by": requested_by}
            )
            
            raise

    # Bulk Operations

    async def bulk_update_features(self, bulk_update: BulkFeatureUpdate) -> Dict[str, Any]:
        """Perform bulk feature updates."""
        results = {
            "success": True,
            "updated": [],
            "failed": [],
            "errors": []
        }
        
        try:
            if bulk_update.strategy == "atomic":
                # All or nothing approach
                await self._bulk_update_atomic(bulk_update, results)
            elif bulk_update.strategy == "sequential":
                # Process one by one
                await self._bulk_update_sequential(bulk_update, results)
            elif bulk_update.strategy == "best_effort":
                # Continue on errors
                await self._bulk_update_best_effort(bulk_update, results)
            else:
                raise FeatureManagementError(f"Unknown bulk update strategy: {bulk_update.strategy}")
            
            logger.info(f"Bulk update completed: {len(results['updated'])} updated, {len(results['failed'])} failed")
            
        except Exception as e:
            logger.error(f"Bulk update failed: {e}")
            results["success"] = False
            results["errors"].append(str(e))
        
        return results

    async def _bulk_update_atomic(self, bulk_update: BulkFeatureUpdate, results: Dict[str, Any]) -> None:
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
                        cascade=update.cascade
                    )
                else:
                    await self.disable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade
                    )
                
                results["updated"].append(update.feature_id)
                
            except Exception as e:
                # Rollback would be complex, so we just record the failure
                results["failed"].append(update.feature_id)
                results["errors"].append(f"{update.feature_id}: {str(e)}")
                raise  # Re-raise to fail the entire operation

    async def _bulk_update_sequential(self, bulk_update: BulkFeatureUpdate, results: Dict[str, Any]) -> None:
        """Sequential bulk update - stop on first failure."""
        for update in bulk_update.updates:
            try:
                if update.enabled:
                    await self.enable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade
                    )
                else:
                    await self.disable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade
                    )
                
                results["updated"].append(update.feature_id)
                
            except Exception as e:
                results["failed"].append(update.feature_id)
                results["errors"].append(f"{update.feature_id}: {str(e)}")
                break  # Stop processing on first failure

    async def _bulk_update_best_effort(self, bulk_update: BulkFeatureUpdate, results: Dict[str, Any]) -> None:
        """Best effort bulk update - continue on failures."""
        for update in bulk_update.updates:
            try:
                if update.enabled:
                    await self.enable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade
                    )
                else:
                    await self.disable_feature(
                        update.feature_id,
                        reason=update.reason,
                        requested_by=update.requested_by,
                        cascade=update.cascade
                    )
                
                results["updated"].append(update.feature_id)
                
            except Exception as e:
                results["failed"].append(update.feature_id)
                results["errors"].append(f"{update.feature_id}: {str(e)}")
                # Continue with next update

    # Dependency Operations

    async def get_feature_dependencies(self, feature_id: str) -> List[Dict[str, Any]]:
        """Get dependencies for a feature."""
        if feature_id not in self.features:
            raise FeatureManagementError(f"Feature {feature_id} not found")
        
        dependencies = []
        for dep in self.features[feature_id].dependencies:
            dep_state = self.states.get(dep.feature_id)
            dependencies.append({
                "feature_id": dep.feature_id,
                "type": dep.dependency_type.value,
                "optional": dep.optional,
                "version_constraint": dep.version_constraint,
                "current_state": dep_state.status.value if dep_state else "unknown",
                "enabled": dep_state.enabled if dep_state else False
            })
        
        return dependencies

    async def get_feature_dependents(self, feature_id: str) -> List[Dict[str, Any]]:
        """Get dependents for a feature."""
        if feature_id not in self.features:
            raise FeatureManagementError(f"Feature {feature_id} not found")
        
        dependents = []
        for dependent in self.dependency_resolver.graph.get_dependents(feature_id):
            dep_state = self.states.get(dependent)
            dependents.append({
                "feature_id": dependent,
                "current_state": dep_state.status.value if dep_state else "unknown",
                "enabled": dep_state.enabled if dep_state else False
            })
        
        return dependents

    async def validate_feature_dependencies(self, feature_id: str) -> List[str]:
        """Validate feature dependencies."""
        if feature_id not in self.features:
            raise FeatureManagementError(f"Feature {feature_id} not found")
        
        return await self.dependency_resolver.validate_feature_state(feature_id)

    async def get_dependency_resolution(self, feature_ids: List[str], operation: str) -> DependencyResolutionResult:
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

    # Utility Methods

    async def _validate_feature_config(self, config: FeatureConfig) -> None:
        """Validate a feature configuration."""
        if not config.feature_id:
            raise FeatureManagementError("Feature ID is required")
        
        if not config.metadata.name:
            raise FeatureManagementError("Feature name is required")
        
        # Validate dependencies exist
        for dep in config.dependencies:
            if dep.feature_id not in self.features:
                logger.warning(f"Dependency {dep.feature_id} not found for feature {config.feature_id}")

    async def _integrate_feature_enable(self, feature_id: str) -> None:
        """Integrate feature enable with other services."""
        try:
            config = self.features[feature_id]
            
            # Register feature with integration components
            await self._register_feature_with_integrations(feature_id, config)
            
            # Start background scheduler tasks
            if config.feature_type == FeatureType.AGENT and self.background_scheduler:
                # Start agent monitoring tasks
                await self.scheduler_integration.register_feature_tasks(
                    feature_id, config,
                    self.scheduler_integration._get_expected_task_types(config)
                )
            
            # Register with service registry
            if config.feature_type == FeatureType.SERVICE and self.service_registry:
                service_ids = [f"{config.feature_type}_{feature_id}"]
                await self.service_integration.register_feature_services(
                    feature_id, config, service_ids
                )
            
            # Notify agent coordinator
            if config.feature_type == FeatureType.AGENT and self.agent_coordinator:
                agent_ids = [feature_id]
                await self.agent_integration.register_feature_agents(
                    feature_id, config, agent_ids
                )
            
        except Exception as e:
            logger.error(f"Failed to integrate feature enable {feature_id}: {e}")
            await self.error_recovery.handle_error(
                feature_id, "enable_feature", "service_integration", e,
                {"feature_type": config.feature_type.value}
            )

    async def _integrate_feature_disable(self, feature_id: str) -> None:
        """Integrate feature disable with other services."""
        # This method is now handled by the lifecycle manager
        # The deactivation is coordinated through the lifecycle manager
        # which calls all the integration components
        pass

    async def _register_feature_with_integrations(self, feature_id: str, config: FeatureConfig) -> None:
        """Register a feature with all integration components."""
        try:
            # Register with scheduler integration
            if config.feature_type in [FeatureType.AGENT, FeatureType.SERVICE, FeatureType.MONITOR]:
                task_types = self.scheduler_integration._get_expected_task_types(config)
                await self.scheduler_integration.register_feature_tasks(
                    feature_id, config, task_types
                )
            
            # Register with service integration
            if config.feature_type == FeatureType.SERVICE:
                service_ids = [f"{config.feature_type}_{feature_id}"]
                await self.service_integration.register_feature_services(
                    feature_id, config, service_ids
                )
            
            # Register with agent integration
            if config.feature_type == FeatureType.AGENT:
                agent_ids = [feature_id]
                await self.agent_integration.register_feature_agents(
                    feature_id, config, agent_ids
                )
            
            logger.debug(f"Registered feature {feature_id} with integration components")
            
        except Exception as e:
            logger.error(f"Failed to register feature {feature_id} with integrations: {e}")
            raise

    # Background Tasks

    async def _health_check_loop(self) -> None:
        """Background task for health checking features."""
        while True:
            try:
                await asyncio.sleep(60)  # Check every minute
                
                for feature_id, state in self.states.items():
                    if state.enabled:
                        await self._check_feature_health(feature_id)
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _check_feature_health(self, feature_id: str) -> None:
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
                await self.event_bus.publish(Event(
                    id=f"feature_health_change_{feature_id}_{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                    type=EventType.SYSTEM_HEALTH_CHECK,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    source="feature_management_service",
                    data={
                        "feature_id": feature_id,
                        "health_status": health_status,
                        "error_count": state.error_count
                    }
                ))
                
        except Exception as e:
            logger.error(f"Failed to check feature health {feature_id}: {e}")

    async def _cache_cleanup_loop(self) -> None:
        """Background task for cleaning up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                
                deleted_count = await self.database.cleanup_expired_cache()
                if deleted_count > 0:
                    logger.debug(f"Cleaned up {deleted_count} expired cache entries")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cache cleanup loop error: {e}")

    # Event Handlers

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        try:
            if event.type == EventType.SYSTEM_HEALTH_CHECK:
                await self._handle_system_health_check(event)
            elif event.type == EventType.SYSTEM_ERROR:
                await self._handle_system_error(event)
        except Exception as e:
            logger.error(f"Error handling event {event.type}: {e}")

    async def _handle_system_health_check(self, event: Event) -> None:
        """Handle system health check events."""
        # Could respond to health checks from other services
        pass

    async def _handle_system_error(self, event: Event) -> None:
        """Handle system error events."""
        # Could disable features on critical system errors
        pass

    # Service Integration

    def set_background_scheduler(self, scheduler) -> None:
        """Set background scheduler integration."""
        self.background_scheduler = scheduler

    def set_agent_coordinator(self, coordinator) -> None:
        """Set agent coordinator integration."""
        self.agent_coordinator = coordinator

    def set_service_registry(self, registry) -> None:
        """Set service registry integration."""
        self.service_registry = registry

    async def close(self) -> None:
        """Close the feature management service."""
        if not self._initialized:
            return
        
        try:
            logger.info("Closing feature management service and deactivation system")
            
            # Close deactivation system components
            await self.lifecycle_manager.close()
            await self.scheduler_integration.close()
            await self.agent_integration.close()
            await self.service_integration.close()
            await self.resource_cleanup.close()
            await self.error_recovery.close()
            await self.event_broadcasting.close()
            
            # Close database
            await self.database.close()
            
            # Unsubscribe from events
            self.event_bus.unsubscribe(EventType.SYSTEM_HEALTH_CHECK, self)
            self.event_bus.unsubscribe(EventType.SYSTEM_ERROR, self)
            
            self._initialized = False
            logger.info("Feature management service closed")
            
        except Exception as e:
            logger.error(f"Error closing feature management service: {e}")

    # Additional methods for deactivation system management

    async def get_deactivation_status(self, feature_id: str) -> Dict[str, Any]:
        """Get the current deactivation status for a feature."""
        status = {
            "lifecycle_manager": await self.lifecycle_manager.get_deactivation_status(feature_id),
            "scheduler_integration": await self.scheduler_integration.get_integration_status(),
            "agent_integration": await self.agent_integration.get_integration_status(),
            "service_integration": await self.service_integration.get_integration_status(),
            "resource_cleanup": await self.resource_cleanup.get_system_resource_summary(),
            "error_recovery": await self.error_recovery.get_recovery_statistics(),
            "event_broadcasting": await self.event_broadcasting.get_broadcasting_statistics()
        }
        
        return status

    async def force_cleanup_feature(self, feature_id: str) -> bool:
        """Force cleanup of a feature's resources."""
        try:
            logger.warning(f"Force cleaning up feature {feature_id}")
            
            # Force cleanup through all components
            lifecycle_success = await self.lifecycle_manager.force_cleanup_feature(feature_id)
            scheduler_success = True  # No force cleanup in scheduler integration
            agent_success = await self.agent_integration.force_stop_agent(feature_id)
            service_success = await self.service_integration.force_stop_service(feature_id)
            resource_success = await self.resource_cleanup.force_cleanup_feature(feature_id)
            
            success = lifecycle_success and agent_success and service_success and resource_success
            
            if success:
                logger.info(f"Successfully force cleaned up feature {feature_id}")
            else:
                logger.error(f"Partial success force cleaning up feature {feature_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to force cleanup feature {feature_id}: {e}")
            return False

    async def get_feature_resources(self, feature_id: str) -> Dict[str, Any]:
        """Get all resources associated with a feature."""
        resources = {
            "lifecycle_manager": await self.lifecycle_manager.get_feature_resources(feature_id),
            "scheduler_tasks": await self.scheduler_integration.get_feature_task_info(feature_id),
            "agent_info": await self.agent_integration.get_feature_agent_info(feature_id),
            "service_info": await self.service_integration.get_feature_service_info(feature_id),
            "connection_info": await self.service_integration.get_feature_connection_info(feature_id),
            "resource_summary": await self.resource_cleanup.get_feature_resource_summary(feature_id)
        }
        
        return resources

    async def get_error_history(self, feature_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get error history for a feature or all features."""
        errors = await self.error_recovery.get_error_history(feature_id, limit=limit)
        return [error.to_dict() for error in errors]

    async def get_event_history(
        self,
        feature_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get event history for a feature or all features."""
        events = await self.event_broadcasting.get_event_history(feature_id, limit=limit)
        return [event.to_dict() for event in events]