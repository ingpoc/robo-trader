"""
Historical Replay Engine

Replays historical OHLCV data through the DeterministicScorer using cached
ResearchLedgerEntry data. Does NOT call Claude for replay — uses stored features.

Outputs trade-by-trade P&L, max drawdown, Sharpe ratio, win rate, profit factor.
"""

import logging
import math
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.services.recommendation_engine.deterministic_scorer import DeterministicScorer, BUY_THRESHOLD

logger = logging.getLogger(__name__)


@dataclass
class ReplayTrade:
    """A simulated trade from replay."""
    symbol: str
    entry_date: str
    entry_price: float
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    score: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    status: str = "open"  # open, closed_win, closed_loss, closed_neutral


@dataclass
class ReplayResult:
    """Result of a historical replay."""
    start_date: str
    end_date: str
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_pnl: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    sharpe_ratio: float = 0.0
    trades: List[ReplayTrade] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "start_date": self.start_date,
            "end_date": self.end_date,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "total_pnl": round(self.total_pnl, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "trade_count": len(self.trades),
            "errors": self.errors,
        }


class ReplayEngine:
    """
    Replays historical data through the scoring system.

    Uses stored ResearchLedgerEntry features (not live Claude calls)
    to simulate what the system would have decided historically.
    """

    def __init__(self, research_ledger_store, stop_loss_pct: float = 8.0, take_profit_pct: float = 15.0):
        self.research_ledger_store = research_ledger_store
        self.scorer = DeterministicScorer()
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct

    async def replay(
        self,
        historical_prices: Dict[str, List[Dict[str, Any]]],
        from_date: str,
        to_date: str,
    ) -> ReplayResult:
        """
        Replay historical price data against stored research ledger entries.

        Args:
            historical_prices: {symbol: [{date, open, high, low, close, volume}, ...]}
            from_date: Start date (ISO format)
            to_date: End date (ISO format)

        Returns:
            ReplayResult with trade-by-trade P&L and aggregate metrics
        """
        result = ReplayResult(start_date=from_date, end_date=to_date)
        open_trades: Dict[str, ReplayTrade] = {}
        all_pnls: List[float] = []
        gross_profit = 0.0
        gross_loss = 0.0
        peak_equity = 0.0
        running_equity = 0.0
        max_drawdown = 0.0

        for symbol, price_bars in historical_prices.items():
            # Get research ledger entries for this symbol
            ledger_entries = await self.research_ledger_store.get_history(symbol, limit=100)
            if not ledger_entries:
                continue

            # Build a date->entry map
            entry_by_date: Dict[str, Dict] = {}
            for entry in ledger_entries:
                date_str = entry.get("timestamp", "")[:10]
                entry_by_date[date_str] = entry

            for bar in price_bars:
                date = bar.get("date", "")[:10]
                close = bar.get("close", 0.0)
                high = bar.get("high", close)
                low = bar.get("low", close)

                if date < from_date or date > to_date:
                    continue

                # Check for exit on open trades
                if symbol in open_trades:
                    trade = open_trades[symbol]
                    stop = trade.entry_price * (1 - self.stop_loss_pct / 100)
                    target = trade.entry_price * (1 + self.take_profit_pct / 100)

                    if low <= stop:
                        trade.exit_price = stop
                        trade.exit_date = date
                        trade.pnl = (stop - trade.entry_price) * 100  # Assume 100 shares
                        trade.pnl_pct = -self.stop_loss_pct
                        trade.status = "closed_loss"
                        result.trades.append(trade)
                        del open_trades[symbol]
                    elif high >= target:
                        trade.exit_price = target
                        trade.exit_date = date
                        trade.pnl = (target - trade.entry_price) * 100
                        trade.pnl_pct = self.take_profit_pct
                        trade.status = "closed_win"
                        result.trades.append(trade)
                        del open_trades[symbol]

                # Check for new entry
                if symbol not in open_trades and date in entry_by_date:
                    entry = entry_by_date[date]
                    score = entry.get("score", 0)
                    action = entry.get("action", "HOLD")

                    if action == "BUY" and score > BUY_THRESHOLD:
                        open_trades[symbol] = ReplayTrade(
                            symbol=symbol,
                            entry_date=date,
                            entry_price=close,
                            score=score,
                        )

        # Close any remaining open trades at last price
        for symbol, trade in open_trades.items():
            prices = historical_prices.get(symbol, [])
            if prices:
                last_close = prices[-1].get("close", trade.entry_price)
                trade.exit_price = last_close
                trade.exit_date = to_date
                trade.pnl = (last_close - trade.entry_price) * 100
                trade.pnl_pct = ((last_close - trade.entry_price) / trade.entry_price) * 100 if trade.entry_price else 0
                trade.status = "closed_win" if trade.pnl > 0 else "closed_loss"
                result.trades.append(trade)

        # Calculate metrics
        for trade in result.trades:
            all_pnls.append(trade.pnl)
            running_equity += trade.pnl
            if running_equity > peak_equity:
                peak_equity = running_equity
            drawdown = peak_equity - running_equity
            if peak_equity > 0:
                dd_pct = (drawdown / peak_equity) * 100
                if dd_pct > max_drawdown:
                    max_drawdown = dd_pct

            if trade.pnl > 0:
                gross_profit += trade.pnl
            else:
                gross_loss += abs(trade.pnl)

        result.total_trades = len(result.trades)
        result.winning_trades = sum(1 for t in result.trades if t.pnl > 0)
        result.losing_trades = sum(1 for t in result.trades if t.pnl < 0)
        result.total_pnl = sum(t.pnl for t in result.trades)
        result.max_drawdown_pct = max_drawdown
        result.win_rate = (result.winning_trades / result.total_trades * 100) if result.total_trades else 0
        result.profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else float('inf') if gross_profit > 0 else 0

        # Sharpe ratio (annualized, assuming daily returns)
        if all_pnls and len(all_pnls) > 1:
            mean_pnl = sum(all_pnls) / len(all_pnls)
            variance = sum((p - mean_pnl) ** 2 for p in all_pnls) / (len(all_pnls) - 1)
            std_pnl = math.sqrt(variance) if variance > 0 else 0
            result.sharpe_ratio = (mean_pnl / std_pnl * math.sqrt(252)) if std_pnl > 0 else 0

        logger.info(
            f"Replay complete: {result.total_trades} trades, "
            f"PnL={result.total_pnl:.2f}, WR={result.win_rate:.1f}%, "
            f"PF={result.profit_factor:.2f}, Sharpe={result.sharpe_ratio:.2f}"
        )

        return result
