"""
Execution Service
Manages order placement, tracking, and execution
Integrates with broker APIs and coordinates with Risk Management
"""

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, Request
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

SERVICE_NAME = os.getenv("SERVICE_NAME", "execution")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8003))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost/robo_trader")
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")
BROKER_API_KEY = os.getenv("BROKER_API_KEY", "")
RISK_SERVICE_URL = os.getenv("RISK_SERVICE_URL", "http://localhost:8002")

# ============================================================================
# MODELS
# ============================================================================


class OrderRequest(BaseModel):
    """Order placement request"""
    symbol: str
    quantity: int
    price: float
    order_type: str  # BUY or SELL


class Order(BaseModel):
    """Order object"""
    order_id: str
    symbol: str
    quantity: int
    price: float
    status: str
    order_type: str
    created_at: datetime
    updated_at: datetime


class OrderExecution(BaseModel):
    """Order execution"""
    order_id: str
    symbol: str
    filled_quantity: int
    filled_price: float
    executed_at: datetime


# ============================================================================
# BROKER CLIENT
# ============================================================================


class BrokerClient:
    """Client for broker API integration"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.example-broker.com"

    async def place_order(self, order_request: OrderRequest) -> dict:
        """Place order with broker"""
        try:
            # Mock broker API call
            broker_order_id = f"BO-{uuid4().hex[:8]}"
            logger.info(f"📤 Order placed with broker: {broker_order_id}")

            return {
                "order_id": broker_order_id,
                "symbol": order_request.symbol,
                "quantity": order_request.quantity,
                "price": order_request.price,
                "status": "PLACED",
            }
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            raise

    async def cancel_order(self, broker_order_id: str) -> bool:
        """Cancel order with broker"""
        try:
            logger.info(f"❌ Order cancelled with broker: {broker_order_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cancel order: {e}")
            raise

    async def get_order_status(self, broker_order_id: str) -> dict:
        """Get order status from broker"""
        try:
            # Mock status check
            return {
                "broker_order_id": broker_order_id,
                "status": "FILLED",
                "filled_quantity": 100,
                "filled_price": 450.50,
            }
        except Exception as e:
            logger.error(f"Failed to get order status: {e}")
            raise


# ============================================================================
# GLOBAL STATE
# ============================================================================

event_bus: EventBus = None
db_pool = None
broker_client: BrokerClient = None


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus, db_pool, broker_client

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
        db_pool = await get_db_pool(DATABASE_URL)
        db_healthy = await check_db_health(db_pool)
        if not db_healthy:
            raise Exception("Database health check failed")

        event_bus = EventBus(RABBITMQ_URL)
        await event_bus.connect()

        broker_client = BrokerClient(BROKER_API_KEY)

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
    description="Order placement and execution tracking",
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
        "broker": "connected" if broker_client else "disconnected",
    }
    return HealthCheck(status="healthy", service=SERVICE_NAME, checks=checks)


@app.post("/orders", response_model=Order)
async def place_order(request: OrderRequest):
    """Place a new order"""
    try:
        correlation_id = str(uuid4())

        client = await get_http_client()

        risk_resp = await client.post(
            f"{RISK_SERVICE_URL}/assess",
            json={
                "symbol": request.symbol,
                "quantity": request.quantity,
                "price": request.price,
            },
            headers={"X-Correlation-ID": correlation_id},
            timeout=10.0,
        )

        if risk_resp.status_code != 200:
            risk_data = risk_resp.json()
            error_msg = risk_data.get("reason", "Risk assessment failed")

            event = Event(
                event_type=EventType.EXECUTION_ORDER_REJECTED,
                data={
                    "symbol": request.symbol,
                    "quantity": request.quantity,
                    "reason": error_msg,
                },
                source=SERVICE_NAME,
                correlation_id=correlation_id,
            )
            await event_bus.publish(event)

            raise HTTPException(status_code=400, detail=error_msg)

        risk_data = risk_resp.json()
        if not risk_data.get("approved", False):
            error_msg = risk_data.get("reason", "Risk limit exceeded")

            event = Event(
                event_type=EventType.EXECUTION_ORDER_REJECTED,
                data={
                    "symbol": request.symbol,
                    "quantity": request.quantity,
                    "reason": error_msg,
                },
                source=SERVICE_NAME,
                correlation_id=correlation_id,
            )
            await event_bus.publish(event)

            raise HTTPException(status_code=400, detail=error_msg)

        # 2. Place order with broker
        broker_response = await broker_client.place_order(request)

        # 3. Store in database
        order_id = f"ORD-{uuid4().hex[:8]}"
        query = """
            INSERT INTO orders (
                order_id, symbol, quantity, price, status, order_type
            )
            VALUES ($1, $2, $3, $4, $5, $6)
            RETURNING order_id, symbol, quantity, price, status, order_type, created_at, updated_at
        """
        result = await execute_update(
            db_pool,
            query,
            order_id,
            request.symbol.upper(),
            request.quantity,
            request.price,
            "PLACED",
            request.order_type.upper(),
        )

        # 4. Emit event
        event = Event(
            event_type=EventType.EXECUTION_ORDER_PLACED,
            data={
                "order_id": order_id,
                "symbol": request.symbol,
                "quantity": request.quantity,
                "price": request.price,
                "broker_order_id": broker_response.get("order_id"),
            },
            source=SERVICE_NAME,
            correlation_id=correlation_id,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Order placed: {order_id} ({request.order_type} {request.quantity} {request.symbol})")

        return Order(
            order_id=order_id,
            symbol=request.symbol,
            quantity=request.quantity,
            price=request.price,
            status="PLACED",
            order_type=request.order_type,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to place order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str):
    """Get order status"""
    try:
        query = """
            SELECT order_id, symbol, quantity, price, status, order_type, created_at, updated_at
            FROM orders
            WHERE order_id = $1
        """
        rows = await execute_query(db_pool, query, order_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        row = rows[0]
        return Order(
            order_id=row["order_id"],
            symbol=row["symbol"],
            quantity=row["quantity"],
            price=row["price"],
            status=row["status"],
            order_type=row["order_type"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/orders", response_model=List[Order])
async def list_orders(status: Optional[str] = None, limit: int = 100):
    """List orders with optional status filter"""
    try:
        if status:
            query = "SELECT * FROM orders WHERE status = $1 ORDER BY created_at DESC LIMIT $2"
            rows = await execute_query(db_pool, query, status.upper(), limit)
        else:
            query = "SELECT * FROM orders ORDER BY created_at DESC LIMIT $1"
            rows = await execute_query(db_pool, query, limit)

        orders = [
            Order(
                order_id=row["order_id"],
                symbol=row["symbol"],
                quantity=row["quantity"],
                price=row["price"],
                status=row["status"],
                order_type=row["order_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]

        return orders

    except Exception as e:
        logger.error(f"Failed to list orders: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an order"""
    try:
        # Get order first
        query = "SELECT broker_order_id, status FROM orders WHERE order_id = $1"
        rows = await execute_query(db_pool, query, order_id)

        if not rows:
            raise HTTPException(status_code=404, detail=f"Order {order_id} not found")

        row = rows[0]
        if row["status"] not in ["PLACED", "PARTIALLY_FILLED"]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel order with status {row['status']}")

        # Cancel with broker
        if row["broker_order_id"]:
            await broker_client.cancel_order(row["broker_order_id"])

        # Update database
        update_query = "UPDATE orders SET status = $1, updated_at = NOW() WHERE order_id = $2"
        await execute_update(db_pool, update_query, "CANCELLED", order_id)

        # Emit event
        event = Event(
            event_type=EventType.EXECUTION_ORDER_CANCELLED,
            data={"order_id": order_id},
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"❌ Order cancelled: {order_id}")

        return {"status": "cancelled", "order_id": order_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/orders/{order_id}/fill")
async def fill_order(order_id: str, filled_quantity: int, filled_price: float):
    """Record order fill/execution"""
    try:
        # Update order status
        query = """
            UPDATE orders
            SET status = CASE WHEN $2 = quantity THEN 'FILLED' ELSE 'PARTIALLY_FILLED' END,
                updated_at = NOW()
            WHERE order_id = $1
            RETURNING symbol, quantity, order_type
        """
        result = await execute_update(db_pool, query, order_id, filled_quantity)

        # Record execution
        exec_query = """
            INSERT INTO executions (order_id, symbol, quantity, filled_quantity, filled_price)
            VALUES ($1, $2, $3, $4, $5)
        """
        # Get symbol from result
        symbol_query = "SELECT symbol FROM orders WHERE order_id = $1"
        symbol_rows = await execute_query(db_pool, symbol_query, order_id)
        symbol = symbol_rows[0]["symbol"] if symbol_rows else "UNKNOWN"

        await execute_update(db_pool, exec_query, order_id, symbol, filled_quantity, filled_quantity, filled_price)

        # Emit event
        event = Event(
            event_type=EventType.EXECUTION_ORDER_FILLED,
            data={
                "order_id": order_id,
                "symbol": symbol,
                "filled_quantity": filled_quantity,
                "filled_price": filled_price,
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.info(f"✅ Order filled: {order_id} ({filled_quantity} @ {filled_price})")

        return {"status": "filled", "order_id": order_id, "filled_quantity": filled_quantity}

    except Exception as e:
        logger.error(f"Failed to fill order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/order-history")
async def get_order_history(symbol: Optional[str] = None, limit: int = 100):
    """Get order history"""
    try:
        if symbol:
            query = """
                SELECT * FROM order_history
                WHERE symbol = $1
                ORDER BY created_at DESC
                LIMIT $2
            """
            rows = await execute_query(db_pool, query, symbol.upper(), limit)
        else:
            query = "SELECT * FROM order_history ORDER BY created_at DESC LIMIT $1"
            rows = await execute_query(db_pool, query, limit)

        return rows

    except Exception as e:
        logger.error(f"Failed to get order history: {e}")
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
