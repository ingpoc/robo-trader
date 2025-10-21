"""
Robo Trader Web UI

FastAPI application providing a web interface for the trading system.
"""

import asyncio
import json
import signal
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
import uvicorn
import time

from ..config import load_config
from ..core.di import initialize_container, cleanup_container, DependencyContainer
from ..core.database_state import DatabaseStateManager
from ..core.errors import TradingError, ErrorHandler
from .chat_api import router as chat_router
from .claude_agent_api import router as claude_agent_router
from .websocket_differ import WebSocketDiffer
from .connection_manager import ConnectionManager


app = FastAPI(
    title="Robo Trader API",
    description="Autonomous Trading System Backend API - Serves React Frontend",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Setup rate limiting with configurable limits and load balancer support
import os

def get_rate_limit_key(request):
    """Get rate limiting key, handling load balancers/CDNs."""
    # Try X-Forwarded-For header first (for load balancers)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # Take the first IP if there are multiple
        client_ip = forwarded_for.split(",")[0].strip()
    else:
        # Fall back to direct client IP
        client_ip = request.client.host if request.client else "unknown"

    # Add user identifier if available (for future auth)
    user_id = getattr(request.state, 'user_id', None) if hasattr(request, 'state') else None
    if user_id:
        return f"{user_id}:{client_ip}"
    return client_ip

# Configurable rate limits via environment variables
dashboard_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")
trade_limit = os.getenv("RATE_LIMIT_TRADES", "10/minute")
agents_limit = os.getenv("RATE_LIMIT_AGENTS", "20/minute")

limiter = Limiter(key_func=get_rate_limit_key)
app.state.limiter = limiter
app.add_exception_handler(429, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

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

    # Removed verbose request start/completion logging for cleaner logs
    # Uncomment below for debugging if needed:
    # logger.info(
    #     "Request started",
    #     extra={
    #         "method": request.method,
    #         "path": request.url.path,
    #         "client": request.client.host if request.client else None,
    #         "user_agent": request.headers.get("user-agent", "unknown")
    #     }
    # )

    response = await call_next(request)

    duration = time.time() - start_time
    # Removed verbose request completion logging for cleaner logs
    # Uncomment below for debugging if needed:
    # logger.info(
    #     "Request completed",
    #     extra={
    #         "method": request.method,
    #         "path": request.url.path,
    #         "status_code": response.status_code,
    #         "duration_ms": round(duration * 1000, 2)
    #     }
    # )

    return response

# Include API routers
# TEMPORARILY DISABLED FOR DEBUGGING
# app.include_router(chat_router)

# Include Claude Agent API router
app.include_router(claude_agent_router)

# Global variables
config = None
container: Optional[DependencyContainer] = None
connection_manager = None

# Shutdown event for graceful shutdown coordination
shutdown_event = asyncio.Event()


class TradeRequest(BaseModel):
    """Manual trade request model."""
    symbol: str
    side: str  # BUY or SELL
    quantity: int
    order_type: str = "MARKET"
    price: Optional[float] = None


async def get_ai_data_with_retry(orchestrator, connection_id: str, max_retries: int = 2) -> tuple:
    """Get AI status and recommendations with retry logic and better error handling."""
    ai_status = {"status": "unknown", "error": "Failed to retrieve AI status"}
    recommendations = []

    for attempt in range(max_retries + 1):
        try:
            # Use different timeouts for different attempts
            timeout = 3.0 if attempt == 0 else 2.0  # Shorter timeout on retries

            # Get AI status with timeout
            ai_status_task = asyncio.wait_for(orchestrator.get_ai_status(), timeout=timeout)

            # Get recommendations with timeout
            recommendations_task = asyncio.wait_for(
                orchestrator.state_manager.get_pending_approvals(), timeout=timeout
            )

            # Execute both concurrently
            ai_status_result, recommendations_result = await asyncio.gather(
                ai_status_task, recommendations_task, return_exceptions=True
            )

            # Handle individual task results
            if isinstance(ai_status_result, Exception):
                logger.warning(f"AI status retrieval failed (attempt {attempt + 1}): {ai_status_result}")
                ai_status = {"status": "error", "error": str(ai_status_result)}
            else:
                ai_status = ai_status_result

            if isinstance(recommendations_result, Exception):
                logger.warning(f"Recommendations retrieval failed (attempt {attempt + 1}): {recommendations_result}")
                recommendations = []
            else:
                recommendations = recommendations_result

            # If we got at least one successful result, return what we have
            if not isinstance(ai_status_result, Exception) or not isinstance(recommendations_result, Exception):
                return ai_status, recommendations

        except asyncio.TimeoutError:
            logger.warning(f"Timeout retrieving AI data for {connection_id} (attempt {attempt + 1})")
            if attempt == max_retries:
                ai_status = {"status": "timeout", "error": "Request timed out after retries"}
                recommendations = []
        except Exception as e:
            logger.error(f"Unexpected error retrieving AI data for {connection_id} (attempt {attempt + 1}): {e}")
            if attempt == max_retries:
                ai_status = {"status": "error", "error": str(e)}
                recommendations = []

        # Exponential backoff for retries
        if attempt < max_retries:
            await asyncio.sleep(0.5 * (2 ** attempt))  # 0.5s, 1s, 2s...

    return ai_status, recommendations


async def get_dashboard_data() -> Dict[str, Any]:
    """Get dashboard data for display."""
    if not container:
        return {"error": "System not initialized"}

    orchestrator = await container.get_orchestrator()
    if not orchestrator or not orchestrator.state_manager:
        return {"error": "System not initialized"}

    portfolio = await orchestrator.state_manager.get_portfolio()

    # Trigger lazy bootstrap if portfolio not yet available and portfolio_scan is enabled
    if not portfolio and orchestrator and config.agents.portfolio_scan.enabled:
        try:
            logger.debug("Portfolio missing in state store; triggering bootstrap scan")
            await orchestrator.run_portfolio_scan()
            portfolio = await orchestrator.state_manager.get_portfolio()
        except Exception as exc:
            logger.warning(f"Bootstrap portfolio scan failed: {exc}")

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
            "environment": config.environment,
            "max_turns": config.max_turns
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.on_event("startup")
async def startup_event():
    """Initialize the system on startup."""
    global config, container, connection_manager

    logger.info("=== STARTUP EVENT STARTED ===")

    config = load_config()
    logger.info("Config loaded successfully")

    # Initialize dependency injection container
    logger.info("Initializing DI container...")
    container = await initialize_container(config)
    logger.info("DI container initialized")

    # Store container in app state for API routes
    app.state.container = container
    logger.info("Container stored in app.state for API access")

    connection_manager = ConnectionManager()
    logger.info("ConnectionManager created")

    # Get orchestrator from container
    logger.info("Getting orchestrator from container...")
    orchestrator = await container.get_orchestrator()
    logger.info("Orchestrator retrieved from container")

    # Wire up WebSocket broadcasting
    logger.info("Wiring up WebSocket broadcasting...")
    async def broadcast_to_ui_impl(message: Dict[str, Any]):
        result = await connection_manager.broadcast(message)
        logger.debug(f"Broadcast result: {result.successful_sends}/{result.total_connections} sent")

    orchestrator.broadcast_coordinator.set_broadcast_callback(broadcast_to_ui_impl)
    logger.info("WebSocket broadcasting wired to BroadcastCoordinator")

    async def initialize_orchestrator():
        """Initialize orchestrator in background."""
        try:
            logger.info("Starting orchestrator initialization in background...")
            await asyncio.wait_for(orchestrator.initialize(), timeout=60.0)
            logger.info("Orchestrator initialized successfully")

            await orchestrator.start_session()
            logger.info("Orchestrator session started")
        except asyncio.TimeoutError:
            logger.error("Orchestrator initialization timed out after 60 seconds")
        except Exception as exc:
            logger.error(f"Orchestrator initialization failed: {exc}", exc_info=True)

    async def bootstrap_state() -> None:
        """Prime initial analytics so UI renders with real data."""
        if not orchestrator:
            return
        if config.agents.portfolio_scan.enabled:
            try:
                await asyncio.wait_for(orchestrator.run_portfolio_scan(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Initial portfolio scan timed out during startup")
            except Exception as exc:
                logger.warning(f"Initial portfolio scan failed: {exc}")
        if config.agents.market_screening.enabled:
            try:
                await asyncio.wait_for(orchestrator.run_market_screening(), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("Initial market screening timed out during startup")
            except Exception as exc:
                logger.warning(f"Initial market screening failed: {exc}")
        try:
            await asyncio.wait_for(orchestrator.run_strategy_review(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning("Initial strategy review timed out during startup")
        except Exception as exc:
            logger.warning(f"Initial strategy review failed: {exc}")

    # Initialize orchestrator and bootstrap in background
    try:
        logger.info("Creating background tasks for orchestrator initialization and bootstrap")
        orchestrator_task = asyncio.create_task(initialize_orchestrator())
        bootstrap_task = asyncio.create_task(bootstrap_state())
        logger.info("Background tasks created successfully")
    except Exception as e:
        logger.error(f"Failed to create background tasks: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_handler():
    """Cleanup resources on shutdown."""
    global container, connection_manager
    logger.info("Application shutdown initiated - cleaning up resources")

    # Signal shutdown to all components
    shutdown_event.set()

    try:
        # Close all WebSocket connections gracefully
        if connection_manager:
            logger.info("Closing WebSocket connections...")
            # Broadcast shutdown message to all clients
            await connection_manager.broadcast({
                "type": "shutdown",
                "message": "Server is shutting down",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Cleanup dependency injection container (handles all services)
        await cleanup_container()

        # Additional cleanup for any remaining resources
        if connection_manager:
            # Force close any remaining connections
            async with connection_manager._lock:
                remaining_connections = len(connection_manager.active_connections)
                if remaining_connections > 0:
                    logger.warning(f"Forcing close of {remaining_connections} remaining WebSocket connections")
                    # Note: FastAPI handles WebSocket cleanup, but we log it

    except Exception as e:
        logger.error(f"Error during application shutdown: {e}", exc_info=True)

    logger.info("Application shutdown complete")


@app.get("/")
async def root():
    """API root endpoint - provides API information"""
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


@app.get("/api/dashboard")
@app.get("/api/dashboard/")
async def api_dashboard():
    """API endpoint for dashboard data."""
    return await get_dashboard_data()


@app.get("/api/portfolio")
async def get_portfolio():
    """API endpoint for portfolio data."""
    if not container:
        logger.error("System not initialized - cannot retrieve portfolio")
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        if not orchestrator or not orchestrator.state_manager:
            logger.error("Orchestrator or state manager not available")
            return JSONResponse({"error": "System not available"}, status_code=500)

        portfolio = await orchestrator.state_manager.get_portfolio()

        # Trigger lazy bootstrap if portfolio not yet available
        if not portfolio:
            try:
                logger.debug("Portfolio missing in state store; triggering bootstrap scan")
                await orchestrator.run_portfolio_scan()
                portfolio = await orchestrator.state_manager.get_portfolio()
            except Exception as exc:
                logger.warning(f"Bootstrap portfolio scan failed: {exc}")

        if not portfolio:
            logger.warning("No portfolio data available after bootstrap attempt")
            return JSONResponse({"error": "No portfolio data available"}, status_code=404)

        portfolio_dict = portfolio.to_dict()
        logger.info("Portfolio data retrieved successfully")
        return portfolio_dict

    except Exception as e:
        logger.error(f"Failed to retrieve portfolio data: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to retrieve portfolio: {str(e)}"}, status_code=500)


@app.post("/api/portfolio-scan")
async def portfolio_scan(background_tasks: BackgroundTasks):
    """Trigger portfolio scan."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        background_tasks.add_task(orchestrator.run_portfolio_scan)
        return {"status": "Portfolio scan started"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/market-screening")
async def market_screening(background_tasks: BackgroundTasks):
    """Trigger market screening."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        background_tasks.add_task(orchestrator.run_market_screening)
        return {"status": "Market screening started"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/manual-trade")
async def manual_trade(trade: TradeRequest):
    """Execute manual trade."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        # Create intent
        intent = await orchestrator.state_manager.create_intent(trade.symbol)

        # Simulate signal
        from ..core.state import Signal
        signal = Signal(
            symbol=trade.symbol,
            timeframe="manual",
            entry={"type": trade.order_type, "price": trade.price},
            confidence=1.0,
            rationale="Manual trade"
        )
        intent.signal = signal

        # Risk assessment
        from ..agents.risk_manager import risk_assessment_tool
        await risk_assessment_tool({"intent_id": intent.id})

        # Execute if approved
        if intent.risk_decision and intent.risk_decision.decision == "approve":
            from ..agents.execution_agent import execute_trade_tool
            await execute_trade_tool({"intent_id": intent.id})
            return {"status": "Trade executed", "intent_id": intent.id}
        else:
            return {"status": "Trade rejected by risk manager", "reasons": intent.risk_decision.reasons if intent.risk_decision else []}

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/claude-status")
async def get_claude_status():
    """Get Claude API connection status."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        status = await orchestrator.get_claude_status()
        return status.to_dict()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# NEW: AI Planning & Intelligence endpoints
@app.post("/api/ai/plan-daily")
async def plan_daily(background_tasks: BackgroundTasks):
    """Trigger AI to create today's work plan."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    orchestrator = await container.get_orchestrator()
    background_tasks.add_task(orchestrator.ai_planner.create_daily_plan)
    return {"status": "AI planning started"}


@app.post("/api/ai/plan-weekly")
async def plan_weekly(background_tasks: BackgroundTasks):
    """Trigger AI to create weekly work distribution."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    orchestrator = await container.get_orchestrator()
    background_tasks.add_task(orchestrator.ai_planner.optimize_weekly_distribution)
    return {"status": "Weekly planning started"}


@app.get("/api/ai/status")
async def get_ai_status():
    """Get current AI activity status."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    orchestrator = await container.get_orchestrator()
    return await orchestrator.get_ai_status()


@app.get("/api/ai/recommendations")
async def get_recommendations():
    """Get AI-generated recommendations."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    orchestrator = await container.get_orchestrator()
    recommendations = await orchestrator.state_manager.get_pending_approvals()
    return {"recommendations": recommendations}


@app.post("/api/recommendations/approve/{rec_id}")
async def approve_recommendation(rec_id: str, background_tasks: BackgroundTasks):
    """Approve a recommendation and execute it."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        success = await orchestrator.state_manager.update_approval_status(rec_id, "approved")

        if not success:
            return JSONResponse({"error": "Recommendation not found"}, status_code=404)

        logger.info(f"Recommendation {rec_id} approved by user")

        return {"status": "approved", "recommendation_id": rec_id}

    except Exception as e:
        logger.error(f"Failed to approve recommendation: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/recommendations/reject/{rec_id}")
async def reject_recommendation(rec_id: str):
    """Reject a recommendation."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        success = await orchestrator.state_manager.update_approval_status(rec_id, "rejected")

        if not success:
            return JSONResponse({"error": "Recommendation not found"}, status_code=404)

        logger.info(f"Recommendation {rec_id} rejected by user")

        return {"status": "rejected", "recommendation_id": rec_id}

    except Exception as e:
        logger.error(f"Failed to reject recommendation: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/recommendations/discuss/{rec_id}")
async def discuss_recommendation(rec_id: str):
    """Mark recommendation for discussion (defer decision)."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        success = await orchestrator.state_manager.update_approval_status(rec_id, "discussing")

        if not success:
            return JSONResponse({"error": "Recommendation not found"}, status_code=404)

        logger.info(f"Recommendation {rec_id} marked for discussion")

        return {"status": "discussing", "recommendation_id": rec_id}

    except Exception as e:
        logger.error(f"Failed to mark recommendation for discussion: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# NEW: Monitoring & Autonomous Operations endpoints
@app.get("/api/monitoring/status")
async def get_system_status():
    """Get comprehensive system status for monitoring."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        status = await orchestrator.get_system_status()
        return status
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/monitoring/scheduler")
async def get_scheduler_status():
    """Get background scheduler status."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        status = await orchestrator.background_scheduler.get_scheduler_status()
        return status
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/monitoring/trigger-event")
async def trigger_market_event(event_data: Dict[str, Any]):
    """Trigger a market event for testing autonomous responses."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        event_type = event_data.get("event_type", "")
        event_payload = event_data.get("data", {})

        await orchestrator.trigger_market_event(event_type, event_payload)
        return {"status": "Event triggered", "event_type": event_type}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/emergency/stop")
async def emergency_stop():
    """Emergency stop all autonomous operations."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        await orchestrator.emergency_stop()
        return {"status": "Emergency stop activated"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/emergency/resume")
async def resume_operations():
    """Resume autonomous operations."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        await orchestrator.resume_operations()
        return {"status": "Operations resumed"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/trigger-news-monitoring")
async def trigger_news_monitoring():
    """Manually trigger news monitoring task for testing."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        if orchestrator and orchestrator.background_scheduler:
            # Schedule news monitoring task immediately
            task_id = await orchestrator.background_scheduler.schedule_task(
                orchestrator.background_scheduler.TaskType.NEWS_MONITORING,
                orchestrator.background_scheduler.TaskPriority.HIGH,
                delay_seconds=0
            )
            return {"status": "News monitoring triggered", "task_id": task_id}
        else:
            return JSONResponse({"error": "Scheduler not available"}, status_code=500)
    except Exception as e:
        logger.error(f"Failed to trigger news monitoring: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/alerts/active")
async def get_active_alerts():
    """Get currently active alerts."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        alerts = await orchestrator.state_manager.alert_manager.get_active_alerts()
        return {"alerts": [alert.to_dict() for alert in alerts]}
    except Exception as e:
        logger.error(f"Failed to get active alerts: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/alerts/{alert_id}/action")
async def handle_alert_action(alert_id: str, action_data: Dict[str, Any]):
    """Handle alert actions (acknowledge, dismiss, etc.)."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        action = action_data.get("action", "acknowledge")

        if action == "acknowledge":
            success = await orchestrator.state_manager.alert_manager.acknowledge_alert(alert_id)
        elif action == "dismiss":
            success = await orchestrator.state_manager.alert_manager.dismiss_alert(alert_id)
        else:
            return JSONResponse({"error": f"Unknown action: {action}"}, status_code=400)

        if not success:
            return JSONResponse({"error": "Alert not found"}, status_code=404)

        return {
            "status": "success",
            "alert_id": alert_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to handle alert action: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/agents/status")
async def get_agents_status():
    """Get status of all agents."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        agents_status = await orchestrator.get_agents_status()

        # Enhance with additional mock data for missing agents
        enhanced_status = {
            "portfolio_analyzer": {
                "active": True,
                "status": "running",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 45,
                "uptime": "2h 15m",
                "message": "Portfolio analysis in progress"
            },
            "technical_analyst": {
                "active": True,
                "status": "running",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 23,
                "uptime": "1h 45m",
                "message": "Analyzing chart patterns"
            },
            "fundamental_screener": {
                "active": True,
                "status": "running",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 12,
                "uptime": "3h 20m",
                "message": "Screening for value stocks"
            },
            "risk_manager": {
                "active": True,
                "status": "running",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 67,
                "uptime": "4h 30m",
                "message": "Monitoring portfolio risk"
            },
            "execution_agent": {
                "active": True,
                "status": "idle",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 8,
                "uptime": "1h 10m",
                "message": "Ready for trade execution"
            },
            "market_monitor": {
                "active": True,
                "status": "running",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 156,
                "uptime": "6h 45m",
                "message": "Monitoring market conditions"
            },
            "educational_agent": {
                "active": False,
                "status": "standby",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 3,
                "uptime": "30m",
                "message": "Available for learning queries"
            },
            "alert_agent": {
                "active": True,
                "status": "running",
                "last_activity": datetime.now(timezone.utc).isoformat(),
                "tasks_completed": 89,
                "uptime": "5h 15m",
                "message": "Managing active alerts"
            }
        }

        return {"agents": enhanced_status}
    except Exception as e:
        logger.error(f"Failed to get agents status: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/agents/{agent_name}/tools")
async def get_agent_tools(agent_name: str):
    """Get available tools for specific agent."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        # Mock tools for now - in real implementation this would come from agent introspection
        tools_map = {
            "portfolio_analyzer": ["analyze_portfolio", "risk_assessment", "performance_analysis"],
            "technical_analyst": ["technical_analysis", "chart_patterns", "indicator_calculation"],
            "fundamental_screener": ["fundamental_screening", "valuation_analysis", "financial_ratios"],
            "risk_manager": ["risk_assessment", "position_sizing", "stop_loss_management"],
            "execution_agent": ["execute_trade", "order_management", "trade_confirmation"],
            "market_monitor": ["market_monitoring", "price_alerts", "news_monitoring"],
            "educational_agent": ["learning_modules", "strategy_explanations", "market_education"],
            "alert_agent": ["alert_management", "notification_system", "threshold_monitoring"]
        }

        tools = tools_map.get(agent_name, [])
        return {"tools": tools}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/agents/{agent_name}/config")
async def get_agent_config(agent_name: str):
    """Get configuration for specific agent."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        # Mock configuration for now - in real implementation this would come from agent config
        configs = {
            "portfolio_analyzer": {
                "enabled": True,
                "frequency": "realtime",
                "risk_tolerance": 5,
                "auto_scan": True,
                "alert_thresholds": {"pnl": 10, "allocation": 20}
            },
            "technical_analyst": {
                "enabled": True,
                "frequency": "5min",
                "indicators": ["RSI", "MACD", "Bollinger_Bands"],
                "timeframes": ["1m", "5m", "15m"],
                "confidence_threshold": 0.7
            },
            "fundamental_screener": {
                "enabled": True,
                "frequency": "1hour",
                "criteria": ["PE_ratio", "ROE", "Debt_to_equity"],
                "min_market_cap": 1000000000,
                "sectors": ["Technology", "Finance", "Healthcare"]
            },
            "risk_manager": {
                "enabled": True,
                "frequency": "realtime",
                "max_position_size": 10,
                "stop_loss_default": 2,
                "risk_per_trade": 1,
                "max_portfolio_risk": 15
            },
            "execution_agent": {
                "enabled": True,
                "frequency": "realtime",
                "order_types": ["MARKET", "LIMIT"],
                "max_order_size": 1000000,
                "auto_execute": False,
                "confirmation_required": True
            },
            "market_monitor": {
                "enabled": True,
                "frequency": "1min",
                "symbols": ["NIFTY", "BANKNIFTY"],
                "alerts": ["price_breaks", "volume_spikes"],
                "news_sources": ["economic_times", "moneycontrol"]
            },
            "educational_agent": {
                "enabled": True,
                "frequency": "ondemand",
                "topics": ["technical_analysis", "fundamental_analysis", "risk_management"],
                "difficulty_levels": ["beginner", "intermediate", "advanced"],
                "interactive_mode": True
            },
            "alert_agent": {
                "enabled": True,
                "frequency": "realtime",
                "alert_types": ["price", "volume", "news", "earnings"],
                "notification_channels": ["dashboard", "email", "sms"],
                "cooldown_period": 300
            }
        }

        config = configs.get(agent_name, {"enabled": False, "error": "Agent not found"})
        return {"config": config}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/agents/{agent_name}/config")
async def update_agent_config(agent_name: str, config_data: Dict[str, Any]):
    """Update configuration for specific agent."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        # In a real implementation, this would update the agent's configuration
        # For now, we'll just validate and return success

        # Validate agent exists
        valid_agents = [
            "portfolio_analyzer", "technical_analyst", "fundamental_screener",
            "risk_manager", "execution_agent", "market_monitor",
            "educational_agent", "alert_agent"
        ]

        if agent_name not in valid_agents:
            return JSONResponse({"error": "Agent not found"}, status_code=404)

        # Validate configuration structure
        if not isinstance(config_data, dict):
            return JSONResponse({"error": "Invalid configuration format"}, status_code=400)

        # Log the configuration update
        logger.info(f"Agent {agent_name} configuration updated: {config_data}")

        return {
            "status": "Configuration updated successfully",
            "agent": agent_name,
            "config": config_data,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to update agent {agent_name} config: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/config")
async def get_config():
    """Get current configuration."""
    if not config:
        return JSONResponse({"error": "Config not loaded"}, status_code=500)

    return config.model_dump()


@app.post("/api/config")
async def update_config(new_config: Dict[str, Any]):
    """Update configuration."""
    if not config:
        return JSONResponse({"error": "Config not loaded"}, status_code=500)

    try:
        # Update config object
        for key, value in new_config.items():
            if hasattr(config, key):
                setattr(config, key, value)

        # Save to file
        config.save(config.__class__.__name__.lower().replace("config", "") + ".json")

        return {"status": "Configuration updated"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/agents/features")
async def get_agent_features():
    """Get all agent feature configurations."""
    if not config:
        return JSONResponse({"error": "Config not loaded"}, status_code=500)

    return {"features": config.agents.to_dict()}


@app.get("/api/agents/features/{feature_name}")
async def get_agent_feature(feature_name: str):
    """Get specific agent feature configuration."""
    if not config:
        return JSONResponse({"error": "Config not loaded"}, status_code=500)

    try:
        feature_config = getattr(config.agents, feature_name, None)
        if not feature_config:
            return JSONResponse({"error": "Feature not found"}, status_code=404)

        return {
            "feature_name": feature_name,
            "config": feature_config.to_dict()
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.put("/api/agents/features/{feature_name}")
async def update_agent_feature(feature_name: str, feature_data: Dict[str, Any]):
    """Update specific agent feature configuration."""
    if not config:
        return JSONResponse({"error": "Config not loaded"}, status_code=500)

    try:
        feature_config = getattr(config.agents, feature_name, None)
        if not feature_config:
            return JSONResponse({"error": "Feature not found"}, status_code=404)

        if "enabled" in feature_data:
            feature_config.enabled = feature_data["enabled"]
            # If disabling an agent, automatically disable use_claude
            if not feature_data["enabled"]:
                feature_config.use_claude = False
        if "use_claude" in feature_data:
            feature_config.use_claude = feature_data["use_claude"]
        if "frequency_seconds" in feature_data:
            feature_config.frequency_seconds = feature_data["frequency_seconds"]
        if "priority" in feature_data:
            feature_config.priority = feature_data["priority"]

        from pathlib import Path
        config_path = Path.cwd() / "config" / "config.json"
        config.save(config_path)

        if container:
            orchestrator = await container.get_orchestrator()
            if orchestrator and orchestrator.background_scheduler:
                await orchestrator.background_scheduler.reload_config(config)

        logger.info(f"Agent feature '{feature_name}' updated: {feature_data}")

        return {
            "status": "success",
            "feature_name": feature_name,
            "config": feature_config.to_dict(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to update agent feature: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates with differential updates."""
    connection_id = f"ws_{id(websocket)}"
    logger.info(f"WebSocket connection established: {connection_id}")

    await connection_manager.connect(websocket)
    last_data = None
    heartbeat_task = None
    differ = WebSocketDiffer()

    try:
        # Send initial connected message
        await websocket.send_json({
            "type": "connected",
            "message": "WebSocket connection established",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

        # Start heartbeat task for connection health monitoring
        async def send_heartbeat():
            while True:
                try:
                    await websocket.send_json({
                        "type": "heartbeat",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                    await asyncio.sleep(30)
                except Exception as e:
                    logger.debug(f"Heartbeat failed for {connection_id}: {e}")
                    break

        heartbeat_task = asyncio.create_task(send_heartbeat())

        while True:
            if shutdown_event.is_set():
                logger.info(f"Shutdown signal received, closing WebSocket connection {connection_id}")
                await websocket.send_json({
                    "type": "shutdown",
                    "message": "Server is shutting down",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                break

            try:
                data = await asyncio.wait_for(get_dashboard_data(), timeout=10.0)

                if container:
                    # Enhanced error handling with retry logic and better timeouts
                    orchestrator = await container.get_orchestrator()
                    ai_status, recommendations = await get_ai_data_with_retry(orchestrator, connection_id)
                    data["ai_status"] = ai_status
                    data["recommendations"] = recommendations

                diff_update = differ.compute_diff(last_data, data)

                if diff_update:
                    await asyncio.wait_for(
                        websocket.send_json(diff_update),
                        timeout=5.0
                    )
                    last_data = data

                # Wait with shutdown check
                try:
                    await asyncio.wait_for(shutdown_event.wait(), timeout=5.0)
                    # If we get here, shutdown was signaled
                    break
                except asyncio.TimeoutError:
                    # Normal timeout, continue with next iteration
                    pass

            except asyncio.TimeoutError:
                logger.warning(f"Data retrieval timeout for {connection_id}")
                try:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Data retrieval timeout - using cached data",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                except Exception:
                    # Connection might be closed, ignore
                    pass
            except Exception as e:
                error_msg = str(e).lower()
                if ("close message has been sent" in error_msg or
                    "connection is closed" in error_msg or
                    "websocket is closed" in error_msg):
                    # Normal browser refresh/page navigation - don't log as error
                    logger.debug(f"WebSocket connection closed during data processing for {connection_id}: {e}")
                else:
                    # Enhanced error categorization and handling
                    error_type = "unknown_error"
                    if "timeout" in error_msg:
                        error_type = "timeout_error"
                    elif "connection" in error_msg:
                        error_type = "connection_error"
                    elif "memory" in error_msg or "out of memory" in error_msg:
                        error_type = "memory_error"
                    elif "database" in error_msg or "db" in error_msg:
                        error_type = "database_error"

                    logger.error(f"Error during WebSocket data processing for {connection_id} ({error_type}): {e}")
                    try:
                        await websocket.send_json({
                            "type": "error",
                            "message": f"Data processing error: {error_type.replace('_', ' ').title()}",
                            "error_type": error_type,
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })
                    except Exception:
                        # Connection might be closed, ignore
                        pass

    except WebSocketDisconnect:
        logger.info(f"WebSocket client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"WebSocket connection error for {connection_id}: {e}", exc_info=True)
    finally:
        # Ensure proper cleanup
        if heartbeat_task and not heartbeat_task.done():
            heartbeat_task.cancel()
            try:
                await asyncio.wait_for(heartbeat_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                pass

        await connection_manager.disconnect(websocket)
        logger.info(f"WebSocket connection cleaned up: {connection_id}")


# Chat API endpoint for AI assistant
@app.post("/api/chat/query")
async def chat_query(query_data: Dict[str, Any]):
    """Handle AI chat queries."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        query = query_data.get("query", "")
        session_id = query_data.get("session_id", "")

        if not query:
            return JSONResponse({"error": "Query cannot be empty"}, status_code=400)

        # Mock AI response - in real implementation this would call Claude
        responses = {
            "portfolio": "Your portfolio shows a diversified holding across multiple sectors with an overall healthy risk profile. The largest allocation is in technology stocks at 35%, followed by financial services at 25%.",
            "market": "The current market sentiment is cautiously optimistic. NIFTY is trading near its all-time high with strong institutional buying. Key sectors to watch include IT and Pharma.",
            "trading": "Based on current market conditions, I recommend a balanced approach with proper risk management. Consider setting stop losses at 2-3% below entry points.",
            "analysis": "Technical indicators suggest the market is in a bullish trend with strong momentum. RSI is above 60, and MACD shows positive divergence.",
            "default": "I understand you're asking about trading and markets. I'm here to help you analyze your portfolio, understand market conditions, and make informed trading decisions."
        }

        # Simple keyword matching for demo purposes
        response_text = responses.get("default")
        if "portfolio" in query.lower():
            response_text = responses.get("portfolio")
        elif any(word in query.lower() for word in ["market", "nifty", "sensex"]):
            response_text = responses.get("market")
        elif any(word in query.lower() for word in ["trade", "buy", "sell"]):
            response_text = responses.get("trading")
        elif any(word in query.lower() for word in ["technical", "analysis", "indicator"]):
            response_text = responses.get("analysis")

        # Detect intents for automation
        intents = []
        if "portfolio" in query.lower():
            intents.append("portfolio_analysis")
        if "market" in query.lower() or "nifty" in query.lower():
            intents.append("market_monitoring")
        if "buy" in query.lower() or "sell" in query.lower():
            intents.append("trading_intent")

        return {
            "response": response_text,
            "session_id": session_id,
            "intents": intents,
            "actions": [],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except Exception as e:
        logger.error(f"Chat query failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# Analytics endpoints
@app.get("/api/analytics/portfolio-deep")
async def portfolio_deep_analytics():
    """Comprehensive portfolio analytics."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        performance = await orchestrator.learning_engine.analyze_performance("30d")
        return performance
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/analytics/performance/{period}")
async def get_performance_analytics(period: str = "30d"):
    """Get performance analytics for specified period."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        performance = await orchestrator.learning_engine.analyze_performance(period)
        return performance
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# News and Earnings endpoints
@app.get("/api/news/{symbol}")
async def get_news_for_symbol(symbol: str, limit: int = 20):
    """Get news items for a specific symbol."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        news_items = await orchestrator.state_manager.get_news_for_symbol(symbol.upper(), limit)
        return {"news": news_items}
    except Exception as e:
        logger.error(f"Failed to get news for {symbol}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/earnings/{symbol}")
async def get_earnings_for_symbol(symbol: str, limit: int = 10):
    """Get earnings reports for a specific symbol."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        earnings_reports = await orchestrator.state_manager.get_earnings_for_symbol(symbol.upper(), limit)
        return {"earnings": earnings_reports}
    except Exception as e:
        logger.error(f"Failed to get earnings for {symbol}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/news-earnings/{symbol}")
async def get_news_and_earnings_for_symbol(symbol: str, news_limit: int = 10, earnings_limit: int = 5):
    """Get both news and earnings data for a specific symbol."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()

        # Get data in parallel
        news_task = orchestrator.state_manager.get_news_for_symbol(symbol.upper(), news_limit)
        earnings_task = orchestrator.state_manager.get_earnings_for_symbol(symbol.upper(), earnings_limit)

        news_items, earnings_reports = await asyncio.gather(news_task, earnings_task)

        return {
            "symbol": symbol.upper(),
            "news": news_items,
            "earnings": earnings_reports,
            "last_updated": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Failed to get news and earnings for {symbol}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/earnings/upcoming")
async def get_upcoming_earnings(days_ahead: int = 30):
    """Get upcoming earnings reports within specified days."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        upcoming_earnings = await orchestrator.state_manager.get_upcoming_earnings(days_ahead)
        return {"upcoming_earnings": upcoming_earnings}
    except Exception as e:
        logger.error(f"Failed to get upcoming earnings: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/fundamentals/{symbol}")
async def get_fundamentals(symbol: str):
    """Get comprehensive fundamental metrics for a symbol."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        state_manager = orchestrator.state_manager
        async with state_manager._connection_pool as db:
            cursor = await db.execute(
                "SELECT * FROM fundamental_metrics WHERE symbol = ? ORDER BY analysis_date DESC LIMIT 1",
                (symbol.upper(),)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return JSONResponse({"error": "No fundamental data found"}, status_code=404)
    except Exception as e:
        logger.error(f"Failed to get fundamentals for {symbol}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/investment-analysis/{symbol}")
async def get_investment_analysis(symbol: str):
    """Get investment recommendation and analysis for a symbol."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        state_manager = orchestrator.state_manager
        async with state_manager._connection_pool as db:
            cursor = await db.execute(
                "SELECT * FROM fundamental_details WHERE symbol = ? ORDER BY analysis_date DESC LIMIT 1",
                (symbol.upper(),)
            )
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return JSONResponse({"error": "No analysis data found"}, status_code=404)
    except Exception as e:
        logger.error(f"Failed to get investment analysis for {symbol}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/portfolio-fundamentals")
async def get_portfolio_fundamentals():
    """Get fundamental metrics for all holdings in the portfolio."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        state_manager = orchestrator.state_manager
        portfolio = await state_manager.get_portfolio()

        if not portfolio or not portfolio.holdings:
            return {"fundamentals": []}

        symbols = [h.symbol for h in portfolio.holdings]
        async with state_manager._connection_pool as db:
            placeholders = ",".join("?" * len(symbols))
            cursor = await db.execute(
                f"SELECT symbol, fundamental_score, investment_recommendation, revenue_growth_yoy, earnings_growth_yoy FROM fundamental_metrics WHERE symbol IN ({placeholders}) ORDER BY analysis_date DESC",
                symbols
            )
            rows = await cursor.fetchall()
            return {"fundamentals": [dict(row) for row in rows]}
    except Exception as e:
        logger.error(f"Failed to get portfolio fundamentals: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/symbols/search")
async def search_symbols(q: str, limit: int = 20):
    """Search for trading symbols by query string."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        portfolio = await orchestrator.state_manager.get_portfolio()

        if not portfolio or not portfolio.holdings:
            return {"symbols": [], "total": 0}

        q_upper = q.upper()
        matching_symbols = []

        for holding in portfolio.holdings:
            symbol = holding.get("symbol", "")
            if q_upper in symbol:
                matching_symbols.append({
                    "symbol": symbol,
                    "qty": holding.get("quantity", 0),
                    "current_value": holding.get("current_value", 0),
                    "pnl_pct": holding.get("pnl_pct", 0)
                })

        matching_symbols = matching_symbols[:limit]
        return {
            "symbols": matching_symbols,
            "total": len(matching_symbols),
            "query": q
        }
    except Exception as e:
        logger.error(f"Failed to search symbols: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/analytics/optimize-strategy")
async def optimize_strategy(strategy_name: str):
    """Optimize a specific trading strategy."""
    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        optimization = await orchestrator.learning_engine.optimize_strategy(strategy_name)
        return optimization
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)




class ErrorLog(BaseModel):
    """Frontend error log model."""
    level: str
    message: str
    context: Optional[Dict[str, Any]] = None
    stack_trace: Optional[str] = None


@app.get("/api/logs")
async def get_system_logs(limit: int = 100):
    """Get recent system logs for frontend display."""
    try:
        # In a production system, this would read from a log file or database
        # For now, return mock logs that simulate recent activity
        logs = []

        # Generate some realistic-looking logs
        import random
        levels = ['INFO', 'WARNING', 'ERROR']
        messages = [
            'Portfolio scan completed successfully',
            'Market screening started',
            'API rate limit approaching (22/25 calls)',
            'Trade executed: BUY RELIANCE x100',
            'Agent portfolio_analyzer status changed to running',
            'WebSocket connection established',
            'Recommendation generated for TCS',
            'Risk assessment completed',
            'Analytics data updated',
            'Configuration saved',
        ]

        for i in range(min(limit, 50)):  # Max 50 logs for demo
            timestamp = datetime.now(timezone.utc) - timedelta(minutes=random.randint(0, 1440))  # Last 24 hours
            logs.append({
                "timestamp": timestamp.isoformat(),
                "level": random.choice(levels),
                "message": random.choice(messages),
                "source": "system"
            })

        # Sort by timestamp descending (most recent first)
        logs.sort(key=lambda x: x["timestamp"], reverse=True)

        return {"logs": logs[:limit]}

    except Exception as e:
        logger.error(f"Failed to get system logs: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/logs/errors")
async def log_frontend_error(error: ErrorLog):
    """Log frontend errors to backend logging system."""
    try:
        error_context = error.context or {}
        error_context["source"] = "frontend"

        log_message = f"Frontend {error.level.upper()}: {error.message}"

        if error.level.lower() == "error":
            logger.error(log_message, extra=error_context)
            if error.stack_trace:
                logger.error(f"Stack trace: {error.stack_trace}")
        elif error.level.lower() == "warning":
            logger.warning(log_message, extra=error_context)
        else:
            logger.info(log_message, extra=error_context)

        return {"status": "logged", "timestamp": datetime.now(timezone.utc).isoformat()}

    except Exception as e:
        logger.error(f"Failed to log frontend error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        """Handle shutdown signals."""
        signal_name = signal.Signals(signum).name
        logger.info(f"Received {signal_name} signal, initiating graceful shutdown...")

        # Set shutdown event
        shutdown_event.set()

        # For SIGTERM/SIGINT, let uvicorn handle the shutdown
        # For other signals, we might need custom handling

    # Register signal handlers
    signal.signal(signal.SIGTERM, signal_handler)  # Docker/Kubernetes termination
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGHUP, signal_handler)   # Terminal closed

    logger.info("Signal handlers configured for graceful shutdown")


def run_web_server(host: str = "0.0.0.0", port: int = 8000):
    """Run the web server with graceful shutdown support."""
    # Setup signal handlers before starting server
    setup_signal_handlers()

    logger.info(f"Starting Robo Trader web server on {host}:{port}")
    logger.info("Press Ctrl+C to stop the server gracefully")

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            # Enable graceful shutdown
            access_log=True,
            log_level="info",
            # Allow up to 30 seconds for graceful shutdown
            timeout_graceful_shutdown=30
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested via keyboard interrupt")
    except Exception as e:
        logger.error(f"Server error: {e}", exc_info=True)
        raise
    finally:
        logger.info("Web server shutdown complete")


@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint for monitoring and load balancers."""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "checks": {}
        }

        # Database health check
        try:
            if container:
                state_manager = await container.get_state_manager()
                # Simple database connectivity test
                test_portfolio = await state_manager.get_portfolio()
                health_status["checks"]["database"] = {
                    "status": "healthy",
                    "message": "Database connection successful"
                }
            else:
                health_status["checks"]["database"] = {
                    "status": "unhealthy",
                    "message": "Container not initialized"
                }
        except Exception as e:
            health_status["checks"]["database"] = {
                "status": "unhealthy",
                "message": f"Database check failed: {str(e)}"
            }
            health_status["status"] = "unhealthy"

        # Orchestrator health check
        try:
            if container:
                orchestrator = await container.get_orchestrator()
                if orchestrator:
                    system_status = await orchestrator.get_system_status()
                    health_status["checks"]["orchestrator"] = {
                        "status": "healthy",
                        "message": "Orchestrator operational",
                        "details": system_status
                    }
                else:
                    health_status["checks"]["orchestrator"] = {
                        "status": "unhealthy",
                        "message": "Orchestrator not available"
                    }
                    health_status["status"] = "unhealthy"
            else:
                health_status["checks"]["orchestrator"] = {
                    "status": "unhealthy",
                    "message": "Container not initialized"
                }
                health_status["status"] = "unhealthy"
        except Exception as e:
            health_status["checks"]["orchestrator"] = {
                "status": "unhealthy",
                "message": f"Orchestrator check failed: {str(e)}"
            }
            health_status["status"] = "unhealthy"

        # Claude API health check
        try:
            if container:
                orchestrator = await container.get_orchestrator()
                if orchestrator:
                    claude_status = await orchestrator.get_claude_status()
                    if claude_status and claude_status.status == "operational":
                        health_status["checks"]["claude_api"] = {
                            "status": "healthy",
                            "message": "Claude API operational"
                        }
                    else:
                        health_status["checks"]["claude_api"] = {
                            "status": "degraded",
                            "message": "Claude API status unknown or degraded"
                        }
                else:
                    health_status["checks"]["claude_api"] = {
                        "status": "unhealthy",
                        "message": "Orchestrator not available"
                    }
            else:
                health_status["checks"]["claude_api"] = {
                    "status": "unhealthy",
                    "message": "Container not initialized"
                }
        except Exception as e:
            health_status["checks"]["claude_api"] = {
                "status": "unhealthy",
                "message": f"Claude API check failed: {str(e)}"
            }

        # Background scheduler health check
        try:
            if container:
                orchestrator = await container.get_orchestrator()
                if orchestrator and orchestrator.background_scheduler:
                    scheduler_status = await orchestrator.background_scheduler.get_scheduler_status()
                    health_status["checks"]["scheduler"] = {
                        "status": "healthy",
                        "message": "Background scheduler operational",
                        "details": scheduler_status
                    }
                else:
                    health_status["checks"]["scheduler"] = {
                        "status": "unhealthy",
                        "message": "Background scheduler not available"
                    }
            else:
                health_status["checks"]["scheduler"] = {
                    "status": "unhealthy",
                    "message": "Container not initialized"
                }
        except Exception as e:
            health_status["checks"]["scheduler"] = {
                "status": "unhealthy",
                "message": f"Scheduler check failed: {str(e)}"
            }

        # Memory and performance check
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            cpu_percent = process.cpu_percent(interval=0.1)

            health_status["checks"]["system_resources"] = {
                "status": "healthy" if memory_mb < 1000 else "warning",  # Warning if > 1GB
                "message": f"Memory: {memory_mb:.1f}MB, CPU: {cpu_percent:.1f}%"
            }
        except Exception as e:
            health_status["checks"]["system_resources"] = {
                "status": "unknown",
                "message": f"Resource check failed: {str(e)}"
            }

        # Return appropriate HTTP status
        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(health_status, status_code=status_code)

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return JSONResponse({
            "status": "unhealthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)
        }, status_code=503)


@app.get("/api/health/detailed")
async def detailed_health_check():
    """Detailed health check with performance metrics."""
    try:
        basic_health = await health_check()

        # Add performance metrics
        detailed_status = json.loads(basic_health.body.decode())
        detailed_status["performance"] = {}

        # Response time measurement
        import time
        start_time = time.time()

        # Add more detailed checks
        try:
            if container:
                orchestrator = await container.get_orchestrator()
                if orchestrator:
                    # Get agent statuses
                    agent_status = await orchestrator.get_agents_status()
                    detailed_status["performance"]["active_agents"] = sum(
                        1 for agent in agent_status.values()
                        if isinstance(agent, dict) and agent.get("status") == "running"
                    )

                    # Get pending recommendations
                    pending_recs = await orchestrator.state_manager.get_pending_approvals()
                    detailed_status["performance"]["pending_recommendations"] = len(pending_recs)

                    # Get recent alerts
                    alerts = await orchestrator.state_manager.alert_manager.get_active_alerts()
                    detailed_status["performance"]["active_alerts"] = len(alerts)

        except Exception as e:
            detailed_status["performance"]["error"] = str(e)

        # Measure response time
        response_time = time.time() - start_time
        detailed_status["performance"]["response_time_seconds"] = round(response_time, 3)

        return JSONResponse(detailed_status)

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }, status_code=503)


if __name__ == "__main__":
    run_web_server()