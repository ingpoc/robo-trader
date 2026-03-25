"""
Reconciliation Service

Compares internal paper trading state against computed truth from trade history.
Detects drift between stored positions/P&L and what trades imply.
Emits RECONCILIATION_DRIFT events when discrepancies are found.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from src.core.event_bus import EventBus, Event, EventType, EventHandler

logger = logging.getLogger(__name__)


class ReconciliationService(EventHandler):
    """
    Reconciles internal paper trading state against trade-derived truth.

    For paper trading: recomputes positions from trade history,
    compares with stored positions, and flags drift.

    For future live trading: would compare with broker state.
    """

    def __init__(self, event_bus: EventBus, paper_trading_store, state_manager=None):
        self.event_bus = event_bus
        self.store = paper_trading_store
        self.state_manager = state_manager
        self._last_reconciliation: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the reconciliation service."""
        logger.info("ReconciliationService initialized")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        logger.info("ReconciliationService cleaned up")

    async def reconcile(self, account_id: str = "paper_swing_main") -> Dict[str, Any]:
        """
        Run a full reconciliation for a paper trading account.

        Recomputes positions from trade history and compares with stored state.
        Returns a reconciliation report.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        report = {
            "account_id": account_id,
            "timestamp": timestamp,
            "status": "clean",
            "drifts": [],
            "positions_checked": 0,
            "pnl_checked": False,
        }

        try:
            # Get stored positions
            stored_positions = await self.store.get_positions(account_id)
            stored_map = {p["symbol"]: p for p in (stored_positions or [])}

            # Get all trades to recompute positions
            all_trades = await self.store.get_trades(account_id, limit=10000)

            # Recompute positions from trades
            computed_positions: Dict[str, Dict[str, Any]] = {}
            for trade in (all_trades or []):
                symbol = trade.get("symbol", "")
                if symbol not in computed_positions:
                    computed_positions[symbol] = {"quantity": 0, "total_cost": 0.0}

                qty = trade.get("quantity", 0)
                price = trade.get("entry_price", 0.0)
                status = trade.get("status", "")
                trade_type = trade.get("trade_type", "BUY")

                if status == "OPEN":
                    if trade_type == "BUY":
                        computed_positions[symbol]["quantity"] += qty
                        computed_positions[symbol]["total_cost"] += qty * price
                    elif trade_type == "SELL":
                        computed_positions[symbol]["quantity"] -= qty

            # Compare stored vs computed
            all_symbols = set(list(stored_map.keys()) + list(computed_positions.keys()))
            report["positions_checked"] = len(all_symbols)

            for symbol in all_symbols:
                stored_qty = stored_map.get(symbol, {}).get("quantity", 0)
                computed_qty = computed_positions.get(symbol, {}).get("quantity", 0)

                if stored_qty != computed_qty:
                    drift = {
                        "type": "position_quantity",
                        "symbol": symbol,
                        "stored": stored_qty,
                        "computed": computed_qty,
                        "delta": computed_qty - stored_qty,
                    }
                    report["drifts"].append(drift)
                    report["status"] = "drift_detected"

            # Check P&L consistency
            report["pnl_checked"] = True
            account = await self.store.get_account(account_id)
            if account:
                stored_pnl = account.get("monthly_pnl", 0.0)
                computed_pnl = await self._compute_pnl_from_trades(all_trades or [])
                if abs(stored_pnl - computed_pnl) > 0.01:
                    report["drifts"].append({
                        "type": "pnl_mismatch",
                        "stored_pnl": stored_pnl,
                        "computed_pnl": computed_pnl,
                        "delta": computed_pnl - stored_pnl,
                    })
                    report["status"] = "drift_detected"

            # Emit event if drift detected
            if report["status"] == "drift_detected":
                logger.warning(f"Reconciliation drift detected: {len(report['drifts'])} issues")
                await self.event_bus.publish(Event(
                    id=f"recon_{timestamp}",
                    type=EventType.RECONCILIATION_DRIFT,
                    data=report,
                    timestamp=timestamp,
                    source="reconciliation_service",
                ))
            else:
                logger.info(f"Reconciliation clean: {report['positions_checked']} positions checked")

            self._last_reconciliation = timestamp
            return report

        except Exception as e:
            logger.error(f"Reconciliation failed: {e}")
            report["status"] = "error"
            report["error"] = str(e)
            return report

    async def _compute_pnl_from_trades(self, trades: List[Dict[str, Any]]) -> float:
        """Compute P&L from closed trades."""
        total_pnl = 0.0
        for trade in trades:
            if trade.get("status") == "CLOSED":
                entry = trade.get("entry_price", 0.0)
                exit_price = trade.get("exit_price", 0.0)
                qty = trade.get("quantity", 0)
                trade_type = trade.get("trade_type", "BUY")
                if trade_type == "BUY":
                    total_pnl += (exit_price - entry) * qty
                else:
                    total_pnl += (entry - exit_price) * qty
        return total_pnl
