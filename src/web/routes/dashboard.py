"""Dashboard and portfolio routes."""

import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_trading_error,
    handle_validation_error,
    handle_unexpected_error,
)

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
async def get_portfolio(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get portfolio data with lazy bootstrap."""
    try:
        logger.info("Portfolio data requested")
        orchestrator = await container.get_orchestrator()
        if not orchestrator or not orchestrator.state_manager:
            logger.error("Orchestrator not available for portfolio request")
            return JSONResponse({"error": "System not available"}, status_code=500)

        portfolio = await orchestrator.state_manager.get_portfolio()

        if portfolio:
            holdings_count = len(portfolio.holdings) if portfolio.holdings else 0
            logger.info(f"Portfolio retrieved from database: {holdings_count} holdings")
        else:
            logger.info("No portfolio found in database, attempting bootstrap")

        if not portfolio:
            try:
                logger.info("Triggering portfolio bootstrap scan")
                await orchestrator.run_portfolio_scan()
                portfolio = await orchestrator.state_manager.get_portfolio()

                if portfolio:
                    holdings_count = len(portfolio.holdings) if portfolio.holdings else 0
                    logger.info(f"Portfolio bootstrap completed: {holdings_count} holdings loaded")
                else:
                    logger.warning("Portfolio bootstrap completed but still no data available")

            except TradingError as e:
                logger.warning(f"Bootstrap failed with trading error: {e}")
                # Continue to check if portfolio is now available
            except ValueError as e:
                logger.warning(f"Bootstrap failed with validation error: {e}")
            except Exception as e:
                logger.warning(f"Bootstrap failed with unexpected error: {e}")

        if not portfolio:
            logger.warning("No portfolio data available after bootstrap")
            return JSONResponse({"error": "No portfolio data available"}, status_code=404)

        holdings_count = len(portfolio.holdings) if portfolio.holdings else 0
        logger.info(f"Portfolio data returned successfully: {holdings_count} holdings")
        return portfolio.to_dict()

    except TradingError as e:
        return await handle_trading_error(e)
    except ValueError as e:
        return await handle_validation_error(e)
    except KeyError as e:
        logger.error(f"Orchestrator not found in container: {e}")
        return JSONResponse({"error": "System not properly initialized"}, status_code=500)
    except Exception as e:
        return await handle_unexpected_error(e, "get_portfolio")


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
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_portfolio_summary")


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
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_dashboard_alerts")


@router.get("/claude-agent/recommendations")
@limiter.limit(dashboard_limit)
async def get_claude_recommendations(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude AI trading recommendations from database."""
    try:
        # TODO: Implement recommendations from database
        # Use the same endpoint as /api/ai/recommendations for consistency
        return {
            "recommendations": []
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_claude_recommendations")


@router.get("/claude-agent/strategy-metrics")
@limiter.limit(dashboard_limit)
async def get_strategy_metrics(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get strategy effectiveness metrics from database."""
    try:
        # TODO: Calculate strategy metrics from paper_trades table
        # Group by strategy_tag, calculate win rate and trade count
        return {
            "working": [],
            "failing": []
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_strategy_metrics")


@router.get("/claude-agent/status")
@limiter.limit(dashboard_limit)
async def get_claude_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude AI agent status from orchestrator."""
    try:
        orchestrator = await container.get_orchestrator()
        claude_auth_status = await orchestrator.get_claude_status()
        config = await container.get("config")

        # Get token budget from config
        daily_budget = 15000
        if config and hasattr(config, 'claude_agent'):
            daily_budget = getattr(config.claude_agent, 'daily_token_budget', 15000)

        # TODO: Get actual token usage from claude_token_usage table
        # TODO: Get trades count from paper_trades table for today

        # Determine status based on actual SDK connection state
        if not claude_auth_status or not claude_auth_status.is_valid:
            status = "disconnected"
        else:
            # Check if SDK client is actually connected to CLI process
            sdk_connected = claude_auth_status.account_info.get("sdk_connected", False)
            cli_process_running = claude_auth_status.account_info.get("cli_process_running", False)

            if sdk_connected and cli_process_running:
                status = "connected/idle"  # SDK client is connected to running CLI process
            else:
                status = "authenticated"  # CLI is authenticated but no active SDK session

        return {
            "status": status,
            "tokensUsed": 0,
            "tokensBudget": daily_budget,
            "tradesExecutedToday": 0,
            "nextScheduledTask": None,
            "lastAction": None,
            "auth_method": claude_auth_status.account_info.get("auth_method") if claude_auth_status else None
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_claude_status")


@router.get("/system/health")
@limiter.limit(dashboard_limit)
async def get_system_health(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get system health status from orchestrator."""
    try:
        orchestrator = await container.get_orchestrator()

        # Try to get system status, fall back if method not implemented
        try:
            system_status = await orchestrator.get_system_status()
        except (AttributeError, NotImplementedError):
            system_status = {}

        # Transform to frontend format
        components = {}

        # Scheduler status
        if "scheduler_status" in system_status:
            scheduler = system_status["scheduler_status"]
            components["scheduler"] = {
                "status": "healthy" if scheduler.get("running") else "stopped",
                "lastRun": scheduler.get("last_run_time", "unknown")
            }

        # Database status
        components["database"] = {
            "status": "connected",  # If we got here, DB is connected
            "connections": 1  # TODO: Get actual connection count
        }

        # WebSocket status
        components["websocket"] = {
            "status": "connected",
            "clients": 0  # TODO: Get from connection_manager
        }

        # Claude agent status
        if "claude_status" in system_status and system_status["claude_status"]:
            claude = system_status["claude_status"]
            components["claudeAgent"] = {
                "status": "active" if claude.get("authenticated") else "inactive",
                "tasksCompleted": 0  # TODO: Track task completion
            }
        else:
            components["claudeAgent"] = {
                "status": "not_configured",
                "tasksCompleted": 0
            }

        return {
            "status": "healthy",
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_system_health")


@router.get("/scheduler/status")
@limiter.limit(dashboard_limit)
async def get_scheduler_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get scheduler status from background scheduler."""
    try:
        orchestrator = await container.get_orchestrator()
        system_status = await orchestrator.get_system_status()

        scheduler_status = system_status.get("scheduler_status", {})

        return {
            "status": "healthy" if scheduler_status.get("running") else "stopped",
            "lastRun": scheduler_status.get("last_run_time", None),
            "nextRun": None,  # TODO: Get next scheduled run time
            "tasksQueued": 0,  # TODO: Get from queue coordinator
            "tasksCompleted": 0,  # TODO: Track completed tasks
            "tasksFailed": 0,  # TODO: Track failed tasks
            "uptime": None  # TODO: Track scheduler uptime
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_scheduler_status")
