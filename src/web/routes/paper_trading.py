"""Paper trading account and position routes."""

import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.web.models.trade_request import BuyTradeRequest, SellTradeRequest, CloseTradeRequest
from src.core.errors import TradingError
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)

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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


@router.get("/paper-trading/accounts/{account_id}/overview")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_account_overview(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get paper trading account overview with REAL account data."""
    try:
        # Get account manager from DI container
        account_manager = await container.get("paper_trading_account_manager")

        # Fetch account from database
        account = await account_manager.get_account(account_id)

        if not account:
            # If account doesn't exist, create it
            account = await account_manager.create_account(
                account_name=f"Paper Trading Account {account_id}",
                initial_balance=100000.0,
                account_id=account_id
            )
            logger.info(f"Created new paper trading account: {account_id}")

        # Get performance metrics
        metrics = await account_manager.get_performance_metrics(account_id, period="all-time")

        # Get open positions count
        positions = await account_manager.get_open_positions(account_id)
        open_positions_count = len(positions)

        # Calculate deployed capital from open positions
        deployed_capital = sum(pos.entry_price * pos.quantity for pos in positions)

        # Build overview response
        overview = {
            "accountId": account.account_id,
            "accountType": account.strategy_type.value if hasattr(account.strategy_type, 'value') else str(account.strategy_type),
            "currency": "INR",
            "createdDate": account.created_at.isoformat() if hasattr(account, 'created_at') else "2025-01-01",
            "initialCapital": account.initial_balance,
            "currentBalance": account.current_balance,
            "totalInvested": deployed_capital,
            "marginAvailable": account.buying_power,
            "todayPnL": metrics.get("realized_pnl", 0) + metrics.get("unrealized_pnl", 0),
            "monthlyROI": metrics.get("monthly_roi", 0),
            "winRate": metrics.get("win_rate", 0),
            "activeStrategy": "AI-Driven Strategy",
            "cashAvailable": account.buying_power,
            "deployedCapital": deployed_capital,
            "openPositions": open_positions_count,
            "closedTodayCount": 0  # TODO: Calculate from closed trades today
        }

        logger.info(f"Retrieved account overview for {account_id}: Balance=₹{account.current_balance}, Open Positions={open_positions_count}")
        return overview

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_account_overview")


@router.get("/paper-trading/accounts/{account_id}/positions")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_positions(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get positions for paper trading account with REAL-TIME prices and P&L."""
    try:
        # Get account manager from DI container
        account_manager = await container.get("paper_trading_account_manager")

        # Fetch open positions with real-time prices
        # This method fetches current market prices and calculates unrealized P&L!
        positions_data = await account_manager.get_open_positions(account_id)

        # Convert to dict format - field names already match frontend expectations
        positions = []
        for pos in positions_data:
            positions.append({
                "trade_id": pos.trade_id,
                "symbol": pos.symbol,
                "entryDate": pos.entry_date,
                "entryPrice": pos.entry_price,
                "quantity": pos.quantity,
                "ltp": pos.current_price,  # Real-time price from market data!
                "pnl": pos.unrealized_pnl,  # Calculated with current price
                "pnlPercent": pos.unrealized_pnl_pct,
                "daysHeld": pos.days_held,
                "target": pos.target_price,
                "stopLoss": pos.stop_loss,
                "strategy": pos.strategy_rationale,
                "currentValue": pos.current_value,
                "tradeType": pos.trade_type
            })

        logger.info(f"Retrieved {len(positions)} open positions for account {account_id} with real-time prices")
        return {"positions": positions}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_positions")


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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


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
        return await handle_unexpected_error(e, "get_paper_trading_endpoint")


# ============================================================================
# TRADE EXECUTION ENDPOINTS - Phase 1 Implementation
# ============================================================================


@router.post("/paper-trading/accounts/{account_id}/trades/buy")
@limiter.limit(paper_trading_limit)
async def execute_buy_trade(
    request: Request,
    account_id: str,
    trade_request: BuyTradeRequest,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Execute a buy trade on a paper trading account.

    Args:
        account_id: Paper trading account ID (e.g., 'swing-001')
        trade_request: BuyTradeRequest with symbol and quantity

    Returns:
        Trade execution result with trade_id and status
    """
    try:
        # Get execution service
        execution_service = await container.get("paper_trading_execution_service")

        # Execute trade
        result = await execution_service.execute_buy_trade(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            order_type=trade_request.order_type,
            price=trade_request.price
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "execute_buy_trade")


@router.post("/paper-trading/accounts/{account_id}/trades/sell")
@limiter.limit(paper_trading_limit)
async def execute_sell_trade(
    request: Request,
    account_id: str,
    trade_request: SellTradeRequest,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Execute a sell trade on a paper trading account.

    Args:
        account_id: Paper trading account ID (e.g., 'swing-001')
        trade_request: SellTradeRequest with symbol and quantity

    Returns:
        Trade execution result with trade_id, P&L, and status
    """
    try:
        # Get execution service
        execution_service = await container.get("paper_trading_execution_service")

        # Execute trade
        result = await execution_service.execute_sell_trade(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            order_type=trade_request.order_type,
            price=trade_request.price
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "execute_sell_trade")


@router.post("/paper-trading/accounts/{account_id}/trades/{trade_id}/close")
@limiter.limit(paper_trading_limit)
async def close_trade(
    request: Request,
    account_id: str,
    trade_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """
    Close an existing open trade.

    Args:
        account_id: Paper trading account ID
        trade_id: Trade ID to close

    Returns:
        Close operation result with exit price and realized P&L
    """
    try:
        # Get execution service
        execution_service = await container.get("paper_trading_execution_service")

        # Close trade
        result = await execution_service.close_trade(
            account_id=account_id,
            trade_id=trade_id
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "close_trade")
