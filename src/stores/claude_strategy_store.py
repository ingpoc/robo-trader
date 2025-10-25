"""Data store for Claude Agent sessions and learnings."""

import logging
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
import aiosqlite
import json

from ..models.claude_agent import ClaudeSessionResult, SessionType, StrategyLearning

logger = logging.getLogger(__name__)


class ClaudeStrategyStore:
    """Async store for Claude Agent sessions."""

    def __init__(self, config):
        """Initialize store with configuration."""
        # Extract database path from config
        if hasattr(config, 'database'):
            db_config = config.database if isinstance(config.database, dict) else config.database.__dict__
            self.db_path = db_config.get("path", "robo_trader.db")
        else:
            self.db_path = "robo_trader.db"

    async def initialize(self) -> None:
        """Initialize database tables for Claude sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            # Create claude_strategy_logs table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS claude_strategy_logs (
                    log_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    session_type TEXT NOT NULL,
                    account_type TEXT NOT NULL,
                    prompt_template TEXT,
                    context_data TEXT,
                    claude_response TEXT,
                    tools_used TEXT,
                    decision_made TEXT,
                    execution_result TEXT,
                    what_worked TEXT,
                    what_failed TEXT,
                    learnings TEXT,
                    token_usage_input INTEGER DEFAULT 0,
                    token_usage_output INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0.0,
                    duration_ms INTEGER DEFAULT 0,
                    timestamp TEXT NOT NULL
                )
            """)

            # Create claude_token_usage table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS claude_token_usage (
                    usage_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    total_cost_usd REAL DEFAULT 0.0,
                    timestamp TEXT NOT NULL
                )
            """)

            await db.commit()

        logger.info(f"ClaudeStrategyStore initialized: {self.db_path}")

    async def save_session(self, session: ClaudeSessionResult) -> None:
        """Save Claude session to database."""
        now = datetime.utcnow().isoformat()

        # Prepare JSON data
        context_json = json.dumps(session.context_provided)
        response_json = json.dumps({"text": session.claude_response})
        tools_json = json.dumps([tc.to_dict() for tc in session.tool_calls])
        decisions_json = json.dumps(session.decisions_made)
        learnings_json = json.dumps(session.learnings.to_dict() if session.learnings else None)
        what_worked_json = json.dumps(session.learnings.what_worked if session.learnings else [])
        what_failed_json = json.dumps(session.learnings.what_failed if session.learnings else [])

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO claude_strategy_logs (
                    log_id, session_id, session_type, account_type, prompt_template,
                    context_data, claude_response, tools_used, decision_made,
                    execution_result, what_worked, what_failed, learnings,
                    token_usage_input, token_usage_output, total_cost_usd,
                    duration_ms, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"log_{uuid.uuid4().hex[:16]}", session.session_id, session.session_type.value,
                    session.account_type, "", context_json, response_json, tools_json,
                    decisions_json, decisions_json, what_worked_json, what_failed_json,
                    learnings_json, session.token_input, session.token_output,
                    session.total_cost_usd, session.duration_ms, now
                )
            )
            await db.commit()

        logger.info(f"Saved session: {session.session_id} ({session.session_type.value})")

    async def get_session(self, session_id: str) -> Optional[ClaudeSessionResult]:
        """Get session by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM claude_strategy_logs WHERE session_id = ?",
                (session_id,)
            )
            row = await cursor.fetchone()
            if row:
                data = dict(row)
                context = json.loads(data['context_data'] or '{}')
                tools = json.loads(data['tools_used'] or '[]')
                decisions = json.loads(data['decision_made'] or '[]')
                learnings_data = json.loads(data['learnings'] or 'null')

                learnings = None
                if learnings_data:
                    learnings = StrategyLearning(
                        what_worked=learnings_data.get('what_worked', []),
                        what_failed=learnings_data.get('what_failed', []),
                        strategy_changes=learnings_data.get('strategy_changes', []),
                        research_topics=learnings_data.get('research_topics', []),
                        confidence_level=learnings_data.get('confidence_level', 0.5)
                    )

                return ClaudeSessionResult(
                    session_id=data['session_id'],
                    session_type=SessionType(data['session_type']),
                    account_type=data['account_type'],
                    context_provided=context,
                    claude_response=json.loads(data['claude_response']).get('text', ''),
                    tool_calls=[],  # Would need ToolCall.from_dict() if needed
                    decisions_made=decisions,
                    learnings=learnings,
                    token_input=data['token_usage_input'],
                    token_output=data['token_usage_output'],
                    total_cost_usd=data['total_cost_usd'],
                    duration_ms=data['duration_ms']
                )
        return None

    async def get_recent_sessions(
        self,
        account_type: str,
        session_type: Optional[SessionType] = None,
        limit: int = 10
    ) -> List[ClaudeSessionResult]:
        """Get recent sessions for account type."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if session_type:
                cursor = await db.execute(
                    """
                    SELECT * FROM claude_strategy_logs
                    WHERE account_type = ? AND session_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (account_type, session_type.value, limit)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM claude_strategy_logs
                    WHERE account_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                    """,
                    (account_type, limit)
                )

            rows = await cursor.fetchall()

        sessions = []
        for row in rows:
            data = dict(row)
            context = json.loads(data['context_data'] or '{}')
            decisions = json.loads(data['decision_made'] or '[]')

            sessions.append(ClaudeSessionResult(
                session_id=data['session_id'],
                session_type=SessionType(data['session_type']),
                account_type=data['account_type'],
                context_provided=context,
                claude_response="",  # Omit large response in list view
                tool_calls=[],
                decisions_made=decisions,
                token_input=data['token_usage_input'],
                token_output=data['token_usage_output'],
                total_cost_usd=data['total_cost_usd'],
                duration_ms=data['duration_ms']
            ))

        return sessions

    async def save_token_usage(
        self,
        session_id: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float
    ) -> None:
        """Save token usage for session."""
        usage_id = f"usage_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO claude_token_usage (
                    usage_id, session_id, operation, input_tokens, output_tokens,
                    total_cost_usd, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (usage_id, session_id, operation, input_tokens, output_tokens, cost_usd, now)
            )
            await db.commit()

        logger.info(f"Logged token usage: {operation} ({input_tokens}in, {output_tokens}out)")

    async def get_daily_token_usage(self) -> Dict[str, Any]:
        """Get token usage summary for today."""
        today = datetime.utcnow().strftime("%Y-%m-%d")

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            cursor = await db.execute(
                """
                SELECT
                    operation,
                    COUNT(*) as count,
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(total_cost_usd) as total_cost
                FROM claude_token_usage
                WHERE timestamp >= ?
                GROUP BY operation
                """,
                (today,)
            )
            rows = await cursor.fetchall()

            # Get grand total
            cursor = await db.execute(
                """
                SELECT
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output,
                    SUM(total_cost_usd) as total_cost
                FROM claude_token_usage
                WHERE timestamp >= ?
                """,
                (today,)
            )
            total_row = await cursor.fetchone()

        usage_by_op = {}
        for row in rows:
            usage_by_op[row['operation']] = {
                "count": row['count'],
                "input_tokens": row['total_input'] or 0,
                "output_tokens": row['total_output'] or 0,
                "total_cost": row['total_cost'] or 0.0
            }

        return {
            "date": today,
            "by_operation": usage_by_op,
            "total": {
                "input_tokens": total_row['total_input'] or 0,
                "output_tokens": total_row['total_output'] or 0,
                "total_cost_usd": total_row['total_cost'] or 0.0
            }
        }

    async def get_strategy_effectiveness(
        self,
        account_type: str,
        days: int = 7
    ) -> Dict[str, Any]:
        """Analyze strategy effectiveness over last N days."""
        cutoff_date = f"datetime('now', '-{days} days')"

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Get learnings
            cursor = await db.execute(
                f"""
                SELECT what_worked, what_failed FROM claude_strategy_logs
                WHERE account_type = ? AND timestamp > {cutoff_date}
                """,
                (account_type,)
            )
            rows = await cursor.fetchall()

        all_worked = []
        all_failed = []

        for row in rows:
            worked = json.loads(row['what_worked'] or '[]')
            failed = json.loads(row['what_failed'] or '[]')
            all_worked.extend(worked)
            all_failed.extend(failed)

        # Count occurrences
        from collections import Counter
        worked_counts = Counter(all_worked)
        failed_counts = Counter(all_failed)

        return {
            "period_days": days,
            "most_effective_strategies": worked_counts.most_common(5),
            "least_effective_strategies": failed_counts.most_common(5),
            "total_working_observations": len(all_worked),
            "total_failing_observations": len(all_failed)
        }

    async def get_sessions(
        self,
        limit: int = 10,
        offset: int = 0,
        account_type: Optional[str] = None,
    ) -> List[ClaudeSessionResult]:
        """Get paginated list of sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if account_type:
                cursor = await db.execute(
                    """
                    SELECT * FROM claude_strategy_logs
                    WHERE account_type = ?
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (account_type, limit, offset)
                )
            else:
                cursor = await db.execute(
                    """
                    SELECT * FROM claude_strategy_logs
                    ORDER BY timestamp DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )

            rows = await cursor.fetchall()

        sessions = []
        for row in rows:
            data = dict(row)
            context = json.loads(data['context_data'] or '{}')
            decisions = json.loads(data['decision_made'] or '[]')
            tools = json.loads(data['tools_used'] or '[]')

            sessions.append(ClaudeSessionResult(
                session_id=data['session_id'],
                session_type=SessionType(data['session_type']),
                account_type=data['account_type'],
                context_provided=context,
                claude_response="",  # Omit large response in list view
                tool_calls=[],
                decisions_made=decisions,
                token_input=data['token_usage_input'],
                token_output=data['token_usage_output'],
                total_cost_usd=data['total_cost_usd'],
                duration_ms=data['duration_ms']
            ))

        return sessions

    async def get_sessions_count(self, account_type: Optional[str] = None) -> int:
        """Get total count of sessions."""
        async with aiosqlite.connect(self.db_path) as db:
            if account_type:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM claude_strategy_logs WHERE account_type = ?",
                    (account_type,)
                )
            else:
                cursor = await db.execute(
                    "SELECT COUNT(*) FROM claude_strategy_logs"
                )
            row = await cursor.fetchone()
            return row[0] if row else 0
