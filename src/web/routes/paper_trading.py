"""Paper trading account and position routes - ALL REAL DATA."""

import logging
import os
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
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

# Global container reference for legacy compatibility
_container = None

def set_container(container):
    """Set container reference for this module."""
    global _container
    _container = container

limiter = Limiter(key_func=get_remote_address)

paper_trading_limit = os.getenv("RATE_LIMIT_PAPER_TRADING", "20/minute")


# ============================================================================
# ACCOUNT MANAGEMENT ENDPOINTS - Phase 1 Implementation (REAL DATA)
# ============================================================================

@router.post("/paper-trading/accounts/create")
@limiter.limit(paper_trading_limit)
async def create_paper_trading_account(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Create a new paper trading account."""
    try:
        account_manager = await container.get("paper_trading_account_manager")

        # Parse request body
        body = await request.json()
        account_name = body.get("account_name", "Paper Trading Account")
        initial_balance = body.get("initial_balance", 100000.0)
        strategy_type = body.get("strategy_type", "swing")

        # Import AccountType enum
        from src.models.paper_trading import AccountType, RiskLevel

        # Map strategy_type string to enum
        strategy_map = {
            "swing": AccountType.SWING,
            "day": AccountType.DAY_TRADING,
            "options": AccountType.OPTIONS,
        }
        strategy_enum = strategy_map.get(strategy_type.lower(), AccountType.SWING)

        # Create account
        account = await account_manager.create_account(
            account_name=account_name,
            initial_balance=initial_balance,
            strategy_type=strategy_enum,
            risk_level=RiskLevel.MODERATE
        )

        logger.info(f"Created new paper trading account: {account.account_id}")

        return {
            "success": True,
            "account": {
                "accountId": account.account_id,
                "accountName": account.account_name,
                "initialBalance": account.initial_balance,
                "currentBalance": account.current_balance,
                "strategyType": strategy_type,
                "createdAt": account.created_at.isoformat() if hasattr(account, 'created_at') else datetime.now(timezone.utc).isoformat()
            }
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "create_paper_trading_account")


@router.delete("/paper-trading/accounts/{account_id}")
@limiter.limit(paper_trading_limit)
async def delete_paper_trading_account(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Delete a paper trading account."""
    try:
        store = await container.get("paper_trading_store")

        # Get account to verify it exists
        account = await store.get_account(account_id)
        if not account:
            return {
                "success": False,
                "error": f"Account {account_id} not found"
            }

        # Check if there are open positions
        open_trades = await store.get_open_trades(account_id)
        if open_trades:
            return {
                "success": False,
                "error": f"Cannot delete account with {len(open_trades)} open positions. Close all positions first."
            }

        # Delete account from database
        await store.db_connection.execute(
            "DELETE FROM paper_trading_accounts WHERE account_id = ?",
            (account_id,)
        )
        await store.db_connection.commit()

        logger.info(f"Deleted paper trading account: {account_id}")

        return {
            "success": True,
            "message": f"Account {account_id} deleted successfully"
        }

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "delete_paper_trading_account")


@router.get("/paper-trading/accounts")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_accounts(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get all paper trading accounts - REAL DATA from database."""
    try:
        account_manager = await container.get("paper_trading_account_manager")

        # Get all accounts from database
        all_accounts = await account_manager.get_all_accounts()

        # If no accounts exist, create default account
        if not all_accounts:
            default_account = await account_manager.create_account(
                account_name="Paper Trading - Swing Trading",
                initial_balance=100000.0,
                account_id="paper_swing_main"
            )
            all_accounts = [default_account]
            logger.info("Created default paper trading account")

        # Format accounts for frontend
        accounts = []
        for acc in all_accounts:
            # Get positions to calculate deployed capital
            positions = await account_manager.get_open_positions(acc.account_id)
            deployed_capital = sum(pos.entry_price * pos.quantity for pos in positions)

            accounts.append({
                "accountId": acc.account_id,
                "accountType": acc.strategy_type.value if hasattr(acc.strategy_type, 'value') else str(acc.strategy_type),
                "currency": "INR",
                "createdDate": acc.created_at.isoformat() if hasattr(acc, 'created_at') else datetime.now(timezone.utc).isoformat(),
                "initialCapital": acc.initial_balance,
                "currentBalance": acc.current_balance,
                "totalInvested": deployed_capital,
                "marginAvailable": acc.buying_power
            })

        logger.info(f"Retrieved {len(accounts)} paper trading accounts from database")
        return {"accounts": accounts}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_accounts")


@router.get("/paper-trading/accounts/{account_id}/overview")
@limiter.limit(paper_trading_limit)
async def get_paper_trading_account_overview(
    request: Request,
    account_id: str,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get paper trading account overview with REAL account data."""
    try:
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

        # Get open positions
        positions = await account_manager.get_open_positions(account_id)
        open_positions_count = len(positions)

        # Calculate deployed capital
        deployed_capital = sum(pos.entry_price * pos.quantity for pos in positions)

        # Get closed trades for today
        store = await container.get("paper_trading_store")
        today = datetime.now(timezone.utc).date()
        all_closed = await store.get_closed_trades(account_id)
        closed_today = [t for t in all_closed if t.exit_timestamp and t.exit_timestamp.date() == today]

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
            "closedTodayCount": len(closed_today)
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
        account_manager = await container.get("paper_trading_account_manager")

        # Fetch open positions with real-time prices from Zerodha
        positions_data = await account_manager.get_open_positions(account_id)

        # Convert to dict format
        positions = []
        for pos in positions_data:
            positions.append({
                "trade_id": pos.trade_id,
                "symbol": pos.symbol,
                "entryDate": pos.entry_date,
                "entryPrice": pos.entry_price,
                "quantity": pos.quantity,
                "ltp": pos.current_price,  # Real-time price from Zerodha!
                "pnl": pos.unrealized_pnl,  # Calculated with current price
                "pnlPercent": pos.unrealized_pnl_pct,
                "daysHeld": pos.days_held,
                "target": pos.target_price,
                "stopLoss": pos.stop_loss,
                "strategy": pos.strategy_rationale,
                "currentValue": pos.current_value,
                "tradeType": pos.trade_type
            })

        logger.info(f"Retrieved {len(positions)} open positions for account {account_id} with real-time Zerodha prices")
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
    """Get REAL closed trades for paper trading account from database."""
    try:
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
    """Get REAL performance data calculated from actual trades."""
    try:
        account_manager = await container.get("paper_trading_account_manager")
        performance_calculator = await container.get("performance_calculator")
        store = await container.get("paper_trading_store")

        # Get real performance metrics
        metrics = await account_manager.get_performance_metrics(account_id, period=period)

        # Get all closed trades for advanced metrics calculation
        all_trades = await store.get_closed_trades(account_id)

        # Calculate max drawdown
        max_drawdown = 0.0
        if all_trades:
            max_drawdown = performance_calculator.calculate_max_drawdown([
                trade.realized_pnl for trade in all_trades
            ])

        # Calculate volatility (std dev of returns)
        volatility = 0.0
        if len(all_trades) > 1:
            returns = [trade.realized_pnl_pct for trade in all_trades]
            import statistics
            volatility = statistics.stdev(returns)

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
            "maxDrawdown": max_drawdown,
            "sharpeRatio": metrics.get("sharpe_ratio"),
            "volatility": volatility,
            "benchmarkReturn": 0,  # TODO: Add benchmark comparison (NIFTY 50)
            "alpha": 0  # TODO: Add alpha calculation vs benchmark
        }

        logger.info(f"Retrieved performance metrics for {account_id} (period={period}): Total P&L=₹{metrics.get('total_pnl', 0)}, Win Rate={metrics.get('win_rate', 0)}%")
        return {"performance": performance_data}

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_paper_trading_performance")


# ============================================================================
# TRADE EXECUTION ENDPOINTS - Phase 1 Implementation (REAL EXECUTION)
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
    Execute a buy trade on a paper trading account with REAL market prices.

    Uses MarketDataService (Zerodha Kite SDK) for real-time pricing.
    """
    try:
        execution_service = await container.get("paper_trading_execution_service")

        # Execute trade with real market price
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
    Execute a sell trade on a paper trading account with REAL market prices.

    Uses MarketDataService (Zerodha Kite SDK) for real-time pricing.
    """
    try:
        execution_service = await container.get("paper_trading_execution_service")

        # Execute trade with real market price
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
    Close an existing open trade with REAL market exit price.

    Uses MarketDataService (Zerodha Kite SDK) for real-time exit pricing.
    """
    try:
        execution_service = await container.get("paper_trading_execution_service")

        # Close trade with real market price
        result = await execution_service.close_trade(
            account_id=account_id,
            trade_id=trade_id
        )

        return result

    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "close_trade")
