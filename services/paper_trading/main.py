"""
Paper Trading Service
Standalone FastAPI service for paper trading functionality
"""

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List

from fastapi import FastAPI, HTTPException, Request, Depends
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.models.paper_trading import PaperTradingAccount, AccountType, RiskLevel
from src.stores.paper_trading_store import PaperTradingStore
from src.services.paper_trading.account_manager import PaperTradingAccountManager
from src.services.paper_trading.trade_executor import PaperTradeExecutor
from src.core.di import DependencyContainer
from src.config import Config

# ============================================================================
# CONFIGURATION
# ============================================================================

logger = logging.getLogger(__name__)

SERVICE_NAME = os.getenv("SERVICE_NAME", "paper-trading")
SERVICE_PORT = int(os.getenv("SERVICE_PORT", 8008))

# ============================================================================
# GLOBAL STATE
# ============================================================================

container: Optional[DependencyContainer] = None
store: Optional[PaperTradingStore] = None
account_manager: Optional[PaperTradingAccountManager] = None
trade_executor: Optional[PaperTradeExecutor] = None

# Rate limiter
limiter = Limiter(key_func=get_remote_address)

# ============================================================================
# MODELS (copied from paper_trading_api.py)
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


class HealthCheck(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    checks: Dict[str, str] = Field(default_factory=dict, description="Individual component health checks")


# ============================================================================
# FASTAPI APP
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifecycle management"""
    global container, store, account_manager, trade_executor

    logger.info(f"🚀 Starting {SERVICE_NAME} service...")

    try:
        # Initialize configuration
        config = Config()

        # Initialize dependency container
        container = DependencyContainer()
        await container.initialize(config)

        # Get paper trading components
        store = await container.get("paper_trading_store")
        account_manager = await container.get("paper_trading_account_manager")
        trade_executor = await container.get("paper_trade_executor")

        # Seed default account for demo/testing if it doesn't exist
        from src.models.paper_trading import AccountType, RiskLevel
        try:
            existing = await account_manager.get_account("paper_swing_main")
            if not existing:
                logger.info("Seeding default paper trading account...")
                await account_manager.create_account(
                    account_name="Paper Trading - Swing Trading Account",
                    initial_balance=100000.0,
                    strategy_type=AccountType.SWING,
                    risk_level=RiskLevel.MODERATE,
                    max_position_size=5.0,
                    max_portfolio_risk=10.0,
                    account_id="paper_swing_main"
                )
                logger.info("✅ Default paper trading account 'paper_swing_main' seeded successfully with ₹100,000 capital")
        except Exception as e:
            logger.warning(f"Could not seed default account: {e}")

        logger.info(f"✅ {SERVICE_NAME} service started")

    except Exception as e:
        logger.error(f"❌ Failed to start {SERVICE_NAME}: {e}")
        raise

    yield

    # Shutdown
    logger.info(f"🛑 Shutting down {SERVICE_NAME} service...")

    try:
        if container:
            await container.cleanup()

        logger.info(f"✅ {SERVICE_NAME} service stopped")

    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


app = FastAPI(
    title=f"{SERVICE_NAME} API",
    description="Paper trading account and position management",
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================================
# DEPENDENCY FUNCTIONS
# ============================================================================

async def get_container_dependency():
    """Get DI container for dependency injection."""
    if not container:
        raise HTTPException(status_code=500, detail="Application not properly initialized")
    return container


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """Health check endpoint"""
    checks = {}

    # Check components
    checks["container"] = "healthy" if container else "not initialized"
    checks["store"] = "healthy" if store else "not initialized"
    checks["account_manager"] = "healthy" if account_manager else "not initialized"
    checks["trade_executor"] = "healthy" if trade_executor else "not initialized"

    # Determine overall status
    status = "healthy" if all(check == "healthy" for check in checks.values()) else "unhealthy"

    return HealthCheck(
        status=status,
        service=SERVICE_NAME,
        checks=checks,
    )


@app.get("/accounts/{account_id}/overview", response_model=AccountOverviewResponse)
@limiter.limit("30/minute")
async def get_account_overview(
    account_id: str,
    request: Request,
    container=Depends(get_container_dependency),
) -> AccountOverviewResponse:
    """
    Get overview of a paper trading account.

    Returns current balance, P&L, and portfolio metrics.
    """
    try:
        logger.info(f"Fetching account overview: {account_id}")

        account = await account_manager.get_account(account_id)

        if not account:
            raise HTTPException(status_code=404, detail=f"Account not found: {account_id}")

        balance_info = await account_manager.get_account_balance(account_id)

        return AccountOverviewResponse(
            account_id=account_id,
            account_type=account.strategy_type.value,
            strategy_type=account.strategy_type.value,
            balance=balance_info.get("current_balance", 0),
            buying_power=balance_info.get("buying_power", 0),
            deployed_capital=balance_info.get("deployed_capital", 0),
            total_pnl=account.total_pnl or 0,
            total_pnl_pct=account.total_pnl_pct or 0,
            monthly_pnl=account.monthly_pnl or 0,
            monthly_pnl_pct=account.monthly_pnl_pct or 0,
            open_positions_count=account.open_positions_count or 0,
            today_trades=account.today_trades or 0,
            win_rate=account.win_rate or 0,
            created_at=account.created_at if isinstance(account.created_at, str) else account.created_at.isoformat() if account.created_at else datetime.utcnow().isoformat(),
            reset_date=account.reset_date or "",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get account overview: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get account overview: {str(e)}")


@app.get("/accounts/{account_id}/positions", response_model=List[OpenPositionResponse])
@limiter.limit("30/minute")
async def get_open_positions(
    account_id: str,
    request: Request,
    container=Depends(get_container_dependency),
) -> List[OpenPositionResponse]:
    """
    Get all open positions for an account.

    Returns list of currently open trades with real-time P&L.
    """
    try:
        logger.info(f"Fetching open positions: {account_id}")

        positions = await account_manager.get_open_positions(account_id)

        return positions

    except Exception as e:
        logger.error(f"Failed to get open positions: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get positions: {str(e)}")


@app.get("/accounts/{account_id}/trades", response_model=List[ClosedTradeResponse])
@limiter.limit("30/minute")
async def get_trade_history(
    account_id: str,
    request: Request,
    container=Depends(get_container_dependency),
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

        trades = await account_manager.get_closed_trades(
            account_id, month=month, year=year, symbol=symbol, limit=limit
        )

        return trades

    except Exception as e:
        logger.error(f"Failed to get trade history: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get trades: {str(e)}")


@app.post("/accounts/{account_id}/trades/buy", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def execute_buy(
    account_id: str,
    trade_request: ExecuteBuyRequest,
    request: Request,
    container=Depends(get_container_dependency),
) -> Dict[str, Any]:
    """
    Execute a BUY trade on the paper trading account.

    Validates buying power and position size limits before execution.
    """
    try:
        logger.info(f"Executing BUY trade: {account_id} {trade_request.symbol}")

        result = await trade_executor.execute_buy(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            entry_price=trade_request.entry_price,
            strategy_rationale=trade_request.strategy_rationale,
            claude_session_id="",  # Not available in standalone service
            stop_loss=trade_request.stop_loss,
            target_price=trade_request.target_price,
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


@app.post("/accounts/{account_id}/trades/sell", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def execute_sell(
    account_id: str,
    trade_request: ExecuteSellRequest,
    request: Request,
    container=Depends(get_container_dependency),
) -> Dict[str, Any]:
    """
    Execute a SELL trade on the paper trading account.

    Only allows selling existing positions.
    """
    try:
        logger.info(f"Executing SELL trade: {account_id} {trade_request.symbol}")

        result = await trade_executor.execute_sell(
            account_id=account_id,
            symbol=trade_request.symbol,
            quantity=trade_request.quantity,
            exit_price=trade_request.exit_price,
            strategy_rationale=trade_request.strategy_rationale,
            claude_session_id="",  # Not available in standalone service
            stop_loss=trade_request.stop_loss,
            target_price=trade_request.target_price,
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


@app.post("/trades/{trade_id}/close", response_model=Dict[str, Any])
@limiter.limit("10/minute")
async def close_position(
    trade_id: str,
    close_request: ClosePositionRequest,
    request: Request,
    container=Depends(get_container_dependency),
) -> Dict[str, Any]:
    """
    Close an open position.

    Calculates realized P&L and updates account balance.
    """
    try:
        logger.info(f"Closing position: {trade_id}")

        result = await trade_executor.close_position(
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
                "realized_pnl_pct": result.get("pnl_percentage", 0),
            }
        else:
            return {
                "success": False,
                "message": result.get("error", "Failed to close position"),
            }

    except Exception as e:
        logger.error(f"Failed to close position: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to close position: {str(e)}")


@app.get("/accounts/{account_id}/performance", response_model=PerformanceMetricsResponse)
@limiter.limit("20/minute")
async def get_performance_metrics(
    account_id: str,
    request: Request,
    container=Depends(get_container_dependency),
    period: str = "all-time",
) -> PerformanceMetricsResponse:
    """
    Get performance metrics for an account.

    Periods: today, week, month, all-time
    """
    try:
        logger.info(f"Fetching performance metrics: {account_id} ({period})")

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


@app.post("/accounts/{account_id}/reset-monthly", response_model=Dict[str, Any])
@limiter.limit("2/minute")
async def reset_monthly(
    account_id: str,
    reset_request: MonthlyResetRequest,
    request: Request,
    container=Depends(get_container_dependency),
) -> Dict[str, Any]:
    """
    Reset monthly paper trading account.

    Closes all positions, resets balance to initial capital, preserves learnings.
    """
    try:
        if not reset_request.confirmation:
            raise HTTPException(status_code=400, detail="Reset confirmation required")

        logger.info(f"Resetting monthly account: {account_id}")

        result = await account_manager.reset_monthly(account_id)

        return {
            "success": True,
            "message": "Account reset successfully",
            "account_id": account_id,
            "previous_balance": result.initial_balance if result else 0,
            "new_balance": result.current_balance if result else 0,
            "learnings_preserved": reset_request.preserve_learnings,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to reset account: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to reset account: {str(e)}")


# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions"""
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "code": str(exc.status_code),
            "service": SERVICE_NAME,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions"""
    from fastapi.responses import JSONResponse
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "code": "500",
            "service": SERVICE_NAME,
        }
    )


if __name__ == "__main__":
    import uvicorn

    # Setup logging
    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=SERVICE_PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
    )