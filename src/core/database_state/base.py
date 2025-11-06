"""
Database connection and table management for Robo Trader.

Handles database initialization, connection pooling, and schema creation.
"""

import asyncio
from typing import Optional

import aiosqlite
from loguru import logger

from src.config import Config
from src.core.database_state.backup_manager import DatabaseBackupManager


class DatabaseConnection:
    """
    Manages database connection and schema for all state managers.

    Provides connection pooling, transaction management, and table creation.
    """

    def __init__(self, config: Config):
        """
        Initialize database connection.

        Args:
            config: Application configuration
        """
        self.config = config
        self.db_path = config.state_dir / "robo_trader.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connection pool
        self._connection_pool: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # Backup manager
        self.backup_manager = DatabaseBackupManager(
            self.db_path, backup_dir=self.db_path.parent / "backups"
        )

    async def initialize(self) -> None:
        """
        Initialize database connection and create tables.

        Raises:
            asyncio.TimeoutError: If connection or table creation times out
            Exception: If database initialization fails
        """
        async with self._lock:
            try:
                logger.info(f"Connecting to database at {self.db_path}")
                self._connection_pool = await asyncio.wait_for(
                    aiosqlite.connect(str(self.db_path)), timeout=10.0
                )
                logger.info("Database connection established")

                await self._perform_operation_with_timeout(
                    self._create_tables(), timeout=15.0, operation_name="Table creation"
                )
                logger.info("Database tables created successfully")

                # Create automatic backup on startup if database exists and has data
                if self.db_path.exists() and self.db_path.stat().st_size > 0:
                    await self.backup_manager.create_backup(label="startup")
                    logger.info("Startup backup created")

            except asyncio.TimeoutError:
                logger.error("Database initialization timed out")
                raise
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                raise

    async def _perform_operation_with_timeout(
        self, coro, timeout: float, operation_name: str
    ):
        """
        Perform async operation with timeout and proper task cancellation.

        Args:
            coro: Coroutine to execute
            timeout: Timeout in seconds
            operation_name: Name for logging

        Returns:
            Result of the coroutine

        Raises:
            asyncio.TimeoutError: If operation times out
        """
        task = None
        try:
            task = asyncio.create_task(coro)
            return await asyncio.wait_for(task, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"{operation_name} timed out after {timeout} seconds")
            if task and not task.done():
                task.cancel()
                try:
                    await asyncio.wait_for(task, timeout=5.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            raise
        except Exception:
            # Re-raise other exceptions without modification
            raise

    async def _create_tables(self) -> None:
        """Create all database tables and indexes."""
        schema = """
        -- Portfolio state
        CREATE TABLE IF NOT EXISTS portfolio (
            id INTEGER PRIMARY KEY,
            as_of TEXT NOT NULL,
            cash TEXT NOT NULL,  -- JSON
            holdings TEXT NOT NULL,  -- JSON
            exposure_total REAL NOT NULL,
            risk_aggregates TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Trading intents
        CREATE TABLE IF NOT EXISTS intents (
            id TEXT PRIMARY KEY,
            symbol TEXT NOT NULL,
            created_at TEXT NOT NULL,
            signal TEXT,  -- JSON
            risk_decision TEXT,  -- JSON
            order_commands TEXT NOT NULL,  -- JSON
            execution_reports TEXT NOT NULL,  -- JSON
            status TEXT NOT NULL,
            approved_at TEXT,
            executed_at TEXT,
            source TEXT NOT NULL
        );

        -- Screening results
        CREATE TABLE IF NOT EXISTS screening_results (
            id INTEGER PRIMARY KEY,
            results TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Strategy results
        CREATE TABLE IF NOT EXISTS strategy_results (
            id INTEGER PRIMARY KEY,
            results TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Analysis history
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            analysis TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL
        );

        -- Priority queue
        CREATE TABLE IF NOT EXISTS priority_queue (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            reason TEXT NOT NULL,
            priority TEXT NOT NULL,
            added_at TEXT NOT NULL,
            processed_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending'
        );

        -- Approval queue
        CREATE TABLE IF NOT EXISTS approval_queue (
            id TEXT PRIMARY KEY,
            recommendation TEXT NOT NULL,  -- JSON
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            user_feedback TEXT
        );

        -- Weekly plans
        CREATE TABLE IF NOT EXISTS weekly_plans (
            id INTEGER PRIMARY KEY,
            plan TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Daily plans
        CREATE TABLE IF NOT EXISTS daily_plans (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Learning insights
        CREATE TABLE IF NOT EXISTS learning_insights (
            id INTEGER PRIMARY KEY,
            insights TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL
        );

        -- News items
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            content TEXT,
            source TEXT,
            sentiment TEXT NOT NULL,
            relevance_score REAL DEFAULT 0.5,
            published_at TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            citations TEXT,  -- JSON
            created_at TEXT NOT NULL
        );

        -- News fetch tracking per symbol
        CREATE TABLE IF NOT EXISTS news_fetch_tracking (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL UNIQUE,
            last_news_fetch TEXT,
            last_earnings_fetch TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Earnings reports
        CREATE TABLE IF NOT EXISTS earnings_reports (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            fiscal_period TEXT NOT NULL,
            fiscal_year INTEGER,
            fiscal_quarter INTEGER,
            report_date TEXT NOT NULL,
            eps_actual REAL,
            eps_estimated REAL,
            revenue_actual REAL,
            revenue_estimated REAL,
            surprise_pct REAL,
            guidance TEXT,
            next_earnings_date TEXT,
            fetched_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(symbol, fiscal_period)
        );

        -- Fundamental Analysis Results
        CREATE TABLE IF NOT EXISTS fundamental_analysis (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            analysis_date TEXT NOT NULL,
            pe_ratio REAL,
            pb_ratio REAL,
            roe REAL,
            roa REAL,
            debt_to_equity REAL,
            current_ratio REAL,
            profit_margins REAL,
            revenue_growth REAL,
            earnings_growth REAL,
            dividend_yield REAL,
            market_cap REAL,
            sector_pe REAL,
            industry_rank INTEGER,
            overall_score REAL,
            recommendation TEXT,
            analysis_data TEXT,  -- JSON for additional metrics
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(symbol, analysis_date)
        );

        -- Trading Recommendations
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            recommendation_type TEXT NOT NULL,  -- BUY/SELL/HOLD
            confidence_score REAL,
            target_price REAL,
            stop_loss REAL,
            quantity INTEGER,
            reasoning TEXT,
            analysis_type TEXT,
            time_horizon TEXT,
            risk_level TEXT,
            potential_impact TEXT,
            alternative_suggestions TEXT,  -- JSON array
            created_at TEXT NOT NULL,
            executed_at TEXT,
            outcome TEXT,
            actual_return REAL
        );

        -- Market Conditions Tracking
        CREATE TABLE IF NOT EXISTS market_conditions (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL UNIQUE,
            vix_index REAL,
            nifty_50_level REAL,
            market_sentiment TEXT,
            interest_rates REAL,
            inflation_rate REAL,
            gdp_growth REAL,
            sector_performance TEXT,  -- JSON
            global_events TEXT,  -- JSON
            created_at TEXT NOT NULL
        );

        -- Analysis Performance Tracking
        CREATE TABLE IF NOT EXISTS analysis_performance (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            recommendation_id INTEGER,
            prediction_date TEXT NOT NULL,
            execution_date TEXT,
            predicted_direction TEXT,
            actual_direction TEXT,
            predicted_return REAL,
            actual_return REAL,
            accuracy_score REAL,
            model_version TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (recommendation_id) REFERENCES recommendations(id)
        );

        -- Stock Scheduler State
        CREATE TABLE IF NOT EXISTS stock_scheduler_state (
            symbol TEXT PRIMARY KEY,
            last_news_check DATE,
            last_earnings_check DATE,
            last_fundamentals_check DATE,
            last_portfolio_update DATETIME,
            needs_fundamentals_recheck BOOLEAN DEFAULT 0,
            updated_at TEXT NOT NULL
        );

        -- Strategy Logs
        CREATE TABLE IF NOT EXISTS strategy_logs (
            id INTEGER PRIMARY KEY,
            strategy_type TEXT NOT NULL,
            date TEXT NOT NULL,
            what_worked TEXT,  -- JSON
            what_didnt_work TEXT,  -- JSON
            tomorrows_focus TEXT,  -- JSON
            market_observations TEXT,  -- JSON
            trades_executed INTEGER DEFAULT 0,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0,
            pnl_realized REAL DEFAULT 0.0,
            token_usage TEXT,  -- JSON
            metadata TEXT,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(strategy_type, date)
        );

        -- Checkpoints
        CREATE TABLE IF NOT EXISTS checkpoints (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            metadata TEXT NOT NULL,  -- JSON
            portfolio TEXT,  -- JSON
            intents TEXT NOT NULL,  -- JSON
            created_at TEXT NOT NULL
        );

        -- Optimized Prompts
        CREATE TABLE IF NOT EXISTS optimized_prompts (
            id INTEGER PRIMARY KEY,
            data_type TEXT NOT NULL,
            original_prompt TEXT NOT NULL,
            optimized_prompt TEXT NOT NULL,
            quality_score REAL DEFAULT 0.0,
            quality_score_before REAL DEFAULT 0.0,
            quality_score_after REAL DEFAULT 0.0,
            usage_count INTEGER DEFAULT 0,
            avg_quality_rating REAL DEFAULT 0.0,
            optimization_attempts INTEGER DEFAULT 0,
            optimization_triggered BOOLEAN DEFAULT 0,
            prompt_optimized BOOLEAN DEFAULT 0,
            optimization_details TEXT,  -- JSON
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(data_type, created_at)
        );

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_analysis_history_symbol ON analysis_history(symbol);
        CREATE INDEX IF NOT EXISTS idx_analysis_history_timestamp ON analysis_history(timestamp);
        CREATE INDEX IF NOT EXISTS idx_daily_plans_date ON daily_plans(date);
        CREATE INDEX IF NOT EXISTS idx_priority_queue_status ON priority_queue(status);
        CREATE INDEX IF NOT EXISTS idx_approval_queue_status ON approval_queue(status);
        CREATE INDEX IF NOT EXISTS idx_news_items_symbol ON news_items(symbol);
        CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at);
        CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_items(sentiment);
        CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news_items(symbol, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_news_relevance ON news_items(relevance_score DESC, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_earnings_symbol ON earnings_reports(symbol);
        CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings_reports(report_date);
        CREATE INDEX IF NOT EXISTS idx_earnings_symbol_date ON earnings_reports(symbol, report_date DESC);
        CREATE INDEX IF NOT EXISTS idx_fundamental_analysis_symbol ON fundamental_analysis(symbol);
        CREATE INDEX IF NOT EXISTS idx_fundamental_analysis_date ON fundamental_analysis(analysis_date);
        CREATE INDEX IF NOT EXISTS idx_fundamental_analysis_symbol_date ON fundamental_analysis(symbol, analysis_date DESC);
        CREATE INDEX IF NOT EXISTS idx_fundamental_analysis_score ON fundamental_analysis(overall_score DESC);
        CREATE INDEX IF NOT EXISTS idx_recommendations_symbol ON recommendations(symbol);
        CREATE INDEX IF NOT EXISTS idx_recommendations_type ON recommendations(recommendation_type);
        CREATE INDEX IF NOT EXISTS idx_recommendations_created ON recommendations(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_recommendations_symbol_type ON recommendations(symbol, recommendation_type);
        CREATE INDEX IF NOT EXISTS idx_market_conditions_date ON market_conditions(date);
        CREATE INDEX IF NOT EXISTS idx_analysis_performance_symbol ON analysis_performance(symbol);
        CREATE INDEX IF NOT EXISTS idx_analysis_performance_recommendation ON analysis_performance(recommendation_id);
        CREATE INDEX IF NOT EXISTS idx_analysis_performance_accuracy ON analysis_performance(accuracy_score DESC);
        CREATE INDEX IF NOT EXISTS idx_analysis_performance_symbol_date ON analysis_performance(symbol, prediction_date DESC);
        CREATE INDEX IF NOT EXISTS idx_stock_scheduler_state_symbol ON stock_scheduler_state(symbol);
        CREATE INDEX IF NOT EXISTS idx_stock_scheduler_state_updated_at ON stock_scheduler_state(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_strategy_logs_strategy_type ON strategy_logs(strategy_type);
        CREATE INDEX IF NOT EXISTS idx_strategy_logs_date ON strategy_logs(date DESC);
        CREATE INDEX IF NOT EXISTS idx_strategy_logs_strategy_type_date ON strategy_logs(strategy_type, date DESC);
        CREATE INDEX IF NOT EXISTS idx_optimized_prompts_data_type ON optimized_prompts(data_type);
        CREATE INDEX IF NOT EXISTS idx_optimized_prompts_created ON optimized_prompts(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_optimized_prompts_data_type_created ON optimized_prompts(data_type, created_at DESC);
        """

        await self._connection_pool.executescript(schema)
        await self._connection_pool.commit()
        logger.info("Database schema initialized")

    @property
    def connection(self) -> aiosqlite.Connection:
        """
        Get database connection.

        Returns:
            Active database connection

        Raises:
            RuntimeError: If database not initialized
        """
        if self._connection_pool is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        return self._connection_pool

    async def cleanup(self) -> None:
        """Close database connection and cleanup resources."""
        async with self._lock:
            if self._connection_pool:
                # Create a final backup before shutdown
                await self.backup_manager.create_backup(label="shutdown")

                await self._connection_pool.close()
                self._connection_pool = None
                logger.info("Database connection closed")
