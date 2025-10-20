"""
Risk Management Service
Manages risk assessments, stop-loss monitoring, and exposure limits
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.shared import EventBus, Event, EventType, get_http_client, close_http_client
from services.shared.database import (
    check_db_health,
    close_db_pool,
    execute_query,
    execute_update,
    get_db_pool,
)
from services.shared.models import HealthCheck

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "risk")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8002))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/robo_trader")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")
PORTFOLIO_SERVICE_URL = os.getenv("PORTFOLIO_SERVICE_URL", "http://localhost:8001")
MARKET_DATA_SERVICE_URL = os.getenv("MARKET_DATA_SERVICE_URL", "http://localhost:8004")

# ============================================================================
# MODELS
# ============================================================================


class RiskAssessment(BaseModel):
    symbol: str
    quantity: int
    price: float
    exposure_percentage: Optional[float] = None
    approved: bool = False
    reason: Optional[str] = None


class RiskLimit(BaseModel):
    symbol: str
    max_position_size: int
    max_loss_percentage: float
    stop_loss_percentage: float


class StopLossTrigger(BaseModel):
    symbol: str
    quantity: int
    stop_loss_price: float
    current_price: Optional[float] = None
    status: str = "ACTIVE"


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

        await get_http_client()

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
        await close_http_client()
        logger.info(f"✅ {SERVICE_NAME} service stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=f"{SERVICE_NAME} API",
    description="Risk management and stop-loss monitoring",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthCheck)
async def health_check():
    checks = {
        "database": "healthy" if db_pool and await check_db_health(db_pool) else "unhealthy",
        "event_bus": "healthy" if event_bus and await event_bus.health_check() else "unhealthy",
    }
    return HealthCheck(status="healthy", service=SERVICE_NAME, checks=checks)


@app.post("/assess", response_model=RiskAssessment)
async def assess_risk(assessment: RiskAssessment):
    """Assess risk for a potential trade"""
    try:
        client = await get_http_client()

        portfolio_resp = await client.get(
            f"{PORTFOLIO_SERVICE_URL}/portfolio/summary",
            timeout=10.0,
        )
        portfolio_data = portfolio_resp.json()

        # Simple exposure check: position_value / total_portfolio < 10%
        position_value = assessment.quantity * assessment.price
        total_portfolio = portfolio_data.get("total_value", 100000)
        exposure_percentage = (position_value / total_portfolio * 100) if total_portfolio > 0 else 0

        approved = exposure_percentage < 10  # Simplified rule
        reason = None if approved else f"Exposure {exposure_percentage:.1f}% exceeds 10% limit"

        # Store assessment
        query = """
            INSERT INTO risk_assessments (symbol, quantity, price, exposure_percentage, approved, reason)
            VALUES ($1, $2, $3, $4, $5, $6)
        """
        await execute_update(db_pool, query, assessment.symbol, assessment.quantity,
                           assessment.price, exposure_percentage, approved, reason)

        logger.info(f"📊 Risk assessment for {assessment.symbol}: {'Approved' if approved else 'Rejected'}")

        return RiskAssessment(
            symbol=assessment.symbol,
            quantity=assessment.quantity,
            price=assessment.price,
            exposure_percentage=exposure_percentage,
            approved=approved,
            reason=reason,
        )

    except Exception as e:
        logger.error(f"Failed to assess risk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/limits", response_model=List[RiskLimit])
async def get_risk_limits():
    """Get all risk limits"""
    try:
        query = "SELECT symbol, max_position_size, max_loss_percentage, stop_loss_percentage FROM risk_limits"
        rows = await execute_query(db_pool, query)

        limits = [
            RiskLimit(
                symbol=row["symbol"],
                max_position_size=row["max_position_size"],
                max_loss_percentage=row["max_loss_percentage"],
                stop_loss_percentage=row["stop_loss_percentage"],
            )
            for row in rows
        ]

        return limits

    except Exception as e:
        logger.error(f"Failed to get risk limits: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/stop-loss", response_model=StopLossTrigger)
async def set_stop_loss(trigger: StopLossTrigger):
    """Set a stop-loss trigger"""
    try:
        query = """
            INSERT INTO stop_loss_triggers (symbol, stop_loss_price, quantity, status)
            VALUES ($1, $2, $3, $4)
        """
        await execute_update(db_pool, query, trigger.symbol, trigger.stop_loss_price,
                           trigger.quantity, "ACTIVE")

        logger.info(f"🛑 Stop-loss set for {trigger.symbol} at {trigger.stop_loss_price}")

        return trigger

    except Exception as e:
        logger.error(f"Failed to set stop-loss: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stop-losses", response_model=List[StopLossTrigger])
async def get_active_stop_losses():
    """Get all active stop-loss triggers"""
    try:
        query = """
            SELECT symbol, quantity, stop_loss_price, current_price, status
            FROM stop_loss_triggers
            WHERE status = 'ACTIVE'
        """
        rows = await execute_query(db_pool, query)

        triggers = [
            StopLossTrigger(
                symbol=row["symbol"],
                quantity=row["quantity"],
                stop_loss_price=row["stop_loss_price"],
                current_price=row["current_price"],
                status=row["status"],
            )
            for row in rows
        ]

        return triggers

    except Exception as e:
        logger.error(f"Failed to get stop-losses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/monitor-stop-losses")
async def monitor_stop_losses():
    """Manually trigger stop-loss monitoring"""
    try:
        query = "SELECT symbol, quantity, stop_loss_price FROM stop_loss_triggers WHERE status = 'ACTIVE'"
        triggers = await execute_query(db_pool, query)

        triggered_count = 0
        client = await get_http_client()

        if triggers:
            symbols = [t["symbol"] for t in triggers]

            for trigger in triggers:
                try:
                    quote_resp = await client.get(
                        f"{MARKET_DATA_SERVICE_URL}/quote/{trigger['symbol']}",
                        timeout=10.0,
                    )
                    quote = quote_resp.json()
                    current_price = quote.get("ltp", 0)

                    if current_price <= trigger["stop_loss_price"]:
                        triggered_count += 1

                        event = Event(
                            event_type=EventType.RISK_STOP_LOSS_TRIGGER,
                            data={
                                "symbol": trigger["symbol"],
                                "stop_loss_price": trigger["stop_loss_price"],
                                "current_price": current_price,
                                "quantity": trigger["quantity"],
                            },
                            source=SERVICE_NAME,
                        )
                        await event_bus.publish(event)

                        update_query = "UPDATE stop_loss_triggers SET status = 'TRIGGERED' WHERE symbol = $1"
                        await execute_update(db_pool, update_query, trigger["symbol"])

                        logger.warning(f"⚠️  Stop-loss triggered for {trigger['symbol']} at {current_price}")

                except asyncio.TimeoutError:
                    logger.error(f"Timeout checking stop-loss for {trigger['symbol']}")
                except Exception as e:
                    logger.error(f"Error checking stop-loss for {trigger['symbol']}: {e}")

        return {"triggered_count": triggered_count, "total_checked": len(triggers)}

    except Exception as e:
        logger.error(f"Failed to monitor stop-losses: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
