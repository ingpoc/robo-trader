"""
Feature Management Service

Main service for managing feature flags, dependencies, and state
with real-time updates and integration with other services.

This is a facade that delegates to focused modules:
- FeatureCRUD: Feature CRUD operations
- FeatureActivation: Enable/disable and bulk operations
- FeatureValidation: Dependency validation and monitoring
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from loguru import logger

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType, EventHandler
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.services.feature_management.models import (
    FeatureConfig, FeatureState, FeatureMetadata, FeatureDependency,
    BulkFeatureUpdate, DependencyResolutionResult,
    FeatureStatus, FeatureType
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

# Import focused modules
from src.services.feature_management.feature_crud import FeatureCRUD
from src.services.feature_management.feature_activation import FeatureActivation
from src.services.feature_management.feature_validation import FeatureValidation


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
    Main service for feature management (facade pattern).

    Delegates to focused modules:
    - FeatureCRUD: Create, read, update, delete operations
    - FeatureActivation: Enable, disable, bulk operations
    - FeatureValidation: Dependency validation, monitoring

    Responsibilities:
    - Service initialization and lifecycle
    - Event handling
    - Integration with other services
    - Background tasks
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

        # Focused operation modules (initialized after first load)
        self.crud: Optional[FeatureCRUD] = None
        self.activation: Optional[FeatureActivation] = None
        self.validation: Optional[FeatureValidation] = None

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

                # Initialize focused modules
                self._initialize_modules()

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

    def _initialize_modules(self) -> None:
        """Initialize focused operation modules."""
        self.crud = FeatureCRUD(
            self.database,
            self.event_bus,
            self.features,
            self.dependency_resolver,
            self._lock
        )

        self.activation = FeatureActivation(
            self.database,
            self.event_bus,
            self.features,
            self.states,
            self.dependency_resolver,
            self.lifecycle_manager,
            self.scheduler_integration,
            self.agent_integration,
            self.service_integration,
            self.error_recovery,
            self.event_broadcasting,
            self._lock
        )

        self.validation = FeatureValidation(
            self.database,
            self.event_bus,
            self.features,
            self.states,
            self.dependency_resolver,
            self.lifecycle_manager,
            self.scheduler_integration,
            self.agent_integration,
            self.service_integration,
            self.resource_cleanup,
            self.error_recovery,
            self.event_broadcasting
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

    # Feature CRUD Operations (delegate to FeatureCRUD)

    async def create_feature(self, config: FeatureConfig) -> bool:
        """Create a new feature."""
        result = await self.crud.create_feature(config)
        # Update dependency resolver after creating
        self.dependency_resolver.update_graph(self.features, self.states)
        return result

    async def get_feature(self, feature_id: str) -> Optional[FeatureConfig]:
        """Get a feature configuration."""
        return await self.crud.get_feature(feature_id)

    async def get_all_features(self) -> List[FeatureConfig]:
        """Get all feature configurations."""
        return await self.crud.get_all_features()

    async def update_feature(self, config: FeatureConfig) -> bool:
        """Update an existing feature."""
        result = await self.crud.update_feature(config)
        # Update dependency resolver after updating
        self.dependency_resolver.update_graph(self.features, self.states)
        return result

    async def delete_feature(self, feature_id: str) -> bool:
        """Delete a feature."""
        result = await self.crud.delete_feature(feature_id)
        # Remove from states if exists
        if feature_id in self.states:
            del self.states[feature_id]
        # Update dependency resolver after deleting
        self.dependency_resolver.update_graph(self.features, self.states)
        return result

    # Feature State Operations (delegate to FeatureActivation)

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
        result = await self.activation.enable_feature(feature_id, reason, requested_by, cascade)
        # Update dependency resolver after enabling
        self.dependency_resolver.update_graph(self.features, self.states)
        return result

    async def disable_feature(
        self,
        feature_id: str,
        reason: Optional[str] = None,
        requested_by: str = "system",
        cascade: bool = True
    ) -> bool:
        """Disable a feature and its dependents."""
        result = await self.activation.disable_feature(feature_id, reason, requested_by, cascade)
        # Update dependency resolver after disabling
        self.dependency_resolver.update_graph(self.features, self.states)
        return result

    # Bulk Operations (delegate to FeatureActivation)

    async def bulk_update_features(self, bulk_update: BulkFeatureUpdate) -> Dict[str, Any]:
        """Perform bulk feature updates."""
        return await self.activation.bulk_update_features(bulk_update)

    # Dependency Operations (delegate to FeatureValidation)

    async def get_feature_dependencies(self, feature_id: str) -> List[Dict[str, Any]]:
        """Get dependencies for a feature."""
        return await self.validation.get_feature_dependencies(feature_id)

    async def get_feature_dependents(self, feature_id: str) -> List[Dict[str, Any]]:
        """Get dependents for a feature."""
        return await self.validation.get_feature_dependents(feature_id)

    async def validate_feature_dependencies(self, feature_id: str) -> List[str]:
        """Validate feature dependencies."""
        return await self.validation.validate_feature_dependencies(feature_id)

    async def get_dependency_resolution(self, feature_ids: List[str], operation: str) -> DependencyResolutionResult:
        """Get dependency resolution for features."""
        return await self.validation.get_dependency_resolution(feature_ids, operation)

    # Background Tasks

    async def _health_check_loop(self) -> None:
        """Background task for health checking features."""
        while True:
            try:
                await asyncio.sleep(60)

                for feature_id, state in self.states.items():
                    if state.enabled:
                        await self.validation.check_feature_health(feature_id)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check loop error: {e}")

    async def _cache_cleanup_loop(self) -> None:
        """Background task for cleaning up expired cache entries."""
        while True:
            try:
                await asyncio.sleep(300)

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
        pass

    async def _handle_system_error(self, event: Event) -> None:
        """Handle system error events."""
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

    # Additional methods for deactivation system management (delegate to FeatureValidation)

    async def get_deactivation_status(self, feature_id: str) -> Dict[str, Any]:
        """Get the current deactivation status for a feature."""
        return await self.validation.get_deactivation_status(feature_id)

    async def force_cleanup_feature(self, feature_id: str) -> bool:
        """Force cleanup of a feature's resources."""
        return await self.validation.force_cleanup_feature(feature_id)

    async def get_feature_resources(self, feature_id: str) -> Dict[str, Any]:
        """Get all resources associated with a feature."""
        return await self.validation.get_feature_resources(feature_id)

    async def get_error_history(self, feature_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        """Get error history for a feature or all features."""
        return await self.validation.get_error_history(feature_id, limit)

    async def get_event_history(
        self,
        feature_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get event history for a feature or all features."""
        return await self.validation.get_event_history(feature_id, limit)
