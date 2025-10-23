"""
Feature Management Data Models

Defines the core data structures for feature configuration, metadata,
and state management in the Robo Trader platform.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import uuid


class FeatureType(Enum):
    """Types of features in the system."""
    AGENT = "agent"
    SERVICE = "service"
    ALGORITHM = "algorithm"
    MONITOR = "monitor"
    UI_COMPONENT = "ui_component"
    INTEGRATION = "integration"


class FeatureStatus(Enum):
    """Feature status states."""
    DISABLED = "disabled"
    ENABLED = "enabled"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    TESTING = "testing"


class DependencyType(Enum):
    """Types of dependencies between features."""
    REQUIRES = "requires"  # Feature A requires Feature B to be enabled
    CONFLICTS = "conflicts"  # Feature A conflicts with Feature B
    ENHANCES = "enhances"  # Feature A enhances Feature B (optional)
    DEPRECATED_BY = "deprecated_by"  # Feature A is deprecated by Feature B


@dataclass
class FeatureDependency:
    """Represents a dependency relationship between features."""
    feature_id: str
    dependency_type: DependencyType
    version_constraint: Optional[str] = None  # e.g., ">=1.0.0", "~2.1.0"
    optional: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_id": self.feature_id,
            "dependency_type": self.dependency_type.value,
            "version_constraint": self.version_constraint,
            "optional": self.optional
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureDependency":
        """Create from dictionary."""
        return cls(
            feature_id=data["feature_id"],
            dependency_type=DependencyType(data["dependency_type"]),
            version_constraint=data.get("version_constraint"),
            optional=data.get("optional", False)
        )


@dataclass
class FeatureMetadata:
    """Metadata about a feature."""
    name: str
    description: str
    feature_type: FeatureType
    version: str
    author: str
    tags: Set[str] = field(default_factory=set)
    documentation_url: Optional[str] = None
    support_contact: Optional[str] = None
    experimental: bool = False
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "description": self.description,
            "feature_type": self.feature_type.value,
            "version": self.version,
            "author": self.author,
            "tags": list(self.tags),
            "documentation_url": self.documentation_url,
            "support_contact": self.support_contact,
            "experimental": self.experimental,
            "deprecated": self.deprecated,
            "deprecation_message": self.deprecation_message,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureMetadata":
        """Create from dictionary."""
        return cls(
            name=data["name"],
            description=data["description"],
            feature_type=FeatureType(data["feature_type"]),
            version=data["version"],
            author=data["author"],
            tags=set(data.get("tags", [])),
            documentation_url=data.get("documentation_url"),
            support_contact=data.get("support_contact"),
            experimental=data.get("experimental", False),
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message"),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat())
        )


@dataclass
class FeatureConfig:
    """Configuration for a feature."""
    feature_id: str
    metadata: FeatureMetadata
    dependencies: List[FeatureDependency] = field(default_factory=list)
    default_enabled: bool = False
    auto_start: bool = False
    restart_on_failure: bool = True
    max_retries: int = 3
    timeout_seconds: int = 30
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    environment_variables: Dict[str, str] = field(default_factory=dict)
    configuration_schema: Optional[Dict[str, Any]] = None
    health_check_url: Optional[str] = None
    metrics_enabled: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_id": self.feature_id,
            "metadata": self.metadata.to_dict(),
            "dependencies": [dep.to_dict() for dep in self.dependencies],
            "default_enabled": self.default_enabled,
            "auto_start": self.auto_start,
            "restart_on_failure": self.restart_on_failure,
            "max_retries": self.max_retries,
            "timeout_seconds": self.timeout_seconds,
            "resource_requirements": self.resource_requirements,
            "environment_variables": self.environment_variables,
            "configuration_schema": self.configuration_schema,
            "health_check_url": self.health_check_url,
            "metrics_enabled": self.metrics_enabled
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureConfig":
        """Create from dictionary."""
        return cls(
            feature_id=data["feature_id"],
            metadata=FeatureMetadata.from_dict(data["metadata"]),
            dependencies=[FeatureDependency.from_dict(dep) for dep in data.get("dependencies", [])],
            default_enabled=data.get("default_enabled", False),
            auto_start=data.get("auto_start", False),
            restart_on_failure=data.get("restart_on_failure", True),
            max_retries=data.get("max_retries", 3),
            timeout_seconds=data.get("timeout_seconds", 30),
            resource_requirements=data.get("resource_requirements", {}),
            environment_variables=data.get("environment_variables", {}),
            configuration_schema=data.get("configuration_schema"),
            health_check_url=data.get("health_check_url"),
            metrics_enabled=data.get("metrics_enabled", True)
        )


@dataclass
class FeatureState:
    """Runtime state of a feature."""
    feature_id: str
    status: FeatureStatus
    enabled: bool
    last_enabled_at: Optional[str] = None
    last_disabled_at: Optional[str] = None
    error_count: int = 0
    last_error: Optional[str] = None
    last_error_at: Optional[str] = None
    restart_count: int = 0
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    last_health_check: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    configuration: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_id": self.feature_id,
            "status": self.status.value,
            "enabled": self.enabled,
            "last_enabled_at": self.last_enabled_at,
            "last_disabled_at": self.last_disabled_at,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_error_at": self.last_error_at,
            "restart_count": self.restart_count,
            "health_status": self.health_status,
            "last_health_check": self.last_health_check,
            "metrics": self.metrics,
            "configuration": self.configuration,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureState":
        """Create from dictionary."""
        return cls(
            feature_id=data["feature_id"],
            status=FeatureStatus(data["status"]),
            enabled=data["enabled"],
            last_enabled_at=data.get("last_enabled_at"),
            last_disabled_at=data.get("last_disabled_at"),
            error_count=data.get("error_count", 0),
            last_error=data.get("last_error"),
            last_error_at=data.get("last_error_at"),
            restart_count=data.get("restart_count", 0),
            health_status=data.get("health_status", "unknown"),
            last_health_check=data.get("last_health_check"),
            metrics=data.get("metrics", {}),
            configuration=data.get("configuration", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat())
        )
    
    def mark_enabled(self) -> None:
        """Mark feature as enabled."""
        self.enabled = True
        self.status = FeatureStatus.ENABLED
        self.last_enabled_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.error_count = 0  # Reset error count on successful enable
        self.last_error = None
        self.last_error_at = None
    
    def mark_disabled(self) -> None:
        """Mark feature as disabled."""
        self.enabled = False
        self.status = FeatureStatus.DISABLED
        self.last_disabled_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def mark_error(self, error_message: str) -> None:
        """Mark feature as having an error."""
        self.status = FeatureStatus.ERROR
        self.error_count += 1
        self.last_error = error_message
        self.last_error_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def mark_maintenance(self) -> None:
        """Mark feature as in maintenance mode."""
        self.status = FeatureStatus.MAINTENANCE
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def update_health(self, health_status: str) -> None:
        """Update health status."""
        self.health_status = health_status
        self.last_health_check = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
    
    def increment_restart_count(self) -> None:
        """Increment restart count."""
        self.restart_count += 1
        self.updated_at = datetime.now(timezone.utc).isoformat()


@dataclass
class FeatureToggleRequest:
    """Request to toggle a feature state."""
    feature_id: str
    enabled: bool
    reason: Optional[str] = None
    requested_by: str = "system"
    cascade: bool = True  # Whether to cascade to dependencies
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "feature_id": self.feature_id,
            "enabled": self.enabled,
            "reason": self.reason,
            "requested_by": self.requested_by,
            "cascade": self.cascade
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FeatureToggleRequest":
        """Create from dictionary."""
        return cls(
            feature_id=data["feature_id"],
            enabled=data["enabled"],
            reason=data.get("reason"),
            requested_by=data.get("requested_by", "system"),
            cascade=data.get("cascade", True)
        )


@dataclass
class BulkFeatureUpdate:
    """Bulk update request for multiple features."""
    updates: List[FeatureToggleRequest]
    strategy: str = "atomic"  # atomic, sequential, best_effort
    timeout_seconds: int = 60
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "updates": [update.to_dict() for update in self.updates],
            "strategy": self.strategy,
            "timeout_seconds": self.timeout_seconds
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BulkFeatureUpdate":
        """Create from dictionary."""
        return cls(
            updates=[FeatureToggleRequest.from_dict(update) for update in data["updates"]],
            strategy=data.get("strategy", "atomic"),
            timeout_seconds=data.get("timeout_seconds", 60)
        )


@dataclass
class DependencyResolutionResult:
    """Result of dependency resolution."""
    success: bool
    resolved_order: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    circular_dependencies: List[List[str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "success": self.success,
            "resolved_order": self.resolved_order,
            "conflicts": self.conflicts,
            "missing_dependencies": self.missing_dependencies,
            "circular_dependencies": self.circular_dependencies,
            "warnings": self.warnings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DependencyResolutionResult":
        """Create from dictionary."""
        return cls(
            success=data["success"],
            resolved_order=data.get("resolved_order", []),
            conflicts=data.get("conflicts", []),
            missing_dependencies=data.get("missing_dependencies", []),
            circular_dependencies=data.get("circular_dependencies", []),
            warnings=data.get("warnings", [])
        )