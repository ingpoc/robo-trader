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
    ExecutionReport, Intent
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
        """

        async with self._connection_pool.executescript(schema):
            pass

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