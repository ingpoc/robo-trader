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
from contextlib import asynccontextmanager
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
from .broadcast_throttler import BroadcastThrottler, ThrottleConfig

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
from .routes.zerodha_auth import router as zerodha_auth_router
from .routes.claude_transparency import router as claude_transparency_router
from .routes.config import router as config_router
from .routes.configuration import router as configuration_router
from .routes.logs import router as logs_router
from .routes.prompt_optimization import router as prompt_optimization_router
from .routes.symbols import router as symbols_router

# ============================================================================
# Global Variables
# ============================================================================

# Background task status tracking
initialization_status = {
    "orchestrator_initialized": False,
    "bootstrap_completed": False,
    "initialization_errors": [],
    "last_error": None
}

# Event for shutdown coordination
shutdown_event = asyncio.Event()

# ============================================================================
# Helper Functions
# ============================================================================

async def bootstrap_state(orchestrator, config):
    """Bootstrap the application state after orchestrator initialization."""
    try:
        # Add timeout to prevent hanging during startup
        import asyncio

        portfolio = await asyncio.wait_for(
            orchestrator.state_manager.get_portfolio(),
            timeout=5.0
        )

        if not portfolio and orchestrator and config and config.agents.portfolio_scan.enabled:
            logger.debug("Triggering bootstrap portfolio scan")
            # Run portfolio scan with timeout to prevent hanging
            try:
                await asyncio.wait_for(
                    orchestrator.run_portfolio_scan(),
                    timeout=10.0
                )
                portfolio = await asyncio.wait_for(
                    orchestrator.state_manager.get_portfolio(),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning("Portfolio scan timed out during bootstrap, skipping")

        logger.info("Bootstrap state completed successfully")
    except Exception as exc:
        logger.warning(f"Bootstrap failed: {exc}")
        # Don't fail initialization for bootstrap issues

async def initialize_orchestrator(config, container, connection_manager):
    """Initialize orchestrator in background."""
    try:
        logger.info("Starting orchestrator initialization...")

        # Get orchestrator from container
        orchestrator = await container.get_orchestrator()

        await asyncio.wait_for(orchestrator.initialize(), timeout=60.0)
        logger.info("Orchestrator initialized")

        await orchestrator.start_session()
        logger.info("Orchestrator session started")

        initialization_status["orchestrator_initialized"] = True

        # Run bootstrap state
        logger.info("Running bootstrap state...")
        await bootstrap_state(orchestrator, config)
        initialization_status["bootstrap_completed"] = True
        logger.info("Bootstrap state completed successfully")
    except asyncio.TimeoutError:
        error_msg = "Orchestrator initialization timed out"
        logger.error(error_msg)
        initialization_status["initialization_errors"].append(error_msg)
        initialization_status["last_error"] = error_msg
    except Exception as exc:
        error_msg = f"Orchestrator initialization failed: {exc}"
        logger.error(error_msg, exc_info=True)
        initialization_status["initialization_errors"].append(error_msg)
        initialization_status["last_error"] = error_msg

# ============================================================================
# FastAPI Application Setup
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan events."""
    global config, container, connection_manager, service_client, initialization_status

    # Startup - Setup logging first
    try:
        # Setup logging as early as possible to catch all errors
        from src.core.logging_config import ensure_logging_setup
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        ensure_logging_setup(logs_dir, 'INFO')
        logger.info("=== STARTUP EVENT STARTED ===")
    except Exception as e:
        # If logging setup fails, at least print to stderr
        print(f"CRITICAL: Failed to setup logging: {e}", file=sys.stderr)
        raise

    config = load_config()
    logger.info("Config loaded successfully")

    logger.info("Initializing DI container...")
    container = await initialize_container(config)
    logger.info("DI container initialized")

    app.state.container = container
    logger.info("Container stored in app.state")

    # Set container for paper trading routes
    from .routes.paper_trading import set_container as set_paper_trading_container
    set_paper_trading_container(container)
    logger.info("Paper trading routes initialized with container")

    connection_manager = ConnectionManager()
    logger.info("ConnectionManager created")

    logger.info("Getting orchestrator from container...")
    orchestrator = await container.get_orchestrator()
    logger.info("Orchestrator retrieved")

    # Set orchestrator initialization status
    initialization_status["orchestrator_initialized"] = True

    logger.info("Wiring WebSocket broadcasting...")
    orchestrator.broadcast_coordinator.set_broadcast_callback(
        lambda data: asyncio.create_task(
            connection_manager.broadcast(data)
        )
    )

    # Set connection manager on status coordinator for real WebSocket client count
    if orchestrator.status_coordinator:
        orchestrator.status_coordinator.set_connection_manager(connection_manager)
        orchestrator.status_coordinator.set_container(container)
        logger.info("Connection manager set on status coordinator")

    logger.info("WebSocket broadcasting wired")

    # Run bootstrap state
    logger.info("Running bootstrap state...")
    await bootstrap_state(orchestrator, config)
    initialization_status["bootstrap_completed"] = True
    logger.info("Bootstrap state completed successfully")

    logger.info("Background tasks created...")
    logger.info("Background tasks created")

    logger.info("Background initialization completed")

    yield

    # Shutdown
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
        logger.info("DI container cleanup completed")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")

    logger.info("Shutdown completed")

app = FastAPI(
    title="Robo Trader API",
    description="Autonomous Trading System Backend API - Serves React Frontend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
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
app.include_router(zerodha_auth_router)
app.include_router(claude_transparency_router)
app.include_router(symbols_router)
app.include_router(config_router)
app.include_router(configuration_router)
app.include_router(logs_router)
app.include_router(prompt_optimization_router)

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
                # Claude Agent SDK best practices: Handle SDK-specific errors gracefully
                if "Claude" in str(e) or "anthropic" in str(e).lower() or "open_process" in str(e):
                    ai_status = {"status": "unavailable", "error": "AI agent temporarily unavailable - paper trading mode active"}
                else:
                    ai_status = {"status": "error", "error": str(e)}
                recommendations = []

        if attempt < max_retries:
            await asyncio.sleep(0.5 * (2 ** attempt))

    return ai_status, recommendations


async def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data for display."""
    global initialization_status

    if not container:
        return {
            "error": "System not initialized",
            "initialization_status": initialization_status
        }

    orchestrator = await container.get_orchestrator()
    if not orchestrator or not orchestrator.state_manager:
        return {
            "error": "System not initialized",
            "initialization_status": initialization_status
        }

    # Check if initialization is complete
    if not initialization_status["orchestrator_initialized"]:
        return {
            "error": "System initialization in progress",
            "initialization_status": initialization_status,
            "message": "Please wait for system initialization to complete"
        }

    portfolio = await orchestrator.state_manager.get_portfolio()

    if not portfolio and orchestrator and config and config.agents.portfolio_scan.enabled:
        try:
            logger.debug("Triggering bootstrap portfolio scan")
            await orchestrator.run_portfolio_scan()
            portfolio = await orchestrator.state_manager.get_portfolio()
        except Exception as exc:
            logger.warning(f"Bootstrap failed: {exc}")

    intents = await orchestrator.state_manager.get_all_intents()

    # Get screening and strategy results with fallback to None if not implemented
    try:
        screening = await orchestrator.state_manager.get_screening_results()
    except (NotImplementedError, AttributeError):
        screening = None

    try:
        strategy = await orchestrator.state_manager.get_strategy_results()
    except (NotImplementedError, AttributeError):
        strategy = None

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
        "initialization_status": initialization_status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


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
        "health": "/api/health",
        "initialization_status": initialization_status,
        "endpoints": {
            "dashboard": "/api/dashboard",
            "trading": "/api/manual-trade",
            "ai": "/api/ai/status",
            "agents": "/api/agents/status",
            "monitoring": "/api/monitoring/status",
        }
    }

# ============================================================================
# Health Check Endpoint
# ============================================================================

@app.get("/api/health")
async def health_check(request: Request) -> Dict[str, Any]:
    """Health check endpoint to verify system initialization."""
    try:
        container = request.app.state.container
        if not container:
            return JSONResponse({
                "status": "unhealthy",
                "error": "Container not initialized",
                "initialization_status": initialization_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=503)

        # Test orchestrator access
        orchestrator = await container.get_orchestrator()
        if not orchestrator:
            return JSONResponse({
                "status": "degraded",
                "error": "Orchestrator not available",
                "initialization_status": initialization_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=503)

        # Test state manager access
        if not hasattr(orchestrator, 'state_manager') or not orchestrator.state_manager:
            return JSONResponse({
                "status": "degraded",
                "error": "State manager not available",
                "initialization_status": initialization_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=503)

        # Check initialization status
        if not initialization_status["orchestrator_initialized"]:
            return JSONResponse({
                "status": "degraded",
                "error": "Orchestrator initialization incomplete",
                "initialization_status": initialization_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=503)

        if initialization_status["initialization_errors"]:
            return JSONResponse({
                "status": "degraded",
                "error": "Initialization errors detected",
                "initialization_status": initialization_status,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, status_code=503)

        return {
            "status": "healthy",
            "message": "All systems operational",
            "components": {
                "container": "initialized",
                "orchestrator": "running",
                "state_manager": "available",
                "initialization": "complete"
            },
            "initialization_status": initialization_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "initialization_status": initialization_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=503)
# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    client_id = None
    try:
        client_id = await connection_manager.connect(websocket)

        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection_established",
            "client_id": client_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": "WebSocket connection established successfully"
        })

        # Broadcast current status to the newly connected client
        if container:
            try:
                orchestrator = await container.get_orchestrator()
                if orchestrator:
                    # Trigger status broadcasts for the new client
                    await orchestrator.get_system_status()  # This broadcasts system health
                    await orchestrator.get_claude_status()  # This broadcasts Claude status

                    # Also broadcast queue status
                    queue_coordinator = await container.get('queue_coordinator')
                    if queue_coordinator:
                        await queue_coordinator.get_queue_status()  # This broadcasts queue status

                    logger.info(f"Broadcast initial status updates to client {client_id}")
            except Exception as e:
                logger.warning(f"Failed to broadcast initial status to client {client_id}: {e}")

        while True:
            data = await websocket.receive_json()

            if data.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
            elif data.get("type") == "subscribe":
                # Handle subscription requests
                await websocket.send_json({
                    "type": "subscription_confirmed",
                    "channels": data.get("channels", ["dashboard", "portfolio"]),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {client_id}")
        if client_id:
            await connection_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error for {client_id}: {e}")
        if connection_manager:
            try:
                await connection_manager.disconnect(websocket)
            except:
                pass

# ============================================================================
# Server Startup Function
# ============================================================================

def run_web_server():
    """Run the web server."""
    uvicorn.run(
        "src.web.app:app",  # Use import string for reload support
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True,
        reload=True,  # Enable auto-reload for development
    )

# ============================================================================
# Main Entry
# ============================================================================

if __name__ == "__main__":
    run_web_server()
