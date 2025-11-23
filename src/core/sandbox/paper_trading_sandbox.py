"""
Paper Trading Sandbox - Auto-Approve Paper Trades

Auto-approves paper trading operations within risk boundaries.
No real financial impact, so trades can execute without confirmation.

Token Savings: ~150 tokens per paper trade (no approval workflow)
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from .sandbox_context import SandboxContext, SandboxBoundary, get_sandbox_context

logger = logging.getLogger(__name__)


@dataclass
class PaperTradeSandboxResult:
    """Result of paper trading sandbox check."""
    approved: bool
    reason: Optional[str] = None
    auto_approved: bool = False
    checks_passed: int = 0


class PaperTradingSandbox:
    """
    Sandbox for paper trading operations.

    Auto-approves trades that:
    1. Are within position size limits
    2. Don't exceed daily trade count
    3. Are for approved symbols
    4. Are during market hours (optional)

    All paper trades are simulation-only, so no real risk.
    """

    def __init__(self, sandbox_context: Optional[SandboxContext] = None):
        self.sandbox = sandbox_context or get_sandbox_context()
        self._paper_trades_today: int = 0
        self._last_reset: datetime = datetime.now()

    async def check_trade(
        self,
        symbol: str,
        action: str,  # "buy" or "sell"
        quantity: int,
        price: float,
        portfolio_value: float = 100000.0
    ) -> PaperTradeSandboxResult:
        """
        Check if paper trade should be auto-approved.

        Token savings: ~150 tokens (no approval queue interaction)

        Returns:
            PaperTradeSandboxResult with approval status
        """
        checks_passed = 0

        # No sandbox context - deny for safety
        if not self.sandbox:
            logger.warning("Paper trading sandbox check failed: no sandbox context")
            return PaperTradeSandboxResult(
                approved=False,
                reason="Sandbox not initialized",
                auto_approved=False
            )

        # Use sandbox context for validation
        approved, reason = self.sandbox.is_operation_approved(
            operation=action.lower(),
            symbol=symbol,
            quantity=quantity,
            price=price,
            portfolio_value=portfolio_value
        )

        if approved:
            checks_passed = 8  # All checks passed
            logger.info(f"Paper trade auto-approved: {action} {quantity} {symbol} @ {price}")
            return PaperTradeSandboxResult(
                approved=True,
                reason=None,
                auto_approved=True,
                checks_passed=checks_passed
            )
        else:
            logger.info(f"Paper trade needs review: {reason}")
            return PaperTradeSandboxResult(
                approved=False,
                reason=reason,
                auto_approved=False,
                checks_passed=checks_passed
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get paper trading sandbox stats."""
        sandbox_stats = self.sandbox.get_stats() if self.sandbox else {}
        return {
            "paper_trades_today": self._paper_trades_today,
            "last_reset": self._last_reset.isoformat(),
            **sandbox_stats
        }


# Module-level convenience function
async def check_paper_trade_sandbox(
    tool_input: Dict[str, Any],
    portfolio_value: float = 100000.0
) -> Tuple[bool, Optional[str]]:
    """
    Convenience function to check paper trade in hooks.

    Args:
        tool_input: Tool input from MCP call
        portfolio_value: Current portfolio value for sizing check

    Returns:
        (approved, reason) tuple
    """
    sandbox = get_sandbox_context()
    if not sandbox:
        return False, "Sandbox not initialized"

    symbol = tool_input.get("symbol", "")
    action = tool_input.get("action", tool_input.get("side", "buy"))
    quantity = tool_input.get("quantity", tool_input.get("qty", 0))
    price = tool_input.get("entry_price", tool_input.get("price", 0))

    if not all([symbol, quantity, price]):
        return False, "Missing required fields: symbol, quantity, price"

    return sandbox.is_operation_approved(
        operation=action.lower(),
        symbol=symbol,
        quantity=quantity,
        price=price,
        portfolio_value=portfolio_value
    )
