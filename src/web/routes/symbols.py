"""Symbol search routes."""

import logging
import os
from typing import Any, Dict

from fastapi import APIRouter, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.errors import TradingError

from ..utils.error_handlers import (handle_trading_error,
                                    handle_unexpected_error)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["symbols"])
limiter = Limiter(key_func=get_remote_address)

symbols_limit = os.getenv("RATE_LIMIT_SYMBOLS", "30/minute")

# NSE Top 100 stocks with current market data
# In production, this would come from a database or real-time API
NSE_SYMBOLS = [
    {
        "symbol": "RELIANCE",
        "name": "Reliance Industries Ltd",
        "price": 2456.75,
        "change": 23.45,
        "changePercent": 0.96,
    },
    {
        "symbol": "TCS",
        "name": "Tata Consultancy Services Ltd",
        "price": 3876.20,
        "change": -12.30,
        "changePercent": -0.32,
    },
    {
        "symbol": "HDFCBANK",
        "name": "HDFC Bank Ltd",
        "price": 1654.80,
        "change": 8.90,
        "changePercent": 0.54,
    },
    {
        "symbol": "ICICIBANK",
        "name": "ICICI Bank Ltd",
        "price": 987.65,
        "change": -5.40,
        "changePercent": -0.54,
    },
    {
        "symbol": "INFY",
        "name": "Infosys Ltd",
        "price": 1432.10,
        "change": 15.75,
        "changePercent": 1.11,
    },
    {
        "symbol": "ITC",
        "name": "ITC Ltd",
        "price": 432.85,
        "change": 2.15,
        "changePercent": 0.50,
    },
    {
        "symbol": "KOTAKBANK",
        "name": "Kotak Mahindra Bank Ltd",
        "price": 1789.45,
        "change": -7.20,
        "changePercent": -0.40,
    },
    {
        "symbol": "LT",
        "name": "Larsen & Toubro Ltd",
        "price": 3456.90,
        "change": 28.60,
        "changePercent": 0.84,
    },
    {
        "symbol": "MARUTI",
        "name": "Maruti Suzuki India Ltd",
        "price": 12345.60,
        "change": -45.30,
        "changePercent": -0.37,
    },
    {
        "symbol": "WIPRO",
        "name": "Wipro Ltd",
        "price": 567.80,
        "change": 3.25,
        "changePercent": 0.58,
    },
    {
        "symbol": "BHARTIARTL",
        "name": "Bharti Airtel Ltd",
        "price": 1234.50,
        "change": 12.30,
        "changePercent": 1.01,
    },
    {
        "symbol": "SBIN",
        "name": "State Bank of India",
        "price": 654.30,
        "change": -3.20,
        "changePercent": -0.49,
    },
    {
        "symbol": "HINDUNILVR",
        "name": "Hindustan Unilever Ltd",
        "price": 2345.60,
        "change": 18.90,
        "changePercent": 0.81,
    },
    {
        "symbol": "BAJFINANCE",
        "name": "Bajaj Finance Ltd",
        "price": 6789.45,
        "change": -34.50,
        "changePercent": -0.51,
    },
    {
        "symbol": "ASIANPAINT",
        "name": "Asian Paints Ltd",
        "price": 3210.80,
        "change": 15.60,
        "changePercent": 0.49,
    },
    {
        "symbol": "AXISBANK",
        "name": "Axis Bank Ltd",
        "price": 1098.75,
        "change": 8.45,
        "changePercent": 0.78,
    },
    {
        "symbol": "TITAN",
        "name": "Titan Company Ltd",
        "price": 3456.20,
        "change": -18.30,
        "changePercent": -0.53,
    },
    {
        "symbol": "SUNPHARMA",
        "name": "Sun Pharmaceutical Industries Ltd",
        "price": 1234.90,
        "change": 10.20,
        "changePercent": 0.83,
    },
    {
        "symbol": "ADANIENT",
        "name": "Adani Enterprises Ltd",
        "price": 2567.40,
        "change": 45.60,
        "changePercent": 1.81,
    },
    {
        "symbol": "ULTRACEMCO",
        "name": "UltraTech Cement Ltd",
        "price": 8901.30,
        "change": -56.70,
        "changePercent": -0.63,
    },
    {
        "symbol": "NESTLEIND",
        "name": "Nestle India Ltd",
        "price": 23456.80,
        "change": 234.50,
        "changePercent": 1.01,
    },
    {
        "symbol": "TATAMOTORS",
        "name": "Tata Motors Ltd",
        "price": 765.40,
        "change": 12.30,
        "changePercent": 1.63,
    },
    {
        "symbol": "TATASTEEL",
        "name": "Tata Steel Ltd",
        "price": 134.50,
        "change": -2.30,
        "changePercent": -1.68,
    },
    {
        "symbol": "M&M",
        "name": "Mahindra & Mahindra Ltd",
        "price": 1876.20,
        "change": 23.40,
        "changePercent": 1.26,
    },
    {
        "symbol": "POWERGRID",
        "name": "Power Grid Corporation of India Ltd",
        "price": 234.60,
        "change": 3.20,
        "changePercent": 1.38,
    },
    {
        "symbol": "NTPC",
        "name": "NTPC Ltd",
        "price": 345.80,
        "change": -2.30,
        "changePercent": -0.66,
    },
    {
        "symbol": "ONGC",
        "name": "Oil & Natural Gas Corporation Ltd",
        "price": 234.50,
        "change": 4.50,
        "changePercent": 1.96,
    },
    {
        "symbol": "JSWSTEEL",
        "name": "JSW Steel Ltd",
        "price": 876.30,
        "change": 12.40,
        "changePercent": 1.44,
    },
    {
        "symbol": "COALINDIA",
        "name": "Coal India Ltd",
        "price": 432.10,
        "change": -5.60,
        "changePercent": -1.28,
    },
    {
        "symbol": "BAJAJFINSV",
        "name": "Bajaj Finserv Ltd",
        "price": 1543.80,
        "change": 18.90,
        "changePercent": 1.24,
    },
    {
        "symbol": "TECHM",
        "name": "Tech Mahindra Ltd",
        "price": 1234.50,
        "change": -8.70,
        "changePercent": -0.70,
    },
    {
        "symbol": "HCLTECH",
        "name": "HCL Technologies Ltd",
        "price": 1456.80,
        "change": 15.60,
        "changePercent": 1.08,
    },
    {
        "symbol": "DIVISLAB",
        "name": "Divi's Laboratories Ltd",
        "price": 3456.90,
        "change": -23.40,
        "changePercent": -0.67,
    },
    {
        "symbol": "DRREDDY",
        "name": "Dr. Reddy's Laboratories Ltd",
        "price": 5678.30,
        "change": 45.60,
        "changePercent": 0.81,
    },
    {
        "symbol": "CIPLA",
        "name": "Cipla Ltd",
        "price": 1234.60,
        "change": 8.90,
        "changePercent": 0.73,
    },
    {
        "symbol": "EICHERMOT",
        "name": "Eicher Motors Ltd",
        "price": 4567.80,
        "change": -34.50,
        "changePercent": -0.75,
    },
    {
        "symbol": "HEROMOTOCO",
        "name": "Hero MotoCorp Ltd",
        "price": 3456.20,
        "change": 23.40,
        "changePercent": 0.68,
    },
    {
        "symbol": "BRITANNIA",
        "name": "Britannia Industries Ltd",
        "price": 5432.10,
        "change": 45.60,
        "changePercent": 0.85,
    },
    {
        "symbol": "APOLLOHOSP",
        "name": "Apollo Hospitals Enterprise Ltd",
        "price": 6543.20,
        "change": -56.70,
        "changePercent": -0.86,
    },
    {
        "symbol": "SHREECEM",
        "name": "Shree Cement Ltd",
        "price": 27654.30,
        "change": 234.50,
        "changePercent": 0.86,
    },
    {
        "symbol": "INDUSINDBK",
        "name": "IndusInd Bank Ltd",
        "price": 1432.50,
        "change": 12.30,
        "changePercent": 0.87,
    },
    {
        "symbol": "GRASIM",
        "name": "Grasim Industries Ltd",
        "price": 2345.60,
        "change": -18.90,
        "changePercent": -0.80,
    },
    {
        "symbol": "ADANIPORTS",
        "name": "Adani Ports and Special Economic Zone Ltd",
        "price": 1234.50,
        "change": 23.40,
        "changePercent": 1.93,
    },
    {
        "symbol": "HINDALCO",
        "name": "Hindalco Industries Ltd",
        "price": 543.20,
        "change": 8.90,
        "changePercent": 1.67,
    },
    {
        "symbol": "BPCL",
        "name": "Bharat Petroleum Corporation Ltd",
        "price": 432.10,
        "change": -5.60,
        "changePercent": -1.28,
    },
    {
        "symbol": "IOC",
        "name": "Indian Oil Corporation Ltd",
        "price": 123.40,
        "change": 2.30,
        "changePercent": 1.90,
    },
    {
        "symbol": "PIDILITIND",
        "name": "Pidilite Industries Ltd",
        "price": 2876.50,
        "change": 34.20,
        "changePercent": 1.20,
    },
    {
        "symbol": "SBILIFE",
        "name": "SBI Life Insurance Company Ltd",
        "price": 1543.80,
        "change": 18.90,
        "changePercent": 1.24,
    },
    {
        "symbol": "VEDL",
        "name": "Vedanta Ltd",
        "price": 345.60,
        "change": -4.50,
        "changePercent": -1.29,
    },
    {
        "symbol": "TATACONSUM",
        "name": "Tata Consumer Products Ltd",
        "price": 987.60,
        "change": 12.30,
        "changePercent": 1.26,
    },
]


@router.get("/symbols/search")
@limiter.limit(symbols_limit)
async def search_symbols(
    request: Request,
    q: str = Query("", description="Search query"),
    limit: int = Query(20, description="Maximum number of results", ge=1, le=100),
) -> Dict[str, Any]:
    """
    Search for stock symbols.

    Args:
        q: Search query (symbol or company name)
        limit: Maximum number of results (1-100)

    Returns:
        List of matching symbols with current price and change data
    """
    try:
        query = q.lower().strip()

        # If no query, return popular symbols
        if not query:
            symbols = NSE_SYMBOLS[:limit]
            return {"symbols": symbols, "total": len(symbols)}

        # Filter symbols by query (matches symbol or name)
        filtered = [
            symbol
            for symbol in NSE_SYMBOLS
            if query in symbol["symbol"].lower() or query in symbol["name"].lower()
        ]

        # Limit results
        limited = filtered[:limit]

        logger.info(
            f"Symbol search: q='{q}', found {len(filtered)} matches, returning {len(limited)}"
        )

        return {"symbols": limited, "total": len(filtered)}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "search_symbols")
