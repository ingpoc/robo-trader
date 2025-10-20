"""Paper Trading API routes for account and position management."""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/paper-trading", tags=["Paper Trading"])

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


# ============================================================================
# Request/Response Models
# ============================================================================


class AccountOverviewResponse(BaseModel):
    """Overview of a paper trading account."""

    account_id: str = Field(..., description="Unique account identifier")
    account_type: str = Field(..., description="Account type: swing_trading, options_trading")
    strategy_type: str = Field(..., description="Strategy type")
    balance: float = Field(..., description="Current account balance (₹)")
    buying_power: float = Field(..., description="Available buying power (₹)")
    deployed_capital: float = Field(..., description="Deployed capital in open positions (₹)")
    total_pnl: float = Field(..., description="Total realized P&L (₹)")
    total_pnl_pct: float = Field(..., description="Total P&L percentage")
    monthly_pnl: float = Field(..., description="Current month P&L (₹)")
    monthly_pnl_pct: float = Field(..., description="Current month P&L percentage")
    open_positions_count: int = Field(..., description="Number of open positions")
    today_trades: int = Field(..., description="Trades executed today")
    win_rate: float = Field(..., description="Win rate percentage")
    created_at: str = Field(..., description="Account creation date")
    reset_date: str = Field(..., description="Next monthly reset date")


class OpenPositionResponse(BaseModel):
    """Details of an open trading position."""

    trade_id: str = Field(..., description="Unique trade ID")
    symbol: str = Field(..., description="Stock symbol")
    trade_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares")
    entry_price: float = Field(..., description="Entry price (₹)")
    current_price: float = Field(..., description="Current market price (₹)")
    current_value: float = Field(..., description="Current position value (₹)")
    unrealized_pnl: float = Field(..., description="Unrealized P&L (₹)")
    unrealized_pnl_pct: float = Field(..., description="Unrealized P&L percentage")
    stop_loss: Optional[float] = Field(None, description="Stop-loss price if set")
    target_price: Optional[float] = Field(None, description="Target price if set")
    entry_date: str = Field(..., description="Entry date and time")
    days_held: int = Field(..., description="Days position has been open")
    strategy_rationale: str = Field(..., description="Reason for the trade")
    ai_suggested: bool = Field(default=False, description="Was this AI recommended?")


class ClosedTradeResponse(BaseModel):
    """Details of a closed trade."""

    trade_id: str = Field(..., description="Unique trade ID")
    symbol: str = Field(..., description="Stock symbol")
    trade_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares")
    entry_price: float = Field(..., description="Entry price (₹)")
    exit_price: float = Field(..., description="Exit price (₹)")
    realized_pnl: float = Field(..., description="Realized P&L (₹)")
    realized_pnl_pct: float = Field(..., description="Realized P&L percentage")
    entry_date: str = Field(..., description="Entry date")
    exit_date: str = Field(..., description="Exit date")
    holding_period_days: int = Field(..., description="How long position was held")
    reason_closed: str = Field(..., description="Reason for closing (target/stoploss/manual)")
    strategy_rationale: str = Field(..., description="Original trade rationale")
    ai_suggested: bool = Field(default=False, description="Was this AI suggested?")


class ExecuteBuyRequest(BaseModel):
    """Request to execute a BUY trade."""

    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares to buy")
    entry_price: float = Field(..., description="Entry price (₹)")
    strategy_rationale: str = Field(..., description="Why this trade?")
    stop_loss: Optional[float] = Field(None, description="Stop-loss price")
    target_price: Optional[float] = Field(None, description="Target price")
    ai_suggested: bool = Field(default=False, description="Is this AI suggested?")


class ExecuteSellRequest(BaseModel):
    """Request to execute a SELL trade."""

    symbol: str = Field(..., description="Stock symbol")
    quantity: int = Field(..., description="Number of shares to sell")
    exit_price: float = Field(..., description="Exit price (₹)")
    strategy_rationale: str = Field(..., description="Why this trade?")
    stop_loss: Optional[float] = Field(None, description="Stop-loss price")
    target_price: Optional[float] = Field(None, description="Target price")
    ai_suggested: bool = Field(default=False, description="Is this AI suggested?")


class ClosePositionRequest(BaseModel):
    """Request to close an open position."""

    exit_price: float = Field(..., description="Price at which to close")
    reason: str = Field(default="Manual exit", description="Reason for closing")


class MonthlyResetRequest(BaseModel):
    """Request to reset monthly account."""

    confirmation: bool = Field(..., description="User confirmation to reset")
    preserve_learnings: bool = Field(default=True, description="Preserve learnings from month")


class PerformanceMetricsResponse(BaseModel):
    """Performance metrics for the account."""

    total_trades: int = Field(..., description="Total trades executed")
    winning_trades: int = Field(..., description="Trades that were profitable")
    losing_trades: int = Field(..., description="Trades that lost money")
    win_rate: float = Field(..., description="Win rate percentage")
    avg_win: float = Field(..., description="Average winning trade (₹)")
    avg_loss: float = Field(..., description="Average losing trade (₹)")
    profit_factor: float = Field(..., description="Gross profit / Gross loss")
    largest_win: float = Field(..., description="Largest winning trade (₹)")
    largest_loss: float = Field(..., description="Largest losing trade (₹)")
    sharpe_ratio: Optional[float] = Field(None, description="Sharpe ratio if applicable")
    period: str = Field(..., description="Period covered (today/week/month/all-time)")


# ============================================================================
# Dependency Functions
# ============================================================================


async def _initialize_default_account(container):
    """Initialize default paper trading account if it doesn't exist."""
    try:
        import aiosqlite
        from pathlib import Path
        import uuid
        from datetime import datetime

        # Get SQLite database path (typically in project root as robo_trader_paper_trading.db)
        db_path = Path(__file__).parent.parent.parent / "robo_trader_paper_trading.db"

        async with aiosqlite.connect(str(db_path)) as db:
            # Initialize schema first
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paper_trading_accounts (
                    account_id TEXT PRIMARY KEY,
                    account_name TEXT NOT NULL,
                    initial_balance REAL NOT NULL,
                    current_balance REAL NOT NULL,
                    buying_power REAL NOT NULL,
                    strategy_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    max_position_size REAL NOT NULL,
                    max_portfolio_risk REAL NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    month_start_date TEXT NOT NULL,
                    monthly_pnl REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    trade_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_timestamp TEXT NOT NULL,
                    strategy_rationale TEXT NOT NULL,
                    claude_session_id TEXT,
                    exit_price REAL,
                    exit_timestamp TEXT,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    status TEXT NOT NULL DEFAULT 'open',
                    stop_loss REAL,
                    target_price REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Check if default account exists
            default_account_id = "paper_swing_main"
            cursor = await db.execute(
                "SELECT account_id FROM paper_trading_accounts WHERE account_id = ?",
                (default_account_id,)
            )
            existing = await cursor.fetchone()

            if not existing:
                # Create default account with ₹1L capital
                now = datetime.utcnow().isoformat()
                today = datetime.utcnow().strftime("%Y-%m-%d")

                await db.execute("""
                    INSERT INTO paper_trading_accounts (
                        account_id, account_name, initial_balance, current_balance, buying_power,
                        strategy_type, risk_level, max_position_size, max_portfolio_risk,
                        is_active, month_start_date, monthly_pnl, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    default_account_id,
                    "Paper Trading - Swing",
                    100000.0,  # ₹1L
                    100000.0,  # ₹1L
                    100000.0,  # ₹1L
                    "swing",
                    "moderate",
                    5.0,  # 5% max position size
                    10.0,  # 10% max portfolio risk
                    1,  # is_active
                    today,
                    0.0,  # monthly_pnl
                    now,
                    now
                ))

                await db.commit()
                logger.info(f"✓ Created default paper trading account: {default_account_id} with ₹100,000 capital")
            else:
                logger.debug(f"Paper trading account already exists: {default_account_id}")

    except Exception as e:
        logger.warning(f"Could not initialize default paper trading account: {e}")
        # Don't raise - let request proceed without default account


async def get_container(request: Request):
    """Get DI container from request state."""
    if not hasattr(request.app.state, "container"):
        raise HTTPException(status_code=500, detail="Application not properly initialized")

    container = request.app.state.container

    # Initialize default account on first request
    if not hasattr(request.app.state, "_paper_trading_initialized"):
        await _initialize_default_account(container)
        request.app.state._paper_trading_initialized = True

    return container


# ============================================================================
# API Endpoints
# ============================================================================


@router.get("/accounts/{account_id}/overview", response_model=AccountOverviewResponse)
@limiter.limit("30/minute")
async def get_account_overview(
    account_id: str,
    request: Request,
    container=Depends(get_container),
) -> AccountOverviewResponse:
    """
    Get overview of a paper trading account.

    Returns current balance, P&L, and portfolio metrics.
    """
    try:
        logger.info(f"Fetching account overview: {account_id}")

        account_manager = await container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)

        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

        balance_info = await account_manager.get_account_balance(account_id)

        return AccountOverviewResponse(
            account_id=account_id,
            account_type=account.get("account_type", "swing_trading"),
            strategy_type=account.get("strategy_type", "momentum"),
            balance=balance_info.get("balance", 0),
            buying_power=balance_info.get("buying_power", 0),
            deployed_capital=balance_info.get("deployed_capital", 0),
            total_pnl=account.get("total_pnl", 0),
            total_pnl_pct=account.get("total_pnl_pct", 0),
            monthly_pnl=account.get("monthly_pnl", 0),
            monthly_pnl_pct=account.get("monthly_pnl_pct", 0),
            open_positions_count=account.get("open_positions_count", 0),
            today_trades=account.get("today_trades", 0),
            win_rate=account.get("win_rate", 0),
            created_at=account.get("created_at", datetime.utcnow().isoformat()),
            reset_date=account.get("reset_date", ""),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get account overview: {str(e)}")


@router.get("/accounts/{account_id}/positions", response_model=List[OpenPositionResponse])
@limiter.limit("30/minute")
async def get_open_positions(
    account_id: str,
    request: Request,
    container=Depends(get_container),
) -> List[OpenPositionResponse]:
    """
    Get all open positions for an account.

    Returns list of currently open trades with real-time P&L.
    """
    try:
        logger.info(f"Fetching open positions: {account_id}")

        account_manager = await container.get("paper_trading_account_manager")
        positions = await account_manager.get_open_positions(account_id)

        position_responses = []
        for pos in positions:
            position_responses.append(
                OpenPositionResponse(
                    trade_id=pos.get("trade_id", ""),
                    symbol=pos.get("symbol", ""),
                    trade_type=pos.get("trade_type", "BUY"),
                    quantity=pos.get("quantity", 0),
                    entry_price=pos.get("entry_price", 0),
                    current_price=pos.get("current_price", 0),
                    current_value=pos.get("current_value", 0),
                    unrealized_pnl=pos.get("unrealized_pnl", 0),
                    unrealized_pnl_pct=pos.get("unrealized_pnl_pct", 0),
                    stop_loss=pos.get("stop_loss"),
                    target_price=pos.get("target_price"),
                    entry_date=pos.get("entry_date", ""),
                    days_held=pos.get("days_held", 0),
                    strategy_rationale=pos.get("strategy_rationale", ""),
                    ai_suggested=pos.get("ai_suggested", False),
                )
            )

        return position_responses

    except Exception as e:
        logger.error(f"Failed to get open positions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@router.get("/accounts/{account_id}/trades", response_model=List[ClosedTradeResponse])
@limiter.limit("30/minute")
async def get_trade_history(
    account_id: str,
    request: Request,
    container=Depends(get_container),
    month: Optional[int] = None,
    year: Optional[int] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
) -> List[ClosedTradeResponse]:
    """
    Get closed trade history for an account.

    Supports filtering by month, year, and symbol.
    """
    try:
        logger.info(f"Fetching trade history: {account_id}")

        account_manager = await container.get("paper_trading_account_manager")
        trades = await account_manager.get_closed_trades(
            account_id, month=month, year=year, symbol=symbol, limit=limit
        )

        trade_responses = []
        for trade in trades:
            trade_responses.append(
                ClosedTradeResponse(
                    trade_id=trade.get("trade_id", ""),
                    symbol=trade.get("symbol", ""),
                    trade_type=trade.get("trade_type", "BUY"),
                    quantity=trade.get("quantity", 0),
                    entry_price=trade.get("entry_price", 0),
                    exit_price=trade.get("exit_price", 0),
                    realized_pnl=trade.get("realized_pnl", 0),
                    realized_pnl_pct=trade.get("realized_pnl_pct", 0),
                    entry_date=trade.get("entry_date", ""),
                    exit_date=trade.get("exit_date", ""),
                    holding_period_days=trade.get("holding_period_days", 0),
                    reason_closed=trade.get("reason_closed", ""),
                    strategy_rationale=trade.get("strategy_rationale", ""),
                    ai_suggested=trade.get("ai_suggested", False),
                )
            )

        return trade_responses

    except Exception as e:
        logger.error(f"Failed to get trade history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trades: {str(e)}")


@router.post("/accounts/{account_id}/trades/buy", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def execute_buy(
    account_id: str,
    trade_request: ExecuteBuyRequest,
    request: Request,
    container=Depends(get_container),
) -> Dict[str, Any]:
    """
    Execute a BUY trade on the paper trading account.

    Validates buying power and position size limits before execution.
    """
    try:
        logger.info(f"Executing BUY trade: {account_id} {trade_request.symbol}")

        executor = await container.get("paper_trade_executor")

        result = await executor.execute_buy(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            entry_price=trade_request.entry_price,
            strategy_rationale=trade_request.strategy_rationale,
            stop_loss=trade_request.stop_loss,
            target_price=trade_request.target_price,
            ai_suggested=trade_request.ai_suggested,
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"BUY trade executed for {trade_request.symbol}",
                "trade_id": result.get("trade_id"),
                "quantity": trade_request.quantity,
                "entry_price": trade_request.entry_price,
                "total_value": trade_request.quantity * trade_request.entry_price,
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Trade execution failed"),
                "reason": result.get("reason"),
            }

    except Exception as e:
        logger.error(f"Failed to execute BUY trade: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {str(e)}")


@router.post("/accounts/{account_id}/trades/sell", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def execute_sell(
    account_id: str,
    trade_request: ExecuteSellRequest,
    request: Request,
    container=Depends(get_container),
) -> Dict[str, Any]:
    """
    Execute a SELL trade on the paper trading account.

    Only allows selling existing positions.
    """
    try:
        logger.info(f"Executing SELL trade: {account_id} {trade_request.symbol}")

        executor = await container.get("paper_trade_executor")

        result = await executor.execute_sell(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            exit_price=trade_request.exit_price,
            strategy_rationale=trade_request.strategy_rationale,
            stop_loss=trade_request.stop_loss,
            target_price=trade_request.target_price,
            ai_suggested=trade_request.ai_suggested,
        )

        if result.get("success"):
            return {
                "success": True,
                "message": f"SELL trade executed for {trade_request.symbol}",
                "trade_id": result.get("trade_id"),
                "quantity": trade_request.quantity,
                "exit_price": trade_request.exit_price,
                "total_proceeds": trade_request.quantity * trade_request.exit_price,
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Trade execution failed"),
                "reason": result.get("reason"),
            }

    except Exception as e:
        logger.error(f"Failed to execute SELL trade: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {str(e)}")


@router.post("/trades/{trade_id}/close", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def close_position(
    trade_id: str,
    close_request: ClosePositionRequest,
    request: Request,
    container=Depends(get_container),
) -> Dict[str, Any]:
    """
    Close an open position.

    Calculates realized P&L and updates account balance.
    """
    try:
        logger.info(f"Closing position: {trade_id}")

        executor = await container.get("paper_trade_executor")

        result = await executor.close_position(
            trade_id=trade_id,
            exit_price=close_request.exit_price,
            reason=close_request.reason,
        )

        if result.get("success"):
            return {
                "success": True,
                "message": "Position closed successfully",
                "trade_id": trade_id,
                "realized_pnl": result.get("realized_pnl", 0),
                "realized_pnl_pct": result.get("realized_pnl_pct", 0),
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Failed to close position"),
            }

    except Exception as e:
        logger.error(f"Failed to close position: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")


@router.get("/accounts/{account_id}/performance", response_model=PerformanceMetricsResponse)
@limiter.limit("20/minute")
async def get_performance_metrics(
    account_id: str,
    request: Request,
    container=Depends(get_container),
    period: str = "all-time",
) -> PerformanceMetricsResponse:
    """
    Get performance metrics for an account.

    Periods: today, week, month, all-time
    """
    try:
        logger.info(f"Fetching performance metrics: {account_id} ({period})")

        account_manager = await container.get("paper_trading_account_manager")
        metrics = await account_manager.get_performance_metrics(account_id, period=period)

        return PerformanceMetricsResponse(
            total_trades=metrics.get("total_trades", 0),
            winning_trades=metrics.get("winning_trades", 0),
            losing_trades=metrics.get("losing_trades", 0),
            win_rate=metrics.get("win_rate", 0),
            avg_win=metrics.get("avg_win", 0),
            avg_loss=metrics.get("avg_loss", 0),
            profit_factor=metrics.get("profit_factor", 0),
            largest_win=metrics.get("largest_win", 0),
            largest_loss=metrics.get("largest_loss", 0),
            sharpe_ratio=metrics.get("sharpe_ratio"),
            period=period,
        )

    except Exception as e:
        logger.error(f"Failed to get performance metrics: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")


@router.post("/accounts/{account_id}/reset-monthly", response_model=Dict[str, Any])
@limiter.limit("2/minute")
async def reset_monthly(
    account_id: str,
    reset_request: MonthlyResetRequest,
    request: Request,
    container=Depends(get_container),
) -> Dict[str, Any]:
    """
    Reset monthly paper trading account.

    Closes all positions, resets balance to initial capital, preserves learnings.
    """
    try:
        if not reset_request.confirmation:
            raise HTTPException(status_code=400, detail="Reset confirmation required")

        logger.info(f"Resetting monthly account: {account_id}")

        account_manager = await container.get("paper_trading_account_manager")
        result = await account_manager.reset_monthly(
            account_id, preserve_learnings=reset_request.preserve_learnings
        )

        return {
            "success": True,
            "message": "Account reset successfully",
            "account_id": account_id,
            "previous_balance": result.get("previous_balance"),
            "new_balance": result.get("new_balance"),
            "learnings_preserved": reset_request.preserve_learnings,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset account: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset account: {str(e)}")
