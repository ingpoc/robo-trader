"""Calculate paper trading performance metrics."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...models.paper_trading import PaperTrade

logger = logging.getLogger(__name__)


class PerformanceCalculator:
    """Calculate trading performance metrics."""

    @staticmethod
    def calculate_days_held(
        entry_timestamp: datetime, exit_timestamp: Optional[datetime] = None
    ) -> int:
        """Calculate days held for a trade.

        Args:
            entry_timestamp: When trade was entered
            exit_timestamp: When trade was exited (None for open trades)

        Returns:
            Number of days held
        """
        if exit_timestamp is None:
            exit_timestamp = datetime.now()

        delta = exit_timestamp - entry_timestamp
        return max(1, delta.days)

    @staticmethod
    def calculate_pnl_percentage(entry_price: float, exit_price: float) -> float:
        """Calculate P&L as percentage.

        Args:
            entry_price: Entry price per unit
            exit_price: Exit price per unit

        Returns:
            P&L percentage
        """
        if entry_price == 0:
            return 0.0

        return ((exit_price - entry_price) / entry_price) * 100

    @staticmethod
    def calculate_trade_metrics(
        trade: PaperTrade, current_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Calculate all metrics for a single trade.

        Args:
            trade: Trade to analyze
            current_price: Current market price (for open trades)

        Returns:
            Dictionary with all trade metrics
        """
        is_open = trade.exit_price is None or trade.exit_timestamp is None

        # Use current price for open trades, exit price for closed
        effective_price = (
            current_price
            if is_open and current_price
            else trade.exit_price or trade.entry_price
        )

        # Total value calculations
        entry_value = trade.entry_price * trade.quantity
        exit_value = effective_price * trade.quantity

        # P&L calculations
        pnl_absolute = exit_value - entry_value
        pnl_percentage = PerformanceCalculator.calculate_pnl_percentage(
            trade.entry_price, effective_price
        )

        # Days held
        if is_open:
            days_held = PerformanceCalculator.calculate_days_held(trade.entry_timestamp)
        else:
            days_held = PerformanceCalculator.calculate_days_held(
                trade.entry_timestamp, trade.exit_timestamp
            )

        return {
            "trade_id": trade.trade_id,
            "symbol": trade.symbol,
            "trade_type": trade.trade_type.value,
            "quantity": trade.quantity,
            "entry_price": trade.entry_price,
            "exit_price": effective_price,
            "entry_value": entry_value,
            "exit_value": exit_value,
            "pnl_absolute": pnl_absolute,
            "pnl_percentage": pnl_percentage,
            "days_held": days_held,
            "is_open": is_open,
            "entry_date": trade.entry_timestamp.isoformat(),
            "exit_date": (
                trade.exit_timestamp.isoformat() if trade.exit_timestamp else None
            ),
        }

    @staticmethod
    def calculate_account_performance(
        initial_balance: float,
        current_balance: float,
        closed_trades: List[PaperTrade],
        open_trades: List[PaperTrade],
        current_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Calculate overall account performance metrics.

        Args:
            initial_balance: Starting capital
            current_balance: Current account balance
            closed_trades: List of closed trades
            open_trades: List of open trades
            current_prices: Dict of symbol -> current price (for open trades)

        Returns:
            Comprehensive performance metrics
        """
        if current_prices is None:
            current_prices = {}

        # Overall P&L
        total_pnl = current_balance - initial_balance
        total_pnl_pct = (
            (total_pnl / initial_balance * 100) if initial_balance > 0 else 0.0
        )

        # Trade count
        total_trades = len(closed_trades) + len(open_trades)
        winning_trades = 0
        losing_trades = 0
        total_realized_pnl = 0.0

        for trade in closed_trades:
            realized_pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            total_realized_pnl += realized_pnl

            if realized_pnl > 0:
                winning_trades += 1
            elif realized_pnl < 0:
                losing_trades += 1

        # Open positions unrealized P&L
        unrealized_pnl = 0.0
        for trade in open_trades:
            current_price = current_prices.get(trade.symbol, trade.entry_price)
            unrealized_pnl += (current_price - trade.entry_price) * trade.quantity

        # Win rate
        win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0.0

        # Average trade metrics
        if closed_trades:
            avg_hold_days = sum(
                PerformanceCalculator.calculate_days_held(
                    t.entry_timestamp, t.exit_timestamp
                )
                for t in closed_trades
            ) / len(closed_trades)

            avg_pnl_per_trade = total_realized_pnl / len(closed_trades)
        else:
            avg_hold_days = 0.0
            avg_pnl_per_trade = 0.0

        # Calculate average win and loss amounts
        winning_pnls = []
        losing_pnls = []

        for trade in closed_trades:
            pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            if pnl > 0:
                winning_pnls.append(pnl)
            elif pnl < 0:
                losing_pnls.append(pnl)

        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0.0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0.0

        # Calculate profit factor (gross profit / gross loss)
        gross_profit = sum(winning_pnls) if winning_pnls else 0.0
        gross_loss = abs(sum(losing_pnls)) if losing_pnls else 0.0
        profit_factor = (
            gross_profit / gross_loss
            if gross_loss > 0
            else float("inf") if gross_profit > 0 else 0.0
        )

        # Largest win/loss
        largest_win = max(winning_pnls) if winning_pnls else 0.0
        largest_loss = min(losing_pnls) if losing_pnls else 0.0

        # Monthly ROI (approximate)
        days_elapsed = (
            (datetime.now() - closed_trades[0].entry_timestamp).days
            if closed_trades
            else 1
        )
        monthly_roi = (
            (total_pnl_pct / max(1, days_elapsed / 30)) if days_elapsed > 0 else 0.0
        )

        return {
            "initial_balance": initial_balance,
            "current_balance": current_balance,
            "total_pnl": total_pnl,
            "total_pnl_percentage": total_pnl_pct,
            "realized_pnl": total_realized_pnl,
            "unrealized_pnl": unrealized_pnl,
            "total_trades": total_trades,
            "closed_trades": len(closed_trades),
            "open_trades": len(open_trades),
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "avg_win": avg_win,
            "avg_loss": avg_loss,
            "profit_factor": profit_factor,
            "largest_win": largest_win,
            "largest_loss": largest_loss,
            "avg_hold_days": avg_hold_days,
            "avg_pnl_per_trade": avg_pnl_per_trade,
            "monthly_roi": monthly_roi,
        }

    @staticmethod
    def calculate_strategy_effectiveness(
        closed_trades: List[PaperTrade], strategy_tag: str
    ) -> Dict[str, Any]:
        """Calculate effectiveness metrics for a specific strategy.

        Args:
            closed_trades: List of closed trades
            strategy_tag: Strategy name/tag to filter on

        Returns:
            Effectiveness metrics for the strategy
        """
        # Filter trades for this strategy
        strategy_trades = [
            t
            for t in closed_trades
            if hasattr(t, "strategy_rationale")
            and strategy_tag in (t.strategy_rationale or "")
        ]

        if not strategy_trades:
            return {"strategy": strategy_tag, "trades": 0}

        wins = 0
        losses = 0
        total_pnl = 0.0

        for trade in strategy_trades:
            pnl = (trade.exit_price - trade.entry_price) * trade.quantity
            total_pnl += pnl

            if pnl > 0:
                wins += 1
            elif pnl < 0:
                losses += 0

        return {
            "strategy": strategy_tag,
            "trades": len(strategy_trades),
            "wins": wins,
            "losses": losses,
            "win_rate": (wins / len(strategy_trades) * 100) if strategy_trades else 0.0,
            "total_pnl": total_pnl,
            "avg_pnl": total_pnl / len(strategy_trades) if strategy_trades else 0.0,
        }

    @staticmethod
    def calculate_drawdown(
        closed_trades: List[PaperTrade], initial_balance: float
    ) -> Dict[str, Any]:
        """Calculate maximum drawdown during trading period.

        Args:
            closed_trades: List of closed trades
            initial_balance: Starting balance

        Returns:
            Drawdown metrics
        """
        if not closed_trades:
            return {"max_drawdown": 0.0, "max_drawdown_percentage": 0.0}

        # Simulate balance progression
        running_balance = initial_balance
        peak_balance = initial_balance
        max_drawdown = 0.0

        for trade in sorted(closed_trades, key=lambda t: t.entry_timestamp):
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
            (max_drawdown / initial_balance * 100) if initial_balance > 0 else 0.0
        )

        return {
            "max_drawdown": max_drawdown,
            "max_drawdown_percentage": max_drawdown_pct,
        }
