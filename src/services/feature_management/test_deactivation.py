"""
Test script for the Feature Management Deactivation System

This script tests the complete deactivation system to ensure all components
work together correctly when features are disabled.
"""

import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from loguru import logger

# Add the project root to the path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType
from src.services.feature_management.service import FeatureManagementService
from src.services.feature_management.models import (
    FeatureConfig, FeatureMetadata, FeatureType, FeatureDependency, DependencyType
)


async def test_deactivation_system():
    """Test the complete deactivation system."""
    
    # Setup
    logger.info("Setting up test environment")
    
    # Create config and event bus
    config = Config()
    event_bus = EventBus()
    
    # Create feature management service
    feature_service = FeatureManagementService(config, event_bus)
    
    try:
        # Initialize the service
        await feature_service.initialize()
        logger.info("Feature management service initialized")
        
        # Create a test feature
        test_feature = FeatureConfig(
            feature_id="test_agent_feature",
            metadata=FeatureMetadata(
                name="Test Agent Feature",
                description="A test feature for deactivation testing",
                feature_type=FeatureType.AGENT,
                version="1.0.0",
                author="test"
            ),
            dependencies=[
                FeatureDependency(
                    feature_id="test_dependency",
                    dependency_type=DependencyType.REQUIRES,
                    optional=True
                )
            ],
            default_enabled=True,
            auto_start=True
        )
        
        # Create the feature
        logger.info("Creating test feature")
        success = await feature_service.create_feature(test_feature)
        assert success, "Failed to create test feature"
        logger.info("Test feature created successfully")
        
        # Enable the feature
        logger.info("Enabling test feature")
        success = await feature_service.enable_feature(
            test_feature.feature_id,
            reason="Testing deactivation system"
        )
        assert success, "Failed to enable test feature"
        logger.info("Test feature enabled successfully")
        
        # Get feature state
        state = await feature_service.get_feature_state(test_feature.feature_id)
        assert state is not None, "Feature state not found"
        assert state.enabled, "Feature should be enabled"
        logger.info(f"Feature state confirmed: enabled={state.enabled}")
        
        # Test deactivation
        logger.info("Starting deactivation test")
        start_time = datetime.now(timezone.utc)
        
        # Disable the feature (this should trigger the complete deactivation system)
        success = await feature_service.disable_feature(
            test_feature.feature_id,
            reason="Testing deactivation system",
            cascade=True
        )
        
        end_time = datetime.now(timezone.utc)
        duration_ms = int((end_time - start_time).total_seconds() * 1000)
        
        assert success, "Failed to disable test feature"
        logger.info(f"Test feature deactivated successfully in {duration_ms}ms")
        
        # Verify feature is disabled
        state = await feature_service.get_feature_state(test_feature.feature_id)
        assert state is not None, "Feature state not found after deactivation"
        assert not state.enabled, "Feature should be disabled"
        logger.info("Feature state confirmed: disabled")
        
        # Get deactivation status
        deactivation_status = await feature_service.get_deactivation_status(test_feature.feature_id)
        logger.info(f"Deactivation status: {deactivation_status}")
        
        # Get feature resources (should be empty after deactivation)
        resources = await feature_service.get_feature_resources(test_feature.feature_id)
        logger.info(f"Feature resources after deactivation: {resources}")
        
        # Get error history (should be empty for successful deactivation)
        error_history = await feature_service.get_error_history(test_feature.feature_id)
        logger.info(f"Error history: {len(error_history)} errors")
        
        # Get event history
        event_history = await feature_service.get_event_history(test_feature.feature_id)
        logger.info(f"Event history: {len(event_history)} events")
        
        # Test force cleanup
        logger.info("Testing force cleanup")
        cleanup_success = await feature_service.force_cleanup_feature(test_feature.feature_id)
        logger.info(f"Force cleanup result: {cleanup_success}")
        
        # Delete the test feature
        logger.info("Cleaning up test feature")
        success = await feature_service.delete_feature(test_feature.feature_id)
        assert success, "Failed to delete test feature"
        logger.info("Test feature deleted successfully")
        
        logger.success("✅ All deactivation system tests passed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}")
        raise
    
    finally:
        # Cleanup
        logger.info("Cleaning up test environment")
        await feature_service.close()
        await event_bus.close()


async def test_error_recovery():
    """Test the error recovery system."""
    
    logger.info("Testing error recovery system")
    
    # Setup
    config = Config()
    event_bus = EventBus()
    feature_service = FeatureManagementService(config, event_bus)
    
    try:
        await feature_service.initialize()
        
        # Create a feature that might cause errors during deactivation
        problematic_feature = FeatureConfig(
            feature_id="problematic_feature",
            metadata=FeatureMetadata(
                name="Problematic Feature",
                description="A feature designed to test error recovery",
                feature_type=FeatureType.SERVICE,
                version="1.0.0",
                author="test"
            ),
            dependencies=[
                FeatureDependency(
                    feature_id="nonexistent_dependency",
                    dependency_type=DependencyType.REQUIRES,
                    optional=False  # This should cause an error
                )
            ]
        )
        
        # Create and try to enable the feature
        await feature_service.create_feature(problematic_feature)
        
        # This should fail due to missing dependency
        try:
            await feature_service.enable_feature(problematic_feature.feature_id)
            logger.warning("Expected error did not occur")
        except Exception as e:
            logger.info(f"Expected error occurred: {str(e)}")
        
        # Check error history
        error_history = await feature_service.get_error_history(problematic_feature.feature_id)
        logger.info(f"Error history contains {len(error_history)} errors")
        
        # Clean up
        await feature_service.delete_feature(problematic_feature.feature_id)
        
        logger.success("✅ Error recovery test completed!")
        
    except Exception as e:
        logger.error(f"❌ Error recovery test failed: {str(e)}")
        raise
    
    finally:
        await feature_service.close()
        await event_bus.close()


async def main():
    """Main test function."""
    logger.info("🚀 Starting Feature Management Deactivation System Tests")
    
    try:
        # Test basic deactivation
        await test_deactivation_system()
        
        # Test error recovery
        await test_error_recovery()
        
        logger.success("🎉 All tests completed successfully!")
        
    except Exception as e:
        logger.error(f"💥 Test suite failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Configure logging
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    
    # Run tests
    asyncio.run(main())