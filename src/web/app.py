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

# Setup very early logging to capture import errors
try:
    from pathlib import Path as PathLibPath
    from loguru import logger
    
    # Configure minimal logging early to capture all errors
    logs_dir = PathLibPath.cwd() / "logs"
    logs_dir.mkdir(exist_ok=True)

    # Get log level from environment (default: INFO)
    # Priority: 1) --log-level CLI flag, 2) .env file, 3) default INFO
    # Command line --log-level flag sets this via main.py
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Clear log files on startup
    for log_file in ["backend.log", "errors.log", "critical.log", "frontend.log"]:
        log_path = logs_dir / log_file
        if log_path.exists():
            try:
                log_path.unlink()
            except Exception:
                pass  # Ignore errors clearing logs

    # Set up basic file logging immediately
    logger.remove()
    backend_log = logs_dir / "backend.log"
    logger.add(
        backend_log,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",  # Always capture DEBUG in file
        backtrace=True,
        diagnose=True,
        enqueue=False  # Synchronous to capture startup errors
    )

    # Console handler - only show logs at configured level
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
        backtrace=True,
        diagnose=True
    )

    logger.info(f"=== EARLY LOGGING SETUP (Level: {log_level}) ===")
    logger.info(f"Starting application - Python {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    
    # Setup global exception handler to capture all errors in log file
    original_excepthook = sys.excepthook
    def log_exception(exc_type, exc_value, exc_traceback):
        """Log all unhandled exceptions to log file before printing to stderr."""
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        try:
            logger.critical(
                f"Unhandled exception during startup: {exc_value}",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
        except Exception:
            pass  # If logging fails, fall back to original handler
        
        # Also call original handler to print to stderr
        original_excepthook(exc_type, exc_value, exc_traceback)
    
    sys.excepthook = log_exception
    logger.info("Global exception handler installed to capture all errors")
except Exception as e:
    # If early logging fails, at least print to stderr
    print(f"CRITICAL: Failed early logging setup: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc(file=sys.stderr)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import uvicorn
import httpx

from src.config import load_config
from src.core.di import initialize_container, cleanup_container, DependencyContainer
from src.core.database_state.database_state import DatabaseStateManager
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
from .routes.database_backups import router as database_backups_router
from .routes.coordinators import router as coordinators_router
from .routes.token_status import router as token_status_router

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
        logger.info("Bootstrap state skipped for faster startup")
        # Skip all bootstrap operations to prevent hanging during startup
        # This will be handled by background tasks after server is running
        return
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
    # Use local variables and app.state instead of globals for better testability
    service_client = None

    # Startup - Enhance logging (already set up early, but add console handler and error handlers)
    try:
        # Enhance logging setup with console handler and error handlers
        from src.core.logging_config import setup_logging
        logs_dir = Path.cwd() / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Enhance existing logging (early logging already set up, just add handlers)
        # Use LOG_LEVEL environment variable set by command-line argument for consistency
        # Priority: 1) --log-level CLI flag, 2) .env file, 3) default INFO
        log_level = os.getenv("LOG_LEVEL", "INFO").upper()
        setup_logging(logs_dir, log_level, clear_logs=False)  # Don't clear again, already cleared
        
        # Configure uvicorn access logger to use our logger
        import logging as std_logging
        uvicorn_access_logger = std_logging.getLogger("uvicorn.access")
        uvicorn_error_logger = std_logging.getLogger("uvicorn.error")

        # Create a handler that forwards uvicorn logs to loguru
        class LoguruHandler(std_logging.Handler):
            def emit(self, record):
                try:
                    level = logger.level(record.levelname).name
                except ValueError:
                    level = log_level  # Use configured level instead of defaulting to INFO

                logger.opt(depth=6, exception=record.exc_info).log(level, record.getMessage())

        # Add loguru handler to uvicorn loggers
        uvicorn_handler = LoguruHandler()
        uvicorn_access_logger.addHandler(uvicorn_handler)
        uvicorn_error_logger.addHandler(uvicorn_handler)
        # Set uvicorn loggers to use the same level as our configured log level
        uvicorn_access_logger.setLevel(getattr(std_logging, log_level))
        uvicorn_error_logger.setLevel(getattr(std_logging, log_level))

        # Log startup confirmation at WARNING level (always visible)
        logger.warning("=== LIFESPAN STARTUP EVENT STARTED ===")
        logger.warning(f"Enhanced logging with all handlers: {logs_dir}")
        logger.warning("Uvicorn access logger configured to use loguru")
    except Exception as e:
        # Log the error using existing logger
        logger.error(f"Failed to enhance logging setup: {e}", exc_info=True)
        raise

    config = load_config()
    logger.info("Config loaded successfully")

    logger.info("Initializing DI container...")
    container = await initialize_container(config)
    logger.info("DI container initialized")

    app.state.container = container
    logger.info("Container stored in app.state - all routes can access via Depends(get_container)")

    connection_manager = ConnectionManager()
    app.state.connection_manager = connection_manager
    logger.info("ConnectionManager created")

    logger.info("Getting orchestrator from container...")
    orchestrator = await container.get_orchestrator()
    logger.info("Orchestrator retrieved")

    # Initialize orchestrator (starts BackgroundScheduler and SequentialQueueManager)
    logger.info("Initializing orchestrator (starting background scheduler and queue manager)...")
    await orchestrator.initialize()
    logger.info("Orchestrator initialization complete - BackgroundScheduler and SequentialQueueManager are now running")

    # Start queue execution after orchestrator initialization
    logger.info("Starting queue execution...")
    try:
        queue_coordinator = orchestrator.queue_coordinator
        if queue_coordinator:
            await queue_coordinator.start_queues()
            logger.info("Queue execution started - queues are now processing pending tasks")
        else:
            logger.warning("Queue coordinator not available - queues will not start")
    except Exception as e:
        logger.warning(f"Failed to start queues: {e} - continuing without queue execution")

    # Set orchestrator initialization status
    initialization_status["orchestrator_initialized"] = True

    logger.info("Wiring WebSocket broadcasting...")

    # Create safe broadcast function with exception handling
    async def safe_broadcast(data):
        """Safely broadcast data with exception handling to prevent TaskGroup errors."""
        try:
            await connection_manager.broadcast(data)
        except Exception as e:
            logger.debug(f"Broadcast failed (likely no active connections): {e}")

    orchestrator.broadcast_coordinator.set_broadcast_callback(
        lambda data: asyncio.create_task(safe_broadcast(data))
    )

    # Set connection manager on status coordinator for real WebSocket client count
    if orchestrator.status_coordinator:
        orchestrator.status_coordinator.set_connection_manager(connection_manager)
        orchestrator.status_coordinator.set_container(container)
        logger.info("Connection manager set on status coordinator")

    logger.info("WebSocket broadcasting wired")

    # Trigger initial status broadcast now that callback is ready
    logger.info("Broadcasting initial system status...")
    await orchestrator.status_coordinator.get_system_status(force_broadcast=True)
    logger.info("Initial status broadcast complete")

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
        # Get service_client from app.state if it was stored there
        service_client = getattr(app.state, "service_client", None)
        if service_client:
            logger.info("Closing HTTP client...")
            await service_client.aclose()

        # Get connection_manager from app.state
        connection_manager = getattr(app.state, "connection_manager", None)
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
        "http://localhost:3001",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
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
async def logging_middleware(request: Request, call_next):
    """Log all API requests and responses."""
    import time

    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()

    # Log request
    start_time = time.time()
    method = request.method
    url = str(request.url)
    path = request.url.path

    logger.debug(f"{method} {path} - Client: {client_ip}")

    try:
        response = await call_next(request)

        # Calculate response time
        process_time = time.time() - start_time

        # Log response
        status_code = response.status_code
        if status_code >= 500:
            logger.error(f"{method} {path} - Status: {status_code} - Time: {process_time:.3f}s - Client: {client_ip}")
        elif status_code >= 400:
            logger.warning(f"{method} {path} - Status: {status_code} - Time: {process_time:.3f}s - Client: {client_ip}")
        else:
            logger.debug(f"{method} {path} - Status: {status_code} - Time: {process_time:.3f}s - Client: {client_ip}")

        return response
    except Exception as e:
        # Calculate response time even on error
        process_time = time.time() - start_time
        logger.error(f"{method} {path} - Exception: {type(e).__name__}: {str(e)} - Time: {process_time:.3f}s - Client: {client_ip}", exc_info=True)
        raise

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
app.include_router(database_backups_router)
app.include_router(coordinators_router)
app.include_router(token_status_router)

# ============================================================================
# Global State (removed - use app.state or dependency injection instead)
# ============================================================================

# shutdown_event remains module-level as it's used for coordination
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
    """Health check endpoint to verify system initialization.

    Phase 4 Enhancement: Added timeout protection (2 second limit).
    Health checks must respond quickly even during long-running tasks.
    With thread-safe queue executors, health checks no longer block.
    """
    try:
        # Wrap entire health check in timeout for safety
        # With non-blocking task execution, this should respond in <100ms
        # 2 second timeout ensures responsiveness even under high load
        async def perform_health_check() -> Dict[str, Any]:
            container = request.app.state.container
            if not container:
                return JSONResponse({
                    "status": "unhealthy",
                    "error": "Container not initialized",
                    "initialization_status": initialization_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, status_code=503)

            # Test orchestrator access (should be instant with new architecture)
            orchestrator = await container.get_orchestrator()
            if not orchestrator:
                return JSONResponse({
                    "status": "degraded",
                    "error": "Orchestrator not available",
                    "initialization_status": initialization_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, status_code=503)

            # Test state manager access (fast check)
            if not hasattr(orchestrator, 'state_manager') or not orchestrator.state_manager:
                return JSONResponse({
                    "status": "degraded",
                    "error": "State manager not available",
                    "initialization_status": initialization_status,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }, status_code=503)

            # Check initialization status (cached check)
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

        # Execute health check with 2-second timeout
        # This ensures health checks respond even under extreme load
        result = await asyncio.wait_for(perform_health_check(), timeout=2.0)
        return result

    except asyncio.TimeoutError:
        logger.warning("Health check exceeded timeout (2s) - returning degraded status")
        return JSONResponse({
            "status": "degraded",
            "error": "Health check timeout - system may be overloaded",
            "initialization_status": initialization_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=503)

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
    # Get connection manager from app state
    connection_manager = getattr(websocket.app.state, "connection_manager", None)
    if not connection_manager:
        await websocket.close(code=1011, reason="Connection manager not initialized")
        return
    
    container = getattr(websocket.app.state, "container", None)
    
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
                logger.info(f"Getting orchestrator for initial status broadcast to client {client_id}")
                orchestrator = await container.get_orchestrator()
                if orchestrator:
                    logger.info(f"Broadcasting system status for client {client_id}")
                    await orchestrator.get_system_status()  # This broadcasts system health
                    logger.info(f"Broadcasting Claude status for client {client_id}")
                    await orchestrator.get_claude_status()  # This broadcasts Claude status

                    # Also broadcast queue status
                    logger.info(f"Getting queue coordinator for client {client_id}")
                    queue_coordinator = await container.get('queue_coordinator')
                    if queue_coordinator:
                        logger.info(f"Broadcasting queue status for client {client_id}")
                        await queue_coordinator.get_queue_status()  # This broadcasts queue status
                        logger.info(f"Queue status broadcast completed for client {client_id}")
                    else:
                        logger.warning(f"Queue coordinator not available for client {client_id}")

                    logger.info(f"Broadcast initial status updates to client {client_id}")
                else:
                    logger.warning(f"Orchestrator not available for client {client_id}")
            except Exception as e:
                logger.error(f"Failed to broadcast initial status to client {client_id}: {e}")
                import traceback
                logger.error(f"Broadcast failure traceback: {traceback.format_exc()}")

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
            except Exception as disconnect_error:
                logger.warning(f"Failed to disconnect WebSocket {client_id}: {disconnect_error}")

# ============================================================================
# Server Startup Function
# ============================================================================

def run_web_server():
    """Run the web server."""
    # Get log level from environment variable (default: INFO)
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()

    # Uvicorn expects lowercase log level
    uvicorn_log_level = log_level.lower()

    uvicorn.run(
        "src.web.app:app",  # Use import string for reload support
        host="0.0.0.0",
        port=8000,
        log_level=uvicorn_log_level,
        access_log=True,
        reload=True,  # Enable auto-reload for development
    )

# ============================================================================
# Main Entry
# ============================================================================

if __name__ == "__main__":
    run_web_server()
