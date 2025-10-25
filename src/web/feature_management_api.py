"""
Feature Management API Endpoints

REST API endpoints for managing features, dependencies, and state
with proper validation, error handling, and rate limiting.
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from slowapi import Limiter
from loguru import logger

from ..core.errors import TradingError, FeatureManagementError
from ..core.di import DependencyContainer
from .connection_manager import ConnectionManager
from ..services.feature_management import (
    FeatureManagementService, FeatureConfig, FeatureState, FeatureMetadata,
    FeatureDependency, FeatureToggleRequest, BulkFeatureUpdate,
    DependencyResolutionResult, FeatureType, FeatureStatus, DependencyType
)

# Create router
router = APIRouter(prefix="/api/features", tags=["feature-management"])

# Rate limiter
limiter = Limiter(key_func=lambda request: request.client.host if request.client else "unknown")

# Pydantic models for API requests/responses

class FeatureMetadataRequest(BaseModel):
    """Feature metadata request model."""
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field(..., min_length=1, max_length=500)
    feature_type: str = Field(..., regex="^(agent|service|algorithm|monitor|ui_component|integration)$")
    version: str = Field(..., regex="^\\d+\\.\\d+\\.\\d+$")
    author: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list, max_items=10)
    documentation_url: Optional[str] = Field(None, regex="^https?://.*")
    support_contact: Optional[str] = Field(None, max_length=100)
    experimental: bool = False
    deprecated: bool = False
    deprecation_message: Optional[str] = None

    @validator('tags')
    def validate_tags(cls, v):
        if len(set(v)) != len(v):
            raise ValueError("Duplicate tags not allowed")
        return v

class FeatureDependencyRequest(BaseModel):
    """Feature dependency request model."""
    feature_id: str = Field(..., min_length=1, max_length=100)
    dependency_type: str = Field(..., regex="^(requires|conflicts|enhances|deprecated_by)$")
    version_constraint: Optional[str] = Field(None, regex="^[><=~!]*\\d+\\.\\d+\\.\\d+$")
    optional: bool = False

class FeatureConfigRequest(BaseModel):
    """Feature configuration request model."""
    feature_id: str = Field(..., min_length=1, max_length=100, regex="^[a-z0-9_-]+$")
    metadata: FeatureMetadataRequest
    dependencies: List[FeatureDependencyRequest] = Field(default_factory=list, max_items=20)
    default_enabled: bool = False
    auto_start: bool = False
    restart_on_failure: bool = True
    max_retries: int = Field(3, ge=0, le=10)
    timeout_seconds: int = Field(30, ge=1, le=300)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    configuration_schema: Optional[Dict[str, Any]] = None
    health_check_url: Optional[str] = Field(None, regex="^https?://.*")
    metrics_enabled: bool = True

    @validator('dependencies')
    def validate_dependencies(cls, v):
        # Check for duplicate dependencies
        seen = set()
        for dep in v:
            if dep.feature_id in seen:
                raise ValueError(f"Duplicate dependency: {dep.feature_id}")
            seen.add(dep.feature_id)
        return v

class FeatureToggleRequest(BaseModel):
    """Feature toggle request model."""
    feature_id: str = Field(..., min_length=1, max_length=100)
    enabled: bool
    reason: Optional[str] = Field(None, max_length=500)
    requested_by: str = Field("api_user", max_length=100)
    cascade: bool = True

class BulkFeatureUpdateRequest(BaseModel):
    """Bulk feature update request model."""
    updates: List[FeatureToggleRequest] = Field(..., min_items=1, max_items=50)
    strategy: str = Field("atomic", regex="^(atomic|sequential|best_effort)$")
    timeout_seconds: int = Field(60, ge=1, le=300)

# Dependency injection

async def get_feature_service(request: Request) -> FeatureManagementService:
    """Get feature management service from DI container."""
    container: DependencyContainer = request.app.state.container
    if not container:
        raise HTTPException(status_code=500, detail="Dependency container not available")
    
    try:
        return await container.get("feature_management_service")
    except Exception as e:
        logger.error(f"Failed to get feature management service: {e}")
        raise HTTPException(status_code=500, detail="Feature management service not available")

async def get_connection_manager(request: Request) -> ConnectionManager:
    """Get connection manager for WebSocket broadcasts."""
    return request.app.state.connection_manager

# API Endpoints

@router.get("/", summary="List all features")
@limiter.limit("30/minute")
async def list_features(
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service)
):
    """Get all feature configurations with their current states."""
    try:
        features = await feature_service.get_all_features()
        states = await feature_service.get_all_feature_states()
        
        # Combine features with their states
        result = []
        for feature in features:
            state = next((s for s in states if s.feature_id == feature.feature_id), None)
            feature_dict = feature.to_dict()
            feature_dict["state"] = state.to_dict() if state else None
            result.append(feature_dict)
        
        return {
            "features": result,
            "total": len(result),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to list features: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{feature_id}", summary="Get feature details")
@limiter.limit("60/minute")
async def get_feature(
    feature_id: str,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service)
):
    """Get detailed information about a specific feature."""
    try:
        # Get feature configuration
        feature = await feature_service.get_feature(feature_id)
        if not feature:
            raise HTTPException(status_code=404, detail=f"Feature {feature_id} not found")
        
        # Get feature state
        state = await feature_service.get_feature_state(feature_id)
        
        # Get dependencies
        dependencies = await feature_service.get_feature_dependencies(feature_id)
        
        # Get dependents
        dependents = await feature_service.get_feature_dependents(feature_id)
        
        # Validate dependencies
        validation_warnings = await feature_service.validate_feature_dependencies(feature_id)
        
        return {
            "feature": feature.to_dict(),
            "state": state.to_dict() if state else None,
            "dependencies": dependencies,
            "dependents": dependents,
            "validation_warnings": validation_warnings,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to get feature {feature_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/", summary="Create a new feature")
@limiter.limit("10/minute")
async def create_feature(
    feature_request: FeatureConfigRequest,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Create a new feature configuration."""
    try:
        # Convert request to FeatureConfig
        metadata = FeatureMetadata(
            name=feature_request.metadata.name,
            description=feature_request.metadata.description,
            feature_type=FeatureType(feature_request.metadata.feature_type),
            version=feature_request.metadata.version,
            author=feature_request.metadata.author,
            tags=set(feature_request.metadata.tags),
            documentation_url=feature_request.metadata.documentation_url,
            support_contact=feature_request.metadata.support_contact,
            experimental=feature_request.metadata.experimental,
            deprecated=feature_request.metadata.deprecated,
            deprecation_message=feature_request.metadata.deprecation_message
        )
        
        dependencies = [
            FeatureDependency(
                feature_id=dep.feature_id,
                dependency_type=DependencyType(dep.dependency_type),
                version_constraint=dep.version_constraint,
                optional=dep.optional
            )
            for dep in feature_request.dependencies
        ]
        
        config = FeatureConfig(
            feature_id=feature_request.feature_id,
            metadata=metadata,
            dependencies=dependencies,
            default_enabled=feature_request.default_enabled,
            auto_start=feature_request.auto_start,
            restart_on_failure=feature_request.restart_on_failure,
            max_retries=feature_request.max_retries,
            timeout_seconds=feature_request.timeout_seconds,
            resource_requirements=feature_request.resource_requirements,
            environment_variables=feature_request.environment_variables,
            configuration_schema=feature_request.configuration_schema,
            health_check_url=feature_request.health_check_url,
            metrics_enabled=feature_request.metrics_enabled
        )
        
        # Create feature
        success = await feature_service.create_feature(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to create feature")
        
        # Broadcast update
        await connection_manager.broadcast({
            "type": "feature_created",
            "feature_id": config.feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "Feature created successfully",
            "feature_id": config.feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to create feature: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.put("/{feature_id}", summary="Update a feature")
@limiter.limit("10/minute")
async def update_feature(
    feature_id: str,
    feature_request: FeatureConfigRequest,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Update an existing feature configuration."""
    try:
        # Ensure feature ID matches
        if feature_request.feature_id != feature_id:
            raise HTTPException(status_code=400, detail="Feature ID in URL and body must match")
        
        # Convert request to FeatureConfig
        metadata = FeatureMetadata(
            name=feature_request.metadata.name,
            description=feature_request.metadata.description,
            feature_type=FeatureType(feature_request.metadata.feature_type),
            version=feature_request.metadata.version,
            author=feature_request.metadata.author,
            tags=set(feature_request.metadata.tags),
            documentation_url=feature_request.metadata.documentation_url,
            support_contact=feature_request.metadata.support_contact,
            experimental=feature_request.metadata.experimental,
            deprecated=feature_request.metadata.deprecated,
            deprecation_message=feature_request.metadata.deprecation_message
        )
        
        dependencies = [
            FeatureDependency(
                feature_id=dep.feature_id,
                dependency_type=DependencyType(dep.dependency_type),
                version_constraint=dep.version_constraint,
                optional=dep.optional
            )
            for dep in feature_request.dependencies
        ]
        
        config = FeatureConfig(
            feature_id=feature_request.feature_id,
            metadata=metadata,
            dependencies=dependencies,
            default_enabled=feature_request.default_enabled,
            auto_start=feature_request.auto_start,
            restart_on_failure=feature_request.restart_on_failure,
            max_retries=feature_request.max_retries,
            timeout_seconds=feature_request.timeout_seconds,
            resource_requirements=feature_request.resource_requirements,
            environment_variables=feature_request.environment_variables,
            configuration_schema=feature_request.configuration_schema,
            health_check_url=feature_request.health_check_url,
            metrics_enabled=feature_request.metrics_enabled
        )
        
        # Update feature
        success = await feature_service.update_feature(config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update feature")
        
        # Broadcast update
        await connection_manager.broadcast({
            "type": "feature_updated",
            "feature_id": config.feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "Feature updated successfully",
            "feature_id": config.feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to update feature {feature_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.delete("/{feature_id}", summary="Delete a feature")
@limiter.limit("5/minute")
async def delete_feature(
    feature_id: str,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Delete a feature configuration."""
    try:
        # Delete feature
        success = await feature_service.delete_feature(feature_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete feature")
        
        # Broadcast update
        await connection_manager.broadcast({
            "type": "feature_deleted",
            "feature_id": feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "message": "Feature deleted successfully",
            "feature_id": feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to delete feature {feature_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{feature_id}/enable", summary="Enable a feature")
@limiter.limit("20/minute")
async def enable_feature(
    feature_id: str,
    toggle_request: FeatureToggleRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Enable a feature and its dependencies."""
    try:
        # Ensure feature ID matches
        if toggle_request.feature_id != feature_id:
            raise HTTPException(status_code=400, detail="Feature ID in URL and body must match")
        
        # Enable feature
        success = await feature_service.enable_feature(
            feature_id=toggle_request.feature_id,
            reason=toggle_request.reason,
            requested_by=toggle_request.requested_by,
            cascade=toggle_request.cascade
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to enable feature")
        
        # Broadcast update in background
        background_tasks.add_task(
            connection_manager.broadcast,
            {
                "type": "feature_enabled",
                "feature_id": feature_id,
                "reason": toggle_request.reason,
                "requested_by": toggle_request.requested_by,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return {
            "message": "Feature enabled successfully",
            "feature_id": feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to enable feature {feature_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/{feature_id}/disable", summary="Disable a feature")
@limiter.limit("20/minute")
async def disable_feature(
    feature_id: str,
    toggle_request: FeatureToggleRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Disable a feature and its dependents."""
    try:
        # Ensure feature ID matches
        if toggle_request.feature_id != feature_id:
            raise HTTPException(status_code=400, detail="Feature ID in URL and body must match")
        
        # Disable feature
        success = await feature_service.disable_feature(
            feature_id=toggle_request.feature_id,
            reason=toggle_request.reason,
            requested_by=toggle_request.requested_by,
            cascade=toggle_request.cascade
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to disable feature")
        
        # Broadcast update in background
        background_tasks.add_task(
            connection_manager.broadcast,
            {
                "type": "feature_disabled",
                "feature_id": feature_id,
                "reason": toggle_request.reason,
                "requested_by": toggle_request.requested_by,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return {
            "message": "Feature disabled successfully",
            "feature_id": feature_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except HTTPException:
        raise
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to disable feature {feature_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/{feature_id}/dependencies", summary="Get feature dependencies")
@limiter.limit("30/minute")
async def get_feature_dependencies(
    feature_id: str,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service)
):
    """Get dependencies for a specific feature."""
    try:
        dependencies = await feature_service.get_feature_dependencies(feature_id)
        
        return {
            "feature_id": feature_id,
            "dependencies": dependencies,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to get dependencies for {feature_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/bulk-update", summary="Bulk update features")
@limiter.limit("5/minute")
async def bulk_update_features(
    bulk_request: BulkFeatureUpdateRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Perform bulk updates on multiple features."""
    try:
        # Convert request to BulkFeatureUpdate
        updates = [
            FeatureToggleRequest(
                feature_id=update.feature_id,
                enabled=update.enabled,
                reason=update.reason,
                requested_by=update.requested_by,
                cascade=update.cascade
            )
            for update in bulk_request.updates
        ]
        
        bulk_update = BulkFeatureUpdate(
            updates=updates,
            strategy=bulk_request.strategy,
            timeout_seconds=bulk_request.timeout_seconds
        )
        
        # Perform bulk update
        results = await feature_service.bulk_update_features(bulk_update)
        
        # Broadcast update in background
        background_tasks.add_task(
            connection_manager.broadcast,
            {
                "type": "bulk_feature_update",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return {
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except FeatureManagementError as e:
        raise HTTPException(status_code=400, detail=e.context.message)
    except Exception as e:
        logger.error(f"Failed to perform bulk update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/state", summary="Get all feature states")
@limiter.limit("30/minute")
async def get_feature_states(
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service)
):
    """Get current states of all features."""
    try:
        states = await feature_service.get_all_feature_states()
        
        return {
            "states": [state.to_dict() for state in states],
            "total": len(states),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get feature states: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reset", summary="Reset features to default")
@limiter.limit("5/minute")
async def reset_features(
    background_tasks: BackgroundTasks,
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service),
    connection_manager: ConnectionManager = Depends(get_connection_manager)
):
    """Reset all features to their default states."""
    try:
        # Get all features
        features = await feature_service.get_all_features()
        
        # Reset each feature to its default state
        results = {"success": True, "reset": [], "failed": [], "errors": []}
        
        for feature in features:
            try:
                if feature.default_enabled:
                    await feature_service.enable_feature(
                        feature.feature_id,
                        reason="reset_to_default",
                        requested_by="system"
                    )
                else:
                    await feature_service.disable_feature(
                        feature.feature_id,
                        reason="reset_to_default",
                        requested_by="system"
                    )
                
                results["reset"].append(feature.feature_id)
                
            except Exception as e:
                results["failed"].append(feature.feature_id)
                results["errors"].append(f"{feature.feature_id}: {str(e)}")
        
        # Broadcast update in background
        background_tasks.add_task(
            connection_manager.broadcast,
            {
                "type": "features_reset",
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return {
            "results": results,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to reset features: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/audit-log", summary="Get feature audit log")
@limiter.limit("20/minute")
async def get_audit_log(
    request: Request,
    feature_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    feature_service: FeatureManagementService = Depends(get_feature_service)
):
    """Get audit log for feature changes."""
    try:
        # Get audit log from database
        audit_entries = await feature_service.database.get_feature_audit_log(
            feature_id=feature_id,
            limit=min(limit, 1000),  # Max 1000 entries
            offset=offset
        )
        
        return {
            "entries": audit_entries,
            "total": len(audit_entries),
            "feature_id": feature_id,
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get audit log: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/health", summary="Get feature management health")
@limiter.limit("60/minute")
async def get_health(
    request: Request,
    feature_service: FeatureManagementService = Depends(get_feature_service)
):
    """Get health status of the feature management system."""
    try:
        # Get all features and their states
        features = await feature_service.get_all_features()
        states = await feature_service.get_all_feature_states()
        
        # Calculate health metrics
        total_features = len(features)
        enabled_features = sum(1 for state in states if state.enabled)
        healthy_features = sum(1 for state in states if state.health_status == "healthy")
        error_features = sum(1 for state in states if state.status == FeatureStatus.ERROR)
        
        health_status = {
            "status": "healthy",
            "total_features": total_features,
            "enabled_features": enabled_features,
            "disabled_features": total_features - enabled_features,
            "healthy_features": healthy_features,
            "error_features": error_features,
            "health_percentage": (healthy_features / total_features * 100) if total_features > 0 else 100,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Determine overall status
        if error_features > 0:
            health_status["status"] = "degraded"
        if error_features > total_features * 0.1:  # More than 10% errors
            health_status["status"] = "unhealthy"
        
        return health_status
        
    except Exception as e:
        logger.error(f"Failed to get health status: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")