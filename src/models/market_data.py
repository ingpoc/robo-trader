"""
Market Data Models

Defines data structures for market data, providers, and subscriptions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime


class MarketDataProvider(Enum):
    """Market data provider types."""
    ZERODHA_KITE = "zerodha_kite"
    UPSTOX = "upstox"
    YAHOO_FINANCE = "yahoo_finance"
    ALPHA_VANTAGE = "alpha_vantage"


class SubscriptionMode(Enum):
    """Market data subscription modes."""
    QUOTE = "quote"
    FULL = "full"
    LTP = "ltp"


@dataclass
class MarketData:
    """Market data snapshot."""
    symbol: str
    ltp: float
    open_price: Optional[float] = None
    high_price: Optional[float] = None
    low_price: Optional[float] = None
    close_price: Optional[float] = None
    volume: Optional[int] = None
    timestamp: str = ""
    provider: str = ""


@dataclass
class MarketDataSubscription:
    """Market data subscription request."""
    symbol: str
    mode: SubscriptionMode
    provider: MarketDataProvider
    exchange: str = "NSE"


@dataclass
class OHLCV:
    """OHLCV candle data."""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    provider: str = ""


@dataclass
class MarketTick:
    """Individual market tick."""
    symbol: str
    timestamp: datetime
    price: float
    volume: int
    exchange: str = ""
    provider: str = ""