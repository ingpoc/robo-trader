"""Pydantic models for trade request validation."""

from pydantic import BaseModel, Field
from typing import Optional


class BuyTradeRequest(BaseModel):
    """Validated buy trade request."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol (e.g., TCS)")
    quantity: int = Field(..., gt=0, le=10000, description="Number of shares to buy")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$", description="Order type")
    price: Optional[float] = Field(None, gt=0, description="Limit price (for LIMIT orders)")

    class Config:
        example = {
            "symbol": "TCS",
            "quantity": 10,
            "order_type": "MARKET",
            "price": None
        }


class SellTradeRequest(BaseModel):
    """Validated sell trade request."""

    symbol: str = Field(..., min_length=1, max_length=20, description="Stock symbol (e.g., TCS)")
    quantity: int = Field(..., gt=0, le=10000, description="Number of shares to sell")
    order_type: str = Field(default="MARKET", pattern="^(MARKET|LIMIT)$", description="Order type")
    price: Optional[float] = Field(None, gt=0, description="Limit price (for LIMIT orders)")

    class Config:
        example = {
            "symbol": "TCS",
            "quantity": 5,
            "order_type": "MARKET",
            "price": None
        }


class CloseTradeRequest(BaseModel):
    """Validated close trade request."""

    trade_id: str = Field(..., min_length=1, description="Trade ID to close")

    class Config:
        example = {
            "trade_id": "trade_001"
        }
