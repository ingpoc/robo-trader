"""
Robo Trader Web UI - Minimal FastAPI Application

Refactored to modular route structure for maintainability.
All endpoints organized in src/web/routes/ modules.
"""

import asyncio
import json
import signal
import sys
import os
import time
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import uvicorn
import httpx

from src.config import load_config
from src.core.di import initialize_container, cleanup_container, DependencyContainer
from src.core.database_state import DatabaseStateManager
from src.core.errors import TradingError, ErrorHandler
from .chat_api import router as chat_router
from .claude_agent_api import router as claude_agent_router
from .queues_api import router as queues_router
from .websocket_differ import WebSocketDiffer
from .connection_manager import ConnectionManager

# Import route modules
from .routes import (
    dashboard_router,
    execution_router,
    monitoring_router,
    agents_router,
    analytics_router
)
from .routes.paper_trading import router as paper_trading_router
from .routes.news_earnings import router as news_earnings_router
from .routes.config import router as config_router
from .routes.logs import router as logs_router

# ============================================================================
# FastAPI Application Setup
# ============================================================================

app = FastAPI(
    title="Robo Trader API",
    description="Autonomous Trading System Backend API - Serves React Frontend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Rate Limiting Configuration
def get_rate_limit_key(request):
    """Get rate limiting key handling load balancers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    user_id = getattr(request.state, 'user_id', None) if hasattr(request, 'state') else None
    if user_id:
        return f"{user_id}:{client_ip}"
    return client_ip

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    max_age=3600,
)

# ============================================================================
# Middleware
# ============================================================================

@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    """Centralized error handling middleware."""
    try:
        response = await call_next(request)
        return response
    except TradingError as e:
        logger.error(f"Trading error: {e.context.message}", extra={
            "category": e.context.category.value,
            "severity": e.context.severity.value,
            "code": e.context.code
        })
        return JSONResponse(
            status_code=500 if e.context.severity.value in ["critical", "high"] else 400,
            content=e.to_dict()
        )
    except Exception as e:
        error_context = ErrorHandler.handle_error(e)
        logger.error(f"Unhandled error: {error_context.message}", extra={
            "category": error_context.category.value,
            "severity": error_context.severity.value
        })
        return JSONResponse(
            status_code=500,
            content=ErrorHandler.format_error_response(e)
        )

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Structured request/response logging middleware."""
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    return response

# ============================================================================
# Include API Route Routers
# ============================================================================

app.include_router(claude_agent_router)
app.include_router(queues_router, prefix="/api")

# Include refactored route modules
app.include_router(dashboard_router)
app.include_router(execution_router)
app.include_router(monitoring_router)
app.include_router(agents_router)
app.include_router(analytics_router)
app.include_router(paper_trading_router)
app.include_router(news_earnings_router)
app.include_router(config_router)
app.include_router(logs_router)

# ============================================================================
# Global State
# ============================================================================

config = None
container: Optional[DependencyContainer] = None
connection_manager = None
service_client = None
shutdown_event = asyncio.Event()

# ============================================================================
# Request Models
# ============================================================================

class TradeRequest(BaseModel):
    """Manual trade request model."""
    symbol: str
    side: str
    quantity: int
    order_type: str = "MARKET"
    price: Optional[float] = None

# ============================================================================
# Utility Functions (kept in main app for ease of access)
# ============================================================================

async def get_ai_data_with_retry(orchestrator, connection_id: str, max_retries: int = 2) -> tuple:
    """Get AI status and recommendations with retry logic."""
    ai_status = {"status": "unknown", "error": "Failed to retrieve AI status"}
    recommendations = []

    for attempt in range(max_retries + 1):
        try:
            timeout = 3.0 if attempt == 0 else 2.0

            ai_status_task = asyncio.wait_for(orchestrator.get_ai_status(), timeout=timeout)
            recommendations_task = asyncio.wait_for(
                orchestrator.state_manager.get_pending_approvals(), timeout=timeout
            )

            ai_status_result, recommendations_result = await asyncio.gather(
                ai_status_task, recommendations_task, return_exceptions=True
            )

            if isinstance(ai_status_result, Exception):
                logger.warning(f"AI status failed (attempt {attempt + 1}): {ai_status_result}")
                ai_status = {"status": "error", "error": str(ai_status_result)}
            else:
                ai_status = ai_status_result

            if isinstance(recommendations_result, Exception):
                logger.warning(f"Recommendations failed (attempt {attempt + 1}): {recommendations_result}")
                recommendations = []
            else:
                recommendations = recommendations_result

            if not isinstance(ai_status_result, Exception) or not isinstance(recommendations_result, Exception):
                return ai_status, recommendations

        except asyncio.TimeoutError:
            logger.warning(f"Timeout retrieving AI data (attempt {attempt + 1})")
            if attempt == max_retries:
                ai_status = {"status": "timeout", "error": "Request timed out"}
                recommendations = []
        except Exception as e:
            logger.error(f"Error retrieving AI data (attempt {attempt + 1}): {e}")
            if attempt == max_retries:
                ai_status = {"status": "error", "error": str(e)}
                recommendations = []

        if attempt < max_retries:
            await asyncio.sleep(0.5 * (2 ** attempt))

    return ai_status, recommendations


async def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data for display."""
    if not container:
        return {"error": "System not initialized"}

    orchestrator = await container.get_orchestrator()
    if not orchestrator or not orchestrator.state_manager:
        return {"error": "System not initialized"}

    portfolio = await orchestrator.state_manager.get_portfolio()

    if not portfolio and orchestrator and config and config.agents.portfolio_scan.enabled:
        try:
            logger.debug("Triggering bootstrap portfolio scan")
            await orchestrator.run_portfolio_scan()
            portfolio = await orchestrator.state_manager.get_portfolio()
        except Exception as exc:
            logger.warning(f"Bootstrap failed: {exc}")

    intents = await orchestrator.state_manager.get_all_intents()
    screening = await orchestrator.state_manager.get_screening_results()
    strategy = await orchestrator.state_manager.get_strategy_results()

    portfolio_dict = portfolio.to_dict() if portfolio else None
    analytics = portfolio_dict.get("risk_aggregates") if portfolio_dict else None

    return {
        "portfolio": portfolio_dict,
        "analytics": analytics,
        "screening": screening,
        "strategy": strategy,
        "intents": [intent.to_dict() for intent in intents],
        "config": {
            "environment": config.environment if config else "unknown",
            "max_turns": config.max_turns if config else 50
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# ============================================================================
# Lifecycle Events
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup."""
    global config, container, connection_manager, service_client

    logger.info("=== STARTUP EVENT STARTED ===")

    config = load_config()
    logger.info("Config loaded successfully")

    logger.info("Initializing DI container...")
    container = await initialize_container(config)
    logger.info("DI container initialized")

    app.state.container = container
    logger.info("Container stored in app.state")

    connection_manager = ConnectionManager()
    logger.info("ConnectionManager created")

    logger.info("Getting orchestrator from container...")
    orchestrator = await container.get_orchestrator()
    logger.info("Orchestrator retrieved")

    logger.info("Wiring WebSocket broadcasting...")
    async def broadcast_to_ui_impl(message: Dict[str, Any]):
        result = await connection_manager.broadcast(message)
        logger.debug(f"Broadcast: {result.successful_sends}/{result.total_connections}")

    orchestrator.broadcast_coordinator.set_broadcast_callback(broadcast_to_ui_impl)
    logger.info("WebSocket broadcasting wired")

    async def initialize_orchestrator():
        """Initialize orchestrator in background."""
        try:
            logger.info("Starting orchestrator initialization...")
            await asyncio.wait_for(orchestrator.initialize(), timeout=60.0)
            logger.info("Orchestrator initialized")
            await orchestrator.start_session()
            logger.info("Orchestrator session started")
        except asyncio.TimeoutError:
            logger.error("Orchestrator initialization timed out")
        except Exception as exc:
            logger.error(f"Orchestrator initialization failed: {exc}", exc_info=True)

    async def bootstrap_state():
        """Prime initial analytics."""
        if not orchestrator:
            return
        if config.agents.portfolio_scan.enabled:
            try:
                await asyncio.wait_for(orchestrator.run_portfolio_scan(), timeout=30.0)
            except Exception as exc:
                logger.warning(f"Portfolio scan failed: {exc}")
        if config.agents.market_screening.enabled:
            try:
                await asyncio.wait_for(orchestrator.run_market_screening(), timeout=30.0)
            except Exception as exc:
                logger.warning(f"Market screening failed: {exc}")

    try:
        orchestrator_task = asyncio.create_task(initialize_orchestrator())
        bootstrap_task = asyncio.create_task(bootstrap_state())
        logger.info("Background tasks created")
    except Exception as e:
        logger.error(f"Failed to create background tasks: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_handler():
    """Cleanup resources on shutdown."""
    global container, connection_manager, service_client
    logger.info("Shutdown initiated")

    shutdown_event.set()

    try:
        if service_client:
            logger.info("Closing HTTP client...")
            await service_client.aclose()

        if connection_manager:
            logger.info("Closing WebSocket connections...")
            await connection_manager.broadcast({
                "type": "shutdown",
                "message": "Server shutting down",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        await cleanup_container()

    except Exception as e:
        logger.error(f"Shutdown error: {e}", exc_info=True)

    logger.info("Shutdown complete")

# ============================================================================
# Root Endpoint
# ============================================================================

@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "Robo Trader API",
        "version": "1.0.0",
        "description": "Autonomous Trading System Backend",
        "frontend": "http://localhost:3000",
        "docs": "/docs",
        "websocket": "ws://localhost:8000/ws",
        "endpoints": {
            "dashboard": "/api/dashboard",
            "trading": "/api/manual-trade",
            "ai": "/api/ai/status",
            "agents": "/api/agents/status",
            "monitoring": "/api/monitoring/status",
        }
    }

# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    client_id = None
    try:
        await connection_manager.connect(websocket, "unknown")

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        if client_id:
            await connection_manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if connection_manager:
            try:
                await connection_manager.disconnect(websocket, client_id or "unknown")
            except:
                pass

# ============================================================================
# Server Startup Function
# ============================================================================

def run_web_server():
    """Run the web server."""
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
    )

# ============================================================================
# Main Entry
# ============================================================================

if __name__ == "__main__":
    run_web_server()
