"""Paper trade execution service with REAL MARKET PRICES."""

import logging
import uuid
from datetime import datetime
from typing import Optional, Dict, Any

from ...models.paper_trading import PaperTrade, TradeType, TradeStatus
from ...stores.paper_trading_store import PaperTradingStore
from .account_manager import PaperTradingAccountManager

logger = logging.getLogger(__name__)


class PaperTradeExecutor:
    """Execute paper trades with real-time market prices from Zerodha."""

    def __init__(self, store: PaperTradingStore, account_manager: PaperTradingAccountManager, market_data_service=None):
        """Initialize executor.

        Args:
            store: PaperTradingStore for database operations
            account_manager: PaperTradingAccountManager for account validation
            market_data_service: MarketDataService for fetching real-time prices
        """
        self.store = store
        self.account_manager = account_manager
        self.market_data_service = market_data_service

        # Slippage configuration (Phase 3)
        self.max_slippage_pct = 0.5  # 0.5% max slippage tolerance

    async def get_current_price(self, symbol: str, fallback_price: Optional[float] = None) -> float:
        """Fetch current market price from Zerodha.

        Args:
            symbol: Stock symbol
            fallback_price: Price to use if market data unavailable

        Returns:
            Current market price (LTP)

        Raises:
            ValueError: If price unavailable and no fallback provided
        """
        if not self.market_data_service:
            if fallback_price is not None:
                logger.warning(f"MarketDataService not available, using fallback price ₹{fallback_price} for {symbol}")
                return fallback_price
            raise ValueError(f"Cannot fetch price for {symbol}: MarketDataService not configured")

        try:
            # Get current market data
            market_data = await self.market_data_service.get_market_data(symbol)

            if market_data and market_data.ltp:
                logger.info(f"Fetched real-time price for {symbol}: ₹{market_data.ltp}")
                return market_data.ltp

            # Market data not available, use fallback
            if fallback_price is not None:
                logger.warning(f"Market data unavailable for {symbol}, using fallback price ₹{fallback_price}")
                return fallback_price

            raise ValueError(f"No market data available for {symbol} and no fallback price provided")

        except Exception as e:
            if fallback_price is not None:
                logger.error(f"Error fetching price for {symbol}: {e}. Using fallback price ₹{fallback_price}")
                return fallback_price
            raise ValueError(f"Failed to fetch price for {symbol}: {e}")

    def validate_slippage(self, requested_price: float, actual_price: float, symbol: str) -> tuple[bool, Optional[str]]:
        """Validate slippage tolerance.

        Args:
            requested_price: Price requested by user
            actual_price: Current market price
            symbol: Stock symbol

        Returns:
            (is_valid, error_message)
        """
        if requested_price <= 0 or actual_price <= 0:
            return True, None  # Skip validation for zero prices

        slippage_pct = abs((actual_price - requested_price) / requested_price) * 100

        if slippage_pct > self.max_slippage_pct:
            error = (
                f"Slippage too high for {symbol}: "
                f"Requested ₹{requested_price}, Market ₹{actual_price} "
                f"({slippage_pct:.2f}% > {self.max_slippage_pct}% max)"
            )
            logger.warning(error)
            return False, error

        logger.info(f"Slippage OK for {symbol}: {slippage_pct:.2f}% (within {self.max_slippage_pct}%)")
        return True, None

    async def execute_buy(
        self,
        account_id: str,
        symbol: str,
        quantity: int,
        entry_price: float,
        strategy_rationale: str,
        claude_session_id: str,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None,
        use_market_price: bool = True  # Phase 3: Use real-time price by default
    ) -> Dict[str, Any]:
        """Execute a BUY trade with REAL-TIME MARKET PRICE.

        Args:
            account_id: Account to execute trade for
            symbol: Stock symbol
            quantity: Number of shares
            entry_price: Requested price (used for slippage validation or fallback)
            strategy_rationale: Trading strategy reasoning
            claude_session_id: Claude session ID
            stop_loss: Stop loss price (optional)
            target_price: Target price (optional)
            use_market_price: If True, fetch real-time price from Zerodha (Phase 3)

        Returns:
            Trade execution result with success status
        """
        # Phase 3: Fetch real-time market price from Zerodha
        if use_market_price:
            try:
                actual_price = await self.get_current_price(symbol, fallback_price=entry_price)

                # Validate slippage tolerance
                is_valid, slippage_error = self.validate_slippage(entry_price, actual_price, symbol)
                if not is_valid:
                    return {
                        "success": False,
                        "error": slippage_error,
                        "trade_id": None,
                        "requested_price": entry_price,
                        "market_price": actual_price
                    }

                # Use actual market price for execution
                execution_price = actual_price
                logger.info(f"Using real-time price for {symbol}: ₹{execution_price} (requested: ₹{entry_price})")
            except Exception as e:
                logger.error(f"Failed to fetch market price for {symbol}: {e}. Using requested price ₹{entry_price}")
                execution_price = entry_price
        else:
            # Use requested price directly (backward compatibility)
            execution_price = entry_price

        # Calculate trade value with actual execution price
        trade_value = quantity * execution_price

        # Validate account can execute trade
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

        # Execute trade with real market price
        trade = await self.store.create_trade(
            account_id=account_id,
            symbol=symbol,
            trade_type=TradeType.BUY,
            quantity=quantity,
            entry_price=execution_price,  # Real-time price!
            strategy_rationale=strategy_rationale,
            claude_session_id=claude_session_id,
            stop_loss=stop_loss,
            target_price=target_price
        )

        # Update account balance (deduct from buying power)
        await self.account_manager.lock_buying_power(account_id, trade_value)

        logger.info(f"BUY trade executed: {symbol} {quantity}@₹{execution_price} (market price from Zerodha)")

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
        exit_price: Optional[float] = None,
        reason: str = "Manual exit",
        use_market_price: bool = True  # Phase 3: Use real-time price by default
    ) -> Dict[str, Any]:
        """Close an open position with REAL-TIME MARKET PRICE.

        Args:
            trade_id: Trade ID to close
            exit_price: Requested exit price (optional, will fetch market price if not provided)
            reason: Reason for closing
            use_market_price: If True, fetch real-time price from Zerodha

        Returns:
            Trade close result with realized P&L
        """
        trade = await self.store.get_trade(trade_id)
        if not trade:
            return {"success": False, "error": "Trade not found"}

        if trade.status != TradeStatus.OPEN:
            return {"success": False, "error": f"Trade is {trade.status.value}, cannot close"}

        # Phase 3: Fetch real-time market price for closing
        if use_market_price:
            try:
                actual_exit_price = await self.get_current_price(trade.symbol, fallback_price=exit_price or trade.entry_price)
                logger.info(f"Using real-time exit price for {trade.symbol}: ₹{actual_exit_price}")
            except Exception as e:
                logger.error(f"Failed to fetch market price for closing {trade.symbol}: {e}")
                actual_exit_price = exit_price or trade.entry_price
        else:
            actual_exit_price = exit_price or trade.entry_price

        # Calculate P&L with real market price
        if trade.trade_type == TradeType.BUY:
            realized_pnl = (actual_exit_price - trade.entry_price) * trade.quantity
        else:  # SELL
            realized_pnl = (trade.entry_price - actual_exit_price) * trade.quantity

        # Close trade
        closed_trade = await self.store.close_trade(
            trade_id=trade_id,
            exit_price=actual_exit_price,  # Real-time market price!
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

        logger.info(f"Position closed: {trade.symbol} P&L: ₹{realized_pnl} (exit price: ₹{actual_exit_price} from market)")

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
