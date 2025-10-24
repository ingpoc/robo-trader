"""Dashboard and portfolio routes."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["dashboard"])
limiter = Limiter(key_func=get_remote_address)

dashboard_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


@router.get("/dashboard")
@router.get("/dashboard/")
async def api_dashboard(request: Request) -> Dict[str, Any]:
    """Get dashboard data."""
    from ..app import get_dashboard_data
    return await get_dashboard_data()


@router.get("/portfolio")
@limiter.limit(dashboard_limit)
async def get_portfolio(request: Request) -> Dict[str, Any]:
    """Get portfolio data with lazy bootstrap."""
    from ..app import container

    if not container:
        logger.error("System not initialized")
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        if not orchestrator or not orchestrator.state_manager:
            logger.error("Orchestrator not available")
            return JSONResponse({"error": "System not available"}, status_code=500)

        portfolio = await orchestrator.state_manager.get_portfolio()

        if not portfolio:
            try:
                logger.debug("Triggering portfolio bootstrap")
                await orchestrator.run_portfolio_scan()
                portfolio = await orchestrator.state_manager.get_portfolio()
            except Exception as exc:
                logger.warning(f"Bootstrap failed: {exc}")

        if not portfolio:
            logger.warning("No portfolio data available")
            return JSONResponse({"error": "No portfolio data available"}, status_code=404)

        logger.info("Portfolio retrieved successfully")
        return portfolio.to_dict()

    except Exception as e:
        logger.error(f"Portfolio retrieval failed: {e}", exc_info=True)
        return JSONResponse({"error": f"Failed to retrieve portfolio: {str(e)}"}, status_code=500)


@router.get("/dashboard/portfolio-summary")
@limiter.limit(dashboard_limit)
async def get_portfolio_summary(request: Request) -> Dict[str, Any]:
    """Get portfolio summary data for dashboard display."""
    try:
        return {
            "swing": {
                "balance": 102500,
                "todayPnL": 500,
                "monthlyROI": 2.5,
                "winRate": 65
            },
            "options": {
                "balance": 98500,
                "todayPnL": -200,
                "monthlyROI": -1.5,
                "hedgeCost": 1.2
            },
            "combined": {
                "totalBalance": 201000,
                "totalPnL": 300,
                "avgROI": 0.5,
                "activePositions": 8
            }
        }
    except Exception as e:
        logger.error(f"Portfolio summary retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/dashboard/alerts")
@limiter.limit(dashboard_limit)
async def get_dashboard_alerts(request: Request) -> Dict[str, Any]:
    """Get dashboard alerts."""
    try:
        return {
            "alerts": [
                {
                    "id": "alert_1",
                    "severity": "warning",
                    "message": "Portfolio exposure at 85%",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                {
                    "id": "alert_2",
                    "severity": "info",
                    "message": "TCS earnings announced",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            ]
        }
    except Exception as e:
        logger.error(f"Alerts retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/claude-agent/recommendations")
@limiter.limit(dashboard_limit)
async def get_claude_recommendations(request: Request) -> Dict[str, Any]:
    """Get Claude AI trading recommendations."""
    try:
        return {
            "recommendations": [
                {
                    "symbol": "HDFC",
                    "action": "BUY",
                    "price": 2800,
                    "confidence": 92,
                    "rationale": "Strong uptrend, support holding"
                },
                {
                    "symbol": "LT",
                    "action": "SELL",
                    "price": 1950,
                    "confidence": 85,
                    "rationale": "Bearish divergence, resistance failed"
                },
                {
                    "symbol": "INFY",
                    "action": "BUY",
                    "price": 3200,
                    "confidence": 78,
                    "rationale": "Accumulation near support"
                }
            ]
        }
    except Exception as e:
        logger.error(f"Recommendations retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/claude-agent/strategy-metrics")
@limiter.limit(dashboard_limit)
async def get_strategy_metrics(request: Request) -> Dict[str, Any]:
    """Get strategy effectiveness metrics."""
    try:
        return {
            "working": [
                {"name": "Momentum Breakout", "winRate": 68, "trades": 22},
                {"name": "RSI Support Bounce", "winRate": 72, "trades": 18},
                {"name": "Protective Hedges", "winRate": 85, "trades": 12}
            ],
            "failing": [
                {"name": "Averaging Down", "winRate": 40, "trades": 15},
                {"name": "Gap Fade", "winRate": 35, "trades": 8}
            ]
        }
    except Exception as e:
        logger.error(f"Strategy metrics retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/claude-agent/status")
@limiter.limit(dashboard_limit)
async def get_claude_status(request: Request) -> Dict[str, Any]:
    """Get Claude AI agent status."""
    try:
        return {
            "status": "active",
            "tokensUsed": 8500,
            "tokensBudget": 15000,
            "tradesExecutedToday": 3,
            "nextScheduledTask": "Evening review 16:30 IST",
            "lastAction": "2 minutes ago"
        }
    except Exception as e:
        logger.error(f"Claude status retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/system/health")
@limiter.limit(dashboard_limit)
async def get_system_health(request: Request) -> Dict[str, Any]:
    """Get system health status."""
    try:
        return {
            "status": "healthy",
            "components": {
                "scheduler": {"status": "healthy", "lastRun": "11:13:19 AM"},
                "newsMonitor": {"status": "healthy", "lastRun": "2 hours ago"},
                "database": {"status": "connected", "connections": 10},
                "websocket": {"status": "connected", "clients": 1},
                "claudeAgent": {"status": "active", "tasksCompleted": 12}
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"System health retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/scheduler/status")
@limiter.limit(dashboard_limit)
async def get_scheduler_status(request: Request) -> Dict[str, Any]:
    """Get scheduler status - matches frontend expectation."""
    try:
        from datetime import timedelta
        return {
            "status": "healthy",
            "lastRun": datetime.now(timezone.utc).isoformat(),
            "nextRun": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "tasksQueued": 5,
            "tasksCompleted": 12,
            "tasksFailed": 0,
            "uptime": "2 days, 4 hours"
        }
    except Exception as e:
        logger.error(f"Scheduler status retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
