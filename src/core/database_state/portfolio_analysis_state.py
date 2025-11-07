"""
Portfolio Analysis State Management.

Manages all portfolio analysis workflow data with proper locking.
Separate from paper trading workflow to maintain data isolation.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.database_state.base import BaseState


class PortfolioAnalysisState(BaseState):
    """
    Manages portfolio analysis workflow data.

    Handles:
    - Portfolio intelligence analysis results
    - Prompt templates and optimization history
    - Data quality metrics and improvements
    - Analysis performance tracking
    """

    def __init__(self, db_connection):
        super().__init__(db_connection)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Initialize portfolio analysis tables."""
        async with self._lock:
            schema = """
            -- Portfolio Analysis Results
            CREATE TABLE IF NOT EXISTS portfolio_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                analysis_date TEXT NOT NULL,
                analysis_type TEXT NOT NULL,  -- 'intelligence', 'data_quality', 'prompt_optimization'
                analysis_data TEXT NOT NULL,  -- JSON blob
                prompt_template_id TEXT,
                data_quality_score REAL,
                confidence_score REAL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(symbol, analysis_date, analysis_type)
            );

            -- Prompt Templates for Portfolio Analysis
            CREATE TABLE IF NOT EXISTS portfolio_prompt_templates (
                id TEXT PRIMARY KEY,
                template_name TEXT NOT NULL,
                template_type TEXT NOT NULL,  -- 'news', 'earnings', 'fundamentals'
                template_content TEXT NOT NULL,
                variables TEXT DEFAULT '{}',  -- JSON blob of template variables
                is_active BOOLEAN DEFAULT TRUE,
                version INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Prompt Optimization History
            CREATE TABLE IF NOT EXISTS prompt_optimization_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                template_id TEXT NOT NULL,
                optimization_date TEXT NOT NULL,
                old_template_content TEXT NOT NULL,
                new_template_content TEXT NOT NULL,
                optimization_reason TEXT NOT NULL,
                quality_improvement_score REAL,
                test_results TEXT,  -- JSON blob
                created_at TEXT NOT NULL,
                FOREIGN KEY (template_id) REFERENCES portfolio_prompt_templates(id)
            );

            -- Data Quality Tracking
            CREATE TABLE IF NOT EXISTS data_quality_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                data_type TEXT NOT NULL,  -- 'news', 'earnings', 'fundamentals'
                quality_date TEXT NOT NULL,
                quality_score REAL NOT NULL,
                issues_detected TEXT,  -- JSON blob
                improvements_made TEXT,  -- JSON blob
                prompt_template_id TEXT,
                created_at TEXT NOT NULL,
                UNIQUE(symbol, data_type, quality_date)
            );

            -- Analysis Performance Tracking
            CREATE TABLE IF NOT EXISTS analysis_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_date TEXT NOT NULL,
                symbols_analyzed INTEGER NOT NULL,
                avg_quality_score REAL,
                avg_confidence_score REAL,
                total_analysis_time_ms INTEGER,
                optimization_suggestions TEXT,  -- JSON blob
                created_at TEXT NOT NULL
            );

            -- Hook Events Audit Trail (for transparency and debugging)
            CREATE TABLE IF NOT EXISTS audit_hook_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                analysis_id TEXT NOT NULL,
                event_type TEXT NOT NULL,  -- 'PreToolUse', 'PostToolUse', 'Stop'
                tool_name TEXT,
                tool_input TEXT,  -- JSON blob
                tool_output TEXT,
                error TEXT,
                reason TEXT,
                event_timestamp REAL NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (analysis_id) REFERENCES portfolio_analysis(id)
            );

            -- Analysis Checkpoints (for crash recovery and resume)
            CREATE TABLE IF NOT EXISTS analysis_checkpoints (
                id TEXT PRIMARY KEY,
                analysis_id TEXT NOT NULL,
                session_id TEXT,
                checkpoint_type TEXT NOT NULL,  -- 'progress', 'completion', 'failure'
                stocks_completed TEXT NOT NULL,  -- JSON array of completed symbols
                stocks_pending TEXT NOT NULL,     -- JSON array of pending symbols
                stocks_total INTEGER NOT NULL,
                checkpoint_data TEXT,             -- JSON blob with additional state
                checkpoint_timestamp REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            -- Indexes for performance
            CREATE INDEX IF NOT EXISTS idx_portfolio_analysis_symbol ON portfolio_analysis(symbol);
            CREATE INDEX IF NOT EXISTS idx_portfolio_analysis_date ON portfolio_analysis(analysis_date DESC);
            CREATE INDEX IF NOT EXISTS idx_portfolio_analysis_type ON portfolio_analysis(analysis_type);
            CREATE INDEX IF NOT EXISTS idx_prompt_templates_type ON portfolio_prompt_templates(template_type);
            CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON portfolio_prompt_templates(is_active);
            CREATE INDEX IF NOT EXISTS idx_optimization_history_date ON prompt_optimization_history(optimization_date DESC);
            CREATE INDEX IF NOT EXISTS idx_data_quality_symbol ON data_quality_metrics(symbol);
            CREATE INDEX IF NOT EXISTS idx_data_quality_date ON data_quality_metrics(quality_date DESC);
            CREATE INDEX IF NOT EXISTS idx_analysis_performance_date ON analysis_performance(analysis_date DESC);
            CREATE INDEX IF NOT EXISTS idx_audit_hook_events_analysis_id ON audit_hook_events(analysis_id);
            CREATE INDEX IF NOT EXISTS idx_audit_hook_events_type ON audit_hook_events(event_type);
            CREATE INDEX IF NOT EXISTS idx_audit_hook_events_timestamp ON audit_hook_events(event_timestamp DESC);
            CREATE INDEX IF NOT EXISTS idx_analysis_checkpoints_analysis_id ON analysis_checkpoints(analysis_id);
            CREATE INDEX IF NOT EXISTS idx_analysis_checkpoints_type ON analysis_checkpoints(checkpoint_type);
            CREATE INDEX IF NOT EXISTS idx_analysis_checkpoints_timestamp ON analysis_checkpoints(checkpoint_timestamp DESC);
            """

            try:
                await self.db.connection.executescript(schema)
                await self.db.connection.commit()
                logger.info("Portfolio analysis tables initialized successfully")

                # Initialize default prompt templates
                await self._initialize_default_prompt_templates()

            except Exception as e:
                logger.error(f"Failed to initialize portfolio analysis tables: {e}")
                raise

    async def _initialize_default_prompt_templates(self) -> None:
        """Initialize default prompt templates for portfolio analysis."""
        default_templates = [
            {
                "id": "portfolio_news_default_v1",
                "name": "Portfolio News Analysis",
                "type": "news",
                "content": """Analyze the following news for {symbol} and provide investment insights:

News: {news_content}
Date: {news_date}
Source: {news_source}

Focus on:
1. Business impact assessment
2. Financial implications
3. Market sentiment analysis
4. Recommendation implications

Provide structured analysis with clear reasoning.""",
                "variables": '{"symbol": "string", "news_content": "text", "news_date": "string", "news_source": "string"}'
            },
            {
                "id": "portfolio_earnings_default_v1",
                "name": "Portfolio Earnings Analysis",
                "type": "earnings",
                "content": """Analyze {symbol}'s earnings report for {fiscal_period}:

Revenue: {revenue}
EPS: {eps}
Growth: {revenue_growth}
Guidance: {guidance}

Key analysis points:
1. Earnings quality assessment
2. Growth trajectory analysis
3. Competitive positioning
4. Future outlook evaluation

Provide investment recommendation with confidence score.""",
                "variables": '{"symbol": "string", "fiscal_period": "string", "revenue": "string", "eps": "string", "revenue_growth": "string", "guidance": "string"}'
            },
            {
                "id": "portfolio_fundamentals_default_v1",
                "name": "Portfolio Fundamentals Analysis",
                "type": "fundamentals",
                "content": """Fundamental analysis for {symbol}:

Financial Metrics:
- P/E Ratio: {pe_ratio}
- P/B Ratio: {pb_ratio}
- ROE: {roe}
- Debt/Equity: {debt_equity}
- Current Ratio: {current_ratio}

Business Analysis:
1. Financial health assessment
2. Valuation analysis
3. Competitive advantages
4. Management effectiveness
5. Industry position

Provide comprehensive investment recommendation.""",
                "variables": '{"symbol": "string", "pe_ratio": "string", "pb_ratio": "string", "roe": "string", "debt_equity": "string", "current_ratio": "string"}'
            }
        ]

        current_time = datetime.now(timezone.utc).isoformat()

        for template in default_templates:
            # Check if template already exists
            cursor = await self.db.connection.execute(
                "SELECT id FROM portfolio_prompt_templates WHERE id = ?",
                (template["id"],)
            )
            if not await cursor.fetchone():
                await self.db.connection.execute(
                    """INSERT INTO portfolio_prompt_templates
                       (id, template_name, template_type, template_content, variables, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (template["id"], template["name"], template["type"],
                     template["content"], template["variables"],
                     current_time, current_time)
                )

        await self.db.connection.commit()
        logger.info("Default portfolio prompt templates initialized")

    # ===== Portfolio Analysis Operations =====
    async def store_analysis(self, symbol: str, analysis_type: str, analysis_data: Dict[str, Any],
                           prompt_template_id: Optional[str] = None,
                           data_quality_score: Optional[float] = None,
                           confidence_score: Optional[float] = None) -> bool:
        """Store portfolio analysis result."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()
                analysis_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                await self.db.connection.execute(
                    """INSERT OR REPLACE INTO portfolio_analysis
                       (symbol, analysis_date, analysis_type, analysis_data,
                        prompt_template_id, data_quality_score, confidence_score,
                        created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, analysis_date, analysis_type, json.dumps(analysis_data),
                     prompt_template_id, data_quality_score, confidence_score,
                     current_time, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store portfolio analysis for {symbol}: {e}")
                return False

    async def get_analysis(self, symbol: str, analysis_type: str,
                          analysis_date: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get portfolio analysis for a symbol."""
        async with self._lock:
            try:
                if analysis_date is None:
                    analysis_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                cursor = await self.db.connection.execute(
                    """SELECT analysis_data, prompt_template_id, data_quality_score, confidence_score
                       FROM portfolio_analysis
                       WHERE symbol = ? AND analysis_type = ? AND analysis_date = ?
                       ORDER BY created_at DESC
                       LIMIT 1""",
                    (symbol, analysis_type, analysis_date)
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "analysis_data": json.loads(row[0]) if row[0] else {},
                        "prompt_template_id": row[1],
                        "data_quality_score": row[2],
                        "confidence_score": row[3]
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get portfolio analysis for {symbol}: {e}")
                return None

    async def get_recent_analyses(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent portfolio analyses."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT symbol, analysis_type, analysis_data, data_quality_score,
                          confidence_score, created_at
                       FROM portfolio_analysis
                       ORDER BY created_at DESC
                       LIMIT ?""",
                    (limit,)
                )
                rows = await cursor.fetchall()

                analyses = []
                for row in rows:
                    analyses.append({
                        "symbol": row[0],
                        "analysis_type": row[1],
                        "analysis_data": json.loads(row[2]) if row[2] else {},
                        "data_quality_score": row[3],
                        "confidence_score": row[4],
                        "created_at": row[5]
                    })
                return analyses

            except Exception as e:
                logger.error(f"Failed to get recent portfolio analyses: {e}")
                return []

    # ===== Prompt Template Operations =====
    async def get_prompt_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get prompt template by ID."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, template_name, template_type, template_content,
                          variables, is_active, version, created_at, updated_at
                       FROM portfolio_prompt_templates
                       WHERE id = ?""",
                    (template_id,)
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "content": row[3],
                        "variables": json.loads(row[4]) if row[4] else {},
                        "is_active": row[5],
                        "version": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get prompt template {template_id}: {e}")
                return None

    async def get_active_prompt_templates(self, template_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all active prompt templates, optionally filtered by type."""
        async with self._lock:
            try:
                query = """
                    SELECT id, template_name, template_type, template_content,
                          variables, is_active, version, created_at, updated_at
                    FROM portfolio_prompt_templates
                    WHERE is_active = TRUE
                """
                params = []

                if template_type:
                    query += " AND template_type = ?"
                    params.append(template_type)

                query += " ORDER BY template_type, version DESC"

                cursor = await self.db.connection.execute(query, params)
                rows = await cursor.fetchall()

                templates = []
                for row in rows:
                    templates.append({
                        "id": row[0],
                        "name": row[1],
                        "type": row[2],
                        "content": row[3],
                        "variables": json.loads(row[4]) if row[4] else {},
                        "is_active": row[5],
                        "version": row[6],
                        "created_at": row[7],
                        "updated_at": row[8]
                    })
                return templates

            except Exception as e:
                logger.error(f"Failed to get active prompt templates: {e}")
                return []

    # ===== Data Quality Operations =====
    async def store_data_quality_metrics(self, symbol: str, data_type: str,
                                        quality_score: float, issues_detected: List[str],
                                        improvements_made: List[str],
                                        prompt_template_id: Optional[str] = None) -> bool:
        """Store data quality metrics for analysis."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()
                quality_date = datetime.now(timezone.utc).strftime('%Y-%m-%d')

                await self.db.connection.execute(
                    """INSERT OR REPLACE INTO data_quality_metrics
                       (symbol, data_type, quality_date, quality_score,
                        issues_detected, improvements_made, prompt_template_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (symbol, data_type, quality_date, quality_score,
                     json.dumps(issues_detected), json.dumps(improvements_made),
                     prompt_template_id, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store data quality metrics for {symbol}: {e}")
                return False

    async def get_data_quality_metrics(self, symbol: str, data_type: Optional[str] = None,
                                     days_back: int = 30) -> List[Dict[str, Any]]:
        """Get data quality metrics for a symbol."""
        async with self._lock:
            try:
                query = """
                    SELECT data_type, quality_date, quality_score, issues_detected,
                          improvements_made, prompt_template_id, created_at
                    FROM data_quality_metrics
                    WHERE symbol = ? AND quality_date >= date('now', '-{} days')
                """.format(days_back)

                params = [symbol]

                if data_type:
                    query += " AND data_type = ?"
                    params.append(data_type)

                query += " ORDER BY quality_date DESC"

                cursor = await self.db.connection.execute(query, params)
                rows = await cursor.fetchall()

                metrics = []
                for row in rows:
                    metrics.append({
                        "data_type": row[0],
                        "quality_date": row[1],
                        "quality_score": row[2],
                        "issues_detected": json.loads(row[3]) if row[3] else [],
                        "improvements_made": json.loads(row[4]) if row[4] else [],
                        "prompt_template_id": row[5],
                        "created_at": row[6]
                    })
                return metrics

            except Exception as e:
                logger.error(f"Failed to get data quality metrics for {symbol}: {e}")
                return []

    # ===== Analysis Performance Operations =====
    async def store_analysis_performance(self, analysis_date: str, symbols_analyzed: int,
                                        avg_quality_score: Optional[float],
                                        avg_confidence_score: Optional[float],
                                        total_analysis_time_ms: int,
                                        optimization_suggestions: List[str]) -> bool:
        """Store daily analysis performance metrics."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """INSERT OR REPLACE INTO analysis_performance
                       (analysis_date, symbols_analyzed, avg_quality_score,
                        avg_confidence_score, total_analysis_time_ms,
                        optimization_suggestions, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (analysis_date, symbols_analyzed, avg_quality_score,
                     avg_confidence_score, total_analysis_time_ms,
                     json.dumps(optimization_suggestions), current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store analysis performance for {analysis_date}: {e}")
                return False

    async def get_analysis_performance(self, days_back: int = 30) -> List[Dict[str, Any]]:
        """Get analysis performance metrics."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT analysis_date, symbols_analyzed, avg_quality_score,
                          avg_confidence_score, total_analysis_time_ms,
                          optimization_suggestions, created_at
                       FROM analysis_performance
                       WHERE analysis_date >= date('now', '-{} days')
                       ORDER BY analysis_date DESC
                    """.format(days_back)
                )
                rows = await cursor.fetchall()

                performance = []
                for row in rows:
                    performance.append({
                        "analysis_date": row[0],
                        "symbols_analyzed": row[1],
                        "avg_quality_score": row[2],
                        "avg_confidence_score": row[3],
                        "total_analysis_time_ms": row[4],
                        "optimization_suggestions": json.loads(row[5]) if row[5] else [],
                        "created_at": row[6]
                    })
                return performance

            except Exception as e:
                logger.error(f"Failed to get analysis performance: {e}")
                return []

    # ===== Hook Events Audit Trail Operations =====
    async def store_hook_event(self, analysis_id: str, event_type: str,
                               tool_name: Optional[str] = None,
                               tool_input: Optional[Dict[str, Any]] = None,
                               tool_output: Optional[str] = None,
                               error: Optional[str] = None,
                               reason: Optional[str] = None,
                               event_timestamp: Optional[float] = None) -> bool:
        """Store a hook event for transparency and debugging."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()
                if event_timestamp is None:
                    event_timestamp = datetime.now(timezone.utc).timestamp()

                await self.db.connection.execute(
                    """INSERT INTO audit_hook_events
                       (analysis_id, event_type, tool_name, tool_input, tool_output,
                        error, reason, event_timestamp, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (analysis_id, event_type, tool_name,
                     json.dumps(tool_input) if tool_input else None,
                     tool_output, error, reason, event_timestamp, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store hook event for analysis {analysis_id}: {e}")
                return False

    async def store_hook_events_batch(self, analysis_id: str, events: List[Dict[str, Any]]) -> bool:
        """Store multiple hook events in a batch."""
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                for event in events:
                    await self.db.connection.execute(
                        """INSERT INTO audit_hook_events
                           (analysis_id, event_type, tool_name, tool_input, tool_output,
                            error, reason, event_timestamp, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (analysis_id, event.get("event_type"), event.get("tool_name"),
                         json.dumps(event.get("tool_input")) if event.get("tool_input") else None,
                         event.get("tool_output"), event.get("error"),
                         event.get("reason"), event.get("timestamp", datetime.now(timezone.utc).timestamp()),
                         current_time)
                    )

                await self.db.connection.commit()
                logger.info(f"Stored {len(events)} hook events for analysis {analysis_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to store hook events batch for analysis {analysis_id}: {e}")
                return False

    async def get_hook_events(self, analysis_id: str) -> List[Dict[str, Any]]:
        """Get hook events for an analysis."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT event_type, tool_name, tool_input, tool_output,
                          error, reason, event_timestamp, created_at
                       FROM audit_hook_events
                       WHERE analysis_id = ?
                       ORDER BY event_timestamp ASC""",
                    (analysis_id,)
                )
                rows = await cursor.fetchall()

                events = []
                for row in rows:
                    events.append({
                        "event_type": row[0],
                        "tool_name": row[1],
                        "tool_input": json.loads(row[2]) if row[2] else None,
                        "tool_output": row[3],
                        "error": row[4],
                        "reason": row[5],
                        "event_timestamp": row[6],
                        "created_at": row[7]
                    })
                return events

            except Exception as e:
                logger.error(f"Failed to get hook events for analysis {analysis_id}: {e}")
                return []

    # ===== Checkpoint Operations (for crash recovery) =====
    async def create_checkpoint(self, analysis_id: str, checkpoint_type: str,
                               stocks_completed: List[str], stocks_pending: List[str],
                               session_id: Optional[str] = None,
                               checkpoint_data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Create a checkpoint for analysis progress."""
        async with self._lock:
            try:
                import uuid
                checkpoint_id = f"checkpoint_{uuid.uuid4().hex[:12]}"
                current_time = datetime.now(timezone.utc).isoformat()
                checkpoint_timestamp = datetime.now(timezone.utc).timestamp()

                await self.db.connection.execute(
                    """INSERT INTO analysis_checkpoints
                       (id, analysis_id, session_id, checkpoint_type, stocks_completed,
                        stocks_pending, stocks_total, checkpoint_data, checkpoint_timestamp, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (checkpoint_id, analysis_id, session_id, checkpoint_type,
                     json.dumps(stocks_completed), json.dumps(stocks_pending),
                     len(stocks_completed) + len(stocks_pending),
                     json.dumps(checkpoint_data) if checkpoint_data else None,
                     checkpoint_timestamp, current_time)
                )

                await self.db.connection.commit()
                logger.info(f"Created {checkpoint_type} checkpoint for analysis {analysis_id}: {len(stocks_completed)} completed, {len(stocks_pending)} pending")
                return checkpoint_id

            except Exception as e:
                logger.error(f"Failed to create checkpoint for analysis {analysis_id}: {e}")
                return None

    async def get_latest_checkpoint(self, analysis_id: str) -> Optional[Dict[str, Any]]:
        """Get the most recent checkpoint for an analysis."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, session_id, checkpoint_type, stocks_completed, stocks_pending,
                          stocks_total, checkpoint_data, checkpoint_timestamp, created_at
                       FROM analysis_checkpoints
                       WHERE analysis_id = ?
                       ORDER BY checkpoint_timestamp DESC
                       LIMIT 1""",
                    (analysis_id,)
                )
                row = await cursor.fetchone()

                if row:
                    return {
                        "checkpoint_id": row[0],
                        "session_id": row[1],
                        "checkpoint_type": row[2],
                        "stocks_completed": json.loads(row[3]) if row[3] else [],
                        "stocks_pending": json.loads(row[4]) if row[4] else [],
                        "stocks_total": row[5],
                        "checkpoint_data": json.loads(row[6]) if row[6] else {},
                        "checkpoint_timestamp": row[7],
                        "created_at": row[8]
                    }
                return None

            except Exception as e:
                logger.error(f"Failed to get latest checkpoint for analysis {analysis_id}: {e}")
                return None

    async def get_checkpoints(self, analysis_id: str) -> List[Dict[str, Any]]:
        """Get all checkpoints for an analysis."""
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    """SELECT id, session_id, checkpoint_type, stocks_completed, stocks_pending,
                          stocks_total, checkpoint_data, checkpoint_timestamp, created_at
                       FROM analysis_checkpoints
                       WHERE analysis_id = ?
                       ORDER BY checkpoint_timestamp ASC""",
                    (analysis_id,)
                )
                rows = await cursor.fetchall()

                checkpoints = []
                for row in rows:
                    checkpoints.append({
                        "checkpoint_id": row[0],
                        "session_id": row[1],
                        "checkpoint_type": row[2],
                        "stocks_completed": json.loads(row[3]) if row[3] else [],
                        "stocks_pending": json.loads(row[4]) if row[4] else [],
                        "stocks_total": row[5],
                        "checkpoint_data": json.loads(row[6]) if row[6] else {},
                        "checkpoint_timestamp": row[7],
                        "created_at": row[8]
                    })
                return checkpoints

            except Exception as e:
                logger.error(f"Failed to get checkpoints for analysis {analysis_id}: {e}")
                return []

    async def delete_old_checkpoints(self, analysis_id: str, keep_latest: int = 5) -> bool:
        """Delete old checkpoints, keeping only the latest N."""
        async with self._lock:
            try:
                # Get all checkpoint IDs for this analysis
                cursor = await self.db.connection.execute(
                    """SELECT id FROM analysis_checkpoints
                       WHERE analysis_id = ?
                       ORDER BY checkpoint_timestamp DESC""",
                    (analysis_id,)
                )
                rows = await cursor.fetchall()

                if len(rows) <= keep_latest:
                    return True  # Nothing to delete

                # Delete old checkpoints
                checkpoints_to_delete = [row[0] for row in rows[keep_latest:]]
                placeholders = ','.join('?' * len(checkpoints_to_delete))
                await self.db.connection.execute(
                    f"""DELETE FROM analysis_checkpoints
                        WHERE id IN ({placeholders})""",
                    checkpoints_to_delete
                )

                await self.db.connection.commit()
                logger.info(f"Deleted {len(checkpoints_to_delete)} old checkpoints for analysis {analysis_id}")
                return True

            except Exception as e:
                logger.error(f"Failed to delete old checkpoints for analysis {analysis_id}: {e}")
                return False