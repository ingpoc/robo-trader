"""Persistent learning store for paper-trading research and outcome feedback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiosqlite

from src.models.paper_trading_learning import (
    DecisionMemoryEntry,
    LearningSummary,
    PromotableImprovement,
    ReviewMemoryEntry,
    SessionRetrospective,
    TradeOutcomeEvaluation,
)

logger = logging.getLogger(__name__)


class PaperTradingLearningStore:
    """Store research memories and post-trade evaluations in the paper-trading DB."""

    def __init__(self, db_connection: aiosqlite.Connection):
        self.db_connection = db_connection
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS research_memory_entries (
                    research_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    candidate_id TEXT,
                    symbol TEXT NOT NULL,
                    sector TEXT NOT NULL DEFAULT '',
                    thesis TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    risks_json TEXT NOT NULL,
                    invalidation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    screening_confidence REAL NOT NULL DEFAULT 0.0,
                    thesis_confidence REAL NOT NULL DEFAULT 0.0,
                    analysis_mode TEXT NOT NULL DEFAULT 'insufficient_evidence',
                    actionability TEXT NOT NULL DEFAULT 'watch_only',
                    external_evidence_status TEXT NOT NULL DEFAULT 'missing',
                    why_now TEXT,
                    source_summary_json TEXT NOT NULL DEFAULT '[]',
                    evidence_citations_json TEXT NOT NULL DEFAULT '[]',
                    market_data_freshness_json TEXT NOT NULL DEFAULT '{}',
                    next_step TEXT,
                    provider_metadata_json TEXT NOT NULL DEFAULT '{}',
                    generated_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_research_memory_schema()
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS trade_outcome_evaluations (
                    evaluation_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    trade_id TEXT NOT NULL UNIQUE,
                    candidate_id TEXT,
                    research_id TEXT,
                    decision_id TEXT,
                    review_id TEXT,
                    symbol TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    realized_pnl REAL NOT NULL,
                    pnl_percentage REAL NOT NULL,
                    holding_days INTEGER NOT NULL,
                    lesson TEXT NOT NULL,
                    improvement TEXT NOT NULL,
                    artifact_lineage_json TEXT NOT NULL DEFAULT '{}',
                    prompt_model_metadata_json TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_trade_outcome_schema()
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS decision_memory_entries (
                    decision_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    action TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    thesis TEXT NOT NULL,
                    invalidation TEXT NOT NULL,
                    next_step TEXT NOT NULL,
                    risk_note TEXT NOT NULL,
                    provider_metadata_json TEXT NOT NULL DEFAULT '{}',
                    generated_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS review_memory_entries (
                    review_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    strengths_json TEXT NOT NULL DEFAULT '[]',
                    weaknesses_json TEXT NOT NULL DEFAULT '[]',
                    risk_flags_json TEXT NOT NULL DEFAULT '[]',
                    top_lessons_json TEXT NOT NULL DEFAULT '[]',
                    strategy_proposals_json TEXT NOT NULL DEFAULT '[]',
                    provider_metadata_json TEXT NOT NULL DEFAULT '{}',
                    generated_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS session_retrospectives (
                    retrospective_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    keep_json TEXT NOT NULL DEFAULT '[]',
                    remove_json TEXT NOT NULL DEFAULT '[]',
                    fix_json TEXT NOT NULL DEFAULT '[]',
                    improve_json TEXT NOT NULL DEFAULT '[]',
                    evidence_json TEXT NOT NULL DEFAULT '[]',
                    owner TEXT NOT NULL,
                    promotion_state TEXT NOT NULL,
                    generated_at TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self.db_connection.execute(
                """
                CREATE TABLE IF NOT EXISTS promotable_improvements (
                    improvement_id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    owner TEXT NOT NULL,
                    promotion_state TEXT NOT NULL,
                    category TEXT NOT NULL DEFAULT '',
                    retrospective_id TEXT,
                    outcome_evidence_json TEXT NOT NULL DEFAULT '[]',
                    benchmark_evidence_json TEXT NOT NULL DEFAULT '[]',
                    guardrail TEXT NOT NULL DEFAULT '',
                    decision TEXT,
                    decision_reason TEXT NOT NULL DEFAULT '',
                    decision_owner TEXT NOT NULL DEFAULT '',
                    decided_at TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self._ensure_promotable_improvement_schema()
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_research_symbol ON research_memory_entries(account_id, symbol, generated_at DESC)"
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_outcome_symbol ON trade_outcome_evaluations(account_id, symbol, created_at DESC)"
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_decision_symbol ON decision_memory_entries(account_id, symbol, generated_at DESC)"
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_review_account ON review_memory_entries(account_id, generated_at DESC)"
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_retrospective_account ON session_retrospectives(account_id, generated_at DESC)"
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_promotable_account ON promotable_improvements(account_id, created_at DESC)"
            )
            await self.db_connection.commit()

    async def _ensure_research_memory_schema(self) -> None:
        cursor = await self.db_connection.execute("PRAGMA table_info(research_memory_entries)")
        rows = await cursor.fetchall()
        await cursor.close()
        existing_columns = {row[1] for row in rows}

        migrations = [
            ("sector", "ALTER TABLE research_memory_entries ADD COLUMN sector TEXT NOT NULL DEFAULT ''"),
            ("screening_confidence", "ALTER TABLE research_memory_entries ADD COLUMN screening_confidence REAL NOT NULL DEFAULT 0.0"),
            ("thesis_confidence", "ALTER TABLE research_memory_entries ADD COLUMN thesis_confidence REAL NOT NULL DEFAULT 0.0"),
            ("analysis_mode", "ALTER TABLE research_memory_entries ADD COLUMN analysis_mode TEXT NOT NULL DEFAULT 'insufficient_evidence'"),
            ("actionability", "ALTER TABLE research_memory_entries ADD COLUMN actionability TEXT NOT NULL DEFAULT 'watch_only'"),
            ("external_evidence_status", "ALTER TABLE research_memory_entries ADD COLUMN external_evidence_status TEXT NOT NULL DEFAULT 'missing'"),
            ("why_now", "ALTER TABLE research_memory_entries ADD COLUMN why_now TEXT"),
            ("source_summary_json", "ALTER TABLE research_memory_entries ADD COLUMN source_summary_json TEXT NOT NULL DEFAULT '[]'"),
            ("evidence_citations_json", "ALTER TABLE research_memory_entries ADD COLUMN evidence_citations_json TEXT NOT NULL DEFAULT '[]'"),
            ("market_data_freshness_json", "ALTER TABLE research_memory_entries ADD COLUMN market_data_freshness_json TEXT NOT NULL DEFAULT '{}'"),
            ("provider_metadata_json", "ALTER TABLE research_memory_entries ADD COLUMN provider_metadata_json TEXT NOT NULL DEFAULT '{}'"),
        ]

        for column_name, statement in migrations:
            if column_name not in existing_columns:
                await self.db_connection.execute(statement)

    async def _ensure_trade_outcome_schema(self) -> None:
        cursor = await self.db_connection.execute("PRAGMA table_info(trade_outcome_evaluations)")
        rows = await cursor.fetchall()
        await cursor.close()
        existing_columns = {row[1] for row in rows}

        migrations = [
            ("candidate_id", "ALTER TABLE trade_outcome_evaluations ADD COLUMN candidate_id TEXT"),
            ("decision_id", "ALTER TABLE trade_outcome_evaluations ADD COLUMN decision_id TEXT"),
            ("review_id", "ALTER TABLE trade_outcome_evaluations ADD COLUMN review_id TEXT"),
            ("artifact_lineage_json", "ALTER TABLE trade_outcome_evaluations ADD COLUMN artifact_lineage_json TEXT NOT NULL DEFAULT '{}'"),
            ("prompt_model_metadata_json", "ALTER TABLE trade_outcome_evaluations ADD COLUMN prompt_model_metadata_json TEXT NOT NULL DEFAULT '{}'"),
        ]

        for column_name, statement in migrations:
            if column_name not in existing_columns:
                await self.db_connection.execute(statement)

    async def _ensure_promotable_improvement_schema(self) -> None:
        cursor = await self.db_connection.execute("PRAGMA table_info(promotable_improvements)")
        rows = await cursor.fetchall()
        await cursor.close()
        existing_columns = {row[1] for row in rows}

        migrations = [
            ("category", "ALTER TABLE promotable_improvements ADD COLUMN category TEXT NOT NULL DEFAULT ''"),
            ("retrospective_id", "ALTER TABLE promotable_improvements ADD COLUMN retrospective_id TEXT"),
            ("decision", "ALTER TABLE promotable_improvements ADD COLUMN decision TEXT"),
            ("decision_reason", "ALTER TABLE promotable_improvements ADD COLUMN decision_reason TEXT NOT NULL DEFAULT ''"),
            ("decision_owner", "ALTER TABLE promotable_improvements ADD COLUMN decision_owner TEXT NOT NULL DEFAULT ''"),
            ("decided_at", "ALTER TABLE promotable_improvements ADD COLUMN decided_at TEXT"),
            ("updated_at", "ALTER TABLE promotable_improvements ADD COLUMN updated_at TEXT"),
        ]

        for column_name, statement in migrations:
            if column_name not in existing_columns:
                await self.db_connection.execute(statement)

    async def store_research_memory(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO research_memory_entries (
                    research_id, account_id, candidate_id, symbol, sector, thesis,
                    evidence_json, risks_json, invalidation, confidence,
                    screening_confidence, thesis_confidence, analysis_mode,
                    actionability, external_evidence_status, why_now, source_summary_json,
                    evidence_citations_json, market_data_freshness_json,
                    next_step, provider_metadata_json, generated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["research_id"],
                    entry["account_id"],
                    entry.get("candidate_id", ""),
                    entry["symbol"],
                    entry.get("sector", ""),
                    entry["thesis"],
                    _dump_json(entry.get("evidence", [])),
                    _dump_json(entry.get("risks", [])),
                    entry["invalidation"],
                    entry.get("confidence", 0.0),
                    entry.get("screening_confidence", 0.0),
                    entry.get("thesis_confidence", 0.0),
                    entry.get("analysis_mode", "insufficient_evidence"),
                    entry.get("actionability", "watch_only"),
                    entry.get("external_evidence_status", "missing"),
                    entry.get("why_now", ""),
                    _dump_json(entry.get("source_summary", [])),
                    _dump_json(entry.get("evidence_citations", [])),
                    _dump_json(entry.get("market_data_freshness", {})),
                    entry.get("next_step", ""),
                    _dump_json(entry.get("provider_metadata", {})),
                    entry["generated_at"],
                    entry["created_at"],
                ),
            )
            await self.db_connection.commit()

    async def get_latest_research_memory(
        self,
        account_id: str,
        symbol: str,
        *,
        before_timestamp: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        async with self._lock:
            query = (
                """
                SELECT research_id, account_id, candidate_id, symbol, sector, thesis, evidence_json,
                       risks_json, invalidation, confidence, screening_confidence,
                       thesis_confidence, analysis_mode, actionability, external_evidence_status, why_now,
                       source_summary_json, evidence_citations_json, market_data_freshness_json,
                       next_step, provider_metadata_json, generated_at, created_at
                FROM research_memory_entries
                WHERE account_id = ? AND symbol = ?
                """
            )
            params: List[Any] = [account_id, symbol]
            if before_timestamp:
                query += " AND generated_at <= ?"
                params.append(before_timestamp)
            query += " ORDER BY generated_at DESC LIMIT 1"

            cursor = await self.db_connection.execute(query, params)
            row = await cursor.fetchone()
            await cursor.close()
            return _research_row_to_dict(row) if row else None

    async def list_recent_research_memory(
        self,
        account_id: str,
        *,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT research_id, account_id, candidate_id, symbol, sector, thesis, evidence_json,
                       risks_json, invalidation, confidence, screening_confidence,
                       thesis_confidence, analysis_mode, actionability, external_evidence_status, why_now,
                       source_summary_json, evidence_citations_json, market_data_freshness_json,
                       next_step, provider_metadata_json, generated_at, created_at
                FROM research_memory_entries
                WHERE account_id = ?
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )
            rows = await cursor.fetchall()
            await cursor.close()
            return [_research_row_to_dict(row) for row in rows]

    async def store_decision_memory(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO decision_memory_entries (
                    decision_id, account_id, symbol, action, confidence, thesis,
                    invalidation, next_step, risk_note, provider_metadata_json,
                    generated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["decision_id"],
                    entry["account_id"],
                    entry["symbol"],
                    entry["action"],
                    entry.get("confidence", 0.0),
                    entry["thesis"],
                    entry["invalidation"],
                    entry["next_step"],
                    entry["risk_note"],
                    _dump_json(entry.get("provider_metadata", {})),
                    entry["generated_at"],
                    entry["created_at"],
                ),
            )
            await self.db_connection.commit()

    async def get_latest_decision_memory(
        self,
        account_id: str,
        symbol: str,
    ) -> Optional[DecisionMemoryEntry]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT decision_id, account_id, symbol, action, confidence, thesis,
                       invalidation, next_step, risk_note, provider_metadata_json,
                       generated_at, created_at
                FROM decision_memory_entries
                WHERE account_id = ? AND symbol = ?
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                (account_id, symbol),
            )
            row = await cursor.fetchone()
            await cursor.close()
        return _decision_from_row(row) if row else None

    async def list_recent_decision_memory(
        self,
        account_id: str,
        *,
        limit: int = 20,
    ) -> List[DecisionMemoryEntry]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT decision_id, account_id, symbol, action, confidence, thesis,
                       invalidation, next_step, risk_note, provider_metadata_json,
                       generated_at, created_at
                FROM decision_memory_entries
                WHERE account_id = ?
                ORDER BY generated_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [_decision_from_row(row) for row in rows]

    async def store_review_memory(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO review_memory_entries (
                    review_id, account_id, summary, confidence, strengths_json,
                    weaknesses_json, risk_flags_json, top_lessons_json,
                    strategy_proposals_json, provider_metadata_json,
                    generated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["review_id"],
                    entry["account_id"],
                    entry["summary"],
                    entry.get("confidence", 0.0),
                    _dump_json(entry.get("strengths", [])),
                    _dump_json(entry.get("weaknesses", [])),
                    _dump_json(entry.get("risk_flags", [])),
                    _dump_json(entry.get("top_lessons", [])),
                    _dump_json(entry.get("strategy_proposals", [])),
                    _dump_json(entry.get("provider_metadata", {})),
                    entry["generated_at"],
                    entry["created_at"],
                ),
            )
            await self.db_connection.commit()

    async def get_latest_review_memory(self, account_id: str) -> Optional[ReviewMemoryEntry]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT review_id, account_id, summary, confidence, strengths_json,
                       weaknesses_json, risk_flags_json, top_lessons_json,
                       strategy_proposals_json, provider_metadata_json,
                       generated_at, created_at
                FROM review_memory_entries
                WHERE account_id = ?
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                (account_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        return _review_from_row(row) if row else None

    async def store_session_retrospective(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO session_retrospectives (
                    retrospective_id, session_id, account_id, keep_json, remove_json,
                    fix_json, improve_json, evidence_json, owner, promotion_state,
                    generated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["retrospective_id"],
                    entry["session_id"],
                    entry["account_id"],
                    _dump_json(entry.get("keep", [])),
                    _dump_json(entry.get("remove", [])),
                    _dump_json(entry.get("fix", [])),
                    _dump_json(entry.get("improve", [])),
                    _dump_json(entry.get("evidence", [])),
                    entry.get("owner", "paper_trading_operator"),
                    entry.get("promotion_state", "queued"),
                    entry["generated_at"],
                    entry["created_at"],
                ),
            )
            await self.db_connection.commit()

    async def get_latest_session_retrospective(self, account_id: str) -> Optional[SessionRetrospective]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT retrospective_id, session_id, account_id, keep_json, remove_json,
                       fix_json, improve_json, evidence_json, owner, promotion_state,
                       generated_at, created_at
                FROM session_retrospectives
                WHERE account_id = ?
                ORDER BY generated_at DESC
                LIMIT 1
                """,
                (account_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
        return _retrospective_from_row(row) if row else None

    async def store_promotable_improvement(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO promotable_improvements (
                    improvement_id, account_id, title, summary, owner, promotion_state,
                    category, retrospective_id, outcome_evidence_json, benchmark_evidence_json,
                    guardrail, decision, decision_reason, decision_owner, decided_at,
                    updated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["improvement_id"],
                    entry["account_id"],
                    entry["title"],
                    entry["summary"],
                    entry["owner"],
                    entry["promotion_state"],
                    entry.get("category", ""),
                    entry.get("retrospective_id"),
                    _dump_json(entry.get("outcome_evidence", [])),
                    _dump_json(entry.get("benchmark_evidence", [])),
                    entry.get("guardrail", ""),
                    entry.get("decision"),
                    entry.get("decision_reason", ""),
                    entry.get("decision_owner", ""),
                    entry.get("decided_at"),
                    entry.get("updated_at", entry.get("created_at")),
                    entry["created_at"],
                ),
            )
            await self.db_connection.commit()

    async def get_promotable_improvement(
        self,
        account_id: str,
        improvement_id: str,
    ) -> Optional[PromotableImprovement]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT improvement_id, account_id, title, summary, owner, promotion_state,
                       category, retrospective_id, outcome_evidence_json, benchmark_evidence_json,
                       guardrail, decision, decision_reason, decision_owner, decided_at,
                       updated_at, created_at
                FROM promotable_improvements
                WHERE account_id = ? AND improvement_id = ?
                LIMIT 1
                """,
                (account_id, improvement_id),
            )
            row = await cursor.fetchone()
            await cursor.close()
        return _improvement_from_row(row) if row else None

    async def list_promotable_improvements(
        self,
        account_id: str,
        *,
        limit: int = 20,
    ) -> List[PromotableImprovement]:
        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT improvement_id, account_id, title, summary, owner, promotion_state,
                       category, retrospective_id, outcome_evidence_json, benchmark_evidence_json,
                       guardrail, decision, decision_reason, decision_owner, decided_at,
                       updated_at, created_at
                FROM promotable_improvements
                WHERE account_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (account_id, limit),
            )
            rows = await cursor.fetchall()
            await cursor.close()
        return [_improvement_from_row(row) for row in rows]

    async def store_trade_evaluation(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO trade_outcome_evaluations (
                    evaluation_id, account_id, trade_id, candidate_id, research_id, decision_id, review_id,
                    symbol, outcome, realized_pnl, pnl_percentage, holding_days, lesson, improvement,
                    artifact_lineage_json, prompt_model_metadata_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["evaluation_id"],
                    entry["account_id"],
                    entry["trade_id"],
                    entry.get("candidate_id"),
                    entry.get("research_id"),
                    entry.get("decision_id"),
                    entry.get("review_id"),
                    entry["symbol"],
                    entry["outcome"],
                    entry.get("realized_pnl", 0.0),
                    entry.get("pnl_percentage", 0.0),
                    entry.get("holding_days", 0),
                    entry["lesson"],
                    entry["improvement"],
                    _dump_json(entry.get("artifact_lineage", {})),
                    _dump_json(entry.get("prompt_model_metadata", {})),
                    entry["created_at"],
                ),
            )
            await self.db_connection.commit()

    async def has_trade_evaluation(self, trade_id: str) -> bool:
        async with self._lock:
            cursor = await self.db_connection.execute(
                "SELECT 1 FROM trade_outcome_evaluations WHERE trade_id = ? LIMIT 1",
                (trade_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()
            return row is not None

    async def list_trade_evaluations(
        self,
        account_id: str,
        *,
        symbol: Optional[str] = None,
        limit: int = 10,
    ) -> List[TradeOutcomeEvaluation]:
        async with self._lock:
            query = (
                """
                SELECT evaluation_id, account_id, trade_id, candidate_id, research_id, decision_id, review_id,
                       symbol, outcome, realized_pnl, pnl_percentage, holding_days, lesson, improvement,
                       artifact_lineage_json, prompt_model_metadata_json, created_at
                FROM trade_outcome_evaluations
                WHERE account_id = ?
                """
            )
            params: List[Any] = [account_id]
            if symbol:
                query += " AND symbol = ?"
                params.append(symbol)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor = await self.db_connection.execute(query, params)
            rows = await cursor.fetchall()
            await cursor.close()
            return [_evaluation_from_row(row) for row in rows]

    async def get_learning_summary(self, account_id: str, *, limit: int = 5) -> LearningSummary:
        evaluations = await self.list_trade_evaluations(account_id, limit=limit)

        async with self._lock:
            cursor = await self.db_connection.execute(
                """
                SELECT
                    COUNT(*) AS total_count,
                    SUM(CASE WHEN outcome = 'win' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN outcome = 'loss' THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN outcome = 'flat' THEN 1 ELSE 0 END) AS flats,
                    AVG(pnl_percentage) AS avg_pnl_percentage
                FROM trade_outcome_evaluations
                WHERE account_id = ?
                """,
                (account_id,),
            )
            row = await cursor.fetchone()
            await cursor.close()

        if row is None:
            return LearningSummary(account_id=account_id)

        top_lessons = [evaluation.lesson for evaluation in evaluations if evaluation.lesson][:3]
        improvement_focus = [evaluation.improvement for evaluation in evaluations if evaluation.improvement][:3]

        return LearningSummary(
            account_id=account_id,
            total_evaluations=row[0] or 0,
            wins=row[1] or 0,
            losses=row[2] or 0,
            flats=row[3] or 0,
            average_pnl_percentage=round(row[4] or 0.0, 2),
            top_lessons=top_lessons,
            improvement_focus=improvement_focus,
            recent_evaluations=evaluations,
        )


def _dump_json(value: Any) -> str:
    import json

    return json.dumps(value)


def _load_json(value: Optional[str], fallback: Any) -> Any:
    import json

    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _research_row_to_dict(row: Any) -> Dict[str, Any]:
    return {
        "research_id": row[0],
        "account_id": row[1],
        "candidate_id": row[2] or "",
        "symbol": row[3],
        "sector": row[4] or "",
        "thesis": row[5],
        "evidence": _load_json(row[6], []),
        "risks": _load_json(row[7], []),
        "invalidation": row[8],
        "confidence": row[9] or 0.0,
        "screening_confidence": row[10] or 0.0,
        "thesis_confidence": row[11] or 0.0,
        "analysis_mode": row[12] or "insufficient_evidence",
        "actionability": row[13] or "watch_only",
        "external_evidence_status": row[14] or "missing",
        "why_now": row[15] or "",
        "source_summary": _load_json(row[16], []),
        "evidence_citations": _load_json(row[17], []),
        "market_data_freshness": _load_json(row[18], {}),
        "next_step": row[19] or "",
        "provider_metadata": _load_json(row[20], {}),
        "generated_at": row[21],
        "created_at": row[22],
    }


def _evaluation_from_row(row: Any) -> TradeOutcomeEvaluation:
    return TradeOutcomeEvaluation(
        evaluation_id=row[0],
        account_id=row[1],
        trade_id=row[2],
        candidate_id=row[3],
        research_id=row[4],
        decision_id=row[5],
        review_id=row[6],
        symbol=row[7],
        outcome=row[8],
        realized_pnl=row[9] or 0.0,
        pnl_percentage=row[10] or 0.0,
        holding_days=row[11] or 0,
        lesson=row[12],
        improvement=row[13],
        artifact_lineage=_load_json(row[14], {}),
        prompt_model_metadata=_load_json(row[15], {}),
        created_at=row[16],
    )


def _decision_from_row(row: Any) -> DecisionMemoryEntry:
    return DecisionMemoryEntry(
        decision_id=row[0],
        account_id=row[1],
        symbol=row[2],
        action=row[3],
        confidence=row[4] or 0.0,
        thesis=row[5],
        invalidation=row[6],
        next_step=row[7],
        risk_note=row[8],
        provider_metadata=_load_json(row[9], {}),
        generated_at=row[10],
        created_at=row[11],
    )


def _review_from_row(row: Any) -> ReviewMemoryEntry:
    return ReviewMemoryEntry(
        review_id=row[0],
        account_id=row[1],
        summary=row[2],
        confidence=row[3] or 0.0,
        strengths=_load_json(row[4], []),
        weaknesses=_load_json(row[5], []),
        risk_flags=_load_json(row[6], []),
        top_lessons=_load_json(row[7], []),
        strategy_proposals=_load_json(row[8], []),
        provider_metadata=_load_json(row[9], {}),
        generated_at=row[10],
        created_at=row[11],
    )


def _retrospective_from_row(row: Any) -> SessionRetrospective:
    return SessionRetrospective(
        retrospective_id=row[0],
        session_id=row[1],
        account_id=row[2],
        keep=_load_json(row[3], []),
        remove=_load_json(row[4], []),
        fix=_load_json(row[5], []),
        improve=_load_json(row[6], []),
        evidence=_load_json(row[7], []),
        owner=row[8],
        promotion_state=row[9],
        generated_at=row[10],
        created_at=row[11],
    )


def _improvement_from_row(row: Any) -> PromotableImprovement:
    return PromotableImprovement(
        improvement_id=row[0],
        account_id=row[1],
        title=row[2],
        summary=row[3],
        owner=row[4],
        promotion_state=row[5],
        category=row[6] or "",
        retrospective_id=row[7],
        outcome_evidence=_load_json(row[8], []),
        benchmark_evidence=_load_json(row[9], []),
        guardrail=row[10] or "",
        decision=row[11],
        decision_reason=row[12] or "",
        decision_owner=row[13] or "",
        decided_at=row[14],
        updated_at=row[15] or row[16],
        created_at=row[16],
    )
