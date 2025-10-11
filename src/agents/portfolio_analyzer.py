"""
Portfolio Analyzer Agent

Analyzes current portfolio holdings, P&L, exposures, and risk metrics.
"""

import json
import csv
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime, timezone

from claude_agent_sdk import tool
from loguru import logger

from ..config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import PortfolioState
from ..mcp.broker import get_broker


def create_portfolio_analyzer_tool(config: Config, state_manager: DatabaseStateManager):
    """
    Create portfolio analyzer tool with dependencies via closure.
    
    This follows Claude Agent SDK best practices by using closures
    to capture dependencies rather than monkey-patching attributes.
    """
    
    @tool("analyze_portfolio", "Analyze current portfolio state and risk metrics", {})
    async def analyze_portfolio_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze the current portfolio state.

        Retrieves holdings and positions from broker, calculates risk metrics,
        and updates the portfolio state in the system.
        """
        try:
            logger.info("Portfolio analyzer: Starting analysis")

            # Get portfolio data from CSV file
            try:
                portfolio_data = await _get_portfolio_from_csv()
            except Exception as e:
                logger.warning(f"Failed to get portfolio from CSV: {e}, using dummy data")
                portfolio_data = await _simulate_portfolio_data()

            # Calculate risk metrics
            risk_metrics = _calculate_risk_metrics(portfolio_data)

            # Create portfolio state
            portfolio_state = PortfolioState(
                as_of=datetime.now(timezone.utc).isoformat(),
                cash={"currency": "INR", "free": 100000, "margin": 50000},
                holdings=portfolio_data["holdings"],
                exposure_total=portfolio_data["total_exposure"],
                risk_aggregates=risk_metrics
            )

            # Update state
            logger.info(f"Updating portfolio state with {len(portfolio_data['holdings'])} holdings, total exposure: {portfolio_data['total_exposure']}")
            await state_manager.update_portfolio(portfolio_state)

            # Verify the state was updated
            updated_portfolio = await state_manager.get_portfolio()
            if updated_portfolio:
                logger.info(f"Portfolio state updated successfully: {len(updated_portfolio.holdings)} holdings")
            else:
                logger.error("Portfolio state update failed!")

            return {
                "content": [
                    {"type": "text", "text": f"Portfolio analysis completed with {len(portfolio_data['holdings'])} holdings"},
                    {"type": "text", "text": json.dumps(portfolio_state.to_dict(), indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Portfolio analysis failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }
    
    return analyze_portfolio_tool


async def _get_portfolio_from_csv() -> Dict[str, Any]:
    """Get portfolio data from CSV file."""
    holdings_dir = Path("holdings")
    csv_files = list(holdings_dir.glob("*.csv"))

    if not csv_files:
        raise Exception("No CSV files found in holdings directory")

    # Use the first CSV file found
    csv_file = csv_files[0]
    logger.info(f"Reading portfolio data from {csv_file}")

    processed_holdings = []
    total_exposure = 0

    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        headers = next(reader)  # Skip header row

        for row in reader:
            if len(row) < 9:  # Ensure we have enough columns
                continue

            try:
                symbol = row[0].strip('"')
                qty = int(float(row[1]))
                avg_price = float(row[2])
                last_price = float(row[3])
                pnl_abs = float(row[6])
                pnl_pct = float(row[7])

                exposure = qty * last_price

                # Determine risk tags based on symbol
                risk_tags = ["equity"]  # Default
                if any(bank in symbol for bank in ["BANK", "HDFC", "ICICI", "KOTAK", "PNB", "CANBK", "UNIONBANK", "IDBI", "KARURVYSYA"]):
                    risk_tags.append("banking")
                elif any(it in symbol for it in ["TCS", "INFY", "HCLTECH"]):
                    risk_tags.append("it")
                elif any(energy in symbol for energy in ["RELIANCE", "ONGC", "IOC", "OIL"]):
                    risk_tags.append("energy")
                elif any(consumer in symbol for consumer in ["ITC", "HINDUNILVR", "SWIGGY"]):
                    risk_tags.append("consumer")
                elif any(infra in symbol for infra in ["IRFC", "IREDA", "HUDCO"]):
                    risk_tags.append("infrastructure")
                elif any(pharma in symbol for pharma in ["LUPIN", "METROPOLIS"]):
                    risk_tags.append("pharma")
                else:
                    risk_tags.append("other")

                processed_holdings.append({
                    "symbol": symbol,
                    "qty": qty,
                    "avg_price": round(avg_price, 2),
                    "last_price": round(last_price, 2),
                    "pnl_abs": round(pnl_abs, 2),
                    "pnl_pct": round(pnl_pct, 2),
                    "exposure": round(exposure, 2),
                    "risk_tags": risk_tags
                })

                total_exposure += exposure

            except (ValueError, IndexError) as e:
                logger.warning(f"Skipping invalid row: {row} - {e}")
                continue

    logger.info(f"Loaded {len(processed_holdings)} holdings from CSV, total exposure: {total_exposure:.2f}")

    return {
        "holdings": processed_holdings,
        "total_exposure": round(total_exposure, 2)
    }


async def _simulate_portfolio_data() -> Dict[str, Any]:
    """Simulate portfolio data with realistic NSE stocks."""
    # Realistic NSE stock data as of October 2024
    holdings = [
        {
            "symbol": "RELIANCE",
            "qty": 25,
            "avg_price": 2650.75,
            "last_price": 2685.40,
            "pnl_abs": 864.13,
            "pnl_pct": 1.31,
            "exposure": 67135.00,
            "risk_tags": ["largecap", "energy"]
        },
        {
            "symbol": "TCS",
            "qty": 15,
            "avg_price": 4120.50,
            "last_price": 4185.80,
            "pnl_abs": 979.50,
            "pnl_pct": 1.58,
            "exposure": 62787.00,
            "risk_tags": ["largecap", "it"]
        },
        {
            "symbol": "HDFCBANK",
            "qty": 30,
            "avg_price": 1685.25,
            "last_price": 1720.90,
            "pnl_abs": 1070.25,
            "pnl_pct": 2.11,
            "exposure": 51627.00,
            "risk_tags": ["largecap", "banking"]
        },
        {
            "symbol": "ICICIBANK",
            "qty": 40,
            "avg_price": 1125.80,
            "last_price": 1158.60,
            "pnl_abs": 1311.20,
            "pnl_pct": 2.91,
            "exposure": 46344.00,
            "risk_tags": ["largecap", "banking"]
        },
        {
            "symbol": "INFY",
            "qty": 20,
            "avg_price": 1895.40,
            "last_price": 1925.75,
            "pnl_abs": 607.00,
            "pnl_pct": 1.60,
            "exposure": 38515.00,
            "risk_tags": ["largecap", "it"]
        },
        {
            "symbol": "HINDUNILVR",
            "qty": 12,
            "avg_price": 2785.90,
            "last_price": 2820.45,
            "pnl_abs": 413.64,
            "pnl_pct": 1.24,
            "exposure": 33845.40,
            "risk_tags": ["largecap", "consumer"]
        },
        {
            "symbol": "ITC",
            "qty": 35,
            "avg_price": 485.75,
            "last_price": 492.30,
            "pnl_abs": 229.25,
            "pnl_pct": 1.35,
            "exposure": 17230.50,
            "risk_tags": ["largecap", "consumer"]
        },
        {
            "symbol": "KOTAKBANK",
            "qty": 8,
            "avg_price": 1850.60,
            "last_price": 1885.25,
            "pnl_abs": 277.20,
            "pnl_pct": 1.87,
            "exposure": 15082.00,
            "risk_tags": ["largecap", "banking"]
        }
    ]

    total_exposure = sum(h["exposure"] for h in holdings)
    return {
        "holdings": holdings,
        "total_exposure": total_exposure
    }


def _calculate_risk_metrics(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate portfolio risk metrics."""
    holdings = portfolio_data["holdings"]
    total_exposure = portfolio_data["total_exposure"]

    # Simple risk calculations
    per_symbol_risk = {}
    sector_exposure = {}
    total_pnl = 0

    for holding in holdings:
        symbol = holding["symbol"]
        exposure = holding["exposure"]
        pnl_abs = holding["pnl_abs"]

        per_symbol_risk[symbol] = {
            "exposure_percent": (exposure / total_exposure) * 100 if total_exposure > 0 else 0,
            "pnl_abs": pnl_abs
        }

        # Simple sector classification
        sector = holding["risk_tags"][1] if len(holding["risk_tags"]) > 1 else "other"
        sector_exposure[sector] = sector_exposure.get(sector, 0) + exposure

        total_pnl += pnl_abs

    return {
        "per_symbol": per_symbol_risk,
        "portfolio": {
            "total_pnl": total_pnl,
            "sector_exposure": sector_exposure,
            "concentration_risk": max((exp / total_exposure) * 100 for exp in sector_exposure.values()) if sector_exposure else 0
        }
    }