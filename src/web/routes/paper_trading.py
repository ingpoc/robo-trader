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
async def get_paper_trading_trades(
    request: Request,
    account_id: str,
    limit: int = 50,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get REAL closed trades for paper trading account."""
    try:
        # Get account manager from DI container
        account_manager = await container.get("paper_trading_account_manager")

        # Fetch real closed trades from database
        closed_trades = await account_manager.get_closed_trades(
            account_id=account_id,
            limit=limit
        )

        # Convert to frontend format
        trades = []
        for trade in closed_trades:
            # Calculate hold time in readable format
            hold_days = trade.holding_period_days
            if hold_days < 1:
                hold_time = "< 1 day"
            elif hold_days == 1:
                hold_time = "1 day"
            else:
                hold_time = f"{hold_days} days"

            trades.append({
                "id": trade.trade_id,
                "date": trade.exit_date,
                "symbol": trade.symbol,
                "action": trade.trade_type,
                "entryPrice": trade.entry_price,
                "exitPrice": trade.exit_price,
                "quantity": trade.quantity,
                "holdTime": hold_time,
                "pnl": trade.realized_pnl,
                "pnlPercent": trade.realized_pnl_pct,
                "strategy": trade.strategy_rationale,
                "notes": trade.reason_closed,
                "status": "closed"
            })

        logger.info(f"Retrieved {len(trades)} closed trades for account {account_id}")
        return {"trades": trades}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_trades")


@router.get("/paper-trading/accounts/{account_id}/performance")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_performance(
    request: Request,
    account_id: str,
    period: str = "all-time",
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get REAL performance data for paper trading account."""
    try:
        # Get account manager from DI container
        account_manager = await container.get("paper_trading_account_manager")

        # Get real performance metrics
        metrics = await account_manager.get_performance_metrics(account_id, period=period)

        # Format for frontend (camelCase keys)
        performance_data = {
            "period": period,
            "totalReturn": metrics.get("total_pnl", 0),
            "totalReturnPercent": metrics.get("total_pnl_percentage", 0),
            "winRate": metrics.get("win_rate", 0),
            "totalTrades": metrics.get("total_trades", 0),
            "winningTrades": metrics.get("winning_trades", 0),
            "losingTrades": metrics.get("losing_trades", 0),
            "avgWin": metrics.get("avg_win", 0),
            "avgLoss": metrics.get("avg_loss", 0),
            "profitFactor": metrics.get("profit_factor", 0),
            "maxDrawdown": 0,  # TODO: Add drawdown calculation
            "sharpeRatio": metrics.get("sharpe_ratio"),
            "volatility": 0,  # TODO: Add volatility calculation
            "benchmarkReturn": 0,  # TODO: Add benchmark comparison
            "alpha": 0  # TODO: Add alpha calculation
        }

        logger.info(f"Retrieved performance metrics for {account_id} (period={period}): Total P&L=₹{metrics.get('total_pnl', 0)}, Win Rate={metrics.get('win_rate', 0)}%")
        return {"performance": performance_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_performance")


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
