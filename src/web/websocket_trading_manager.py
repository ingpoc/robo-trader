"""
WebSocket trading manager for real-time trading data broadcasting.

This service manages WebSocket connections for real-time trading data,
including live quotes, position updates, order status changes, and P&L tracking.
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, asdict
import websockets
from websockets.server import WebSocketServerProtocol

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.core.database_state.real_time_trading_state import (
    RealTimeTradingState, RealTimeQuote, OrderBookEntry, RealTimePosition
)


@dataclass
class WebSocketMessage:
    """WebSocket message structure."""
    type: str
    data: Dict[str, Any]
    timestamp: str
    account_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class ClientSubscription:
    """Client subscription information."""
    session_id: str
    account_id: Optional[str] = None
    subscribed_symbols: Set[str] = None
    subscribed_events: Set[str] = None
    last_ping: datetime = None

    def __post_init__(self):
        if self.subscribed_symbols is None:
            self.subscribed_symbols = set()
        if self.subscribed_events is None:
            self.subscribed_events = set()
        if self.last_ping is None:
            self.last_ping = datetime.now()


class WebSocketTradingManager:
    """WebSocket manager for real-time trading data broadcasting."""

    def __init__(self, real_time_state: RealTimeTradingState):
        self.real_time_state = real_time_state
        self.logger = logging.getLogger(__name__)

        # WebSocket connections
        self.connections: Dict[str, WebSocketServerProtocol] = {}
        self.client_subscriptions: Dict[str, ClientSubscription] = {}
        self._running = False
        self._lock = asyncio.Lock()

        # Event types for subscriptions
        self.available_events = {
            "quotes", "positions", "orders", "portfolio", "trades",
            "market_updates", "order_status", "pnl_updates"
        }

        # Broadcasting intervals
        self._broadcast_intervals = {
            "quotes": 2,  # Every 2 seconds
            "positions": 5,  # Every 5 seconds
            "portfolio": 10,  # Every 10 seconds
            "keep_alive": 30  # Every 30 seconds
        }

        # Market data cache
        self._quotes_cache: Dict[str, RealTimeQuote] = {}
        self._positions_cache: Dict[str, List[RealTimePosition]] = {}
        self._orders_cache: Dict[str, List[OrderBookEntry]] = {}

    async def initialize(self):
        """Initialize WebSocket trading manager."""
        try:
            self._running = True
            asyncio.create_task(self._background_broadcasting())
            asyncio.create_task(self._cleanup_inactive_connections())
            self.logger.info("WebSocket trading manager initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebSocket trading manager: {e}")
            raise TradingError(
                f"WebSocket trading manager initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH
            )

    async def register_connection(self, websocket: WebSocketServerProtocol,
                                session_id: str, account_id: Optional[str] = None) -> bool:
        """Register a new WebSocket connection."""
        try:
            async with self._lock:
                self.connections[session_id] = websocket
                self.client_subscriptions[session_id] = ClientSubscription(
                    session_id=session_id,
                    account_id=account_id
                )

                # Send initial connection confirmation
                await self._send_message(session_id, WebSocketMessage(
                    type="connection_established",
                    data={
                        "session_id": session_id,
                        "account_id": account_id,
                        "available_events": list(self.available_events),
                        "message": "WebSocket connection established for real-time trading"
                    },
                    timestamp=datetime.now().isoformat()
                ))

                # Send initial data if account is specified
                if account_id:
                    await self._send_initial_data(session_id, account_id)

                self.logger.info(f"WebSocket connection registered: {session_id} (account: {account_id})")
                return True

        except Exception as e:
            self.logger.error(f"Failed to register WebSocket connection {session_id}: {e}")
            return False

    async def unregister_connection(self, session_id: str):
        """Unregister WebSocket connection."""
        try:
            async with self._lock:
                if session_id in self.connections:
                    del self.connections[session_id]
                if session_id in self.client_subscriptions:
                    del self.client_subscriptions[session_id]

                self.logger.info(f"WebSocket connection unregistered: {session_id}")

        except Exception as e:
            self.logger.error(f"Failed to unregister WebSocket connection {session_id}: {e}")

    async def subscribe_to_symbols(self, session_id: str, symbols: List[str]) -> bool:
        """Subscribe client to specific symbols."""
        try:
            if session_id not in self.client_subscriptions:
                return False

            async with self._lock:
                subscription = self.client_subscriptions[session_id]
                subscription.subscribed_symbols.update(symbols)

                # Send current quotes for subscribed symbols
                current_quotes = {}
                for symbol in symbols:
                    if symbol in self._quotes_cache:
                        current_quotes[symbol] = asdict(self._quotes_cache[symbol])

                if current_quotes:
                    await self._send_message(session_id, WebSocketMessage(
                        type="quotes_update",
                        data=current_quotes,
                        timestamp=datetime.now().isoformat()
                    ))

                self.logger.info(f"Client {session_id} subscribed to symbols: {symbols}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe symbols for {session_id}: {e}")
            return False

    async def subscribe_to_events(self, session_id: str, events: List[str]) -> bool:
        """Subscribe client to specific events."""
        try:
            if session_id not in self.client_subscriptions:
                return False

            # Validate events
            invalid_events = set(events) - self.available_events
            if invalid_events:
                raise TradingError(
                    f"Invalid events: {invalid_events}",
                    category=ErrorCategory.VALIDATION,
                    severity=ErrorSeverity.MEDIUM
                )

            async with self._lock:
                subscription = self.client_subscriptions[session_id]
                subscription.subscribed_events.update(events)

                self.logger.info(f"Client {session_id} subscribed to events: {events}")
                return True

        except Exception as e:
            self.logger.error(f"Failed to subscribe events for {session_id}: {e}")
            return False

    async def broadcast_quote_update(self, symbol: str, quote: RealTimeQuote):
        """Broadcast quote update to subscribed clients."""
        try:
            # Update cache
            self._quotes_cache[symbol] = quote

            # Broadcast to subscribed clients
            message = WebSocketMessage(
                type="quote_update",
                data={"symbol": symbol, **asdict(quote)},
                timestamp=datetime.now().isoformat()
            )

            await self._broadcast_to_subscribed_clients("quotes", symbol, message)

        except Exception as e:
            self.logger.error(f"Failed to broadcast quote update for {symbol}: {e}")

    async def broadcast_position_update(self, account_id: str, position: RealTimePosition):
        """Broadcast position update to subscribed clients."""
        try:
            # Update cache
            if account_id not in self._positions_cache:
                self._positions_cache[account_id] = []

            # Update or add position in cache
            existing_positions = self._positions_cache[account_id]
            for i, existing_pos in enumerate(existing_positions):
                if existing_pos.symbol == position.symbol and existing_pos.product_type == position.product_type:
                    existing_positions[i] = position
                    break
            else:
                existing_positions.append(position)

            # Broadcast to subscribed clients
            message = WebSocketMessage(
                type="position_update",
                data={"account_id": account_id, **asdict(position)},
                timestamp=datetime.now().isoformat(),
                account_id=account_id
            )

            await self._broadcast_to_account_subscribers("positions", account_id, message)

        except Exception as e:
            self.logger.error(f"Failed to broadcast position update for {account_id}: {e}")

    async def broadcast_order_update(self, account_id: str, order: OrderBookEntry):
        """Broadcast order update to subscribed clients."""
        try:
            # Update cache
            if account_id not in self._orders_cache:
                self._orders_cache[account_id] = []

            # Update or add order in cache
            existing_orders = self._orders_cache[account_id]
            for i, existing_order in enumerate(existing_orders):
                if existing_order.order_id == order.order_id:
                    existing_orders[i] = order
                    break
            else:
                existing_orders.append(order)

            # Broadcast to subscribed clients
            message = WebSocketMessage(
                type="order_update",
                data={"account_id": account_id, **asdict(order)},
                timestamp=datetime.now().isoformat(),
                account_id=account_id
            )

            await self._broadcast_to_account_subscribers("orders", account_id, message)

        except Exception as e:
            self.logger.error(f"Failed to broadcast order update for {account_id}: {e}")

    async def broadcast_portfolio_update(self, account_id: str, portfolio_data: Dict[str, Any]):
        """Broadcast portfolio update to subscribed clients."""
        try:
            message = WebSocketMessage(
                type="portfolio_update",
                data={"account_id": account_id, **portfolio_data},
                timestamp=datetime.now().isoformat(),
                account_id=account_id
            )

            await self._broadcast_to_account_subscribers("portfolio", account_id, message)

        except Exception as e:
            self.logger.error(f"Failed to broadcast portfolio update for {account_id}: {e}")

    async def _send_message(self, session_id: str, message: WebSocketMessage):
        """Send message to specific client."""
        try:
            if session_id not in self.connections:
                return

            websocket = self.connections[session_id]
            message_data = asdict(message)
            await websocket.send(json.dumps(message_data))

        except Exception as e:
            self.logger.error(f"Failed to send message to {session_id}: {e}")
            # Remove dead connection
            await self.unregister_connection(session_id)

    async def _broadcast_to_subscribed_clients(self, event_type: str, symbol: str, message: WebSocketMessage):
        """Broadcast message to clients subscribed to symbol/event."""
        try:
            async with self._lock:
                for session_id, subscription in self.client_subscriptions.items():
                    if (event_type in subscription.subscribed_events and
                        symbol in subscription.subscribed_symbols):
                        await self._send_message(session_id, message)

        except Exception as e:
            self.logger.error(f"Failed to broadcast to subscribed clients: {e}")

    async def _broadcast_to_account_subscribers(self, event_type: str, account_id: str, message: WebSocketMessage):
        """Broadcast message to clients subscribed to account events."""
        try:
            async with self._lock:
                for session_id, subscription in self.client_subscriptions.items():
                    if (subscription.account_id == account_id and
                        event_type in subscription.subscribed_events):
                        await self._send_message(session_id, message)

        except Exception as e:
            self.logger.error(f"Failed to broadcast to account subscribers: {e}")

    async def _send_initial_data(self, session_id: str, account_id: str):
        """Send initial data to newly connected client."""
        try:
            # Send current positions
            positions = await self.real_time_state.get_positions_by_account(account_id)
            if positions:
                await self._send_message(session_id, WebSocketMessage(
                    type="positions_initial",
                    data={
                        "account_id": account_id,
                        "positions": [asdict(pos) for pos in positions]
                    },
                    timestamp=datetime.now().isoformat(),
                    account_id=account_id
                ))

            # Send recent orders
            recent_orders = await self.real_time_state.get_orders_by_account(account_id, limit=20)
            if recent_orders:
                await self._send_message(session_id, WebSocketMessage(
                    type="orders_initial",
                    data={
                        "account_id": account_id,
                        "orders": [asdict(order) for order in recent_orders]
                    },
                    timestamp=datetime.now().isoformat(),
                    account_id=account_id
                ))

        except Exception as e:
            self.logger.error(f"Failed to send initial data to {session_id}: {e}")

    async def _background_broadcasting(self):
        """Background task for periodic broadcasting."""
        while self._running:
            try:
                await asyncio.sleep(self._broadcast_intervals["quotes"])
                await self._broadcast_quotes_updates()

                await asyncio.sleep(self._broadcast_intervals["positions"])
                await self._broadcast_positions_updates()

                await asyncio.sleep(self._broadcast_intervals["portfolio"])
                await self._broadcast_portfolio_updates()

            except Exception as e:
                self.logger.error(f"Background broadcasting error: {e}")
                await asyncio.sleep(5)  # Brief pause on error

    async def _broadcast_quotes_updates(self):
        """Broadcast periodic quotes updates."""
        try:
            # Get symbols that clients are subscribed to
            subscribed_symbols = set()
            for subscription in self.client_subscriptions.values():
                subscribed_symbols.update(subscription.subscribed_symbols)

            if not subscribed_symbols:
                return

            # Get latest quotes
            quotes = await self.real_time_state.get_multiple_quotes(list(subscribed_symbols))
            if quotes:
                # Update cache and broadcast
                for symbol, quote in quotes.items():
                    self._quotes_cache[symbol] = quote
                    await self.broadcast_quote_update(symbol, quote)

        except Exception as e:
            self.logger.error(f"Failed to broadcast quotes updates: {e}")

    async def _broadcast_positions_updates(self):
        """Broadcast periodic positions updates."""
        try:
            # Get unique account IDs
            account_ids = set()
            for subscription in self.client_subscriptions.values():
                if subscription.account_id:
                    account_ids.add(subscription.account_id)

            for account_id in account_ids:
                try:
                    positions = await self.real_time_state.get_positions_by_account(account_id)
                    for position in positions:
                        await self.broadcast_position_update(account_id, position)

                except Exception as e:
                    self.logger.error(f"Failed to broadcast positions for {account_id}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to broadcast positions updates: {e}")

    async def _broadcast_portfolio_updates(self):
        """Broadcast periodic portfolio updates."""
        try:
            # Get unique account IDs
            account_ids = set()
            for subscription in self.client_subscriptions.values():
                if subscription.account_id:
                    account_ids.add(subscription.account_id)

            for account_id in account_ids:
                try:
                    # Calculate portfolio metrics
                    positions = await self.real_time_state.get_positions_by_account(account_id)

                    total_value = sum(pos.value for pos in positions if pos.value > 0)
                    total_pnl = sum(pos.total_pnl for pos in positions)
                    total_investment = sum(pos.investment for pos in positions if pos.investment > 0)

                    portfolio_data = {
                        "total_value": total_value,
                        "total_pnl": total_pnl,
                        "total_investment": total_investment,
                        "pnl_percent": (total_pnl / total_investment) * 100 if total_investment > 0 else 0,
                        "positions_count": len([pos for pos in positions if pos.quantity != 0])
                    }

                    await self.broadcast_portfolio_update(account_id, portfolio_data)

                except Exception as e:
                    self.logger.error(f"Failed to broadcast portfolio for {account_id}: {e}")

        except Exception as e:
            self.logger.error(f"Failed to broadcast portfolio updates: {e}")

    async def _cleanup_inactive_connections(self):
        """Clean up inactive WebSocket connections."""
        while self._running:
            try:
                await asyncio.sleep(self._broadcast_intervals["keep_alive"])

                current_time = datetime.now()
                inactive_sessions = []

                async with self._lock:
                    for session_id, subscription in self.client_subscriptions.items():
                        # Check if connection is inactive
                        time_since_last_ping = (current_time - subscription.last_ping).total_seconds()

                        if time_since_last_ping > self._broadcast_intervals["keep_alive"] * 2:
                            inactive_sessions.append(session_id)
                            continue

                        # Send ping
                        if session_id in self.connections:
                            try:
                                await self._send_message(session_id, WebSocketMessage(
                                    type="ping",
                                    data={"timestamp": current_time.isoformat()},
                                    timestamp=current_time.isoformat()
                                ))
                                subscription.last_ping = current_time
                            except Exception:
                                # Connection is dead
                                inactive_sessions.append(session_id)

                # Remove inactive connections
                for session_id in inactive_sessions:
                    await self.unregister_connection(session_id)
                    self.logger.info(f"Removed inactive connection: {session_id}")

            except Exception as e:
                self.logger.error(f"Cleanup task error: {e}")
                await asyncio.sleep(10)

    async def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics."""
        try:
            async with self._lock:
                total_connections = len(self.connections)
                account_connections = {}
                symbol_subscriptions = {}
                event_subscriptions = {}

                for subscription in self.client_subscriptions.values():
                    # Account connections
                    if subscription.account_id:
                        account_connections[subscription.account_id] = account_connections.get(subscription.account_id, 0) + 1

                    # Symbol subscriptions
                    for symbol in subscription.subscribed_symbols:
                        symbol_subscriptions[symbol] = symbol_subscriptions.get(symbol, 0) + 1

                    # Event subscriptions
                    for event in subscription.subscribed_events:
                        event_subscriptions[event] = event_subscriptions.get(event, 0) + 1

                return {
                    "total_connections": total_connections,
                    "account_connections": account_connections,
                    "symbol_subscriptions": symbol_subscriptions,
                    "event_subscriptions": event_subscriptions,
                    "available_events": list(self.available_events),
                    "cache_sizes": {
                        "quotes": len(self._quotes_cache),
                        "positions": sum(len(positions) for positions in self._positions_cache.values()),
                        "orders": sum(len(orders) for orders in self._orders_cache.values())
                    }
                }

        except Exception as e:
            self.logger.error(f"Failed to get connection stats: {e}")
            return {}

    async def close(self):
        """Close WebSocket trading manager and cleanup."""
        try:
            self._running = False

            # Close all connections
            for session_id in list(self.connections.keys()):
                await self.unregister_connection(session_id)

            self.logger.info("WebSocket trading manager closed")

        except Exception as e:
            self.logger.error(f"Error closing WebSocket trading manager: {e}")


# Global instance for use in the application
_websocket_manager = None


async def get_websocket_trading_manager(real_time_state: RealTimeTradingState) -> WebSocketTradingManager:
    """Get or create WebSocket trading manager instance."""
    global _websocket_manager

    if _websocket_manager is None:
        _websocket_manager = WebSocketTradingManager(real_time_state)
        await _websocket_manager.initialize()

    return _websocket_manager


async def close_websocket_trading_manager():
    """Close global WebSocket trading manager."""
    global _websocket_manager

    if _websocket_manager:
        await _websocket_manager.close()
        _websocket_manager = None