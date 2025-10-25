"""Paper trade execution service."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from ...models.paper_trading import PaperTrade, TradeType, TradeStatus
from ...stores.paper_trading_store import PaperTradingStore
from .account_manager import PaperTradingAccountManager

logger = logging.getLogger(__name__)


class PaperTradeExecutor:
    """Execute paper trades."""

    def __init__(self, store: PaperTradingStore, account_manager: PaperTradingAccountManager):
        """Initialize executor."""
        self.store = store
        self.account_manager = account_manager

    async def execute_buy(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        entry_price: float,
        strategy_rationale: str,
        claude_session_id: str,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a BUY trade."""
        # Calculate trade value
        trade_value = quantity * entry_price

        # Validate
        can_execute, error = await self.account_manager.can_execute_trade(
            account_id=account_id,
            trade_value=trade_value,
            max_position_pct=5.0
        )

        if not can_execute:
            return {
                "success": False,
                "error": error,
                "trade_id": None
            }

        # Execute trade
        trade = await self.store.create_trade(
            account_id=account_id,
            symbol=symbol,
            trade_type=TradeType.BUY,
            quantity=quantity,
            entry_price=entry_price,
            strategy_rationale=strategy_rationale,
            claude_session_id=claude_session_id,
            stop_loss=stop_loss,
            target_price=target_price
        )

        # Update account balance (deduct from buying power)
        await self.account_manager.lock_buying_power(account_id, trade_value)

        logger.info(f"BUY trade executed: {symbol} {quantity}@{entry_price}")

        return {
            "success": True,
            "trade_id": trade.trade_id,
            "symbol": symbol,
            "action": "BUY",
            "quantity": quantity,
            "entry_price": entry_price,
            "trade_value": trade_value,
            "timestamp": trade.entry_timestamp
        }

    async def execute_sell(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        exit_price: float,
        strategy_rationale: str,
        claude_session_id: str,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """Execute a SELL trade."""
        # Calculate trade value
        trade_value = quantity * exit_price

        # Execute trade
        trade = await self.store.create_trade(
            account_id=account_id,
            symbol=symbol,
            trade_type=TradeType.SELL,
            quantity=quantity,
            entry_price=exit_price,  # For SELL, entry_price is the sell price
            strategy_rationale=strategy_rationale,
            claude_session_id=claude_session_id,
            stop_loss=stop_loss,
            target_price=target_price
        )

        # Update account balance (add to buying power)
        await self.account_manager.unlock_buying_power(account_id, trade_value)

        logger.info(f"SELL trade executed: {symbol} {quantity}@{exit_price}")

        return {
            "success": True,
            "trade_id": trade.trade_id,
            "symbol": symbol,
            "action": "SELL",
            "quantity": quantity,
            "exit_price": exit_price,
            "trade_value": trade_value,
            "timestamp": trade.entry_timestamp
        }

    async def close_position(
        self,
        trade_id: str,
        exit_price: float,
        reason: str = "Manual exit"
    ) -> Dict[str, Any]:
        """Close an open position."""
        trade = await self.store.get_trade(trade_id)
        if not trade:
            return {"success": False, "error": "Trade not found"}

        if trade.status != TradeStatus.OPEN:
            return {"success": False, "error": f"Trade is {trade.status.value}, cannot close"}

        # Calculate P&L
        if trade.trade_type == TradeType.BUY:
            realized_pnl = (exit_price - trade.entry_price) * trade.quantity
        else:  # SELL
            realized_pnl = (trade.entry_price - exit_price) * trade.quantity

        # Close trade
        closed_trade = await self.store.close_trade(
            trade_id=trade_id,
            exit_price=exit_price,
            realized_pnl=realized_pnl,
            reason=reason
        )

        # Update account balance
        if trade.trade_type == TradeType.BUY:
            # Release locked buying power + realized P&L
            await self.account_manager.unlock_buying_power(
                account_id=trade.account_id,
                amount=trade.entry_price * trade.quantity
            )
            # Add realized P&L to balance
            if realized_pnl > 0:
                await self.account_manager.update_balance(trade.account_id, realized_pnl)
        else:  # SELL
            # Release locked value + realized P&L
            await self.account_manager.unlock_buying_power(
                account_id=trade.account_id,
                amount=trade.entry_price * trade.quantity
            )

        logger.info(f"Position closed: {trade.symbol} P&L: {realized_pnl}")

        return {
            "success": True,
            "trade_id": trade_id,
            "symbol": trade.symbol,
            "exit_price": exit_price,
            "realized_pnl": realized_pnl,
            "pnl_percentage": (realized_pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price > 0 else 0.0
        }

    async def check_stop_loss(
        self,
        trade_id: str,
        current_price: float
    ) -> Dict[str, Any]:
        """Check if stop loss is triggered."""
        trade = await self.store.get_trade(trade_id)
        if not trade or trade.status != TradeStatus.OPEN:
            return {"triggered": False, "trade_id": trade_id}

        if not trade.is_stop_loss_triggered(current_price):
            return {"triggered": False, "trade_id": trade_id}

        # Stop loss hit - close position
        realized_pnl = (current_price - trade.entry_price) * trade.quantity if trade.trade_type == TradeType.BUY else (trade.entry_price - current_price) * trade.quantity

        await self.store.mark_stopped_out(
            trade_id=trade_id,
            exit_price=current_price,
            realized_pnl=realized_pnl
        )

        logger.warning(f"Stop loss triggered: {trade.symbol} {trade.trade_type.value} at {current_price}")

        return {
            "triggered": True,
            "trade_id": trade_id,
            "symbol": trade.symbol,
            "exit_price": current_price,
            "realized_pnl": realized_pnl
        }

    async def check_target(
        self,
        trade_id: str,
        current_price: float
    ) -> Dict[str, Any]:
        """Check if target price is hit."""
        trade = await self.store.get_trade(trade_id)
        if not trade or trade.status != TradeStatus.OPEN:
            return {"target_hit": False, "trade_id": trade_id}

        if not trade.is_target_hit(current_price):
            return {"target_hit": False, "trade_id": trade_id}

        logger.info(f"Target hit: {trade.symbol} at {current_price}")

        return {
            "target_hit": True,
            "trade_id": trade_id,
            "symbol": trade.symbol,
            "target_price": trade.target_price,
            "current_price": current_price
        }
