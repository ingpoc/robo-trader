"""Native paper-trade execution service.

This service no longer uses Claude for trade approval. Execution-critical
validation must remain deterministic and tied to explicit prices or live
market data.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, Optional, TYPE_CHECKING

from loguru import logger as loguru_logger

from src.core.errors import ErrorCategory, ErrorSeverity, TradingError

if TYPE_CHECKING:
    from src.services.paper_trading.trade_executor import PaperTradeExecutor
    from src.services.paper_trading.account_manager import PaperTradingAccountManager
    from src.stores.paper_trading_store import PaperTradingStore

logger = logging.getLogger(__name__)


class PaperTradingExecutionService:
    """Store-backed execution facade with explicit-price or real-price enforcement."""

    def __init__(
        self,
        trade_executor: "PaperTradeExecutor",
        account_manager: "PaperTradingAccountManager",
        store: "PaperTradingStore",
    ):
        self._trade_executor = trade_executor
        self._account_manager = account_manager
        self._store = store
        self._initialized = False

    async def initialize(self) -> None:
        self._initialized = True
        loguru_logger.info("PaperTradingExecutionService initialized in native validation mode")

    async def cleanup(self) -> None:
        self._initialized = False
        loguru_logger.info("PaperTradingExecutionService cleanup complete")

    async def execute_buy_trade(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        strategy_rationale: str = "User initiated trade",
    ) -> Dict[str, object]:
        await self._ensure_initialized()
        await self._require_account(account_id)
        symbol = self._normalize_symbol(symbol)
        self._validate_quantity(quantity)

        execution_price = await self._resolve_execution_price(symbol, order_type, price)
        execution_result = await self._trade_executor.execute_buy(
            account_id=account_id,
            symbol=symbol,
            quantity=quantity,
            entry_price=execution_price,
            strategy_rationale=strategy_rationale,
            claude_session_id="paper_trading_execution_service",
        )
        if not execution_result.get("success"):
            raise TradingError(
                str(execution_result.get("error", f"Failed to execute BUY trade for {symbol}")),
                category=ErrorCategory.EXECUTION,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
            )

        balance_info = await self._account_manager.get_account_balance(account_id)
        return {
            "success": True,
            "trade_id": execution_result["trade_id"],
            "symbol": symbol,
            "side": "BUY",
            "quantity": quantity,
            "price": float(execution_price),
            "status": "COMPLETED",
            "timestamp": execution_result.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "account_id": account_id,
            "remaining_balance": balance_info["current_balance"],
            "buying_power": balance_info["buying_power"],
            "validation_reason": "Validated natively using explicit account context and real or explicit price.",
        }

    async def execute_sell_trade(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        strategy_rationale: str = "User initiated trade",
    ) -> Dict[str, object]:
        await self._ensure_initialized()
        await self._require_account(account_id)
        symbol = self._normalize_symbol(symbol)
        self._validate_quantity(quantity)

        execution_price = await self._resolve_execution_price(symbol, order_type, price)
        execution_result = await self._trade_executor.execute_sell(
            account_id=account_id,
            symbol=symbol,
            quantity=quantity,
            exit_price=execution_price,
            strategy_rationale=strategy_rationale,
            claude_session_id="paper_trading_execution_service",
        )
        if not execution_result.get("success"):
            raise TradingError(
                str(execution_result.get("error", f"Failed to execute SELL trade for {symbol}")),
                category=ErrorCategory.EXECUTION,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
            )

        balance_info = await self._account_manager.get_account_balance(account_id)
        return {
            "success": True,
            "trade_id": execution_result["trade_id"],
            "symbol": symbol,
            "side": "SELL",
            "quantity": quantity,
            "price": float(execution_price),
            "status": "COMPLETED",
            "timestamp": execution_result.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "account_id": account_id,
            "remaining_balance": balance_info["current_balance"],
            "buying_power": balance_info["buying_power"],
            "validation_reason": "Validated natively using explicit account context and real or explicit price.",
        }

    async def close_trade(
        self,
        trade_id: str,
        order_type: str = "MARKET",
        price: Optional[float] = None,
        reason: str = "User initiated close",
    ) -> Dict[str, object]:
        await self._ensure_initialized()
        trade = await self._store.get_trade(trade_id)
        if trade is None:
            raise TradingError(
                f"Trade {trade_id} was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        explicit_price = self._validate_explicit_price(price) if price is not None else None
        use_market_price = explicit_price is None and order_type.upper() == "MARKET"
        if explicit_price is None and order_type.upper() != "MARKET":
            raise TradingError(
                "LIMIT trade close requires an explicit price.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        close_result = await self._trade_executor.close_position(
            trade_id=trade_id,
            exit_price=explicit_price,
            reason=reason,
            use_market_price=use_market_price,
        )
        if not close_result.get("success"):
            raise TradingError(
                str(close_result.get("error", f"Failed to close trade {trade_id}")),
                category=ErrorCategory.EXECUTION,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
            )

        return {
            "success": True,
            "trade_id": trade_id,
            "status": "CLOSED",
            "exit_price": float(close_result["exit_price"]),
            "realized_pnl": float(close_result["realized_pnl"]),
            "timestamp": close_result.get("timestamp", datetime.now(timezone.utc).isoformat()),
        }

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            raise TradingError(
                "PaperTradingExecutionService is not initialized.",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

    async def _require_account(self, account_id: str) -> None:
        account = await self._account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

    async def _resolve_execution_price(self, symbol: str, order_type: str, price: Optional[float]) -> float:
        explicit_price = self._validate_explicit_price(price) if price is not None else None
        if explicit_price is not None:
            return explicit_price

        if order_type.upper() != "MARKET":
            raise TradingError(
                f"{order_type.upper()} orders require an explicit price.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        try:
            return float(await self._trade_executor.get_current_price(symbol))
        except Exception as exc:
            loguru_logger.error("Failed to fetch live price for %s: %s", symbol, exc)
            raise TradingError(
                f"Cannot execute {symbol}: live market price is unavailable and no explicit price was provided.",
                category=ErrorCategory.MARKET_DATA,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
            ) from exc

    @staticmethod
    def _normalize_symbol(symbol: str) -> str:
        clean = symbol.strip().upper()
        if not clean:
            raise TradingError(
                "Symbol is required.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )
        return clean

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if quantity <= 0:
            raise TradingError(
                "Quantity must be a positive integer.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

    @staticmethod
    def _validate_explicit_price(price: Optional[float]) -> Optional[float]:
        if price is None:
            return None
        if price <= 0:
            raise TradingError(
                "Price must be greater than zero.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )
        return float(price)
