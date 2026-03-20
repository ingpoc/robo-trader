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
                performance_impact TEXT,  -- JSON blob with before/after metrics
                evolution_reason TEXT,
                automated BOOLEAN DEFAULT FALSE,
                created_at TEXT NOT NULL
            );

            -- Stock Discovery Watchlist
            CREATE TABLE IF NOT EXISTS stock_discovery_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                company_name TEXT,
                sector TEXT,
                discovery_date TEXT NOT NULL,
                discovery_source TEXT NOT NULL,  -- 'perplexity_research', 'market_scanner', 'news_alert', 'sector_analysis'
                discovery_reason TEXT,  -- Why this stock was discovered
                current_price REAL,
                market_cap TEXT,
                recommendation TEXT DEFAULT 'WATCH',  -- 'WATCH', 'BUY', 'AVOID'
                confidence_score REAL CHECK (confidence_score >= 0 AND confidence_score <= 1),
                research_summary TEXT,  -- JSON blob with key findings
                technical_indicators TEXT,  -- JSON blob with technical analysis
                fundamental_metrics TEXT,  -- JSON blob with fundamentals
                last_analyzed TEXT,
                status TEXT DEFAULT 'ACTIVE' CHECK (status IN ('ACTIVE', 'INACTIVE', 'REVIEWED', 'ACTIONED')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(symbol, discovery_date)
            );

            -- Stock Discovery Screening Sessions
            CREATE TABLE IF NOT EXISTS stock_discovery_sessions (
                id TEXT PRIMARY KEY,
                session_date TEXT NOT NULL,
                session_type TEXT NOT NULL,  -- 'daily_screen', 'sector_focus', 'market_sweep', 'event_driven'
                screening_criteria TEXT,  -- JSON blob with filters used
                total_stocks_scanned INTEGER DEFAULT 0,
                stocks_discovered INTEGER DEFAULT 0,
                high_potential_stocks INTEGER DEFAULT 0,
                session_duration_ms INTEGER,
                key_insights TEXT,  -- JSON array of important findings
                market_conditions TEXT,  -- JSON blob with market context
                session_status TEXT DEFAULT 'RUNNING' CHECK (session_status IN ('RUNNING', 'COMPLETED', 'FAILED', 'CANCELLED')),
                error_message TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            );

            -- Stock Discovery Results
            CREATE TABLE IF NOT EXISTS stock_discovery_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                score REAL NOT NULL,  -- Composite score (0-100)
                recommendation TEXT NOT NULL,  -- 'STRONG_BUY', 'BUY', 'HOLD', 'AVOID', 'STRONG_AVOID'
                analysis_summary TEXT,  -- JSON with key analysis points
                risk_level TEXT,  -- 'LOW', 'MEDIUM', 'HIGH', 'VERY_HIGH'
                catalyst_events TEXT,  -- JSON array of upcoming catalysts
                valuation_metrics TEXT,  -- JSON with valuation data
                momentum_indicators TEXT,  -- JSON with momentum data
                research_depth TEXT,  -- 'BASIC', 'STANDARD', 'DEEP'
                confidence_level REAL,
                action_taken TEXT DEFAULT 'NONE',  -- 'NONE', 'ADDED_TO_WATCHLIST', 'TRIGGERED_RESEARCH'
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES stock_discovery_sessions(id) ON DELETE CASCADE
            );

            -- Morning Trading Sessions (PT-003)
            CREATE TABLE IF NOT EXISTS morning_trading_sessions (
                session_id TEXT PRIMARY KEY,
                session_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                metrics TEXT NOT NULL,  -- JSON blob with session metrics
                pre_market_data TEXT,  -- JSON blob with scanned stocks
                trade_ideas TEXT,  -- JSON array of generated ideas
                executed_trades TEXT,  -- JSON array of executed trades
                session_context TEXT,  -- JSON blob with market conditions, etc.
                trigger_source TEXT DEFAULT 'SCHEDULED',  -- 'SCHEDULED', 'MANUAL', 'MARKET_EVENT'
                total_duration_ms INTEGER,
                created_at TEXT NOT NULL
            );

            -- Evening Performance Reviews (PT-004)
            CREATE TABLE IF NOT EXISTS daily_performance_reviews (
                review_id TEXT PRIMARY KEY,
                review_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                success BOOLEAN NOT NULL,
                error_message TEXT,
                review_data TEXT NOT NULL,  -- JSON blob with review metrics
                trades_reviewed TEXT,  -- JSON array of trades reviewed
                daily_pnl REAL NOT NULL,
                daily_pnl_percent REAL NOT NULL,
                open_positions_count INTEGER DEFAULT 0,
                closed_positions_count INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0.0,
                trading_insights TEXT,  -- JSON array of key insights
                strategy_performance TEXT,  -- JSON blob with strategy analysis
                market_observations TEXT,  -- JSON blob with market notes
                next_day_watchlist TEXT,  -- JSON array of symbols to watch
                session_context TEXT,  -- JSON blob with market conditions, etc.
                trigger_source TEXT DEFAULT 'SCHEDULED',  -- 'SCHEDULED', 'MANUAL'
                total_duration_ms INTEGER,
                created_at TEXT NOT NULL
            );

            -- AI Automation Configuration (PT-003, PT-004 scheduling)
            CREATE TABLE IF NOT EXISTS ai_automation_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                morning_session_enabled BOOLEAN DEFAULT FALSE,  -- PT-003
                morning_session_time TEXT DEFAULT '09:00',
                evening_review_enabled BOOLEAN DEFAULT FALSE,  -- PT-004
                evening_review_time TEXT DEFAULT '16:00',
                auto_trade_enabled BOOLEAN DEFAULT FALSE,
                max_positions INTEGER DEFAULT 10,
                max_position_size_percent REAL DEFAULT 5.0,
                stop_loss_percent REAL DEFAULT 2.0,
                target_profit_percent REAL DEFAULT 5.0,
                risk_per_trade_percent REAL DEFAULT 1.0,
                discovery_frequency TEXT DEFAULT 'daily',  -- PT-002
                sectors_to_watch TEXT,  -- JSON array of preferred sectors
                market_cap_range TEXT,  -- JSON with min/max
                last_updated TEXT NOT NULL
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
            CREATE INDEX IF NOT EXISTS idx_ai_automation_config ON ai_automation_config(id);

            -- Morning Session Indexes
            CREATE INDEX IF NOT EXISTS idx_morning_sessions_date ON morning_trading_sessions(session_date DESC);
            CREATE INDEX IF NOT EXISTS idx_morning_sessions_success ON morning_trading_sessions(success);

            -- Evening Performance Review Indexes
            CREATE INDEX IF NOT EXISTS idx_evening_reviews_date ON daily_performance_reviews(review_date DESC);
            CREATE INDEX IF NOT EXISTS idx_evening_reviews_success ON daily_performance_reviews(success);
            CREATE INDEX IF NOT EXISTS idx_evening_reviews_pnl ON daily_performance_reviews(daily_pnl DESC);

            -- Stock Discovery Indexes
            CREATE INDEX IF NOT EXISTS idx_discovery_watchlist_symbol ON stock_discovery_watchlist(symbol);
            CREATE INDEX IF NOT EXISTS idx_discovery_watchlist_date ON stock_discovery_watchlist(discovery_date DESC);
            CREATE INDEX IF NOT EXISTS idx_discovery_watchlist_status ON stock_discovery_watchlist(status);
            CREATE INDEX IF NOT EXISTS idx_discovery_sessions_date ON stock_discovery_sessions(session_date DESC);
            CREATE INDEX IF NOT EXISTS idx_discovery_sessions_type ON stock_discovery_sessions(session_type);
            CREATE INDEX IF NOT EXISTS idx_discovery_results_session ON stock_discovery_results(session_id);
            CREATE INDEX IF NOT EXISTS idx_discovery_results_symbol ON stock_discovery_results(symbol);
            CREATE INDEX IF NOT EXISTS idx_discovery_results_score ON stock_discovery_results(score DESC);
            """

            try:
                await self.db.connection.executescript(schema)
                await self.db.connection.commit()
                logger.info("Paper trading tables initialized successfully")

                # Initialize paper trading account
                await self._initialize_paper_account()

                # Initialize AI automation configuration
                await self._initialize_ai_automation_config()

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

    async def _initialize_ai_automation_config(self) -> None:
        """Initialize AI automation configuration with default settings."""
        # Check if config already exists
        cursor = await self.db.connection.execute(
            "SELECT id FROM ai_automation_config WHERE id = 1"
        )
        if not await cursor.fetchone():
            current_time = datetime.now(timezone.utc).isoformat()

            # Default sectors to watch
            default_sectors = ["Technology", "Healthcare", "Finance", "Consumer", "Industrial"]

            # Default market cap range (in crores)
            default_market_cap_range = {"min": 1000, "max": 100000}

            await self.db.connection.execute(
                """INSERT INTO ai_automation_config
                   (id, morning_session_enabled, morning_session_time, evening_review_enabled,
                    evening_review_time, auto_trade_enabled, max_positions,
                    max_position_size_percent, stop_loss_percent, target_profit_percent,
                    risk_per_trade_percent, discovery_frequency, sectors_to_watch,
                    market_cap_range, last_updated)
                   VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (False, "09:00", False, "16:00", False, 10, 5.0, 2.0, 5.0, 1.0, "daily",
                 json.dumps(default_sectors), json.dumps(default_market_cap_range), current_time)
            )

            await self.db.connection.commit()
            logger.info("AI automation configuration initialized with default settings")

    # ===== AI Automation Operations =====
    async def get_ai_automation_config(self) -> Optional[Dict[str, Any]]:
        """Get AI automation configuration (delegates to get_automation_config)."""
        return await self.get_automation_config()

    async def toggle_ai_trading(self, enabled: bool) -> bool:
        """Toggle AI trading on/off."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """UPDATE ai_automation_config
                       SET auto_trade_enabled = ?, last_updated = ?
                       WHERE id = 1""",
                    (enabled, current_time)
                )

                await self.db.connection.commit()
                logger.info(f"AI trading {'enabled' if enabled else 'disabled'}")
                return True

            except Exception as e:
                logger.error(f"Failed to toggle AI trading: {e}")
                return False

    async def update_risk_limits(self, risk_limits: Dict[str, Any]) -> bool:
        """Update AI trading risk limits."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                # Validate risk limits
                max_position_size = risk_limits.get("max_position_size_percent", 5.0)
                stop_loss = risk_limits.get("stop_loss_percent", 2.0)
                target_profit = risk_limits.get("target_profit_percent", 5.0)
                risk_per_trade = risk_limits.get("risk_per_trade_percent", 1.0)

                # Validate reasonable ranges
                if max_position_size < 0.5 or max_position_size > 20:
                    raise ValueError("max_position_size_percent must be between 0.5 and 20")
                if stop_loss < 0.5 or stop_loss > 10:
                    raise ValueError("stop_loss_percent must be between 0.5 and 10")
                if target_profit < 1 or target_profit > 50:
                    raise ValueError("target_profit_percent must be between 1 and 50")
                if risk_per_trade < 0.5 or risk_per_trade > 5:
                    raise ValueError("risk_per_trade_percent must be between 0.5 and 5")

                await self.db.connection.execute(
                    """UPDATE ai_automation_config
                       SET max_position_size_percent = ?,
                           stop_loss_percent = ?,
                           target_profit_percent = ?,
                           risk_per_trade_percent = ?,
                           last_updated = ?
                       WHERE id = 1""",
                    (max_position_size, stop_loss, target_profit, risk_per_trade, current_time)
                )

                await self.db.connection.commit()
                logger.info("AI trading risk limits updated")
                return True

            except Exception as e:
                logger.error(f"Failed to update risk limits: {e}")
                return False

    async def check_daily_loss_limit(self, current_day_pnl: float) -> bool:
        """Check if daily loss limit has been exceeded based on risk_per_trade_percent."""
        try:
            config = await self.get_automation_config()
            if not config:
                return False

            account = await self.get_account()
            if not account:
                return False

            # Calculate max daily loss based on risk per trade
            risk_per_trade = config.get("risk_per_trade_percent", 1.0)
            total_equity = account.get("total_equity", 1000000.0)

            # Allow max 5 losing trades per day (5 * risk_per_trade_percent)
            max_daily_loss = (risk_per_trade / 100) * total_equity * 5

            return current_day_pnl <= -max_daily_loss

        except Exception as e:
            logger.error(f"Failed to check daily loss limit: {e}")
            return True  # Fail safe - stop trading if check fails

    async def check_trading_hours(self) -> bool:
        """Check if current time is within allowed trading hours (market hours 9:15-15:30 IST)."""
        try:
            # For Indian markets, trading hours are 9:15 AM to 3:30 PM IST
            # TODO: Add proper timezone handling for IST
            now = datetime.now(timezone.utc)

            # Check if it's a weekday (Monday=0 to Friday=4)
            if now.weekday() > 4:  # Saturday=5, Sunday=6
                return False

            # Simple time check (would need timezone conversion for production)
            # For now, assume UTC+5:30 offset for IST
            # This is a simplified check - proper implementation would use pytz

            return True  # For now, allow trading during all hours

        except Exception as e:
            logger.error(f"Failed to check trading hours: {e}")
            return False

    async def record_automated_trade_result(self, success: bool, pnl: float = 0.0) -> bool:
        """Record the result of an automated trade (no-op - trades are tracked in paper_trades table)."""
        # This method is deprecated - trades are already tracked in paper_trades table
        # and can be queried from there
        logger.info(f"Automated trade result recorded: success={success}, pnl={pnl}")
        return True

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
                        risk_metrics, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (trade_id, symbol, side, quantity, entry_price, entry_date, entry_reason,
                     strategy_tag, confidence_score, json.dumps(research_sources),
                     json.dumps(market_conditions), json.dumps(risk_metrics),
                     'OPEN',  # Match CHECK constraint (uppercase)
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

    async def modify_trade(
        self,
        trade_id: str,
        stop_loss: Optional[float] = None,
        target_price: Optional[float] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Modify stop loss and/or target price for an open trade.

        Args:
            trade_id: The trade to modify
            stop_loss: New stop loss price (optional)
            target_price: New target price (optional)

        Returns:
            Updated trade dict or None if failed
        """
        async with self._lock:
            try:
                # Get current trade and risk_metrics
                cursor = await self.db.connection.execute(
                    """SELECT id, symbol, side, quantity, entry_price, risk_metrics, status
                       FROM paper_trades WHERE id = ?""",
                    (trade_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    logger.warning(f"Trade {trade_id} not found")
                    return None

                if row[6] != 'OPEN':
                    logger.warning(f"Trade {trade_id} is not open (status: {row[6]})")
                    return None

                # Parse existing risk_metrics
                risk_metrics = json.loads(row[5]) if row[5] else {}

                # Update stop_loss and target_price
                if stop_loss is not None:
                    risk_metrics["stop_loss"] = stop_loss
                if target_price is not None:
                    risk_metrics["target_price"] = target_price

                current_time = datetime.now(timezone.utc).isoformat()

                # Update in database
                await self.db.connection.execute(
                    """UPDATE paper_trades
                       SET risk_metrics = ?, updated_at = ?
                       WHERE id = ?""",
                    (json.dumps(risk_metrics), current_time, trade_id)
                )
                await self.db.connection.commit()

                logger.info(f"Modified trade {trade_id}: stop_loss={stop_loss}, target_price={target_price}")

                return {
                    "trade_id": row[0],
                    "symbol": row[1],
                    "side": row[2],
                    "quantity": row[3],
                    "entry_price": row[4],
                    "stop_loss": risk_metrics.get("stop_loss"),
                    "target_price": risk_metrics.get("target_price"),
                    "updated_at": current_time
                }

            except Exception as e:
                logger.error(f"Failed to modify trade {trade_id}: {e}")
                return None

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

    # Stock Discovery Methods (PT-002)

    async def get_discovery_watchlist_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock discovery watchlist entry by symbol."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, symbol, company_name, sector, discovery_date,
                             discovery_source, discovery_reason, current_price, market_cap,
                             recommendation, confidence_score, research_summary,
                             technical_indicators, fundamental_metrics, last_analyzed,
                             status, created_at, updated_at
                       FROM stock_discovery_watchlist
                       WHERE symbol = ?
                       ORDER BY discovery_date DESC
                       LIMIT 1""",
                    (symbol,)
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "symbol": row[1],
                        "company_name": row[2],
                        "sector": row[3],
                        "discovery_date": row[4],
                        "discovery_source": row[5],
                        "discovery_reason": row[6],
                        "current_price": row[7],
                        "market_cap": row[8],
                        "recommendation": row[9],
                        "confidence_score": row[10],
                        "research_summary": json.loads(row[11]) if row[11] else {},
                        "technical_indicators": json.loads(row[12]) if row[12] else {},
                        "fundamental_metrics": json.loads(row[13]) if row[13] else {},
                        "last_analyzed": row[14],
                        "status": row[15],
                        "created_at": row[16],
                        "updated_at": row[17]
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get discovery watchlist entry for {symbol}: {e}")
                return None

    async def add_to_discovery_watchlist(self, stock_data: Dict[str, Any]) -> bool:
        """Add stock to discovery watchlist."""
        async with self._lock:
            try:
                await self.db.connection.execute(
                    """INSERT OR REPLACE INTO stock_discovery_watchlist
                       (symbol, company_name, sector, discovery_date, discovery_source,
                        discovery_reason, current_price, market_cap, recommendation,
                        confidence_score, research_summary, technical_indicators,
                        fundamental_metrics, status, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (stock_data["symbol"], stock_data.get("company_name"),
                     stock_data.get("sector"), stock_data["discovery_date"],
                     stock_data["discovery_source"], stock_data.get("discovery_reason"),
                     stock_data.get("current_price"), stock_data.get("market_cap"),
                     stock_data.get("recommendation", "WATCH"),
                     stock_data.get("confidence_score", 0.5),
                     json.dumps(stock_data.get("research_summary", {})),
                     json.dumps(stock_data.get("technical_indicators", {})),
                     json.dumps(stock_data.get("fundamental_metrics", {})),
                     stock_data.get("status", "ACTIVE"),
                     datetime.now(timezone.utc).isoformat(),
                     datetime.now(timezone.utc).isoformat())
                )
                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to add {stock_data.get('symbol')} to discovery watchlist: {e}")
                return False

    async def get_discovery_watchlist(self, limit: int = 50, status: str = "ACTIVE") -> List[Dict[str, Any]]:
        """Get discovery watchlist with optional filters."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, symbol, company_name, sector, discovery_date,
                             discovery_source, recommendation, confidence_score,
                             current_price, status, last_analyzed, created_at
                       FROM stock_discovery_watchlist
                       WHERE status = ?
                       ORDER BY confidence_score DESC, discovery_date DESC
                       LIMIT ?""",
                    (status, limit)
                )
                rows = await cursor.fetchall()

                watchlist = []
                for row in rows:
                    watchlist.append({
                        "id": row[0],
                        "symbol": row[1],
                        "company_name": row[2],
                        "sector": row[3],
                        "discovery_date": row[4],
                        "discovery_source": row[5],
                        "recommendation": row[6],
                        "confidence_score": row[7],
                        "current_price": row[8],
                        "status": row[9],
                        "last_analyzed": row[10],
                        "created_at": row[11]
                    })
                return watchlist

            except Exception as e:
                logger.error(f"Failed to get discovery watchlist: {e}")
                return []

    async def create_discovery_session(self, session_data: Dict[str, Any]) -> str:
        """Create a new stock discovery session."""
        async with self._lock:
            try:
                session_id = session_data.get("id", f"session_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")

                await self.db.connection.execute(
                    """INSERT OR REPLACE INTO stock_discovery_sessions
                       (id, session_date, session_type, screening_criteria,
                        total_stocks_scanned, stocks_discovered, high_potential_stocks,
                        session_duration_ms, key_insights, market_conditions,
                        session_status, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_id, session_data["session_date"], session_data["session_type"],
                     json.dumps(session_data.get("screening_criteria", {})),
                     session_data.get("total_stocks_scanned", 0),
                     session_data.get("stocks_discovered", 0),
                     session_data.get("high_potential_stocks", 0),
                     session_data.get("session_duration_ms"),
                     json.dumps(session_data.get("key_insights", [])),
                     json.dumps(session_data.get("market_conditions", {})),
                     session_data.get("session_status", "RUNNING"),
                     datetime.now(timezone.utc).isoformat())
                )
                await self.db.connection.commit()
                return session_id

            except Exception as e:
                logger.error(f"Failed to create discovery session: {e}")
                return ""

    async def update_discovery_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update discovery session with results."""
        async with self._lock:
            try:
                set_clauses = []
                values = []

                for key, value in updates.items():
                    if key in ["session_status", "total_stocks_scanned", "stocks_discovered",
                              "high_potential_stocks", "session_duration_ms", "error_message"]:
                        set_clauses.append(f"{key} = ?")
                        values.append(value)
                    elif key in ["key_insights", "market_conditions"]:
                        set_clauses.append(f"{key} = ?")
                        values.append(json.dumps(value))

                if updates.get("session_status") == "COMPLETED":
                    set_clauses.append("completed_at = ?")
                    values.append(datetime.now(timezone.utc).isoformat())

                if not set_clauses:
                    return True

                values.append(session_id)

                await self.db.connection.execute(
                    f"""UPDATE stock_discovery_sessions
                       SET {', '.join(set_clauses)}
                       WHERE id = ?""",
                    values
                )
                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to update discovery session {session_id}: {e}")
                return False

    async def store_discovery_results(self, session_id: str, results: List[Dict[str, Any]]) -> bool:
        """Store discovery results for a session."""
        async with self._lock:
            try:
                for result in results:
                    await self.db.connection.execute(
                        """INSERT INTO stock_discovery_results
                           (session_id, symbol, score, recommendation, analysis_summary,
                            risk_level, catalyst_events, valuation_metrics,
                            momentum_indicators, research_depth, confidence_level, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (session_id, result["symbol"], result["score"],
                         result["recommendation"], json.dumps(result.get("analysis_summary", {})),
                         result.get("risk_level"), json.dumps(result.get("catalyst_events", [])),
                         json.dumps(result.get("valuation_metrics", {})),
                         json.dumps(result.get("momentum_indicators", {})),
                         result.get("research_depth", "BASIC"),
                         result.get("confidence_level", 0.5),
                         datetime.now(timezone.utc).isoformat())
                    )
                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store discovery results for session {session_id}: {e}")
                return False

    async def get_discovery_sessions(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent discovery sessions."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, session_date, session_type, total_stocks_scanned,
                             stocks_discovered, high_potential_stocks, session_duration_ms,
                             session_status, created_at, completed_at
                       FROM stock_discovery_sessions
                       ORDER BY created_at DESC
                       LIMIT ?""",
                    (limit,)
                )
                rows = await cursor.fetchall()

                sessions = []
                for row in rows:
                    sessions.append({
                        "id": row[0],
                        "session_date": row[1],
                        "session_type": row[2],
                        "total_stocks_scanned": row[3],
                        "stocks_discovered": row[4],
                        "high_potential_stocks": row[5],
                        "session_duration_ms": row[6],
                        "session_status": row[7],
                        "created_at": row[8],
                        "completed_at": row[9]
                    })
                return sessions

            except Exception as e:
                logger.error(f"Failed to get discovery sessions: {e}")
                return []

    async def get_automation_config(self) -> Dict[str, Any]:
        """Get AI automation configuration."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT morning_session_enabled, morning_session_time,
                             evening_review_enabled, evening_review_time,
                             auto_trade_enabled, max_positions, max_position_size_percent,
                             stop_loss_percent, target_profit_percent, risk_per_trade_percent,
                             discovery_frequency, sectors_to_watch, market_cap_range, last_updated
                       FROM ai_automation_config
                       WHERE id = 1"""
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "morning_session_enabled": bool(row[0]),
                        "morning_session_time": row[1],
                        "evening_review_enabled": bool(row[2]),
                        "evening_review_time": row[3],
                        "auto_trade_enabled": bool(row[4]),
                        "max_positions": row[5],
                        "max_position_size_percent": row[6],
                        "stop_loss_percent": row[7],
                        "target_profit_percent": row[8],
                        "risk_per_trade_percent": row[9],
                        "discovery_frequency": row[10],
                        "sectors_to_watch": json.loads(row[11]) if row[11] else [],
                        "market_cap_range": json.loads(row[12]) if row[12] else {},
                        "last_updated": row[13]
                    }

                # Return default config if not found
                return {
                    "morning_session_enabled": False,
                    "morning_session_time": "09:00",
                    "evening_review_enabled": False,
                    "evening_review_time": "16:00",
                    "auto_trade_enabled": False,
                    "max_positions": 10,
                    "max_position_size_percent": 5.0,
                    "stop_loss_percent": 2.0,
                    "target_profit_percent": 5.0,
                    "risk_per_trade_percent": 1.0,
                    "discovery_frequency": "daily",
                    "sectors_to_watch": [],
                    "market_cap_range": {"min": 0, "max": 0},
                    "last_updated": datetime.now(timezone.utc).isoformat()
                }

            except Exception as e:
                logger.error(f"Failed to get automation config: {e}")
                return {}

    async def store_morning_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """
        Store morning trading session result.

        Args:
            session_id: Unique session identifier
            session_data: Session data to store

        Returns:
            True if stored successfully
        """
        async with self._lock:
            try:
                await self.db.connection.execute(
                    """
                    INSERT INTO morning_trading_sessions (
                        session_id, session_date, start_time, end_time,
                        success, error_message, metrics, pre_market_data,
                        trade_ideas, executed_trades, session_context,
                        trigger_source, total_duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        session_id,
                        session_data["session_date"],
                        session_data["start_time"],
                        session_data["end_time"],
                        session_data["success"],
                        session_data.get("error_message"),
                        json.dumps(session_data["metrics"]),
                        json.dumps(session_data.get("pre_market_data", [])),
                        json.dumps(session_data.get("trade_ideas", [])),
                        json.dumps(session_data.get("executed_trades", [])),
                        json.dumps(session_data.get("session_context", {})),
                        session_data.get("trigger_source", "SCHEDULED"),
                        session_data.get("total_duration_ms", 0),
                        datetime.now(timezone.utc).isoformat()
                    )
                )

                await self.db.connection.commit()
                logger.info(f"Stored morning session: {session_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to store morning session {session_id}: {e}")
                return False

    async def store_evening_performance_review(self, review_id: str, review_data: Dict[str, Any]) -> bool:
        """
        Store evening performance review result.

        Args:
            review_id: Unique review identifier
            review_data: Review data to store

        Returns:
            True if stored successfully
        """
        async with self._lock:
            try:
                await self.db.connection.execute(
                    """
                    INSERT INTO daily_performance_reviews (
                        review_id, review_date, start_time, end_time,
                        success, error_message, review_data, trades_reviewed,
                        daily_pnl, daily_pnl_percent, open_positions_count,
                        closed_positions_count, win_rate, trading_insights,
                        strategy_performance, market_observations, next_day_watchlist,
                        session_context, trigger_source, total_duration_ms, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        review_id,
                        review_data["review_date"],
                        review_data["start_time"],
                        review_data["end_time"],
                        review_data["success"],
                        review_data.get("error_message"),
                        json.dumps(review_data["review_data"]),
                        json.dumps(review_data.get("trades_reviewed", [])),
                        review_data.get("daily_pnl", 0.0),
                        review_data.get("daily_pnl_percent", 0.0),
                        review_data.get("open_positions_count", 0),
                        review_data.get("closed_positions_count", 0),
                        review_data.get("win_rate", 0.0),
                        json.dumps(review_data.get("trading_insights", [])),
                        json.dumps(review_data.get("strategy_performance", {})),
                        json.dumps(review_data.get("market_observations", {})),
                        json.dumps(review_data.get("next_day_watchlist", [])),
                        json.dumps(review_data.get("session_context", {})),
                        review_data.get("trigger_source", "SCHEDULED"),
                        review_data.get("total_duration_ms", 0),
                        datetime.now(timezone.utc).isoformat()
                    )
                )

                await self.db.connection.commit()
                logger.info(f"Stored evening performance review: {review_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to store evening performance review {review_id}: {e}")
                return False

    async def get_evening_performance_reviews(self, limit: int = 30, successful_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get recent evening performance reviews.

        Args:
            limit: Maximum number of reviews to return
            successful_only: Only return successful reviews

        Returns:
            List of evening performance review data
        """
        async with self._lock:
            try:
                query = """
                    SELECT * FROM daily_performance_reviews
                    WHERE 1=1
                """
                params = []

                if successful_only:
                    query += " AND success = ?"
                    params.append(True)

                query += " ORDER BY review_date DESC, start_time DESC LIMIT ?"
                params.append(limit)

                cursor = await self.db.connection.execute(query, params)
                rows = await cursor.fetchall()

                reviews = []
                for row in rows:
                    review = {key: row[key] for key in row.keys()}
                    # Parse JSON fields
                    review["review_data"] = json.loads(review["review_data"]) if review["review_data"] else {}
                    review["trades_reviewed"] = json.loads(review["trades_reviewed"]) if review["trades_reviewed"] else []
                    review["trading_insights"] = json.loads(review["trading_insights"]) if review["trading_insights"] else []
                    review["strategy_performance"] = json.loads(review["strategy_performance"]) if review["strategy_performance"] else {}
                    review["market_observations"] = json.loads(review["market_observations"]) if review["market_observations"] else {}
                    review["next_day_watchlist"] = json.loads(review["next_day_watchlist"]) if review["next_day_watchlist"] else []
                    review["session_context"] = json.loads(review["session_context"]) if review["session_context"] else {}
                    reviews.append(review)

                return reviews

            except Exception as e:
                logger.error(f"Failed to get evening performance reviews: {e}")
                return []

    async def calculate_daily_performance_metrics(self, review_date: str) -> Dict[str, Any]:
        """
        Calculate daily performance metrics for the evening review.

        Args:
            review_date: Date in YYYY-MM-DD format

        Returns:
            Dictionary with daily performance metrics
        """
        async with self._lock:
            try:
                # Get all trades executed on the review date
                cursor = await self.db.connection.execute(
                    """
                    SELECT id, symbol, side, quantity, entry_price, exit_price,
                           entry_date, exit_date, strategy_tag, status
                    FROM paper_trades
                    WHERE entry_date = ? OR exit_date = ?
                    ORDER BY entry_date DESC
                    """,
                    (review_date, review_date)
                )
                rows = await cursor.fetchall()

                trades_reviewed = []
                daily_pnl = 0.0
                open_positions_count = 0
                closed_positions_count = 0
                winning_trades = 0
                losing_trades = 0

                # Process trades
                for row in rows:
                    trade_id, symbol, side, quantity, entry_price, exit_price, entry_date, exit_date, strategy_tag, status = row

                    trade_info = {
                        "id": trade_id,
                        "symbol": symbol,
                        "side": side,
                        "quantity": quantity,
                        "entry_price": entry_price,
                        "exit_price": exit_price,
                        "strategy_tag": strategy_tag,
                        "status": status
                    }

                    trades_reviewed.append(trade_info)

                    if status == "OPEN":
                        open_positions_count += 1
                        # For open positions, calculate unrealized P&L with current price
                        cursor_price = await self.db.connection.execute(
                            "SELECT current_price FROM paper_positions WHERE symbol = ?",
                            (symbol,)
                        )
                        price_row = await cursor_price.fetchone()
                        if price_row:
                            current_price = price_row[0]
                            if side == "BUY":
                                unrealized_pnl = (current_price - entry_price) * quantity
                            else:
                                unrealized_pnl = (entry_price - current_price) * quantity
                            daily_pnl += unrealized_pnl
                    else:
                        # For closed trades, calculate realized P&L
                        closed_positions_count += 1
                        if exit_price is not None:
                            if side == "BUY":
                                trade_pnl = (exit_price - entry_price) * quantity
                            else:
                                trade_pnl = (entry_price - exit_price) * quantity
                            daily_pnl += trade_pnl

                            if trade_pnl > 0:
                                winning_trades += 1
                            elif trade_pnl < 0:
                                losing_trades += 1

                # Calculate win rate
                total_closed_trades = closed_positions_count
                win_rate = (winning_trades / total_closed_trades * 100) if total_closed_trades > 0 else 0.0

                # Get account data for P&L percentage
                cursor = await self.db.connection.execute(
                    "SELECT initial_capital, total_equity FROM paper_trading_account WHERE id = 1"
                )
                account_row = await cursor.fetchone()
                daily_pnl_percent = 0.0
                if account_row:
                    initial_capital, total_equity = account_row
                    if initial_capital > 0:
                        daily_pnl_percent = (daily_pnl / initial_capital) * 100

                # Get strategy performance breakdown
                strategy_performance = {}
                for trade in trades_reviewed:
                    strategy = trade["strategy_tag"]
                    if strategy not in strategy_performance:
                        strategy_performance[strategy] = {
                            "trades": 0,
                            "winning_trades": 0,
                            "total_pnl": 0.0
                        }

                    strategy_performance[strategy]["trades"] += 1

                    # Add P&L if trade is closed
                    if trade["status"] == "CLOSED" and trade["exit_price"]:
                        if trade["side"] == "BUY":
                            trade_pnl = (trade["exit_price"] - trade["entry_price"]) * trade["quantity"]
                        else:
                            trade_pnl = (trade["entry_price"] - trade["exit_price"]) * trade["quantity"]

                        strategy_performance[strategy]["total_pnl"] += trade_pnl

                        if trade_pnl > 0:
                            strategy_performance[strategy]["winning_trades"] += 1

                # Calculate strategy win rates
                for strategy in strategy_performance:
                    trades = strategy_performance[strategy]["trades"]
                    wins = strategy_performance[strategy]["winning_trades"]
                    strategy_performance[strategy]["win_rate"] = (wins / trades * 100) if trades > 0 else 0.0

                return {
                    "trades_reviewed": trades_reviewed,
                    "daily_pnl": daily_pnl,
                    "daily_pnl_percent": daily_pnl_percent,
                    "open_positions_count": open_positions_count,
                    "closed_positions_count": closed_positions_count,
                    "win_rate": win_rate,
                    "strategy_performance": strategy_performance,
                    "winning_trades": winning_trades,
                    "losing_trades": losing_trades
                }

            except Exception as e:
                logger.error(f"Failed to calculate daily performance metrics for {review_date}: {e}")
                return {
                    "trades_reviewed": [],
                    "daily_pnl": 0.0,
                    "daily_pnl_percent": 0.0,
                    "open_positions_count": 0,
                    "closed_positions_count": 0,
                    "win_rate": 0.0,
                    "strategy_performance": {},
                    "winning_trades": 0,
                    "losing_trades": 0
                }

    async def get_morning_sessions(self, limit: int = 30, successful_only: bool = False) -> List[Dict[str, Any]]:
        """
        Get recent morning trading sessions.

        Args:
            limit: Maximum number of sessions to return
            successful_only: Only return successful sessions

        Returns:
            List of morning session data
        """
        async with self._lock:
            try:
                query = """
                    SELECT * FROM morning_trading_sessions
                    WHERE 1=1
                """
                params = []

                if successful_only:
                    query += " AND success = ?"
                    params.append(True)

                query += " ORDER BY session_date DESC, start_time DESC LIMIT ?"
                params.append(limit)

                cursor = await self.db.connection.execute(query, params)
                rows = await cursor.fetchall()

                sessions = []
                for row in rows:
                    session = {key: row[key] for key in row.keys()}
                    # Parse JSON fields
                    session["metrics"] = json.loads(session["metrics"]) if session["metrics"] else {}
                    session["pre_market_data"] = json.loads(session["pre_market_data"]) if session["pre_market_data"] else []
                    session["trade_ideas"] = json.loads(session["trade_ideas"]) if session["trade_ideas"] else []
                    session["executed_trades"] = json.loads(session["executed_trades"]) if session["executed_trades"] else []
                    session["session_context"] = json.loads(session["session_context"]) if session["session_context"] else {}
                    sessions.append(session)

                return sessions

            except Exception as e:
                logger.error(f"Failed to get morning sessions: {e}")
                return []