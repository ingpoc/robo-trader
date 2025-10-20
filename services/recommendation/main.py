"""
Recommendation Service
Generates AI recommendations and manages approval workflows
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

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

SERVICE_NAME = os.getenv("SERVICE_NAME", "recommendation")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8006))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/robo_trader")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")

# ============================================================================
# MODELS
# ============================================================================


class RecommendationRequest(BaseModel):
    """Recommendation creation request"""
    symbol: str
    action: str  # BUY, SELL, HOLD
    reason: str
    target_price: Optional[float] = None


class Recommendation(BaseModel):
    """Recommendation"""
    recommendation_id: str
    symbol: str
    action: str
    reason: str
    target_price: Optional[float] = None
    status: str
    created_at: datetime


class ApprovalRequest(BaseModel):
    """Approval request"""
    recommendation_id: str
    approved: bool
    comments: Optional[str] = None


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
    description="AI recommendations and approval workflows",
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
    }
    return HealthCheck(status="healthy", service=SERVICE_NAME, checks=checks)


@app.get("/recommendations", response_model=List[Recommendation])
async def get_recommendations(status: Optional[str] = None, limit: int = 50):
    """Get recommendations"""
    try:
        if status:
            query = """
                SELECT recommendation_id, symbol, action, reason, target_price, status, created_at
                FROM recommendations
                WHERE status = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            rows = await execute_query(db_pool, query, status.upper(), limit)
        else:
            query = """
                SELECT recommendation_id, symbol, action, reason, target_price, status, created_at
                FROM recommendations
                ORDER BY created_at DESC
                LIMIT $1
            """
            rows = await execute_query(db_pool, query, limit)

        recommendations = [
            Recommendation(
                recommendation_id=row["recommendation_id"],
                symbol=row["symbol"],
                action=row["action"],
                reason=row["reason"],
                target_price=row["target_price"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ]

        return recommendations

    except Exception as e:
        logger.error(f"Failed to get recommendations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommendations", response_model=Recommendation)
async def create_recommendation(req: RecommendationRequest):
    """Create a new recommendation"""
    try:
        recommendation_id = f"REC-{uuid4().hex[:8]}"

        query = """
            INSERT INTO recommendations (
                recommendation_id, symbol, action, reason, target_price, status
            )
            VALUES ($1, $2, $3, $4, $5, 'PENDING')
            RETURNING recommendation_id, symbol, action, reason, target_price, status, created_at
        """
        result = await execute_update(
            db_pool,
            query,
            recommendation_id,
            req.symbol.upper(),
            req.action.upper(),
            req.reason,
            req.target_price,
        )

        logger.info(f"✅ Recommendation created: {recommendation_id} ({req.action} {req.symbol})")

        return Recommendation(
            recommendation_id=recommendation_id,
            symbol=req.symbol,
            action=req.action,
            reason=req.reason,
            target_price=req.target_price,
            status="PENDING",
            created_at=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Failed to create recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/{recommendation_id}", response_model=Recommendation)
async def get_recommendation(recommendation_id: str):
    """Get specific recommendation"""
    try:
        query = """
            SELECT recommendation_id, symbol, action, reason, target_price, status, created_at
            FROM recommendations
            WHERE recommendation_id = $1
        """
        rows = await execute_query(db_pool, query, recommendation_id)

        if not rows:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        row = rows[0]
        return Recommendation(
            recommendation_id=row["recommendation_id"],
            symbol=row["symbol"],
            action=row["action"],
            reason=row["reason"],
            target_price=row["target_price"],
            status=row["status"],
            created_at=row["created_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommendations/{recommendation_id}/approve")
async def approve_recommendation(recommendation_id: str, comments: Optional[str] = None):
    """Approve a recommendation"""
    try:
        # Update status
        query = """
            UPDATE recommendations
            SET status = 'APPROVED', updated_at = NOW()
            WHERE recommendation_id = $1
            RETURNING symbol, action
        """
        result = await execute_update(db_pool, query, recommendation_id)

        if not result:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        # Record approval
        approval_query = """
            INSERT INTO approval_queue (recommendation_id, symbol, action, approved_at)
            SELECT recommendation_id, symbol, action, NOW()
            FROM recommendations
            WHERE recommendation_id = $1
        """
        await execute_update(db_pool, approval_query, recommendation_id)

        # Get recommendation details
        detail_query = "SELECT symbol, action FROM recommendations WHERE recommendation_id = $1"
        detail_rows = await execute_query(db_pool, detail_query, recommendation_id)

        if detail_rows:
            detail = detail_rows[0]
            # Emit event
            event = Event(
                event_type=EventType.AI_RECOMMENDATION,
                data={
                    "recommendation_id": recommendation_id,
                    "symbol": detail["symbol"],
                    "action": detail["action"],
                    "approved": True,
                },
                source=SERVICE_NAME,
            )
            await event_bus.publish(event)

        logger.info(f"✅ Recommendation approved: {recommendation_id}")

        return {"status": "approved", "recommendation_id": recommendation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/recommendations/{recommendation_id}/reject")
async def reject_recommendation(recommendation_id: str, reason: Optional[str] = None):
    """Reject a recommendation"""
    try:
        query = """
            UPDATE recommendations
            SET status = 'REJECTED', updated_at = NOW()
            WHERE recommendation_id = $1
            RETURNING symbol, action
        """
        result = await execute_update(db_pool, query, recommendation_id)

        if not result:
            raise HTTPException(status_code=404, detail="Recommendation not found")

        logger.info(f"❌ Recommendation rejected: {recommendation_id}")

        return {"status": "rejected", "recommendation_id": recommendation_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reject recommendation: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/approval-queue", response_model=List[dict])
async def get_approval_queue():
    """Get pending approval queue"""
    try:
        query = """
            SELECT recommendation_id, symbol, action, submitted_at, approved_at
            FROM approval_queue
            WHERE approved_at IS NULL
            ORDER BY submitted_at ASC
        """
        rows = await execute_query(db_pool, query)
        return rows

    except Exception as e:
        logger.error(f"Failed to get approval queue: {e}")
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
