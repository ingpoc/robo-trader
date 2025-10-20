"""
Task Scheduler Service
Manages background task orchestration and Celery workers
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional

from celery import Celery
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.shared import EventBus, Event, EventType
from services.shared.database import (
    check_db_health,
    close_db_pool,
    execute_query,
    execute_update,
    get_db_pool,
)
from services.shared.models import HealthCheck

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "task-scheduler")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8007))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/robo_trader")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost//")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

# ============================================================================
# CELERY APP
# ============================================================================

celery_app = Celery(SERVICE_NAME)
celery_app.conf.broker_url = CELERY_BROKER_URL
celery_app.conf.result_backend = CELERY_RESULT_BACKEND
celery_app.conf.task_serializer = "json"
celery_app.conf.accept_content = ["json"]
celery_app.conf.result_serializer = "json"
celery_app.conf.timezone = "Asia/Kolkata"


@celery_app.task(bind=True, name="analyze_market")
def analyze_market(self, symbol: str):
    """Background task: Analyze market for symbol"""
    logger.info(f"Analyzing market for {symbol}")
    return {"symbol": symbol, "status": "analyzed"}


@celery_app.task(bind=True, name="process_news")
def process_news(self, symbol: str):
    """Background task: Process news for symbol"""
    logger.info(f"Processing news for {symbol}")
    return {"symbol": symbol, "status": "processed"}


@celery_app.task(bind=True, name="check_earnings")
def check_earnings(self, symbol: str):
    """Background task: Check earnings for symbol"""
    logger.info(f"Checking earnings for {symbol}")
    return {"symbol": symbol, "status": "checked"}


# ============================================================================
# MODELS
# ============================================================================


class TaskRequest(BaseModel):
    """Task creation request"""
    task_type: str
    params: dict
    priority: str = "MEDIUM"


class ScheduledTask(BaseModel):
    """Scheduled task"""
    task_id: str
    task_type: str
    status: str
    created_at: datetime
    updated_at: datetime


# ============================================================================
# GLOBAL STATE
# ============================================================================

event_bus: EventBus = None
db_pool = None


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus, db_pool

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
        db_pool = await get_db_pool(DATABASE_URL)
        db_healthy = await check_db_health(db_pool)
        if not db_healthy:
            raise Exception("Database health check failed")

        event_bus = EventBus(RABBITMQ_URL)
        await event_bus.connect()

        logger.info(f"✅ {SERVICE_NAME} service started")

    except Exception as e:
        logger.error(f"❌ Failed to start {SERVICE_NAME}: {e}")
        raise

    yield

    logger.info(f"🛑 Shutting down {SERVICE_NAME} service...")
    try:
        if event_bus:
            await event_bus.disconnect()
        if db_pool:
            await close_db_pool()
        logger.info(f"✅ {SERVICE_NAME} service stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=f"{SERVICE_NAME} API",
    description="Background task orchestration and monitoring",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    checks = {
        "database": "healthy" if db_pool and await check_db_health(db_pool) else "unhealthy",
        "event_bus": "healthy" if event_bus and await event_bus.health_check() else "unhealthy",
        "celery": "connected",
    }
    return HealthCheck(status="healthy", service=SERVICE_NAME, checks=checks)


@app.post("/tasks")
async def create_task(req: TaskRequest):
    """Create and enqueue a task"""
    try:
        # Determine which Celery task to call
        task_mapping = {
            "analyze_market": analyze_market,
            "process_news": process_news,
            "check_earnings": check_earnings,
        }

        if req.task_type not in task_mapping:
            raise HTTPException(status_code=400, detail=f"Unknown task type: {req.task_type}")

        # Enqueue task
        celery_task = task_mapping[req.task_type]
        async_result = celery_task.delay(**req.params)

        # Store in database
        query = """
            INSERT INTO scheduled_tasks (task_id, task_type, task_name, priority, is_active)
            VALUES ($1, $2, $3, $4, $5)
        """
        await execute_update(
            db_pool,
            query,
            async_result.id,
            req.task_type,
            req.task_type.replace("_", " ").title(),
            req.priority,
            True,
        )

        # Emit event
        event = Event(
            event_type=EventType.TASK_STARTED,
            data={
                "task_id": async_result.id,
                "task_type": req.task_type,
                "params": req.params,
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Task enqueued: {async_result.id} ({req.task_type})")

        return {
            "task_id": async_result.id,
            "task_type": req.task_type,
            "status": "QUEUED",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status"""
    try:
        # Get from Celery
        async_result = celery_app.AsyncResult(task_id)

        return {
            "task_id": task_id,
            "status": async_result.status,
            "result": async_result.result if async_result.ready() else None,
        }

    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks")
async def list_tasks(status: Optional[str] = None, limit: int = 50):
    """List scheduled tasks"""
    try:
        if status:
            query = """
                SELECT task_id, task_type, task_name, is_active, created_at, updated_at
                FROM scheduled_tasks
                WHERE is_active = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            active = status.upper() == "ACTIVE"
            rows = await execute_query(db_pool, query, active, limit)
        else:
            query = """
                SELECT task_id, task_type, task_name, is_active, created_at, updated_at
                FROM scheduled_tasks
                ORDER BY created_at DESC
                LIMIT $1
            """
            rows = await execute_query(db_pool, query, limit)

        return rows

    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """Get task result"""
    try:
        async_result = celery_app.AsyncResult(task_id)

        if not async_result.ready():
            raise HTTPException(status_code=202, detail="Task still processing")

        if async_result.failed():
            raise HTTPException(status_code=500, detail=f"Task failed: {async_result.info}")

        return {
            "task_id": task_id,
            "status": "COMPLETED",
            "result": async_result.result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task result: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a task"""
    try:
        celery_app.control.revoke(task_id, terminate=True)

        # Update database
        query = "UPDATE scheduled_tasks SET is_active = FALSE WHERE task_id = $1"
        await execute_update(db_pool, query, task_id)

        logger.info(f"❌ Task cancelled: {task_id}")

        return {"task_id": task_id, "status": "CANCELLED"}

    except Exception as e:
        logger.error(f"Failed to cancel task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/workers")
async def get_workers():
    """Get active Celery workers"""
    try:
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()

        return {
            "active_workers": len(active_workers or {}) if active_workers else 0,
            "workers": active_workers or {},
        }

    except Exception as e:
        logger.error(f"Failed to get workers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return {"error": exc.detail, "code": str(exc.status_code), "service": SERVICE_NAME}


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return {"error": "Internal server error", "code": "500", "service": SERVICE_NAME}


if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )
