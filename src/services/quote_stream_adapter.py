"""Provider-neutral quote stream adapters for paper-trading live marks."""

from __future__ import annotations

import asyncio
import gzip
import importlib.util
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Awaitable, Callable, Dict, Iterable, Optional

import aiofiles
import httpx

# KiteTicker import for Zerodha streaming
try:
    from kiteconnect import KiteTicker
except ImportError:
    KiteTicker = None

from src.config import Config
from src.models.market_data import MarketData, MarketDataProvider, SubscriptionMode

logger = logging.getLogger(__name__)

QuoteUpdateCallback = Callable[[MarketData], Awaitable[None]]


@dataclass(frozen=True)
class QuoteSubscriptionRequest:
    """Normalized quote subscription request."""

    symbol: str
    mode: SubscriptionMode


@dataclass
class QuoteStreamStatus:
    """Current status for a quote streaming adapter."""

    provider: str
    configured: bool
    connected: bool
    status: str
    summary: str
    detail: Optional[str] = None
    last_tick_at: Optional[str] = None
    last_error: Optional[str] = None
    active_symbols: int = 0
    mode: str = "ltpc"
    instrument_cache_ready: bool = False

    def to_metadata(self) -> Dict[str, object]:
        """Serialize status for capability checks and UI surfaces."""
        return {
            "provider": self.provider,
            "configured": self.configured,
            "connected": self.connected,
            "status": self.status,
            "summary": self.summary,
            "detail": self.detail,
            "last_tick_at": self.last_tick_at,
            "last_error": self.last_error,
            "active_symbols": self.active_symbols,
            "mode": self.mode,
            "instrument_cache_ready": self.instrument_cache_ready,
        }


class QuoteStreamAdapter(ABC):
    """Abstract contract for provider-backed live quote streams."""

    provider: MarketDataProvider
    supports_streaming: bool = True

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare the adapter for use."""

    @abstractmethod
    async def subscribe(self, requests: Iterable[QuoteSubscriptionRequest]) -> None:
        """Ensure the requested symbols are actively subscribed."""

    @abstractmethod
    async def unsubscribe(self, symbols: Iterable[str]) -> None:
        """Remove the requested symbols from the live stream."""

    @abstractmethod
    async def get_status(self) -> QuoteStreamStatus:
        """Return the current stream status."""

    @abstractmethod
    async def close(self) -> None:
        """Release stream resources."""

    def set_quote_update_callback(self, callback: QuoteUpdateCallback) -> None:
        """Update the callback used for normalized quote delivery."""
        return None


class NullQuoteStreamAdapter(QuoteStreamAdapter):
    """No-op adapter used when no quote provider is configured."""

    provider = MarketDataProvider.ALPHA_VANTAGE

    def __init__(self, reason: str = "No quote stream provider is configured.") -> None:
        self._reason = reason

    async def initialize(self) -> None:
        return None

    async def subscribe(self, requests: Iterable[QuoteSubscriptionRequest]) -> None:
        return None

    async def unsubscribe(self, symbols: Iterable[str]) -> None:
        return None

    async def get_status(self) -> QuoteStreamStatus:
        return QuoteStreamStatus(
            provider="none",
            configured=False,
            connected=False,
            status="blocked",
            summary="Quote stream is not configured.",
            detail=self._reason,
        )

    async def close(self) -> None:
        return None


class UpstoxInstrumentResolver:
    """Resolve NSE trading symbols to Upstox instrument keys using the official BOD JSON file."""

    NSE_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"

    def __init__(self, state_dir: Path) -> None:
        self._cache_path = state_dir / "upstox" / "nse_instruments.json.gz"
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._symbol_map: Dict[str, str] = {}
        self._loaded_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def cache_ready(self) -> bool:
        return bool(self._symbol_map)

    async def resolve_instrument_key(self, symbol: str) -> Optional[str]:
        """Resolve one NSE trading symbol to its Upstox instrument key."""
        await self._ensure_loaded()
        return self._symbol_map.get(symbol.upper())

    async def _ensure_loaded(self) -> None:
        async with self._lock:
            if self._symbol_map and self._loaded_at and datetime.now(timezone.utc) - self._loaded_at < timedelta(hours=12):
                return

            payload: Optional[bytes] = None
            if self._cache_path.exists():
                age = datetime.now(timezone.utc) - datetime.fromtimestamp(self._cache_path.stat().st_mtime, tz=timezone.utc)
                if age < timedelta(hours=24):
                    try:
                        async with aiofiles.open(self._cache_path, "rb") as handle:
                            payload = await handle.read()
                    except OSError as exc:
                        logger.warning("Failed to read Upstox instrument cache %s: %s", self._cache_path, exc)
                        payload = None

            if payload is None:
                async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                    response = await client.get(self.NSE_INSTRUMENTS_URL)
                    response.raise_for_status()
                    payload = response.content
                try:
                    async with aiofiles.open(self._cache_path, "wb") as handle:
                        await handle.write(payload)
                except OSError as exc:
                    logger.warning("Failed to write Upstox instrument cache %s: %s", self._cache_path, exc)

            records = json.loads(gzip.decompress(payload).decode("utf-8"))
            self._symbol_map = {
                str(item.get("trading_symbol", "")).upper(): item["instrument_key"]
                for item in records
                if item.get("segment") == "NSE_EQ"
                and item.get("instrument_type") in {"EQ", "BE"}
                and item.get("trading_symbol")
                and item.get("instrument_key")
            }
            self._loaded_at = datetime.now(timezone.utc)


class UpstoxQuoteStreamAdapter(QuoteStreamAdapter):
    """Official Upstox Market Data Feed V3 adapter."""

    provider = MarketDataProvider.UPSTOX

    def __init__(
        self,
        config: Config,
        on_quote_update: QuoteUpdateCallback,
    ) -> None:
        self._config = config
        self._on_quote_update = on_quote_update
        self._resolver = UpstoxInstrumentResolver(config.state_dir)
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = asyncio.Lock()

        self._sdk_available = importlib.util.find_spec("upstox_client") is not None
        self._streamer = None
        self._api_client = None
        self._connected = False
        self._status_summary = "Upstox quote stream has not been initialized."
        self._status_detail: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_tick_at: Optional[str] = None
        self._current_mode = self._normalize_mode(getattr(config.integration, "upstox_stream_mode", "ltpc") or "ltpc")
        self._symbol_to_key: Dict[str, str] = {}
        self._key_to_symbol: Dict[str, str] = {}

    async def initialize(self) -> None:
        self._loop = asyncio.get_running_loop()
        if not self._sdk_available:
            self._status_summary = "Upstox Python SDK is not installed."
            self._status_detail = "Install upstox-python-sdk to enable live paper-trading quote streaming."
            return

        access_token = getattr(self._config.integration, "upstox_access_token", None)
        if not access_token:
            self._status_summary = "Upstox access token is not configured."
            self._status_detail = "Set UPSTOX_ACCESS_TOKEN to enable Market Data Feed V3."
            return

        upstox_client = await asyncio.to_thread(__import__, "upstox_client")
        configuration = upstox_client.Configuration()
        configuration.access_token = access_token
        self._api_client = upstox_client.ApiClient(configuration)
        self._status_summary = "Upstox quote stream is configured and idle."
        self._status_detail = "Quotes will start streaming once symbols are subscribed."

    async def subscribe(self, requests: Iterable[QuoteSubscriptionRequest]) -> None:
        async with self._lock:
            if self._api_client is None:
                await self.initialize()
            if self._api_client is None:
                return

            normalized_requests = list(requests)
            if not normalized_requests:
                return

            instrument_keys: list[str] = []
            target_mode = self._current_mode
            for request in normalized_requests:
                instrument_key = await self._resolver.resolve_instrument_key(request.symbol)
                if not instrument_key:
                    logger.warning("Unable to resolve Upstox instrument key for %s", request.symbol)
                    continue
                symbol = request.symbol.upper()
                self._symbol_to_key[symbol] = instrument_key
                self._key_to_symbol[instrument_key] = symbol
                instrument_keys.append(instrument_key)
                target_mode = self._normalize_mode(request.mode.value)

            if not instrument_keys:
                self._status_summary = "Upstox quote stream could not resolve any instrument keys."
                self._status_detail = "The NSE instruments catalog did not contain the requested symbols."
                return

            if self._streamer is None:
                await self._create_streamer(instrument_keys, target_mode)
                await asyncio.to_thread(self._streamer.connect)
                return

            if target_mode != self._current_mode:
                await asyncio.to_thread(self._streamer.change_mode, instrument_keys, target_mode)
                self._current_mode = target_mode

            await asyncio.to_thread(self._streamer.subscribe, instrument_keys, target_mode)
            self._status_summary = "Upstox quote stream subscriptions updated."
            self._status_detail = f"Streaming {len(self._symbol_to_key)} active symbol(s)."

    async def unsubscribe(self, symbols: Iterable[str]) -> None:
        async with self._lock:
            if self._streamer is None:
                return

            instrument_keys: list[str] = []
            for raw_symbol in symbols:
                symbol = raw_symbol.upper()
                instrument_key = self._symbol_to_key.pop(symbol, None)
                if instrument_key:
                    self._key_to_symbol.pop(instrument_key, None)
                    instrument_keys.append(instrument_key)

            if instrument_keys:
                await asyncio.to_thread(self._streamer.unsubscribe, instrument_keys)

            if not self._symbol_to_key:
                self._status_summary = "Upstox quote stream is connected but idle."
                self._status_detail = "No active paper-trading symbols are subscribed."

    async def get_status(self) -> QuoteStreamStatus:
        configured = self._sdk_available and self._api_client is not None
        if not self._sdk_available:
            status = "blocked"
        elif not configured:
            status = "blocked"
        elif self._connected and self._is_last_tick_fresh():
            status = "ready"
        elif self._connected:
            status = "degraded"
        else:
            status = "degraded" if self._symbol_to_key else "blocked"

        return QuoteStreamStatus(
            provider=self.provider.value,
            configured=configured,
            connected=self._connected,
            status=status,
            summary=self._status_summary,
            detail=self._status_detail,
            last_tick_at=self._last_tick_at,
            last_error=self._last_error,
            active_symbols=len(self._symbol_to_key),
            mode=self._current_mode,
            instrument_cache_ready=self._resolver.cache_ready,
        )

    async def close(self) -> None:
        async with self._lock:
            if self._streamer is not None:
                try:
                    await asyncio.to_thread(self._streamer.disconnect)
                except Exception as exc:  # pragma: no cover - defensive cleanup
                    logger.warning("Failed to disconnect Upstox quote stream cleanly: %s", exc)
            self._streamer = None
            self._connected = False

    def set_quote_update_callback(self, callback: QuoteUpdateCallback) -> None:
        self._on_quote_update = callback

    async def _create_streamer(self, instrument_keys: list[str], mode: str) -> None:
        upstox_client = await asyncio.to_thread(__import__, "upstox_client")
        streamer = upstox_client.MarketDataStreamerV3(
            self._api_client,
            instrumentKeys=instrument_keys,
            mode=mode,
        )
        streamer.on("open", self._handle_open)
        streamer.on("message", self._handle_message)
        streamer.on("error", self._handle_error)
        streamer.on("close", self._handle_close)
        streamer.on("reconnecting", self._handle_reconnecting)
        streamer.on("autoReconnectStopped", self._handle_reconnect_stopped)
        if hasattr(streamer, "auto_reconnect"):
            streamer.auto_reconnect(True, 5, 5)
        self._streamer = streamer
        self._current_mode = mode
        self._status_summary = "Connecting to Upstox quote stream."
        self._status_detail = f"Subscribing to {len(instrument_keys)} instrument key(s)."

    def _normalize_mode(self, mode: str) -> str:
        return "full" if mode == SubscriptionMode.FULL.value else "ltpc"

    def _is_last_tick_fresh(self) -> bool:
        if not self._last_tick_at:
            return False
        last_tick = datetime.fromisoformat(self._last_tick_at)
        return datetime.now(timezone.utc) - last_tick <= timedelta(seconds=120)

    def _handle_open(self, *args) -> None:
        self._connected = True
        self._status_summary = "Upstox quote stream is connected."
        self._status_detail = f"Streaming {len(self._symbol_to_key)} active symbol(s) in {self._current_mode} mode."

    def _handle_close(self, *args) -> None:
        self._connected = False
        self._status_summary = "Upstox quote stream connection is closed."
        self._status_detail = "Reconnect or refresh subscriptions to resume live paper marks."

    def _handle_error(self, error: object) -> None:
        self._connected = False
        self._last_error = str(error)
        self._status_summary = "Upstox quote stream reported an error."
        self._status_detail = self._last_error

    def _handle_reconnecting(self, *args) -> None:
        self._connected = False
        self._status_summary = "Upstox quote stream is reconnecting."
        self._status_detail = "Live paper marks are temporarily degraded while the stream reconnects."

    def _handle_reconnect_stopped(self, *args) -> None:
        self._connected = False
        self._status_summary = "Upstox quote stream stopped reconnecting."
        self._status_detail = "Manual intervention is required to resume live quote streaming."

    def _handle_message(self, payload: Dict[str, object]) -> None:
        now = datetime.now(timezone.utc)
        self._last_tick_at = now.isoformat()
        self._status_summary = "Upstox quote stream is serving live quotes."
        self._status_detail = f"Last tick received at {self._last_tick_at}."

        feeds = payload.get("feeds") if isinstance(payload, dict) else None
        if not isinstance(feeds, dict):
            return

        for instrument_key, feed in feeds.items():
            symbol = self._key_to_symbol.get(instrument_key)
            if not symbol:
                continue

            try:
                normalized = self._normalize_feed(symbol, feed, payload.get("currentTs"))
                if normalized is None:
                    continue
                if self._loop is not None and not self._loop.is_closed():
                    asyncio.run_coroutine_threadsafe(self._on_quote_update(normalized), self._loop)
            except Exception as exc:
                logger.warning(
                    "Ignoring malformed Upstox feed for %s (%s): %s",
                    symbol,
                    instrument_key,
                    exc,
                )

    def _normalize_feed(
        self,
        symbol: str,
        feed: object,
        current_ts: object,
    ) -> Optional[MarketData]:
        if not isinstance(feed, dict):
            return None

        ltpc = None
        if isinstance(feed.get("ltpc"), dict):
            ltpc = feed["ltpc"]
        elif isinstance(feed.get("firstLevelWithGreeks"), dict):
            ltpc = feed["firstLevelWithGreeks"].get("ltpc")
        elif isinstance(feed.get("marketFF"), dict):
            ltpc = feed["marketFF"].get("ltpc")

        if not isinstance(ltpc, dict) or ltpc.get("ltp") is None:
            return None

        timestamp = datetime.now(timezone.utc)
        if current_ts is not None:
            try:
                timestamp = datetime.fromtimestamp(int(current_ts) / 1000, tz=timezone.utc)
            except Exception:
                pass

        close_price = ltpc.get("cp")
        return MarketData(
            symbol=symbol,
            ltp=float(ltpc["ltp"]),
            close_price=float(close_price) if close_price is not None else None,
            timestamp=timestamp.isoformat(),
            provider=self.provider.value,
        )


class KiteInstrumentResolver:
    """Resolve NSE trading symbols to Kite instrument tokens using the instruments API."""

    KITE_INSTRUMENTS_URL = "https://api.kite.trade/instruments"

    def __init__(self, api_key: str, access_token: str, state_dir: Path) -> None:
        self._api_key = api_key
        self._access_token = access_token
        self._cache_path = state_dir / "kite" / "nse_instruments.json"
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._symbol_map: Dict[str, int] = {}  # symbol -> instrument_token
        self._loaded_at: Optional[datetime] = None
        self._lock = asyncio.Lock()

    @property
    def cache_ready(self) -> bool:
        return bool(self._symbol_map)

    async def resolve_instrument_token(self, symbol: str) -> Optional[int]:
        """Resolve one NSE trading symbol to its Kite instrument token."""
        await self._ensure_loaded()
        return self._symbol_map.get(symbol.upper())

    async def _ensure_loaded(self) -> None:
        async with self._lock:
            if self._symbol_map and self._loaded_at and datetime.now(timezone.utc) - self._loaded_at < timedelta(hours=12):
                return

            payload: Optional[str] = None
            if self._cache_path.exists():
                age = datetime.now(timezone.utc) - datetime.fromtimestamp(self._cache_path.stat().st_mtime, tz=timezone.utc)
                if age < timedelta(hours=24):
                    try:
                        async with aiofiles.open(self._cache_path, "r", encoding="utf-8") as handle:
                            payload = await handle.read()
                    except OSError as exc:
                        logger.warning("Failed to read Kite instrument cache %s: %s", self._cache_path, exc)
                        payload = None

            if payload is None:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    # Kite instruments endpoint requires api_key as query param
                    url = f"{self.KITE_INSTRUMENTS_URL}?api_key={self._api_key}"
                    response = await client.get(url)
                    response.raise_for_status()
                    payload = response.text
                try:
                    async with aiofiles.open(self._cache_path, "w", encoding="utf-8") as handle:
                        await handle.write(payload)
                except OSError as exc:
                    logger.warning("Failed to write Kite instrument cache %s: %s", self._cache_path, exc)

            # Parse CSV format: instrument_token,exchange,tradingsymbol,...
            lines = payload.strip().split("\n")
            if len(lines) < 2:
                return

            headers = lines[0].split(",")
            try:
                symbol_idx = headers.index("tradingsymbol")
                token_idx = headers.index("instrument_token")
                exchange_idx = headers.index("exchange")
            except ValueError:
                logger.warning("Kite instruments CSV missing required columns")
                return

            self._symbol_map = {}
            for line in lines[1:]:
                parts = line.split(",")
                if len(parts) <= max(symbol_idx, token_idx, exchange_idx):
                    continue
                exchange = parts[exchange_idx]
                symbol = parts[symbol_idx].upper()
                try:
                    token = int(parts[token_idx])
                except ValueError:
                    continue
                if exchange == "NSE":
                    self._symbol_map[symbol] = token

            self._loaded_at = datetime.now(timezone.utc)


class KiteTickerQuoteStreamAdapter(QuoteStreamAdapter):
    """Zerodha Kite Connect WebSocket adapter for real-time market data."""

    provider = MarketDataProvider.ZERODHA_KITE

    def __init__(
        self,
        config: Config,
        on_quote_update: QuoteUpdateCallback,
    ) -> None:
        self._config = config
        self._on_quote_update = on_quote_update
        self._api_key = getattr(config.integration, "zerodha_api_key", None)
        self._access_token = getattr(config.integration, "zerodha_access_token", None)
        self._resolver = KiteInstrumentResolver(self._api_key, self._access_token, config.state_dir) if self._api_key else None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = asyncio.Lock()

        self._sdk_available = KiteTicker is not None
        self._ticker = None
        self._connected = False
        self._connection_ready = None  # threading.Event for connection synchronization
        self._status_summary = "KiteTicker has not been initialized."
        self._status_detail: Optional[str] = None
        self._last_error: Optional[str] = None
        self._last_tick_at: Optional[str] = None
        self._current_mode = "ltp"
        self._symbol_to_token: Dict[str, int] = {}
        self._token_to_symbol: Dict[int, str] = {}

    async def initialize(self) -> None:
        self._loop = asyncio.get_running_loop()
        if not self._sdk_available:
            self._status_summary = "KiteConnect package is not installed."
            self._status_detail = "Install kiteconnect to enable live paper-trading quote streaming."
            return

        if not self._api_key:
            self._status_summary = "Zerodha API key is not configured."
            self._status_detail = "Set ZERODHA_API_KEY to enable KiteTicker streaming."
            return

        if not self._access_token:
            self._status_summary = "Zerodha access token is not configured."
            self._status_detail = "Set ZERODHA_ACCESS_TOKEN to enable KiteTicker streaming."
            return

        self._status_summary = "KiteTicker is configured and idle."
        self._status_detail = "Quotes will start streaming once symbols are subscribed."

    async def subscribe(self, requests: Iterable[QuoteSubscriptionRequest]) -> None:
        logger.info("KiteTickerQuoteStreamAdapter.subscribe called")
        async with self._lock:
            if not self._sdk_available:
                await self.initialize()
            if not self._sdk_available or not self._api_key or not self._access_token:
                logger.warning("KiteTicker subscribe: SDK not available or credentials missing")
                return

            normalized_requests = list(requests)
            if not normalized_requests:
                logger.warning("KiteTicker subscribe: no requests")
                return

            instrument_tokens: list[int] = []
            for request in normalized_requests:
                if not self._resolver:
                    continue
                instrument_token = await self._resolver.resolve_instrument_token(request.symbol)
                if not instrument_token:
                    logger.warning("Unable to resolve Kite instrument token for %s", request.symbol)
                    continue
                symbol = request.symbol.upper()
                self._symbol_to_token[symbol] = instrument_token
                self._token_to_symbol[instrument_token] = symbol
                instrument_tokens.append(instrument_token)

            if not instrument_tokens:
                self._status_summary = "KiteTicker could not resolve any instrument tokens."
                self._status_detail = "The NSE instruments did not contain the requested symbols."
                return

            logger.info(f"KiteTicker subscribe: ticker={'None' if self._ticker is None else 'exists'}, tokens={len(instrument_tokens)}")
            if self._ticker is None:
                logger.info("KiteTicker subscribe: creating new ticker")
                await self._create_ticker(instrument_tokens)
                return

            # Subscribe to new tokens
            await asyncio.to_thread(self._ticker.subscribe, instrument_tokens)
            await self._apply_mode(instrument_tokens)
            self._status_summary = "KiteTicker subscriptions updated."
            self._status_detail = f"Streaming {len(self._symbol_to_token)} active symbol(s)."

    async def unsubscribe(self, symbols: Iterable[str]) -> None:
        async with self._lock:
            if self._ticker is None:
                return

            instrument_tokens: list[int] = []
            for raw_symbol in symbols:
                symbol = raw_symbol.upper()
                instrument_token = self._symbol_to_token.pop(symbol, None)
                if instrument_token:
                    self._token_to_symbol.pop(instrument_token, None)
                    instrument_tokens.append(instrument_token)

            if instrument_tokens:
                await asyncio.to_thread(self._ticker.unsubscribe, instrument_tokens)

            if not self._symbol_to_token:
                self._status_summary = "KiteTicker is connected but idle."
                self._status_detail = "No active paper-trading symbols are subscribed."

    async def get_status(self) -> QuoteStreamStatus:
        configured = self._sdk_available and self._api_key and self._access_token
        if not self._sdk_available:
            status = "blocked"
        elif not configured:
            status = "blocked"
        elif self._connected and self._is_last_tick_fresh():
            status = "ready"
        elif self._connected:
            status = "degraded"
        else:
            status = "degraded" if self._symbol_to_token else "blocked"

        return QuoteStreamStatus(
            provider=self.provider.value,
            configured=configured,
            connected=self._connected,
            status=status,
            summary=self._status_summary,
            detail=self._status_detail,
            last_tick_at=self._last_tick_at,
            last_error=self._last_error,
            active_symbols=len(self._symbol_to_token),
            mode=self._current_mode,
            instrument_cache_ready=self._resolver.cache_ready if self._resolver else False,
        )

    async def close(self) -> None:
        async with self._lock:
            if self._ticker is not None:
                try:
                    await asyncio.to_thread(self._ticker.close)
                except Exception as exc:
                    logger.warning("Failed to disconnect KiteTicker cleanly: %s", exc)
            self._ticker = None
            self._connected = False

    def set_quote_update_callback(self, callback: QuoteUpdateCallback) -> None:
        self._on_quote_update = callback

    async def update_credentials(
        self,
        *,
        api_key: Optional[str] = None,
        access_token: Optional[str] = None,
    ) -> None:
        """Refresh runtime Kite credentials without recreating the service."""
        async with self._lock:
            if api_key:
                self._api_key = api_key
            if access_token:
                self._access_token = access_token

            if self._ticker is not None:
                try:
                    await asyncio.to_thread(self._ticker.close)
                except Exception as exc:
                    logger.warning("Failed to close KiteTicker during credential refresh: %s", exc)

            self._ticker = None
            self._connected = False
            self._resolver = (
                KiteInstrumentResolver(self._api_key, self._access_token, self._config.state_dir)
                if self._api_key and self._access_token
                else None
            )

        await self.initialize()

    async def _create_ticker(self, instrument_tokens: list[int]) -> None:
        # Import KiteTicker here to avoid top-level import issues
        import kiteconnect
        import threading
        KiteTickerCls = kiteconnect.KiteTicker
        logger.info(f"_create_ticker called with {len(instrument_tokens)} tokens")

        self._ticker = KiteTickerCls(self._api_key, self._access_token)

        # Set up event handlers
        # Zerodha's SDK invokes `on_ticks`, not `on_tick`.
        self._ticker.on_ticks = self._handle_tick
        self._ticker.on_connect = self._handle_connect
        self._ticker.on_close = self._handle_close
        self._ticker.on_error = self._handle_error
        self._ticker.on_reconnect = self._handle_reconnect
        self._ticker.on_noreconnect = self._handle_noreconnect

        # Enable auto-reconnect
        self._ticker.auto_reconnect = True
        self._ticker.reconnect_interval = 5  # seconds

        # Create connection ready event for synchronization
        self._connection_ready = threading.Event()

        # Use threaded=True and wait for connection callback
        # The daemon thread started by connect() handles the websocket
        try:
            logger.info(f"Connecting to KiteTicker with API key: {self._api_key[:4]}***")

            # Run connect in a daemon thread - it creates its own thread for websocket
            self._ticker.connect(threaded=True)

            # Wait for connection callback with timeout
            if not self._connection_ready.wait(timeout=15):
                raise Exception("KiteTicker connection timeout - on_connect callback not received within 15s")

            logger.info("KiteTicker connected successfully, subscribing to %d instruments", len(instrument_tokens))

            # Subscribe runs in thread pool since ticker is now connected
            await asyncio.to_thread(self._ticker.subscribe, instrument_tokens)
            await self._apply_mode(instrument_tokens)
            self._status_summary = "Connecting to KiteTicker."
            self._status_detail = f"Subscribing to {len(instrument_tokens)} instrument token(s)."
        except Exception as exc:
            logger.error(f"Failed to connect to KiteTicker: {exc}")
            self._last_error = str(exc)
            self._status_summary = "KiteTicker connection failed."
            self._status_detail = f"Error: {exc}"
            self._ticker = None
            self._connection_ready = None
            return

    async def _apply_mode(self, instrument_tokens: list[int]) -> None:
        """Apply the configured Zerodha stream mode after subscribing."""
        if self._ticker is None or not instrument_tokens:
            return

        mode_map = {
            SubscriptionMode.FULL.value: getattr(self._ticker, "MODE_FULL", "full"),
            SubscriptionMode.QUOTE.value: getattr(self._ticker, "MODE_QUOTE", "quote"),
            SubscriptionMode.LTP.value: getattr(self._ticker, "MODE_LTP", "ltp"),
        }
        target_mode = mode_map.get(self._current_mode, getattr(self._ticker, "MODE_LTP", "ltp"))
        await asyncio.to_thread(self._ticker.set_mode, target_mode, instrument_tokens)
        self._current_mode = SubscriptionMode.LTP.value if target_mode == getattr(self._ticker, "MODE_LTP", "ltp") else self._current_mode

    def _is_last_tick_fresh(self) -> bool:
        if not self._last_tick_at:
            return False
        last_tick = datetime.fromisoformat(self._last_tick_at)
        return datetime.now(timezone.utc) - last_tick <= timedelta(seconds=120)

    def _handle_connect(self, *args) -> None:
        logger.info("KiteTicker _handle_connect called! args=%s", args)
        self._connected = True
        self._status_summary = "KiteTicker is connected."
        self._status_detail = f"Streaming {len(self._symbol_to_token)} active symbol(s) in {self._current_mode} mode."
        # Signal that connection is ready
        if self._connection_ready is not None:
            self._connection_ready.set()
            logger.info("KiteTicker connection ready event set")

    def _handle_close(self, *args) -> None:
        self._connected = False
        self._status_summary = "KiteTicker connection is closed."
        self._status_detail = "Reconnect or refresh subscriptions to resume live paper marks."
        # Clear connection ready event for reconnect scenarios
        if self._connection_ready is not None:
            self._connection_ready.clear()

    def _handle_error(self, *args) -> None:
        # KiteTicker passes (ws, code, reason) to on_error
        error_msg = str(args) if args else "Unknown error"
        self._connected = False
        self._last_error = error_msg
        self._status_summary = "KiteTicker reported an error."
        self._status_detail = error_msg
        logger.error("KiteTicker error: %s", args)
        # Clear connection ready event for reconnect scenarios
        if self._connection_ready is not None:
            self._connection_ready.clear()

    def _handle_reconnect(self, *args) -> None:
        self._connected = False
        self._status_summary = "KiteTicker is reconnecting."
        self._status_detail = f"Reconnect attempt {args}"

    def _handle_noreconnect(self, *args) -> None:
        self._connected = False
        self._status_summary = "KiteTicker stopped reconnecting."
        self._status_detail = "Manual intervention is required to resume live quote streaming."
        # Clear connection ready event
        if self._connection_ready is not None:
            self._connection_ready.clear()

    def _handle_tick(self, *args) -> None:
        # KiteTicker passes (ws, ticks) where ticks can be a single dict or list of dicts
        tick_data = args[1] if len(args) > 1 else args[0] if args else None
        if tick_data is None:
            return

        now = datetime.now(timezone.utc)
        self._last_tick_at = now.isoformat()
        self._status_summary = "KiteTicker is serving live quotes."
        self._status_detail = f"Last tick received at {self._last_tick_at}."

        # Handle both single tick and list of ticks
        ticks = tick_data if isinstance(tick_data, list) else [tick_data]

        for t in ticks:
            if not isinstance(t, dict):
                continue

            instrument_token = t.get("instrument_token")
            if not instrument_token:
                continue

            symbol = self._token_to_symbol.get(instrument_token)
            if not symbol:
                continue

            normalized = self._normalize_tick(symbol, t)
            if normalized is None:
                continue

            if self._loop is not None and not self._loop.is_closed():
                asyncio.run_coroutine_threadsafe(self._on_quote_update(normalized), self._loop)

    def _normalize_tick(self, symbol: str, tick: object) -> Optional[MarketData]:
        if not isinstance(tick, dict):
            return None

        ltp = tick.get("last_price")
        if ltp is None:
            return None

        timestamp = datetime.now(timezone.utc)
        if tick.get("timestamp"):
            try:
                timestamp = datetime.fromisoformat(str(tick.get("timestamp")).replace("Z", "+00:00"))
            except Exception:
                pass

        close_price = tick.get("close") or tick.get("last_price")

        return MarketData(
            symbol=symbol,
            ltp=float(ltp),
            close_price=float(close_price) if close_price else None,
            timestamp=timestamp.isoformat(),
            provider=self.provider.value,
        )
