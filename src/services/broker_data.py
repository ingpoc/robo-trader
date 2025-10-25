"""
Real-time broker data integration using Kite MCP server.

Fetches live portfolio, holdings, and market data from Zerodha Kite Connect
instead of CSV files.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from loguru import logger

from src.config import Config


async def fetch_live_holdings_from_broker(broker) -> Optional[List[Dict[str, Any]]]:
    """
    Fetch live holdings directly from broker client.
    """
    try:
        if not broker or not broker.is_authenticated():
            logger.warning("Broker not authenticated, cannot fetch live holdings")
            return None
        
        logger.info("Fetching live holdings from Zerodha...")
        holdings = broker.kite.holdings()
        
        logger.info(f"Fetched {len(holdings)} holdings from Zerodha")
        return holdings
        
    except Exception as e:
        logger.error(f"Error fetching holdings from broker: {e}")
        return None


async def fetch_live_positions_from_broker(broker) -> Optional[Dict[str, Any]]:
    """
    Fetch live positions directly from broker client.
    """
    try:
        if not broker or not broker.is_authenticated():
            logger.warning("Broker not authenticated, cannot fetch live positions")
            return None
        
        logger.info("Fetching live positions from Zerodha...")
        positions = broker.kite.positions()
        
        logger.info("Fetched positions from Zerodha")
        return positions
        
    except Exception as e:
        logger.error(f"Error fetching positions from broker: {e}")
        return None


async def fetch_margins_from_broker(broker) -> Optional[Dict[str, Any]]:
    """
    Fetch margin details directly from broker client.
    """
    try:
        if not broker or not broker.is_authenticated():
            logger.warning("Broker not authenticated, cannot fetch margins")
            return None
        
        logger.info("Fetching margins from Zerodha...")
        margins = broker.kite.margins()
        
        return margins
        
    except Exception as e:
        logger.error(f"Error fetching margins from broker: {e}")
        return None


def normalize_kite_holding(holding: Dict[str, Any], classify_func=None) -> Dict[str, Any]:
    """
    Normalize Kite holding data to internal format.
    
    Kite format:
    {
        "tradingsymbol": "INFY",
        "exchange": "NSE",
        "quantity": 100,
        "average_price": 1520.50,
        "last_price": 1540.20,
        "pnl": 1970.0,
        "product": "CNC",
        ...
    }
    
    Internal format:
    {
        "symbol": "INFY",
        "qty": 100,
        "avg_price": 1520.50,
        "last_price": 1540.20,
        "pnl_abs": 1970.0,
        "pnl_pct": 1.29,
        "exposure": 154020.0,
        ...
    }
    """
    try:
        symbol = holding.get("tradingsymbol", "")
        qty = holding.get("quantity", 0)
        avg_price = holding.get("average_price", 0.0)
        last_price = holding.get("last_price", 0.0)
        pnl_abs = holding.get("pnl", 0.0)
        
        # Calculate derived values
        invested = qty * avg_price
        current_value = qty * last_price
        pnl_pct = (pnl_abs / invested * 100) if invested > 0 else 0.0
        day_change_pct = holding.get("day_change_percentage", 0.0)
        
        # Classify sector
        from . import analytics
        sector = analytics._classify_symbol(symbol)
        
        return {
            "symbol": symbol,
            "qty": qty,
            "quantity": qty,
            "avg_price": avg_price,
            "last_price": last_price,
            "invested": invested,
            "current_value": current_value,
            "exposure": current_value,
            "pnl_abs": pnl_abs,
            "pnl_pct": pnl_pct,
            "day_change_pct": day_change_pct,
            "sector": sector,
            "risk_tags": [sector.lower().replace(" ", "_"), sector.lower()],
            "product": holding.get("product", "CNC"),
            "exchange": holding.get("exchange", "NSE"),
        }
    except Exception as e:
        logger.error(f"Error normalizing holding {holding.get('tradingsymbol')}: {e}")
        return {}


async def get_live_portfolio_data(broker) -> Optional[Dict[str, Any]]:
    """
    Get complete live portfolio data from broker client.
    
    Returns:
        {
            "holdings": [...],
            "positions": {...},
            "cash": {"free": ..., "margin": ...}
        }
    """
    try:
        # Fetch all data in parallel
        import asyncio
        
        holdings_task = fetch_live_holdings_from_broker(broker)
        positions_task = fetch_live_positions_from_broker(broker)
        margins_task = fetch_margins_from_broker(broker)
        
        holdings_raw, positions_raw, margins_raw = await asyncio.gather(
            holdings_task,
            positions_task,
            margins_task,
            return_exceptions=True
        )
        
        # Handle errors
        if isinstance(holdings_raw, Exception):
            logger.error(f"Holdings fetch failed: {holdings_raw}")
            holdings_raw = None
        
        if isinstance(positions_raw, Exception):
            logger.error(f"Positions fetch failed: {positions_raw}")
            positions_raw = None
        
        if isinstance(margins_raw, Exception):
            logger.error(f"Margins fetch failed: {margins_raw}")
            margins_raw = None
        
        # Normalize holdings
        holdings = []
        if holdings_raw:
            holdings = [normalize_kite_holding(h) for h in holdings_raw if h]
            holdings = [h for h in holdings if h]  # Remove empty dicts
        
        # Extract cash info
        cash = {"free": 0.0, "margin": 0.0}
        if margins_raw and "equity" in margins_raw:
            equity_margins = margins_raw["equity"]
            cash["free"] = equity_margins.get("available", {}).get("live_balance", 0.0)
            cash["margin"] = equity_margins.get("utilised", {}).get("debits", 0.0)
        
        return {
            "holdings": holdings,
            "positions": positions_raw,
            "cash": cash,
            "source": "zerodha_live",
            "fetched_at": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error fetching live portfolio data: {e}")
        return None


def is_broker_connected(broker) -> bool:
    """Check if broker client is available and authenticated."""
    return broker is not None and broker.is_authenticated()