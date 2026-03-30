"""Data store for paper trading accounts and trades."""

import logging
import asyncio
import json
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

    REQUIRED_TRADE_COLUMNS = {
        "trade_id",
        "account_id",
        "symbol",
        "trade_type",
        "quantity",
        "entry_price",
        "entry_timestamp",
        "strategy_rationale",
        "status",
    }
    CANONICAL_OPEN_STATUSES = (TradeStatus.OPEN.value,)
    CANONICAL_CLOSED_STATUSES = (TradeStatus.CLOSED.value, TradeStatus.STOPPED_OUT.value)
    VALID_TRADE_STATUSES = {
        TradeStatus.OPEN.value,
        TradeStatus.CLOSED.value,
        TradeStatus.STOPPED_OUT.value,
        TradeStatus.CANCELLED.value,
    }

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

            await db.execute("""
                CREATE TABLE IF NOT EXISTS manual_run_audit (
                    run_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    route_name TEXT NOT NULL,
                    status TEXT NOT NULL,
                    status_reason TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT NOT NULL,
                    duration_ms INTEGER NOT NULL,
                    dependency_state TEXT NOT NULL,
                    provider_metadata TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS automation_runs (
                    run_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    job_type TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    runtime_session_id TEXT,
                    status TEXT NOT NULL,
                    status_reason TEXT NOT NULL DEFAULT '',
                    block_reason TEXT NOT NULL DEFAULT '',
                    schedule_source TEXT NOT NULL DEFAULT 'manual',
                    trigger_reason TEXT NOT NULL DEFAULT '',
                    input_digest TEXT NOT NULL DEFAULT '',
                    provider_metadata TEXT NOT NULL DEFAULT '{}',
                    tool_trace TEXT NOT NULL DEFAULT '[]',
                    artifact_path TEXT,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    timeout_at TEXT,
                    duration_ms INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS automation_job_controls (
                    job_type TEXT PRIMARY KEY,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    schedule_minutes INTEGER NOT NULL DEFAULT 60,
                    last_run_at TEXT,
                    next_run_at TEXT,
                    paused_at TEXT,
                    pause_reason TEXT NOT NULL DEFAULT '',
                    updated_at TEXT NOT NULL
                )
            """)

            await db.execute("""
                CREATE TABLE IF NOT EXISTS automation_global_control (
                    control_key TEXT PRIMARY KEY,
                    control_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Check and migrate legacy schemas
            await self._migrate_legacy_schema(db)
            await self._normalize_trade_statuses(db)
            await self._validate_trade_schema_and_statuses(db)

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
                await cursor.close()
                column_names = [col[1] for col in columns]

                legacy_alias_columns = {"id", "side", "entry_date", "entry_reason", "strategy_tag", "exit_date"}
                requires_canonical_rebuild = bool(
                    legacy_alias_columns.intersection(column_names)
                    or (self.REQUIRED_TRADE_COLUMNS - set(column_names))
                )

                if requires_canonical_rebuild:
                    logger.info("Rebuilding legacy paper_trades table into canonical schema")
                    await self._rebuild_legacy_trades_table(db, set(column_names))
                    cursor = await db.execute("PRAGMA table_info(paper_trades)")
                    columns = await cursor.fetchall()
                    await cursor.close()
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

    @staticmethod
    def _legacy_column_expression(
        available_columns: set[str],
        *candidates: str,
        default_sql: str,
        lowercase: bool = False,
    ) -> str:
        expressions = [name for name in candidates if name in available_columns]
        if expressions:
            expression = "COALESCE(" + ", ".join(expressions) + f", {default_sql})"
        else:
            expression = default_sql
        if lowercase:
            return f"LOWER({expression})"
        return expression

    async def _rebuild_legacy_trades_table(self, db, available_columns: set[str]) -> None:
        """Upgrade legacy trade storage into the canonical paper_trades schema."""
        await db.execute("ALTER TABLE paper_trades RENAME TO paper_trades_legacy_backup")
        await db.execute("""
            CREATE TABLE paper_trades (
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

        trade_id_expr = self._legacy_column_expression(
            available_columns,
            "trade_id",
            "id",
            default_sql="'trade_legacy_' || lower(hex(randomblob(8)))",
        )
        account_id_expr = self._legacy_column_expression(
            available_columns,
            "account_id",
            default_sql="'paper_swing_main'",
        )
        trade_type_expr = self._legacy_column_expression(
            available_columns,
            "trade_type",
            "side",
            default_sql="'buy'",
            lowercase=True,
        )
        entry_timestamp_expr = self._legacy_column_expression(
            available_columns,
            "entry_timestamp",
            "entry_date",
            "created_at",
            default_sql="CURRENT_TIMESTAMP",
        )
        strategy_rationale_expr = self._legacy_column_expression(
            available_columns,
            "strategy_rationale",
            "entry_reason",
            "strategy_tag",
            default_sql="''",
        )
        exit_timestamp_expr = self._legacy_column_expression(
            available_columns,
            "exit_timestamp",
            "exit_date",
            default_sql="NULL",
        )
        status_expr = self._legacy_column_expression(
            available_columns,
            "status",
            default_sql="'open'",
            lowercase=True,
        )
        created_at_expr = self._legacy_column_expression(
            available_columns,
            "created_at",
            "entry_timestamp",
            "entry_date",
            default_sql="CURRENT_TIMESTAMP",
        )
        updated_at_expr = self._legacy_column_expression(
            available_columns,
            "updated_at",
            "created_at",
            "entry_timestamp",
            "entry_date",
            default_sql="CURRENT_TIMESTAMP",
        )
        claude_session_expr = self._legacy_column_expression(
            available_columns,
            "claude_session_id",
            default_sql="NULL",
        )
        exit_price_expr = self._legacy_column_expression(
            available_columns,
            "exit_price",
            default_sql="NULL",
        )
        realized_pnl_expr = self._legacy_column_expression(
            available_columns,
            "realized_pnl",
            default_sql="NULL",
        )
        unrealized_pnl_expr = self._legacy_column_expression(
            available_columns,
            "unrealized_pnl",
            default_sql="NULL",
        )
        stop_loss_expr = self._legacy_column_expression(
            available_columns,
            "stop_loss",
            default_sql="NULL",
        )
        target_price_expr = self._legacy_column_expression(
            available_columns,
            "target_price",
            default_sql="NULL",
        )

        await db.execute(
            f"""
            INSERT INTO paper_trades (
                trade_id, account_id, symbol, trade_type, quantity, entry_price,
                entry_timestamp, strategy_rationale, claude_session_id, exit_price,
                exit_timestamp, realized_pnl, unrealized_pnl, status, stop_loss,
                target_price, created_at, updated_at
            )
            SELECT
                {trade_id_expr},
                {account_id_expr},
                symbol,
                {trade_type_expr},
                quantity,
                entry_price,
                {entry_timestamp_expr},
                {strategy_rationale_expr},
                {claude_session_expr},
                {exit_price_expr},
                {exit_timestamp_expr},
                {realized_pnl_expr},
                {unrealized_pnl_expr},
                {status_expr},
                {stop_loss_expr},
                {target_price_expr},
                {created_at_expr},
                {updated_at_expr}
            FROM paper_trades_legacy_backup
            """
        )
        await db.execute("DROP TABLE paper_trades_legacy_backup")

    async def _normalize_trade_statuses(self, db) -> None:
        """Canonicalize legacy trade statuses to lowercase enum values."""
        try:
            cursor = await db.execute("SELECT DISTINCT status FROM paper_trades")
            statuses = await cursor.fetchall()
            await cursor.close()
        except Exception as exc:
            logger.warning("Unable to inspect trade statuses during startup migration: %s", exc)
            return

        for row in statuses:
            raw_status = str((row or [""])[0] or "").strip()
            if not raw_status:
                continue
            canonical = raw_status.lower()
            if raw_status == canonical:
                continue
            logger.info("Normalizing legacy paper trade status %s -> %s", raw_status, canonical)
            await db.execute(
                "UPDATE paper_trades SET status = ? WHERE status = ?",
                (canonical, raw_status),
            )

    async def _validate_trade_schema_and_statuses(self, db) -> None:
        """Fail loud when canonical trade storage is not decision-safe."""
        cursor = await db.execute("PRAGMA table_info(paper_trades)")
        columns = await cursor.fetchall()
        await cursor.close()
        column_names = {str(column[1]) for column in columns}
        missing_columns = sorted(self.REQUIRED_TRADE_COLUMNS - column_names)
        if missing_columns:
            raise RuntimeError(
                "paper_trades schema is missing required canonical columns: "
                + ", ".join(missing_columns)
            )

        cursor = await db.execute("SELECT DISTINCT LOWER(status) FROM paper_trades")
        statuses = {str((row or [""])[0] or "").strip() for row in await cursor.fetchall()}
        await cursor.close()
        unexpected = sorted(status for status in statuses if status and status not in self.VALID_TRADE_STATUSES)
        if unexpected:
            raise RuntimeError(
                "paper_trades contains unsupported status values after startup migration: "
                + ", ".join(unexpected)
            )

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

        try:
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_manual_run_audit_account_started
                ON manual_run_audit(account_id, started_at DESC)
            """)
        except Exception as e:
            logger.warning(f"Failed to create manual run audit index: {e}")

        try:
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_automation_runs_account_started
                ON automation_runs(account_id, started_at DESC)
            """)
        except Exception as e:
            logger.warning(f"Failed to create automation run history index: {e}")

        try:
            await db.execute("""
                CREATE INDEX IF NOT EXISTS idx_automation_runs_account_job_status
                ON automation_runs(account_id, job_type, status)
            """)
        except Exception as e:
            logger.warning(f"Failed to create automation run active index: {e}")

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
            "SELECT * FROM paper_trades WHERE account_id = ? AND LOWER(status) = ?",
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
                WHERE trade_id = ? AND account_id = ? AND LOWER(status) = ?
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
            WHERE account_id = ? AND LOWER(status) IN (?, ?) AND exit_timestamp >= ?
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
            WHERE account_id = ? AND LOWER(status) IN (?, ?)
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

    async def record_manual_run_audit(
        self,
        *,
        run_id: str,
        account_id: str,
        route_name: str,
        status: str,
        status_reason: str,
        started_at: str,
        completed_at: str,
        duration_ms: int,
        dependency_state: Dict[str, Any],
        provider_metadata: Dict[str, Any],
    ) -> None:
        """Persist audit metadata for explicit operator-triggered runs."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            cursor = await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO manual_run_audit (
                    run_id, account_id, route_name, status, status_reason,
                    started_at, completed_at, duration_ms, dependency_state,
                    provider_metadata, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    account_id,
                    route_name,
                    status,
                    status_reason,
                    started_at,
                    completed_at,
                    duration_ms,
                    json.dumps(dependency_state or {}),
                    json.dumps(provider_metadata or {}),
                    now,
                ),
            )
            await cursor.close()
            await self.db_connection.commit()

    async def get_manual_run_audit_entries(
        self,
        account_id: str,
        *,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Return recent manual-run audit entries for the account."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                """
                SELECT *
                FROM manual_run_audit
                WHERE account_id = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )
            rows = await cursor.fetchall()
            await cursor.close()

        entries: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            for field in ("dependency_state", "provider_metadata"):
                raw_value = item.get(field)
                if isinstance(raw_value, str) and raw_value.strip():
                    try:
                        item[field] = json.loads(raw_value)
                    except json.JSONDecodeError:
                        item[field] = {"raw": raw_value}
                elif raw_value is None:
                    item[field] = {}
            entries.append(item)
        return entries

    async def create_automation_run(self, entry: Dict[str, Any]) -> None:
        """Persist a new automation run record."""
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO automation_runs (
                    run_id, account_id, job_type, provider, runtime_session_id, status,
                    status_reason, block_reason, schedule_source, trigger_reason, input_digest,
                    provider_metadata, tool_trace, artifact_path, started_at, completed_at,
                    timeout_at, duration_ms, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["run_id"],
                    entry["account_id"],
                    entry["job_type"],
                    entry["provider"],
                    entry.get("runtime_session_id"),
                    entry["status"],
                    entry.get("status_reason", ""),
                    entry.get("block_reason", ""),
                    entry.get("schedule_source", "manual"),
                    entry.get("trigger_reason", ""),
                    entry.get("input_digest", ""),
                    json.dumps(entry.get("provider_metadata") or {}),
                    json.dumps(entry.get("tool_trace") or []),
                    entry.get("artifact_path"),
                    entry["started_at"],
                    entry.get("completed_at"),
                    entry.get("timeout_at"),
                    entry.get("duration_ms"),
                    entry["created_at"],
                    entry["updated_at"],
                ),
            )
            await self.db_connection.commit()

    async def update_automation_run(self, run_id: str, updates: Dict[str, Any]) -> None:
        """Update an existing automation run record."""
        allowed = {
            "runtime_session_id",
            "status",
            "status_reason",
            "block_reason",
            "provider_metadata",
            "tool_trace",
            "artifact_path",
            "completed_at",
            "timeout_at",
            "duration_ms",
            "updated_at",
        }
        columns = []
        params: List[Any] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            columns.append(f"{key} = ?")
            if key in {"provider_metadata", "tool_trace"}:
                params.append(json.dumps(value or ({} if key == "provider_metadata" else [])))
            else:
                params.append(value)
        if not columns:
            return
        params.append(run_id)
        async with self._lock:
            await self.db_connection.execute(
                f"UPDATE automation_runs SET {', '.join(columns)} WHERE run_id = ?",
                tuple(params),
            )
            await self.db_connection.commit()

    async def get_automation_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Return a single automation run record."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                "SELECT * FROM automation_runs WHERE run_id = ?",
                (run_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return self._decode_automation_run_row(dict(row))

    async def list_automation_runs(self, account_id: str, *, limit: int = 20) -> List[Dict[str, Any]]:
        """Return recent automation runs for the account."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                """
                SELECT *
                FROM automation_runs
                WHERE account_id = ?
                ORDER BY started_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [self._decode_automation_run_row(dict(row)) for row in rows]

    async def get_active_automation_run(self, account_id: str, job_type: str) -> Optional[Dict[str, Any]]:
        """Return an active queued/in-progress automation run if present."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                """
                SELECT *
                FROM automation_runs
                WHERE account_id = ? AND job_type = ? AND status IN ('queued', 'in_progress')
                ORDER BY started_at DESC
                LIMIT 1
                """,
                (account_id, job_type),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        return self._decode_automation_run_row(dict(row))

    async def set_automation_global_pause(self, paused: bool, *, reason: str = "") -> None:
        """Persist the global automation pause state."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO automation_global_control (control_key, control_value, updated_at)
                VALUES (?, ?, ?)
                """,
                ("global_pause", json.dumps({"paused": paused, "reason": reason}), now),
            )
            await self.db_connection.commit()

    async def get_automation_global_pause(self) -> Dict[str, Any]:
        """Return the global automation pause state."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                "SELECT control_value, updated_at FROM automation_global_control WHERE control_key = ?",
                ("global_pause",),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return {"paused": False, "reason": "", "updated_at": None}
        payload = json.loads(row["control_value"]) if row["control_value"] else {"paused": False, "reason": ""}
        payload["updated_at"] = row["updated_at"]
        return payload

    async def upsert_automation_job_control(self, entry: Dict[str, Any]) -> None:
        """Create or update per-job automation controls."""
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO automation_job_controls (
                    job_type, enabled, schedule_minutes, last_run_at, next_run_at,
                    paused_at, pause_reason, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["job_type"],
                    1 if entry.get("enabled", True) else 0,
                    int(entry.get("schedule_minutes", 60)),
                    entry.get("last_run_at"),
                    entry.get("next_run_at"),
                    entry.get("paused_at"),
                    entry.get("pause_reason", ""),
                    entry["updated_at"],
                ),
            )
            await self.db_connection.commit()

    async def get_automation_job_control(self, job_type: str) -> Optional[Dict[str, Any]]:
        """Return a single per-job automation control row."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                "SELECT * FROM automation_job_controls WHERE job_type = ?",
                (job_type,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        if not row:
            return None
        item = dict(row)
        item["enabled"] = bool(item.get("enabled", 1))
        return item

    async def list_automation_job_controls(self) -> List[Dict[str, Any]]:
        """Return all per-job automation controls."""
        async with self._lock:
            self.db_connection.row_factory = aiosqlite.Row
            cursor = await self.db_connection.execute(
                "SELECT * FROM automation_job_controls ORDER BY job_type ASC"
            )
            rows = await cursor.fetchall()
            await cursor.close()
        items: List[Dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["enabled"] = bool(item.get("enabled", 1))
            items.append(item)
        return items

    @staticmethod
    def _decode_automation_run_row(item: Dict[str, Any]) -> Dict[str, Any]:
        for field, fallback in (("provider_metadata", {}), ("tool_trace", [])):
            raw_value = item.get(field)
            if isinstance(raw_value, str) and raw_value.strip():
                try:
                    item[field] = json.loads(raw_value)
                except json.JSONDecodeError:
                    item[field] = fallback
            elif raw_value is None:
                item[field] = fallback
        return item

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
                WHERE account_id = ? AND LOWER(status) = ?
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
                  AND LOWER(status) IN (?, ?)
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
