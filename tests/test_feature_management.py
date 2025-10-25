"""
Feature Management System Tests

Basic tests for the feature management service, models, and API endpoints.
"""

import pytest
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import json

from src.services.feature_management.models import (
    FeatureConfig, FeatureState, FeatureMetadata, FeatureDependency,
    FeatureType, FeatureStatus, DependencyType
)
from src.services.feature_management.database import FeatureDatabase
from src.services.feature_management.dependency_resolver import DependencyResolver
from src.services.feature_management.service import FeatureManagementService
from src.core.event_bus import EventBus
from src.config import Config


class TestFeatureModels:
    """Test feature data models."""

    def test_feature_metadata_creation(self):
        """Test feature metadata creation and validation."""
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature for unit testing",
            feature_type=FeatureType.AGENT,
            version="1.0.0",
            author="Test Author",
            tags={"test", "unit"},
            experimental=True
        )
        
        assert metadata.name == "Test Feature"
        assert metadata.feature_type == FeatureType.AGENT
        assert metadata.version == "1.0.0"
        assert metadata.experimental is True
        assert "test" in metadata.tags
        
        # Test serialization
        metadata_dict = metadata.to_dict()
        assert metadata_dict["name"] == "Test Feature"
        assert metadata_dict["feature_type"] == "agent"
        
        # Test deserialization
        restored_metadata = FeatureMetadata.from_dict(metadata_dict)
        assert restored_metadata.name == metadata.name
        assert restored_metadata.feature_type == metadata.feature_type

    def test_feature_dependency_creation(self):
        """Test feature dependency creation and validation."""
        dependency = FeatureDependency(
            feature_id="dependency_feature",
            dependency_type=DependencyType.REQUIRES,
            version_constraint=">=1.0.0",
            optional=False
        )
        
        assert dependency.feature_id == "dependency_feature"
        assert dependency.dependency_type == DependencyType.REQUIRES
        assert dependency.optional is False
        
        # Test serialization
        dep_dict = dependency.to_dict()
        assert dep_dict["feature_id"] == "dependency_feature"
        assert dep_dict["dependency_type"] == "requires"
        
        # Test deserialization
        restored_dep = FeatureDependency.from_dict(dep_dict)
        assert restored_dep.feature_id == dependency.feature_id
        assert restored_dep.dependency_type == dependency.dependency_type

    def test_feature_config_creation(self):
        """Test feature configuration creation and validation."""
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.SERVICE,
            version="1.0.0",
            author="Test Author"
        )
        
        dependency = FeatureDependency(
            feature_id="required_feature",
            dependency_type=DependencyType.REQUIRES,
            optional=False
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata,
            dependencies=[dependency],
            default_enabled=False,
            auto_start=True,
            timeout_seconds=60
        )
        
        assert config.feature_id == "test_feature"
        assert config.metadata.name == "Test Feature"
        assert len(config.dependencies) == 1
        assert config.dependencies[0].feature_id == "required_feature"
        assert config.auto_start is True
        assert config.timeout_seconds == 60

    def test_feature_state_creation(self):
        """Test feature state creation and management."""
        state = FeatureState(
            feature_id="test_feature",
            status=FeatureStatus.DISABLED,
            enabled=False
        )
        
        assert state.feature_id == "test_feature"
        assert state.status == FeatureStatus.DISABLED
        assert state.enabled is False
        assert state.error_count == 0
        
        # Test marking as enabled
        state.mark_enabled()
        assert state.enabled is True
        assert state.status == FeatureStatus.ENABLED
        assert state.last_enabled_at is not None
        
        # Test marking as disabled
        state.mark_disabled()
        assert state.enabled is False
        assert state.status == FeatureStatus.DISABLED
        assert state.last_disabled_at is not None
        
        # Test marking error
        state.mark_error("Test error message")
        assert state.status == FeatureStatus.ERROR
        assert state.error_count == 1
        assert state.last_error == "Test error message"


class TestFeatureDatabase:
    """Test feature database operations."""

    @pytest.fixture
    async def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test_features.db"
            db = FeatureDatabase(db_path)
            await db.initialize()
            yield db
            await db.close()

    @pytest.mark.asyncio
    async def test_create_and_get_feature_config(self, temp_db):
        """Test creating and retrieving a feature configuration."""
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.AGENT,
            version="1.0.0",
            author="Test Author"
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata,
            default_enabled=True
        )
        
        # Create feature
        result = await temp_db.create_feature_config(config)
        assert result is True
        
        # Retrieve feature
        retrieved_config = await temp_db.get_feature_config("test_feature")
        assert retrieved_config is not None
        assert retrieved_config.feature_id == "test_feature"
        assert retrieved_config.metadata.name == "Test Feature"
        assert retrieved_config.default_enabled is True

    @pytest.mark.asyncio
    async def test_update_feature_config(self, temp_db):
        """Test updating a feature configuration."""
        # Create initial feature
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.SERVICE,
            version="1.0.0",
            author="Test Author"
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata,
            default_enabled=False
        )
        
        await temp_db.create_feature_config(config)
        
        # Update feature
        updated_metadata = FeatureMetadata(
            name="Updated Test Feature",
            description="An updated test feature",
            feature_type=FeatureType.SERVICE,
            version="1.1.0",
            author="Test Author"
        )
        
        updated_config = FeatureConfig(
            feature_id="test_feature",
            metadata=updated_metadata,
            default_enabled=True
        )
        
        result = await temp_db.update_feature_config(updated_config)
        assert result is True
        
        # Verify update
        retrieved_config = await temp_db.get_feature_config("test_feature")
        assert retrieved_config.metadata.name == "Updated Test Feature"
        assert retrieved_config.metadata.version == "1.1.0"
        assert retrieved_config.default_enabled is True

    @pytest.mark.asyncio
    async def test_feature_state_operations(self, temp_db):
        """Test feature state operations."""
        # Create feature first
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.AGENT,
            version="1.0.0",
            author="Test Author"
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata
        )
        
        await temp_db.create_feature_config(config)
        
        # Create state
        state = FeatureState(
            feature_id="test_feature",
            status=FeatureStatus.DISABLED,
            enabled=False
        )
        
        result = await temp_db.create_feature_state(state)
        assert result is True
        
        # Retrieve state
        retrieved_state = await temp_db.get_feature_state("test_feature")
        assert retrieved_state is not None
        assert retrieved_state.feature_id == "test_feature"
        assert retrieved_state.enabled is False
        
        # Update state
        retrieved_state.mark_enabled()
        result = await temp_db.update_feature_state(retrieved_state)
        assert result is True
        
        # Verify update
        updated_state = await temp_db.get_feature_state("test_feature")
        assert updated_state.enabled is True
        assert updated_state.status == FeatureStatus.ENABLED

    @pytest.mark.asyncio
    async def test_audit_log(self, temp_db):
        """Test audit log functionality."""
        # Create feature first
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.SERVICE,
            version="1.0.0",
            author="Test Author"
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata
        )
        
        await temp_db.create_feature_config(config)
        
        # Log action
        result = await temp_db.log_feature_action(
            feature_id="test_feature",
            action="enable",
            old_state={"enabled": False},
            new_state={"enabled": True},
            reason="Test enable",
            requested_by="test_user"
        )
        assert result is True
        
        # Retrieve audit log
        audit_entries = await temp_db.get_feature_audit_log(feature_id="test_feature")
        assert len(audit_entries) == 1
        assert audit_entries[0]["feature_id"] == "test_feature"
        assert audit_entries[0]["action"] == "enable"
        assert audit_entries[0]["reason"] == "Test enable"
        assert audit_entries[0]["requested_by"] == "test_user"


class TestDependencyResolver:
    """Test dependency resolution engine."""

    @pytest.fixture
    def resolver(self):
        """Create a dependency resolver for testing."""
        return DependencyResolver()

    def test_simple_dependency_resolution(self, resolver):
        """Test simple dependency resolution."""
        # Create features with simple dependencies
        features = {
            "feature_a": FeatureConfig(
                feature_id="feature_a",
                metadata=FeatureMetadata(
                    name="Feature A",
                    description="Test feature A",
                    feature_type=FeatureType.SERVICE,
                    version="1.0.0",
                    author="Test"
                ),
                dependencies=[
                    FeatureDependency(
                        feature_id="feature_b",
                        dependency_type=DependencyType.REQUIRES,
                        optional=False
                    )
                ]
            ),
            "feature_b": FeatureConfig(
                feature_id="feature_b",
                metadata=FeatureMetadata(
                    name="Feature B",
                    description="Test feature B",
                    feature_type=FeatureType.SERVICE,
                    version="1.0.0",
                    author="Test"
                ),
                dependencies=[]
            )
        }
        
        states = {
            "feature_a": FeatureState(
                feature_id="feature_a",
                status=FeatureStatus.DISABLED,
                enabled=False
            ),
            "feature_b": FeatureState(
                feature_id="feature_b",
                status=FeatureStatus.DISABLED,
                enabled=False
            )
        }
        
        resolver.update_graph(features, states)
        
        # Test enable order resolution
        result = asyncio.run(resolver.resolve_enable_order(["feature_a"]))
        assert result.success is True
        assert "feature_b" in result.resolved_order
        assert "feature_a" in result.resolved_order
        # feature_b should come before feature_a
        assert result.resolved_order.index("feature_b") < result.resolved_order.index("feature_a")

    def test_circular_dependency_detection(self, resolver):
        """Test circular dependency detection."""
        # Create features with circular dependencies
        features = {
            "feature_a": FeatureConfig(
                feature_id="feature_a",
                metadata=FeatureMetadata(
                    name="Feature A",
                    description="Test feature A",
                    feature_type=FeatureType.SERVICE,
                    version="1.0.0",
                    author="Test"
                ),
                dependencies=[
                    FeatureDependency(
                        feature_id="feature_b",
                        dependency_type=DependencyType.REQUIRES,
                        optional=False
                    )
                ]
            ),
            "feature_b": FeatureConfig(
                feature_id="feature_b",
                metadata=FeatureMetadata(
                    name="Feature B",
                    description="Test feature B",
                    feature_type=FeatureType.SERVICE,
                    version="1.0.0",
                    author="Test"
                ),
                dependencies=[
                    FeatureDependency(
                        feature_id="feature_a",
                        dependency_type=DependencyType.REQUIRES,
                        optional=False
                    )
                ]
            )
        }
        
        states = {
            "feature_a": FeatureState(
                feature_id="feature_a",
                status=FeatureStatus.DISABLED,
                enabled=False
            ),
            "feature_b": FeatureState(
                feature_id="feature_b",
                status=FeatureStatus.DISABLED,
                enabled=False
            )
        }
        
        resolver.update_graph(features, states)
        
        # Test circular dependency detection
        cycles = resolver.graph.find_cycles()
        assert len(cycles) > 0
        
        # Test enable order resolution should fail
        result = asyncio.run(resolver.resolve_enable_order(["feature_a"]))
        assert result.success is False
        assert len(result.circular_dependencies) > 0

    def test_conflict_detection(self, resolver):
        """Test conflict detection between features."""
        # Create features with conflicts
        features = {
            "feature_a": FeatureConfig(
                feature_id="feature_a",
                metadata=FeatureMetadata(
                    name="Feature A",
                    description="Test feature A",
                    feature_type=FeatureType.SERVICE,
                    version="1.0.0",
                    author="Test"
                ),
                dependencies=[
                    FeatureDependency(
                        feature_id="feature_b",
                        dependency_type=DependencyType.CONFLICTS,
                        optional=False
                    )
                ]
            ),
            "feature_b": FeatureConfig(
                feature_id="feature_b",
                metadata=FeatureMetadata(
                    name="Feature B",
                    description="Test feature B",
                    feature_type=FeatureType.SERVICE,
                    version="1.0.0",
                    author="Test"
                ),
                dependencies=[]
            )
        }
        
        states = {
            "feature_a": FeatureState(
                feature_id="feature_a",
                status=FeatureStatus.DISABLED,
                enabled=False
            ),
            "feature_b": FeatureState(
                feature_id="feature_b",
                status=FeatureStatus.DISABLED,
                enabled=False
            )
        }
        
        resolver.update_graph(features, states)
        
        # Test conflict detection
        conflicts = resolver._check_conflicts({"feature_a", "feature_b"})
        assert len(conflicts) > 0
        assert conflicts[0]["type"] == "direct_conflict"


class TestFeatureManagementService:
    """Test feature management service integration."""

    @pytest.fixture
    async def temp_service(self):
        """Create a temporary feature management service."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test config
            config = Config()
            config.state_dir = Path(temp_dir)
            
            # Create event bus
            event_bus = EventBus(config)
            await event_bus.initialize()
            
            # Create service
            service = FeatureManagementService(config, event_bus)
            await service.initialize()
            
            yield service
            
            await service.close()
            await event_bus.close()

    @pytest.mark.asyncio
    async def test_service_initialization(self, temp_service):
        """Test service initialization."""
        assert temp_service._initialized is True
        assert temp_service.database is not None
        assert temp_service.dependency_resolver is not None

    @pytest.mark.asyncio
    async def test_create_and_enable_feature(self, temp_service):
        """Test creating and enabling a feature."""
        # Create feature
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.AGENT,
            version="1.0.0",
            author="Test Author"
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata,
            default_enabled=False
        )
        
        result = await temp_service.create_feature(config)
        assert result is True
        
        # Verify feature exists
        retrieved_config = await temp_service.get_feature("test_feature")
        assert retrieved_config is not None
        assert retrieved_config.feature_id == "test_feature"
        
        # Enable feature
        result = await temp_service.enable_feature("test_feature", reason="Test enable")
        assert result is True
        
        # Verify feature is enabled
        state = await temp_service.get_feature_state("test_feature")
        assert state is not None
        assert state.enabled is True
        assert state.status == FeatureStatus.ENABLED

    @pytest.mark.asyncio
    async def test_disable_feature(self, temp_service):
        """Test disabling a feature."""
        # Create and enable feature
        metadata = FeatureMetadata(
            name="Test Feature",
            description="A test feature",
            feature_type=FeatureType.SERVICE,
            version="1.0.0",
            author="Test Author"
        )
        
        config = FeatureConfig(
            feature_id="test_feature",
            metadata=metadata,
            default_enabled=True
        )
        
        await temp_service.create_feature(config)
        await temp_service.enable_feature("test_feature")
        
        # Disable feature
        result = await temp_service.disable_feature("test_feature", reason="Test disable")
        assert result is True
        
        # Verify feature is disabled
        state = await temp_service.get_feature_state("test_feature")
        assert state is not None
        assert state.enabled is False
        assert state.status == FeatureStatus.DISABLED


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])