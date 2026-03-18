"""Data store for paper trading accounts and trades."""

import logging
import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any, Tuple
import aiosqlite

from ..models.paper_trading import (
    PaperTradingAccount, PaperTrade, TradeType, TradeStatus, AccountType, RiskLevel
)

logger = logging.getLogger(__name__)


class PaperTradingStore:
    """Async store for paper trading data."""

    def __init__(self, db_connection):
        """Initialize store with database connection."""
        self.db_connection = db_connection
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize the store."""
        await self.initialize_schema()

    async def initialize_schema(self) -> None:
        """Initialize database schema if it doesn't exist, with migrations for legacy schemas."""
        async with self._lock:
            # Use the database connection from state manager (direct connection, not pool)
            db = self.db_connection

            # Create accounts table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paper_trading_accounts (
                    account_id TEXT PRIMARY KEY,
                    account_name TEXT NOT NULL,
                    initial_balance REAL NOT NULL,
                    current_balance REAL NOT NULL,
                    buying_power REAL NOT NULL,
                    strategy_type TEXT NOT NULL,
                    risk_level TEXT NOT NULL,
                    max_position_size REAL NOT NULL,
                    max_portfolio_risk REAL NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    month_start_date TEXT NOT NULL,
                    monthly_pnl REAL DEFAULT 0.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Create trades table with current schema
            await db.execute("""
                CREATE TABLE IF NOT EXISTS paper_trades (
                    trade_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    trade_type TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    entry_timestamp TEXT NOT NULL,
                    strategy_rationale TEXT NOT NULL,
                    claude_session_id TEXT,
                    exit_price REAL,
                    exit_timestamp TEXT,
                    realized_pnl REAL,
                    unrealized_pnl REAL,
                    status TEXT NOT NULL DEFAULT 'open',
                    stop_loss REAL,
                    target_price REAL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Check and migrate legacy schemas
            await self._migrate_legacy_schema(db)

            # Create indexes (these will only succeed if columns exist)
            await self._create_indexes_safely(db)

            await db.commit()
            logger.info("Paper trading schema initialized and migrated in database")

    async def _migrate_legacy_schema(self, db) -> None:
        """Migrate legacy database schemas to current format."""
        try:
            # Check if paper_trades table exists and has the required columns
            cursor = await db.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='paper_trades'
            """)
            table_exists = await cursor.fetchone()

            if table_exists:
                # Check existing columns
                cursor = await db.execute("PRAGMA table_info(paper_trades)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

                # Migration for account_id column
                if 'account_id' not in column_names:
                    logger.info("Migrating paper_trades table: adding account_id column")
                    await db.execute("""
                        ALTER TABLE paper_trades
                        ADD COLUMN account_id TEXT NOT NULL DEFAULT 'paper_swing_main'
                    """)
                    logger.info("Added account_id column to paper_trades table")

                # Migration for exit_timestamp column
                if 'exit_timestamp' not in column_names:
                    logger.info("Migrating paper_trades table: adding exit_timestamp column")
                    await db.execute("""
                        ALTER TABLE paper_trades
                        ADD COLUMN exit_timestamp TEXT
                    """)
                    logger.info("Added exit_timestamp column to paper_trades table")

                # Migration for other missing columns that might be in legacy schemas
                required_columns = {
                    'realized_pnl': 'REAL DEFAULT 0.0',
                    'unrealized_pnl': 'REAL DEFAULT 0.0',
                    'status': 'TEXT NOT NULL DEFAULT "open"',
                    'stop_loss': 'REAL',
                    'target_price': 'REAL',
                    'claude_session_id': 'TEXT'
                }

                for column, definition in required_columns.items():
                    if column not in column_names:
                        logger.info(f"Migrating paper_trades table: adding {column} column")
                        await db.execute(f"""
                            ALTER TABLE paper_trades
                            ADD COLUMN {column} {definition}
                        """)
                        logger.info(f"Added {column} column to paper_trades table")

        except Exception as e:
            logger.warning(f"Schema migration failed (non-critical): {e}")
            # Continue anyway - the table might be fine or this might be a fresh install

    async def _create_indexes_safely(self, db) -> None:
        """Create indexes safely, handling cases where columns might not exist."""
        try:
            # Create account_id index (will fail gracefully if column doesn't exist)
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_account_id
                ON paper_trades(account_id)
            """)
        except Exception as e:
            logger.warning(f"Failed to create account_id index (column may not exist): {e}")

        try:
            # Create symbol index
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_trades_symbol
                ON paper_trades(symbol)
            """)
        except Exception as e:
            logger.warning(f"Failed to create symbol index: {e}")

    async def create_account(
        self,
        account_name: str,
        initial_balance: float,
        strategy_type: AccountType,
        risk_level: RiskLevel = RiskLevel.MODERATE,
        max_position_size: float = 5.0,
        max_portfolio_risk: float = 10.0,
        account_id: Optional[str] = None
    ) -> PaperTradingAccount:
        """Create new paper trading account."""
        async with self._lock:
            if not account_id:
                account_id = f"paper_{strategy_type.value}_{uuid.uuid4().hex[:8]}"
            now = datetime.now(timezone.utc).isoformat()
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            cursor = await self.db_connection.execute(
                """
                INSERT INTO paper_trading_accounts (
                    account_id, account_name, initial_balance, current_balance, buying_power,
                    strategy_type, risk_level, max_position_size, max_portfolio_risk,
                    is_active, month_start_date, monthly_pnl, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account_id, account_name, initial_balance, initial_balance, initial_balance,
                    strategy_type.value, risk_level.value, max_position_size, max_portfolio_risk,
                    1, today, 0.0, now, now
                )
            )
            await cursor.close()
            await self.db_connection.commit()

            logger.info(f"Created paper trading account: {account_id}")
            return await self._get_account_unlocked(account_id)

    async def _get_account_unlocked(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Get account by ID (assumes lock is already held)."""
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            "SELECT * FROM paper_trading_accounts WHERE account_id = ?",
            (account_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return PaperTradingAccount.from_dict(dict(row))
        return None

    async def get_account(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Get account by ID."""
        async with self._lock:
            return await self._get_account_unlocked(account_id)

    async def get_all_accounts(self) -> List[PaperTradingAccount]:
        """Get all paper trading accounts."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                "SELECT * FROM paper_trading_accounts ORDER BY created_at DESC"
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [PaperTradingAccount.from_dict(dict(row)) for row in rows]

    async def delete_account(self, account_id: str) -> bool:
        """
        Delete a paper trading account.

        Args:
            account_id: ID of the account to delete

        Returns:
            True if account was deleted, False if not found
        """
        async with self._lock:
            # First check if account exists
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                "SELECT account_id FROM paper_trading_accounts WHERE account_id = ?",
                (account_id,)
            )
            row = await cursor.fetchone()
            await cursor.close()

            if not row:
                return False

            # Delete the account
            await self.db_connection.execute(
                "DELETE FROM paper_trading_accounts WHERE account_id = ?",
                (account_id,)
            )
            await self.db_connection.commit()
            logger.info(f"Deleted paper trading account: {account_id}")
            return True

    async def update_account_balance(self, account_id: str, new_balance: float, buying_power: float) -> None:
        """Update account balance and buying power."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            cursor = await self.db_connection.execute(
                """
                UPDATE paper_trading_accounts
                SET current_balance = ?, buying_power = ?, updated_at = ?
                WHERE account_id = ?
                """,
                (new_balance, buying_power, now, account_id)
            )
            await cursor.close()
            await self.db_connection.commit()

    async def create_trade(
        self,
        account_id: str,
        symbol: str,
        trade_type: TradeType,
        quantity: int,
        entry_price: float,
        strategy_rationale: str,
        claude_session_id: str,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None
    ) -> PaperTrade:
        """Create new trade record."""
        async with self._lock:
            trade_id = f"trade_{uuid.uuid4().hex[:16]}"
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db_connection.execute(
                """
                INSERT INTO paper_trades (
                    trade_id, account_id, symbol, trade_type, quantity, entry_price,
                    entry_timestamp, strategy_rationale, claude_session_id, stop_loss,
                    target_price, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trade_id, account_id, symbol, trade_type.value, quantity, entry_price,
                    now, strategy_rationale, claude_session_id, stop_loss,
                    target_price, TradeStatus.OPEN.value, now, now
                )
            )
            await cursor.close()
            await self.db_connection.commit()

            logger.info(f"Created trade: {trade_id} ({symbol} {quantity}@{entry_price})")
            return await self._get_trade_unlocked(trade_id)

    async def _get_trade_unlocked(self, trade_id: str) -> Optional[PaperTrade]:
        """Get trade by ID (assumes lock is already held)."""
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            "SELECT * FROM paper_trades WHERE trade_id = ?",
            (trade_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return PaperTrade.from_dict(self._normalize_trade_row(dict(row)))
        return None

    async def get_trade(self, trade_id: str) -> Optional[PaperTrade]:
        """Get trade by ID."""
        async with self._lock:
            return await self._get_trade_unlocked(trade_id)

    async def get_open_trades(self, account_id: str) -> List[PaperTrade]:
        """Get all open trades for account."""
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            "SELECT * FROM paper_trades WHERE account_id = ? AND status = ?",
            (account_id, TradeStatus.OPEN.value)
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [PaperTrade.from_dict(self._normalize_trade_row(dict(row))) for row in rows]

    async def update_trade_risk_levels(
        self,
        account_id: str,
        trade_id: str,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None,
    ) -> Optional[PaperTrade]:
        """Update stop-loss and target-price values for an open trade."""
        async with self._lock:
            existing_trade = await self._get_trade_unlocked(trade_id)
            if existing_trade is None or existing_trade.account_id != account_id:
                return None

            if existing_trade.status != TradeStatus.OPEN:
                return None

            now = datetime.now(timezone.utc).isoformat()
            cursor = await self.db_connection.execute(
                """
                UPDATE paper_trades
                SET stop_loss = COALESCE(?, stop_loss),
                    target_price = COALESCE(?, target_price),
                    updated_at = ?
                WHERE trade_id = ? AND account_id = ? AND status = ?
                """,
                (
                    stop_loss,
                    target_price,
                    now,
                    trade_id,
                    account_id,
                    TradeStatus.OPEN.value,
                ),
            )
            await cursor.close()
            await self.db_connection.commit()
            return await self._get_trade_unlocked(trade_id)

    def _normalize_trade_row(self, row: dict) -> dict:
        """Map both current and legacy DB column names to the PaperTrade model."""
        return {
            'trade_id': row.get('trade_id') or row.get('id'),
            'account_id': row.get('account_id'),
            'symbol': row.get('symbol'),
            'trade_type': (row.get('trade_type') or row.get('side') or 'buy').lower(),
            'quantity': row.get('quantity'),
            'entry_price': row.get('entry_price'),
            'entry_timestamp': row.get('entry_timestamp') or row.get('entry_date') or row.get('created_at'),
            'strategy_rationale': row.get('strategy_rationale') or row.get('entry_reason') or row.get('strategy_tag') or '',
            'claude_session_id': row.get('claude_session_id') or '',
            'exit_price': row.get('exit_price'),
            'exit_timestamp': row.get('exit_timestamp') or row.get('exit_date'),
            'realized_pnl': row.get('realized_pnl'),
            'unrealized_pnl': row.get('unrealized_pnl'),
            'status': (row.get('status') or 'open').lower(),
            'stop_loss': row.get('stop_loss'),
            'target_price': row.get('target_price'),
            'created_at': row.get('created_at'),
            'updated_at': row.get('updated_at'),
        }

    @staticmethod
    def _get_period_bounds(start_day: str) -> Tuple[str, str]:
        """Return ISO timestamp bounds for a day."""
        start = datetime.fromisoformat(start_day)
        end = start + timedelta(days=1)
        return start.isoformat(), end.isoformat()

    @staticmethod
    def _get_month_bounds(year: int, month: int) -> Tuple[str, str]:
        """Return ISO timestamp bounds for a month."""
        start = datetime(year, month, 1)
        if month == 12:
            end = datetime(year + 1, 1, 1)
        else:
            end = datetime(year, month + 1, 1)
        return start.isoformat(), end.isoformat()

    @staticmethod
    def _calculate_realized_pnl(trade: PaperTrade) -> float:
        """Calculate realized P&L when it is not already persisted."""
        if trade.realized_pnl is not None:
            return trade.realized_pnl

        if trade.exit_price is None:
            return 0.0

        if trade.trade_type == TradeType.BUY:
            return (trade.exit_price - trade.entry_price) * trade.quantity

        return (trade.entry_price - trade.exit_price) * trade.quantity

    async def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        realized_pnl: float,
        reason: str = "Manual exit"
    ) -> Optional[PaperTrade]:
        """Close a trade."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db_connection.execute(
                """
                UPDATE paper_trades
                SET exit_price = ?, exit_timestamp = ?, realized_pnl = ?,
                    status = ?, updated_at = ?
                WHERE trade_id = ?
                """,
                (exit_price, now, realized_pnl, TradeStatus.CLOSED.value, now, trade_id)
            )
            await cursor.close()
            await self.db_connection.commit()

            return await self._get_trade_unlocked(trade_id)

    async def mark_stopped_out(self, trade_id: str, exit_price: float, realized_pnl: float) -> Optional[PaperTrade]:
        """Mark trade as stopped out."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            cursor = await self.db_connection.execute(
                """
                UPDATE paper_trades
                SET exit_price = ?, exit_timestamp = ?, realized_pnl = ?,
                    status = ?, updated_at = ?
                WHERE trade_id = ?
                """,
                (exit_price, now, realized_pnl, TradeStatus.STOPPED_OUT.value, now, trade_id)
            )
            await cursor.close()
            await self.db_connection.commit()

            return await self._get_trade_unlocked(trade_id)

    async def get_monthly_trades(self, account_id: str, year: int, month: int) -> List[PaperTrade]:
        """Get all trades for a specific month."""
        start_date, end_date = self._get_month_bounds(year, month)

        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            """
            SELECT * FROM paper_trades
            WHERE account_id = ? AND entry_timestamp >= ? AND entry_timestamp < ?
            ORDER BY entry_timestamp DESC
            """,
            (account_id, start_date, end_date)
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [PaperTrade.from_dict(self._normalize_trade_row(dict(row))) for row in rows]

    async def calculate_account_pnl(self, account_id: str, current_prices: Dict[str, float]) -> tuple[float, float]:
        """
        Calculate account P&L.

        Returns:
            (total_pnl, pnl_percentage)
        """
        account = await self.get_account(account_id)
        if not account:
            return 0.0, 0.0

        open_trades = await self.get_open_trades(account_id)
        unrealized_pnl = 0.0

        for trade in open_trades:
            if trade.symbol in current_prices:
                current_price = current_prices[trade.symbol]
                pnl, _ = trade.calculate_pnl(current_price)
                unrealized_pnl += pnl

        # Get realized PnL from closed trades
        realized_pnl = 0.0
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            """
            SELECT COALESCE(SUM(realized_pnl), 0) as total
            FROM paper_trades
            WHERE account_id = ? AND status IN (?, ?) AND exit_timestamp >= ?
            """,
            (account_id, TradeStatus.CLOSED.value, TradeStatus.STOPPED_OUT.value, today)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            realized_pnl = row['total']

        total_pnl = realized_pnl + unrealized_pnl
        initial = account.initial_balance
        pnl_pct = (total_pnl / initial) * 100 if initial > 0 else 0.0

        return total_pnl, pnl_pct

    async def reset_monthly_account(self, account_id: str) -> None:
        """Reset account for new month."""
        account = await self.get_account(account_id)
        if not account:
            return

        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        now = datetime.now(timezone.utc).isoformat()

        cursor = await self.db_connection.execute(
            """
            UPDATE paper_trading_accounts
            SET current_balance = ?, buying_power = ?, month_start_date = ?,
                monthly_pnl = 0.0, updated_at = ?
            WHERE account_id = ?
            """,
            (account.initial_balance, account.initial_balance, today, now, account_id)
        )
        await cursor.close()
        await self.db_connection.commit()

        logger.info(f"Reset monthly account: {account_id}")
    async def get_closed_trades(self, account_id: str, month: Optional[int] = None, year: Optional[int] = None, symbol: Optional[str] = None, limit: int = 50) -> List[PaperTrade]:
        """Get closed trades for account with optional filters."""
        query = """
            SELECT * FROM paper_trades
            WHERE account_id = ? AND status IN (?, ?)
        """
        params = [account_id, TradeStatus.CLOSED.value, TradeStatus.STOPPED_OUT.value]

        if month and year:
            start_date, end_date = self._get_month_bounds(year, month)
            query += " AND exit_timestamp >= ? AND exit_timestamp < ?"
            params.extend([start_date, end_date])

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        query += " ORDER BY exit_timestamp DESC LIMIT ?"
        params.append(limit)

        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [PaperTrade.from_dict(self._normalize_trade_row(dict(row))) for row in rows]

    async def calculate_daily_performance_metrics(
        self,
        account_id: str,
        review_date: str,
        current_prices: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Calculate truthful daily performance metrics from the store-backed authority path."""
        current_prices = current_prices or {}
        start_ts, end_ts = self._get_period_bounds(review_date)

        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row

            cursor = await self.db_connection.execute(
                """
                SELECT * FROM paper_trades
                WHERE account_id = ?
                  AND (
                    (entry_timestamp >= ? AND entry_timestamp < ?)
                    OR (exit_timestamp >= ? AND exit_timestamp < ?)
                  )
                ORDER BY COALESCE(exit_timestamp, entry_timestamp) DESC
                """,
                (account_id, start_ts, end_ts, start_ts, end_ts),
            )
            reviewed_rows = await cursor.fetchall()
            await cursor.close()

            trades_reviewed: List[Dict[str, Any]] = []
            strategy_performance: Dict[str, Dict[str, Any]] = {}
            realized_pnl = 0.0
            closed_positions_count = 0
            winning_trades = 0
            losing_trades = 0

            for row in reviewed_rows:
                trade = PaperTrade.from_dict(self._normalize_trade_row(dict(row)))
                realized = self._calculate_realized_pnl(trade)
                strategy_tag = trade.strategy_rationale or "unclassified"
                status_value = trade.status.value.upper()

                trades_reviewed.append({
                    "id": trade.trade_id,
                    "symbol": trade.symbol,
                    "side": trade.trade_type.value.upper(),
                    "quantity": trade.quantity,
                    "entry_price": trade.entry_price,
                    "exit_price": trade.exit_price,
                    "strategy_tag": strategy_tag,
                    "status": status_value,
                })

                metrics = strategy_performance.setdefault(
                    strategy_tag,
                    {"trades": 0, "winning_trades": 0, "total_pnl": 0.0},
                )
                metrics["trades"] += 1

                exit_ts = trade.exit_timestamp
                if exit_ts and start_ts <= exit_ts < end_ts and trade.status in {TradeStatus.CLOSED, TradeStatus.STOPPED_OUT}:
                    closed_positions_count += 1
                    realized_pnl += realized
                    metrics["total_pnl"] += realized
                    if realized > 0:
                        winning_trades += 1
                        metrics["winning_trades"] += 1
                    elif realized < 0:
                        losing_trades += 1

            cursor = await self.db_connection.execute(
                """
                SELECT * FROM paper_trades
                WHERE account_id = ? AND status = ?
                ORDER BY entry_timestamp DESC
                """,
                (account_id, TradeStatus.OPEN.value),
            )
            open_rows = await cursor.fetchall()
            await cursor.close()
            open_trades = [PaperTrade.from_dict(self._normalize_trade_row(dict(row))) for row in open_rows]

            unrealized_pnl = 0.0
            for trade in open_trades:
                current_price = current_prices.get(trade.symbol, trade.entry_price)
                trade_pnl, _ = trade.calculate_pnl(current_price)
                unrealized_pnl += trade_pnl

            account = await self._get_account_unlocked(account_id)
            initial_balance = account.initial_balance if account else 0.0
            daily_pnl = realized_pnl + unrealized_pnl
            daily_pnl_percent = (daily_pnl / initial_balance * 100) if initial_balance > 0 else 0.0

            for metrics in strategy_performance.values():
                trades = metrics["trades"]
                wins = metrics["winning_trades"]
                metrics["win_rate"] = (wins / trades * 100) if trades > 0 else 0.0

            total_closed_trades = winning_trades + losing_trades
            win_rate = (winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0.0

            return {
                "trades_reviewed": trades_reviewed,
                "daily_pnl": daily_pnl,
                "daily_pnl_percent": daily_pnl_percent,
                "realized_pnl": realized_pnl,
                "unrealized_pnl": unrealized_pnl,
                "open_positions_count": len(open_trades),
                "closed_positions_count": closed_positions_count,
                "win_rate": win_rate,
                "strategy_performance": strategy_performance,
                "winning_trades": winning_trades,
                "losing_trades": losing_trades,
            }

    async def calculate_monthly_pnl(self, account_id: str, year: int, month: int) -> Dict[str, Any]:
        """Calculate truthful monthly P&L summary from closed trades."""
        start_ts, end_ts = self._get_month_bounds(year, month)

        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                """
                SELECT * FROM paper_trades
                WHERE account_id = ?
                  AND status IN (?, ?)
                  AND exit_timestamp >= ?
                  AND exit_timestamp < ?
                ORDER BY exit_timestamp DESC
                """,
                (
                    account_id,
                    TradeStatus.CLOSED.value,
                    TradeStatus.STOPPED_OUT.value,
                    start_ts,
                    end_ts,
                ),
            )
            rows = await cursor.fetchall()
            await cursor.close()

            trades = [PaperTrade.from_dict(self._normalize_trade_row(dict(row))) for row in rows]
            strategy_breakdown: Dict[str, Dict[str, Any]] = {}
            total_pnl = 0.0
            winning_trades = 0
            best_trade = 0.0
            worst_trade = 0.0

            for trade in trades:
                realized = self._calculate_realized_pnl(trade)
                total_pnl += realized
                if realized > 0:
                    winning_trades += 1
                    best_trade = max(best_trade, realized)
                else:
                    worst_trade = min(worst_trade, realized)

                strategy_tag = trade.strategy_rationale or "unclassified"
                strategy_metrics = strategy_breakdown.setdefault(
                    strategy_tag,
                    {"name": strategy_tag, "pnl": 0.0, "trades": 0, "winning_trades": 0},
                )
                strategy_metrics["pnl"] += realized
                strategy_metrics["trades"] += 1
                if realized > 0:
                    strategy_metrics["winning_trades"] += 1

            top_strategies = sorted(
                [
                    {
                        "name": name,
                        "pnl": metrics["pnl"],
                        "trades": metrics["trades"],
                        "win_rate": (metrics["winning_trades"] / metrics["trades"] * 100) if metrics["trades"] else 0.0,
                    }
                    for name, metrics in strategy_breakdown.items()
                ],
                key=lambda item: item["pnl"],
                reverse=True,
            )

            total_trades = len(trades)
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

            return {
                "account_id": account_id,
                "year": year,
                "month": month,
                "total_pnl": total_pnl,
                "win_rate": win_rate,
                "total_trades": total_trades,
                "winning_trades": winning_trades,
                "best_trade": best_trade if total_trades else 0.0,
                "worst_trade": worst_trade if total_trades else 0.0,
                "top_strategies": top_strategies,
                "strategy_breakdown": strategy_breakdown,
            }
