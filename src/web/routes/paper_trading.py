"""Paper trading account and position routes."""

import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["paper-trading"])
limiter = Limiter(key_func=get_remote_address)

paper_trading_limit = os.getenv("RATE_LIMIT_PAPER_TRADING", "20/minute")


@router.get("/paper-trading/account")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_account(request: Request) -> Dict[str, Any]:
    """Get paper trading account overview."""
    try:
        return {
            "accountId": "swing-001",
            "accountType": "paper_trading",
            "currency": "INR",
            "createdDate": "2025-01-01",
            "initialCapital": 100000,
            "currentBalance": 102500,
            "totalInvested": 75000,
            "marginAvailable": 27500
        }
    except Exception as e:
        logger.error(f"Paper trading account retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/paper-trading/accounts/{account_id}/status")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_account_status(request: Request, account_id: str) -> Dict[str, Any]:
    """Get specific paper trading account status."""
    try:
        account_type = "swing" if "swing" in account_id else "options"
        if account_type == "swing":
            return {
                "accountId": account_id,
                "balance": 102500,
                "todayPnL": 500,
                "monthlyROI": 2.5,
                "winRate": 65,
                "activeStrategy": "Momentum + RSI",
                "cashAvailable": 27500,
                "deployedCapital": 75000,
                "openPositions": 5,
                "closedTodayCount": 2
            }
        else:  # options
            return {
                "accountId": account_id,
                "balance": 98500,
                "premiumCollected": 5500,
                "premiumPaid": 2000,
                "monthlyROI": -1.5,
                "hedgeEffectiveness": 92,
                "openPositions": 3,
                "maxLoss": 8000,
                "breakEvenRange": "±2%"
            }
    except Exception as e:
        logger.error(f"Paper trading account status retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/paper-trading/accounts/{account_id}/open-positions")
@limiter.limit(paper_trading_limit)
async def get_open_positions(request: Request, account_id: str) -> Dict[str, Any]:
    """Get open positions for paper trading account."""
    try:
        positions = [
            {
                "symbol": "HDFC",
                "entryDate": "2025-10-20",
                "entryPrice": 2750,
                "quantity": 10,
                "ltp": 2800,
                "pnl": 500,
                "pnlPercent": 1.82,
                "daysHeld": 4,
                "target": 2900,
                "stopLoss": 2650
            },
            {
                "symbol": "INFY",
                "entryDate": "2025-10-22",
                "entryPrice": 3150,
                "quantity": 5,
                "ltp": 3200,
                "pnl": 250,
                "pnlPercent": 1.59,
                "daysHeld": 2,
                "target": 3350,
                "stopLoss": 3050
            },
            {
                "symbol": "TCS",
                "entryDate": "2025-10-21",
                "entryPrice": 4450,
                "quantity": 3,
                "ltp": 4420,
                "pnl": -90,
                "pnlPercent": -0.67,
                "daysHeld": 3,
                "target": 4650,
                "stopLoss": 4350
            }
        ]
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Open positions retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/paper-trading/accounts/{account_id}/closed-trades")
@limiter.limit(paper_trading_limit)
async def get_closed_trades(request: Request, account_id: str) -> Dict[str, Any]:
    """Get closed trades for paper trading account."""
    try:
        trades = [
            {
                "date": "2025-10-24",
                "symbol": "RELIANCE",
                "entryPrice": 2950,
                "exitPrice": 2980,
                "quantity": 5,
                "holdTime": "2h 30m",
                "pnl": 150,
                "pnlPercent": 1.02,
                "strategy": "Momentum Breakout",
                "notes": "Good breakout confirmation"
            },
            {
                "date": "2025-10-23",
                "symbol": "SBIN",
                "entryPrice": 620,
                "exitPrice": 615,
                "quantity": 10,
                "holdTime": "4h 15m",
                "pnl": -50,
                "pnlPercent": -0.81,
                "strategy": "RSI Support",
                "notes": "Failed to hold support"
            },
            {
                "date": "2025-10-22",
                "symbol": "MARUTI",
                "entryPrice": 13200,
                "exitPrice": 13450,
                "quantity": 2,
                "holdTime": "1h 45m",
                "pnl": 500,
                "pnlPercent": 1.89,
                "strategy": "RSI Support Bounce",
                "notes": "Perfect bounce entry"
            }
        ]
        return {"trades": trades}
    except Exception as e:
        logger.error(f"Closed trades retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
