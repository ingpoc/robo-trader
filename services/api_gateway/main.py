"""
API Gateway Service
Central request router and aggregator for all microservices
Handles routing, WebSocket aggregation, and request transformation
"""

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

import httpx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from services.shared import EventBus, EventType, get_http_client, close_http_client
from services.shared.models import HealthCheck
from aggregators import (
    DashboardAggregator,
    AnalyticsAggregator,
    AgentsAggregator,
    MonitoringAggregator,
    AlertsAggregator,
    RecommendationsAggregator,
    EarningsAggregator,
    ConfigAggregator,
    AgentFeaturesAggregator,
    LogsAggregator,
    ActionAggregator,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "api-gateway")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8000))
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost//")

# Service registry
SERVICES = {
    "market-data": "http://market-data.orb.local:8004",
    "portfolio": "http://portfolio.orb.local:8001",
    "risk": "http://risk.orb.local:8002",
    "execution": "http://execution.orb.local:8003",
    "analytics": "http://analytics.orb.local:8005",
    "recommendation": "http://recommendation.orb.local:8006",
    "task-scheduler": "http://scheduler.orb.local:8007",
}

# ============================================================================
# GLOBAL STATE
# ============================================================================

event_bus: EventBus = None
connected_clients = set()


# ============================================================================
# FASTAPI APP
# ============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    global event_bus

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
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
        await close_http_client()
        logger.info(f"✅ {SERVICE_NAME} service stopped")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title="Robo Trader API Gateway",
    description="Central entry point for all microservices",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# CORS MIDDLEWARE
# ============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins in development
    allow_credentials=True,
    allow_methods=["*"],  # Allow all methods
    allow_headers=["*"],  # Allow all headers
)


# ============================================================================
# MIDDLEWARE FOR REQUEST LOGGING
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming HTTP requests"""
    import time
    import sys
    start_time = time.time()

    # Log incoming request (use print to ensure it shows in terminal)
    print(f"📥 {request.method} {request.url.path}", file=sys.stdout, flush=True)

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Log response with status code and duration
        status_emoji = "✅" if 200 <= response.status_code < 300 else "⚠️" if 400 <= response.status_code < 500 else "❌"
        print(f"📤 {status_emoji} {response.status_code} {request.method} {request.url.path} ({process_time:.2f}s)", file=sys.stdout, flush=True)

        return response
    except Exception as e:
        process_time = time.time() - start_time
        print(f"❌ ERROR {request.method} {request.url.path} ({process_time:.2f}s): {str(e)}", file=sys.stdout, flush=True)
        raise


# ============================================================================
# ENDPOINTS
# ============================================================================


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    checks = {"event_bus": "healthy" if event_bus and await event_bus.health_check() else "unhealthy"}

    return HealthCheck(status="healthy", service=SERVICE_NAME, checks=checks)


# ============================================================================
# AGGREGATION ENDPOINTS - Must come BEFORE generic proxy route
# ============================================================================


@app.get("/api/dashboard")
async def get_dashboard():
    """Get aggregated dashboard data from multiple services"""
    client = await get_http_client()
    aggregator = DashboardAggregator(client, SERVICES)
    return await aggregator.get_dashboard()


@app.get("/api/analytics/performance/{period}")
async def get_performance_analytics(period: str = "30d"):
    """Get aggregated performance analytics"""
    client = await get_http_client()
    aggregator = AnalyticsAggregator(client, SERVICES)
    return await aggregator.get_performance_analytics(period)


@app.get("/api/agents/status")
async def get_agents_status():
    """Get aggregated agent status"""
    client = await get_http_client()
    aggregator = AgentsAggregator(client, SERVICES)
    return await aggregator.get_agents_status()


@app.get("/api/monitoring/status")
async def get_monitoring_status():
    """Get aggregated system monitoring status"""
    client = await get_http_client()
    aggregator = MonitoringAggregator(client, SERVICES)
    return await aggregator.get_system_status()


@app.get("/api/alerts/active")
async def get_active_alerts():
    """Get active alerts"""
    client = await get_http_client()
    aggregator = AlertsAggregator(client, SERVICES)
    return await aggregator.get_active_alerts()


@app.get("/api/ai/recommendations")
async def get_ai_recommendations():
    """Get AI recommendations"""
    client = await get_http_client()
    aggregator = RecommendationsAggregator(client, SERVICES)
    return await aggregator.get_recommendations()


@app.get("/api/earnings/upcoming")
async def get_upcoming_earnings(days_ahead: int = 60):
    """Get upcoming earnings"""
    client = await get_http_client()
    aggregator = EarningsAggregator(client, SERVICES)
    return await aggregator.get_upcoming_earnings(days_ahead)


@app.get("/api/config")
async def get_config():
    """Get system configuration"""
    client = await get_http_client()
    aggregator = ConfigAggregator(client, SERVICES)
    return await aggregator.get_config()


@app.post("/api/config")
async def update_config(config_data: Dict[str, Any]):
    """Update system configuration"""
    client = await get_http_client()
    aggregator = ConfigAggregator(client, SERVICES)
    return await aggregator.update_config(config_data)


@app.get("/api/agents/features")
async def get_agent_features():
    """Get agent features and capabilities"""
    client = await get_http_client()
    aggregator = AgentFeaturesAggregator(client, SERVICES)
    return await aggregator.get_agent_features()


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get application logs"""
    client = await get_http_client()
    aggregator = LogsAggregator(client, SERVICES)
    return await aggregator.get_logs(limit)


@app.post("/api/portfolio-scan")
async def portfolio_scan():
    """Trigger portfolio scan"""
    client = await get_http_client()
    aggregator = ActionAggregator(client, SERVICES)
    return await aggregator.portfolio_scan()


@app.post("/api/market-screening")
async def market_screening():
    """Trigger market screening"""
    client = await get_http_client()
    aggregator = ActionAggregator(client, SERVICES)
    return await aggregator.market_screening()


@app.post("/api/manual-trade")
async def manual_trade(trade_data: Dict[str, Any]):
    """Execute a manual trade"""
    client = await get_http_client()
    aggregator = ActionAggregator(client, SERVICES)
    return await aggregator.manual_trade(trade_data)


# ============================================================================
# GENERIC PROXY ROUTE - Must come AFTER all specific aggregation endpoints
# ============================================================================


@app.api_route("/api/{service}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_request(service: str, path: str, request: Request):
    """Proxy requests to microservices"""
    try:
        if service not in SERVICES:
            raise HTTPException(status_code=404, detail=f"Service '{service}' not found")

        service_url = SERVICES[service]
        url = f"{service_url}/{path}"

        client = await get_http_client()

        try:
            if "application/json" in request.headers.get("content-type", ""):
                content = await request.body()
            else:
                content = await request.body()

            response = await client.request(
                method=request.method,
                url=url,
                content=content,
                headers=dict(request.headers),
            )

            try:
                content_data = response.json()
            except json.JSONDecodeError:
                content_data = {"raw_response": response.text[:200]}

            return JSONResponse(
                content=content_data,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        except httpx.TimeoutException:
            logger.error(f"Timeout proxying request to {service}")
            raise HTTPException(status_code=504, detail=f"Service '{service}' timeout")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to proxy request to {service}: {e}")
        raise HTTPException(status_code=502, detail=f"Service '{service}' unavailable")


@app.get("/api/services")
async def list_services():
    """List all available services"""
    return {
        "services": list(SERVICES.keys()),
        "total": len(SERVICES),
    }


@app.get("/api/logs")
async def get_logs(limit: int = 100):
    """Get application logs"""
    import aiofiles
    from datetime import datetime

    try:
        logs = []
        log_file = "/app/logs/frontend.log"

        # Try to read frontend logs if available
        try:
            async with aiofiles.open(log_file, mode='r') as f:
                content = await f.read()
                lines = content.strip().split('\n')[-limit:]
                logs = [
                    {
                        "timestamp": datetime.utcnow().isoformat(),
                        "level": "INFO",
                        "message": line.strip(),
                        "source": "frontend"
                    }
                    for line in lines if line.strip()
                ]
        except FileNotFoundError:
            logs = [
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "level": "INFO",
                    "message": "Frontend logs not available yet",
                    "source": "system"
                }
            ]

        return {"logs": logs, "total": len(logs)}

    except Exception as e:
        logger.error(f"Failed to get logs: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve logs")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time event updates"""
    await websocket.accept()
    connected_clients.add(websocket)

    subscription_tasks = []

    try:
        event_types = [
            EventType.MARKET_PRICE_UPDATE,
            EventType.PORTFOLIO_POSITION_CHANGE,
            EventType.PORTFOLIO_PNL_UPDATE,
            EventType.PORTFOLIO_CASH_CHANGE,
            EventType.EXECUTION_ORDER_FILLED,
            EventType.EXECUTION_ORDER_PLACED,
            EventType.EXECUTION_ORDER_REJECTED,
            EventType.RISK_STOP_LOSS_TRIGGER,
            EventType.RISK_BREACH,
            EventType.AI_ANALYSIS_COMPLETE,
            EventType.AI_RECOMMENDATION,
            EventType.ALERT_TRIGGERED,
            EventType.TASK_COMPLETED,
            EventType.TASK_FAILED,
        ]

        async def broadcast_event(event):
            """Broadcast event to connected WebSocket client"""
            message = {
                "type": "event",
                "event_id": event.id,
                "event_type": event.type.value,
                "data": event.data,
                "timestamp": event.timestamp,
                "source": event.source,
                "correlation_id": event.correlation_id,
            }

            try:
                await websocket.send_json(message)
                logger.debug(f"📤 Sent event to WebSocket: {event.type.value}")
            except Exception as e:
                logger.error(f"Failed to send WebSocket message: {e}")

        logger.info(f"📥 WebSocket client connected, subscribing to {len(event_types)} event types")

        subscription_tasks = await event_bus.subscribe_multi(event_types, broadcast_event)

        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
                logger.debug(f"Received WebSocket message: {data}")

                try:
                    message = json.loads(data)
                    if message.get("type") == "ping":
                        await websocket.send_json({"type": "pong", "timestamp": str(
                            __import__("datetime").datetime.utcnow().isoformat()
                        )})
                except json.JSONDecodeError:
                    logger.warning("Invalid JSON in WebSocket message")
            except asyncio.TimeoutError:
                pass

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except asyncio.CancelledError:
        logger.debug("WebSocket subscription cancelled")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        connected_clients.discard(websocket)

        for task in subscription_tasks:
            try:
                task.cancel()
            except Exception as e:
                logger.debug(f"Error cancelling subscription task: {e}")


# ============================================================================
# PAPER TRADING ENDPOINTS
# ============================================================================

import sqlite3
from datetime import datetime

# Paper trading database path
PAPER_TRADING_DB = "/tmp/robo_trader_paper_trading.db"

def init_paper_trading_db():
    """Initialize paper trading database if needed"""
    try:
        conn = sqlite3.connect(PAPER_TRADING_DB)
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_trading_accounts (
                account_id TEXT PRIMARY KEY,
                account_name TEXT NOT NULL,
                initial_balance REAL NOT NULL,
                current_balance REAL NOT NULL,
                buying_power REAL NOT NULL,
                strategy_type TEXT NOT NULL,
                risk_level TEXT NOT NULL,
                max_position_size REAL NOT NULL,
                max_portfolio_risk REAL NOT NULL,
                is_active INTEGER DEFAULT 1,
                month_start_date TEXT NOT NULL,
                monthly_pnl REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS paper_trades (
                trade_id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                entry_timestamp TEXT NOT NULL,
                strategy_rationale TEXT NOT NULL,
                exit_price REAL,
                exit_timestamp TEXT,
                realized_pnl REAL,
                unrealized_pnl REAL,
                status TEXT NOT NULL DEFAULT 'open',
                stop_loss REAL,
                target_price REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Check if default account exists
        cursor.execute("SELECT account_id FROM paper_trading_accounts WHERE account_id = ?", ("paper_swing_main",))
        if not cursor.fetchone():
            # Create default account
            now = datetime.utcnow().isoformat()
            today = datetime.utcnow().strftime("%Y-%m-%d")

            cursor.execute("""
                INSERT INTO paper_trading_accounts (
                    account_id, account_name, initial_balance, current_balance, buying_power,
                    strategy_type, risk_level, max_position_size, max_portfolio_risk,
                    is_active, month_start_date, monthly_pnl, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "paper_swing_main",
                "Paper Trading - Swing",
                100000.0,
                100000.0,
                100000.0,
                "swing",
                "moderate",
                5.0,
                10.0,
                1,
                today,
                0.0,
                now,
                now
            ))

        conn.commit()
        conn.close()
        logger.info("✓ Paper trading database initialized")
    except Exception as e:
        logger.warning(f"Could not initialize paper trading database: {e}")


@app.get("/api/paper-trading/accounts/{account_id}/overview")
async def get_paper_trading_overview(account_id: str):
    """Get paper trading account overview"""
    try:
        init_paper_trading_db()
        conn = sqlite3.connect(PAPER_TRADING_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM paper_trading_accounts WHERE account_id = ?", (account_id,))
        row = cursor.fetchone()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

        account = dict(row)
        return {
            "account_id": account["account_id"],
            "account_type": "swing_trading",
            "strategy_type": account["strategy_type"],
            "balance": account["current_balance"],
            "buying_power": account["buying_power"],
            "deployed_capital": account["initial_balance"] - account["buying_power"],
            "total_pnl": account["monthly_pnl"],
            "total_pnl_pct": (account["monthly_pnl"] / account["initial_balance"] * 100) if account["initial_balance"] > 0 else 0,
            "monthly_pnl": account["monthly_pnl"],
            "monthly_pnl_pct": (account["monthly_pnl"] / account["initial_balance"] * 100) if account["initial_balance"] > 0 else 0,
            "open_positions_count": 0,
            "today_trades": 0,
            "win_rate": 0.0,
            "created_at": account["created_at"],
            "reset_date": account["month_start_date"],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get paper trading account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/paper-trading/accounts/{account_id}/positions")
async def get_paper_trading_positions(account_id: str):
    """Get paper trading open positions"""
    try:
        init_paper_trading_db()
        conn = sqlite3.connect(PAPER_TRADING_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM paper_trades
            WHERE account_id = ? AND status = 'open'
            ORDER BY entry_timestamp DESC
        """, (account_id,))
        rows = cursor.fetchall()
        conn.close()

        positions = []
        for row in rows:
            trade = dict(row)
            positions.append({
                "trade_id": trade["trade_id"],
                "symbol": trade["symbol"],
                "trade_type": trade["trade_type"],
                "quantity": trade["quantity"],
                "entry_price": trade["entry_price"],
                "current_price": trade["entry_price"],  # Use entry price as placeholder
                "current_value": trade["quantity"] * trade["entry_price"],
                "unrealized_pnl": trade["unrealized_pnl"] or 0.0,
                "unrealized_pnl_pct": 0.0,
                "stop_loss": trade["stop_loss"],
                "target_price": trade["target_price"],
                "entry_date": trade["entry_timestamp"],
                "days_held": 0,
                "strategy_rationale": trade["strategy_rationale"],
                "ai_suggested": False,
            })

        return positions
    except Exception as e:
        logger.error(f"Failed to get paper trading positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/paper-trading/accounts/{account_id}/trades")
async def get_paper_trading_trades(account_id: str):
    """Get paper trading closed trades"""
    try:
        init_paper_trading_db()
        conn = sqlite3.connect(PAPER_TRADING_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM paper_trades
            WHERE account_id = ? AND status IN ('closed', 'stopped_out')
            ORDER BY exit_timestamp DESC
            LIMIT 50
        """, (account_id,))
        rows = cursor.fetchall()
        conn.close()

        trades = []
        for row in rows:
            trade = dict(row)
            trades.append({
                "trade_id": trade["trade_id"],
                "symbol": trade["symbol"],
                "trade_type": trade["trade_type"],
                "quantity": trade["quantity"],
                "entry_price": trade["entry_price"],
                "exit_price": trade["exit_price"] or 0.0,
                "realized_pnl": trade["realized_pnl"] or 0.0,
                "realized_pnl_pct": 0.0,
                "entry_date": trade["entry_timestamp"],
                "exit_date": trade["exit_timestamp"] or "",
                "holding_period_days": 0,
                "reason_closed": "manual",
                "strategy_rationale": trade["strategy_rationale"],
                "ai_suggested": False,
            })

        return trades
    except Exception as e:
        logger.error(f"Failed to get paper trading trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ERROR HANDLERS
# ============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "code": str(exc.status_code), "service": SERVICE_NAME},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "code": "500", "service": SERVICE_NAME},
    )


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
