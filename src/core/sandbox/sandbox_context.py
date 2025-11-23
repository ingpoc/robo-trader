"""
Sandbox Context - Risk-Bounded Pre-Approval

Based on Anthropic's sandboxing research for Claude Code.
Pre-validates operations within defined risk boundaries.

Token Savings: ~100 tokens per operation (eliminates async validation)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Dict, List, Optional, Set, Tuple, Any

logger = logging.getLogger(__name__)


@dataclass
class SandboxBoundary:
    """
    Risk boundaries for sandbox operations.

    Operations within these boundaries are auto-approved.
    Operations exceeding boundaries require explicit approval.
    """

    # Position limits
    max_position_size_pct: float = 5.0
    max_symbol_exposure_pct: float = 15.0

    # Daily limits
    max_daily_trades: int = 10
    max_daily_loss_pct: float = 3.0

    # Symbol controls
    allowed_symbols: List[str] = field(default_factory=list)
    blocked_symbols: List[str] = field(default_factory=list)

    # Time controls
    market_hours_only: bool = True

    # Mode controls
    paper_trading_only: bool = True

    # Auto-approve thresholds (operations below these are always approved)
    auto_approve_qty_threshold: int = 100  # Shares
    auto_approve_value_threshold: float = 50000.0  # INR


@dataclass
class SandboxOperation:
    """Record of an operation within sandbox."""
    operation: str  # "buy", "sell", "close"
    symbol: str
    quantity: int
    price: float
    timestamp: datetime
    approved: bool
    reason: Optional[str] = None


class SandboxContext:
    """
    Pre-approval context for operations within boundaries.

    Reduces token usage by:
    - Pre-validating common operations without async calls
    - Caching approval decisions
    - Tracking daily limits locally
    """

    def __init__(self, boundary: SandboxBoundary, environment: str = "paper"):
        self.boundary = boundary
        self.environment = environment
        self._operations: List[SandboxOperation] = []
        self._approved_symbols_cache: Set[str] = set(boundary.allowed_symbols)
        self._daily_pnl: float = 0.0

    def is_operation_approved(
        self,
        operation: str,
        symbol: str,
        quantity: int,
        price: float,
        portfolio_value: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if operation is within sandbox boundaries (sync, no DB calls).

        Token savings: ~100 tokens vs async validation

        Returns:
            (approved, reason) - True if within sandbox, False with reason if not
        """
        # 1. Paper trading mode check
        if self.boundary.paper_trading_only and self.environment != "paper":
            return False, "Sandbox only allows paper trading"

        # 2. Market hours check (simple IST check)
        if self.boundary.market_hours_only:
            if not self._is_market_hours():
                return False, "Outside market hours"

        # 3. Symbol whitelist check
        if self.boundary.allowed_symbols:
            if symbol not in self._approved_symbols_cache:
                return False, f"Symbol {symbol} not in approved list"

        # 4. Symbol blacklist check
        if symbol in self.boundary.blocked_symbols:
            return False, f"Symbol {symbol} is blocked"

        # 5. Auto-approve threshold (small trades always OK)
        if quantity <= self.boundary.auto_approve_qty_threshold:
            order_value = quantity * price
            if order_value <= self.boundary.auto_approve_value_threshold:
                self._log_operation(operation, symbol, quantity, price, True)
                return True, None

        # 6. Position size check
        if portfolio_value > 0:
            position_pct = (quantity * price) / portfolio_value * 100
            if position_pct > self.boundary.max_position_size_pct:
                return False, f"Position {position_pct:.1f}% exceeds max {self.boundary.max_position_size_pct}%"

        # 7. Daily trade count check
        today_trades = self._get_today_trade_count()
        if today_trades >= self.boundary.max_daily_trades:
            return False, f"Daily trade limit ({self.boundary.max_daily_trades}) reached"

        # 8. Daily loss check
        if self._daily_pnl < 0:
            loss_pct = abs(self._daily_pnl) / portfolio_value * 100 if portfolio_value > 0 else 0
            if loss_pct >= self.boundary.max_daily_loss_pct:
                return False, f"Daily loss limit ({self.boundary.max_daily_loss_pct}%) reached"

        # All checks passed - approved within sandbox
        self._log_operation(operation, symbol, quantity, price, True)
        return True, None

    def update_daily_pnl(self, pnl: float) -> None:
        """Update daily P&L for loss limit tracking."""
        self._daily_pnl = pnl

    def add_approved_symbol(self, symbol: str) -> None:
        """Add symbol to approved list (from portfolio)."""
        self._approved_symbols_cache.add(symbol)

    def sync_portfolio_symbols(self, symbols: List[str]) -> None:
        """Sync approved symbols with current portfolio."""
        self._approved_symbols_cache = set(symbols)
        logger.debug(f"Sandbox symbols synced: {len(symbols)} symbols")

    def reset_daily(self) -> None:
        """Reset daily counters (call at market open)."""
        self._operations = [
            op for op in self._operations
            if op.timestamp.date() == date.today()
        ]
        self._daily_pnl = 0.0
        logger.info("Sandbox daily counters reset")

    def get_stats(self) -> Dict[str, Any]:
        """Get sandbox statistics."""
        today_ops = [op for op in self._operations if op.timestamp.date() == date.today()]
        return {
            "today_trades": len(today_ops),
            "approved_symbols": len(self._approved_symbols_cache),
            "daily_pnl": self._daily_pnl,
            "environment": self.environment,
            "remaining_trades": max(0, self.boundary.max_daily_trades - len(today_ops))
        }

    def _get_today_trade_count(self) -> int:
        """Count today's trades."""
        today = date.today()
        return sum(1 for op in self._operations if op.timestamp.date() == today)

    def _log_operation(
        self,
        operation: str,
        symbol: str,
        quantity: int,
        price: float,
        approved: bool,
        reason: Optional[str] = None
    ) -> None:
        """Log operation for audit trail."""
        self._operations.append(SandboxOperation(
            operation=operation,
            symbol=symbol,
            quantity=quantity,
            price=price,
            timestamp=datetime.now(),
            approved=approved,
            reason=reason
        ))

    @staticmethod
    def _is_market_hours() -> bool:
        """Check if within NSE market hours (9:15 AM - 3:30 PM IST)."""
        from datetime import timezone, timedelta

        now = datetime.now(timezone.utc)
        # Convert to IST (UTC+5:30)
        ist = now + timedelta(hours=5, minutes=30)

        # Weekday check
        if ist.weekday() >= 5:  # Saturday/Sunday
            return False

        # Time check (9:15 AM to 3:30 PM)
        market_open = ist.replace(hour=9, minute=15, second=0)
        market_close = ist.replace(hour=15, minute=30, second=0)

        return market_open <= ist <= market_close


# Global sandbox context (lazily initialized)
_global_sandbox: Optional[SandboxContext] = None


def get_sandbox_context() -> Optional[SandboxContext]:
    """Get global sandbox context."""
    return _global_sandbox


def create_default_sandbox_boundary() -> SandboxBoundary:
    """Create default sandbox boundary for paper trading."""
    return SandboxBoundary(
        max_position_size_pct=5.0,
        max_symbol_exposure_pct=15.0,
        max_daily_trades=10,
        max_daily_loss_pct=3.0,
        allowed_symbols=[],  # Will be populated from portfolio
        blocked_symbols=[],
        market_hours_only=True,
        paper_trading_only=True,
        auto_approve_qty_threshold=100,
        auto_approve_value_threshold=50000.0
    )


def initialize_sandbox(
    boundary: Optional[SandboxBoundary] = None,
    environment: str = "paper"
) -> SandboxContext:
    """Initialize global sandbox context."""
    global _global_sandbox

    if boundary is None:
        boundary = create_default_sandbox_boundary()

    _global_sandbox = SandboxContext(boundary, environment)
    logger.info(f"Sandbox initialized for {environment} environment")

    return _global_sandbox
