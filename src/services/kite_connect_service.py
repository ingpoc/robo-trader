"""
Kite Connect integration service for real-time trading.

This service handles Kite Connect authentication, market data fetching,
order placement, and WebSocket connections for real-time updates.
"""

import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import websockets
import threading

from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.core.database_state.real_time_trading_state import (
    RealTimeTradingState, KiteSession, RealTimeQuote, OrderBookEntry
)

try:
    from kiteconnect import KiteConnect, KiteTicker
    from kiteconnect.exceptions import KiteException, KiteConnectException
except ImportError:
    # For development without actual KiteConnect
    KiteConnect = None
    KiteTicker = None
    logging.warning("KiteConnect not available - using mock implementation")


@dataclass
class KiteCredentials:
    """Kite Connect API credentials."""
    api_key: str
    api_secret: str
    request_token: Optional[str] = None


@dataclass
class OrderRequest:
    """Kite Connect order request."""
    tradingsymbol: str
    exchange: str
    transaction_type: str  # BUY or SELL
    quantity: int
    product: str  # CNC, INTRADAY, CO, OCO
    order_type: str  # MARKET, LIMIT, SL, SL-M
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    validity: str = "DAY"  # DAY, IOC
    disclosed_quantity: Optional[int] = None
    squareoff: Optional[float] = None
    stoploss: Optional[float] = None
    trailing_stoploss: Optional[float] = None


@dataclass
class QuoteData:
    """Quote data from Kite Connect."""
    instrument_token: int
    timestamp: str
    last_price: float
    last_quantity: int
    last_trade_time: str
    average_price: float
    volume: int
    buy_quantity: int
    sell_quantity: int
    ohlc: Dict[str, float]
    change: float
    change_percent: float


class MockKiteConnect:
    """Mock Kite Connect for development without actual API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.access_token = None
        self.request_token = None
        self.session_expiry = None

        # Mock data
        self._mock_quotes = {
            "RELIANCE": {"last_price": 2500.0, "change": 50.0, "volume": 1000000},
            "TCS": {"last_price": 3500.0, "change": -30.0, "volume": 500000},
            "INFY": {"last_price": 1500.0, "change": 20.0, "volume": 800000},
        }

    def set_access_token(self, access_token: str):
        """Set access token."""
        self.access_token = access_token
        self.session_expiry = datetime.now() + timedelta(hours=24)

    def generate_session(self, request_token: str, api_secret: str) -> Dict[str, Any]:
        """Generate session (mock)."""
        return {
            "user_id": "TEST_USER",
            "public_token": "TEST_PUBLIC_TOKEN",
            "access_token": "TEST_ACCESS_TOKEN",
            "enctoken": "TEST_ENCRYPTION_TOKEN",
            "refresh_token": "TEST_REFRESH_TOKEN",
            "user_type": "individual",
            "email": "test@example.com",
            "user_name": "Test User",
            "user_shortname": "Test",
            "avatar_url": None,
            "broker": "ZERODHA",
            "products": ["CNC", "MIS", "CO", "BO"],
            "exchanges": ["NSE", "BSE", "MCX", "CDS"],
            "login_time": datetime.now().isoformat(),
            "expiry": (datetime.now() + timedelta(days=1)).isoformat()
        }

    def instruments(self, exchange: str = "NSE") -> List[Dict[str, Any]]:
        """Get instruments (mock)."""
        return [
            {
                "instrument_token": 738561,
                "exchange_token": "500112",
                "tradingsymbol": "RELIANCE",
                "name": "Reliance Industries Ltd.",
                "last_price": 2500.0,
                "expiry": None,
                "strike": None,
                "tick_size": 0.05,
                "lot_size": 1,
                "instrument_type": "EQB",
                "segment": "EQUITY",
                "exchange": "NSE"
            }
        ]

    def quote(self, instruments: List[str]) -> Dict[str, QuoteData]:
        """Get quotes (mock)."""
        result = {}
        for instrument in instruments:
            symbol = instrument.split(":")[-1] if ":" in instrument else instrument
            if symbol in self._mock_quotes:
                data = self._mock_quotes[symbol]
                result[instrument] = QuoteData(
                    instrument_token=738561,
                    timestamp=datetime.now().isoformat(),
                    last_price=data["last_price"],
                    last_quantity=100,
                    last_trade_time=datetime.now().isoformat(),
                    average_price=data["last_price"],
                    volume=data["volume"],
                    buy_quantity=5000,
                    sell_quantity=3000,
                    ohlc={"open": data["last_price"] - data["change"], "high": data["last_price"] + 10, "low": data["last_price"] - 20, "close": data["last_price"]},
                    change=data["change"],
                    change_percent=(data["change"] / (data["last_price"] - data["change"])) * 100
                )
        return result

    def place_order(self, tradingsymbol: str, exchange: str, transaction_type: str,
                   quantity: int, product: str, order_type: str, price: Optional[float] = None,
                   trigger_price: Optional[float] = None, validity: str = "DAY",
                   disclosed_quantity: Optional[int] = None, squareoff: Optional[float] = None,
                   stoploss: Optional[float] = None, trailing_stoploss: Optional[float] = None,
                   variety: str = "regular") -> Dict[str, Any]:
        """Place order (mock)."""
        order_id = f"ORDER_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{quantity}"
        return {
            "order_id": order_id,
            "status": "COMPLETE",
            "status_message": "ORDER COMPLETE",
            "average_price": price or self._mock_quotes.get(tradingsymbol, {}).get("last_price", 2500.0),
            "quantity": quantity,
            "filled_quantity": quantity,
            "pending_quantity": 0,
            "cancelled_quantity": 0,
            "order_timestamp": datetime.now().isoformat(),
            "exchange_order_id": f"EX_{order_id}",
            "exchange_timestamp": datetime.now().isoformat(),
            "variety": variety,
            "exchange": exchange,
            "tradingsymbol": tradingsymbol,
            "order_type": order_type,
            "transaction_type": transaction_type,
            "validity": validity,
            "product": product,
            "price": price,
            "trigger_price": trigger_price,
            "squareoff": squareoff,
            "stoploss": stoploss,
            "trailing_stoploss": trailing_stoploss,
            "disclosed_quantity": disclosed_quantity
        }

    def cancel_order(self, order_id: str, variety: str = "regular") -> Dict[str, Any]:
        """Cancel order (mock)."""
        return {
            "order_id": order_id,
            "status": "CANCELLED",
            "status_message": "ORDER CANCELLED",
            "order_timestamp": datetime.now().isoformat(),
            "exchange_order_id": f"EX_{order_id}",
            "exchange_timestamp": datetime.now().isoformat()
        }

    def positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get positions (mock)."""
        return {
            "day": [],
            "net": [
                {
                    "tradingsymbol": "RELIANCE",
                    "exchange": "NSE",
                    "instrument_token": 738561,
                    "product": "CNC",
                    "quantity": 10,
                    "overnight_quantity": 10,
                    "multiplier": 1,
                    "price": 2500.0,
                    "close_price": 2520.0,
                    "last_price": 2520.0,
                    "pnl": 200.0,
                    "m2m": 200.0,
                    "unrealised": 200.0,
                    "realised": 0.0,
                    "buy_value": 25000.0,
                    "sell_value": 0.0,
                    "day_buy_value": 0.0,
                    "day_sell_value": 0.0,
                    "buy_quantity": 10,
                    "sell_quantity": 0,
                    "buy_price": 2500.0,
                    "sell_price": 0.0,
                    "day_buy_quantity": 0,
                    "day_sell_quantity": 0,
                    "day_buy_price": 0.0,
                    "day_sell_price": 0.0
                }
            ]
        }

    def holdings(self) -> List[Dict[str, Any]]:
        """Get holdings (mock)."""
        return [
            {
                "tradingsymbol": "RELIANCE",
                "exchange": "NSE",
                "instrument_token": 738561,
                "isin": "INE002A01018",
                "product": "CNC",
                "quantity": 10,
                "t1_quantity": 0,
                "average_price": 2500.0,
                "last_price": 2520.0,
                "close_price": 2520.0,
                "pnl": 200.0,
                "pnlpercentage": 0.8
            }
        ]


class KiteConnectService:
    """Kite Connect integration service."""

    def __init__(self, config: Dict[str, Any], real_time_state: RealTimeTradingState):
        self.config = config
        self.real_time_state = real_time_state
        self.logger = logging.getLogger(__name__)

        # Kite Connect client
        self.kite = None
        self.kite_ticker = None
        self._credentials = None
        self._active_session = None

        # WebSocket connections
        self._ws_connections = {}
        self._ws_threads = {}
        self._running = False

        # Rate limiting
        self._last_api_call = {}
        self._min_interval = 0.1  # 100ms between calls

    async def initialize(self, credentials: KiteCredentials) -> bool:
        """Initialize Kite Connect service."""
        try:
            self._credentials = credentials

            # Initialize Kite Connect client
            if KiteConnect:
                self.kite = KiteConnect(api_key=credentials.api_key)
                self.logger.info("Kite Connect client initialized")
            else:
                self.kite = MockKiteConnect(api_key=credentials.api_key)
                self.logger.info("Mock Kite Connect client initialized")

            # Try to restore existing session
            await self._restore_session()

            self._running = True
            self.logger.info("Kite Connect service initialized successfully")
            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize Kite Connect service: {e}")
            raise TradingError(
                f"Kite Connect service initialization failed: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def _restore_session(self) -> bool:
        """Restore existing Kite session from database."""
        try:
            # Assuming we have a default account for paper trading
            account_id = "paper_swing_main"
            session = await self.real_time_state.get_active_kite_session(account_id)

            if session and session.access_token:
                # Check if session is still valid
                if self._is_session_valid(session):
                    self.kite.set_access_token(session.access_token)
                    self._active_session = session
                    self.logger.info("Restored existing Kite session")
                    return True
                else:
                    # Deactivate expired session
                    session.active = False
                    await self.real_time_state.store_kite_session(session)
                    self.logger.info("Deactivated expired Kite session")

            return False

        except Exception as e:
            self.logger.error(f"Failed to restore Kite session: {e}")
            return False

    def _is_session_valid(self, session: KiteSession) -> bool:
        """Check if session is still valid."""
        if not session.expires_at:
            return False

        try:
            expiry = datetime.fromisoformat(session.expires_at.replace('Z', '+00:00'))
            # Consider session valid if expires in more than 5 minutes
            return expiry > datetime.now() + timedelta(minutes=5)
        except:
            return False

    async def authenticate(self, request_token: str) -> Dict[str, Any]:
        """Authenticate with Kite Connect using request token."""
        try:
            if not self.kite or not self._credentials:
                raise TradingError(
                    "Kite Connect not initialized",
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH
                )

            # Generate session
            session_data = self.kite.generate_session(request_token, self._credentials.api_secret)

            # Set access token
            self.kite.set_access_token(session_data["access_token"])

            # Store session
            account_id = "paper_swing_main"
            session = KiteSession(
                account_id=account_id,
                user_id=session_data.get("user_id"),
                public_token=session_data.get("public_token"),
                access_token=session_data.get("access_token"),
                refresh_token=session_data.get("refresh_token"),
                enctoken=session_data.get("enctoken"),
                user_type=session_data.get("user_type"),
                email=session_data.get("email"),
                user_name=session_data.get("user_name"),
                user_shortname=session_data.get("user_shortname"),
                avatar_url=session_data.get("avatar_url"),
                broker=session_data.get("broker", "ZERODHA"),
                products=json.dumps(session_data.get("products", [])),
                exchanges=json.dumps(session_data.get("exchanges", [])),
                expires_at=session_data.get("expiry"),
                active=True
            )

            await self.real_time_state.store_kite_session(session)
            self._active_session = session

            self.logger.info(f"Kite Connect authenticated for user {session_data.get('user_name')}")
            return session_data

        except Exception as e:
            self.logger.error(f"Kite Connect authentication failed: {e}")
            raise TradingError(
                f"Kite Connect authentication failed: {e}",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def get_login_url(self) -> str:
        """Get Kite Connect login URL."""
        if not self.kite or not self._credentials:
            raise TradingError(
                "Kite Connect not initialized",
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH
            )

        return self.kite.login_url()

    async def place_order(self, order_request: OrderRequest, account_id: str = "paper_swing_main") -> Dict[str, Any]:
        """Place order through Kite Connect."""
        try:
            if not self.kite or not self._active_session:
                raise TradingError(
                    "Kite Connect not authenticated",
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH
                )

            # Rate limiting
            await self._rate_limit_check("place_order")

            # Place order
            start_time = datetime.now()
            result = self.kite.place_order(
                tradingsymbol=order_request.tradingsymbol,
                exchange=order_request.exchange,
                transaction_type=order_request.transaction_type,
                quantity=order_request.quantity,
                product=order_request.product,
                order_type=order_request.order_type,
                price=order_request.price,
                trigger_price=order_request.trigger_price,
                validity=order_request.validity,
                disclosed_quantity=order_request.disclosed_quantity,
                squareoff=order_request.squareoff,
                stoploss=order_request.stoploss,
                trailing_stoploss=order_request.trailing_stoploss,
                variety="regular"
            )

            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Store order in database
            order_entry = OrderBookEntry(
                order_id=result["order_id"],
                account_id=account_id,
                symbol=order_request.tradingsymbol,
                exchange=order_request.exchange,
                order_type=order_request.transaction_type,
                product_type=order_request.product,
                quantity=order_request.quantity,
                price=order_request.price,
                trigger_price=order_request.trigger_price,
                status=result["status"],
                filled_quantity=result.get("filled_quantity", 0),
                pending_quantity=result.get("pending_quantity", 0),
                average_price=result.get("average_price", 0.0),
                placed_at=result.get("order_timestamp", datetime.now().isoformat()),
                exchange_order_id=result.get("exchange_order_id"),
                exchange_timestamp=result.get("exchange_timestamp")
            )

            await self.real_time_state.store_order(order_entry)

            # Log execution
            await self.real_time_state.log_trade_execution(
                account_id=account_id,
                order_id=result["order_id"],
                symbol=order_request.tradingsymbol,
                action="PLACE_ORDER",
                request_data=json.dumps(order_request.__dict__),
                response_data=json.dumps(result),
                status="SUCCESS",
                execution_time_ms=execution_time
            )

            self.logger.info(f"Order placed successfully: {result['order_id']}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to place order: {e}")

            # Log execution failure
            await self.real_time_state.log_trade_execution(
                account_id=account_id,
                order_id=None,
                symbol=order_request.tradingsymbol,
                action="PLACE_ORDER",
                request_data=json.dumps(order_request.__dict__),
                response_data=None,
                status="ERROR",
                error_message=str(e)
            )

            raise TradingError(
                f"Failed to place order: {e}",
                category=ErrorCategory.EXECUTION,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    async def cancel_order(self, order_id: str, account_id: str = "paper_swing_main") -> Dict[str, Any]:
        """Cancel order."""
        try:
            if not self.kite or not self._active_session:
                raise TradingError(
                    "Kite Connect not authenticated",
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH
                )

            # Rate limiting
            await self._rate_limit_check("cancel_order")

            # Cancel order
            result = self.kite.cancel_order(order_id, variety="regular")

            # Update order status in database
            await self.real_time_state.update_order_status(
                order_id=order_id,
                status=result["status"]
            )

            # Log execution
            await self.real_time_state.log_trade_execution(
                account_id=account_id,
                order_id=order_id,
                symbol="",
                action="CANCEL_ORDER",
                request_data=f"order_id: {order_id}",
                response_data=json.dumps(result),
                status="SUCCESS"
            )

            self.logger.info(f"Order cancelled successfully: {order_id}")
            return result

        except Exception as e:
            self.logger.error(f"Failed to cancel order {order_id}: {e}")

            # Log execution failure
            await self.real_time_state.log_trade_execution(
                account_id=account_id,
                order_id=order_id,
                symbol="",
                action="CANCEL_ORDER",
                request_data=f"order_id: {order_id}",
                response_data=None,
                status="ERROR",
                error_message=str(e)
            )

            raise TradingError(
                f"Failed to cancel order: {e}",
                category=ErrorCategory.EXECUTION,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def get_quotes(self, symbols: List[str]) -> Dict[str, QuoteData]:
        """Get real-time quotes for multiple symbols."""
        try:
            if not self.kite or not self._active_session:
                raise TradingError(
                    "Kite Connect not authenticated",
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH
                )

            # Rate limiting
            await self._rate_limit_check("quote")

            # Prepare instrument tokens
            instruments = [f"NSE:{symbol}" for symbol in symbols]

            # Get quotes
            quotes_data = self.kite.quote(instruments)

            # Convert to QuoteData objects and store in database
            result = {}
            for instrument, quote in quotes_data.items():
                symbol = instrument.split(":")[-1] if ":" in instrument else instrument

                quote_data = QuoteData(
                    instrument_token=quote["instrument_token"],
                    timestamp=quote.get("timestamp", datetime.now().isoformat()),
                    last_price=quote["last_price"],
                    last_quantity=quote.get("last_quantity", 0),
                    last_trade_time=quote.get("last_trade_time", ""),
                    average_price=quote["average_price"],
                    volume=quote["volume"],
                    buy_quantity=quote["buy_quantity"],
                    sell_quantity=quote["sell_quantity"],
                    ohlc=quote["ohlc"],
                    change=quote["change"],
                    change_percent=quote["change_percent"]
                )

                result[symbol] = quote_data

                # Store in database
                real_time_quote = RealTimeQuote(
                    symbol=symbol,
                    last_price=quote["last_price"],
                    change_price=quote["change"],
                    change_percent=quote["change_percent"],
                    volume=quote["volume"],
                    timestamp=quote.get("timestamp", datetime.now().isoformat())
                )
                await self.real_time_state.store_real_time_quote(real_time_quote)

            return result

        except Exception as e:
            self.logger.error(f"Failed to get quotes: {e}")
            raise TradingError(
                f"Failed to get quotes: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def get_positions(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get current positions."""
        try:
            if not self.kite or not self._active_session:
                raise TradingError(
                    "Kite Connect not authenticated",
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH
                )

            # Rate limiting
            await self._rate_limit_check("positions")

            positions = self.kite.positions()
            return positions

        except Exception as e:
            self.logger.error(f"Failed to get positions: {e}")
            raise TradingError(
                f"Failed to get positions: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def get_holdings(self) -> List[Dict[str, Any]]:
        """Get current holdings."""
        try:
            if not self.kite or not self._active_session:
                raise TradingError(
                    "Kite Connect not authenticated",
                    category=ErrorCategory.AUTHENTICATION,
                    severity=ErrorSeverity.HIGH
                )

            # Rate limiting
            await self._rate_limit_check("holdings")

            holdings = self.kite.holdings()
            return holdings

        except Exception as e:
            self.logger.error(f"Failed to get holdings: {e}")
            raise TradingError(
                f"Failed to get holdings: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    async def _rate_limit_check(self, operation: str):
        """Check and enforce rate limiting."""
        now = datetime.now()
        last_call = self._last_api_call.get(operation, datetime.min)

        # Ensure minimum interval between calls
        time_since_last = (now - last_call).total_seconds()
        if time_since_last < self._min_interval:
            await asyncio.sleep(self._min_interval - time_since_last)

        self._last_api_call[operation] = datetime.now()

    async def close(self):
        """Close Kite Connect service and cleanup resources."""
        try:
            self._running = False

            # Close WebSocket connections
            for connection_id in list(self._ws_connections.keys()):
                await self._close_websocket_connection(connection_id)

            # Wait for threads to finish
            for thread in self._ws_threads.values():
                if thread.is_alive():
                    thread.join(timeout=5)

            self.logger.info("Kite Connect service closed")

        except Exception as e:
            self.logger.error(f"Error closing Kite Connect service: {e}")

    async def _close_websocket_connection(self, connection_id: str):
        """Close WebSocket connection."""
        try:
            if connection_id in self._ws_connections:
                await self._ws_connections[connection_id].close()
                del self._ws_connections[connection_id]

            if connection_id in self._ws_threads:
                del self._ws_threads[connection_id]

        except Exception as e:
            self.logger.error(f"Error closing WebSocket connection {connection_id}: {e}")

    async def is_authenticated(self) -> bool:
        """Check if Kite Connect is authenticated."""
        return (
            self.kite is not None and
            self._active_session is not None and
            self._is_session_valid(self._active_session)
        )