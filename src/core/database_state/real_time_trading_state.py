"""
Real-time trading state management with async operations and proper locking.

This module manages the state for real-time trading operations including
market data, positions, orders, and Kite Connect sessions.
"""

import json
import sqlite3
import asyncio
from datetime import datetime, date
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict

from src.core.database_state.base_state import BaseState
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity


@dataclass
class RealTimeQuote:
    """Real-time market quote data."""
    symbol: str
    last_price: float
    change_price: float = 0.0
    change_percent: float = 0.0
    volume: int = 0
    timestamp: str = ""
    source: str = "kite"

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> 'RealTimeQuote':
        """Create RealTimeQuote from database row."""
        return cls(
            symbol=row['symbol'],
            last_price=row['last_price'],
            change_price=row['change_price'] or 0.0,
            change_percent=row['change_percent'] or 0.0,
            volume=row['volume'] or 0,
            timestamp=row['timestamp'],
            source=row['source'] or 'kite'
        )


@dataclass
class OrderBookEntry:
    """Order book entry for tracking orders."""
    order_id: str
    account_id: str
    symbol: str
    exchange: str = "NSE"
    order_type: str = "BUY"  # BUY or SELL
    product_type: str = "CNC"  # CNC, INTRADAY, CO, OCO
    quantity: int = 0
    price: Optional[float] = None
    trigger_price: Optional[float] = None
    status: str = "PENDING"  # PENDING, OPEN, COMPLETE, CANCELLED, REJECTED
    validity: str = "DAY"  # DAY, IOC
    variety: str = "regular"  # regular, amo, bo, co
    disclosed_quantity: int = 0
    filled_quantity: int = 0
    pending_quantity: int = 0
    cancelled_quantity: int = 0
    average_price: float = 0.0
    placed_at: str = ""
    updated_at: str = ""
    exchange_order_id: Optional[str] = None
    exchange_timestamp: Optional[str] = None
    exchange_update_timestamp: Optional[str] = None
    parent_order_id: Optional[str] = None
    order_guid: Optional[str] = None

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> 'OrderBookEntry':
        """Create OrderBookEntry from database row."""
        return cls(
            order_id=row['order_id'],
            account_id=row['account_id'],
            symbol=row['symbol'],
            exchange=row['exchange'] or 'NSE',
            order_type=row['order_type'],
            product_type=row['product_type'],
            quantity=row['quantity'],
            price=row['price'],
            trigger_price=row['trigger_price'],
            status=row['status'],
            validity=row['validity'] or 'DAY',
            variety=row['variety'] or 'regular',
            disclosed_quantity=row['disclosed_quantity'] or 0,
            filled_quantity=row['filled_quantity'] or 0,
            pending_quantity=row['pending_quantity'] or 0,
            cancelled_quantity=row['cancelled_quantity'] or 0,
            average_price=row['average_price'] or 0.0,
            placed_at=row['placed_at'],
            updated_at=row['updated_at'],
            exchange_order_id=row['exchange_order_id'],
            exchange_timestamp=row['exchange_timestamp'],
            exchange_update_timestamp=row['exchange_update_timestamp'],
            parent_order_id=row['parent_order_id'],
            order_guid=row['order_guid']
        )


@dataclass
class RealTimePosition:
    """Real-time position with P&L tracking."""
    account_id: str
    symbol: str
    exchange: str = "NSE"
    product_type: str = "CNC"
    quantity: int = 0
    buy_quantity: int = 0
    sell_quantity: int = 0
    buy_average_price: float = 0.0
    sell_average_price: float = 0.0
    last_price: float = 0.0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_pnl: float = 0.0
    pnl_percent: float = 0.0
    day_change_price: float = 0.0
    day_change_percent: float = 0.0
    value: float = 0.0
    investment: float = 0.0
    margin_used: float = 0.0
    span_margin: float = 0.0
    exposure_margin: float = 0.0
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> 'RealTimePosition':
        """Create RealTimePosition from database row."""
        return cls(
            account_id=row['account_id'],
            symbol=row['symbol'],
            exchange=row['exchange'] or 'NSE',
            product_type=row['product_type'],
            quantity=row['quantity'],
            buy_quantity=row['buy_quantity'] or 0,
            sell_quantity=row['sell_quantity'] or 0,
            buy_average_price=row['buy_average_price'] or 0.0,
            sell_average_price=row['sell_average_price'] or 0.0,
            last_price=row['last_price'] or 0.0,
            unrealized_pnl=row['unrealized_pnl'] or 0.0,
            realized_pnl=row['realized_pnl'] or 0.0,
            total_pnl=row['total_pnl'] or 0.0,
            pnl_percent=row['pnl_percent'] or 0.0,
            day_change_price=row['day_change_price'] or 0.0,
            day_change_percent=row['day_change_percent'] or 0.0,
            value=row['value'] or 0.0,
            investment=row['investment'] or 0.0,
            margin_used=row['margin_used'] or 0.0,
            span_margin=row['span_margin'] or 0.0,
            exposure_margin=row['exposure_margin'] or 0.0,
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )


@dataclass
class KiteSession:
    """Kite Connect session information."""
    account_id: str
    user_id: Optional[str] = None
    public_token: Optional[str] = None
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    enctoken: Optional[str] = None
    user_type: Optional[str] = None
    email: Optional[str] = None
    user_name: Optional[str] = None
    user_shortname: Optional[str] = None
    avatar_url: Optional[str] = None
    broker: str = "ZERODHA"
    products: Optional[str] = None
    exchanges: Optional[str] = None
    active: bool = True
    expires_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    last_used_at: str = ""

    @classmethod
    def from_db_row(cls, row: sqlite3.Row) -> 'KiteSession':
        """Create KiteSession from database row."""
        return cls(
            account_id=row['account_id'],
            user_id=row['user_id'],
            public_token=row['public_token'],
            access_token=row['access_token'],
            refresh_token=row['refresh_token'],
            enctoken=row['enctoken'],
            user_type=row['user_type'],
            email=row['email'],
            user_name=row['user_name'],
            user_shortname=row['user_shortname'],
            avatar_url=row['avatar_url'],
            broker=row['broker'] or 'ZERODHA',
            products=row['products'],
            exchanges=row['exchanges'],
            active=bool(row['active']),
            expires_at=row['expires_at'],
            created_at=row['created_at'],
            updated_at=row['updated_at'],
            last_used_at=row['last_used_at']
        )


class RealTimeTradingState(BaseState):
    """Real-time trading state management with async operations and locking."""

    def __init__(self, db_path: str):
        super().__init__(db_path)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize real-time trading tables."""
        async with self._lock:
            try:
                # Read and execute schema
                schema_path = "/Users/gurusharan/Documents/remote-claude/robo-trader/src/core/database_state/schemas/real_time_trading_schema.sql"
                async with self._aiofiles_open(schema_path, 'r') as f:
                    schema_sql = await f.read()

                # Execute schema
                await self._execute_schema(schema_sql)
                await self.db.commit()

                self.logger.info("Real-time trading state initialized successfully")

            except Exception as e:
                self.logger.error(f"Failed to initialize real-time trading state: {e}")
                raise TradingError(
                    f"Real-time trading state initialization failed: {e}",
                    category=ErrorCategory.DATABASE,
                    severity=ErrorSeverity.HIGH,
                    recoverable=False
                )

    # Market Data Operations
    async def store_real_time_quote(self, quote: RealTimeQuote) -> bool:
        """Store real-time quote data."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    INSERT OR REPLACE INTO real_time_quotes
                    (symbol, last_price, change_price, change_percent, volume, timestamp, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    quote.symbol,
                    quote.last_price,
                    quote.change_price,
                    quote.change_percent,
                    quote.volume,
                    quote.timestamp or datetime.utcnow().isoformat(),
                    quote.source
                ))
                await self.db.commit()
                return True

            except Exception as e:
                self.logger.error(f"Failed to store real-time quote for {quote.symbol}: {e}")
                return False

    async def get_latest_quote(self, symbol: str) -> Optional[RealTimeQuote]:
        """Get latest quote for a symbol."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    SELECT * FROM real_time_quotes
                    WHERE symbol = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                """, (symbol,))
                row = await cursor.fetchone()
                return RealTimeQuote.from_db_row(row) if row else None

            except Exception as e:
                self.logger.error(f"Failed to get latest quote for {symbol}: {e}")
                return None

    async def get_multiple_quotes(self, symbols: List[str]) -> Dict[str, RealTimeQuote]:
        """Get latest quotes for multiple symbols."""
        async with self._lock:
            try:
                if not symbols:
                    return {}

                placeholders = ','.join(['?' for _ in symbols])
                cursor = await self.db.connection.execute(f"""
                    SELECT * FROM real_time_quotes
                    WHERE symbol IN ({placeholders})
                    ORDER BY timestamp DESC
                """, symbols)
                rows = await cursor.fetchall()

                result = {}
                for row in rows:
                    quote = RealTimeQuote.from_db_row(row)
                    if quote.symbol not in result:  # Keep only the latest per symbol
                        result[quote.symbol] = quote
                return result

            except Exception as e:
                self.logger.error(f"Failed to get multiple quotes: {e}")
                return {}

    # Order Book Operations
    async def store_order(self, order: OrderBookEntry) -> bool:
        """Store order book entry."""
        async with self._lock:
            try:
                now = datetime.utcnow().isoformat()
                cursor = await self.db.connection.execute("""
                    INSERT OR REPLACE INTO order_book
                    (order_id, account_id, symbol, exchange, order_type, product_type,
                     quantity, price, trigger_price, status, validity, variety,
                     disclosed_quantity, filled_quantity, pending_quantity,
                     cancelled_quantity, average_price, placed_at, updated_at,
                     exchange_order_id, exchange_timestamp, exchange_update_timestamp,
                     parent_order_id, order_guid)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    order.order_id,
                    order.account_id,
                    order.symbol,
                    order.exchange,
                    order.order_type,
                    order.product_type,
                    order.quantity,
                    order.price,
                    order.trigger_price,
                    order.status,
                    order.validity,
                    order.variety,
                    order.disclosed_quantity,
                    order.filled_quantity,
                    order.pending_quantity,
                    order.cancelled_quantity,
                    order.average_price,
                    order.placed_at or now,
                    order.updated_at or now,
                    order.exchange_order_id,
                    order.exchange_timestamp,
                    order.exchange_update_timestamp,
                    order.parent_order_id,
                    order.order_guid
                ))
                await self.db.commit()
                return True

            except Exception as e:
                self.logger.error(f"Failed to store order {order.order_id}: {e}")
                return False

    async def get_orders_by_account(self, account_id: str, limit: int = 50) -> List[OrderBookEntry]:
        """Get orders for an account."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    SELECT * FROM order_book
                    WHERE account_id = ?
                    ORDER BY placed_at DESC
                    LIMIT ?
                """, (account_id, limit))
                rows = await cursor.fetchall()
                return [OrderBookEntry.from_db_row(row) for row in rows]

            except Exception as e:
                self.logger.error(f"Failed to get orders for account {account_id}: {e}")
                return []

    async def update_order_status(self, order_id: str, status: str,
                                filled_quantity: Optional[int] = None,
                                average_price: Optional[float] = None) -> bool:
        """Update order status and fill information."""
        async with self._lock:
            try:
                update_fields = ["status = ?", "updated_at = ?"]
                params = [status, datetime.utcnow().isoformat()]

                if filled_quantity is not None:
                    update_fields.append("filled_quantity = ?")
                    params.append(filled_quantity)

                if average_price is not None:
                    update_fields.append("average_price = ?")
                    params.append(average_price)

                params.append(order_id)

                cursor = await self.db.connection.execute(f"""
                    UPDATE order_book
                    SET {', '.join(update_fields)}
                    WHERE order_id = ?
                """, params)
                await self.db.commit()
                return cursor.rowcount > 0

            except Exception as e:
                self.logger.error(f"Failed to update order status for {order_id}: {e}")
                return False

    # Position Operations
    async def store_position(self, position: RealTimePosition) -> bool:
        """Store or update position."""
        async with self._lock:
            try:
                now = datetime.utcnow().isoformat()
                cursor = await self.db.connection.execute("""
                    INSERT OR REPLACE INTO real_time_positions
                    (account_id, symbol, exchange, product_type, quantity,
                     buy_quantity, sell_quantity, buy_average_price, sell_average_price,
                     last_price, unrealized_pnl, realized_pnl, total_pnl, pnl_percent,
                     day_change_price, day_change_percent, value, investment,
                     margin_used, span_margin, exposure_margin, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    position.account_id,
                    position.symbol,
                    position.exchange,
                    position.product_type,
                    position.quantity,
                    position.buy_quantity,
                    position.sell_quantity,
                    position.buy_average_price,
                    position.sell_average_price,
                    position.last_price,
                    position.unrealized_pnl,
                    position.realized_pnl,
                    position.total_pnl,
                    position.pnl_percent,
                    position.day_change_price,
                    position.day_change_percent,
                    position.value,
                    position.investment,
                    position.margin_used,
                    position.span_margin,
                    position.exposure_margin,
                    position.created_at or now,
                    position.updated_at or now
                ))
                await self.db.commit()
                return True

            except Exception as e:
                self.logger.error(f"Failed to store position for {position.symbol}: {e}")
                return False

    async def get_positions_by_account(self, account_id: str) -> List[RealTimePosition]:
        """Get all positions for an account."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    SELECT * FROM real_time_positions
                    WHERE account_id = ?
                    ORDER BY updated_at DESC
                """, (account_id,))
                rows = await cursor.fetchall()
                return [RealTimePosition.from_db_row(row) for row in rows]

            except Exception as e:
                self.logger.error(f"Failed to get positions for account {account_id}: {e}")
                return []

    async def update_position_prices(self, symbol: str, last_price: float) -> bool:
        """Update position prices for a symbol across all accounts."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    UPDATE real_time_positions
                    SET last_price = ?, updated_at = ?
                    WHERE symbol = ?
                """, (last_price, datetime.utcnow().isoformat(), symbol))
                await self.db.commit()
                return cursor.rowcount > 0

            except Exception as e:
                self.logger.error(f"Failed to update position prices for {symbol}: {e}")
                return False

    # Kite Session Operations
    async def store_kite_session(self, session: KiteSession) -> bool:
        """Store Kite Connect session."""
        async with self._lock:
            try:
                now = datetime.utcnow().isoformat()
                cursor = await self.db.connection.execute("""
                    INSERT OR REPLACE INTO kite_sessions
                    (account_id, user_id, public_token, access_token, refresh_token,
                     enctoken, user_type, email, user_name, user_shortname,
                     avatar_url, broker, products, exchanges, active, expires_at,
                     created_at, updated_at, last_used_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    session.account_id,
                    session.user_id,
                    session.public_token,
                    session.access_token,
                    session.refresh_token,
                    session.enctoken,
                    session.user_type,
                    session.email,
                    session.user_name,
                    session.user_shortname,
                    session.avatar_url,
                    session.broker,
                    session.products,
                    session.exchanges,
                    session.active,
                    session.expires_at,
                    session.created_at or now,
                    session.updated_at or now,
                    session.last_used_at or now
                ))
                await self.db.commit()
                return True

            except Exception as e:
                self.logger.error(f"Failed to store Kite session for {session.account_id}: {e}")
                return False

    async def get_active_kite_session(self, account_id: str) -> Optional[KiteSession]:
        """Get active Kite session for an account."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    SELECT * FROM kite_sessions
                    WHERE account_id = ? AND active = 1
                    ORDER BY last_used_at DESC
                    LIMIT 1
                """, (account_id,))
                row = await cursor.fetchone()
                return KiteSession.from_db_row(row) if row else None

            except Exception as e:
                self.logger.error(f"Failed to get Kite session for {account_id}: {e}")
                return None

    # Trade Execution Logs
    async def log_trade_execution(self, account_id: str, order_id: Optional[str],
                                symbol: str, action: str, request_data: Optional[str],
                                response_data: Optional[str], status: str,
                                error_message: Optional[str] = None,
                                execution_time_ms: Optional[int] = None) -> bool:
        """Log trade execution for audit trail."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    INSERT INTO trade_execution_logs
                    (account_id, order_id, symbol, action, request_data, response_data,
                     status, error_message, execution_time_ms, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id,
                    order_id,
                    symbol,
                    action,
                    request_data,
                    response_data,
                    status,
                    error_message,
                    execution_time_ms,
                    datetime.utcnow().isoformat()
                ))
                await self.db.commit()
                return True

            except Exception as e:
                self.logger.error(f"Failed to log trade execution: {e}")
                return False

    # Performance Metrics
    async def store_daily_performance(self, account_id: str, metrics: Dict[str, Any]) -> bool:
        """Store daily performance metrics."""
        async with self._lock:
            try:
                today = date.today().isoformat()
                cursor = await self.db.connection.execute("""
                    INSERT OR REPLACE INTO real_time_performance_metrics
                    (account_id, metric_date, total_value, cash_balance, invested_amount,
                     day_pnl, day_pnl_percent, total_pnl, total_pnl_percent,
                     max_drawdown, win_rate, total_trades, winning_trades, losing_trades,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account_id,
                    today,
                    metrics.get('total_value', 0),
                    metrics.get('cash_balance', 0),
                    metrics.get('invested_amount', 0),
                    metrics.get('day_pnl', 0),
                    metrics.get('day_pnl_percent', 0),
                    metrics.get('total_pnl', 0),
                    metrics.get('total_pnl_percent', 0),
                    metrics.get('max_drawdown', 0),
                    metrics.get('win_rate', 0),
                    metrics.get('total_trades', 0),
                    metrics.get('winning_trades', 0),
                    metrics.get('losing_trades', 0),
                    datetime.utcnow().isoformat(),
                    datetime.utcnow().isoformat()
                ))
                await self.db.commit()
                return True

            except Exception as e:
                self.logger.error(f"Failed to store daily performance for {account_id}: {e}")
                return False