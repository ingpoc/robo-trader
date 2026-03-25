"""Persistent learning store for paper-trading research and outcome feedback."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiosqlite

from src.models.paper_trading_learning import LearningSummary, TradeOutcomeEvaluation

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
                    thesis TEXT NOT NULL,
                    evidence_json TEXT NOT NULL,
                    risks_json TEXT NOT NULL,
                    invalidation TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    screening_confidence REAL NOT NULL DEFAULT 0.0,
                    thesis_confidence REAL NOT NULL DEFAULT 0.0,
                    analysis_mode TEXT NOT NULL DEFAULT 'insufficient_evidence',
                    actionability TEXT NOT NULL DEFAULT 'watch_only',
                    why_now TEXT,
                    source_summary_json TEXT NOT NULL DEFAULT '[]',
                    evidence_citations_json TEXT NOT NULL DEFAULT '[]',
                    market_data_freshness_json TEXT NOT NULL DEFAULT '{}',
                    next_step TEXT,
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
                    research_id TEXT,
                    symbol TEXT NOT NULL,
                    outcome TEXT NOT NULL,
                    realized_pnl REAL NOT NULL,
                    pnl_percentage REAL NOT NULL,
                    holding_days INTEGER NOT NULL,
                    lesson TEXT NOT NULL,
                    improvement TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_research_symbol ON research_memory_entries(account_id, symbol, generated_at DESC)"
            )
            await self.db_connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_learning_outcome_symbol ON trade_outcome_evaluations(account_id, symbol, created_at DESC)"
            )
            await self.db_connection.commit()

    async def _ensure_research_memory_schema(self) -> None:
        cursor = await self.db_connection.execute("PRAGMA table_info(research_memory_entries)")
        rows = await cursor.fetchall()
        await cursor.close()
        existing_columns = {row[1] for row in rows}

        migrations = [
            ("screening_confidence", "ALTER TABLE research_memory_entries ADD COLUMN screening_confidence REAL NOT NULL DEFAULT 0.0"),
            ("thesis_confidence", "ALTER TABLE research_memory_entries ADD COLUMN thesis_confidence REAL NOT NULL DEFAULT 0.0"),
            ("analysis_mode", "ALTER TABLE research_memory_entries ADD COLUMN analysis_mode TEXT NOT NULL DEFAULT 'insufficient_evidence'"),
            ("actionability", "ALTER TABLE research_memory_entries ADD COLUMN actionability TEXT NOT NULL DEFAULT 'watch_only'"),
            ("why_now", "ALTER TABLE research_memory_entries ADD COLUMN why_now TEXT"),
            ("source_summary_json", "ALTER TABLE research_memory_entries ADD COLUMN source_summary_json TEXT NOT NULL DEFAULT '[]'"),
            ("evidence_citations_json", "ALTER TABLE research_memory_entries ADD COLUMN evidence_citations_json TEXT NOT NULL DEFAULT '[]'"),
            ("market_data_freshness_json", "ALTER TABLE research_memory_entries ADD COLUMN market_data_freshness_json TEXT NOT NULL DEFAULT '{}'"),
        ]

        for column_name, statement in migrations:
            if column_name not in existing_columns:
                await self.db_connection.execute(statement)

    async def store_research_memory(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO research_memory_entries (
                    research_id, account_id, candidate_id, symbol, thesis,
                    evidence_json, risks_json, invalidation, confidence,
                    screening_confidence, thesis_confidence, analysis_mode,
                    actionability, why_now, source_summary_json,
                    evidence_citations_json, market_data_freshness_json,
                    next_step, generated_at, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["research_id"],
                    entry["account_id"],
                    entry.get("candidate_id", ""),
                    entry["symbol"],
                    entry["thesis"],
                    _dump_json(entry.get("evidence", [])),
                    _dump_json(entry.get("risks", [])),
                    entry["invalidation"],
                    entry.get("confidence", 0.0),
                    entry.get("screening_confidence", 0.0),
                    entry.get("thesis_confidence", 0.0),
                    entry.get("analysis_mode", "insufficient_evidence"),
                    entry.get("actionability", "watch_only"),
                    entry.get("why_now", ""),
                    _dump_json(entry.get("source_summary", [])),
                    _dump_json(entry.get("evidence_citations", [])),
                    _dump_json(entry.get("market_data_freshness", {})),
                    entry.get("next_step", ""),
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
                SELECT research_id, account_id, candidate_id, symbol, thesis, evidence_json,
                       risks_json, invalidation, confidence, screening_confidence,
                       thesis_confidence, analysis_mode, actionability, why_now,
                       source_summary_json, evidence_citations_json, market_data_freshness_json,
                       next_step, generated_at, created_at
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

    async def store_trade_evaluation(self, entry: Dict[str, Any]) -> None:
        async with self._lock:
            await self.db_connection.execute(
                """
                INSERT OR REPLACE INTO trade_outcome_evaluations (
                    evaluation_id, account_id, trade_id, research_id, symbol, outcome,
                    realized_pnl, pnl_percentage, holding_days, lesson, improvement, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    entry["evaluation_id"],
                    entry["account_id"],
                    entry["trade_id"],
                    entry.get("research_id"),
                    entry["symbol"],
                    entry["outcome"],
                    entry.get("realized_pnl", 0.0),
                    entry.get("pnl_percentage", 0.0),
                    entry.get("holding_days", 0),
                    entry["lesson"],
                    entry["improvement"],
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
                SELECT evaluation_id, account_id, trade_id, research_id, symbol, outcome,
                       realized_pnl, pnl_percentage, holding_days, lesson, improvement, created_at
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
        "thesis": row[4],
        "evidence": _load_json(row[5], []),
        "risks": _load_json(row[6], []),
        "invalidation": row[7],
        "confidence": row[8] or 0.0,
        "screening_confidence": row[9] or 0.0,
        "thesis_confidence": row[10] or 0.0,
        "analysis_mode": row[11] or "insufficient_evidence",
        "actionability": row[12] or "watch_only",
        "why_now": row[13] or "",
        "source_summary": _load_json(row[14], []),
        "evidence_citations": _load_json(row[15], []),
        "market_data_freshness": _load_json(row[16], {}),
        "next_step": row[17] or "",
        "generated_at": row[18],
        "created_at": row[19],
    }


def _evaluation_from_row(row: Any) -> TradeOutcomeEvaluation:
    return TradeOutcomeEvaluation(
        evaluation_id=row[0],
        account_id=row[1],
        trade_id=row[2],
        research_id=row[3],
        symbol=row[4],
        outcome=row[5],
        realized_pnl=row[6] or 0.0,
        pnl_percentage=row[7] or 0.0,
        holding_days=row[8] or 0,
        lesson=row[9],
        improvement=row[10],
        created_at=row[11],
    )
