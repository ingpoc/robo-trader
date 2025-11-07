"""
Paper Trading State Management.

Manages all paper trading workflow data with proper locking.
Completely separate from portfolio analysis workflow.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.database_state.base import BaseState


class PaperTradingState(BaseState):
    """
    Manages paper trading workflow data.

    Handles:
    - Paper trades and positions
    - Market research from Perplexity API
    - Strategy performance tracking
    - Monthly P&L calculations
    - Trading strategy evolution
    """

    def __init__(self, db_connection):
        super().__init__(db_connection)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize paper trading tables."""
        async with self._lock:
            schema = """
            -- Paper Trading Account
            CREATE TABLE IF NOT EXISTS paper_trading_account (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                initial_capital REAL NOT NULL DEFAULT 1000000.0,
                current_cash REAL NOT NULL DEFAULT 1000000.0,
                total_equity REAL NOT NULL DEFAULT 1000000.0,
                margin_used REAL DEFAULT 0.0,
                day_pnl REAL DEFAULT 0.0,
                total_pnl REAL DEFAULT 0.0,
                last_updated TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            -- Paper Trades
            CREATE TABLE IF NOT EXISTS paper_trades (
                id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                side TEXT NOT NULL CHECK (side IN ('BUY', 'SELL')),
                quantity INTEGER NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL,
                entry_date TEXT NOT NULL,
                exit_date TEXT,
                status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'CLOSED', 'CANCELLED')),
                entry_reason TEXT NOT NULL,
                exit_reason TEXT,
                strategy_tag TEXT NOT NULL,
                confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
                research_sources TEXT,  -- JSON array of research sources
                market_conditions TEXT,  -- JSON blob
                risk_metrics TEXT,  -- JSON blob
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Paper Positions
            CREATE TABLE IF NOT EXISTS paper_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL UNIQUE,
                quantity INTEGER NOT NULL DEFAULT 0,
                avg_cost_price REAL NOT NULL DEFAULT 0.0,
                current_price REAL NOT NULL DEFAULT 0.0,
                unrealized_pnl REAL DEFAULT 0.0,
                unrealized_pnl_percent REAL DEFAULT 0.0,
                day_change REAL DEFAULT 0.0,
                day_change_percent REAL DEFAULT 0.0,
                last_price_update TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Market Research Log
            CREATE TABLE IF NOT EXISTS market_research_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                research_date TEXT NOT NULL,
                symbol TEXT NOT NULL,
                research_type TEXT NOT NULL,  -- 'perplexity_research', 'technical_analysis', 'fundamental_check'
                research_query TEXT NOT NULL,
                research_response TEXT NOT NULL,  -- JSON blob with structured response
                sources_used TEXT,  -- JSON array of sources
                confidence_level REAL,
                actionable_insights TEXT,  -- JSON array
                research_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(research_date, symbol, research_type, research_query)
            );

            -- Strategy Performance Tracking
            CREATE TABLE IF NOT EXISTS strategy_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_tag TEXT NOT NULL,
                performance_date TEXT NOT NULL,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                losing_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                total_pnl REAL DEFAULT 0.0,
                avg_win REAL DEFAULT 0.0,
                avg_loss REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                max_drawdown REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                effectiveness_score REAL DEFAULT 0.0,  -- 0-100 calculated score
                recommendation TEXT,  -- 'increase_use', 'maintain_use', 'modify_parameters', 'reduce_use', 'retire'
                created_at TEXT NOT NULL,
                UNIQUE(strategy_tag, performance_date)
            );

            -- Monthly P&L Summary
            CREATE TABLE IF NOT EXISTS monthly_pnl_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year INTEGER NOT NULL,
                month INTEGER NOT NULL CHECK (month >= 1 AND month <= 12),
                opening_equity REAL NOT NULL,
                closing_equity REAL NOT NULL,
                monthly_pnl REAL NOT NULL,
                monthly_pnl_percent REAL NOT NULL,
                max_drawdown REAL DEFAULT 0.0,
                total_trades INTEGER DEFAULT 0,
                winning_trades INTEGER DEFAULT 0,
                best_trade REAL DEFAULT 0.0,
                worst_trade REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,
                strategy_breakdown TEXT,  -- JSON blob with P&L by strategy
                monthly_insights TEXT,  -- JSON blob with key insights
                created_at TEXT NOT NULL,
                UNIQUE(year, month)
            );

            -- Trading Strategy Evolution
            CREATE TABLE IF NOT EXISTS strategy_evolution (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                strategy_tag TEXT NOT NULL,
                evolution_date TEXT NOT NULL,
                evolution_type TEXT NOT NULL,  -- 'parameter_tuning', 'rule_addition', 'rule_removal', 'strategy_merge'
                old_parameters TEXT,  -- JSON blob
                new_parameters TEXT,  -- JSON blob
                performance_before REAL DEFAULT 0.0,
                performance_after REAL DEFAULT 0.0,
                improvement_reason TEXT NOT NULL,
                test_period_days INTEGER DEFAULT 30,
                created_at TEXT NOT NULL
            );

            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_paper_trades_symbol ON paper_trades(symbol);
            CREATE INDEX IF NOT EXISTS idx_paper_trades_status ON paper_trades(status);
            CREATE INDEX IF NOT EXISTS idx_paper_trades_strategy ON paper_trades(strategy_tag);
            CREATE INDEX IF NOT EXISTS idx_paper_trades_entry_date ON paper_trades(entry_date DESC);
            CREATE INDEX IF NOT EXISTS idx_paper_positions_symbol ON paper_positions(symbol);
            CREATE INDEX IF NOT EXISTS idx_research_log_symbol ON market_research_log(symbol);
            CREATE INDEX IF NOT EXISTS idx_research_log_date ON market_research_log(research_date DESC);
            CREATE INDEX IF NOT EXISTS idx_strategy_performance_tag ON strategy_performance(strategy_tag);
            CREATE INDEX IF NOT EXISTS idx_strategy_performance_date ON strategy_performance(performance_date DESC);
            CREATE INDEX IF NOT EXISTS idx_monthly_pnl_date ON monthly_pnl_summary(year DESC, month DESC);
            CREATE INDEX IF NOT EXISTS idx_evolution_strategy ON strategy_evolution(strategy_tag);
            CREATE INDEX IF NOT EXISTS idx_evolution_date ON strategy_evolution(evolution_date DESC);
            """

            try:
                await self.db.connection.executescript(schema)
                await self.db.connection.commit()
                logger.info("Paper trading tables initialized successfully")

                # Initialize paper trading account
                await self._initialize_paper_account()

            except Exception as e:
                logger.error(f"Failed to initialize paper trading tables: {e}")
                raise

    async def _initialize_paper_account(self) -> None:
        """Initialize paper trading account with default capital."""
        # Check if account already exists
        cursor = await self.db.connection.execute(
            "SELECT id FROM paper_trading_account WHERE id = 1"
        )
        if not await cursor.fetchone():
            current_time = datetime.now(timezone.utc).isoformat()

            await self.db.connection.execute(
                """INSERT INTO paper_trading_account
                   (id, initial_capital, current_cash, total_equity, last_updated, created_at)
                   VALUES (1, ?, ?, ?, ?, ?)""",
                (1000000.0, 1000000.0, 1000000.0, current_time, current_time)
            )

            await self.db.connection.commit()
            logger.info("Paper trading account initialized with ₹10,00,000 capital")

    # ===== Account Operations =====
    async def get_account(self) -> Optional[Dict[str, Any]]:
        """Get paper trading account information."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT initial_capital, current_cash, total_equity, margin_used,
                          day_pnl, total_pnl, last_updated, created_at
                       FROM paper_trading_account
                       WHERE id = 1"""
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "initial_capital": row[0],
                        "current_cash": row[1],
                        "total_equity": row[2],
                        "margin_used": row[3],
                        "day_pnl": row[4],
                        "total_pnl": row[5],
                        "last_updated": row[6],
                        "created_at": row[7],
                        "total_return_percent": ((row[2] - row[0]) / row[0]) * 100 if row[0] > 0 else 0
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get paper trading account: {e}")
                return None

    async def update_account(self, cash_change: float, equity_change: float) -> bool:
        """Update paper trading account balances."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """UPDATE paper_trading_account
                       SET current_cash = current_cash + ?,
                           total_equity = total_equity + ?,
                           last_updated = ?
                       WHERE id = 1""",
                    (cash_change, equity_change, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to update paper trading account: {e}")
                return False

    # ===== Trade Operations =====
    async def create_trade(self, trade_id: str, symbol: str, side: str, quantity: int,
                          entry_price: float, entry_reason: str, strategy_tag: str,
                          confidence_score: float, research_sources: List[str],
                          market_conditions: Dict[str, Any], risk_metrics: Dict[str, Any]) -> bool:
        """Create a new paper trade."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()
                entry_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                await self.db.connection.execute(
                    """INSERT INTO paper_trades
                       (id, symbol, side, quantity, entry_price, entry_date, entry_reason,
                        strategy_tag, confidence_score, research_sources, market_conditions,
                        risk_metrics, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (trade_id, symbol, side, quantity, entry_price, entry_date, entry_reason,
                     strategy_tag, confidence_score, json.dumps(research_sources),
                     json.dumps(market_conditions), json.dumps(risk_metrics),
                     current_time, current_time)
                )

                await self.db.connection.commit()

                # Update position
                await self._update_position(symbol, quantity, entry_price, side)

                return True

            except Exception as e:
                logger.error(f"Failed to create paper trade {trade_id}: {e}")
                return False

    async def close_trade(self, trade_id: str, exit_price: float, exit_reason: str) -> bool:
        """Close an existing paper trade."""
        async with self._lock:
            try:
                # Get trade details
                cursor = await self.db.connection.execute(
                    "SELECT symbol, quantity, side FROM paper_trades WHERE id = ? AND status = 'OPEN'",
                    (trade_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    logger.warning(f"Trade {trade_id} not found or already closed")
                    return False

                symbol, quantity, side = row
                current_time = datetime.now(timezone.utc).isoformat()
                exit_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                # Update trade
                await self.db.connection.execute(
                    """UPDATE paper_trades
                       SET exit_price = ?, exit_date = ?, exit_reason = ?, status = 'CLOSED',
                           updated_at = ?
                       WHERE id = ?""",
                    (exit_price, exit_date, exit_reason, current_time, trade_id)
                )

                # Update position (reverse of entry)
                position_quantity = -quantity if side == 'BUY' else quantity
                await self._update_position(symbol, position_quantity, exit_price, 'SELL' if side == 'BUY' else 'BUY')

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to close paper trade {trade_id}: {e}")
                return False

    async def get_open_trades(self) -> List[Dict[str, Any]]:
        """Get all open paper trades."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, symbol, side, quantity, entry_price, entry_date,
                          entry_reason, strategy_tag, confidence_score, research_sources,
                          market_conditions, risk_metrics, created_at
                       FROM paper_trades
                       WHERE status = 'OPEN'
                       ORDER BY entry_date DESC"""
                )
                rows = await cursor.fetchall()

                trades = []
                for row in rows:
                    trades.append({
                        "id": row[0],
                        "symbol": row[1],
                        "side": row[2],
                        "quantity": row[3],
                        "entry_price": row[4],
                        "entry_date": row[5],
                        "entry_reason": row[6],
                        "strategy_tag": row[7],
                        "confidence_score": row[8],
                        "research_sources": json.loads(row[9]) if row[9] else [],
                        "market_conditions": json.loads(row[10]) if row[10] else {},
                        "risk_metrics": json.loads(row[11]) if row[11] else {},
                        "created_at": row[12]
                    })
                return trades

            except Exception as e:
                logger.error(f"Failed to get open paper trades: {e}")
                return []

    async def _update_position(self, symbol: str, quantity: int, price: float, side: str) -> None:
        """Update paper position after trade."""
        # Get current position
        cursor = await self.db.connection.execute(
            "SELECT quantity, avg_cost_price FROM paper_positions WHERE symbol = ?",
            (symbol,)
        )
        row = await cursor.fetchone()

        current_time = datetime.now(timezone.utc).isoformat()

        if row:
            current_qty, avg_cost = row
            new_qty = current_qty + quantity

            if new_qty == 0:
                # Position closed
                await self.db.connection.execute(
                    "DELETE FROM paper_positions WHERE symbol = ?",
                    (symbol,)
                )
            else:
                # Update average cost price
                if side == 'BUY':
                    new_avg_cost = ((current_qty * avg_cost) + (quantity * price)) / new_qty
                else:
                    new_avg_cost = avg_cost  # Keep same average cost for sells

                await self.db.connection.execute(
                    """UPDATE paper_positions
                       SET quantity = ?, avg_cost_price = ?, current_price = ?,
                           updated_at = ?
                       WHERE symbol = ?""",
                    (new_qty, new_avg_cost, price, current_time, symbol)
                )
        else:
            # New position
            if quantity != 0:
                await self.db.connection.execute(
                    """INSERT INTO paper_positions
                       (symbol, quantity, avg_cost_price, current_price,
                        last_price_update, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, quantity, price, price, current_time, current_time, current_time)
                )

    # ===== Research Operations =====
    async def store_research(self, symbol: str, research_type: str, query: str,
                           response: Dict[str, Any], sources_used: List[str],
                           confidence_level: float, actionable_insights: List[str]) -> bool:
        """Store market research from Perplexity or other sources."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()
                research_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
                research_timestamp = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """INSERT OR REPLACE INTO market_research_log
                       (research_date, symbol, research_type, research_query,
                        research_response, sources_used, confidence_level,
                        actionable_insights, research_timestamp, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (research_date, symbol, research_type, query,
                     json.dumps(response), json.dumps(sources_used), confidence_level,
                     json.dumps(actionable_insights), research_timestamp, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store research for {symbol}: {e}")
                return False

    async def get_research_history(self, symbol: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get research history for a symbol."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT research_type, research_query, research_response,
                          sources_used, confidence_level, actionable_insights,
                          research_timestamp, created_at
                       FROM market_research_log
                       WHERE symbol = ? AND research_date >= date('now', '-{} days')
                       ORDER BY research_timestamp DESC
                    """.format(days_back),
                    (symbol,)
                )
                rows = await cursor.fetchall()

                research = []
                for row in rows:
                    research.append({
                        "research_type": row[0],
                        "research_query": row[1],
                        "research_response": json.loads(row[2]) if row[2] else {},
                        "sources_used": json.loads(row[3]) if row[3] else [],
                        "confidence_level": row[4],
                        "actionable_insights": json.loads(row[5]) if row[5] else [],
                        "research_timestamp": row[6],
                        "created_at": row[7]
                    })
                return research

            except Exception as e:
                logger.error(f"Failed to get research history for {symbol}: {e}")
                return []

    # ===== Strategy Performance Operations =====
    async def update_strategy_performance(self, strategy_tag: str, trade_pnl: float) -> None:
        """Update strategy performance after a trade closes."""
        async with self._lock:
            try:
                performance_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                # Get current performance
                cursor = await self.db.connection.execute(
                    """SELECT total_trades, winning_trades, losing_trades,
                          total_pnl, avg_win, avg_loss
                       FROM strategy_performance
                       WHERE strategy_tag = ? AND performance_date = ?""",
                    (strategy_tag, performance_date)
                )
                row = await cursor.fetchone()

                if row:
                    # Update existing record
                    total_trades, winning_trades, losing_trades, total_pnl, avg_win, avg_loss = row

                    new_total_trades = total_trades + 1
                    new_winning_trades = winning_trades + (1 if trade_pnl > 0 else 0)
                    new_losing_trades = losing_trades + (1 if trade_pnl < 0 else 0)
                    new_total_pnl = total_pnl + trade_pnl

                    # Update averages
                    if trade_pnl > 0:
                        new_avg_win = ((avg_win * winning_trades) + trade_pnl) / new_winning_trades if new_winning_trades > 0 else trade_pnl
                    else:
                        new_avg_win = avg_win

                    if trade_pnl < 0:
                        new_avg_loss = ((avg_loss * losing_trades) + abs(trade_pnl)) / new_losing_trades if new_losing_trades > 0 else abs(trade_pnl)
                    else:
                        new_avg_loss = avg_loss

                    # Calculate metrics
                    win_rate = (new_winning_trades / new_total_trades) * 100 if new_total_trades > 0 else 0
                    profit_factor = (new_avg_win * new_winning_trades) / (abs(new_avg_loss) * new_losing_trades) if new_losing_trades > 0 else 0

                    # Calculate effectiveness score (0-100)
                    effectiveness_score = min(100, (win_rate * 0.4) + (min(profit_factor, 3) / 3 * 30) + (min(new_total_pnl / 1000, 50) / 50 * 30))

                    # Generate recommendation
                    if effectiveness_score >= 80:
                        recommendation = "increase_use"
                    elif effectiveness_score >= 60:
                        recommendation = "maintain_use"
                    elif effectiveness_score >= 40:
                        recommendation = "modify_parameters"
                    else:
                        recommendation = "reduce_use"

                    await self.db.connection.execute(
                        """UPDATE strategy_performance
                           SET total_trades = ?, winning_trades = ?, losing_trades = ?,
                               win_rate = ?, total_pnl = ?, avg_win = ?, avg_loss = ?,
                               profit_factor = ?, effectiveness_score = ?, recommendation = ?
                           WHERE strategy_tag = ? AND performance_date = ?""",
                        (new_total_trades, new_winning_trades, new_losing_trades,
                         win_rate, new_total_pnl, new_avg_win, new_avg_loss,
                         profit_factor, effectiveness_score, recommendation,
                         strategy_tag, performance_date)
                    )
                else:
                    # Create new record
                    winning_trades = 1 if trade_pnl > 0 else 0
                    losing_trades = 1 if trade_pnl < 0 else 0
                    win_rate = 100 if trade_pnl > 0 else 0
                    avg_win = trade_pnl if trade_pnl > 0 else 0
                    avg_loss = abs(trade_pnl) if trade_pnl < 0 else 0
                    profit_factor = float('inf') if trade_pnl > 0 and losing_trades == 0 else 0
                    effectiveness_score = 100 if trade_pnl > 0 else 0
                    recommendation = "increase_use" if trade_pnl > 0 else "reduce_use"

                    await self.db.connection.execute(
                        """INSERT INTO strategy_performance
                           (strategy_tag, performance_date, total_trades, winning_trades,
                            losing_trades, win_rate, total_pnl, avg_win, avg_loss,
                            profit_factor, effectiveness_score, recommendation, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (strategy_tag, performance_date, 1, winning_trades, losing_trades,
                         win_rate, trade_pnl, avg_win, avg_loss, profit_factor,
                         effectiveness_score, recommendation, datetime.now(timezone.utc).isoformat())
                    )

                await self.db.connection.commit()

            except Exception as e:
                logger.error(f"Failed to update strategy performance for {strategy_tag}: {e}")

    async def get_strategy_performance(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get strategy performance data."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT strategy_tag, performance_date, total_trades, winning_trades,
                          losing_trades, win_rate, total_pnl, avg_win, avg_loss,
                          profit_factor, effectiveness_score, recommendation
                       FROM strategy_performance
                       WHERE performance_date >= date('now', '-{} days')
                       ORDER BY performance_date DESC, effectiveness_score DESC
                    """.format(days_back)
                )
                rows = await cursor.fetchall()

                performance = []
                for row in rows:
                    performance.append({
                        "strategy_tag": row[0],
                        "performance_date": row[1],
                        "total_trades": row[2],
                        "winning_trades": row[3],
                        "losing_trades": row[4],
                        "win_rate": row[5],
                        "total_pnl": row[6],
                        "avg_win": row[7],
                        "avg_loss": row[8],
                        "profit_factor": row[9],
                        "effectiveness_score": row[10],
                        "recommendation": row[11]
                    })
                return performance

            except Exception as e:
                logger.error(f"Failed to get strategy performance: {e}")
                return []

    # ===== Monthly P&L Operations =====
    async def calculate_monthly_pnl(self, year: int, month: int) -> Dict[str, Any]:
        """Calculate monthly P&L summary."""
        async with self._lock:
            try:
                # Get account at start and end of month
                start_date = f"{year}-{month:02d}-01"
                if month == 12:
                    end_date = f"{year+1}-01-01"
                else:
                    end_date = f"{year}-{month+1:02d}-01"

                # Get all trades in the month
                cursor = await self.db.connection.execute(
                    """SELECT entry_price, exit_price, quantity, side, strategy_tag
                       FROM paper_trades
                       WHERE entry_date >= ? AND entry_date < ?
                       OR (exit_date >= ? AND exit_date < ?)""",
                    (start_date, end_date, start_date, end_date)
                )
                rows = await cursor.fetchall()

                monthly_pnl = 0.0
                total_trades = len(rows)
                winning_trades = 0
                best_trade = 0.0
                worst_trade = 0.0
                strategy_breakdown = {}

                for row in rows:
                    entry_price, exit_price, quantity, side, strategy_tag = row

                    if exit_price is not None:  # Trade closed in period
                        if side == 'BUY':
                            trade_pnl = (exit_price - entry_price) * quantity
                        else:
                            trade_pnl = (entry_price - exit_price) * quantity

                        monthly_pnl += trade_pnl

                        if trade_pnl > 0:
                            winning_trades += 1
                            best_trade = max(best_trade, trade_pnl)
                        else:
                            worst_trade = min(worst_trade, trade_pnl)

                        # Track by strategy
                        if strategy_tag not in strategy_breakdown:
                            strategy_breakdown[strategy_tag] = 0.0
                        strategy_breakdown[strategy_tag] += trade_pnl

                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

                # Get opening and closing equity
                cursor = await self.db.connection.execute(
                    """SELECT total_equity FROM paper_trading_account
                       ORDER BY last_updated ASC LIMIT 1"""
                )
                opening_equity = (await cursor.fetchone())[0] if await cursor.fetchone() else 1000000.0

                cursor = await self.db.connection.execute(
                    """SELECT total_equity FROM paper_trading_account
                       ORDER BY last_updated DESC LIMIT 1"""
                )
                row = await cursor.fetchone()
                closing_equity = row[0] if row else opening_equity

                monthly_pnl_percent = ((closing_equity - opening_equity) / opening_equity) * 100 if opening_equity > 0 else 0

                # Generate insights
                insights = []
                if win_rate > 70:
                    insights.append("High win rate indicates effective strategy selection")
                elif win_rate < 40:
                    insights.append("Low win rate suggests strategy review needed")

                if monthly_pnl > 0:
                    insights.append("Profitable month - consider increasing position sizes")
                else:
                    insights.append("Loss-making month - review risk management")

                summary = {
                    "year": year,
                    "month": month,
                    "opening_equity": opening_equity,
                    "closing_equity": closing_equity,
                    "monthly_pnl": monthly_pnl,
                    "monthly_pnl_percent": monthly_pnl_percent,
                    "total_trades": total_trades,
                    "winning_trades": winning_trades,
                    "win_rate": win_rate,
                    "best_trade": best_trade,
                    "worst_trade": worst_trade,
                    "strategy_breakdown": strategy_breakdown,
                    "monthly_insights": insights
                }

                # Store summary
                await self._store_monthly_summary(summary)

                return summary

            except Exception as e:
                logger.error(f"Failed to calculate monthly P&L for {year}-{month:02d}: {e}")
                return {}

    async def _store_monthly_summary(self, summary: Dict[str, Any]) -> None:
        """Store monthly P&L summary."""
        try:
            await self.db.connection.execute(
                """INSERT OR REPLACE INTO monthly_pnl_summary
                   (year, month, opening_equity, closing_equity, monthly_pnl,
                    monthly_pnl_percent, total_trades, winning_trades,
                    best_trade, worst_trade, strategy_breakdown, monthly_insights, created_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (summary["year"], summary["month"], summary["opening_equity"],
                 summary["closing_equity"], summary["monthly_pnl"],
                 summary["monthly_pnl_percent"], summary["total_trades"],
                 summary["winning_trades"], summary["best_trade"],
                 summary["worst_trade"], json.dumps(summary["strategy_breakdown"]),
                 json.dumps(summary["monthly_insights"]), datetime.now(timezone.utc).isoformat())
            )
            await self.db.connection.commit()

        except Exception as e:
            logger.error(f"Failed to store monthly summary: {e}")

    async def get_monthly_performance(self, months_back: int = 12) -> List[Dict[str, Any]]:
        """Get monthly performance data."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT year, month, opening_equity, closing_equity, monthly_pnl,
                          monthly_pnl_percent, total_trades, winning_trades,
                          best_trade, worst_trade, strategy_breakdown, monthly_insights
                       FROM monthly_pnl_summary
                       ORDER BY year DESC, month DESC
                       LIMIT ?""",
                    (months_back,)
                )
                rows = await cursor.fetchall()

                performance = []
                for row in rows:
                    performance.append({
                        "year": row[0],
                        "month": row[1],
                        "opening_equity": row[2],
                        "closing_equity": row[3],
                        "monthly_pnl": row[4],
                        "monthly_pnl_percent": row[5],
                        "total_trades": row[6],
                        "winning_trades": row[7],
                        "best_trade": row[8],
                        "worst_trade": row[9],
                        "strategy_breakdown": json.loads(row[10]) if row[10] else {},
                        "monthly_insights": json.loads(row[11]) if row[11] else []
                    })
                return performance

            except Exception as e:
                logger.error(f"Failed to get monthly performance: {e}")
                return []