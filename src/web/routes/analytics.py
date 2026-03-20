"""Truthful analytics and alert routes for the operator console."""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from src.models.trading_capabilities import CapabilityStatus
from src.services.paper_trading.account_manager import PaperTradingAccountManager

from ..dependencies import get_container
from ..utils.error_handlers import handle_trading_error, handle_unexpected_error

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])
limiter = Limiter(key_func=get_remote_address)

default_limit = os.getenv("RATE_LIMIT_DASHBOARD", "30/minute")


def _parse_iso_timestamp(value: Optional[str]) -> Optional[datetime]:
    """Parse a stored ISO timestamp safely."""
    if not value:
        return None

    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


async def _get_accounts(account_manager: PaperTradingAccountManager) -> list:
    """Return all paper-trading accounts."""
    return await account_manager.get_all_accounts()


async def _collect_open_positions(
    account_manager: PaperTradingAccountManager,
    accounts: list,
) -> Dict[str, list]:
    """Collect open positions per account."""
    positions_by_account: Dict[str, list] = {}
    for account in accounts:
        positions_by_account[account.account_id] = await account_manager.get_open_positions(account.account_id)
    return positions_by_account


async def _collect_closed_trades(
    account_manager: PaperTradingAccountManager,
    accounts: list,
    *,
    months_back_limit: int = 1000,
) -> Dict[str, list]:
    """Collect closed trades per account."""
    closed_by_account: Dict[str, list] = {}
    for account in accounts:
        closed_by_account[account.account_id] = await account_manager.get_closed_trades(
            account.account_id,
            limit=months_back_limit,
        )
    return closed_by_account


def _build_performance_payload(
    accounts: list,
    positions_by_account: Dict[str, list],
    closed_by_account: Dict[str, list],
    *,
    lookback_days: int = 30,
) -> Dict[str, Any]:
    """Build a truthful performance summary from paper-trading state."""
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=lookback_days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    total_initial_balance = sum(account.initial_balance for account in accounts)
    total_cash_balance = sum(account.current_balance for account in accounts)
    total_market_value = 0.0
    total_unrealized_pnl = 0.0

    realized_by_day: Dict[str, float] = defaultdict(float)
    winning_trades = 0
    total_closed_trades = 0

    for positions in positions_by_account.values():
        for position in positions:
            total_market_value += position.current_value
            total_unrealized_pnl += position.unrealized_pnl

    for trades in closed_by_account.values():
        for trade in trades:
            exit_dt = _parse_iso_timestamp(getattr(trade, "exit_date", None))
            if exit_dt is None or exit_dt < window_start:
                continue

            realized = float(getattr(trade, "realized_pnl", 0.0) or 0.0)
            realized_by_day[exit_dt.date().isoformat()] += realized
            total_closed_trades += 1
            if realized > 0:
                winning_trades += 1

    total_portfolio_value = total_cash_balance + total_market_value
    pnl_absolute = total_portfolio_value - total_initial_balance
    pnl_percentage = (pnl_absolute / total_initial_balance * 100) if total_initial_balance > 0 else 0.0
    win_rate = (winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0.0

    chart_data: List[Dict[str, Any]] = []
    cumulative_realized = 0.0
    for day_offset in range(lookback_days):
        day = window_start + timedelta(days=day_offset)
        day_key = day.date().isoformat()
        cumulative_realized += realized_by_day.get(day_key, 0.0)
        value = total_initial_balance + cumulative_realized
        if day.date() == now.date():
            value += total_unrealized_pnl

        chart_data.append(
            {
                "timestamp": day.replace(hour=12, minute=0, second=0, microsecond=0).isoformat(),
                "value": round(value, 2),
                "label": day.strftime("%d %b"),
            }
        )

    return {
        "timestamp": now.isoformat(),
        "portfolio_value": round(total_portfolio_value, 2),
        "pnl_absolute": round(pnl_absolute, 2),
        "pnl_percentage": round(pnl_percentage, 2),
        "win_rate": round(win_rate, 2),
        "chart_data": chart_data,
    }


def _build_active_alerts(capability_snapshot: Dict[str, Any], positions_by_account: Dict[str, list]) -> List[Dict[str, Any]]:
    """Build truthful operator alerts from capability blockers and open positions."""
    alerts: List[Dict[str, Any]] = []
    generated_at = capability_snapshot.get("generated_at", datetime.now(timezone.utc).isoformat())

    for check in capability_snapshot.get("checks", []):
        status = check.get("status")
        if status == CapabilityStatus.READY.value:
            continue

        severity = "high" if status == CapabilityStatus.BLOCKED.value else "medium"
        if check.get("blocking") is False and status != CapabilityStatus.BLOCKED.value:
            severity = "low"
        alerts.append(
            {
                "id": f"capability-{check['key']}",
                "title": check["label"],
                "type": check["key"],
                "severity": severity,
                "message": check["summary"],
                "details": check.get("detail"),
                "timestamp": generated_at,
                "acknowledged": False,
                "actionable": False,
                "autoGenerated": True,
            }
        )

    positions_without_stop_loss = 0
    positions_at_stop = 0
    positions_at_target = 0

    for positions in positions_by_account.values():
        for position in positions:
            if position.stop_loss is None:
                positions_without_stop_loss += 1
            elif position.trade_type.lower() == "buy" and position.current_price <= position.stop_loss:
                positions_at_stop += 1
            elif position.trade_type.lower() == "sell" and position.current_price >= position.stop_loss:
                positions_at_stop += 1

            if position.target_price is not None:
                if position.trade_type.lower() == "buy" and position.current_price >= position.target_price:
                    positions_at_target += 1
                elif position.trade_type.lower() == "sell" and position.current_price <= position.target_price:
                    positions_at_target += 1

    if positions_without_stop_loss:
        alerts.append(
            {
                "id": "paper-risk-missing-stop-loss",
                "title": "Missing stop-loss coverage",
                "type": "risk_policy",
                "severity": "medium",
                "message": f"{positions_without_stop_loss} open position(s) do not have a stop-loss configured.",
                "timestamp": generated_at,
                "acknowledged": False,
                "actionable": False,
                "autoGenerated": True,
            }
        )

    if positions_at_stop:
        alerts.append(
            {
                "id": "paper-risk-stop-loss-breached",
                "title": "Stop-loss breached",
                "type": "stop_loss",
                "severity": "high",
                "message": f"{positions_at_stop} open position(s) are trading through their configured stop-loss.",
                "timestamp": generated_at,
                "acknowledged": False,
                "actionable": False,
                "autoGenerated": True,
            }
        )

    if positions_at_target:
        alerts.append(
            {
                "id": "paper-risk-target-hit",
                "title": "Target reached",
                "type": "target_price",
                "severity": "low",
                "message": f"{positions_at_target} open position(s) have reached their configured target price.",
                "timestamp": generated_at,
                "acknowledged": False,
                "actionable": False,
                "autoGenerated": True,
            }
        )

    return alerts


@router.get("/analytics/portfolio-deep")
@limiter.limit(default_limit)
async def portfolio_deep_analytics(
    request: Request,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return truthful paper-trading performance summary."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        accounts = await _get_accounts(account_manager)
        if not accounts:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "portfolio_value": 0.0,
                "pnl_absolute": 0.0,
                "pnl_percentage": 0.0,
                "win_rate": 0.0,
                "chart_data": [],
            }

        positions_by_account = await _collect_open_positions(account_manager, accounts)
        closed_by_account = await _collect_closed_trades(account_manager, accounts)
        return _build_performance_payload(accounts, positions_by_account, closed_by_account, lookback_days=30)
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "analytics_endpoint")


@router.get("/analytics/trades")
@limiter.limit(default_limit)
async def get_trades_analytics(
    request: Request,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return truthful closed-trade analytics for the operator console."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        accounts = await _get_accounts(account_manager)
        closed_by_account = await _collect_closed_trades(account_manager, accounts)

        trades = [
            trade.model_dump() if hasattr(trade, "model_dump") else trade.dict()
            for account_trades in closed_by_account.values()
            for trade in account_trades
        ]

        return {
            "total_trades": len(trades),
            "trades": trades,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "analytics_endpoint")


@router.get("/alerts")
@limiter.limit(default_limit)
async def get_risk_alerts(
    request: Request,
    user_id: Optional[str] = None,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return the same truthful active alerts used by the dashboard."""
    del user_id
    return await get_active_alerts(request=request, container=container)


@router.get("/monitor/status")
@limiter.limit(default_limit)
async def get_risk_monitoring_status(
    request: Request,
    user_id: Optional[str] = None,
    portfolio_id: Optional[str] = None,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return truthful monitoring status from current capability state."""
    del user_id, portfolio_id
    try:
        capability_service = await container.get("trading_capability_service")
        snapshot = (await capability_service.get_snapshot()).to_dict()
        alerts = _build_active_alerts(snapshot, {})
        return {
            "monitoring_active": True,
            "last_check": snapshot["generated_at"],
            "risk_score": len(snapshot["blockers"]),
            "alerts_count": len(alerts),
            "status": snapshot["overall_status"],
            "automation_allowed": snapshot["automation_allowed"],
            "blockers": snapshot["blockers"],
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "analytics_endpoint")


@router.get("/portfolio/risk-metrics")
@limiter.limit(default_limit)
async def get_portfolio_risk_metrics(
    request: Request,
    portfolio_id: str = "paper-trading",
    period: str = "30d",
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return truthful paper-portfolio risk metrics."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        accounts = await _get_accounts(account_manager)
        positions_by_account = await _collect_open_positions(account_manager, accounts)

        total_market_value = 0.0
        largest_position_value = 0.0
        open_positions = 0
        total_cash = sum(account.current_balance for account in accounts)

        for positions in positions_by_account.values():
            open_positions += len(positions)
            for position in positions:
                total_market_value += position.current_value
                largest_position_value = max(largest_position_value, position.current_value)

        gross_portfolio_value = total_cash + total_market_value
        concentration_risk = (
            largest_position_value / gross_portfolio_value * 100
            if gross_portfolio_value > 0
            else 0.0
        )

        return {
            "portfolio_id": portfolio_id,
            "period": period,
            "sharpe_ratio": None,
            "max_drawdown": None,
            "volatility": None,
            "var_95": None,
            "beta": None,
            "alpha": None,
            "concentration_risk": round(concentration_risk, 2),
            "gross_portfolio_value": round(gross_portfolio_value, 2),
            "cash_ratio": round((total_cash / gross_portfolio_value * 100), 2) if gross_portfolio_value > 0 else 0.0,
            "open_positions": open_positions,
            "account_count": len(accounts),
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "analytics_endpoint")


@router.get("/analytics/performance/30d")
@limiter.limit(default_limit)
async def get_performance_30d(
    request: Request,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return truthful 30-day performance data matching the frontend contract."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        accounts = await _get_accounts(account_manager)
        if not accounts:
            return {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "portfolio_value": 0.0,
                "pnl_absolute": 0.0,
                "pnl_percentage": 0.0,
                "win_rate": 0.0,
                "chart_data": [],
            }

        positions_by_account = await _collect_open_positions(account_manager, accounts)
        closed_by_account = await _collect_closed_trades(account_manager, accounts)
        return _build_performance_payload(accounts, positions_by_account, closed_by_account, lookback_days=30)
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "analytics_endpoint")


@router.get("/alerts/active")
@limiter.limit(default_limit)
async def get_active_alerts(
    request: Request,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Return truthful active alerts from capability state and open positions."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        capability_service = await container.get("trading_capability_service")

        accounts = await _get_accounts(account_manager)
        positions_by_account = await _collect_open_positions(account_manager, accounts)
        snapshot = (await capability_service.get_snapshot()).to_dict()
        alerts = _build_active_alerts(snapshot, positions_by_account)

        return {
            "alerts": alerts,
            "total": len(alerts),
            "critical": len([alert for alert in alerts if alert["severity"] in {"critical", "high"}]),
            "warning": len([alert for alert in alerts if alert["severity"] == "medium"]),
            "info": len([alert for alert in alerts if alert["severity"] in {"low", "info"}]),
            "lastUpdated": snapshot["generated_at"],
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "analytics_endpoint")
