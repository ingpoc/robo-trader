# Queue Management API Directory Guidelines

> **Scope**: Applies to `src/services/queue_management/api/` directory. Read `src/services/queue_management/CLAUDE.md` for context.

## Purpose

The `api/` directory contains FastAPI route handlers for the Queue Management Service. It provides REST API endpoints for orchestration, task scheduling, and monitoring operations.

## Architecture Pattern

### FastAPI Route Pattern

The API uses FastAPI routers to organize endpoints by functionality. Routes handle request validation, orchestration execution, and response formatting.

### Directory Structure

```
api/
└── routes.py    # FastAPI route handlers
```

## Rules

### ✅ DO

- ✅ Use Pydantic models for request/response validation
- ✅ Validate request parameters
- ✅ Handle errors with proper HTTP status codes
- ✅ Use async route handlers
- ✅ Emit events for API operations
- ✅ Log API requests and responses
- ✅ Document endpoints with docstrings

### ❌ DON'T

- ❌ Skip request validation
- ❌ Return raw exceptions to clients
- ❌ Use blocking operations
- ❌ Mix business logic with route handlers
- ❌ Skip error handling
- ❌ Omit API documentation

## Route Pattern

```python
from fastapi import APIRouter
from src.services.queue_management.api.routes import create_router

# Create router with dependencies
router = create_router(
    orchestration_layer=orchestration,
    scheduling_engine=scheduler,
    monitoring=monitoring
)

# Register router with FastAPI app
app.include_router(router, prefix="/api/v1")
```

## Endpoint Structure

### Orchestration Endpoints

```python
@router.post("/orchestrate/sequential")
async def execute_sequential_workflow(
    request: OrchestrationRequest
) -> Dict[str, Any]:
    """Execute queues in sequential order."""
    result = await orchestration_layer.execute_sequential_workflow(
        queues=request.queues
    )
    return result
```

### Task Scheduling Endpoints

```python
@router.post("/tasks")
async def create_task(
    request: TaskRequest
) -> Dict[str, Any]:
    """Create new scheduler task."""
    task = await scheduling_engine.schedule_task_with_dependencies(
        queue_name=request.queue_name,
        task_type=request.task_type,
        payload=request.payload,
        dependencies=request.dependencies,
        priority=request.priority
    )
    return {"task_id": task.task_id, "status": "created"}
```

### Monitoring Endpoints

```python
@router.get("/monitoring/status")
async def get_monitoring_status() -> HealthResponse:
    """Get monitoring status."""
    status = monitoring.get_monitoring_status()
    return HealthResponse(
        status=status['overall_status'],
        components=status['components'],
        timestamp=status['timestamp']
    )
```

## Request Models

```python
class TaskRequest(BaseModel):
    """Request model for creating tasks."""
    queue_name: QueueName
    task_type: TaskType
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    dependencies: Optional[List[str]] = None
```

## Response Models

```python
class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str
    components: Dict[str, Any]
    timestamp: str
```

## Error Handling

```python
from fastapi import HTTPException

@router.post("/tasks")
async def create_task(request: TaskRequest):
    try:
        task = await scheduling_engine.schedule_task(...)
        return {"task_id": task.task_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Task creation error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

## Dependencies

API components depend on:
- `FastAPI` - For web framework
- `Pydantic` - For request/response validation
- `QueueOrchestrationLayer` - For orchestration operations
- `TaskSchedulingEngine` - For task scheduling
- `QueueMonitoring` - For monitoring operations

## Testing

Test API endpoints:

```python
import pytest
from fastapi.testclient import TestClient
from src.services.queue_management.main import app

client = TestClient(app)

def test_create_task():
    """Test task creation endpoint."""
    response = client.post("/api/v1/tasks", json={
        "queue_name": "AI_ANALYSIS",
        "task_type": "RECOMMENDATION_GENERATION",
        "payload": {"symbols": ["AAPL"]}
    })
    assert response.status_code == 200
    assert "task_id" in response.json()
```

## Maintenance

When adding new endpoints:

1. Create Pydantic models for request/response
2. Add route handler with validation
3. Implement error handling
4. Add API documentation
5. Update this CLAUDE.md file

