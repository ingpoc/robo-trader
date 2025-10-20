"""Data models for paper trading accounts and trades."""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class TradeType(str, Enum):
    """Trade execution types."""
    BUY = "buy"
    SELL = "sell"


class TradeStatus(str, Enum):
    """Trade status states."""
    OPEN = "open"
    CLOSED = "closed"
    STOPPED_OUT = "stopped_out"


class AccountType(str, Enum):
    """Paper trading account types."""
    SWING = "swing"
    OPTIONS = "options"
    HYBRID = "hybrid"


class RiskLevel(str, Enum):
    """Risk profile levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class PaperTradingAccount:
    """Paper trading account state."""
    account_id: str
    account_name: str
    initial_balance: float
    current_balance: float
    buying_power: float
    strategy_type: AccountType
    risk_level: RiskLevel
    max_position_size: float  # Percentage
    max_portfolio_risk: float  # Percentage
    is_active: bool
    month_start_date: str
    monthly_pnl: float
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['strategy_type'] = self.strategy_type.value
        d['risk_level'] = self.risk_level.value
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PaperTradingAccount':
        """Create from dictionary."""
        data = data.copy()
        data['strategy_type'] = AccountType(data['strategy_type'])
        data['risk_level'] = RiskLevel(data['risk_level'])
        return PaperTradingAccount(**data)


@dataclass
class PaperTrade:
    """Individual paper trade record."""
    trade_id: str
    account_id: str
    symbol: str
    trade_type: TradeType
    quantity: int
    entry_price: float
    entry_timestamp: str
    strategy_rationale: str
    claude_session_id: str
    exit_price: Optional[float] = None
    exit_timestamp: Optional[str] = None
    realized_pnl: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    status: TradeStatus = TradeStatus.OPEN
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        d = asdict(self)
        d['trade_type'] = self.trade_type.value
        d['status'] = self.status.value
        return d

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'PaperTrade':
        """Create from dictionary."""
        data = data.copy()
        data['trade_type'] = TradeType(data['trade_type'])
        data['status'] = TradeStatus(data['status'])
        return PaperTrade(**data)

    def calculate_pnl(self, current_price: float) -> tuple[float, float]:
        """
        Calculate P&L for open position.

        Returns:
            (unrealized_pnl, pnl_percentage)
        """
        if self.status != TradeStatus.OPEN:
            return self.realized_pnl or 0.0, 0.0

        if self.trade_type == TradeType.BUY:
            pnl = (current_price - self.entry_price) * self.quantity
        else:  # SELL
            pnl = (self.entry_price - current_price) * self.quantity

        pnl_pct = (pnl / (self.entry_price * self.quantity)) * 100 if self.entry_price > 0 else 0.0
        return pnl, pnl_pct

    def is_stop_loss_triggered(self, current_price: float) -> bool:
        """Check if stop loss price is hit."""
        if not self.stop_loss or self.status != TradeStatus.OPEN:
            return False

        if self.trade_type == TradeType.BUY:
            return current_price <= self.stop_loss
        else:  # SELL
            return current_price >= self.stop_loss

    def is_target_hit(self, current_price: float) -> bool:
        """Check if target price is hit."""
        if not self.target_price or self.status != TradeStatus.OPEN:
            return False

        if self.trade_type == TradeType.BUY:
            return current_price >= self.target_price
        else:  # SELL
            return current_price <= self.target_price


@dataclass
class PaperPortfolioSnapshot:
    """Current portfolio snapshot."""
    account_id: str
    total_value: float
    cash: float
    invested: float
    total_pnl: float
    total_pnl_percentage: float
    open_positions: int
    closed_today: int
    daily_pnl: float
    timestamp: str
    holdings: Dict[str, Dict[str, Any]]  # symbol -> {qty, entry_price, current_price, pnl}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)
