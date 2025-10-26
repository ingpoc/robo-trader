"""FastAPI routes for the Queue Management Service."""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field

from ....models.scheduler import QueueName, TaskType
from ..core.queue_orchestration_layer import QueueOrchestrationLayer
from ..core.task_scheduling_engine import TaskSchedulingEngine
from ..core.queue_monitoring import QueueMonitoring


# Pydantic models for API requests/responses

class TaskRequest(BaseModel):
    """Request model for creating tasks."""
    queue_name: QueueName
    task_type: TaskType
    payload: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=5, ge=1, le=10)
    dependencies: Optional[List[str]] = None


class OrchestrationRequest(BaseModel):
    """Request model for orchestration operations."""
    queues: List[QueueName]
    mode: str = Field(default="sequential", pattern="^(sequential|parallel)$")


class RecommendationRequest(BaseModel):
    """Request model for recommendation generation."""
    trigger: str = "manual"
    market_conditions: Dict[str, Any] = Field(default_factory=dict)
    portfolio_status: Dict[str, Any] = Field(default_factory=dict)
    risk_tolerance: str = "moderate"
    max_recommendations: int = Field(default=5, ge=1, le=20)


class HealthResponse(BaseModel):
    """Response model for health checks."""
    status: str
    components: Dict[str, Any]
    timestamp: str


def create_router(
    orchestration_layer: QueueOrchestrationLayer,
    scheduling_engine: TaskSchedulingEngine,
    monitoring: QueueMonitoring
) -> APIRouter:
    """Create the FastAPI router for queue management endpoints."""

    router = APIRouter()

    # Orchestration endpoints

    @router.post("/orchestrate/sequential", summary="Execute queues sequentially")
    async def execute_sequential_workflow(request: OrchestrationRequest, background_tasks: BackgroundTasks):
        """Execute the specified queues in strict sequential order."""
        try:
            # Add to background tasks to avoid blocking
            background_tasks.add_task(orchestration_layer.execute_sequential_workflow, request.queues)

            return {
                "message": "Sequential workflow execution started",
                "queues": [q.value for q in request.queues],
                "mode": "sequential"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start sequential workflow: {e}")

    @router.post("/orchestrate/parallel", summary="Execute queues in parallel")
    async def execute_parallel_workflow(
        request: OrchestrationRequest,
        max_concurrent: int = Query(default=3, ge=1, le=10)
    ):
        """Execute the specified queues in parallel with concurrency control."""
        try:
            result = await orchestration_layer.execute_parallel_workflow(
                request.queues,
                max_concurrent
            )

            return {
                "execution_id": result["execution_id"],
                "status": result["status"],
                "results": result["results"],
                "duration": result["duration"],
                "mode": "parallel",
                "max_concurrent": max_concurrent
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to execute parallel workflow: {e}")

    @router.get("/orchestration/status", summary="Get orchestration status")
    async def get_orchestration_status():
        """Get current orchestration layer status."""
        try:
            status = orchestration_layer.get_orchestration_status()
            return status
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get orchestration status: {e}")

    # Scheduling endpoints

    @router.post("/tasks", summary="Create a new task")
    async def create_task(request: TaskRequest):
        """Create a new task in the specified queue."""
        try:
            task = await scheduling_engine.schedule_task_with_dependencies(
                queue_name=request.queue_name,
                task_type=request.task_type,
                payload=request.payload,
                dependencies=request.dependencies,
                priority=request.priority
            )

            return {
                "task_id": task.task_id,
                "queue_name": task.queue_name.value,
                "task_type": task.task_type.value,
                "priority": task.priority,
                "status": task.status.value,
                "created_at": task.created_at
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create task: {e}")

    @router.get("/scheduling/status", summary="Get scheduling status")
    async def get_scheduling_status():
        """Get current scheduling engine status."""
        try:
            status = scheduling_engine.get_scheduling_status()
            return status
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get scheduling status: {e}")

    # AI Analysis endpoints

    @router.post("/ai/recommendations", summary="Generate AI recommendations")
    async def generate_recommendations(request: RecommendationRequest):
        """Generate AI-powered trading recommendations."""
        try:
            # Create recommendation generation task
            task = await scheduling_engine.schedule_task_with_dependencies(
                queue_name=QueueName.AI_ANALYSIS,
                task_type=TaskType.RECOMMENDATION_GENERATION,
                payload={
                    "trigger": request.trigger,
                    "market_conditions": request.market_conditions,
                    "portfolio_status": request.portfolio_status,
                    "risk_tolerance": request.risk_tolerance,
                    "max_recommendations": request.max_recommendations
                },
                priority=9
            )

            return {
                "task_id": task.task_id,
                "message": "Recommendation generation task created",
                "trigger": request.trigger,
                "expected_completion": "Task will be processed by AI analysis queue"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate recommendations: {e}")

    @router.post("/ai/morning-prep", summary="Trigger morning preparation analysis")
    async def trigger_morning_prep(
        include_market_analysis: bool = True,
        include_portfolio_review: bool = True,
        risk_tolerance: str = "moderate"
    ):
        """Trigger AI-powered morning preparation analysis."""
        try:
            task = await scheduling_engine.schedule_task_with_dependencies(
                queue_name=QueueName.AI_ANALYSIS,
                task_type=TaskType.CLAUDE_MORNING_PREP,
                payload={
                    "include_market_analysis": include_market_analysis,
                    "include_portfolio_review": include_portfolio_review,
                    "risk_tolerance": risk_tolerance
                },
                priority=8
            )

            return {
                "task_id": task.task_id,
                "message": "Morning preparation analysis started",
                "analysis_type": "morning_prep"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to trigger morning prep: {e}")

    @router.post("/ai/evening-review", summary="Trigger evening performance review")
    async def trigger_evening_review(
        include_performance_analysis: bool = True,
        include_learning_insights: bool = True,
        generate_report: bool = True
    ):
        """Trigger AI-powered evening performance review."""
        try:
            task = await scheduling_engine.schedule_task_with_dependencies(
                queue_name=QueueName.AI_ANALYSIS,
                task_type=TaskType.CLAUDE_EVENING_REVIEW,
                payload={
                    "include_performance_analysis": include_performance_analysis,
                    "include_learning_insights": include_learning_insights,
                    "generate_report": generate_report
                },
                priority=7
            )

            return {
                "task_id": task.task_id,
                "message": "Evening review analysis started",
                "analysis_type": "evening_review"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to trigger evening review: {e}")

    # Monitoring endpoints

    @router.get("/monitoring/status", summary="Get monitoring status")
    async def get_monitoring_status():
        """Get comprehensive monitoring status."""
        try:
            status = monitoring.get_monitoring_status()
            return status
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get monitoring status: {e}")

    @router.get("/monitoring/alerts", summary="Get active alerts")
    async def get_alerts(
        severity: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = Query(default=50, ge=1, le=500)
    ):
        """Get monitoring alerts with optional filtering."""
        try:
            alerts = monitoring.get_alerts(
                severity=severity,
                resolved=resolved,
                limit=limit
            )
            return {"alerts": alerts, "count": len(alerts)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get alerts: {e}")

    @router.get("/monitoring/metrics", summary="Get metrics")
    async def get_metrics(
        name: Optional[str] = None,
        tags: Optional[str] = None,  # JSON string of tag filters
        limit: int = Query(default=1000, ge=1, le=10000)
    ):
        """Get monitoring metrics with optional filtering."""
        try:
            tag_filters = None
            if tags:
                import json
                tag_filters = json.loads(tags)

            metrics = monitoring.get_metrics(
                name=name,
                tags=tag_filters,
                limit=limit
            )
            return {"metrics": metrics, "count": len(metrics)}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")

    # Queue-specific endpoints

    @router.post("/queues/{queue_name}/tasks", summary="Create task in specific queue")
    async def create_queue_task(queue_name: QueueName, request: TaskRequest):
        """Create a task in a specific queue."""
        if request.queue_name != queue_name:
            raise HTTPException(
                status_code=400,
                detail="Queue name in path must match queue name in request"
            )

        try:
            task = await scheduling_engine.schedule_task_with_dependencies(
                queue_name=request.queue_name,
                task_type=request.task_type,
                payload=request.payload,
                dependencies=request.dependencies,
                priority=request.priority
            )

            return {
                "task_id": task.task_id,
                "queue_name": task.queue_name.value,
                "task_type": task.task_type.value,
                "status": "scheduled"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to create queue task: {e}")

    @router.get("/queues/{queue_name}/status", summary="Get queue status")
    async def get_queue_status(queue_name: QueueName):
        """Get status of a specific queue."""
        try:
            # This would need to be implemented to get individual queue status
            # For now, return basic info
            return {
                "queue_name": queue_name.value,
                "status": "active",  # Would be retrieved from actual queue
                "message": "Queue status endpoint - implementation pending"
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get queue status: {e}")

    # System endpoints

    @router.post("/system/start", summary="Start all queue management components")
    async def start_system():
        """Start all queue management components."""
        try:
            # This would trigger startup of all components
            return {
                "message": "System start initiated",
                "components": ["orchestration_layer", "scheduling_engine", "monitoring"]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to start system: {e}")

    @router.post("/system/stop", summary="Stop all queue management components")
    async def stop_system():
        """Stop all queue management components."""
        try:
            # This would trigger shutdown of all components
            return {
                "message": "System stop initiated",
                "components": ["orchestration_layer", "scheduling_engine", "monitoring"]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to stop system: {e}")

    return router