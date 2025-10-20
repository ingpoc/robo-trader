"""
Market Data Service
Handles real-time market data, quotes, and ticker subscriptions
Emits market events to RabbitMQ for other services to consume
"""

import logging
import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from services.shared import EventBus, Event, EventType
from services.shared.models import HealthCheck, ServiceError

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "market-data")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8004))
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")
BROKER_API_KEY = os.getenv("BROKER_API_KEY", "")

# ============================================================================
# MODELS
# ============================================================================


class Quote(BaseModel):
    """Market quote"""

    symbol: str
    ltp: float  # Last Traded Price
    bid: float
    ask: float
    volume: int
    change: float
    change_percentage: float
    high_52w: float
    low_52w: float
    market_cap: int


class TickerSubscription(BaseModel):
    """Ticker subscription"""

    symbol: str
    is_subscribed: bool


# ============================================================================
# GLOBAL STATE
# ============================================================================

event_bus: EventBus = None
broker_client: "BrokerClient" = None


# ============================================================================
# BROKER CLIENT
# ============================================================================


class BrokerClient:
    """Client for interacting with broker APIs"""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.example-broker.com"  # Replace with actual broker

    async def get_quote(self, symbol: str) -> dict:
        """Get real-time quote for symbol"""
        try:
            # In production, this would call the actual broker API
            # For now, return mock data
            return {
                "symbol": symbol,
                "ltp": 450.50,
                "bid": 450.45,
                "ask": 450.55,
                "volume": 10000,
                "change": 2.50,
                "change_percentage": 0.56,
                "high_52w": 500.00,
                "low_52w": 350.00,
                "market_cap": 5000000000000,
            }
        except Exception as e:
            logger.error(f"Failed to fetch quote for {symbol}: {e}")
            raise

    async def subscribe_ticker(self, symbol: str) -> bool:
        """Subscribe to ticker updates"""
        try:
            logger.info(f"Subscribed to ticker: {symbol}")
            return True
        except Exception as e:
            logger.error(f"Failed to subscribe to {symbol}: {e}")
            raise


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle management"""
    # Startup
    global event_bus, broker_client

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
        # Initialize broker client
        broker_client = BrokerClient(BROKER_API_KEY)

        # Initialize event bus
        event_bus = EventBus(RABBITMQ_URL)
        await event_bus.connect()

        logger.info(f"✅ {SERVICE_NAME} service started")

    except Exception as e:
        logger.error(f"❌ Failed to start {SERVICE_NAME}: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"🛑 Shutting down {SERVICE_NAME} service...")

    try:
        if event_bus:
            await event_bus.disconnect()

        logger.info(f"✅ {SERVICE_NAME} service stopped")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=f"{SERVICE_NAME} API",
    description="Real-time market data and ticker subscriptions",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    checks = {}

    # Check event bus
    if event_bus:
        checks["event_bus"] = "healthy" if await event_bus.health_check() else "unhealthy"
    else:
        checks["event_bus"] = "not initialized"

    return HealthCheck(
        status="healthy",
        service=SERVICE_NAME,
        checks=checks,
    )


@app.get("/quote/{symbol}", response_model=Quote)
async def get_quote(symbol: str):
    """Get real-time quote for a symbol"""
    try:
        if not broker_client:
            raise HTTPException(status_code=503, detail="Service not ready")

        quote_data = await broker_client.get_quote(symbol)

        # Emit price update event
        event = Event(
            event_type=EventType.MARKET_PRICE_UPDATE,
            data={
                "symbol": symbol,
                "ltp": quote_data["ltp"],
                "bid": quote_data["bid"],
                "ask": quote_data["ask"],
                "volume": quote_data["volume"],
                "change": quote_data["change"],
                "change_percentage": quote_data["change_percentage"],
            },
            source=SERVICE_NAME,
        )
        await event_bus.publish(event)

        logger.debug(f"📊 Fetched quote for {symbol}")

        return Quote(**quote_data)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/market-status")
async def get_market_status():
    """Get market open/close status"""
    return {
        "market_open": True,
        "trading_session": "regular",
        "market_time": "14:30:00",
    }


@app.post("/ticker/subscribe")
async def subscribe_ticker(subscription: TickerSubscription):
    """Subscribe to real-time ticker updates"""
    try:
        result = await broker_client.subscribe_ticker(subscription.symbol)

        if result:
            logger.info(f"✅ Subscribed to {subscription.symbol}")
            return {"status": "subscribed", "symbol": subscription.symbol}
        else:
            raise HTTPException(status_code=400, detail="Failed to subscribe")

    except Exception as e:
        logger.error(f"Failed to subscribe to {subscription.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/ticker/unsubscribe")
async def unsubscribe_ticker(symbol: str):
    """Unsubscribe from ticker updates"""
    logger.info(f"Unsubscribed from {symbol}")
    return {"status": "unsubscribed", "symbol": symbol}


@app.get("/quotes")
async def get_quotes(symbols: str):
    """Get quotes for multiple symbols (comma-separated)"""
    try:
        symbol_list = [s.strip() for s in symbols.split(",")]
        quotes = []

        for symbol in symbol_list:
            quote_data = await broker_client.get_quote(symbol)
            quotes.append(Quote(**quote_data))

        return {"quotes": quotes, "count": len(quotes)}

    except Exception as e:
        logger.error(f"Failed to fetch quotes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    return {
        "error": exc.detail,
        "code": str(exc.status_code),
        "service": SERVICE_NAME,
    }


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {exc}")
    return {
        "error": "Internal server error",
        "code": "500",
        "service": SERVICE_NAME,
        "details": str(exc) if os.getenv("LOG_LEVEL") == "DEBUG" else None,
    }


if __name__ == "__main__":
    import uvicorn

    # Setup logging
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
