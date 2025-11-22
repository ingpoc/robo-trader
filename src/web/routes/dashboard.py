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

# Track server start time for uptime calculation
_server_start_time = datetime.now(timezone.utc)


def _empty_portfolio_summary() -> Dict[str, Any]:
    """Return empty portfolio summary structure when no accounts exist."""
    empty_strategy = {
        "balance": 0,
        "todayPnL": 0,
        "monthlyROI": 0,
        "activePositions": 0
    }
    return {
        "swing": empty_strategy,
        "options": empty_strategy,
        "combined": {
            "totalBalance": 0,
            "totalPnL": 0,
            "avgROI": 0,
            "activePositions": 0
        }
    }


def _calculate_strategy_metrics(
    accounts: list,
    positions_by_account: Dict[str, list],
    live_prices: Dict[str, float],
    strategy_type: str
) -> Dict[str, Any]:
    """Calculate portfolio metrics for a specific strategy type.

    Args:
        accounts: List of paper trading accounts
        positions_by_account: Dict mapping account_id to positions list
        live_prices: Dict mapping symbol to current price from Zerodha
        strategy_type: "swing" or "options" to filter accounts

    Returns:
        Dict with balance, todayPnL, monthlyROI, activePositions
    """
    total_balance = 0
    total_pnl = 0
    total_positions = 0
    total_initial_balance = 0

    for account in accounts:
        # Filter by strategy type
        if strategy_type.lower() not in account.account_name.lower():
            continue

        positions = positions_by_account.get(account.account_id, [])
        total_positions += len(positions)
        total_initial_balance += account.initial_balance

        # Calculate deployed capital and P&L using live prices
        deployed = 0
        position_pnl = 0

        for pos in positions:
            entry_value = pos.entry_price * pos.quantity
            deployed += entry_value

            # Get live price for P&L calculation
            current_price = live_prices.get(pos.symbol, pos.entry_price)
            current_value = current_price * pos.quantity

            if pos.position_type == "LONG":
                position_pnl += current_value - entry_value
            else:  # SHORT
                position_pnl += entry_value - current_value

        # Balance = initial balance - deployed + realized gains + unrealized P&L
        # Simplified: use current balance from account + position P&L
        total_balance += account.current_balance + position_pnl
        total_pnl += position_pnl

    # Calculate monthly ROI (simplified as % of initial balance)
    monthly_roi = 0
    if total_initial_balance > 0:
        monthly_roi = round((total_pnl / total_initial_balance) * 100, 2)

    return {
        "balance": round(total_balance, 2),
        "todayPnL": round(total_pnl, 2),
        "monthlyROI": monthly_roi,
        "activePositions": total_positions
    }


@router.get("/dashboard")
@router.get("/dashboard/")
async def api_dashboard(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get dashboard data."""
    try:
        # Get required dependencies from container
        orchestrator = await container.get_orchestrator()
        config = await container.get("config")

        # Use module-level initialization_status from app
        from ..app import initialization_status

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

        if not portfolio and orchestrator and config and hasattr(config, 'agents') and config.agents.portfolio_scan.enabled:
            try:
                logger.info("Triggering bootstrap portfolio scan")
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
                "max_turns": getattr(config, 'max_turns', 50) if config else 50
            },
            "initialization_status": initialization_status,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "api_dashboard")


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
async def get_portfolio_summary(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get portfolio summary data from paper trading accounts with live Zerodha prices."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        kite_service = await container.get("kite_connect_service")

        if not account_manager:
            return _empty_portfolio_summary()

        accounts = await account_manager.get_all_accounts()
        if not accounts:
            return _empty_portfolio_summary()

        # Collect all symbols and positions
        all_symbols = set()
        positions_by_account = {}

        for account in accounts:
            positions = await account_manager.get_open_positions(account.account_id)
            positions_by_account[account.account_id] = positions
            for pos in positions:
                all_symbols.add(pos.symbol)

        # Fetch all prices in one call (efficient)
        live_prices = {}
        if kite_service and all_symbols:
            live_prices = await kite_service.get_bulk_prices(list(all_symbols))

        # Calculate metrics by strategy type
        swing_data = _calculate_strategy_metrics(accounts, positions_by_account, live_prices, "swing")
        options_data = _calculate_strategy_metrics(accounts, positions_by_account, live_prices, "options")

        total_balance = swing_data["balance"] + options_data["balance"]
        total_pnl = swing_data["todayPnL"] + options_data["todayPnL"]
        total_positions = sum(len(p) for p in positions_by_account.values())

        return {
            "swing": swing_data,
            "options": options_data,
            "combined": {
                "totalBalance": total_balance,
                "totalPnL": total_pnl,
                "avgROI": round((swing_data["monthlyROI"] + options_data["monthlyROI"]) / 2, 2) if swing_data["balance"] or options_data["balance"] else 0,
                "activePositions": total_positions
            }
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Portfolio summary error: {e}")
        return _empty_portfolio_summary()


@router.get("/dashboard/alerts")
@limiter.limit(dashboard_limit)
async def get_dashboard_alerts(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get dynamic dashboard alerts based on portfolio state."""
    try:
        alerts = []
        account_manager = await container.get("paper_trading_account_manager")

        if account_manager:
            accounts = await account_manager.get_all_accounts()

            for account in accounts:
                positions = await account_manager.get_open_positions(account.account_id)

                # Alert: High portfolio exposure
                deployed = sum(p.entry_price * p.quantity for p in positions)
                exposure_pct = (deployed / account.initial_balance) * 100 if account.initial_balance > 0 else 0

                if exposure_pct > 80:
                    alerts.append({
                        "id": f"exposure_{account.account_id}",
                        "severity": "warning",
                        "message": f"Portfolio exposure at {exposure_pct:.0f}%",
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })

                # Alert: Positions near stop loss
                for pos in positions:
                    if hasattr(pos, 'stop_loss') and pos.stop_loss and hasattr(pos, 'current_price') and pos.current_price:
                        if pos.current_price <= pos.stop_loss * 1.02:  # Within 2% of stop loss
                            alerts.append({
                                "id": f"stoploss_{pos.trade_id}",
                                "severity": "critical",
                                "message": f"{pos.symbol} approaching stop loss",
                                "timestamp": datetime.now(timezone.utc).isoformat()
                            })

                # Alert: Large unrealized loss
                for pos in positions:
                    if hasattr(pos, 'unrealized_pnl_pct') and pos.unrealized_pnl_pct and pos.unrealized_pnl_pct < -10:
                        alerts.append({
                            "id": f"loss_{pos.trade_id}",
                            "severity": "warning",
                            "message": f"{pos.symbol} down {abs(pos.unrealized_pnl_pct):.1f}%",
                            "timestamp": datetime.now(timezone.utc).isoformat()
                        })

        return {"alerts": alerts[:10]}  # Limit to 10 alerts
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Dashboard alerts error: {e}")
        return {"alerts": []}


@router.get("/claude-agent/recommendations")
@limiter.limit(dashboard_limit)
async def get_claude_recommendations(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude AI trading recommendations from database."""
    try:
        db_state = await container.get("database_state_manager")
        if not db_state:
            return {"recommendations": []}

        # Get recent recommendations from database
        recommendations = await db_state.get_recommendations(limit=10)

        return {
            "recommendations": [
                {
                    "symbol": r.symbol,
                    "type": r.recommendation_type,
                    "confidence": r.confidence_score,
                    "reasoning": r.reasoning[:200] if r.reasoning else "",
                    "targetPrice": r.target_price,
                    "stopLoss": r.stop_loss,
                    "timeHorizon": r.time_horizon,
                    "riskLevel": r.risk_level
                }
                for r in recommendations
            ]
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Recommendations error: {e}")
        return {"recommendations": []}


@router.get("/claude-agent/strategy-metrics")
@limiter.limit(dashboard_limit)
async def get_strategy_metrics(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Calculate strategy effectiveness metrics from closed trades."""
    try:
        store = await container.get("paper_trading_store")
        if not store:
            return {"working": [], "failing": []}

        # Get all accounts and their closed trades
        accounts = await store.get_all_accounts()
        strategy_stats = {}

        for account in accounts:
            trades = await store.get_closed_trades(account.account_id, limit=100)

            for trade in trades:
                strategy = trade.strategy_rationale[:30] if trade.strategy_rationale else "Unknown"
                if strategy not in strategy_stats:
                    strategy_stats[strategy] = {"wins": 0, "losses": 0, "total_pnl": 0}

                if trade.realized_pnl and trade.realized_pnl > 0:
                    strategy_stats[strategy]["wins"] += 1
                else:
                    strategy_stats[strategy]["losses"] += 1
                strategy_stats[strategy]["total_pnl"] += trade.realized_pnl or 0

        # Classify strategies as working or failing
        working = []
        failing = []

        for strategy, stats in strategy_stats.items():
            total = stats["wins"] + stats["losses"]
            if total == 0:
                continue

            win_rate = (stats["wins"] / total) * 100

            entry = {
                "strategy": strategy,
                "trades": total,
                "winRate": round(win_rate, 1)
            }

            if win_rate >= 50:
                working.append(entry)
            else:
                failing.append(entry)

        # Sort by win rate and limit
        working.sort(key=lambda x: x["winRate"], reverse=True)
        failing.sort(key=lambda x: x["winRate"])

        return {"working": working[:5], "failing": failing[:5]}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        logger.error(f"Strategy metrics error: {e}")
        return {"working": [], "failing": []}


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
        connection_manager = await container.get("connection_manager")

        # Try to get system status, fall back if method not implemented
        try:
            system_status = await orchestrator.get_system_status()
        except (AttributeError, NotImplementedError):
            system_status = {}

        # Transform to frontend format
        components = {}

        # Scheduler status with real data
        if "scheduler_status" in system_status:
            scheduler = system_status["scheduler_status"]
            components["scheduler"] = {
                "status": scheduler.get("status", "unknown"),
                "lastRun": scheduler.get("lastRun", "unknown"),
                "activeJobs": scheduler.get("activeJobs", 0),
                "completedJobs": scheduler.get("completedJobs", 0),
                "totalSchedulers": scheduler.get("totalSchedulers", 0),
                "runningSchedulers": scheduler.get("runningSchedulers", 0)
            }
        else:
            components["scheduler"] = {
                "status": "unknown",
                "lastRun": "unknown",
                "activeJobs": 0,
                "completedJobs": 0
            }

        # Database status
        components["database"] = {
            "status": "connected",  # If we got here, DB is connected
            "connections": 1
        }

        # WebSocket status with real client count
        ws_clients = 0
        if connection_manager:
            try:
                ws_clients = len(connection_manager.active_connections)
            except (AttributeError, TypeError):
                ws_clients = 0
        components["websocket"] = {
            "status": "connected",
            "clients": ws_clients
        }

        # Claude agent status with real data
        if "claude_status" in system_status and system_status["claude_status"]:
            claude = system_status["claude_status"]
            components["claudeAgent"] = {
                "status": "active" if claude.get("authenticated") else "inactive",
                "tasksCompleted": claude.get("tasksCompleted", 0)
            }
        else:
            components["claudeAgent"] = {
                "status": "not_configured",
                "tasksCompleted": 0
            }

        # Calculate uptime
        uptime_seconds = int((datetime.now(timezone.utc) - _server_start_time).total_seconds())

        return {
            "status": "healthy",
            "components": components,
            "uptime_seconds": uptime_seconds,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_system_health")


@router.get("/status")
@limiter.limit(dashboard_limit)
async def get_system_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get overall system status - basic health and version information."""
    try:
        orchestrator = await container.get_orchestrator()

        # Calculate uptime
        uptime_seconds = int((datetime.now(timezone.utc) - _server_start_time).total_seconds())

        # Get scheduler status for queue info
        queue_status = "running"
        try:
            system_status = await orchestrator.get_system_status()
            scheduler = system_status.get("scheduler_status", {})
            if scheduler.get("status") == "error":
                queue_status = "error"
            elif scheduler.get("runningSchedulers", 0) == 0:
                queue_status = "idle"
        except Exception:
            queue_status = "unknown"

        # Get Claude status
        claude_status = "unknown"
        try:
            claude_auth = await orchestrator.get_claude_status()
            if claude_auth and claude_auth.is_valid:
                claude_status = "authenticated"
            else:
                claude_status = "not_configured"
        except Exception:
            claude_status = "unknown"

        status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
            "uptime_seconds": uptime_seconds,
            "components": {
                "api": {"status": "healthy"},
                "database": {"status": "connected"},
                "orchestrator": {"status": "running"},
                "queues": {"status": queue_status},
                "claude": {"status": claude_status}
            }
        }

        return status
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_system_status")


@router.get("/scheduler/status")
@limiter.limit(dashboard_limit)
async def get_scheduler_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get scheduler status from background scheduler with detailed metrics."""
    try:
        orchestrator = await container.get_orchestrator()
        system_status = await orchestrator.get_system_status()

        scheduler_status = system_status.get("scheduler_status", {})
        schedulers = scheduler_status.get("schedulers", [])

        # Calculate totals from all schedulers
        total_processed = sum(s.get("jobs_processed", 0) for s in schedulers)
        total_failed = sum(s.get("jobs_failed", 0) for s in schedulers)
        total_active = sum(s.get("active_jobs", 0) for s in schedulers)

        # Calculate success rate
        total_jobs = total_processed + total_failed
        success_rate = round((total_processed / total_jobs * 100), 1) if total_jobs > 0 else 100.0

        # Get running jobs
        running_jobs = []
        for s in schedulers:
            if s.get("current_task"):
                running_jobs.append({
                    "queue": s.get("name", s.get("scheduler_id", "unknown")),
                    "task_id": s["current_task"].get("task_id"),
                    "task_type": s["current_task"].get("task_type"),
                    "started_at": s["current_task"].get("started_at")
                })

        return {
            "status": scheduler_status.get("status", "unknown"),
            "lastRun": scheduler_status.get("lastRun"),
            "activeJobs": total_active,
            "tasksQueued": total_active,
            "tasksProcessed": total_processed,
            "tasksFailed": total_failed,
            "successRate": success_rate,
            "totalSchedulers": scheduler_status.get("totalSchedulers", len(schedulers)),
            "runningSchedulers": scheduler_status.get("runningSchedulers", 0),
            "runningJobs": running_jobs,
            "schedulers": [
                {
                    "id": s.get("scheduler_id"),
                    "name": s.get("name"),
                    "status": s.get("status"),
                    "processed": s.get("jobs_processed", 0),
                    "failed": s.get("jobs_failed", 0),
                    "active": s.get("active_jobs", 0),
                    "lastRun": s.get("last_run_time")
                }
                for s in schedulers
            ]
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_scheduler_status")
