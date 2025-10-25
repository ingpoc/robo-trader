"""Paper trading account management service."""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

from ...models.paper_trading import PaperTradingAccount, AccountType, RiskLevel
from ...stores.paper_trading_store import PaperTradingStore
from ...web.paper_trading_api import OpenPositionResponse, ClosedTradeResponse
from .performance_calculator import PerformanceCalculator
from ...services.market_data_service import SubscriptionMode, MarketDataProvider

logger = logging.getLogger(__name__)


class PaperTradingAccountManager:
    """Manage paper trading accounts with REAL-TIME market data from Zerodha."""

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
        if self.market_data_service:
            try:
                # Subscribe to market data for all symbols if not already subscribed
                for symbol in symbols:
                    # Check if already subscribed, if not subscribe
                    subscriptions = await self.market_data_service.get_active_subscriptions()
                    if symbol not in subscriptions:
                        await self.market_data_service.subscribe_market_data(
                            symbol=symbol,
                            mode=SubscriptionMode.LTP,  # Last Traded Price only for efficiency
                            provider=MarketDataProvider.ZERODHA_KITE  # Use Zerodha Kite API
                        )
                        logger.info(f"Subscribed to Zerodha market data for {symbol}")

                # Get current market data for all symbols
                market_data_map = await self.market_data_service.get_multiple_market_data(symbols)
                for symbol, market_data in market_data_map.items():
                    if market_data:
                        current_prices[symbol] = market_data.ltp
                        logger.debug(f"Got real-time price for {symbol}: ₹{market_data.ltp}")
            except Exception as e:
                logger.warning(f"Failed to fetch market data from Zerodha: {e}. Using entry prices as fallback.")

        # Convert to response format
        positions = []
        for trade in open_trades:
            # Get current price from market data, fallback to entry price if unavailable
            current_price = current_prices.get(trade.symbol, trade.entry_price)
            if current_price == trade.entry_price:
                logger.warning(f"Market data unavailable for {trade.symbol}, using entry price ₹{trade.entry_price}")

            # Calculate unrealized P&L with current market price
            unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
            unrealized_pnl_pct = (unrealized_pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price > 0 else 0.0

            # Calculate days held
            days_held = PerformanceCalculator.calculate_days_held(trade.entry_timestamp)

            positions.append(OpenPositionResponse(
                trade_id=trade.trade_id,
                symbol=trade.symbol,
                trade_type=trade.trade_type.value,
                quantity=trade.quantity,
                entry_price=trade.entry_price,
                current_price=current_price,  # Real-time from Zerodha!
                current_value=current_price * trade.quantity,
                unrealized_pnl=unrealized_pnl,  # Calculated with live price
                unrealized_pnl_pct=unrealized_pnl_pct,
                stop_loss=trade.stop_loss,
                target_price=trade.target_price,
                entry_date=trade.entry_timestamp,
                days_held=days_held,
                strategy_rationale=trade.strategy_rationale,
                ai_suggested=False  # TODO: Add this field to trade model
            ))

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
        from datetime import datetime, timedelta

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
            symbols = list(set(trade.symbol for trade in open_trades))
            current_prices = await self.market_data_client.get_quotes(symbols)

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
        from datetime import datetime, timedelta

        now = datetime.now()
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
                trade_date = datetime.fromisoformat(trade.exit_timestamp)
                if trade_date >= start_date:
                    filtered.append(trade)

        return filtered
