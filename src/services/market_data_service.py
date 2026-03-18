"""
Market Data Service

Provides real-time market data integration, price feeds, and market data management
for live trading operations.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import aiosqlite
from loguru import logger

from src.config import Config
from src.models.market_data import MarketData, MarketDataProvider, SubscriptionMode
from ..core.event_bus import EventBus, Event, EventType, EventHandler
from .quote_stream_adapter import (
    NullQuoteStreamAdapter,
    QuoteStreamAdapter,
    QuoteStreamStatus,
    QuoteSubscriptionRequest,
)


@dataclass
class MarketSubscription:
    """Market data subscription."""
    symbol: str
    mode: SubscriptionMode
    provider: MarketDataProvider
    active: bool = True
    last_update: str = ""

    def __post_init__(self):
        if not self.last_update:
            self.last_update = datetime.now(timezone.utc).isoformat()


class MarketDataService(EventHandler):
    """
    Market Data Service - Real-time market data integration.

    Responsibilities:
    - Real-time price feeds from multiple providers
    - Market data subscription management
    - Price caching and optimization
    - Market data validation and error handling
    - Event-driven price updates
    """

    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        broker=None,
        quote_stream_adapter: Optional[QuoteStreamAdapter] = None,
        default_provider: MarketDataProvider = MarketDataProvider.UPSTOX,
    ):
        self.config = config
        self.event_bus = event_bus
        self.broker = broker  # Optional for paper trading only
        self.quote_stream_adapter = quote_stream_adapter or NullQuoteStreamAdapter()
        self.default_provider = default_provider
        configured_mode = getattr(config.integration, "upstox_stream_mode", SubscriptionMode.LTP.value)
        self.default_subscription_mode = (
            SubscriptionMode.FULL if configured_mode == SubscriptionMode.FULL.value else SubscriptionMode.LTP
        )
        self.db_path = config.state_dir / "market_data.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Database connection
        self._db_connection: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Market data state
        self._market_data: Dict[str, MarketData] = {}
        self._subscriptions: Dict[str, MarketSubscription] = {}
        self._update_interval = 5  # seconds

        # Background tasks
        self._update_task: Optional[asyncio.Task] = None
        self._cleanup_task: Optional[asyncio.Task] = None

        # Subscribe to relevant events
        self.event_bus.subscribe(EventType.MARKET_PRICE_UPDATE, self)

    async def initialize(self) -> None:
        """Initialize the market data service."""
        async with self._lock:
            self._db_connection = await aiosqlite.connect(str(self.db_path))
            await self._create_tables()
            await self._load_subscriptions()
            await self._load_cached_data()
            await self.quote_stream_adapter.initialize()
            logger.info("Market data service initialized")

            # Start background tasks
            self._update_task = asyncio.create_task(self._background_price_updates())
            self._cleanup_task = asyncio.create_task(self._cache_cleanup())

        await self._sync_streaming_subscriptions()

    async def _create_tables(self) -> None:
        """Create market data database tables."""
        schema = """
        -- Market data cache
        CREATE TABLE IF NOT EXISTS market_data_cache (
            symbol TEXT PRIMARY KEY,
            ltp REAL NOT NULL,
            open_price REAL,
            high_price REAL,
            low_price REAL,
            close_price REAL,
            volume INTEGER,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL,
            cached_at TEXT NOT NULL
        );

        -- Market subscriptions
        CREATE TABLE IF NOT EXISTS market_subscriptions (
            symbol TEXT PRIMARY KEY,
            mode TEXT NOT NULL,
            provider TEXT NOT NULL,
            active INTEGER DEFAULT 1,
            last_update TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Price history (for analytics)
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            price REAL NOT NULL,
            volume INTEGER,
            timestamp TEXT NOT NULL,
            provider TEXT NOT NULL
        );

        -- Indexes
        CREATE INDEX IF NOT EXISTS idx_cache_timestamp ON market_data_cache(timestamp);
        CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON market_subscriptions(active);
        CREATE INDEX IF NOT EXISTS idx_history_symbol_timestamp ON price_history(symbol, timestamp);
        """

        await self._db_connection.executescript(schema)
        await self._db_connection.commit()

    async def _load_subscriptions(self) -> None:
        """Load subscriptions from database."""
        cursor = await self._db_connection.execute("""
            SELECT symbol, mode, provider, active, last_update
            FROM market_subscriptions
            WHERE active = 1
        """)

        async for row in cursor:
            subscription = MarketSubscription(
                symbol=row[0],
                mode=SubscriptionMode(row[1]),
                provider=MarketDataProvider(row[2]),
                active=bool(row[3]),
                last_update=row[4]
            )
            self._subscriptions[row[0]] = subscription

    async def _load_cached_data(self) -> None:
        """Load cached market data from database."""
        cursor = await self._db_connection.execute("""
            SELECT symbol, ltp, open_price, high_price, low_price, close_price, volume, timestamp, provider
            FROM market_data_cache
            WHERE datetime(cached_at) > datetime('now', '-5 minutes')
        """)

        async for row in cursor:
            market_data = MarketData(
                symbol=row[0],
                ltp=row[1],
                open_price=row[2],
                high_price=row[3],
                low_price=row[4],
                close_price=row[5],
                volume=row[6],
                timestamp=row[7],
                provider=row[8]
            )
            self._market_data[row[0]] = market_data

    async def _sync_streaming_subscriptions(self) -> None:
        """Ensure streaming provider subscriptions are reattached after startup."""
        if self.quote_stream_adapter.provider != MarketDataProvider.UPSTOX:
            return

        requests = [
            QuoteSubscriptionRequest(symbol=sub.symbol, mode=sub.mode)
            for sub in self._subscriptions.values()
            if sub.active and sub.provider == MarketDataProvider.UPSTOX
        ]
        if requests:
            await self.quote_stream_adapter.subscribe(requests)

    async def subscribe_market_data(
        self,
        symbol: str,
        mode: SubscriptionMode = SubscriptionMode.LTP,
        provider: Optional[MarketDataProvider] = None,
    ) -> bool:
        """Subscribe to market data for a symbol."""
        provider = provider or self.default_provider
        async with self._lock:
            if symbol in self._subscriptions:
                # Update existing subscription
                subscription = self._subscriptions[symbol]
                subscription.mode = mode
                subscription.provider = provider
                subscription.active = True
                subscription.last_update = datetime.now(timezone.utc).isoformat()

                await self._db_connection.execute("""
                    UPDATE market_subscriptions SET mode = ?, provider = ?, active = 1, last_update = ?
                    WHERE symbol = ?
                """, (mode.value, provider.value, subscription.last_update, symbol))
            else:
                # Create new subscription
                subscription = MarketSubscription(
                    symbol=symbol,
                    mode=mode,
                    provider=provider
                )
                self._subscriptions[symbol] = subscription

                now = datetime.now(timezone.utc).isoformat()
                await self._db_connection.execute("""
                    INSERT INTO market_subscriptions (symbol, mode, provider, active, last_update, created_at)
                    VALUES (?, ?, ?, 1, ?, ?)
                """, (symbol, mode.value, provider.value, now, now))

            await self._db_connection.commit()

        await self._activate_subscription(symbol, mode, provider)
        logger.info(f"Subscribed to {mode.value} data for {symbol} via {provider.value}")
        return True

    async def unsubscribe_market_data(self, symbol: str) -> bool:
        """Unsubscribe from market data for a symbol."""
        provider: Optional[MarketDataProvider] = None
        async with self._lock:
            if symbol in self._subscriptions:
                subscription = self._subscriptions[symbol]
                provider = subscription.provider
                subscription.active = False

                await self._db_connection.execute("""
                    UPDATE market_subscriptions SET active = 0 WHERE symbol = ?
                """, (symbol,))
                await self._db_connection.commit()

                # Remove from memory
                del self._subscriptions[symbol]
                if symbol in self._market_data:
                    del self._market_data[symbol]
            else:
                return False

        if provider is not None:
            await self._deactivate_subscription(symbol, provider)

        logger.info(f"Unsubscribed from market data for {symbol}")
        return True

    async def get_market_data(self, symbol: str) -> Optional[MarketData]:
        """Get current market data for a symbol."""
        async with self._lock:
            return self._market_data.get(symbol)

    async def get_multiple_market_data(self, symbols: List[str]) -> Dict[str, MarketData]:
        """Get market data for multiple symbols."""
        async with self._lock:
            result = {}
            for symbol in symbols:
                if symbol in self._market_data:
                    result[symbol] = self._market_data[symbol]
            return result

    async def get_quote_stream_status(self) -> QuoteStreamStatus:
        """Return the current quote stream status."""
        return await self.quote_stream_adapter.get_status()

    async def apply_runtime_preferences(
        self,
        *,
        provider: Optional[str] = None,
        mode: Optional[str] = None,
    ) -> None:
        """Apply runtime quote-provider preferences to future and active subscriptions."""
        if provider:
            try:
                self.default_provider = MarketDataProvider(provider)
            except ValueError:
                logger.warning("Ignoring unknown quote stream provider preference: %s", provider)

        if mode:
            try:
                self.default_subscription_mode = SubscriptionMode(mode)
            except ValueError:
                logger.warning("Ignoring unknown quote stream mode preference: %s", mode)

        async with self._lock:
            active_subscriptions = [sub for sub in self._subscriptions.values() if sub.active]
            for subscription in active_subscriptions:
                subscription.provider = self.default_provider
                subscription.mode = self.default_subscription_mode
                subscription.last_update = datetime.now(timezone.utc).isoformat()
                await self._db_connection.execute(
                    """
                    UPDATE market_subscriptions
                    SET provider = ?, mode = ?, last_update = ?
                    WHERE symbol = ?
                    """,
                    (
                        subscription.provider.value,
                        subscription.mode.value,
                        subscription.last_update,
                        subscription.symbol,
                    ),
                )
            await self._db_connection.commit()

        if active_subscriptions:
            await self.refresh_active_subscriptions()

    async def refresh_active_subscriptions(self) -> List[str]:
        """Refresh active subscriptions using the configured provider for each symbol."""
        async with self._lock:
            active_subscriptions = [
                subscription
                for subscription in self._subscriptions.values()
                if subscription.active
            ]

        refreshed_symbols: List[str] = []
        for subscription in active_subscriptions:
            await self._activate_subscription(subscription.symbol, subscription.mode, subscription.provider)
            refreshed_symbols.append(subscription.symbol)

        return refreshed_symbols

    async def _activate_subscription(
        self,
        symbol: str,
        mode: SubscriptionMode,
        provider: MarketDataProvider,
    ) -> None:
        """Activate the runtime path for one subscription."""
        if provider == self.quote_stream_adapter.provider:
            await self.quote_stream_adapter.subscribe([QuoteSubscriptionRequest(symbol=symbol, mode=mode)])
            return
        await self._fetch_symbol_data(symbol, provider)

    async def _deactivate_subscription(self, symbol: str, provider: MarketDataProvider) -> None:
        """Deactivate the runtime path for one subscription."""
        if provider == self.quote_stream_adapter.provider:
            await self.quote_stream_adapter.unsubscribe([symbol])

    async def _fetch_symbol_data(self, symbol: str, provider: MarketDataProvider) -> None:
        """Fetch market data for a symbol from the specified provider."""
        try:
            if provider == MarketDataProvider.ZERODHA_KITE:
                await self._fetch_from_zerodha(symbol)
            elif provider == MarketDataProvider.UPSTOX:
                await self._fetch_from_upstox(symbol)
            else:
                await self._fetch_from_broker_api(symbol)

        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol} from {provider.value}: {e}")

    async def _fetch_from_zerodha(self, symbol: str) -> None:
        """Fetch data from Zerodha Kite."""
        if self.broker is None:
            logger.warning("Zerodha broker is not configured on MarketDataService")
            return

        if not await self.broker.is_authenticated():
            logger.warning("Zerodha broker not authenticated, skipping data fetch")
            return

        try:
            # Convert symbol to Zerodha format if needed
            kite_symbol = self._convert_to_kite_symbol(symbol)

            # Get quote
            quotes = await self.broker.quote(kite_symbol)
            if kite_symbol in quotes:
                quote = quotes[kite_symbol]

                market_data = MarketData(
                    symbol=symbol,
                    ltp=quote.get("last_price", 0),
                    open_price=quote.get("ohlc", {}).get("open"),
                    high_price=quote.get("ohlc", {}).get("high"),
                    low_price=quote.get("ohlc", {}).get("low"),
                    close_price=quote.get("ohlc", {}).get("close"),
                    volume=quote.get("volume"),
                    provider="zerodha_kite"
                )

                await self._update_market_data(market_data)

        except Exception as e:
            logger.error(f"Failed to fetch from Zerodha for {symbol}: {e}")

    async def _fetch_from_upstox(self, symbol: str) -> None:
        """Ensure Upstox live quote subscriptions are active."""
        await self.quote_stream_adapter.subscribe(
            [QuoteSubscriptionRequest(symbol=symbol, mode=self.default_subscription_mode)]
        )

    async def _fetch_from_broker_api(self, symbol: str) -> None:
        """Fallback to broker API."""
        if hasattr(self.broker, 'quote'):
            try:
                quotes = await self.broker.quote(instruments=[symbol])
                if symbol in quotes:
                    quote = quotes[symbol]
                    market_data = MarketData(
                        symbol=symbol,
                        ltp=quote.get("last_price", 0),
                        provider="broker_api"
                    )
                    await self._update_market_data(market_data)
            except Exception as e:
                logger.error(f"Failed to fetch from broker API for {symbol}: {e}")

    def _convert_to_kite_symbol(self, symbol: str) -> str:
        """Convert standard symbol to Zerodha Kite format."""
        # This would handle symbol format conversions
        # For now, assume NSE format
        return f"NSE:{symbol}"

    async def _update_market_data(self, market_data: MarketData) -> None:
        """Update market data in memory and database."""
        async with self._lock:
            # Update memory
            self._market_data[market_data.symbol] = market_data

            # Update database cache
            now = datetime.now(timezone.utc).isoformat()
            await self._db_connection.execute("""
                INSERT OR REPLACE INTO market_data_cache
                (symbol, ltp, open_price, high_price, low_price, close_price, volume, timestamp, provider, cached_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                market_data.symbol,
                market_data.ltp,
                market_data.open_price,
                market_data.high_price,
                market_data.low_price,
                market_data.close_price,
                market_data.volume,
                market_data.timestamp,
                market_data.provider,
                now
            ))

            # Store in price history
            await self._db_connection.execute("""
                INSERT INTO price_history (symbol, price, volume, timestamp, provider)
                VALUES (?, ?, ?, ?, ?)
            """, (
                market_data.symbol,
                market_data.ltp,
                market_data.volume,
                market_data.timestamp,
                market_data.provider
            ))

            await self._db_connection.commit()

            # Emit price update event
            await self.event_bus.publish(Event(
                id=f"price_update_{market_data.symbol}_{int(datetime.now(timezone.utc).timestamp())}",
                type=EventType.MARKET_PRICE_UPDATE,
                timestamp=market_data.timestamp,
                source="market_data_service",
                data={
                    "symbol": market_data.symbol,
                    "price": market_data.ltp,
                    "volume": market_data.volume,
                    "provider": market_data.provider
                }
            ))

    async def _background_price_updates(self) -> None:
        """Background task for polling non-streaming providers and healing streaming subscriptions."""
        while True:
            try:
                await asyncio.sleep(self._update_interval)

                active_subscriptions = [subscription for subscription in self._subscriptions.values() if subscription.active]
                if not active_subscriptions:
                    continue

                streaming_subscriptions = [
                    sub for sub in active_subscriptions if sub.provider == self.quote_stream_adapter.provider
                ]
                if streaming_subscriptions:
                    await self.quote_stream_adapter.subscribe(
                        [
                            QuoteSubscriptionRequest(symbol=sub.symbol, mode=sub.mode)
                            for sub in streaming_subscriptions
                        ]
                    )

                polled_subscriptions = [
                    sub for sub in active_subscriptions if sub.provider != self.quote_stream_adapter.provider
                ]
                if polled_subscriptions:
                    await asyncio.gather(
                        *[
                            self._fetch_symbol_data(subscription.symbol, subscription.provider)
                            for subscription in polled_subscriptions
                        ]
                    )

            except asyncio.CancelledError:
                logger.info("Background price update task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in background price updates: {e}")
                await asyncio.sleep(5)  # Wait before retrying

    async def _cache_cleanup(self) -> None:
        """Background task for cache cleanup."""
        while True:
            try:
                await asyncio.sleep(300)  # Clean up every 5 minutes

                # Remove old cache entries
                cutoff_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
                await self._db_connection.execute("""
                    DELETE FROM market_data_cache WHERE cached_at < ?
                """, (cutoff_time,))
                await self._db_connection.commit()

                # Remove old price history (keep last 30 days)
                history_cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                await self._db_connection.execute("""
                    DELETE FROM price_history WHERE timestamp < ?
                """, (history_cutoff,))
                await self._db_connection.commit()

            except asyncio.CancelledError:
                logger.info("Cache cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)

    async def get_price_history(self, symbol: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get price history for a symbol."""
        cutoff_time = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()

        cursor = await self._db_connection.execute("""
            SELECT price, volume, timestamp, provider
            FROM price_history
            WHERE symbol = ? AND timestamp > ?
            ORDER BY timestamp ASC
        """, (symbol, cutoff_time))

        history = []
        async for row in cursor:
            history.append({
                "price": row[0],
                "volume": row[1],
                "timestamp": row[2],
                "provider": row[3]
            })

        return history

    async def get_active_subscriptions(self) -> Dict[str, MarketSubscription]:
        """Get all active subscriptions."""
        async with self._lock:
            return {k: v for k, v in self._subscriptions.items() if v.active}

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.MARKET_PRICE_UPDATE:
            # This could trigger additional processing or alerts
            pass

    async def close(self) -> None:
        """Close the market data service."""
        # Cancel background tasks
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass

        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._db_connection:
            await self._db_connection.close()
            self._db_connection = None

        await self.quote_stream_adapter.close()
