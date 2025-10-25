"""Data store for paper trading accounts and trades."""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
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

    async def initialize(self) -> None:
        """Initialize the store."""
        await self.initialize_schema()

    async def initialize_schema(self) -> None:
        """Initialize database schema if it doesn't exist."""
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

        # Create trades table
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

        # Create indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_account_id
            ON paper_trades(account_id)
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_trades_symbol
            ON paper_trades(symbol)
        """)

        await db.commit()
        logger.info("Paper trading schema initialized in database")

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
        if not account_id:
            account_id = f"paper_{strategy_type.value}_{uuid.uuid4().hex[:8]}"
        now = datetime.utcnow().isoformat()
        today = datetime.utcnow().strftime("%Y-%m-%d")

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
        return await self.get_account(account_id)

    async def get_account(self, account_id: str) -> Optional[PaperTradingAccount]:
        """Get account by ID."""
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

    async def get_all_accounts(self) -> List[PaperTradingAccount]:
        """Get all paper trading accounts."""
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            "SELECT * FROM paper_trading_accounts ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [PaperTradingAccount.from_dict(dict(row)) for row in rows]

    async def update_account_balance(self, account_id: str, new_balance: float, buying_power: float) -> None:
        """Update account balance and buying power."""
        now = datetime.utcnow().isoformat()
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
        trade_id = f"trade_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()

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
        return await self.get_trade(trade_id)

    async def get_trade(self, trade_id: str) -> Optional[PaperTrade]:
        """Get trade by ID."""
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            "SELECT * FROM paper_trades WHERE trade_id = ?",
            (trade_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return PaperTrade.from_dict(dict(row))
        return None

    async def get_open_trades(self, account_id: str) -> List[PaperTrade]:
        """Get all open trades for account."""
        self.db_connection.row_factory = aiosqlite.Row
        cursor = await self.db_connection.execute(
            "SELECT * FROM paper_trades WHERE account_id = ? AND status = ?",
            (account_id, TradeStatus.OPEN.value)
        )
        rows = await cursor.fetchall()
        await cursor.close()
        return [PaperTrade.from_dict(dict(row)) for row in rows]

    async def close_trade(
        self,
        trade_id: str,
        exit_price: float,
        realized_pnl: float,
        reason: str = "Manual exit"
    ) -> Optional[PaperTrade]:
        """Close a trade."""
        now = datetime.utcnow().isoformat()

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

        return await self.get_trade(trade_id)

    async def mark_stopped_out(self, trade_id: str, exit_price: float, realized_pnl: float) -> Optional[PaperTrade]:
        """Mark trade as stopped out."""
        now = datetime.utcnow().isoformat()

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

        return await self.get_trade(trade_id)

    async def get_monthly_trades(self, account_id: str, year: int, month: int) -> List[PaperTrade]:
        """Get all trades for a specific month."""
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01"

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
        return [PaperTrade.from_dict(dict(row)) for row in rows]

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
        today = datetime.utcnow().strftime("%Y-%m-%d")
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

        today = datetime.utcnow().strftime("%Y-%m-%d")
        now = datetime.utcnow().isoformat()

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
            start_date = f"{year:04d}-{month:02d}-01"
            if month == 12:
                end_date = f"{year+1:04d}-01-01"
            else:
                end_date = f"{year:04d}-{month+1:02d}-01"
            query += " AND entry_timestamp >= ? AND entry_timestamp < ?"
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
        return [PaperTrade.from_dict(dict(row)) for row in rows]
