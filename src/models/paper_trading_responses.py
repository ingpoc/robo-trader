"""Shared response models for paper-trading services and routes."""

from typing import Optional

from pydantic import BaseModel, Field


class OpenPositionResponse(BaseModel):
    """Details of an open trading position."""

    trade_id: str = Field(..., description="Unique trade ID")
    symbol: str = Field(..., description="Stock symbol")
    trade_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares")
    entry_price: float = Field(..., description="Entry price (INR)")
    current_price: float = Field(..., description="Current market price (INR)")
    current_value: float = Field(..., description="Current position value (INR)")
    unrealized_pnl: float = Field(..., description="Unrealized P&L (INR)")
    unrealized_pnl_pct: float = Field(..., description="Unrealized P&L percentage")
    stop_loss: Optional[float] = Field(None, description="Stop-loss price if set")
    target_price: Optional[float] = Field(None, description="Target price if set")
    entry_date: str = Field(..., description="Entry date and time")
    days_held: int = Field(..., description="Days position has been open")
    strategy_rationale: str = Field(..., description="Reason for the trade")
    ai_suggested: bool = Field(default=False, description="Was this AI recommended?")
    market_price_status: str = Field(default="live", description="Whether the current mark is live or stale")
    market_price_detail: Optional[str] = Field(default=None, description="Explanation when live pricing is unavailable")


class ClosedTradeResponse(BaseModel):
    """Details of a closed trade."""

    trade_id: str = Field(..., description="Unique trade ID")
    symbol: str = Field(..., description="Stock symbol")
    trade_type: str = Field(..., description="BUY or SELL")
    quantity: int = Field(..., description="Number of shares")
    entry_price: float = Field(..., description="Entry price (INR)")
    exit_price: float = Field(..., description="Exit price (INR)")
    realized_pnl: float = Field(..., description="Realized P&L (INR)")
    realized_pnl_pct: float = Field(..., description="Realized P&L percentage")
    entry_date: str = Field(..., description="Entry date")
    exit_date: str = Field(..., description="Exit date")
    holding_period_days: int = Field(..., description="How long position was held")
    reason_closed: str = Field(..., description="Reason for closing")
    strategy_rationale: str = Field(..., description="Original trade rationale")
    ai_suggested: bool = Field(default=False, description="Was this AI suggested?")
