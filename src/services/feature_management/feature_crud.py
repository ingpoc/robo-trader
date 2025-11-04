"""
Feature CRUD Operations

Handles creation, reading, updating, and deletion of feature configurations
with database persistence and event emission.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from loguru import logger

from src.core.event_bus import EventBus, Event, EventType
from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.services.feature_management.models import FeatureConfig
from src.services.feature_management.database import FeatureDatabase
from src.services.feature_management.dependency_resolver import DependencyResolver


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


class FeatureCRUD:
    """
    Handles feature CRUD operations.

    Responsibilities:
    - Create new features
    - Read feature configurations
    - Update existing features
    - Delete features
    - Validate feature configurations
    """

    def __init__(
        self,
        database: FeatureDatabase,
        event_bus: EventBus,
        features: Dict[str, FeatureConfig],
        dependency_resolver: DependencyResolver,
        lock: asyncio.Lock
    ):
        self.database = database
        self.event_bus = event_bus
        self.features = features
        self.dependency_resolver = dependency_resolver
        self._lock = lock

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
