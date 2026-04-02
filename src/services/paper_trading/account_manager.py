"""Paper trading account management service."""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from ...core.errors import ErrorSeverity, MarketDataError
from ...models.paper_trading import (
    PaperTradingAccount,
    PaperTradingAccountPolicy,
    PaperTrade,
    AccountType,
    RiskLevel,
)
from ...models.paper_trading_responses import OpenPositionResponse, ClosedTradeResponse
from ...stores.paper_trading_store import PaperTradingStore
from .performance_calculator import PerformanceCalculator
from ...services.market_data_service import SubscriptionMode, MarketDataProvider

logger = logging.getLogger(__name__)


class PaperTradingAccountManager:
    """Manage paper trading accounts with REAL-TIME market data from Zerodha."""

    MARKET_DATA_FETCH_TIMEOUT_SECONDS = 5.0
    MARKET_DATA_FRESHNESS_THRESHOLD_SECONDS = 5 * 60
    QUOTE_UNAVAILABLE_MARK_STATUS = "quote_unavailable"

    def __init__(self, store: PaperTradingStore, market_data_service=None, price_monitor=None):
        """Initialize manager with MarketDataService integration.

        Args:
            store: PaperTradingStore for database operations
            market_data_service: MarketDataService for real-time prices (optional, injected via DI)
            price_monitor: PaperTradingPriceMonitor for WebSocket updates (optional, injected via DI)
        """
        self.store = store
        self.market_data_service = market_data_service  # Injected from DI container
        self.price_monitor = price_monitor  # Injected for WebSocket broadcasting

    def _raise_live_market_data_unavailable(
        self,
        *,
        account_id: str,
        missing_symbols: List[str],
        detail: Optional[str],
    ) -> None:
        symbols = sorted({symbol for symbol in missing_symbols if symbol})
        raise MarketDataError(
            "Live market data is unavailable for one or more open positions. Refusing to synthesize entry-price marks.",
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            code="MARKET_DATA_LIVE_QUOTES_REQUIRED",
            details=detail,
            account_id=account_id,
            missing_symbols=symbols,
        )

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        """Parse ISO timestamps while tolerating legacy date-only strings."""
        if value is None:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            text = str(value).strip()
            if not text:
                return None
            if len(text) == 10:
                text = f"{text}T00:00:00+00:00"
            elif text.endswith("Z"):
                text = f"{text[:-1]}+00:00"
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    @classmethod
    def _is_fresh_market_timestamp(cls, value: Any) -> bool:
        parsed = cls._parse_timestamp(value)
        if parsed is None:
            return False
        age_seconds = (datetime.now(timezone.utc) - parsed).total_seconds()
        return age_seconds <= cls.MARKET_DATA_FRESHNESS_THRESHOLD_SECONDS

    async def create_account(
        self,
        account_name: str,
        initial_balance: float = 100000.0,
        strategy_type: AccountType = AccountType.SWING,
        risk_level: RiskLevel = RiskLevel.MODERATE,
        max_position_size: float = 5.0,
        max_portfolio_risk: float = 10.0,
        account_id: Optional[str] = None
    ) -> PaperTradingAccount:
        """Create new paper trading account."""
        account = await self.store.create_account(
            account_name=account_name,
            initial_balance=initial_balance,
            strategy_type=strategy_type,
            risk_level=risk_level,
            max_position_size=max_position_size,
            max_portfolio_risk=max_portfolio_risk,
            account_id=account_id
        )
        logger.info(f"Account created: {account.account_id}")
        return account

    async def get_account(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Get account by ID."""
        return await self.store.get_account(account_id)

    async def get_account_policy(self, account_id: str) -> Optional[PaperTradingAccountPolicy]:
        """Get operator policy for an account."""
        return await self.store.get_account_policy(account_id)

    async def update_account_policy(
        self,
        account_id: str,
        policy_data: Dict[str, Any],
    ) -> Optional[PaperTradingAccountPolicy]:
        """Update operator policy for an account."""
        return await self.store.update_account_policy(account_id, policy_data)

    async def get_all_accounts(self) -> List[PaperTradingAccount]:
        """Get all paper trading accounts."""
        return await self.store.get_all_accounts()

    async def get_account_balance(self, account_id: str) -> Dict[str, float]:
        """Get account balance details."""
        account = await self.get_account(account_id)
        if not account:
            return {}

        return {
            "current_balance": account.current_balance,
            "buying_power": account.buying_power,
            "initial_balance": account.initial_balance,
            "deployed_capital": account.current_balance - account.buying_power,
            "available_percentage": (account.buying_power / account.initial_balance) * 100
        }

    async def can_execute_trade(
        self,
        account_id: str,
        trade_value: float,
        max_position_pct: float
    ) -> tuple[bool, Optional[str]]:
        """
        Check if trade can be executed.

        Returns:
            (can_execute, error_message)
        """
        account = await self.get_account(account_id)
        if not account:
            return False, "Account not found"

        # Check buying power
        if trade_value > account.buying_power:
            return False, f"Insufficient buying power. Required: {trade_value}, Available: {account.buying_power}"

        # Check position size limit (relative to initial balance)
        max_allowed = account.initial_balance * (max_position_pct / 100)
        if trade_value > max_allowed:
            return False, f"Position exceeds max size limit. Max: {max_allowed}, Requested: {trade_value}"

        return True, None

    async def update_balance(
        self,
        account_id: str,
        amount_change: float
    ) -> Optional[PaperTradingAccount]:
        """Update account balance after trade execution."""
        account = await self.get_account(account_id)
        if not account:
            return None

        new_balance = account.current_balance + amount_change
        new_buying_power = account.buying_power + amount_change

        await self.store.update_account_balance(account_id, new_balance, new_buying_power)
        logger.info(f"Account {account_id} balance updated: {account.current_balance} → {new_balance}")

        return await self.get_account(account_id)

    async def lock_buying_power(
        self,
        account_id: str,
        amount: float
    ) -> Optional[PaperTradingAccount]:
        """Lock buying power for pending trade."""
        account = await self.get_account(account_id)
        if not account:
            return None

        new_buying_power = account.buying_power - amount
        await self.store.update_account_balance(account_id, account.current_balance, new_buying_power)

        return await self.get_account(account_id)

    async def unlock_buying_power(
        self,
        account_id: str,
        amount: float
    ) -> Optional[PaperTradingAccount]:
        """Unlock buying power from pending trade."""
        account = await self.get_account(account_id)
        if not account:
            return None

        new_buying_power = account.buying_power + amount
        await self.store.update_account_balance(account_id, account.current_balance, new_buying_power)

        return await self.get_account(account_id)

    async def reset_monthly(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Reset account for new month."""
        await self.store.reset_monthly_account(account_id)
        return await self.get_account(account_id)

    async def to_dict(self, account: PaperTradingAccount) -> Dict[str, Any]:
        """Convert account to dictionary."""
        return account.to_dict()

    @staticmethod
    def _default_quote_unavailable_detail() -> str:
        return (
            "Live market valuation is unavailable for this position. Showing store-backed position data only; "
            "no entry-price substitution was used."
        )

    def _build_position_response(
        self,
        trade: PaperTrade,
        *,
        current_price: Optional[float],
        price_status: str,
        price_detail: Optional[str],
        price_timestamp: Optional[str],
    ) -> OpenPositionResponse:
        current_value = None
        unrealized_pnl = None
        unrealized_pnl_pct = None
        if current_price is not None:
            current_value = current_price * trade.quantity
            unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
            unrealized_pnl_pct = (
                (unrealized_pnl / (trade.entry_price * trade.quantity)) * 100
                if trade.entry_price > 0
                else 0.0
            )

        return OpenPositionResponse(
            trade_id=trade.trade_id,
            symbol=trade.symbol,
            trade_type=trade.trade_type.value,
            quantity=trade.quantity,
            entry_price=trade.entry_price,
            current_price=current_price,
            current_value=current_value,
            unrealized_pnl=unrealized_pnl,
            unrealized_pnl_pct=unrealized_pnl_pct,
            stop_loss=trade.stop_loss,
            target_price=trade.target_price,
            entry_date=trade.entry_timestamp,
            days_held=PerformanceCalculator.calculate_days_held(trade.entry_timestamp),
            strategy_rationale=trade.strategy_rationale,
            ai_suggested=False,
            market_price_status=price_status,
            market_price_detail=price_detail,
            market_price_timestamp=price_timestamp,
        )

    async def get_store_backed_open_positions(
        self,
        account_id: str,
        *,
        mark_status: Optional[str] = None,
        mark_detail: Optional[str] = None,
    ) -> List[OpenPositionResponse]:
        """Return open-position identity and entry data without live valuation."""
        open_trades = await self.store.get_open_trades(account_id)
        if not open_trades:
            return []

        status = mark_status or self.QUOTE_UNAVAILABLE_MARK_STATUS
        detail = mark_detail or self._default_quote_unavailable_detail()
        return [
            self._build_position_response(
                trade,
                current_price=None,
                price_status=status,
                price_detail=detail,
                price_timestamp=None,
            )
            for trade in open_trades
        ]

    async def get_store_backed_position_metrics(self, account_id: str) -> Dict[str, int | float]:
        """Return deployed capital and open-position count from the trade ledger only."""
        open_trades = await self.store.get_open_trades(account_id)
        deployed_capital = sum(trade.entry_price * trade.quantity for trade in open_trades)
        return {
            "open_positions_count": len(open_trades),
            "deployed_capital": deployed_capital,
        }

    async def get_open_positions(self, account_id: str) -> List[OpenPositionResponse]:
        """Get all open positions with REAL-TIME prices from Zerodha Kite."""
        # Register account for real-time price monitoring (Phase 2: WebSocket updates)
        if self.price_monitor:
            await self.price_monitor.register_account(account_id)

        # Get open trades from store
        open_trades = await self.store.get_open_trades(account_id)

        if not open_trades:
            return []

        # Get unique symbols for batch quote fetching
        symbols = list(set(trade.symbol for trade in open_trades))

        # Fetch current prices from MarketDataService (Zerodha Kite integration)
        current_prices = {}
        current_price_timestamps = {}
        stale_price_details = {}
        market_price_detail = None
        if self.market_data_service:
            try:
                market_data_map = await self.market_data_service.get_multiple_market_data(symbols)
                for symbol, market_data in market_data_map.items():
                    if market_data:
                        timestamp = getattr(market_data, "timestamp", None)
                        timestamp_text = (
                            timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp or "")
                        )
                        if self._is_fresh_market_timestamp(timestamp):
                            current_prices[symbol] = market_data.ltp
                            current_price_timestamps[symbol] = timestamp_text
                        else:
                            stale_price_details[symbol] = (
                                f"Live market price for {symbol} is stale; latest cached mark timestamp is "
                                f"{timestamp_text or 'unknown'}."
                            )

                quote_stream_status = await self.market_data_service.get_quote_stream_status()
                quote_stream_connected = bool(getattr(quote_stream_status, "connected", False))
                quote_stream_state = str(getattr(quote_stream_status, "status", "") or "").strip().lower()
                if len(current_prices) < len(symbols) and (not quote_stream_connected or quote_stream_state != "ready"):
                    market_price_detail = (
                        str(getattr(quote_stream_status, "detail", "") or "").strip()
                        or str(getattr(quote_stream_status, "summary", "") or "").strip()
                        or "Live market data unavailable because the quote stream is not ready."
                    )
                    logger.warning(
                        "Skipping live market fetch for %s because quote stream is %s (connected=%s)",
                        account_id,
                        quote_stream_state or "unknown",
                        quote_stream_connected,
                    )
                    quote_stream_status = None

                async def _load_market_data():
                    subscriptions = await self.market_data_service.get_active_subscriptions()
                    for symbol in symbols:
                        if symbol not in subscriptions:
                            await self.market_data_service.subscribe_market_data(
                                symbol=symbol,
                                mode=SubscriptionMode.LTP,  # Last Traded Price only for efficiency
                                provider=MarketDataProvider.ZERODHA_KITE,  # Use Zerodha Kite API
                            )
                            logger.info(f"Subscribed to Zerodha market data for {symbol}")

                    return await self.market_data_service.get_multiple_market_data(symbols)

                if len(current_prices) < len(symbols) and quote_stream_status is not None:
                    market_data_map = await asyncio.wait_for(
                        _load_market_data(),
                        timeout=self.MARKET_DATA_FETCH_TIMEOUT_SECONDS,
                    )
                    for symbol, market_data in market_data_map.items():
                        if market_data:
                            timestamp = getattr(market_data, "timestamp", None)
                            timestamp_text = (
                                timestamp.isoformat() if hasattr(timestamp, "isoformat") else str(timestamp or "")
                            )
                            if self._is_fresh_market_timestamp(timestamp):
                                current_prices[symbol] = market_data.ltp
                                current_price_timestamps[symbol] = timestamp_text
                                logger.debug(f"Got real-time price for {symbol}: ₹{market_data.ltp}")
                            else:
                                stale_price_details[symbol] = (
                                    f"Live market price for {symbol} is stale; latest cached mark timestamp is "
                                    f"{timestamp_text or 'unknown'}."
                                )
            except asyncio.TimeoutError:
                market_price_detail = (
                    "Live market data unavailable: timed out after "
                    f"{int(self.MARKET_DATA_FETCH_TIMEOUT_SECONDS)}s."
                )
                logger.warning(
                    "Timed out fetching market data for %s after %.1fs",
                    account_id,
                    self.MARKET_DATA_FETCH_TIMEOUT_SECONDS,
                )
            except Exception as e:
                market_price_detail = f"Live market data unavailable: {e}"
                logger.warning("Failed to fetch market data from Zerodha: %s", e)
        else:
            market_price_detail = "MarketDataService is not configured."

        missing_symbols = [symbol for symbol in symbols if symbol not in current_prices]
        if missing_symbols:
            detail = "; ".join(
                filter(
                    None,
                    [stale_price_details.get(symbol) for symbol in missing_symbols] + [market_price_detail],
                )
            ) or "A fresh live quote is required for every open position."
            self._raise_live_market_data_unavailable(
                account_id=account_id,
                missing_symbols=missing_symbols,
                detail=detail,
            )

        # Convert to response format
        positions = [
            self._build_position_response(
                trade,
                current_price=current_prices[trade.symbol],
                price_status="live",
                price_detail=None,
                price_timestamp=current_price_timestamps.get(trade.symbol)
                or datetime.now(timezone.utc).isoformat(),
            )
            for trade in open_trades
        ]

        logger.info(f"Retrieved {len(positions)} open positions with real-time prices from Zerodha")
        return positions

    async def get_closed_trades(self, account_id: str, month: Optional[int] = None, year: Optional[int] = None, symbol: Optional[str] = None, limit: int = 50) -> List[ClosedTradeResponse]:
        """Get closed trade history for account."""
        # Get closed trades from store
        closed_trades = await self.store.get_closed_trades(account_id, month, year, symbol, limit)

        # Convert to response format
        trades = []
        for trade in closed_trades:
            # Calculate holding period days
            holding_period_days = PerformanceCalculator.calculate_days_held(
                trade.entry_timestamp, trade.exit_timestamp
            )

            # Calculate realized P&L percentage
            realized_pnl_pct = PerformanceCalculator.calculate_pnl_percentage(
                trade.entry_price, trade.exit_price
            )

            trades.append(ClosedTradeResponse(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                trade_type=trade.trade_type.value,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                exit_price=trade.exit_price,
                realized_pnl=trade.realized_pnl,
                realized_pnl_pct=realized_pnl_pct,
                entry_date=trade.entry_timestamp,
                exit_date=trade.exit_timestamp,
                holding_period_days=holding_period_days,
                reason_closed="Manual exit",  # TODO: Add reason field
                strategy_rationale=trade.strategy_rationale,
                ai_suggested=False  # TODO: Add this field to trade model
            ))

        return trades

    async def get_performance_metrics(self, account_id: str, period: str = "all-time") -> Dict[str, Any]:
        """Get performance metrics for account."""

        # Get account for initial balance
        account = await self.get_account(account_id)
        if not account:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "profit_factor": 0.0,
                "largest_win": 0.0,
                "largest_loss": 0.0,
                "sharpe_ratio": None,
                "period": period
            }

        # Filter trades based on period
        closed_trades = await self.store.get_closed_trades(account_id)
        filtered_trades = self._filter_trades_by_period(closed_trades, period)

        # Get open trades for unrealized P&L
        open_trades = await self.store.get_open_trades(account_id)

        # Get current prices for open positions
        current_prices = {}
        if open_trades:
            if not self.market_data_service:
                self._raise_live_market_data_unavailable(
                    account_id=account_id,
                    missing_symbols=[trade.symbol for trade in open_trades],
                    detail="MarketDataService is not configured.",
                )

            symbols = list(set(trade.symbol for trade in open_trades))
            market_data_map = await self.market_data_service.get_multiple_market_data(symbols)
            current_prices = {
                symbol: market_data.ltp
                for symbol, market_data in market_data_map.items()
                if market_data
                and market_data.ltp is not None
                and self._is_fresh_market_timestamp(getattr(market_data, "timestamp", None))
            }
            missing_symbols = [symbol for symbol in symbols if symbol not in current_prices]
            if missing_symbols:
                self._raise_live_market_data_unavailable(
                    account_id=account_id,
                    missing_symbols=missing_symbols,
                    detail="Performance metrics require fresh live quotes for every open position.",
                )

        # Use PerformanceCalculator to calculate metrics
        metrics = PerformanceCalculator.calculate_account_performance(
            initial_balance=account.initial_balance,
            current_balance=account.current_balance,
            closed_trades=filtered_trades,
            open_trades=open_trades,
            current_prices=current_prices
        )

        # Add period info
        metrics["period"] = period

        return metrics

    def _filter_trades_by_period(self, trades: List, period: str) -> List:
        """Filter trades based on period."""
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        if period == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start_date = now - timedelta(days=7)
        elif period == "month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # all-time
            return trades

        filtered = []
        for trade in trades:
            if hasattr(trade, 'exit_timestamp') and trade.exit_timestamp:
                trade_date = self._parse_timestamp(trade.exit_timestamp)
                if trade_date is None:
                    continue
                if trade_date >= start_date:
                    filtered.append(trade)

        return filtered
