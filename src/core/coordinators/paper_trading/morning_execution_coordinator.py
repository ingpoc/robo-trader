"""Morning Execution Coordinator - executes approved trades and logs decisions."""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.services.paper_trading_execution_service import PaperTradingExecutionService
from src.services.paper_trading.account_manager import PaperTradingAccountManager
from src.services.claude_agent.decision_logger import ClaudeDecisionLogger
from src.services.kite_connect_service import KiteConnectService

if TYPE_CHECKING:
    from src.core.di import DependencyContainer


class MorningExecutionCoordinator(BaseCoordinator):
    """Executes approved trades and logs decisions."""

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container
        self.execution_service: Optional[PaperTradingExecutionService] = None
        self.account_manager: Optional[PaperTradingAccountManager] = None
        self.decision_logger: Optional[ClaudeDecisionLogger] = None
        self.kite_service: Optional[KiteConnectService] = None

    async def initialize(self) -> None:
        self.execution_service = await self.container.get("paper_trading_execution_service")
        self.account_manager = await self.container.get("paper_trading_account_manager")
        self.decision_logger = await self.container.get("trade_decision_logger")
        try:
            self.kite_service = await self.container.get("kite_connect_service")
        except ValueError:
            self._log_warning("kite_connect_service not registered - using market_data_service")
            self.kite_service = await self.container.get("market_data_service")
        self._initialized = True

    async def execute_trades(self, approved_trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute approved trades via paper trading with live prices."""
        results = []
        kite_ok = await self._check_kite_available()
        if kite_ok:
            self._log_info("Using Kite Connect for live prices (paper trading mode)")
        else:
            self._log_warning("Kite Connect unavailable; requires explicit decision prices")
        for trade in approved_trades:
            try:
                r = await self._execute_single_trade(trade, kite_ok)
                r["original_idea"] = trade
                results.append(r)
            except Exception as e:
                self._log_error(f"Trade execution failed for {trade['symbol']}: {e}")
                await self.decision_logger.log_decision({
                    "decision_type": "EXECUTION_FAILED", "symbol": trade["symbol"],
                    "reasoning": f"Execution failed: {e}", "confidence": 1.0,
                    "context": {"trade": trade}})
        return results

    async def _check_kite_available(self) -> bool:
        if not self.kite_service:
            return False
        try:
            if hasattr(self.kite_service, 'is_authenticated'):
                return await self.kite_service.is_authenticated()
            if hasattr(self.kite_service, '_active_session') and self.kite_service._active_session:
                return True
        except Exception as e:
            self._log_warning(f"Kite Connect check failed: {e}")
        return False

    async def _execute_single_trade(self, trade: Dict[str, Any], kite_ok: bool) -> Dict[str, Any]:
        entry_price = trade.get("entry_price") or trade.get("price")
        if kite_ok and hasattr(self.kite_service, 'get_current_price'):
            try:
                live = await self.kite_service.get_current_price(trade["symbol"])
                if live and live > 0:
                    entry_price = live
                    self._log_info(f"Live price for {trade['symbol']}: Rs.{entry_price}")
                else:
                    self._log_warning(f"No usable live price for {trade['symbol']}")
            except Exception as e:
                self._log_warning(f"Failed to get live price for {trade['symbol']}: {e}")
        if not entry_price or entry_price == 0:
            raise TradingError(
                f"Cannot execute {trade['symbol']}: no live or decision entry price",
                category=ErrorCategory.VALIDATION, severity=ErrorSeverity.HIGH)
        pct = trade.get("position_size_pct", 5.0)
        qty = max(1, int((100000.0 * pct / 100.0) / entry_price))
        self._log_info(f"Executing {trade['action']} {trade['symbol']}: {qty} @ Rs.{entry_price}")
        account_id = await self._resolve_account_id()
        rationale = trade.get("rationale", "Morning session trade")
        method = (self.execution_service.execute_buy_trade if trade["action"] == "BUY"
                  else self.execution_service.execute_sell_trade if trade["action"] == "SELL"
                  else None)
        if not method:
            raise ValueError(f"Unknown action: {trade['action']}")
        return await method(account_id=account_id, symbol=trade["symbol"],
                            quantity=qty, order_type="MARKET", strategy_rationale=rationale)

    async def _resolve_account_id(self) -> str:
        if not self.account_manager:
            raise TradingError("PaperTradingAccountManager not initialized",
                               category=ErrorCategory.SYSTEM, severity=ErrorSeverity.CRITICAL)
        accounts = await self.account_manager.get_all_accounts()
        if not accounts:
            raise TradingError("No paper trading account exists",
                               category=ErrorCategory.VALIDATION, severity=ErrorSeverity.HIGH)
        if len(accounts) > 1:
            ids = ", ".join(a.account_id for a in accounts)
            raise TradingError(f"Explicit account selection required; available: {ids}",
                               category=ErrorCategory.VALIDATION, severity=ErrorSeverity.HIGH)
        return accounts[0].account_id

    async def log_session_decisions(
        self, session_id: str, trade_ideas: List[Dict[str, Any]],
        approved_trades: List[Dict[str, Any]], execution_results: List[Dict[str, Any]]
    ) -> None:
        """Log all decisions made during the session."""
        for idea in trade_ideas:
            await self.decision_logger.log_decision({
                "decision_type": "TRADE_IDEA", "symbol": idea["symbol"],
                "reasoning": idea.get("rationale", ""), "confidence": idea.get("confidence", 0),
                "context": {"session_id": session_id, "action": idea.get("action"),
                            "quantity": idea.get("quantity"), "price": idea.get("price")}})
        for trade in approved_trades:
            await self.decision_logger.log_decision({
                "decision_type": "TRADE_APPROVED", "symbol": trade["symbol"],
                "reasoning": "Passed all safeguards", "confidence": trade.get("confidence", 0),
                "context": {"session_id": session_id,
                            "safeguards": trade.get("safeguard_checks", {})}})
        for result in execution_results:
            await self.decision_logger.log_decision({
                "decision_type": "TRADE_EXECUTED", "symbol": result["symbol"],
                "reasoning": f"Trade executed at {result['price']}", "confidence": 1.0,
                "context": {"session_id": session_id, "trade_id": result["trade_id"],
                            "quantity": result["quantity"], "side": result["side"]}})

    async def cleanup(self) -> None:
        self._log_info("MorningExecutionCoordinator cleanup complete")
