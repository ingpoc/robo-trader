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


@router.get("/paper-trading/accounts")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_accounts(request: Request) -> Dict[str, Any]:
    """Get all paper trading accounts - matches frontend expectation."""
    try:
        return {
            "accounts": [
                {
                    "accountId": "swing-001",
                    "accountType": "swing",
                    "currency": "INR",
                    "createdDate": "2025-01-01",
                    "initialCapital": 100000,
                    "currentBalance": 102500,
                    "totalInvested": 75000,
                    "marginAvailable": 27500
                },
                {
                    "accountId": "options-001",
                    "accountType": "options",
                    "currency": "INR",
                    "createdDate": "2025-01-01",
                    "initialCapital": 100000,
                    "currentBalance": 98500,
                    "totalInvested": 55000,
                    "marginAvailable": 43500
                }
            ]
        }
    except Exception as e:
        logger.error(f"Paper trading accounts retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


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


@router.get("/paper-trading/accounts/{account_id}/overview")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_account_overview(request: Request, account_id: str) -> Dict[str, Any]:
    """Get paper trading account overview - matches frontend expectation."""
    try:
        account_type = "swing" if "swing" in account_id else "options"
        if account_type == "swing":
            return {
                "accountId": account_id,
                "accountType": "swing",
                "currency": "INR",
                "createdDate": "2025-01-01",
                "initialCapital": 100000,
                "currentBalance": 102500,
                "totalInvested": 75000,
                "marginAvailable": 27500,
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
                "accountType": "options",
                "currency": "INR",
                "createdDate": "2025-01-01",
                "initialCapital": 100000,
                "currentBalance": 98500,
                "totalInvested": 55000,
                "marginAvailable": 43500,
                "premiumCollected": 5500,
                "premiumPaid": 2000,
                "monthlyROI": -1.5,
                "hedgeEffectiveness": 92,
                "openPositions": 3,
                "maxLoss": 8000,
                "breakEvenRange": "±2%"
            }
    except Exception as e:
        logger.error(f"Paper trading account overview retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/paper-trading/accounts/{account_id}/positions")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_positions(request: Request, account_id: str) -> Dict[str, Any]:
    """Get positions for paper trading account - matches frontend expectation."""
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
                "stopLoss": 2650,
                "strategy": "Momentum Breakout"
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
                "stopLoss": 3050,
                "strategy": "RSI Support"
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
                "stopLoss": 4350,
                "strategy": "Support Bounce"
            }
        ]
        return {"positions": positions}
    except Exception as e:
        logger.error(f"Paper trading positions retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/paper-trading/accounts/{account_id}/trades")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_trades(request: Request, account_id: str, limit: int = 50) -> Dict[str, Any]:
    """Get trades for paper trading account - matches frontend expectation."""
    try:
        trades = [
            {
                "id": "trade_1",
                "date": "2025-10-24",
                "symbol": "RELIANCE",
                "action": "BUY",
                "entryPrice": 2950,
                "exitPrice": 2980,
                "quantity": 5,
                "holdTime": "2h 30m",
                "pnl": 150,
                "pnlPercent": 1.02,
                "strategy": "Momentum Breakout",
                "notes": "Good breakout confirmation",
                "status": "closed"
            },
            {
                "id": "trade_2",
                "date": "2025-10-23",
                "symbol": "SBIN",
                "action": "SELL",
                "entryPrice": 620,
                "exitPrice": 615,
                "quantity": 10,
                "holdTime": "4h 15m",
                "pnl": -50,
                "pnlPercent": -0.81,
                "strategy": "RSI Support",
                "notes": "Failed to hold support",
                "status": "closed"
            },
            {
                "id": "trade_3",
                "date": "2025-10-22",
                "symbol": "MARUTI",
                "action": "BUY",
                "entryPrice": 13200,
                "exitPrice": 13450,
                "quantity": 2,
                "holdTime": "1h 45m",
                "pnl": 500,
                "pnlPercent": 1.89,
                "strategy": "RSI Support Bounce",
                "notes": "Perfect bounce entry",
                "status": "closed"
            }
        ]
        return {"trades": trades[:limit]}
    except Exception as e:
        logger.error(f"Paper trading trades retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/paper-trading/accounts/{account_id}/performance")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_performance(request: Request, account_id: str, period: str = "all-time") -> Dict[str, Any]:
    """Get performance data for paper trading account - matches frontend expectation."""
    try:
        account_type = "swing" if "swing" in account_id else "options"

        if period == "30d":
            performance_data = {
                "period": "30d",
                "totalReturn": 2.5,
                "totalReturnPercent": 2.5,
                "winRate": 65,
                "totalTrades": 12,
                "winningTrades": 8,
                "losingTrades": 4,
                "avgWin": 450,
                "avgLoss": -320,
                "profitFactor": 1.8,
                "maxDrawdown": -1200,
                "sharpeRatio": 1.2,
                "volatility": 8.5,
                "benchmarkReturn": 1.8,
                "alpha": 0.7
            }
        elif period == "all-time":
            performance_data = {
                "period": "all-time",
                "totalReturn": 2500,
                "totalReturnPercent": 2.5,
                "winRate": 65,
                "totalTrades": 45,
                "winningTrades": 29,
                "losingTrades": 16,
                "avgWin": 420,
                "avgLoss": -280,
                "profitFactor": 1.9,
                "maxDrawdown": -2500,
                "sharpeRatio": 1.1,
                "volatility": 9.2,
                "benchmarkReturn": 1.5,
                "alpha": 1.0
            }
        else:
            performance_data = {
                "period": period,
                "totalReturn": 0,
                "totalReturnPercent": 0,
                "winRate": 0,
                "totalTrades": 0,
                "winningTrades": 0,
                "losingTrades": 0,
                "avgWin": 0,
                "avgLoss": 0,
                "profitFactor": 0,
                "maxDrawdown": 0,
                "sharpeRatio": 0,
                "volatility": 0,
                "benchmarkReturn": 0,
                "alpha": 0
            }

        return {"performance": performance_data}
    except Exception as e:
        logger.error(f"Paper trading performance retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
