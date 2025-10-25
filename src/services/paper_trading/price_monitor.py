"""
Paper Trading Price Monitor - WebSocket Real-Time Updates

Subscribes to MARKET_PRICE_UPDATE events and broadcasts position updates
via WebSocket when prices change, eliminating frontend polling.
"""

import logging
import asyncio
from typing import Dict, Set, Optional
from datetime import datetime

from ...core.event_bus import EventBus, Event, EventType, EventHandler
from ...stores.paper_trading_store import PaperTradingStore
from .performance_calculator import PerformanceCalculator

logger = logging.getLogger(__name__)


class PaperTradingPriceMonitor(EventHandler):
    """
    Monitors market price updates and broadcasts paper trading position changes via WebSocket.

    **Phase 2: Real-Time WebSocket Updates**

    Responsibilities:
    - Subscribe to MARKET_PRICE_UPDATE events from MarketDataService
    - Track active positions and their symbols
    - Recalculate unrealized P&L when prices change
    - Broadcast position updates to connected WebSocket clients
    - Reduce frontend polling (2s → real-time)

    Architecture:
    ```
    MarketDataService → MARKET_PRICE_UPDATE event
        ↓
    PaperTradingPriceMonitor.handle_event()
        ↓
    Check if symbol affects any open positions
        ↓
    Recalculate unrealized P&L for affected positions
        ↓
    BroadcastCoordinator → WebSocket clients
        ↓
    Frontend updates in real-time (< 1s latency)
    ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        paper_trading_store: PaperTradingStore,
        broadcast_coordinator=None
    ):
        """Initialize price monitor.

        Args:
            event_bus: EventBus for subscribing to price updates
            paper_trading_store: Store for fetching open trades
            broadcast_coordinator: BroadcastCoordinator for WebSocket broadcasting
        """
        self.event_bus = event_bus
        self.store = paper_trading_store
        self.broadcast_coordinator = broadcast_coordinator

        # Track which symbols we're monitoring (symbol → set of account_ids)
        self._monitored_symbols: Dict[str, Set[str]] = {}

        # Track active accounts with open positions
        self._active_accounts: Set[str] = set()

        # Price cache for detecting actual changes
        self._price_cache: Dict[str, float] = {}

        # Background refresh task
        self._refresh_task: Optional[asyncio.Task] = None

        # Subscribe to price update events
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)
        logger.info("PaperTradingPriceMonitor initialized - subscribing to MARKET_PRICE_UPDATE events")

    async def initialize(self) -> None:
        """Initialize the monitor and start background tasks."""
        # Refresh monitored symbols every 30 seconds
        self._refresh_task = asyncio.create_task(self._refresh_monitored_symbols())
        logger.info("PaperTradingPriceMonitor background tasks started")

    async def _refresh_monitored_symbols(self) -> None:
        """Background task to refresh which symbols we're monitoring."""
        while True:
            try:
                await asyncio.sleep(30)  # Refresh every 30 seconds

                # Get all accounts with open positions
                # Note: This is a simplified version - in production you'd query all accounts
                monitored_symbols = {}
                active_accounts = set()

                # For each active account, get their open positions
                # (In production, you'd iterate through all accounts in the database)
                for account_id in list(self._active_accounts):
                    try:
                        open_trades = await self.store.get_open_trades(account_id)
                        if open_trades:
                            active_accounts.add(account_id)
                            for trade in open_trades:
                                if trade.symbol not in monitored_symbols:
                                    monitored_symbols[trade.symbol] = set()
                                monitored_symbols[trade.symbol].add(account_id)
                    except Exception as e:
                        logger.error(f"Failed to refresh positions for account {account_id}: {e}")

                self._monitored_symbols = monitored_symbols
                self._active_accounts = active_accounts

                if monitored_symbols:
                    logger.debug(f"Monitoring {len(monitored_symbols)} symbols across {len(active_accounts)} accounts: {list(monitored_symbols.keys())}")

            except asyncio.CancelledError:
                logger.info("Price monitor refresh task cancelled")
                break
            except Exception as e:
                logger.error(f"Error refreshing monitored symbols: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def register_account(self, account_id: str) -> None:
        """Register an account for price monitoring.

        Args:
            account_id: Account ID to start monitoring
        """
        self._active_accounts.add(account_id)
        logger.info(f"Registered account {account_id} for real-time price monitoring")

    async def unregister_account(self, account_id: str) -> None:
        """Unregister an account from price monitoring.

        Args:
            account_id: Account ID to stop monitoring
        """
        self._active_accounts.discard(account_id)

        # Clean up monitored symbols
        for symbol in list(self._monitored_symbols.keys()):
            self._monitored_symbols[symbol].discard(account_id)
            if not self._monitored_symbols[symbol]:
                del self._monitored_symbols[symbol]

        logger.info(f"Unregistered account {account_id} from price monitoring")

    async def handle_event(self, event: Event) -> None:
        """Handle MARKET_PRICE_UPDATE events.

        Args:
            event: Price update event from MarketDataService
        """
        if event.type != EventType.MARKET_PRICE_UPDATE:
            return

        try:
            symbol = event.data.get("symbol")
            new_price = event.data.get("price")

            if not symbol or new_price is None:
                logger.warning(f"Invalid price update event: {event.data}")
                return

            # Check if this symbol affects any monitored positions
            affected_accounts = self._monitored_symbols.get(symbol, set())
            if not affected_accounts:
                # Not monitoring this symbol, skip
                return

            # Check if price actually changed (avoid unnecessary broadcasts)
            cached_price = self._price_cache.get(symbol)
            if cached_price == new_price:
                # Price hasn't changed, skip
                return

            self._price_cache[symbol] = new_price
            logger.info(f"Price update for {symbol}: ₹{new_price} (affects {len(affected_accounts)} accounts)")

            # Recalculate and broadcast updates for each affected account
            for account_id in affected_accounts:
                await self._broadcast_position_update(account_id, symbol, new_price)

        except Exception as e:
            logger.error(f"Error handling price update event: {e}", exc_info=True)

    async def _broadcast_position_update(self, account_id: str, symbol: str, new_price: float) -> None:
        """Recalculate position P&L and broadcast via WebSocket.

        Args:
            account_id: Account with affected position
            symbol: Symbol that updated
            new_price: New market price
        """
        try:
            # Get open trades for this symbol
            all_trades = await self.store.get_open_trades(account_id)
            affected_trades = [t for t in all_trades if t.symbol == symbol]

            if not affected_trades:
                return

            # Recalculate unrealized P&L for each affected position
            position_updates = []
            for trade in affected_trades:
                unrealized_pnl = (new_price - trade.entry_price) * trade.quantity
                unrealized_pnl_pct = (unrealized_pnl / (trade.entry_price * trade.quantity)) * 100 if trade.entry_price > 0 else 0.0

                position_update = {
                    "trade_id": trade.trade_id,
                    "symbol": trade.symbol,
                    "current_price": new_price,
                    "unrealized_pnl": unrealized_pnl,
                    "unrealized_pnl_pct": unrealized_pnl_pct,
                    "current_value": new_price * trade.quantity,
                    "updated_at": datetime.now().isoformat()
                }
                position_updates.append(position_update)

            # Broadcast to WebSocket clients
            if self.broadcast_coordinator and position_updates:
                await self.broadcast_coordinator.broadcast_to_ui({
                    "type": "paper_trading_position_update",
                    "account_id": account_id,
                    "symbol": symbol,
                    "positions": position_updates,
                    "timestamp": datetime.now().isoformat()
                })

                logger.info(f"Broadcasted real-time update for {symbol} to account {account_id}: {len(position_updates)} positions updated")

        except Exception as e:
            logger.error(f"Error broadcasting position update for {account_id}/{symbol}: {e}", exc_info=True)

    async def close(self) -> None:
        """Cleanup resources."""
        # Cancel background refresh task
        if self._refresh_task:
            self._refresh_task.cancel()
            try:
                await self._refresh_task
            except asyncio.CancelledError:
                pass

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.MARKET_PRICE_UPDATE, self)

        logger.info("PaperTradingPriceMonitor closed")
