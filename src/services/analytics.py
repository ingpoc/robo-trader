from __future__ import annotations

import csv
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple, Optional

from loguru import logger

from ..config import Config
from ..core.state_models import PortfolioState
from ..core.database_state import DatabaseStateManager
from .broker_data import get_live_portfolio_data, is_broker_connected

SECTOR_KEYWORDS: Dict[str, Iterable[str]] = {
    "Banking": (
        "BANK",
        "HDFC",
        "ICICI",
        "PNB",
        "IDFC",
        "KARUR",
        "UNION",
        "CANARA",
        "INDUS",
    ),
    "Information Technology": ("INFY", "TCS", "HCL", "TECH", "MCX", "LTIM", "IT"),
    "Energy": ("OIL", "ONGC", "IOC", "POWER", "IOCL", "GAIL", "ENERGY"),
    "Industrial": ("ACE", "GRAVITA", "ETERNAL", "SKIPPER", "HGINFRA", "CEM", "GVT"),
    "Infrastructure": ("IRCTC", "IRFC", "IREDA", "HUDCO", "GRSE", "LARSEN"),
    "Consumer": ("ITC", "TITAN", "TBZ", "SWIGGY", "HIND", "MONARCH", "CONSUMER"),
    "Metals & Mining": ("JSL", "TATASTEEL", "GENUS", "WELCORP", "UPL", "METAL"),
    "Healthcare": ("ASTER", "METROPOLIS", "SUPRIYA", "LUPIN", "PHARMA"),
    "Automobile": ("BAJAJ", "TATAMOTORS", "FIEM", "GABRIEL", "AUTO"),
}


def _parse_float(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (float, int)):
        return float(value)
    text = str(value).strip().replace(",", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _parse_int(value: Any) -> int:
    return int(round(_parse_float(value)))


def _classify_symbol(symbol: str) -> str:
    upper_symbol = symbol.upper()
    for sector, keywords in SECTOR_KEYWORDS.items():
        if any(keyword.upper() in upper_symbol for keyword in keywords):
            return sector
    return "Others"


def _find_holdings_csv(config: Config) -> Path:
    holdings_dir = Path(config.project_dir) / "holdings"
    if not holdings_dir.exists():
        raise FileNotFoundError(f"Holdings directory not found: {holdings_dir}")

    csv_files = sorted(
        holdings_dir.glob("*.csv"), key=lambda path: path.stat().st_mtime, reverse=True
    )
    if not csv_files:
        raise FileNotFoundError(
            f"No holdings CSV discovered inside directory: {holdings_dir}"
        )
    return csv_files[0]


async def _load_holdings_rows(csv_path: Path) -> List[Dict[str, Any]]:
    import aiofiles
    holdings: List[Dict[str, Any]] = []
    async with aiofiles.open(csv_path, mode='r', newline="", encoding="utf-8-sig") as csvfile:
        content = await csvfile.read()
        reader = csv.DictReader(content.splitlines())
        for row in reader:
            raw_symbol = row.get("Instrument", "").strip().strip('"')
            if not raw_symbol:
                continue

            quantity = _parse_int(row.get("Qty."))
            avg_cost = _parse_float(row.get("Avg. cost"))
            last_price = _parse_float(row.get("LTP"))
            invested = _parse_float(row.get("Invested"))
            current_value = _parse_float(row.get("Cur. val"))
            pnl_abs = _parse_float(row.get("P&L"))
            pnl_pct = _parse_float(row.get("Net chg."))
            day_change_pct = _parse_float(row.get("Day chg."))
            sector = _classify_symbol(raw_symbol)
            risk_tag = sector.lower().replace(" ", "_")

            holdings.append(
                {
                    "symbol": raw_symbol,
                    "qty": quantity,
                    "quantity": quantity,
                    "avg_price": avg_cost,
                    "last_price": last_price,
                    "invested": invested,
                    "current_value": current_value,
                    "exposure": current_value,
                    "pnl_abs": pnl_abs,
                    "pnl_pct": pnl_pct,
                    "day_change_pct": day_change_pct,
                    "sector": sector,
                    "risk_tags": [risk_tag, sector.lower()],
                }
            )
    return holdings


def _aggregate_sector_exposure(
    holdings: List[Dict[str, Any]], total_value: float
) -> Dict[str, float]:
    exposure: Dict[str, float] = {}
    for item in holdings:
        sector = item["sector"]
        exposure[sector] = exposure.get(sector, 0.0) + item["current_value"]

    if total_value <= 0:
        return {sector: 0.0 for sector in exposure}

    return {sector: (value / total_value) * 100 for sector, value in exposure.items()}


def _build_portfolio_state(
    holdings: List[Dict[str, Any]], config: Config
) -> Tuple[PortfolioState, Dict[str, Any]]:
    total_invested = sum(item["invested"] for item in holdings)
    total_value = sum(item["current_value"] for item in holdings)
    total_pnl = total_value - total_invested
    net_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0.0

    weighted_day_change = (
        sum(item["day_change_pct"] * item["current_value"] for item in holdings)
        if total_value
        else 0.0
    )
    weighted_day_change_pct = (
        weighted_day_change / total_value if total_value else 0.0
    )

    timestamp = datetime.now(timezone.utc).isoformat()

    top_gainers = sorted(
        holdings, key=lambda item: item["day_change_pct"], reverse=True
    )[:5]
    top_losers = sorted(holdings, key=lambda item: item["day_change_pct"])[:5]
    largest_positions = sorted(
        holdings, key=lambda item: item["current_value"], reverse=True
    )[:5]

    sector_breakdown = _aggregate_sector_exposure(holdings, total_value)
    concentration_risk = max(sector_breakdown.values()) if sector_breakdown else 0.0
    dominant_sector = (
        max(sector_breakdown, key=sector_breakdown.get) if sector_breakdown else None
    )

    portfolio_metrics = {
        "total_invested": total_invested,
        "total_current_value": total_value,
        "total_pnl": total_pnl,
        "total_pnl_pct": net_pnl_pct,
        "day_change_pct": weighted_day_change_pct,
        "holdings_count": len(holdings),
        "timestamp": timestamp,
        "concentration_risk": concentration_risk,
        "dominant_sector": dominant_sector,
    }

    per_symbol = {
        item["symbol"]: {
            "allocation_pct": (item["current_value"] / total_value * 100)
            if total_value
            else 0.0,
            "pnl_pct": item["pnl_pct"],
            "day_change_pct": item["day_change_pct"],
        }
        for item in holdings
    }

    risk_aggregates = {
        "portfolio": portfolio_metrics,
        "per_symbol": per_symbol,
        "sector_exposure": sector_breakdown,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "largest_positions": largest_positions,
    }

    portfolio_state = PortfolioState(
        as_of=timestamp,
        cash={
            "currency": "INR",
            "free": 0.0,
            "margin": 0.0,
        },
        holdings=holdings,
        exposure_total=total_value,
        risk_aggregates=risk_aggregates,
    )

    analytics_summary = {
        "portfolio": portfolio_metrics,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "largest_positions": largest_positions,
        "sector_breakdown": sector_breakdown,
    }

    return portfolio_state, analytics_summary


def _generate_screening_report(holdings: List[Dict[str, Any]]) -> Dict[str, Any]:
    value_opportunities = sorted(
        [item for item in holdings if item["pnl_pct"] < 0],
        key=lambda item: item["pnl_pct"],
    )[:5]

    momentum_candidates = sorted(
        holdings, key=lambda item: (item["day_change_pct"], item["pnl_pct"]), reverse=True
    )[:5]

    risk_alerts = sorted(
        holdings, key=lambda item: (item["day_change_pct"], item["pnl_pct"])
    )[:5]

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "value_opportunities": value_opportunities,
        "momentum": momentum_candidates,
        "risk_alerts": risk_alerts,
    }


def _generate_technical_signals(
    holdings: List[Dict[str, Any]], timeframe: str = "1d"
) -> Dict[str, Any]:
    signals = []
    for item in holdings:
        avg_price = item["avg_price"]
        last_price = item["last_price"]
        if avg_price <= 0 or last_price <= 0:
            continue

        return_pct = ((last_price - avg_price) / avg_price) * 100
        day_change = item["day_change_pct"]

        if day_change >= 2 and return_pct >= 10:
            disposition = "strong_buy"
            rationale = "Strong positive momentum with sustained gains"
        elif day_change >= 1 and return_pct >= 0:
            disposition = "buy"
            rationale = "Positive daily momentum reinforcing uptrend"
        elif return_pct <= -10:
            disposition = "review"
            rationale = "Significant drawdown detected; review position"
        elif day_change <= -2:
            disposition = "watchlist"
            rationale = "Sharp daily decline; consider tightening stops"
        else:
            disposition = "hold"
            rationale = "Neutral movement"

        signals.append(
            {
                "symbol": item["symbol"],
                "timeframe": timeframe,
                "disposition": disposition,
                "return_since_entry_pct": round(return_pct, 2),
                "day_change_pct": round(day_change, 2),
                "allocation_pct": (
                    item["current_value"] / sum(h["current_value"] for h in holdings) * 100
                    if holdings
                    else 0.0
                ),
                "rationale": rationale,
            }
        )

    signals.sort(key=lambda entry: abs(entry["day_change_pct"]), reverse=True)
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "timeframe": timeframe,
        "signals": signals[:20],
    }


def _generate_strategy_analysis(
    holdings: List[Dict[str, Any]], analytics: Dict[str, Any]
) -> Dict[str, Any]:
    portfolio_metrics = analytics.get("portfolio", {})
    total_value = portfolio_metrics.get("total_current_value", 0.0)

    largest_positions = analytics.get("largest_positions", [])
    outsized_positions = [
        {
            "symbol": item["symbol"],
            "allocation_pct": (item["current_value"] / total_value * 100)
            if total_value
            else 0.0,
            "current_value": item["current_value"],
        }
        for item in largest_positions
        if total_value and (item["current_value"] / total_value * 100) > 10
    ]

    profit_taking = [
        {
            "symbol": item["symbol"],
            "pnl_pct": item["pnl_pct"],
            "current_value": item["current_value"],
        }
        for item in holdings
        if item["pnl_pct"] >= 25
    ][:5]

    cut_losses = [
        {
            "symbol": item["symbol"],
            "pnl_pct": item["pnl_pct"],
            "current_value": item["current_value"],
        }
        for item in holdings
        if item["pnl_pct"] <= -15
    ][:5]

    rebalance_actions = []
    if outsized_positions:
        rebalance_actions.append(
            "Consider trimming outsized positions to reduce concentration risk."
        )
    if profit_taking:
        rebalance_actions.append(
            "Trail stops or harvest profits on high-return holdings."
        )
    if cut_losses:
        rebalance_actions.append(
            "Review underperforming positions for potential exit or risk adjustment."
        )
    if not rebalance_actions:
        rebalance_actions.append(
            "Portfolio allocations within normal bounds; continue monitoring."
        )

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "portfolio_summary": portfolio_metrics,
        "rebalance_candidates": outsized_positions,
        "take_profit_candidates": profit_taking,
        "loss_cut_candidates": cut_losses,
        "actions": rebalance_actions,
    }


async def run_portfolio_scan(
    config: Config, state_manager: DatabaseStateManager
) -> Dict[str, Any]:
    """
    Run portfolio scan using live data from broker if available,
    falling back to CSV data if not connected.
    """
    # Try to fetch live data from broker first
    from ..mcp.broker import get_broker
    broker = get_broker(config)
    
    if is_broker_connected(broker):
        logger.info("Using live data from Zerodha broker")
        live_data = await get_live_portfolio_data(broker)
        
        if live_data and live_data.get("holdings"):
            holdings = live_data["holdings"]
            
            # Update cash info
            portfolio_state, analytics = _build_portfolio_state(holdings, config)
            portfolio_state.cash = live_data.get("cash", {"free": 0.0, "margin": 0.0})
            
            await state_manager.update_portfolio(portfolio_state)
            return {
                "source": "zerodha_live",
                "portfolio": portfolio_state.to_dict(),
                "analytics": analytics,
            }
        else:
            logger.warning("Broker returned no holdings, falling back to CSV")
    else:
        logger.info("Broker not connected, using CSV data as fallback")
    
    # Fallback to CSV data
    try:
        csv_path = _find_holdings_csv(config)
        holdings = await _load_holdings_rows(csv_path)
        portfolio_state, analytics = _build_portfolio_state(holdings, config)

        await state_manager.update_portfolio(portfolio_state)
        return {
            "source": f"csv_fallback",
            "portfolio": portfolio_state.to_dict(),
            "analytics": analytics,
        }
    except FileNotFoundError as e:
        logger.warning(f"No CSV fallback available: {e}")
        # Return empty portfolio
        empty_portfolio = PortfolioState(
            as_of=datetime.now(timezone.utc).isoformat(),
            cash={"currency": "INR", "free": 0.0, "margin": 0.0},
            holdings=[],
            exposure_total=0.0,
            risk_aggregates={"portfolio": {}, "per_symbol": {}}
        )
        await state_manager.update_portfolio(empty_portfolio)
        return {
            "source": "empty",
            "portfolio": empty_portfolio.to_dict(),
            "analytics": {},
        }


async def run_market_screening(
    config: Config, state_manager: DatabaseStateManager
) -> Dict[str, Any]:
    """
    Run market screening using live data if available.
    """
    # Try live data first
    from ..mcp.broker import get_broker
    broker = get_broker(config)
    
    if is_broker_connected(broker):
        live_data = await get_live_portfolio_data(broker)
        if live_data and live_data.get("holdings"):
            holdings = live_data["holdings"]
            report = _generate_screening_report(holdings)
            await state_manager.update_screening_results(report)
            return {"source": "zerodha_live", "screening": report}
    
    # Fallback to CSV
    try:
        csv_path = _find_holdings_csv(config)
        holdings = await _load_holdings_rows(csv_path)
        report = _generate_screening_report(holdings)
        await state_manager.update_screening_results(report)
        return {"source": "csv_fallback", "screening": report}
    except FileNotFoundError:
        # Return empty screening
        empty_report = {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "value_opportunities": [],
            "momentum": [],
            "risk_alerts": []
        }
        await state_manager.update_screening_results(empty_report)
        return {"source": "empty", "screening": empty_report}


async def run_strategy_analysis(
    config: Config, state_manager: DatabaseStateManager
) -> Dict[str, Any]:
    """
    Run strategy analysis using live data if available.
    """
    # Try live data first
    from ..mcp.broker import get_broker
    broker = get_broker(config)
    
    if is_broker_connected(broker):
        live_data = await get_live_portfolio_data(broker)
        if live_data and live_data.get("holdings"):
            holdings = live_data["holdings"]
            portfolio_state, analytics = _build_portfolio_state(holdings, config)
            portfolio_state.cash = live_data.get("cash", {"free": 0.0, "margin": 0.0})
            analysis = _generate_strategy_analysis(holdings, analytics)
            await state_manager.update_strategy_results(analysis)
            return {
                "source": "zerodha_live",
                "strategy": analysis,
                "portfolio": analytics.get("portfolio"),
            }
    
    # Fallback to CSV
    try:
        csv_path = _find_holdings_csv(config)
        holdings = await _load_holdings_rows(csv_path)
        portfolio_state, analytics = _build_portfolio_state(holdings, config)
        analysis = _generate_strategy_analysis(holdings, analytics)
        await state_manager.update_strategy_results(analysis)
        return {
            "source": "csv_fallback",
            "strategy": analysis,
            "portfolio": analytics.get("portfolio"),
        }
    except FileNotFoundError:
        # Return empty analysis
        empty_analysis = {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "portfolio_summary": {},
            "rebalance_candidates": [],
            "take_profit_candidates": [],
            "loss_cut_candidates": [],
            "actions": ["No portfolio data available. Connect to broker or provide CSV data."]
        }
        await state_manager.update_strategy_results(empty_analysis)
        return {
            "source": "empty",
            "strategy": empty_analysis,
            "portfolio": {},
        }


async def run_technical_snapshot(
    config: Config, timeframe: str = "1d"
) -> Dict[str, Any]:
    csv_path = _find_holdings_csv(config)
    holdings = await _load_holdings_rows(csv_path)
    signals = _generate_technical_signals(holdings, timeframe)
    signals["source"] = str(csv_path)
    return signals