"""Monthly Reset Monitor - Handles monthly capital resets for paper trading accounts.

Runs daily and checks if it's the 1st of the month. If so:
1. Saves current balance to monthly performance history
2. Resets capital to initial amount (₹1,00,000)
3. Preserves closed trades and strategy learnings
4. Emits account reset event
"""

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import aiofiles
import aiofiles.os
from loguru import logger


@dataclass
class MonthlyPerformanceHistory:
    """Record of monthly performance."""

    month: str  # "2024-10" format
    initial_balance: float
    final_balance: float
    profit_loss: float
    profit_loss_percentage: float
    trades_count: int
    winning_trades: int
    win_rate: float
    best_trade: float
    worst_trade: float
    max_drawdown: float
    recorded_at: str


class MonthlyResetMonitor:
    """Monitors and executes monthly account resets."""

    def __init__(self, config):
        """Initialize monthly reset monitor.

        Args:
            config: Application configuration
        """
        self.config = config
        self.state_dir = config.state_dir / "monthly_resets"
        self.history_file = self.state_dir / "monthly_performance_history.json"

        # In-memory cache
        self._history: list[MonthlyPerformanceHistory] = []
        self._last_reset_month: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the monthly reset monitor."""
        try:
            await aiofiles.os.makedirs(str(self.state_dir), exist_ok=True)
            await self._load_history()
            logger.info("Monthly Reset Monitor initialized")
        except Exception as e:
            logger.error(f"Failed to initialize monthly reset monitor: {e}")

    async def _load_history(self) -> None:
        """Load historical monthly performance data."""
        try:
            if await aiofiles.os.path.exists(str(self.history_file)):
                async with aiofiles.open(str(self.history_file), "r") as f:
                    content = await f.read()
                    data = json.loads(content)
                    self._history = [MonthlyPerformanceHistory(**item) for item in data]
                logger.debug(
                    f"Loaded {len(self._history)} months of performance history"
                )
        except Exception as e:
            logger.warning(f"Could not load monthly performance history: {e}")

    async def check_and_execute_reset(
        self,
        account_manager,
        current_balance: float,
        initial_balance: float,
        closed_trades: list,
        account_type: str = "swing",
    ) -> Optional[Dict[str, Any]]:
        """Check if reset is needed and execute if so.

        Args:
            account_manager: PaperTradingAccountManager instance
            current_balance: Current account balance
            initial_balance: Initial account balance (e.g., 100,000)
            closed_trades: List of closed trades in current month
            account_type: Account type ("swing" or "options")

        Returns:
            Reset result if executed, None otherwise
        """
        today = datetime.now(timezone.utc)
        current_month = today.strftime("%Y-%m")

        # Check if already reset this month
        if self._last_reset_month == current_month:
            return None

        # Check if today is 1st of month
        if today.day != 1:
            return None

        # Execute reset
        logger.info(
            f"Monthly reset triggered for {account_type} account ({current_month})"
        )

        result = await self._execute_reset(
            account_manager,
            current_balance,
            initial_balance,
            closed_trades,
            account_type,
            current_month,
        )

        self._last_reset_month = current_month
        return result

    async def _execute_reset(
        self,
        account_manager,
        current_balance: float,
        initial_balance: float,
        closed_trades: list,
        account_type: str,
        month: str,
    ) -> Dict[str, Any]:
        """Execute the monthly reset process.

        Steps:
        1. Calculate monthly performance metrics
        2. Save to history
        3. Reset capital
        4. Emit reset event
        """
        try:
            # Calculate performance metrics
            profit_loss = current_balance - initial_balance
            profit_loss_pct = (
                (profit_loss / initial_balance * 100) if initial_balance > 0 else 0
            )

            # Trade statistics
            trade_count = len(closed_trades)
            winning_trades = sum(
                1
                for t in closed_trades
                if t.exit_price and t.exit_price > t.entry_price
            )
            win_rate = (winning_trades / trade_count * 100) if trade_count > 0 else 0

            # Calculate best/worst trades
            best_trade = 0.0
            worst_trade = 0.0
            if closed_trades:
                pnls = [
                    (t.exit_price - t.entry_price) * t.quantity
                    for t in closed_trades
                    if t.exit_price
                ]
                best_trade = max(pnls) if pnls else 0
                worst_trade = min(pnls) if pnls else 0

            # Calculate max drawdown (simplified)
            max_dd = await self._calculate_max_drawdown(closed_trades, initial_balance)

            # Create history record
            history_record = MonthlyPerformanceHistory(
                month=month,
                initial_balance=initial_balance,
                final_balance=current_balance,
                profit_loss=profit_loss,
                profit_loss_percentage=profit_loss_pct,
                trades_count=trade_count,
                winning_trades=winning_trades,
                win_rate=win_rate,
                best_trade=best_trade,
                worst_trade=worst_trade,
                max_drawdown=max_dd,
                recorded_at=datetime.now(timezone.utc).isoformat(),
            )

            # Save to history
            self._history.append(history_record)
            await self._save_history()

            # Reset capital in account manager
            await account_manager.reset_capital(account_type, initial_balance)

            result = {
                "status": "success",
                "month": month,
                "account_type": account_type,
                "previous_balance": current_balance,
                "reset_balance": initial_balance,
                "profit_loss": profit_loss,
                "profit_loss_percentage": f"{profit_loss_pct:.2f}%",
                "trades_count": trade_count,
                "win_rate": f"{win_rate:.1f}%",
                "best_trade": best_trade,
                "worst_trade": worst_trade,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            logger.info(
                f"Monthly reset completed for {account_type}: "
                f"Balance {current_balance:.0f} → {initial_balance:.0f} "
                f"(P&L: {profit_loss:+.0f} / {profit_loss_pct:+.1f}%)"
            )

            return result

        except Exception as e:
            logger.error(f"Monthly reset failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

    async def _calculate_max_drawdown(
        self, closed_trades: list, initial_balance: float
    ) -> float:
        """Calculate maximum drawdown during the month.

        Args:
            closed_trades: List of closed trades
            initial_balance: Starting balance

        Returns:
            Maximum drawdown percentage
        """
        if not closed_trades:
            return 0.0

        # Simulate balance progression
        running_balance = initial_balance
        peak_balance = initial_balance
        max_drawdown = 0.0

        for trade in sorted(closed_trades, key=lambda t: t.entry_timestamp):
            if trade.exit_price:
                pnl = (trade.exit_price - trade.entry_price) * trade.quantity
                running_balance += pnl

                # Update peak
                if running_balance > peak_balance:
                    peak_balance = running_balance

                # Calculate drawdown
                drawdown = peak_balance - running_balance
                if drawdown > max_drawdown:
                    max_drawdown = drawdown

        max_drawdown_pct = (
            (max_drawdown / initial_balance * 100) if initial_balance > 0 else 0
        )
        return max_drawdown_pct

    async def get_performance_history(
        self, months: Optional[int] = None
    ) -> list[Dict[str, Any]]:
        """Get performance history for past months.

        Args:
            months: Number of months to return (None = all)

        Returns:
            List of monthly performance records
        """
        records = self._history
        if months:
            records = records[-months:]

        return [
            {
                "month": r.month,
                "initial_balance": r.initial_balance,
                "final_balance": r.final_balance,
                "profit_loss": r.profit_loss,
                "profit_loss_percentage": f"{r.profit_loss_percentage:.2f}%",
                "trades_count": r.trades_count,
                "winning_trades": r.winning_trades,
                "win_rate": f"{r.win_rate:.1f}%",
                "best_trade": r.best_trade,
                "worst_trade": r.worst_trade,
                "max_drawdown": f"{r.max_drawdown:.2f}%",
                "recorded_at": r.recorded_at,
            }
            for r in records
        ]

    async def get_yearly_summary(self, year: Optional[str] = None) -> Dict[str, Any]:
        """Get summary for entire year.

        Args:
            year: Year in format "2024" (None = current year)

        Returns:
            Yearly performance summary
        """
        if not year:
            year = datetime.now().strftime("%Y")

        yearly_records = [r for r in self._history if r.month.startswith(year)]

        if not yearly_records:
            return {"year": year, "status": "no_data"}

        total_pnl = sum(r.profit_loss for r in yearly_records)
        total_trades = sum(r.trades_count for r in yearly_records)
        total_wins = sum(r.winning_trades for r in yearly_records)

        avg_pnl_pct = sum(r.profit_loss_percentage for r in yearly_records) / len(
            yearly_records
        )
        avg_win_rate = sum(r.win_rate for r in yearly_records) / len(yearly_records)

        return {
            "year": year,
            "months_traded": len(yearly_records),
            "total_trades": total_trades,
            "total_wins": total_wins,
            "total_pnl": total_pnl,
            "average_monthly_pnl_percentage": f"{avg_pnl_pct:.2f}%",
            "average_win_rate": f"{avg_win_rate:.1f}%",
            "best_month": (
                max(yearly_records, key=lambda r: r.profit_loss).month
                if yearly_records
                else None
            ),
            "worst_month": (
                min(yearly_records, key=lambda r: r.profit_loss).month
                if yearly_records
                else None
            ),
        }

    async def _save_history(self) -> None:
        """Save monthly performance history to file."""
        try:
            data = [
                {
                    "month": r.month,
                    "initial_balance": r.initial_balance,
                    "final_balance": r.final_balance,
                    "profit_loss": r.profit_loss,
                    "profit_loss_percentage": r.profit_loss_percentage,
                    "trades_count": r.trades_count,
                    "winning_trades": r.winning_trades,
                    "win_rate": r.win_rate,
                    "best_trade": r.best_trade,
                    "worst_trade": r.worst_trade,
                    "max_drawdown": r.max_drawdown,
                    "recorded_at": r.recorded_at,
                }
                for r in self._history
            ]

            # Use atomic write
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", delete=False, dir=str(self.state_dir)
            ) as tmp:
                json.dump(data, tmp, indent=2)
                tmp_path = tmp.name

            await aiofiles.os.replace(tmp_path, str(self.history_file))
        except Exception as e:
            logger.error(f"Failed to save monthly performance history: {e}")
