"""
Database-backed State Manager for Robo Trader

Replaces file-based storage with SQLite database for better concurrency,
ACID compliance, and production readiness.
"""

import asyncio
import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import asynccontextmanager
import aiosqlite
from loguru import logger

from ..config import Config
from .state_models import (
    PortfolioState, Signal, RiskDecision, OrderCommand,
    ExecutionReport, Intent, FundamentalAnalysis, Recommendation,
    MarketConditions, AnalysisPerformance
)
from .alerts import AlertManager


class DatabaseStateManager:
    """
    Database-backed state manager with proper transaction management
    and concurrent access support.
    """

    def __init__(self, config: Config):
        self.config = config
        self.db_path = config.state_dir / "robo_trader.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Connection pool settings
        self._connection_pool: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

        # In-memory caches for performance
        self._portfolio: Optional[PortfolioState] = None
        self._intents: Dict[str, Intent] = {}
        self._screening_results: Optional[Dict[str, Any]] = None
        self._strategy_results: Optional[Dict[str, Any]] = None
        self._priority_queue: List[Dict] = []
        self._approval_queue: List[Dict] = []
        self._weekly_plan: Optional[Dict] = None

        # Alert manager
        self.alert_manager = AlertManager(config.state_dir)

    async def _perform_operation_with_timeout(self, coro, timeout: float, operation_name: str):
        """Perform an async operation with timeout and proper task cancellation."""
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
            # Re-raise other exceptions without cancellation
            raise

    async def initialize(self) -> None:
        """Initialize database and create tables."""
        async with self._lock:
            try:
                # Add timeout to database connection
                logger.info(f"Connecting to database at {self.db_path}")
                self._connection_pool = await asyncio.wait_for(
                    aiosqlite.connect(str(self.db_path)),
                    timeout=10.0
                )
                logger.info("Database connection established")

                # Add timeout to table creation
                await self._perform_operation_with_timeout(
                    self._create_tables(),
                    timeout=15.0,
                    operation_name="Table creation"
                )
                logger.info("Database tables created")

                # Add timeout to initial state loading
                await self._perform_operation_with_timeout(
                    self._load_initial_state(),
                    timeout=20.0,
                    operation_name="Initial state loading"
                )
                logger.info("Initial state loaded from database")

                logger.info("Database state manager initialized successfully")

            except asyncio.TimeoutError as e:
                logger.error(f"Database initialization timed out: {e}")
                # Close connection if it was established
                if self._connection_pool:
                    await self._connection_pool.close()
                    self._connection_pool = None
                raise
            except Exception as e:
                logger.error(f"Database initialization failed: {e}")
                # Close connection if it was established
                if self._connection_pool:
                    await self._connection_pool.close()
                    self._connection_pool = None
                raise

    async def _create_tables(self) -> None:
        """Create all database tables."""
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

        -- News and earnings data
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

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_news_symbol ON news_items(symbol);
        CREATE INDEX IF NOT EXISTS idx_news_published_at ON news_items(published_at);
        CREATE INDEX IF NOT EXISTS idx_news_sentiment ON news_items(sentiment);
        CREATE INDEX IF NOT EXISTS idx_news_symbol_date ON news_items(symbol, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_news_relevance ON news_items(relevance_score DESC, published_at DESC);
        CREATE INDEX IF NOT EXISTS idx_earnings_symbol ON earnings_reports(symbol);
        CREATE INDEX IF NOT EXISTS idx_earnings_date ON earnings_reports(report_date);
        CREATE INDEX IF NOT EXISTS idx_earnings_symbol_date ON earnings_reports(symbol, report_date DESC);

        -- News items
        CREATE TABLE IF NOT EXISTS news_items (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT,
            url TEXT,
            sentiment TEXT,
            published_at TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        -- Earnings reports
        CREATE TABLE IF NOT EXISTS earnings_reports (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            fiscal_period TEXT NOT NULL,
            report_date TEXT NOT NULL,
            eps_actual REAL,
            eps_estimated REAL,
            revenue_actual REAL,
            revenue_estimated REAL,
            surprise_pct REAL,
            guidance TEXT,
            next_earnings_date TEXT,
            created_at TEXT NOT NULL
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

        -- Create indexes for performance
        CREATE INDEX IF NOT EXISTS idx_analysis_history_symbol ON analysis_history(symbol);
        CREATE INDEX IF NOT EXISTS idx_analysis_history_timestamp ON analysis_history(timestamp);
        CREATE INDEX IF NOT EXISTS idx_daily_plans_date ON daily_plans(date);
        CREATE INDEX IF NOT EXISTS idx_priority_queue_status ON priority_queue(status);
        CREATE INDEX IF NOT EXISTS idx_approval_queue_status ON approval_queue(status);
        CREATE INDEX IF NOT EXISTS idx_news_items_symbol ON news_items(symbol);
        CREATE INDEX IF NOT EXISTS idx_news_items_published_at ON news_items(published_at);
        CREATE INDEX IF NOT EXISTS idx_earnings_reports_symbol ON earnings_reports(symbol);
        CREATE INDEX IF NOT EXISTS idx_earnings_reports_report_date ON earnings_reports(report_date);

        -- Indexes for new analysis tables
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
        """

        await self._connection_pool.executescript(schema)
        await self._connection_pool.commit()
        logger.info("Database tables and indexes created")

    async def _load_initial_state(self) -> None:
        """Load initial state from database into memory."""
        # Load portfolio
        async with self._connection_pool.execute(
            "SELECT * FROM portfolio ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                self._portfolio = PortfolioState(
                    as_of=row[1],
                    cash=json.loads(row[2]),
                    holdings=json.loads(row[3]),
                    exposure_total=row[4],
                    risk_aggregates=json.loads(row[5])
                )

        # Load intents
        async with self._connection_pool.execute("SELECT * FROM intents") as cursor:
            async for row in cursor:
                intent_data = {
                    "id": row[0],
                    "symbol": row[1],
                    "created_at": row[2],
                    "signal": json.loads(row[3]) if row[3] else None,
                    "risk_decision": json.loads(row[4]) if row[4] else None,
                    "order_commands": json.loads(row[5]),
                    "execution_reports": json.loads(row[6]),
                    "status": row[7],
                    "approved_at": row[8],
                    "executed_at": row[9],
                    "source": row[10]
                }
                self._intents[row[0]] = Intent.from_dict(intent_data)

        # Load other state as needed
        await self._load_screening_results()
        await self._load_strategy_results()
        await self._load_priority_queue()
        await self._load_approval_queue()
        await self._load_weekly_plan()

    async def _load_screening_results(self) -> None:
        """Load screening results from database."""
        async with self._connection_pool.execute(
            "SELECT results FROM screening_results ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                self._screening_results = json.loads(row[0])

    async def _load_strategy_results(self) -> None:
        """Load strategy results from database."""
        async with self._connection_pool.execute(
            "SELECT results FROM strategy_results ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                self._strategy_results = json.loads(row[0])

    async def _load_priority_queue(self) -> None:
        """Load priority queue from database."""
        self._priority_queue = []
        async with self._connection_pool.execute(
            "SELECT symbol, reason, priority, added_at FROM priority_queue WHERE status = 'pending' ORDER BY added_at DESC"
        ) as cursor:
            async for row in cursor:
                self._priority_queue.append({
                    "symbol": row[0],
                    "reason": row[1],
                    "priority": row[2],
                    "added_at": row[3]
                })

    async def _load_approval_queue(self) -> None:
        """Load approval queue from database."""
        self._approval_queue = []
        async with self._connection_pool.execute(
            "SELECT id, recommendation, status, created_at, updated_at, user_feedback FROM approval_queue ORDER BY created_at DESC"
        ) as cursor:
            async for row in cursor:
                self._approval_queue.append({
                    "id": row[0],
                    "recommendation": json.loads(row[1]),
                    "status": row[2],
                    "created_at": row[3],
                    "updated_at": row[4],
                    "user_feedback": row[5]
                })

    async def _load_weekly_plan(self) -> None:
        """Load weekly plan from database."""
        async with self._connection_pool.execute(
            "SELECT plan FROM weekly_plans ORDER BY updated_at DESC LIMIT 1"
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                self._weekly_plan = json.loads(row[0])

    # Portfolio operations
    async def get_portfolio(self) -> Optional[PortfolioState]:
        """Get current portfolio state."""
        async with self._lock:
            return self._portfolio

    async def update_portfolio(self, portfolio: PortfolioState) -> None:
        """Update portfolio state."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self._portfolio = portfolio

            async with self._connection_pool.execute("""
                INSERT OR REPLACE INTO portfolio
                (id, as_of, cash, holdings, exposure_total, risk_aggregates, created_at, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            """, (
                portfolio.as_of,
                json.dumps(portfolio.cash),
                json.dumps(portfolio.holdings),
                portfolio.exposure_total,
                json.dumps(portfolio.risk_aggregates),
                now,
                now
            )):
                await self._connection_pool.commit()

            logger.info(f"Portfolio updated as of {portfolio.as_of}")

    # Intent operations
    async def get_intent(self, intent_id: str) -> Optional[Intent]:
        """Get intent by ID."""
        async with self._lock:
            return self._intents.get(intent_id)

    async def get_all_intents(self) -> List[Intent]:
        """Get all intents."""
        async with self._lock:
            return list(self._intents.values())

    async def create_intent(self, symbol: str, signal: Optional[Signal] = None, source: str = "system") -> Intent:
        """Create new trading intent."""
        async with self._lock:
            intent_id = f"intent_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}"
            intent = Intent(
                id=intent_id,
                symbol=symbol,
                signal=signal,
                source=source
            )
            self._intents[intent_id] = intent

            await self._save_intent(intent)
            logger.info(f"Created intent {intent_id} for {symbol}")
            return intent

    async def update_intent(self, intent: Intent) -> None:
        """Update existing intent."""
        async with self._lock:
            self._intents[intent.id] = intent
            await self._save_intent(intent)
            logger.info(f"Updated intent {intent.id}")

    async def _save_intent(self, intent: Intent) -> None:
        """Save intent to database."""
        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO intents
            (id, symbol, created_at, signal, risk_decision, order_commands, execution_reports, status, approved_at, executed_at, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            intent.id,
            intent.symbol,
            intent.created_at,
            json.dumps(intent.signal.to_dict()) if intent.signal else None,
            json.dumps(intent.risk_decision.to_dict()) if intent.risk_decision else None,
            json.dumps([cmd.to_dict() for cmd in intent.order_commands]),
            json.dumps([rep.to_dict() for rep in intent.execution_reports]),
            intent.status,
            intent.approved_at,
            intent.executed_at,
            intent.source
        )):
            await self._connection_pool.commit()

    # Screening and strategy results
    async def update_screening_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update screening results."""
        async with self._lock:
            self._screening_results = results
            now = datetime.now(timezone.utc).isoformat()

            async with self._connection_pool.execute("""
                INSERT OR REPLACE INTO screening_results (id, results, created_at, updated_at)
                VALUES (1, ?, ?, ?)
            """, (json.dumps(results), now, now)):
                await self._connection_pool.commit()

    async def get_screening_results(self) -> Optional[Dict[str, Any]]:
        """Get screening results."""
        async with self._lock:
            return self._screening_results

    async def update_strategy_results(self, results: Optional[Dict[str, Any]]) -> None:
        """Update strategy results."""
        async with self._lock:
            self._strategy_results = results
            now = datetime.now(timezone.utc).isoformat()

            async with self._connection_pool.execute("""
                INSERT OR REPLACE INTO strategy_results (id, results, created_at, updated_at)
                VALUES (1, ?, ?, ?)
            """, (json.dumps(results), now, now)):
                await self._connection_pool.commit()

    async def get_strategy_results(self) -> Optional[Dict[str, Any]]:
        """Get strategy results."""
        async with self._lock:
            return self._strategy_results

    # Analysis history
    async def save_analysis_history(self, symbol: str, analysis: Dict) -> None:
        """Save detailed analysis history per stock."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT INTO analysis_history (symbol, timestamp, analysis, created_at)
            VALUES (?, ?, ?, ?)
        """, (symbol, now, json.dumps(analysis), now)):
            await self._connection_pool.commit()

        # Clean up old records (keep last 30 days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        async with self._connection_pool.execute("""
            DELETE FROM analysis_history WHERE timestamp < ?
        """, (cutoff,)):
            await self._connection_pool.commit()

        logger.debug(f"Saved analysis history for {symbol}")

    # Priority queue
    async def add_priority_item(self, symbol: str, reason: str, priority: str) -> None:
        """Add item to priority queue."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self._priority_queue.append({
                "symbol": symbol,
                "reason": reason,
                "priority": priority,
                "added_at": now
            })

            async with self._connection_pool.execute("""
                INSERT INTO priority_queue (symbol, reason, priority, added_at, status)
                VALUES (?, ?, ?, ?, 'pending')
            """, (symbol, reason, priority, now)):
                await self._connection_pool.commit()

    async def get_priority_items(self) -> List[Dict]:
        """Get items needing urgent attention."""
        async with self._lock:
            return self._priority_queue.copy()

    # Approval queue
    async def add_to_approval_queue(self, recommendation: Dict) -> None:
        """Add AI recommendation to user approval queue."""
        async with self._lock:
            symbol = recommendation.get("symbol", "")
            action = recommendation.get("action", "")
            now = datetime.now(timezone.utc).isoformat()

            # Check for duplicates
            for existing in self._approval_queue:
                existing_rec = existing.get("recommendation", {})
                if (existing.get("status") == "pending" and
                    existing_rec.get("symbol") == symbol and
                    existing_rec.get("action") == action):
                    logger.debug(f"Skipping duplicate recommendation for {symbol} {action}")
                    return

            # Add new recommendation
            rec_id = f"rec_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{symbol}_{action}"
            new_item = {
                "id": rec_id,
                "recommendation": recommendation,
                "status": "pending",
                "created_at": now,
                "updated_at": now
            }
            self._approval_queue.append(new_item)

            async with self._connection_pool.execute("""
                INSERT INTO approval_queue (id, recommendation, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, (rec_id, json.dumps(recommendation), "pending", now, now)):
                await self._connection_pool.commit()

    async def get_pending_approvals(self) -> List[Dict]:
        """Get recommendations awaiting user approval."""
        async with self._lock:
            # If no recommendations exist, add some sample ones for demo
            if not self._approval_queue:
                sample_recommendations = self._get_sample_recommendations()
                for rec in sample_recommendations:
                    await self.add_to_approval_queue(rec)

            return [item for item in self._approval_queue if item["status"] == "pending"]

    async def update_approval_status(self, recommendation_id: str, status: str, user_feedback: Optional[str] = None) -> bool:
        """Update approval status for a recommendation."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()

            for item in self._approval_queue:
                if item["id"] == recommendation_id:
                    item["status"] = status
                    item["updated_at"] = now
                    if user_feedback:
                        item["user_feedback"] = user_feedback

                    async with self._connection_pool.execute("""
                        UPDATE approval_queue
                        SET status = ?, updated_at = ?, user_feedback = ?
                        WHERE id = ?
                    """, (status, now, user_feedback, recommendation_id)):
                        await self._connection_pool.commit()

                    return True
            return False

    # Daily and weekly plans
    async def save_daily_plan(self, plan: Dict) -> None:
        """Save AI-generated daily work plan."""
        date = plan['date']
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO daily_plans (date, plan, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (date, json.dumps(plan), now, now)):
            await self._connection_pool.commit()

        logger.debug(f"Saved daily plan for {date}")

    async def load_daily_plan(self, date: str) -> Optional[Dict]:
        """Load daily plan for specific date."""
        async with self._connection_pool.execute("""
            SELECT plan FROM daily_plans WHERE date = ?
        """, (date,)) as cursor:
            row = await cursor.fetchone()
            return json.loads(row[0]) if row else None

    async def save_weekly_plan(self, plan: Dict) -> None:
        """Save AI-generated weekly work distribution plan."""
        async with self._lock:
            now = datetime.now(timezone.utc).isoformat()
            self._weekly_plan = plan

            async with self._connection_pool.execute("""
                INSERT OR REPLACE INTO weekly_plans (id, plan, created_at, updated_at)
                VALUES (1, ?, ?, ?)
            """, (json.dumps(plan), now, now)):
                await self._connection_pool.commit()

    async def load_weekly_plan(self) -> Optional[Dict]:
        """Load current weekly plan."""
        async with self._lock:
            return self._weekly_plan.copy() if self._weekly_plan else None

    # Learning insights
    async def save_learning_insights(self, insights: Dict) -> None:
        """Save AI learning insights."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT INTO learning_insights (insights, created_at)
            VALUES (?, ?)
        """, (json.dumps(insights), now)):
            await self._connection_pool.commit()

        # Keep last 50 insights
        async with self._connection_pool.execute("""
            DELETE FROM learning_insights
            WHERE id NOT IN (SELECT id FROM learning_insights ORDER BY created_at DESC LIMIT 50)
        """):
            await self._connection_pool.commit()

    async def get_learning_insights(self, limit: int = 10) -> List[Dict]:
        """Get recent learning insights."""
        async with self._connection_pool.execute("""
            SELECT insights FROM learning_insights ORDER BY created_at DESC LIMIT ?
        """, (limit,)) as cursor:
            return [json.loads(row[0]) async for row in cursor]

    # News and earnings data methods
    async def save_news_item(self, symbol: str, title: str, summary: str, content: str = None,
                           source: str = None, sentiment: str = "neutral", relevance_score: float = 0.5,
                           published_at: str = None, citations: List[str] = None) -> None:
        """Save news item to database."""
        now = datetime.now(timezone.utc).isoformat()
        published_at = published_at or now

        async with self._connection_pool.execute("""
            INSERT INTO news_items
            (symbol, title, summary, content, source, sentiment, relevance_score, published_at, fetched_at, citations, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, title, summary, content, source, sentiment, relevance_score,
            published_at, now, json.dumps(citations) if citations else None, now
        )):
            await self._connection_pool.commit()

        logger.debug(f"Saved news item for {symbol}: {title}")

    async def save_earnings_report(self, symbol: str, fiscal_period: str, report_date: str,
                                 eps_actual: float = None, eps_estimated: float = None,
                                 revenue_actual: float = None, revenue_estimated: float = None,
                                 guidance: str = None, next_earnings_date: str = None) -> None:
        """Save earnings report to database."""
        now = datetime.now(timezone.utc).isoformat()

        # Calculate surprise percentage if both actual and estimated are available
        surprise_pct = None
        if eps_actual is not None and eps_estimated is not None and eps_estimated != 0:
            surprise_pct = ((eps_actual - eps_estimated) / abs(eps_estimated)) * 100

        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO earnings_reports
            (symbol, fiscal_period, fiscal_year, fiscal_quarter, report_date, eps_actual, eps_estimated,
             revenue_actual, revenue_estimated, surprise_pct, guidance, next_earnings_date, fetched_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, fiscal_period,
            None, None,  # fiscal_year, fiscal_quarter (could be parsed from fiscal_period)
            report_date, eps_actual, eps_estimated, revenue_actual, revenue_estimated,
            surprise_pct, guidance, next_earnings_date, now, now
        )):
            await self._connection_pool.commit()

        logger.debug(f"Saved earnings report for {symbol}: {fiscal_period}")

    async def get_news_for_symbol(self, symbol: str, limit: int = 20) -> List[Dict]:
        """Get recent news for a specific symbol."""
        async with self._connection_pool.execute("""
            SELECT symbol, title, summary, content, source, sentiment, relevance_score,
                   published_at, fetched_at, citations, created_at
            FROM news_items
            WHERE symbol = ?
            ORDER BY published_at DESC
            LIMIT ?
        """, (symbol, limit)) as cursor:
            news_items = []
            async for row in cursor:
                item = {
                    "symbol": row[0],
                    "title": row[1],
                    "summary": row[2],
                    "content": row[3],
                    "source": row[4],
                    "sentiment": row[5],
                    "relevance_score": row[6],
                    "published_at": row[7],
                    "fetched_at": row[8],
                    "citations": json.loads(row[9]) if row[9] else None,
                    "created_at": row[10]
                }
                news_items.append(item)
            return news_items

    async def get_earnings_for_symbol(self, symbol: str, limit: int = 10) -> List[Dict]:
        """Get earnings reports for a specific symbol."""
        async with self._connection_pool.execute("""
            SELECT symbol, fiscal_period, fiscal_year, fiscal_quarter, report_date,
                   eps_actual, eps_estimated, revenue_actual, revenue_estimated,
                   surprise_pct, guidance, next_earnings_date, fetched_at, created_at
            FROM earnings_reports
            WHERE symbol = ?
            ORDER BY report_date DESC
            LIMIT ?
        """, (symbol, limit)) as cursor:
            earnings_reports = []
            async for row in cursor:
                report = {
                    "symbol": row[0],
                    "fiscal_period": row[1],
                    "fiscal_year": row[2],
                    "fiscal_quarter": row[3],
                    "report_date": row[4],
                    "eps_actual": row[5],
                    "eps_estimated": row[6],
                    "revenue_actual": row[7],
                    "revenue_estimated": row[8],
                    "surprise_pct": row[9],
                    "guidance": row[10],
                    "next_earnings_date": row[11],
                    "fetched_at": row[12],
                    "created_at": row[13]
                }
                earnings_reports.append(report)
            return earnings_reports

    async def get_upcoming_earnings(self, days_ahead: int = 30) -> List[Dict]:
        """Get upcoming earnings reports within specified days."""
        cutoff_date = (datetime.now(timezone.utc) + timedelta(days=days_ahead)).isoformat()

        async with self._connection_pool.execute("""
            SELECT symbol, fiscal_period, next_earnings_date, guidance
            FROM earnings_reports
            WHERE next_earnings_date IS NOT NULL
              AND next_earnings_date <= ?
              AND next_earnings_date >= ?
            ORDER BY next_earnings_date ASC
        """, (cutoff_date, datetime.now(timezone.utc).isoformat())) as cursor:
            upcoming = []
            async for row in cursor:
                upcoming.append({
                    "symbol": row[0],
                    "fiscal_period": row[1],
                    "next_earnings_date": row[2],
                    "guidance": row[3]
                })
            return upcoming

    # News fetch tracking methods
    async def get_last_news_fetch(self, symbol: str) -> Optional[str]:
        """Get the last news fetch timestamp for a symbol."""
        async with self._connection_pool.execute("""
            SELECT last_news_fetch FROM news_fetch_tracking WHERE symbol = ?
        """, (symbol,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def update_last_news_fetch(self, symbol: str, fetch_time: Optional[str] = None) -> None:
        """Update the last news fetch timestamp for a symbol."""
        if fetch_time is None:
            fetch_time = datetime.now(timezone.utc).isoformat()

        now = datetime.now(timezone.utc).isoformat()
        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO news_fetch_tracking (symbol, last_news_fetch, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (symbol, fetch_time, now, now)):
            await self._connection_pool.commit()

    async def get_last_earnings_fetch(self, symbol: str) -> Optional[str]:
        """Get the last earnings fetch timestamp for a symbol."""
        async with self._connection_pool.execute("""
            SELECT last_earnings_fetch FROM news_fetch_tracking WHERE symbol = ?
        """, (symbol,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def update_last_earnings_fetch(self, symbol: str, fetch_time: Optional[str] = None) -> None:
        """Update the last earnings fetch timestamp for a symbol."""
        if fetch_time is None:
            fetch_time = datetime.now(timezone.utc).isoformat()

        now = datetime.now(timezone.utc).isoformat()
        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO news_fetch_tracking (symbol, last_earnings_fetch, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (symbol, fetch_time, now, now)):
            await self._connection_pool.execute("""
                UPDATE news_fetch_tracking SET last_earnings_fetch = ?, updated_at = ? WHERE symbol = ?
            """, (fetch_time, now, symbol))
            await self._connection_pool.commit()

    async def get_last_news_fetch(self, symbol: str) -> Optional[str]:
        """Get the last news fetch timestamp for a symbol."""
        async with self._connection_pool.execute("""
            SELECT last_news_fetch FROM news_fetch_tracking WHERE symbol = ?
        """, (symbol,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def update_last_news_fetch(self, symbol: str, fetch_time: Optional[str] = None) -> None:
        """Update the last news fetch timestamp for a symbol."""
        now = datetime.now(timezone.utc).isoformat()
        fetch_time = fetch_time or now

        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO news_fetch_tracking
            (symbol, last_news_fetch, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (symbol, fetch_time, now, now)):
            await self._connection_pool.commit()

    async def get_last_earnings_fetch(self, symbol: str) -> Optional[str]:
        """Get the last earnings fetch timestamp for a symbol."""
        async with self._connection_pool.execute("""
            SELECT last_earnings_fetch FROM news_fetch_tracking WHERE symbol = ?
        """, (symbol,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def update_last_earnings_fetch(self, symbol: str, fetch_time: Optional[str] = None) -> None:
        """Update the last earnings fetch timestamp for a symbol."""
        now = datetime.now(timezone.utc).isoformat()
        fetch_time = fetch_time or now

        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO news_fetch_tracking
            (symbol, last_earnings_fetch, created_at, updated_at)
            VALUES (?, ?, ?, ?)
        """, (symbol, fetch_time, now, now)):
            await self._connection_pool.commit()

    # Data cleanup methods
    async def cleanup_old_data(self) -> None:
        """Clean up old news and earnings data."""
        now = datetime.now(timezone.utc)
        news_cutoff = (now - timedelta(days=90)).isoformat()  # Keep 90 days of news
        earnings_cutoff = (now - timedelta(days=365)).isoformat()  # Keep 1 year of earnings

        # Clean up old news
        async with self._connection_pool.execute("""
            DELETE FROM news_items WHERE published_at < ?
        """, (news_cutoff,)):
            news_deleted = self._connection_pool.total_changes

        # Clean up old earnings
        async with self._connection_pool.execute("""
            DELETE FROM earnings_reports WHERE report_date < ?
        """, (earnings_cutoff,)):
            earnings_deleted = self._connection_pool.total_changes

        if news_deleted > 0 or earnings_deleted > 0:
            logger.info(f"Cleaned up {news_deleted} old news items and {earnings_deleted} old earnings reports")

    # Checkpoints
    async def create_checkpoint(self, name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Create a checkpoint of current state."""
        async with self._lock:
            timestamp = datetime.now(timezone.utc).isoformat()
            checkpoint_id = f"checkpoint_{int(datetime.now(timezone.utc).timestamp() * 1000)}"

            checkpoint_data = {
                "id": checkpoint_id,
                "name": name,
                "timestamp": timestamp,
                "metadata": metadata or {},
                "portfolio": self._portfolio.to_dict() if self._portfolio else None,
                "intents": {k: v.to_dict() for k, v in self._intents.items()}
            }

            async with self._connection_pool.execute("""
                INSERT INTO checkpoints (id, name, timestamp, metadata, portfolio, intents, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                checkpoint_id,
                name,
                timestamp,
                json.dumps(metadata or {}),
                json.dumps(checkpoint_data["portfolio"]),
                json.dumps(checkpoint_data["intents"]),
                timestamp
            )):
                await self._connection_pool.commit()

            logger.info(f"Created checkpoint {checkpoint_id}: {name}")
            return checkpoint_id

    async def restore_checkpoint(self, checkpoint_id: str) -> bool:
        """Restore state from checkpoint."""
        async with self._lock:
            async with self._connection_pool.execute("""
                SELECT portfolio, intents FROM checkpoints WHERE id = ?
            """, (checkpoint_id,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    logger.error(f"Checkpoint {checkpoint_id} not found")
                    return False

                # Restore portfolio
                portfolio_data = json.loads(row[0])
                if portfolio_data:
                    self._portfolio = PortfolioState.from_dict(portfolio_data)

                # Restore intents
                intents_data = json.loads(row[1])
                self._intents = {}
                for intent_id, intent_data in intents_data.items():
                    self._intents[intent_id] = Intent.from_dict(intent_data)

                # Save restored state
                if self._portfolio:
                    await self.update_portfolio(self._portfolio)

                logger.info(f"Restored checkpoint {checkpoint_id}")
                return True

    # Fundamental Analysis methods
    async def save_fundamental_analysis(self, analysis: FundamentalAnalysis) -> int:
        """Save fundamental analysis results."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO fundamental_analysis
            (symbol, analysis_date, pe_ratio, pb_ratio, roe, roa, debt_to_equity, current_ratio,
             profit_margins, revenue_growth, earnings_growth, dividend_yield, market_cap,
             sector_pe, industry_rank, overall_score, recommendation, analysis_data, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            analysis.symbol, analysis.analysis_date, analysis.pe_ratio, analysis.pb_ratio,
            analysis.roe, analysis.roa, analysis.debt_to_equity, analysis.current_ratio,
            analysis.profit_margins, analysis.revenue_growth, analysis.earnings_growth,
            analysis.dividend_yield, analysis.market_cap, analysis.sector_pe, analysis.industry_rank,
            analysis.overall_score, analysis.recommendation,
            json.dumps(analysis.analysis_data) if analysis.analysis_data else None,
            now, now
        )) as cursor:
            await self._connection_pool.commit()
            analysis_id = cursor.lastrowid
            logger.debug(f"Saved fundamental analysis for {analysis.symbol}")
            return analysis_id

    async def get_fundamental_analysis(self, symbol: str, limit: int = 1) -> List[FundamentalAnalysis]:
        """Get fundamental analysis for a symbol."""
        async with self._connection_pool.execute("""
            SELECT symbol, analysis_date, pe_ratio, pb_ratio, roe, roa, debt_to_equity, current_ratio,
                   profit_margins, revenue_growth, earnings_growth, dividend_yield, market_cap,
                   sector_pe, industry_rank, overall_score, recommendation, analysis_data
            FROM fundamental_analysis
            WHERE symbol = ?
            ORDER BY analysis_date DESC
            LIMIT ?
        """, (symbol, limit)) as cursor:
            analyses = []
            async for row in cursor:
                analysis_data = {
                    "symbol": row[0],
                    "analysis_date": row[1],
                    "pe_ratio": row[2],
                    "pb_ratio": row[3],
                    "roe": row[4],
                    "roa": row[5],
                    "debt_to_equity": row[6],
                    "current_ratio": row[7],
                    "profit_margins": row[8],
                    "revenue_growth": row[9],
                    "earnings_growth": row[10],
                    "dividend_yield": row[11],
                    "market_cap": row[12],
                    "sector_pe": row[13],
                    "industry_rank": row[14],
                    "overall_score": row[15],
                    "recommendation": row[16],
                    "analysis_data": json.loads(row[17]) if row[17] else None
                }
                analyses.append(FundamentalAnalysis.from_dict(analysis_data))
            return analyses

    # Recommendation methods
    async def save_recommendation(self, recommendation: Recommendation) -> int:
        """Save trading recommendation."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT INTO recommendations
            (symbol, recommendation_type, confidence_score, target_price, stop_loss, quantity,
             reasoning, analysis_type, time_horizon, risk_level, potential_impact,
             alternative_suggestions, created_at, executed_at, outcome, actual_return)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recommendation.symbol, recommendation.recommendation_type, recommendation.confidence_score,
            recommendation.target_price, recommendation.stop_loss, recommendation.quantity,
            recommendation.reasoning, recommendation.analysis_type, recommendation.time_horizon,
            recommendation.risk_level, recommendation.potential_impact,
            json.dumps(recommendation.alternative_suggestions) if recommendation.alternative_suggestions else None,
            now, recommendation.executed_at, recommendation.outcome, recommendation.actual_return
        )) as cursor:
            await self._connection_pool.commit()
            rec_id = cursor.lastrowid
            logger.debug(f"Saved recommendation for {recommendation.symbol}: {recommendation.recommendation_type}")
            return rec_id

    async def get_recommendations(self, symbol: Optional[str] = None, limit: int = 20) -> List[Recommendation]:
        """Get recommendations, optionally filtered by symbol."""
        query = """
            SELECT id, symbol, recommendation_type, confidence_score, target_price, stop_loss, quantity,
                   reasoning, analysis_type, time_horizon, risk_level, potential_impact,
                   alternative_suggestions, created_at, executed_at, outcome, actual_return
            FROM recommendations
        """
        params = []

        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        async with self._connection_pool.execute(query, params) as cursor:
            recommendations = []
            async for row in cursor:
                rec_data = {
                    "recommendation_id": row[0],  # Include ID for tracking
                    "symbol": row[1],
                    "recommendation_type": row[2],
                    "confidence_score": row[3],
                    "target_price": row[4],
                    "stop_loss": row[5],
                    "quantity": row[6],
                    "reasoning": row[7],
                    "analysis_type": row[8],
                    "time_horizon": row[9],
                    "risk_level": row[10],
                    "potential_impact": row[11],
                    "alternative_suggestions": json.loads(row[12]) if row[12] else None,
                    "executed_at": row[13],
                    "outcome": row[14],
                    "actual_return": row[15]
                }
                recommendations.append(Recommendation.from_dict(rec_data))
            return recommendations

    async def get_all_recommendations(self, limit: int = 100) -> List[Recommendation]:
        """Get all recommendations across all symbols."""
        return await self.get_recommendations(symbol=None, limit=limit)

    async def update_recommendation_outcome(self, recommendation_id: int, outcome: str,
                                          actual_return: Optional[float] = None) -> bool:
        """Update recommendation outcome after execution."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            UPDATE recommendations
            SET executed_at = ?, outcome = ?, actual_return = ?
            WHERE id = ?
        """, (now, outcome, actual_return, recommendation_id)):
            await self._connection_pool.commit()
            return self._connection_pool.total_changes > 0

    # Market Conditions methods
    async def save_market_conditions(self, conditions: MarketConditions) -> int:
        """Save market conditions data."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT OR REPLACE INTO market_conditions
            (date, vix_index, nifty_50_level, market_sentiment, interest_rates,
             inflation_rate, gdp_growth, sector_performance, global_events, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            conditions.date, conditions.vix_index, conditions.nifty_50_level,
            conditions.market_sentiment, conditions.interest_rates, conditions.inflation_rate,
            conditions.gdp_growth,
            json.dumps(conditions.sector_performance) if conditions.sector_performance else None,
            json.dumps(conditions.global_events) if conditions.global_events else None,
            now
        )) as cursor:
            await self._connection_pool.commit()
            conditions_id = cursor.lastrowid
            logger.debug(f"Saved market conditions for {conditions.date}")
            return conditions_id

    async def get_market_conditions(self, limit: int = 30) -> List[MarketConditions]:
        """Get recent market conditions."""
        async with self._connection_pool.execute("""
            SELECT date, vix_index, nifty_50_level, market_sentiment, interest_rates,
                   inflation_rate, gdp_growth, sector_performance, global_events
            FROM market_conditions
            ORDER BY date DESC
            LIMIT ?
        """, (limit,)) as cursor:
            conditions = []
            async for row in cursor:
                cond_data = {
                    "date": row[0],
                    "vix_index": row[1],
                    "nifty_50_level": row[2],
                    "market_sentiment": row[3],
                    "interest_rates": row[4],
                    "inflation_rate": row[5],
                    "gdp_growth": row[6],
                    "sector_performance": json.loads(row[7]) if row[7] else None,
                    "global_events": json.loads(row[8]) if row[8] else None
                }
                conditions.append(MarketConditions.from_dict(cond_data))
            return conditions

    # Analysis Performance methods
    async def save_analysis_performance(self, performance: AnalysisPerformance) -> int:
        """Save analysis performance tracking."""
        now = datetime.now(timezone.utc).isoformat()

        async with self._connection_pool.execute("""
            INSERT INTO analysis_performance
            (symbol, recommendation_id, prediction_date, execution_date, predicted_direction,
             actual_direction, predicted_return, actual_return, accuracy_score, model_version, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            performance.symbol, performance.recommendation_id, performance.prediction_date,
            performance.execution_date, performance.predicted_direction, performance.actual_direction,
            performance.predicted_return, performance.actual_return, performance.accuracy_score,
            performance.model_version, now
        )) as cursor:
            await self._connection_pool.commit()
            perf_id = cursor.lastrowid
            logger.debug(f"Saved analysis performance for {performance.symbol}")
            return perf_id

    async def get_analysis_performance(self, symbol: Optional[str] = None, limit: int = 50) -> List[AnalysisPerformance]:
        """Get analysis performance records."""
        query = """
            SELECT symbol, recommendation_id, prediction_date, execution_date, predicted_direction,
                   actual_direction, predicted_return, actual_return, accuracy_score, model_version
            FROM analysis_performance
        """
        params = []

        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)

        query += " ORDER BY prediction_date DESC LIMIT ?"
        params.append(limit)

        async with self._connection_pool.execute(query, params) as cursor:
            performances = []
            async for row in cursor:
                perf_data = {
                    "symbol": row[0],
                    "recommendation_id": row[1],
                    "prediction_date": row[2],
                    "execution_date": row[3],
                    "predicted_direction": row[4],
                    "actual_direction": row[5],
                    "predicted_return": row[6],
                    "actual_return": row[7],
                    "accuracy_score": row[8],
                    "model_version": row[9]
                }
                performances.append(AnalysisPerformance.from_dict(perf_data))
            return performances

    async def get_performance_stats(self, symbol: Optional[str] = None) -> Dict[str, Any]:
        """Get performance statistics."""
        query = """
            SELECT
                COUNT(*) as total_predictions,
                AVG(accuracy_score) as avg_accuracy,
                SUM(CASE WHEN accuracy_score >= 0.7 THEN 1 ELSE 0 END) as accurate_predictions,
                AVG(predicted_return) as avg_predicted_return,
                AVG(actual_return) as avg_actual_return
            FROM analysis_performance
        """
        params = []

        if symbol:
            query += " WHERE symbol = ?"
            params.append(symbol)

        async with self._connection_pool.execute(query, params) as cursor:
            row = await cursor.fetchone()
            if row:
                return {
                    "total_predictions": row[0],
                    "avg_accuracy": row[1],
                    "accurate_predictions": row[2],
                    "accuracy_rate": row[2] / row[0] if row[0] > 0 else 0,
                    "avg_predicted_return": row[3],
                    "avg_actual_return": row[4]
                }
            return {}

    async def close(self) -> None:
        """Close database connections."""
        if self._connection_pool:
            await self._connection_pool.close()
            self._connection_pool = None

    def _get_sample_recommendations(self) -> List[Dict]:
        """Get sample AI recommendations for demo purposes."""
        # Same as in the original state.py
        return [
            {
                "symbol": "AARTIIND",
                "action": "SELL",
                "confidence": 78,
                "reasoning": "Stock has declined 21.8% from purchase price. Fundamentals show deteriorating margins and high valuation (P/E 24.5 vs industry 18.2). Recent quarterly results missed expectations with revenue down 6%.",
                "analysis_type": "fundamental_analysis",
                "current_price": 377.85,
                "target_price": None,
                "stop_loss": 350.0,
                "quantity": 50,
                "potential_impact": "Free up ₹18,893 for better opportunities",
                "risk_level": "medium",
                "time_horizon": "immediate",
                "alternative_suggestions": ["Consider switching to APOLLOHOSP or DRREDDY in healthcare sector"]
            },
            # ... other sample recommendations (truncated for brevity)
        ]