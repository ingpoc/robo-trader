"""Context-bounded AI artifact generation for paper trading."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import BaseModel, Field

from src.auth.claude_auth import get_claude_status, record_claude_runtime_limit
from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.models.agent_artifacts import (
    AgentPromptContext,
    Candidate,
    CandidateLifecycleState,
    DecisionEnvelope,
    DecisionPacket,
    DiscoveryEnvelope,
    MarketDataFreshness,
    ResearchActionability,
    ResearchClassification,
    ResearchEnvelope,
    ResearchEvidenceCitation,
    ResearchPacket,
    ResearchSourceSummary,
    ReviewEnvelope,
    ReviewReport,
    SessionLoopSummary,
    StrategyProposal,
)
from src.models.market_data import MarketData
from src.services.codex_runtime_client import CodexRuntimeError, _normalize_output_schema
from src.services.claude_agent.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class FocusedResearchDraft(BaseModel):
    """Lean model-generated fields for focused research."""

    thesis: str
    evidence: List[str] = Field(default_factory=list)
    risks: List[str] = Field(default_factory=list)
    invalidation: str
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    thesis_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    actionability: ResearchActionability = "watch_only"
    why_now: str = ""
    next_step: str = ""


class AgentArtifactService:
    """Produce typed paper-trading artifacts with bounded AI runtime context."""

    DISCOVERY_CANDIDATE_MAX_AGE_HOURS = 36
    DECISION_MARK_FRESHNESS_THRESHOLD_SECONDS = 5 * 60
    DISCOVERY_MIN_CONFIDENCE = 0.45
    DISCOVERY_RESEARCH_READY_CONFIDENCE = 0.60
    RESEARCH_ACTIONABLE_CONFIDENCE = 0.60
    DECISION_MIN_CONFIDENCE = 0.55
    DECISION_READY_CONFIDENCE = 0.65
    REVIEW_READY_CONFIDENCE = 0.60
    FOCUSED_RESEARCH_EXTERNAL_TIMEOUT_SECONDS = 30.0
    FOCUSED_RESEARCH_MARKET_CONTEXT_TIMEOUT_SECONDS = 12.0
    FOCUSED_RESEARCH_SYNTHESIS_TIMEOUT_SECONDS = 60.0
    RESEARCH_QUOTE_PREFLIGHT_WAIT_SECONDS = 4.0
    RESEARCH_QUOTE_PREFLIGHT_POLL_SECONDS = 0.5
    RESEARCH_MEMORY_FRESH_HOURS = 6
    SESSION_TARGET_ACTIONABLE_COUNT = 1
    MAX_RESEARCH_ATTEMPTS_PER_SESSION = 6
    DISCOVERY_POSTURE = "balanced"
    REENTRY_POLICY = "event_plus_stale"
    MODEL_ROUTE_TRIAGE = "gpt-5-mini"
    MODEL_ROUTE_DISCOVERY = "gpt-5-mini"
    MODEL_ROUTE_RESEARCH = "gpt-5.4"
    MODEL_ROUTE_DECISION = "gpt-5.4"

    @staticmethod
    def _runtime_supports_compact_models(runtime_mode: str) -> bool:
        return (runtime_mode or "").strip().lower() not in {"local_runtime_service"}

    def __init__(self, container: "DependencyContainer"):
        self.container = container
        self.context_builder = ContextBuilder(token_limit=1800)
        self._decision_cache: Dict[str, DecisionEnvelope] = {}
        self._review_cache: Dict[str, ReviewEnvelope] = {}
        self._research_cache: Dict[str, Dict[str, ResearchPacket]] = {}
        self.discovery_candidate_max_age = timedelta(hours=self.DISCOVERY_CANDIDATE_MAX_AGE_HOURS)

    @staticmethod
    def _claude_usage_exhausted(claude_status: Any) -> bool:
        """Return whether the active runtime is authenticated but temporarily usage-limited."""
        rate_limit_info = getattr(claude_status, "rate_limit_info", {}) or {}
        return rate_limit_info.get("status") == "exhausted"

    @staticmethod
    def _claude_blockers(claude_status: Any, *, action: str) -> List[str]:
        """Build a truthful blocker message for runtime-dependent workflows."""
        rate_limit_info = getattr(claude_status, "rate_limit_info", {}) or {}
        if rate_limit_info.get("status") == "exhausted":
            message = rate_limit_info.get("message") or "AI runtime usage is temporarily exhausted."
            return [f"AI runtime is usage-limited for {action}. {message}"]
        return [f"AI runtime is not ready for {action}."]

    @classmethod
    def discovery_criteria(cls, *, discovery_defaults: Optional[Dict[str, Any]] = None) -> List[str]:
        defaults = discovery_defaults if isinstance(discovery_defaults, dict) else {}
        min_price = float(defaults.get("min_price") or 50.0)
        max_price = float(defaults.get("max_price") or 5000.0)
        liquidity = str(defaults.get("liquidity_min") or "medium")
        min_cap = str(defaults.get("min_market_cap") or "small")
        max_cap = str(defaults.get("max_market_cap") or "mega")
        return [
            (
                f"Universe: NSE names priced between INR {min_price:.0f} and INR {max_price:.0f}, "
                f"liquidity at least {liquidity}, market-cap tiers {min_cap} through {max_cap}."
            ),
            f"Discovery posture defaults to {cls.DISCOVERY_POSTURE}: prefer undercovered small and mid caps with regime fit and stronger evidence, not novelty alone.",
            "Exclude penny stocks and already-held symbols for the selected paper account.",
            f"Ignore watchlist rows older than {cls.DISCOVERY_CANDIDATE_MAX_AGE_HOURS} hours.",
            f"Show discovery candidates only when confidence is at least {cls.DISCOVERY_MIN_CONFIDENCE:.2f}.",
            f"Promote to focused research only when confidence is at least {cls.DISCOVERY_RESEARCH_READY_CONFIDENCE:.2f}.",
            f"Previously analyzed names reenter only on stale research or a fresh trigger ({cls.REENTRY_POLICY}).",
        ]

    @classmethod
    def research_criteria(cls) -> List[str]:
        return [
            "Research runs from the fresh queue or an explicit symbol selection and keeps advancing until one actionable candidate is found or the queue is exhausted.",
            f"Actionable research requires thesis confidence at least {cls.RESEARCH_ACTIONABLE_CONFIDENCE:.2f} and zero blockers.",
            "Fresh evidence target: at least two fresh sources with at least one primary external source.",
            "Stale or missing live market data caps confidence below actionable status.",
            "Research must classify the candidate as actionable_buy_candidate, keep_watch, or rejected.",
            (
                f"Runtime budgets: {cls.FOCUSED_RESEARCH_EXTERNAL_TIMEOUT_SECONDS:.0f}s external research, "
                f"{cls.FOCUSED_RESEARCH_MARKET_CONTEXT_TIMEOUT_SECONDS:.0f}s market context, "
                f"{cls.FOCUSED_RESEARCH_SYNTHESIS_TIMEOUT_SECONDS:.0f}s synthesis."
            ),
            "Use cheaper model routing for routine triage and reserve GPT-5.4 synthesis for finalists.",
        ]

    @classmethod
    def decision_criteria(cls) -> List[str]:
        return [
            "Decision review considers open positions only; it does not generate new entries.",
            f"Position marks must be live enough; stale marks older than {cls.DECISION_MARK_FRESHNESS_THRESHOLD_SECONDS}s block decisions.",
            f"Decision packets are ready only when confidence is at least {cls.DECISION_READY_CONFIDENCE:.2f}.",
            f"Confidence below {cls.DECISION_MIN_CONFIDENCE:.2f} is treated as review-exit territory rather than promotable guidance.",
            "Actions are limited to hold, review_exit, tighten_stop, or take_profit.",
        ]

    @classmethod
    def review_criteria(cls) -> List[str]:
        return [
            "Daily review is observational unless confidence clears the promotion threshold.",
            f"Review confidence must reach at least {cls.REVIEW_READY_CONFIDENCE:.2f} before strategy proposals should influence future behavior.",
            "No recent closed trades caps review confidence below the ready threshold.",
            "Strategy proposals stay guarded suggestions until separate benchmark or outcome evidence promotes them.",
            "The loop should keep only lessons that materially change research quality, risk control, or execution discipline.",
        ]

    @staticmethod
    def _dedupe_preserving_order(values: List[str]) -> List[str]:
        seen: set[str] = set()
        ordered: List[str] = []
        for value in values:
            text = str(value).strip()
            if not text or text in seen:
                continue
            seen.add(text)
            ordered.append(text)
        return ordered

    @classmethod
    def _freshness_from_timestamp(
        cls,
        value: Optional[str],
        *,
        max_age_hours: int,
    ) -> str:
        parsed = cls._parse_timestamp(value)
        if parsed is None:
            return "unknown"
        age = datetime.now(timezone.utc) - parsed
        return "fresh" if age <= timedelta(hours=max_age_hours) else "stale"

    @classmethod
    def _empty_reason_from_state(
        cls,
        *,
        status: str,
        blockers: List[str],
        default_empty_reason: Optional[str] = None,
    ) -> Optional[str]:
        if default_empty_reason:
            return default_empty_reason
        lowered = " ".join(blockers).lower()
        if status == "empty":
            if "select" in lowered or "choose" in lowered:
                return "requires_selection"
            if "stale" in lowered:
                return "stale"
            return "no_candidates"
        if status == "blocked":
            if "usage-limited" in lowered or "usage limit" in lowered or "spending cap" in lowered:
                return "blocked_by_quota"
            if "ai runtime" in lowered:
                return "blocked_by_runtime"
        return None

    @staticmethod
    def _research_source_counts(source_summary: List[ResearchSourceSummary]) -> tuple[int, int]:
        primary = sum(
            1
            for item in source_summary
            if item.tier == "primary" and item.freshness in {"fresh", "live"}
        )
        external = sum(
            1
            for item in source_summary
            if item.freshness in {"fresh", "live"}
            and AgentArtifactService._source_type_is_external(item.source_type)
        )
        return primary, external

    @staticmethod
    def _technical_context_available(source_summary: List[ResearchSourceSummary]) -> bool:
        return any(item.source_type == "technical_context" for item in source_summary)

    def _project_discovery_research_memory(
        self,
        latest_research: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        latest_research = latest_research if isinstance(latest_research, dict) else {}
        generated_at = latest_research.get("generated_at")
        source_summary = [
            ResearchSourceSummary.model_validate(item)
            for item in list(latest_research.get("source_summary") or [])
        ]
        primary_sources, external_sources = self._research_source_counts(source_summary)
        latest_market_data = latest_research.get("market_data_freshness") or {}

        return {
            "generated_at": generated_at,
            "actionability": latest_research.get("actionability"),
            "thesis_confidence": self._clamp_confidence(latest_research.get("thesis_confidence")),
            "analysis_mode": latest_research.get("analysis_mode"),
            "freshness": self._freshness_from_timestamp(
                generated_at,
                max_age_hours=self.RESEARCH_MEMORY_FRESH_HOURS,
            ) if generated_at else "unknown",
            "fresh_primary_source_count": primary_sources,
            "fresh_external_source_count": external_sources,
            "market_data_freshness": str(latest_market_data.get("status") or "unknown"),
            "technical_context_available": self._technical_context_available(source_summary),
            "evidence_mode": str(latest_research.get("analysis_mode") or ""),
        }

    @staticmethod
    def _market_trigger_text(item: Dict[str, Any], latest_research: Dict[str, Any]) -> str:
        research_summary = item.get("research_summary") or {}
        trigger_fields: List[str] = []
        for key in ("discovery_reason", "summary", "research_summary", "news", "financial_data", "filings", "market_context"):
            value = research_summary.get(key) if isinstance(research_summary, dict) else None
            if value:
                trigger_fields.append(str(value))
        trigger_fields.extend(str(entry) for entry in (latest_research.get("evidence") or []) if entry)
        trigger_fields.extend(str(entry) for entry in (latest_research.get("risks") or []) if entry)
        return " ".join(trigger_fields).lower()

    @classmethod
    def _detect_trigger_type(cls, item: Dict[str, Any], latest_research: Optional[Dict[str, Any]] = None) -> Optional[str]:
        research_summary = item.get("research_summary") or {}
        if isinstance(research_summary, dict) and research_summary.get("last_trigger_type"):
            return str(research_summary.get("last_trigger_type"))
        text = cls._market_trigger_text(item, latest_research or {})
        if not text:
            return None
        if any(marker in text for marker in ("earnings", "result", "quarter", "q1", "q2", "q3", "q4")):
            return "earnings"
        if any(marker in text for marker in ("guidance", "outlook", "margin expansion")):
            return "guidance_change"
        if any(marker in text for marker in ("order win", "order book", "contract win", "award")):
            return "order_win"
        if any(marker in text for marker in ("filing", "exchange disclosure", "board meeting", "investor presentation", "disclosure")):
            return "filing"
        if any(marker in text for marker in ("breakout", "relative strength", "uptrend", "momentum")):
            return "price_regime_change"
        if any(marker in text for marker in ("news", "catalyst", "re-rating", "rerating")):
            return "news"
        return None

    @classmethod
    def _evidence_quality_score(cls, research_memory: Dict[str, Any]) -> float:
        primary = int(research_memory.get("fresh_primary_source_count") or 0)
        external = int(research_memory.get("fresh_external_source_count") or 0)
        technical = 0.1 if research_memory.get("technical_context_available") else 0.0
        market_status = str(research_memory.get("market_data_freshness") or "unknown")
        market_bonus = 0.15 if market_status in {"fresh", "live"} else 0.0
        freshness_bonus = 0.15 if research_memory.get("freshness") == "fresh" else 0.0
        score = min(primary * 0.25 + external * 0.2 + technical + market_bonus + freshness_bonus, 1.0)
        return round(max(score, 0.0), 2)

    @classmethod
    def _lifecycle_state_for_candidate(
        cls,
        *,
        research_memory: Dict[str, Any],
        trigger_type: Optional[str],
    ) -> CandidateLifecycleState:
        freshness = str(research_memory.get("freshness") or "unknown")
        actionability = str(research_memory.get("actionability") or "")
        if freshness != "fresh":
            return "fresh_queue"
        if trigger_type:
            return "fresh_queue"
        if actionability == "actionable":
            return "actionable"
        if actionability == "watch_only":
            return "keep_watch"
        return "rejected"

    @classmethod
    def _reentry_reason_for_candidate(
        cls,
        *,
        lifecycle_state: CandidateLifecycleState,
        research_memory: Dict[str, Any],
        trigger_type: Optional[str],
    ) -> Optional[str]:
        if lifecycle_state != "fresh_queue":
            return None
        if trigger_type:
            return f"fresh_{trigger_type}"
        if research_memory.get("generated_at"):
            return "stale_research_memory"
        return None

    @classmethod
    def _dark_horse_score_for_candidate(
        cls,
        *,
        item: Dict[str, Any],
        confidence: float,
        research_memory: Dict[str, Any],
        trigger_type: Optional[str],
    ) -> float:
        score = confidence * 0.45
        sector = str(item.get("sector") or "").lower()
        if sector and sector not in {"banking", "financial services"}:
            score += 0.05
        discovery_source = str(item.get("discovery_source") or "")
        if "stateful_opportunity_funnel" in discovery_source:
            score += 0.1
        rationale = str(item.get("discovery_reason") or "").lower()
        if any(marker in rationale for marker in ("underfollowed", "dark horse", "re-rating", "under-researched")):
            score += 0.15
        if trigger_type:
            score += 0.15
        if research_memory.get("freshness") == "fresh" and research_memory.get("actionability") == "blocked":
            score -= 0.2
        return round(max(0.0, min(score, 1.0)), 2)

    @classmethod
    def _research_classification(cls, research: ResearchPacket) -> ResearchClassification:
        if research.actionability == "actionable":
            return "actionable_buy_candidate"
        if research.actionability == "blocked" or research.analysis_mode == "insufficient_evidence":
            return "rejected"
        return "keep_watch"

    def _transition_reason_for_research(self, research: ResearchPacket) -> str:
        if research.classification == "actionable_buy_candidate":
            return "Fresh evidence, adequate thesis confidence, and zero blockers cleared the packet into the actionable queue."
        if research.classification == "rejected":
            return "Evidence quality or runtime blockers were too weak for continued promotion, so the name moved to rejected memory."
        return "The packet is not fit for action now but remains worth watching for a fresh trigger or stale-memory refresh."

    def _build_loop_summary(
        self,
        *,
        candidates: List[Candidate],
        attempted_candidates: Optional[List[Candidate]] = None,
        promoted: Optional[List[Candidate]] = None,
        termination_reason: str = "not_started",
        latest_transition_reason: Optional[str] = None,
        model_usage_by_phase: Optional[Dict[str, Dict[str, Any]]] = None,
        token_usage_by_phase: Optional[Dict[str, Dict[str, Any]]] = None,
        current_candidate: Optional[Candidate] = None,
    ) -> SessionLoopSummary:
        attempted_candidates = attempted_candidates or []
        promoted = promoted or []
        actionable_found_count = len(promoted)
        return SessionLoopSummary(
            target_actionable_count=self.SESSION_TARGET_ACTIONABLE_COUNT,
            actionable_found_count=actionable_found_count,
            research_attempt_count=len(attempted_candidates),
            attempted_candidates=[candidate.symbol for candidate in attempted_candidates],
            attempted_candidate_ids=[candidate.candidate_id for candidate in attempted_candidates],
            queue_exhausted=termination_reason == "queue_exhausted",
            termination_reason=termination_reason,
            current_candidate_symbol=current_candidate.symbol if current_candidate else None,
            current_candidate_id=current_candidate.candidate_id if current_candidate else None,
            latest_transition_reason=latest_transition_reason,
            model_usage_by_phase=model_usage_by_phase or {},
            token_usage_by_phase=token_usage_by_phase or {},
            total_candidates_scanned=len(candidates),
            promoted_actionable_symbols=[candidate.symbol for candidate in promoted],
        )

    async def _latest_research_memory_by_symbol(
        self,
        *,
        account_id: str,
        symbols: List[str],
    ) -> Dict[str, Dict[str, Any]]:
        if not symbols:
            return {}
        try:
            learning_service = await self.container.get("paper_trading_learning_service")
        except Exception:
            return {}

        memory: Dict[str, Dict[str, Any]] = {}
        for symbol in sorted({symbol for symbol in symbols if symbol}):
            latest = await learning_service.learning_store.get_latest_research_memory(account_id, symbol)
            if isinstance(latest, dict) and latest:
                memory[symbol] = latest
        return memory

    def _discovery_considered(
        self,
        *,
        watchlist: List[Dict[str, Any]],
        held_symbols: set[str],
        latest_research_by_symbol: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> List[str]:
        considered: List[str] = []
        for item in watchlist:
            symbol = str(item.get("symbol") or "").upper().strip()
            if not symbol:
                continue
            if symbol in held_symbols:
                considered.append(f"{symbol} · already held, excluded from discovery output")
                continue
            if not self._is_current_discovery_candidate(item):
                considered.append(f"{symbol} · stale watchlist row, waiting for refresh")
                continue
            candidate = self._build_discovery_candidate(item)
            if candidate is None:
                considered.append(
                    f"{symbol} · below discovery threshold of {self.DISCOVERY_MIN_CONFIDENCE:.2f}"
                )
                continue
            readiness = (
                "research-ready"
                if candidate.confidence >= self.DISCOVERY_RESEARCH_READY_CONFIDENCE
                else "watch-only"
            )
            latest_research = (latest_research_by_symbol or {}).get(candidate.symbol) or {}
            if latest_research:
                freshness = self._freshness_from_timestamp(
                    latest_research.get("generated_at"),
                    max_age_hours=self.RESEARCH_MEMORY_FRESH_HOURS,
                )
                considered.append(
                    f"{candidate.symbol} · {int(round(candidate.confidence * 100))}% · "
                    f"{latest_research.get('actionability', readiness)} · {freshness} research memory"
                )
            else:
                considered.append(
                    f"{candidate.symbol} · {int(round(candidate.confidence * 100))}% · {readiness}"
                )
        return self._dedupe_preserving_order(considered[:8])

    @staticmethod
    def _symbol_from_trade_like(item: Dict[str, Any]) -> str:
        for key in ("symbol", "ticker"):
            value = item.get(key)
            if value:
                return str(value).upper()
        return ""

    def _review_considered(self, *, snapshot: AgentPromptContext) -> List[str]:
        considered: List[str] = []
        for position in snapshot.positions[:4]:
            symbol = self._symbol_from_trade_like(position)
            if symbol:
                considered.append(f"{symbol} · open position under active review")
        for trade in snapshot.recent_trades[:4]:
            symbol = self._symbol_from_trade_like(trade)
            if symbol:
                considered.append(f"{symbol} · recent realized outcome in review memory")
        if not considered:
            considered.append("No realized trade outcomes are currently available for review.")
        return self._dedupe_preserving_order(considered[:8])

    def _research_considered(
        self,
        *,
        candidate: Optional[Candidate] = None,
        symbol: Optional[str] = None,
        research: Optional[ResearchPacket] = None,
    ) -> List[str]:
        considered: List[str] = []
        resolved_symbol = (
            (research.symbol if research is not None else None)
            or (candidate.symbol if candidate is not None else None)
            or (str(symbol).upper() if symbol else "")
        )
        if resolved_symbol:
            considered.append(f"{resolved_symbol} · staged candidate for focused research")
        if candidate is not None and candidate.sector:
            considered.append(f"{candidate.sector} · current sector context from discovery")
        if research is not None:
            considered.append(
                f"External evidence · {research.external_evidence_status.replace('_', ' ')}"
            )
            considered.append(
                f"Market data · {research.market_data_freshness.status.replace('_', ' ')}"
            )
            for source in research.source_summary[:3]:
                considered.append(
                    f"{source.label} · {source.freshness.replace('_', ' ')} · {source.tier}"
                )
        if not considered:
            considered.append("No candidate is currently staged for focused research.")
        return self._dedupe_preserving_order(considered[:8])

    async def get_discovery_view(self, account_id: str, limit: int = 10) -> DiscoveryEnvelope:
        """Return watchlist-backed discovery candidates without inflating runtime context."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        try:
            discovery_service = await self.container.get("stock_discovery_service")
        except Exception as exc:
            logger.warning("Stock discovery service unavailable: %s", exc)
            return DiscoveryEnvelope(
                status="blocked",
                context_mode="stateful_watchlist",
                blockers=["Stock discovery service is unavailable."],
                artifact_count=0,
                criteria=self.discovery_criteria(),
                considered=["Discovery watchlist could not be loaded because the discovery service is unavailable."],
                freshness_state="unknown",
                empty_reason="blocked_by_runtime",
                candidates=[],
            )

        watchlist = await discovery_service.get_watchlist(limit=limit)
        open_positions = await account_manager.get_open_positions(account_id)
        held_symbols = {position.symbol for position in open_positions}
        discovery_defaults = getattr(discovery_service, "default_criteria", None)
        if not isinstance(discovery_defaults, dict):
            discovery_defaults = None
        criteria = self.discovery_criteria(discovery_defaults=discovery_defaults)
        latest_research_by_symbol = await self._latest_research_memory_by_symbol(
            account_id=account_id,
            symbols=[str(item.get("symbol") or "").upper() for item in watchlist],
        )
        considered = self._discovery_considered(
            watchlist=watchlist,
            held_symbols=held_symbols,
            latest_research_by_symbol=latest_research_by_symbol,
        )

        candidates: List[Candidate] = []
        for item in watchlist:
            symbol = item.get("symbol")
            if not symbol or symbol in held_symbols:
                continue
            if not self._is_current_discovery_candidate(item):
                continue
            candidate = self._build_discovery_candidate(
                item,
                latest_research=latest_research_by_symbol.get(str(symbol).upper()),
            )
            if candidate is None:
                continue
            candidates.append(candidate)

        candidates.sort(
            key=lambda candidate: (
                {"high": 0, "medium": 1, "low": 2}.get(candidate.priority, 3),
                -candidate.confidence,
                candidate.symbol,
            )
        )
        candidates.sort(
            key=lambda candidate: (
                1 if candidate.lifecycle_state == "fresh_queue" else 0,
                candidate.dark_horse_score,
                candidate.evidence_quality_score,
                candidate.confidence,
            ),
            reverse=True,
        )
        promotable_count = sum(
            1
            for candidate in candidates
            if candidate.lifecycle_state == "fresh_queue"
            and candidate.confidence >= self.DISCOVERY_RESEARCH_READY_CONFIDENCE
        )
        fresh_queue = [candidate for candidate in candidates if candidate.lifecycle_state == "fresh_queue"]
        status = "ready" if candidates else "empty"
        blockers = [] if candidates else ["No active discovery candidates cleared the confidence threshold in the watchlist."]
        if fresh_queue and promotable_count == 0:
            blockers.append(
                "Discovery candidates remain below the research promotion confidence threshold; refresh discovery before spending research budget automatically."
            )
        if not fresh_queue and candidates:
            blockers.append("All visible candidates already have fresh analyzed memory; wait for stale or trigger-based reentry before spending research budget again.")

        return DiscoveryEnvelope(
            status=status,
            context_mode="stateful_watchlist",
            blockers=blockers,
            artifact_count=len(candidates),
            criteria=criteria,
            considered=considered,
            freshness_state="fresh" if status == "ready" else "unknown",
            empty_reason=self._empty_reason_from_state(status=status, blockers=blockers),
            candidates=candidates[:limit],
            loop_summary=self._build_loop_summary(
                candidates=candidates[:limit],
                termination_reason="idle" if fresh_queue else "waiting_for_reentry" if candidates else "queue_exhausted",
                current_candidate=fresh_queue[0] if fresh_queue else None,
                latest_transition_reason=(
                    "The next research run will start with the highest-ranked fresh queue candidate."
                    if fresh_queue
                    else "No fresh queue candidate is currently eligible; analyzed names are waiting for stale or trigger-based reentry."
                ),
                model_usage_by_phase={
                    "discovery_scout": {
                        "model": self.MODEL_ROUTE_DISCOVERY,
                        "reasoning": "low",
                    }
                },
            ),
        )

    def _build_discovery_candidate(
        self,
        item: Dict[str, Any],
        *,
        latest_research: Optional[Dict[str, Any]] = None,
    ) -> Optional[Candidate]:
        confidence = self._clamp_confidence(item.get("confidence_score"))
        if confidence < self.DISCOVERY_MIN_CONFIDENCE:
            return None

        recommendation = str(item.get("recommendation") or "WATCH").upper()
        if recommendation in {"BUY", "ACCUMULATE"} or confidence >= 0.75:
            priority = "high"
        elif confidence >= self.DISCOVERY_RESEARCH_READY_CONFIDENCE:
            priority = "medium"
        else:
            priority = "low"

        promotable = confidence >= self.DISCOVERY_RESEARCH_READY_CONFIDENCE
        research_memory = self._project_discovery_research_memory(latest_research)
        trigger_type = self._detect_trigger_type(item, latest_research or {})
        if research_memory.get("freshness") == "fresh":
            trigger_type = None
        lifecycle_state = self._lifecycle_state_for_candidate(
            research_memory=research_memory,
            trigger_type=trigger_type,
        )
        reentry_reason = self._reentry_reason_for_candidate(
            lifecycle_state=lifecycle_state,
            research_memory=research_memory,
            trigger_type=trigger_type,
        )
        dark_horse_score = self._dark_horse_score_for_candidate(
            item=item,
            confidence=confidence,
            research_memory=research_memory,
            trigger_type=trigger_type,
        )
        evidence_quality_score = self._evidence_quality_score(research_memory)
        next_step = (
            "View the current focused research packet before making any trade decision."
            if lifecycle_state == "actionable"
            else "Keep this packet on watch until a new trigger or stale-memory refresh brings it back into the queue."
            if lifecycle_state == "keep_watch"
            else "Leave this name in rejected memory until a new trigger or stale-memory refresh changes the setup."
            if lifecycle_state == "rejected"
            else (
                "Open a focused research packet before making any trade decision."
                if promotable
                else "Refresh discovery evidence before promoting this symbol into focused research."
            )
        )
        return Candidate(
            candidate_id=str(item.get("id") or uuid.uuid4()),
            symbol=str(item.get("symbol") or "").upper(),
            company_name=item.get("company_name"),
            sector=item.get("sector"),
            source=str(item.get("discovery_source") or "watchlist"),
            priority=priority,
            confidence=confidence,
            rationale=str(
                item.get("discovery_reason") or item.get("recommendation") or "Discovery watchlist candidate"
            ),
            next_step=next_step,
            generated_at=str(item.get("updated_at") or item.get("created_at") or self._utc_now()),
            last_researched_at=research_memory["generated_at"],
            last_actionability=research_memory["actionability"],
            last_thesis_confidence=research_memory["thesis_confidence"],
            last_analysis_mode=research_memory["analysis_mode"],
            research_freshness=research_memory["freshness"],
            fresh_primary_source_count=research_memory["fresh_primary_source_count"],
            fresh_external_source_count=research_memory["fresh_external_source_count"],
            market_data_freshness=research_memory["market_data_freshness"],
            technical_context_available=research_memory["technical_context_available"],
            evidence_mode=research_memory["evidence_mode"],
            lifecycle_state=lifecycle_state,
            reentry_reason=reentry_reason,
            last_trigger_type=trigger_type,
            dark_horse_score=dark_horse_score,
            evidence_quality_score=evidence_quality_score,
        )

    def _is_current_discovery_candidate(self, item: Dict[str, Any]) -> bool:
        """Reject watchlist rows that are too old to count as current discovery output."""
        timestamp = (
            item.get("last_analyzed")
            or item.get("updated_at")
            or item.get("discovery_date")
            or item.get("created_at")
        )
        if timestamp is None:
            return True
        parsed = self._parse_timestamp(timestamp)
        if parsed is None:
            return True
        return datetime.now(timezone.utc) - parsed <= self.discovery_candidate_max_age

    async def get_research_view(
        self,
        account_id: str,
        *,
        candidate_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 10,
        refresh: bool = False,
    ) -> ResearchEnvelope:
        """Generate focused research and continue through the fresh queue until actionable or exhausted."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )
        criteria = self.research_criteria()

        if not refresh:
            cached = self._get_cached_research(account_id, candidate_id=candidate_id, symbol=symbol)
            if cached is not None:
                return ResearchEnvelope(
                    status="ready",
                    context_mode="single_candidate_research",
                    blockers=[],
                    artifact_count=1,
                    criteria=criteria,
                    considered=self._research_considered(symbol=symbol, research=cached),
                    provider_metadata=cached.provider_metadata or {},
                    freshness_state=self._freshness_from_timestamp(
                        cached.generated_at,
                        max_age_hours=self.RESEARCH_MEMORY_FRESH_HOURS,
                    ),
                    research=cached,
                    loop_summary=self._build_loop_summary(
                        candidates=[],
                        termination_reason="cached_packet",
                        current_candidate=Candidate(
                            candidate_id=cached.candidate_id or f"symbol:{cached.symbol.lower()}",
                            symbol=cached.symbol,
                            source="cached_research_packet",
                            priority="medium",
                            confidence=cached.confidence,
                            rationale=cached.thesis,
                            next_step=cached.next_step,
                        ),
                        model_usage_by_phase={
                            "research_synthesis": {
                                "model": str((cached.provider_metadata or {}).get("model") or self.MODEL_ROUTE_RESEARCH),
                                "reasoning": str((cached.provider_metadata or {}).get("reasoning") or "medium"),
                            }
                        },
                    ),
                )
            return ResearchEnvelope(
                status="empty",
                context_mode="single_candidate_research",
                blockers=["Run research from Discovery to create a focused research packet."],
                artifact_count=0,
                criteria=criteria,
                considered=self._research_considered(symbol=symbol),
                freshness_state="unknown",
                empty_reason="never_run",
                research=None,
            )

        discovery = await self.get_discovery_view(account_id, limit=limit)
        preferred_candidate = self._resolve_research_candidate(
            discovery=discovery,
            candidate_id=candidate_id,
            symbol=symbol,
        )
        logger.info(
            "Focused research loop requested for account=%s candidate_id=%s symbol=%s resolved_symbol=%s",
            account_id,
            candidate_id,
            symbol,
            getattr(preferred_candidate, "symbol", None),
        )
        if preferred_candidate is None:
            blockers = (
                discovery.blockers
                if discovery.status == "blocked"
                else ["No discovery candidate is available for focused research."]
            )
            return ResearchEnvelope(
                status="blocked" if discovery.status == "blocked" else "empty",
                context_mode="single_candidate_research",
                blockers=blockers,
                artifact_count=0,
                criteria=criteria,
                considered=self._research_considered(symbol=symbol),
                freshness_state="unknown",
                empty_reason=self._empty_reason_from_state(
                    status="blocked" if discovery.status == "blocked" else "empty",
                    blockers=blockers,
                ),
                research=None,
                loop_summary=self._build_loop_summary(
                    candidates=discovery.candidates,
                    termination_reason="runtime_blocked" if discovery.status == "blocked" else "no_candidates",
                    latest_transition_reason=blockers[0] if blockers else None,
                ),
            )

        loop_candidates = self._eligible_loop_candidates(discovery, preferred_candidate=preferred_candidate)
        if not loop_candidates:
            blockers = ["No fresh-queue candidate is currently eligible for focused research."]
            return ResearchEnvelope(
                status="empty",
                context_mode="single_candidate_research",
                blockers=blockers,
                artifact_count=0,
                criteria=criteria,
                considered=self._research_considered(candidate=preferred_candidate, symbol=symbol),
                freshness_state="unknown",
                empty_reason="no_candidates",
                research=None,
                loop_summary=self._build_loop_summary(
                    candidates=discovery.candidates,
                    termination_reason="queue_exhausted",
                    latest_transition_reason=blockers[0],
                ),
            )

        attempted_candidates: List[Candidate] = []
        promoted: List[Candidate] = []
        model_usage_by_phase: Dict[str, Dict[str, Any]] = {}
        token_usage_by_phase: Dict[str, Dict[str, Any]] = {}
        latest_transition_reason: Optional[str] = None
        last_envelope: Optional[ResearchEnvelope] = None

        for current_candidate in loop_candidates:
            attempted_candidates.append(current_candidate)
            envelope = await self._generate_research_for_candidate(
                account_id=account_id,
                candidate=current_candidate,
                symbol=symbol,
                criteria=criteria,
            )
            last_envelope = envelope

            provider_metadata = envelope.provider_metadata or {}
            if provider_metadata:
                model_usage_by_phase["research_synthesis"] = {
                    "model": str(provider_metadata.get("model") or self.MODEL_ROUTE_RESEARCH),
                    "reasoning": str(provider_metadata.get("reasoning") or "medium"),
                }
                usage_payload = provider_metadata.get("usage")
                if isinstance(usage_payload, dict) and usage_payload:
                    token_usage_by_phase["research_synthesis"] = usage_payload

            if envelope.research is not None:
                latest_transition_reason = self._transition_reason_for_research(envelope.research)
                if envelope.research.classification == "actionable_buy_candidate":
                    promoted.append(current_candidate)
                    break
            elif envelope.blockers:
                latest_transition_reason = envelope.blockers[0]

            if envelope.status == "blocked" and envelope.empty_reason in {"blocked_by_runtime", "blocked_by_quota"}:
                break

        if last_envelope is None:
            last_envelope = ResearchEnvelope(
                status="empty",
                context_mode="single_candidate_research",
                blockers=["No focused research attempt was executed."],
                artifact_count=0,
                criteria=criteria,
                considered=self._research_considered(candidate=preferred_candidate, symbol=symbol),
                freshness_state="unknown",
                empty_reason="no_candidates",
                research=None,
            )

        if promoted:
            termination_reason = "actionable_found"
        elif last_envelope.status == "blocked" and last_envelope.empty_reason in {"blocked_by_runtime", "blocked_by_quota"}:
            termination_reason = "runtime_blocked"
        else:
            termination_reason = "queue_exhausted"

        return last_envelope.model_copy(
            update={
                "loop_summary": self._build_loop_summary(
                    candidates=discovery.candidates,
                    attempted_candidates=attempted_candidates,
                    promoted=promoted,
                    termination_reason=termination_reason,
                    latest_transition_reason=latest_transition_reason,
                    model_usage_by_phase=model_usage_by_phase,
                    token_usage_by_phase=token_usage_by_phase,
                    current_candidate=attempted_candidates[-1] if attempted_candidates else preferred_candidate,
                )
            }
        )

    async def _generate_research_for_candidate(
        self,
        *,
        account_id: str,
        candidate: Candidate,
        symbol: Optional[str],
        criteria: List[str],
    ) -> ResearchEnvelope:
        claude_status = await get_claude_status()
        if not claude_status.is_valid or self._claude_usage_exhausted(claude_status):
            blocker = self._claude_blockers(claude_status, action="research generation")[0]
            await self._record_failed_research_attempt(
                account_id=account_id,
                candidate=candidate,
                blocker=blocker,
            )
            return ResearchEnvelope(
                status="blocked",
                context_mode="single_candidate_research",
                blockers=[blocker],
                artifact_count=0,
                criteria=criteria,
                considered=self._research_considered(candidate=candidate, symbol=symbol),
                freshness_state="unknown",
                empty_reason=self._empty_reason_from_state(status="blocked", blockers=[blocker]),
                research=None,
            )

        snapshot = await self._build_prompt_context(account_id, positions_limit=3, trades_limit=4)
        try:
            learning_service = await self.container.get("paper_trading_learning_service")
            symbol_learning = await learning_service.get_symbol_learning_context(account_id, candidate.symbol)
        except Exception:
            learning_service = None
            symbol_learning = {}

        runtime_inputs = await self._collect_focused_research_runtime_inputs(
            symbol=candidate.symbol,
            company_name=candidate.company_name,
        )
        research_inputs = await self._build_focused_research_inputs(
            account_id=account_id,
            candidate=candidate,
            snapshot=snapshot,
            symbol_learning=symbol_learning,
            external_research=runtime_inputs["external_research"],
            market_context=runtime_inputs["market_context"],
        )
        logger.info(
            "Focused research inputs prepared for account=%s symbol=%s with %s sources",
            account_id,
            candidate.symbol,
            len(research_inputs.get("source_summary", [])),
        )
        serialized_context = self.context_builder.serialize_for_prompt(
            self._compact_research_context(
                candidate=candidate,
                snapshot=snapshot,
                symbol_learning=symbol_learning,
                research_inputs=research_inputs,
            )
        )
        prompt = (
            "Create a focused research packet for a single swing-trading candidate.\n"
            "Optimize for the highest probability of clearing actionability, not just interesting stories.\n"
            "Use only the provided context. Fresh external web research has already been captured in the context when available.\n"
            "Do not invent catalysts, prices, filings, or technical levels.\n"
            "Separate screening confidence, evidence quality, thesis confidence, and trade readiness.\n"
            "If evidence is thin or stale, stop early and classify as keep_watch or rejected instead of bluffing certainty.\n"
            "Return a concise why_now, supporting evidence, key risks, invalidation, actionability, and the next operator step.\n"
            f"Context:\n{serialized_context}"
        )

        try:
            research_draft, provider_metadata = await self._run_structured_role(
                client_type=f"agent_research_{account_id}",
                role_name="research",
                system_prompt=(
                    "You are the Research Agent for Robo Trader. "
                    "Produce a single-candidate research packet with explicit evidence, explicit classification, and clear invalidation."
                ),
                prompt=prompt,
                output_model=FocusedResearchDraft,
                allowed_tools=[],
                session_id=f"research:{account_id}:{candidate.candidate_id}",
                model=self.MODEL_ROUTE_RESEARCH,
                max_turns=3,
                max_budget_usd=0.75,
                timeout_seconds=self.FOCUSED_RESEARCH_SYNTHESIS_TIMEOUT_SECONDS,
            )
        except TradingError as exc:
            usage_limit_message = self._extract_usage_limited_message(str(exc))
            if not usage_limit_message:
                response_text = self._extract_error_response_text(exc)
                usage_limit_message = self._extract_usage_limited_message(response_text)
            if usage_limit_message:
                record_claude_runtime_limit(usage_limit_message)
                if learning_service is not None:
                    await self._record_failed_research_attempt(
                        account_id=account_id,
                        candidate=candidate,
                        blocker=f"AI runtime is usage-limited for research generation. {usage_limit_message}",
                        learning_service=learning_service,
                        research_inputs=research_inputs,
                    )
                return ResearchEnvelope(
                    status="blocked",
                    context_mode="single_candidate_research",
                    blockers=[f"AI runtime is usage-limited for research generation. {usage_limit_message}"],
                    artifact_count=0,
                    criteria=criteria,
                    considered=self._research_considered(candidate=candidate, symbol=symbol),
                    freshness_state="unknown",
                    empty_reason="blocked_by_quota",
                    research=None,
                )
            runtime_blocker = self._build_runtime_blocker(exc, action="research generation")
            if runtime_blocker:
                if learning_service is not None:
                    await self._record_failed_research_attempt(
                        account_id=account_id,
                        candidate=candidate,
                        blocker=runtime_blocker,
                        learning_service=learning_service,
                        research_inputs=research_inputs,
                    )
                return ResearchEnvelope(
                    status="blocked",
                    context_mode="single_candidate_research",
                    blockers=[runtime_blocker],
                    artifact_count=0,
                    criteria=criteria,
                    considered=self._research_considered(candidate=candidate, symbol=symbol),
                    freshness_state="unknown",
                    empty_reason="blocked_by_runtime",
                    research=None,
                )
            raise

        logger.info(
            "Focused research synthesis completed for account=%s symbol=%s actionability=%s",
            account_id,
            candidate.symbol,
            getattr(research_draft, "actionability", None),
        )

        research = ResearchPacket(
            research_id=f"RESEARCH-{candidate.symbol.upper()}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            candidate_id=candidate.candidate_id,
            account_id=account_id,
            symbol=candidate.symbol,
            thesis=research_draft.thesis,
            evidence=research_draft.evidence,
            risks=research_draft.risks,
            invalidation=research_draft.invalidation,
            confidence=research_draft.confidence,
            thesis_confidence=research_draft.thesis_confidence,
            actionability=research_draft.actionability,
            why_now=research_draft.why_now,
            next_step=research_draft.next_step,
        )

        if not research.candidate_id:
            research.candidate_id = candidate.candidate_id
        if not research.account_id:
            research.account_id = account_id
        if not research.symbol:
            research.symbol = candidate.symbol
        research = self._finalize_research_packet(
            research,
            candidate=candidate,
            account_id=account_id,
            research_inputs=research_inputs,
            capability_summary=snapshot.capability_summary,
        )
        research.provider_metadata = {
            **provider_metadata,
            "usage": (provider_metadata or {}).get("usage", {}),
            "phase": "research_synthesis",
        }
        research.classification = self._research_classification(research)
        research.what_changed_since_last_research = (
            f"Reactivated because {candidate.reentry_reason.replace('_', ' ')}."
            if candidate.reentry_reason
            else (
                f"Fresh trigger detected: {candidate.last_trigger_type.replace('_', ' ')}."
                if candidate.last_trigger_type
                else "No prior research memory existed for this symbol."
                if not candidate.last_researched_at
                else "The previous packet was refreshed to replace stale or incomplete evidence."
            )
        )

        self._store_research(account_id, research)
        if learning_service is not None:
            await learning_service.record_research_packet(
                account_id,
                candidate.candidate_id,
                research,
                sector=candidate.sector,
            )

        blockers = self._derive_research_blockers(
            analysis_mode=research.analysis_mode,
            market_data_freshness=research.market_data_freshness,
            source_summary=research.source_summary,
            external_errors=(research_inputs.get("fresh_external_research") or {}).get("errors", []),
            capability_blockers=snapshot.capability_summary.get("blockers", []),
        )

        return ResearchEnvelope(
            status="ready",
            context_mode="single_candidate_research",
            blockers=blockers,
            artifact_count=1,
            criteria=criteria,
            considered=self._research_considered(candidate=candidate, symbol=symbol, research=research),
            provider_metadata=research.provider_metadata,
            freshness_state=self._freshness_from_timestamp(
                research.generated_at,
                max_age_hours=self.RESEARCH_MEMORY_FRESH_HOURS,
            ),
            research=research,
        )

    async def _record_failed_research_attempt(
        self,
        *,
        account_id: str,
        candidate: Candidate,
        blocker: str,
        learning_service: Optional[Any] = None,
        research_inputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Persist a blocked research attempt so the same friction is not rediscovered repeatedly."""
        if learning_service is None:
            try:
                learning_service = await self.container.get("paper_trading_learning_service")
            except Exception:
                learning_service = None
        if learning_service is None:
            return

        source_summary = list((research_inputs or {}).get("source_summary") or [])
        evidence_citations = list((research_inputs or {}).get("evidence_citations") or [])
        market_data_freshness = (research_inputs or {}).get("market_data_freshness") or {}
        now = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

        failed_research = ResearchPacket(
            research_id=f"RESEARCH-FAILED-{candidate.symbol.upper()}-{now}",
            candidate_id=candidate.candidate_id,
            account_id=account_id,
            symbol=candidate.symbol,
            thesis="Focused research was blocked before a trade-ready thesis could be formed.",
            evidence=[],
            risks=[blocker],
            invalidation="Retry only after the blocker clears and fresh evidence is available.",
            confidence=0.0,
            screening_confidence=max(0.0, min(candidate.confidence, 1.0)),
            thesis_confidence=0.0,
            analysis_mode="insufficient_evidence",
            actionability="blocked",
            why_now=str(candidate.rationale or ""),
            source_summary=source_summary,
            evidence_citations=evidence_citations,
            market_data_freshness=market_data_freshness,
            next_step=f"Do not retry this symbol until the blocker clears: {blocker}",
            generated_at=datetime.now(timezone.utc).isoformat(),
        )
        await learning_service.record_research_packet(
            account_id,
            candidate.candidate_id,
            failed_research,
            sector=candidate.sector,
        )

    async def get_decision_view(self, account_id: str, limit: int = 3, refresh: bool = False) -> DecisionEnvelope:
        """Generate compact position-level decision packets via the active AI runtime."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )
        criteria = self.decision_criteria()

        if not refresh and account_id in self._decision_cache:
            return self._decision_cache[account_id]

        claude_status = await get_claude_status()
        if not claude_status.is_valid or self._claude_usage_exhausted(claude_status):
            blockers = self._claude_blockers(claude_status, action="decision generation")
            return DecisionEnvelope(
                status="blocked",
                context_mode="delta_position_review",
                blockers=blockers,
                artifact_count=0,
                criteria=criteria,
                considered=["AI runtime blocker prevented any open-position review."],
                freshness_state="unknown",
                empty_reason=self._empty_reason_from_state(status="blocked", blockers=blockers),
                decisions=[],
            )

        if not refresh:
            return DecisionEnvelope(
                status="empty",
                context_mode="delta_position_review",
                blockers=["Run decision review to generate current position guidance."],
                artifact_count=0,
                criteria=criteria,
                considered=["No open positions are being reviewed until you run the decision stage."],
                freshness_state="unknown",
                empty_reason="never_run",
                decisions=[],
            )

        positions = await account_manager.get_open_positions(account_id)
        considered = self._dedupe_preserving_order(
            [f"{position.symbol} · open position in current review set" for position in positions[:8]]
        )
        if not positions:
            return DecisionEnvelope(
                status="empty",
                context_mode="delta_position_review",
                blockers=["No open positions are available for decision review."],
                artifact_count=0,
                criteria=criteria,
                considered=["No open positions are currently in scope for decision review."],
                freshness_state="unknown",
                empty_reason="no_candidates",
                decisions=[],
            )

        stale_position_blocker = self._decision_market_data_blocker(positions)
        if stale_position_blocker:
            return DecisionEnvelope(
                status="blocked",
                context_mode="delta_position_review",
                blockers=[stale_position_blocker],
                artifact_count=0,
                criteria=criteria,
                considered=considered,
                freshness_state="stale",
                empty_reason="stale",
                decisions=[],
            )

        snapshot = await self._build_prompt_context(account_id, positions_limit=limit, trades_limit=6)
        serialized_context = self.context_builder.serialize_with_delta(
            f"decision:{account_id}",
            snapshot.model_dump(mode="json"),
        )

        prompt = (
            "Review the current paper-trading positions and emit one decision packet per position.\n"
            "Use only the provided context. Do not invent prices, catalysts, or exits.\n"
            "Choose action from: hold, review_exit, tighten_stop, take_profit.\n"
            "Keep each thesis and next_step concise and operator-facing.\n"
            f"Context:\n{serialized_context}"
        )

        response, provider_metadata = await self._run_structured_role(
            client_type=f"agent_decision_{account_id}",
            role_name="decision",
            system_prompt=(
                "You are the Decision Agent for Robo Trader. "
                "Your job is to review existing paper positions using minimal context and return only structured decision packets."
            ),
            prompt=prompt,
            output_model=DecisionEnvelopePayload,
            allowed_tools=[],
            session_id=f"decision:{account_id}",
        )
        decisions, confidence_blockers, ready_decision_count = self._finalize_decision_packets(
            response.decisions,
            positions=positions,
        )

        envelope = DecisionEnvelope(
            status=(
                "ready"
                if decisions and ready_decision_count > 0
                else "blocked"
                if decisions
                else "empty"
            ),
            context_mode="delta_position_review",
            blockers=confidence_blockers if decisions else ["AI runtime returned no decision packets."],
            artifact_count=len(decisions),
            criteria=criteria,
            considered=considered,
            provider_metadata=provider_metadata,
            freshness_state="fresh" if decisions else "unknown",
            empty_reason="no_candidates" if not decisions else None,
            decisions=decisions,
        )
        try:
            learning_service = await self.container.get("paper_trading_learning_service")
        except Exception:
            learning_service = None
        if learning_service is not None:
            for decision in decisions:
                await learning_service.record_decision_packet(
                    account_id,
                    decision,
                    provider_metadata=provider_metadata,
                )
        self._decision_cache[account_id] = envelope
        return envelope

    async def get_review_view(self, account_id: str, refresh: bool = False) -> ReviewEnvelope:
        """Generate a compact end-of-day style review report via the active AI runtime."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )
        criteria = self.review_criteria()

        if not refresh and account_id in self._review_cache:
            return self._review_cache[account_id]

        claude_status = await get_claude_status()
        if not claude_status.is_valid or self._claude_usage_exhausted(claude_status):
            blockers = self._claude_blockers(claude_status, action="review generation")
            return ReviewEnvelope(
                status="blocked",
                context_mode="delta_daily_review",
                blockers=blockers,
                artifact_count=0,
                criteria=criteria,
                considered=["Review runtime blocker prevented any outcome analysis."],
                freshness_state="unknown",
                empty_reason=self._empty_reason_from_state(status="blocked", blockers=blockers),
                review=None,
            )

        if not refresh:
            return ReviewEnvelope(
                status="empty",
                context_mode="delta_daily_review",
                blockers=["Run daily review to generate a fresh review report."],
                artifact_count=0,
                criteria=criteria,
                considered=["No positions or recent trades are being reviewed until you run this stage."],
                freshness_state="unknown",
                empty_reason="never_run",
                review=None,
            )

        snapshot = await self._build_prompt_context(account_id, positions_limit=5, trades_limit=10)
        considered = self._review_considered(snapshot=snapshot)
        if not snapshot.positions and not snapshot.recent_trades:
            return ReviewEnvelope(
                status="empty",
                context_mode="delta_daily_review",
                blockers=["No positions or recent trades are available for review."],
                artifact_count=0,
                criteria=criteria,
                considered=considered,
                freshness_state="unknown",
                empty_reason="no_candidates",
                review=None,
            )

        serialized_context = self.context_builder.serialize_with_delta(
            f"review:{account_id}",
            snapshot.model_dump(mode="json"),
        )
        prompt = (
            "Create a concise operator review for the current paper-trading account.\n"
            "Use only the provided context. Do not invent market narratives or performance claims.\n"
            "The output must highlight strengths, weaknesses, and risk flags.\n"
            "Only include strategy proposals when the context contains benchmark-backed promotable proposals.\n"
            f"Context:\n{serialized_context}"
        )

        review, provider_metadata = await self._run_structured_role(
            client_type=f"agent_review_{account_id}",
            role_name="review",
            system_prompt=(
                "You are the Review Agent for Robo Trader. "
                "Summarize only verified outcomes and turn them into concise operator guidance."
            ),
            prompt=prompt,
            output_model=ReviewReport,
            allowed_tools=[],
            session_id=f"review:{account_id}",
        )
        review.strategy_proposals = self._deterministic_strategy_proposals(snapshot.improvement_report)
        review, review_blockers = self._finalize_review_report(
            review,
            snapshot=snapshot,
        )

        envelope = ReviewEnvelope(
            status="ready",
            context_mode="delta_daily_review",
            blockers=review_blockers,
            artifact_count=1,
            criteria=criteria,
            considered=considered,
            provider_metadata=provider_metadata,
            freshness_state="fresh",
            review=review,
        )
        try:
            learning_service = await self.container.get("paper_trading_learning_service")
        except Exception:
            learning_service = None
        if learning_service is not None:
            await learning_service.record_review_report(
                account_id,
                review,
                provider_metadata=provider_metadata,
            )
        self._review_cache[account_id] = envelope
        return envelope

    async def _build_focused_research_inputs(
        self,
        *,
        account_id: str,
        candidate: Candidate,
        snapshot: AgentPromptContext,
        symbol_learning: Dict[str, Any],
        external_research: Optional[Dict[str, Any]] = None,
        market_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        symbol = candidate.symbol.upper()
        watchlist_entry = await self._load_watchlist_entry(symbol)
        research_ledger = await self._load_research_ledger_entry(symbol)
        external_research = external_research or await self._load_fresh_external_research(
            symbol,
            company_name=candidate.company_name,
        )
        market_context = market_context or await self._load_market_context(symbol)

        stored_summary = self._parse_json_blob((watchlist_entry or {}).get("research_summary")) or {}
        if not isinstance(stored_summary, dict):
            stored_summary = {}
        source_summary: List[ResearchSourceSummary] = []

        if watchlist_entry:
            watchlist_ts = (
                watchlist_entry.get("last_analyzed")
                or watchlist_entry.get("updated_at")
                or watchlist_entry.get("created_at")
                or ""
            )
            source_summary.append(
                ResearchSourceSummary(
                    source_type="discovery_watchlist",
                    label="Discovery watchlist entry",
                    timestamp=watchlist_ts,
                    freshness=self._freshness_label(watchlist_ts, fresh_after=timedelta(days=2)),
                    detail=str(watchlist_entry.get("recommendation") or candidate.rationale),
                )
            )

        if research_ledger:
            source_summary.append(
                ResearchSourceSummary(
                    source_type="research_ledger",
                    label="Structured screening ledger",
                    timestamp=str(research_ledger.get("timestamp") or ""),
                    freshness=self._freshness_label(
                        research_ledger.get("timestamp"),
                        fresh_after=timedelta(days=2),
                    ),
                    detail=(
                        f"Action {research_ledger.get('action') or 'UNKNOWN'} "
                        f"at score {float(research_ledger.get('score') or 0.0):.2f}"
                    ),
                )
            )

        latest_research = symbol_learning.get("latest_research") or {}
        if latest_research:
            latest_research_ts = latest_research.get("generated_at") or latest_research.get("created_at") or ""
            source_summary.append(
                ResearchSourceSummary(
                    source_type="learning_memory",
                    label="Prior research memory",
                    timestamp=latest_research_ts,
                    freshness=self._freshness_label(latest_research_ts, fresh_after=timedelta(days=7)),
                    detail=str(latest_research.get("analysis_mode") or latest_research.get("thesis") or ""),
                )
            )

        stored_external_research = (
            stored_summary.get("external_research")
            or stored_summary.get("codex_web_research")
            or stored_summary.get("claude_web_research")
            or stored_summary.get("perplexity")
        )
        if stored_external_research:
            fallback_ts = (
                stored_external_research.get("research_timestamp")
                or watchlist_entry.get("last_analyzed")
                if watchlist_entry
                else ""
            )
            source_summary.append(
                ResearchSourceSummary(
                    source_type="stored_external_research",
                    label="Stored discovery research",
                    timestamp=str(fallback_ts or ""),
                    freshness=self._freshness_label(fallback_ts, fresh_after=timedelta(days=2)),
                    detail="Using stored discovery-time external research for historical context.",
                )
            )

        for item in external_research.get("source_summary", []):
            source_summary.append(ResearchSourceSummary.model_validate(item))

        market_freshness = MarketDataFreshness.model_validate(market_context.get("market_data_freshness") or {})
        if market_freshness.timestamp or market_freshness.summary:
            source_summary.append(
                ResearchSourceSummary(
                    source_type="market_quote",
                    label="Current market quote",
                    timestamp=market_freshness.timestamp,
                    freshness=market_freshness.status,
                    detail=market_freshness.summary,
                )
            )

        technical_state = market_context.get("technical_state") or {}
        technical_ts = str(technical_state.get("timestamp") or "")
        if technical_state:
            source_summary.append(
                ResearchSourceSummary(
                    source_type="technical_context",
                    label="OHLCV technical state",
                    timestamp=technical_ts,
                    freshness=self._freshness_label(technical_ts, fresh_after=timedelta(days=3)),
                    detail=technical_state.get("summary", ""),
                )
            )

        citations = self._build_evidence_citations(
            symbol=symbol,
            candidate=candidate,
            source_summary=source_summary,
            research_ledger=research_ledger,
            watchlist_entry=watchlist_entry,
            technical_state=technical_state,
        )
        citations = self._merge_evidence_citations(
            citations,
            [
                ResearchEvidenceCitation.model_validate(item)
                for item in external_research.get("evidence_citations", [])
            ],
        )

        return {
            "screening_snapshot": {
                "candidate_confidence": candidate.confidence,
                "candidate_priority": candidate.priority,
                "candidate_rationale": candidate.rationale,
                "watchlist": watchlist_entry or {},
                "research_ledger": research_ledger or {},
            },
            "fresh_external_research": external_research,
            "market_context": market_context,
            "source_summary": [item.model_dump(mode="json") for item in source_summary],
            "evidence_citations": [item.model_dump(mode="json") for item in citations],
            "market_data_freshness": market_freshness.model_dump(mode="json"),
        }

    async def _collect_focused_research_runtime_inputs(
        self,
        *,
        symbol: str,
        company_name: Optional[str] = None,
    ) -> Dict[str, Dict[str, Any]]:
        external_research, market_context = await asyncio.gather(
            self._load_bounded_external_research(
                symbol,
                company_name=company_name,
            ),
            self._load_bounded_market_context(symbol),
        )
        return {
            "external_research": external_research,
            "market_context": market_context,
        }

    async def _load_watchlist_entry(self, symbol: str) -> Dict[str, Any]:
        try:
            state_manager = await self.container.get("state_manager")
            return await state_manager.paper_trading.get_discovery_watchlist_by_symbol(symbol) or {}
        except Exception as exc:
            logger.debug("Watchlist entry unavailable for %s: %s", symbol, exc)
            return {}

    async def _load_research_ledger_entry(self, symbol: str) -> Dict[str, Any]:
        try:
            research_ledger_store = await self.container.get("research_ledger_store")
            history = await research_ledger_store.get_history(symbol, limit=1)
            return history[0] if history else {}
        except Exception as exc:
            logger.debug("Research ledger entry unavailable for %s: %s", symbol, exc)
            return {}

    async def _load_fresh_external_research(
        self,
        symbol: str,
        *,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        logger.info("Starting AI runtime web research for symbol=%s", symbol)
        try:
            market_research_service = await self.container.get("ai_market_research_service")
            result = await market_research_service.collect_symbol_research(
                symbol,
                company_name=company_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("AI runtime web research unavailable for %s: %s", symbol, exc)
            return {
                "research_timestamp": "",
                "summary": "",
                "research_summary": "",
                "news": "",
                "financial_data": "",
                "filings": "",
                "market_context": "",
                "evidence": [],
                "risks": [],
                "source_summary": [],
                "evidence_citations": [],
                "errors": ["Fresh AI runtime web research is unavailable right now."],
            }
        logger.info(
            "AI runtime web research completed for symbol=%s with %s evidence items and %s citations",
            symbol,
            len(result.get("evidence", [])),
            len(result.get("evidence_citations", [])),
        )
        return result

    async def _load_bounded_external_research(
        self,
        symbol: str,
        *,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            return await asyncio.wait_for(
                self._load_fresh_external_research(
                    symbol,
                    company_name=company_name,
                ),
                timeout=self.FOCUSED_RESEARCH_EXTERNAL_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.info(
                "Timed out fetching fresh external research for symbol=%s after %.1fs",
                symbol,
                self.FOCUSED_RESEARCH_EXTERNAL_TIMEOUT_SECONDS,
            )
            return {
                "research_timestamp": "",
                "summary": "",
                "research_summary": "",
                "news": "",
                "financial_data": "",
                "filings": "",
                "market_context": "",
                "evidence": [],
                "risks": [],
                "source_summary": [],
                "evidence_citations": [],
                "errors": [f"Codex runtime timed out after {self.FOCUSED_RESEARCH_EXTERNAL_TIMEOUT_SECONDS:.1f}s."],
            }

    async def _load_bounded_market_context(self, symbol: str) -> Dict[str, Any]:
        try:
            return await asyncio.wait_for(
                self._load_market_context(symbol),
                timeout=self.FOCUSED_RESEARCH_MARKET_CONTEXT_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            logger.info(
                "Timed out loading market context for symbol=%s after %.1fs",
                symbol,
                self.FOCUSED_RESEARCH_MARKET_CONTEXT_TIMEOUT_SECONDS,
            )
            return {
                "market_data": {},
                "market_data_freshness": {
                    "status": "missing",
                    "summary": (
                        "Live market quote preflight exceeded the bounded research budget; "
                        "current price confirmation is unavailable."
                    ),
                    "timestamp": "",
                    "age_seconds": None,
                    "provider": "",
                    "has_intraday_quote": False,
                    "has_historical_data": False,
                },
                "technical_state": {},
                "historical_data": [],
            }

    async def _load_market_context(self, symbol: str) -> Dict[str, Any]:
        market_data = None
        historical_data: List[Dict[str, Any]] = []
        kite_service = None
        market_data_service = None

        try:
            market_data_service = await self.container.get("market_data_service")
            market_data = await market_data_service.get_market_data(symbol)
        except Exception as exc:
            logger.debug("Market data unavailable for %s: %s", symbol, exc)

        if market_data_service is not None and self._needs_fresh_quote(market_data):
            try:
                prefetched_market_data = await self._prime_research_market_data_subscription(
                    symbol,
                    market_data_service,
                )
                if prefetched_market_data is not None:
                    market_data = prefetched_market_data
            except Exception as exc:
                logger.debug("Research quote preflight unavailable for %s: %s", symbol, exc)

        try:
            kite_service = await self.container.get("kite_connect_service")
            if self._needs_fresh_quote(market_data):
                quotes = await kite_service.get_quotes([symbol])
                quote = quotes.get(symbol) or quotes.get(f"NSE:{symbol}")
                if quote is not None:
                    market_data = self._market_data_from_quote(symbol, quote)
            to_date = datetime.now(timezone.utc).date()
            from_date = to_date - timedelta(days=45)
            historical_data = await kite_service.get_historical_data(
                symbol,
                from_date=from_date.isoformat(),
                to_date=to_date.isoformat(),
                interval="day",
            )
        except Exception as exc:
            logger.debug("Historical data unavailable for %s: %s", symbol, exc)

        market_freshness = self._build_market_data_freshness(market_data, historical_data)
        technical_state = self._build_technical_state(symbol, historical_data)

        return {
            "market_data": {
                "ltp": getattr(market_data, "ltp", None),
                "open_price": getattr(market_data, "open_price", None),
                "high_price": getattr(market_data, "high_price", None),
                "low_price": getattr(market_data, "low_price", None),
                "close_price": getattr(market_data, "close_price", None),
                "volume": getattr(market_data, "volume", None),
                "timestamp": getattr(market_data, "timestamp", ""),
                "provider": getattr(market_data, "provider", ""),
            }
            if market_data
            else {},
            "market_data_freshness": market_freshness.model_dump(mode="json"),
            "technical_state": technical_state,
        }

    @staticmethod
    def _needs_fresh_quote(market_data: Optional[MarketData]) -> bool:
        if market_data is None or getattr(market_data, "ltp", None) is None:
            return True
        age_seconds = AgentArtifactService._age_seconds(getattr(market_data, "timestamp", ""))
        return age_seconds is None or age_seconds > 15 * 60

    async def _prime_research_market_data_subscription(
        self,
        symbol: str,
        market_data_service: Any,
    ) -> Optional[MarketData]:
        subscribe = getattr(market_data_service, "subscribe_market_data", None)
        get_market_data = getattr(market_data_service, "get_market_data", None)
        if subscribe is None or get_market_data is None:
            return None

        await subscribe(symbol)
        deadline = asyncio.get_running_loop().time() + self.RESEARCH_QUOTE_PREFLIGHT_WAIT_SECONDS
        latest_market_data: Optional[MarketData] = None

        while True:
            latest_market_data = await get_market_data(symbol)
            if not self._needs_fresh_quote(latest_market_data):
                return latest_market_data
            if asyncio.get_running_loop().time() >= deadline:
                return latest_market_data
            await asyncio.sleep(self.RESEARCH_QUOTE_PREFLIGHT_POLL_SECONDS)

    @staticmethod
    def _market_data_from_quote(symbol: str, quote: Any) -> MarketData:
        if isinstance(quote, dict):
            ohlc = quote.get("ohlc", {}) or {}
            last_price = quote.get("last_price", 0.0)
            volume = quote.get("volume")
            timestamp = quote.get("timestamp")
            provider = str(quote.get("provider") or "zerodha_kite")
        else:
            ohlc = getattr(quote, "ohlc", {}) or {}
            last_price = getattr(quote, "last_price", 0.0)
            volume = getattr(quote, "volume", None)
            timestamp = getattr(quote, "timestamp", None)
            provider = str(getattr(quote, "provider", "") or "zerodha_kite")

        normalized_timestamp = timestamp
        if isinstance(timestamp, datetime):
            normalized_timestamp = timestamp.isoformat()
        elif not timestamp:
            normalized_timestamp = datetime.now(timezone.utc).isoformat()

        return MarketData(
            symbol=symbol,
            ltp=float(last_price or 0.0),
            open_price=ohlc.get("open"),
            high_price=ohlc.get("high"),
            low_price=ohlc.get("low"),
            close_price=ohlc.get("close"),
            volume=volume,
            timestamp=str(normalized_timestamp),
            provider=provider,
        )

    @staticmethod
    def _parse_json_blob(raw_value: Any) -> Any:
        if raw_value in (None, ""):
            return None
        if isinstance(raw_value, (dict, list)):
            return raw_value
        if isinstance(raw_value, str):
            try:
                return json.loads(raw_value)
            except json.JSONDecodeError:
                return {"raw_text": raw_value[:2000]}
        return {"raw_value": str(raw_value)}

    @staticmethod
    def _build_evidence_citations(
        *,
        symbol: str,
        candidate: Candidate,
        source_summary: List[ResearchSourceSummary],
        research_ledger: Dict[str, Any],
        watchlist_entry: Dict[str, Any],
        technical_state: Dict[str, Any],
    ) -> List[ResearchEvidenceCitation]:
        citations: List[ResearchEvidenceCitation] = []
        for source in source_summary:
            reference = source.label
            if source.source_type == "research_ledger" and research_ledger.get("id"):
                reference = f"ledger:{research_ledger['id']}"
            elif source.source_type == "discovery_watchlist" and watchlist_entry.get("id"):
                reference = f"watchlist:{watchlist_entry['id']}"
            elif source.source_type == "technical_context" and technical_state.get("window"):
                reference = f"{symbol}:{technical_state['window']}"

            citations.append(
                ResearchEvidenceCitation(
                    source_type=source.source_type,
                    label=source.label,
                    reference=reference,
                    tier=source.tier,
                    freshness=source.freshness,
                    timestamp=source.timestamp,
                )
            )
        if not citations:
            citations.append(
                ResearchEvidenceCitation(
                    source_type="candidate",
                    label="Discovery candidate",
                    reference=candidate.candidate_id,
                    tier="derived",
                    freshness="unknown",
                    timestamp=candidate.generated_at,
                )
            )
        return citations

    @staticmethod
    def _derive_analysis_mode(
        *,
        source_summary: List[ResearchSourceSummary],
        has_screening: bool,
        has_external: bool,
        has_technical: bool,
    ) -> str:
        fresh_count = sum(1 for item in source_summary if item.freshness == "fresh")
        if has_screening and has_external and has_technical and fresh_count >= 2:
            return "fresh_evidence"
        if has_screening and (has_external or has_technical):
            return "stale_evidence"
        return "insufficient_evidence"

    @staticmethod
    def _derive_research_blockers(
        *,
        analysis_mode: str,
        market_data_freshness: MarketDataFreshness,
        source_summary: List[ResearchSourceSummary],
        external_errors: List[str],
        capability_blockers: List[str],
    ) -> List[str]:
        blockers: List[str] = []
        fresh_source_count = sum(1 for item in source_summary if item.freshness == "fresh")
        fresh_external_source_count = sum(
            1
            for item in source_summary
            if item.freshness == "fresh" and AgentArtifactService._source_type_is_external(item.source_type)
        )

        if fresh_external_source_count == 0:
            blockers.append("Fresh external web evidence is unavailable for this research packet.")
        if market_data_freshness.status in {"stale", "missing", "unknown"}:
            blockers.append(
                market_data_freshness.summary
                or "Current market data is stale or unavailable; any thesis should stay watch-only."
            )
        if not any(item.source_type == "technical_context" for item in source_summary):
            blockers.append("Recent OHLCV technical context is unavailable.")
        if fresh_source_count < 2 and analysis_mode != "insufficient_evidence":
            blockers.append("Fresh evidence is thin; this packet should stay watch-only until more sources refresh.")
        if analysis_mode == "insufficient_evidence":
            blockers.append("Insufficient evidence is available to justify a trade-ready thesis.")

        blockers.extend(external_errors[:2])
        for blocker in capability_blockers:
            if (
                "market data" in blocker.lower()
                and market_data_freshness.status in {"stale", "missing", "unknown"}
                and blocker not in blockers
            ):
                blockers.append(blocker)
        return blockers

    def _finalize_research_packet(
        self,
        research: ResearchPacket,
        *,
        candidate: Candidate,
        account_id: str,
        research_inputs: Dict[str, Any],
        capability_summary: Dict[str, Any],
    ) -> ResearchPacket:
        local_source_summary = [
            ResearchSourceSummary.model_validate(item)
            for item in research_inputs.get("source_summary", [])
        ]
        model_source_summary = [
            ResearchSourceSummary.model_validate(item)
            for item in (research.source_summary or [])
        ]
        source_summary = self._merge_source_summary(local_source_summary, model_source_summary)
        source_summary = self._enforce_source_tiers(source_summary)

        local_evidence_citations = [
            ResearchEvidenceCitation.model_validate(item)
            for item in research_inputs.get("evidence_citations", [])
        ]
        model_evidence_citations = [
            ResearchEvidenceCitation.model_validate(item)
            for item in (research.evidence_citations or [])
        ]
        evidence_citations = self._merge_evidence_citations(
            local_evidence_citations,
            model_evidence_citations,
        )
        evidence_citations = self._enforce_citation_tiers(evidence_citations)
        market_data_freshness = MarketDataFreshness.model_validate(
            research_inputs.get("market_data_freshness") or {}
        )
        external_evidence_status = self._derive_external_evidence_status(
            source_summary=source_summary,
            evidence_citations=evidence_citations,
            external_errors=(research_inputs.get("fresh_external_research") or {}).get("errors", []),
        )
        analysis_mode = self._derive_analysis_mode(
            source_summary=source_summary,
            has_screening=bool(
                (research_inputs.get("screening_snapshot") or {}).get("research_ledger")
                or (research_inputs.get("screening_snapshot") or {}).get("watchlist")
            ),
            has_external=any(self._source_type_is_external(item.source_type) for item in source_summary),
            has_technical=any(item.source_type == "technical_context" for item in source_summary),
        )
        screening_confidence = round(max(0.0, min(candidate.confidence, 1.0)), 2)
        thesis_confidence = float(
            research.thesis_confidence
            or research.confidence
            or screening_confidence
        )

        fresh_source_count = sum(1 for item in source_summary if item.freshness == "fresh")
        if analysis_mode == "stale_evidence":
            thesis_confidence = min(thesis_confidence, 0.62)
        elif analysis_mode == "insufficient_evidence":
            thesis_confidence = min(thesis_confidence, 0.35)
        if external_evidence_status == "partial":
            thesis_confidence = min(thesis_confidence, 0.55)
        elif external_evidence_status == "missing":
            thesis_confidence = min(thesis_confidence, 0.35)
        if fresh_source_count < 2:
            thesis_confidence = min(thesis_confidence, 0.58)
        if not any(item.tier == "primary" for item in source_summary if self._source_type_is_external(item.source_type)):
            thesis_confidence = min(thesis_confidence, 0.57)
        if market_data_freshness.status in {"stale", "missing", "unknown"}:
            thesis_confidence = min(thesis_confidence, 0.49)
        thesis_confidence = round(max(0.0, min(thesis_confidence, 1.0)), 2)

        research_blockers = self._derive_research_blockers(
            analysis_mode=analysis_mode,
            market_data_freshness=market_data_freshness,
            source_summary=source_summary,
            external_errors=(research_inputs.get("fresh_external_research") or {}).get("errors", []),
            capability_blockers=capability_summary.get("blockers", []),
        )

        deterministic_actionability = "actionable"
        if analysis_mode == "insufficient_evidence":
            deterministic_actionability = "blocked"
        elif thesis_confidence < self.RESEARCH_ACTIONABLE_CONFIDENCE or research_blockers:
            deterministic_actionability = "watch_only"

        if research.actionability == "blocked":
            deterministic_actionability = "blocked"
        research.actionability = deterministic_actionability

        research.candidate_id = research.candidate_id or candidate.candidate_id
        research.account_id = research.account_id or account_id
        research.symbol = research.symbol or candidate.symbol
        research.analysis_mode = analysis_mode
        research.screening_confidence = screening_confidence
        research.thesis_confidence = thesis_confidence
        research.confidence = thesis_confidence
        research.external_evidence_status = external_evidence_status
        research.source_summary = source_summary
        research.evidence_citations = evidence_citations
        research.market_data_freshness = market_data_freshness
        primary_source_count, external_source_count = self._research_source_counts(source_summary)
        research.fresh_primary_source_count = primary_source_count
        research.fresh_external_source_count = external_source_count
        research.technical_context_available = self._technical_context_available(source_summary)
        research.evidence_mode = analysis_mode
        research.why_now = research.why_now or candidate.rationale

        existing_risks = {risk.lower(): risk for risk in research.risks}
        for blocker in research_blockers:
            if blocker.lower() not in existing_risks:
                research.risks.append(blocker)

        if not research.next_step:
            if research.actionability == "actionable":
                research.next_step = "Use this packet as the basis for an operator-reviewed decision packet."
            elif research.actionability == "watch_only":
                research.next_step = "Keep the symbol on watch and refresh the degraded evidence before generating a decision packet."
            else:
                research.next_step = "Do not generate a decision packet until the missing evidence is available."

        return research

    @staticmethod
    def _source_type_is_external(source_type: str) -> bool:
        normalized = (source_type or "").strip().lower()
        if not normalized:
            return False
        if normalized in {
            "stored_external_research",
            "codex_web_research",
            "claude_web_news",
            "claude_web_fundamentals",
            "exchange_disclosure",
            "company_filing",
            "company_ir",
            "reputable_financial_news",
        }:
            return True
        return normalized.startswith("claude_web_") or normalized.startswith("codex_web_")

    @staticmethod
    def _source_tier_for_type(source_type: str) -> str:
        normalized = (source_type or "").strip().lower()
        if normalized in {"exchange_disclosure", "company_filing", "company_ir"}:
            return "primary"
        if normalized in {"reputable_financial_news", "claude_web_news", "codex_web_research"}:
            return "secondary"
        return "derived"

    @classmethod
    def _enforce_source_tiers(
        cls,
        items: List[ResearchSourceSummary],
    ) -> List[ResearchSourceSummary]:
        normalized: List[ResearchSourceSummary] = []
        for item in items:
            inferred_tier = cls._source_tier_for_type(item.source_type)
            normalized.append(
                item.model_copy(
                    update={
                        "tier": inferred_tier if item.tier == "derived" and inferred_tier != "derived" else item.tier
                    }
                )
            )
        return normalized

    @classmethod
    def _enforce_citation_tiers(
        cls,
        items: List[ResearchEvidenceCitation],
    ) -> List[ResearchEvidenceCitation]:
        normalized: List[ResearchEvidenceCitation] = []
        for item in items:
            inferred_tier = cls._source_tier_for_type(item.source_type)
            normalized.append(
                item.model_copy(
                    update={
                        "tier": inferred_tier if item.tier == "derived" and inferred_tier != "derived" else item.tier
                    }
                )
            )
        return normalized

    @classmethod
    def _derive_external_evidence_status(
        cls,
        *,
        source_summary: List[ResearchSourceSummary],
        evidence_citations: List[ResearchEvidenceCitation],
        external_errors: List[str],
    ) -> str:
        external_sources = [item for item in source_summary if cls._source_type_is_external(item.source_type)]
        if not external_sources and not evidence_citations:
            return "missing"
        if external_errors:
            return "partial"
        if any(item.freshness == "fresh" for item in external_sources):
            return "fresh"
        return "partial"

    @staticmethod
    def _merge_source_summary(
        *groups: List[ResearchSourceSummary],
    ) -> List[ResearchSourceSummary]:
        merged: List[ResearchSourceSummary] = []
        seen: set[tuple[str, str, str, str]] = set()
        for group in groups:
            for item in group:
                key = (
                    item.source_type.strip().lower(),
                    item.label.strip().lower(),
                    item.timestamp.strip(),
                    item.detail.strip().lower(),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged

    @staticmethod
    def _merge_evidence_citations(
        *groups: List[ResearchEvidenceCitation],
    ) -> List[ResearchEvidenceCitation]:
        merged: List[ResearchEvidenceCitation] = []
        seen: set[tuple[str, str, str]] = set()
        for group in groups:
            for item in group:
                key = (
                    item.source_type.strip().lower(),
                    item.label.strip().lower(),
                    item.reference.strip(),
                )
                if key in seen:
                    continue
                seen.add(key)
                merged.append(item)
        return merged

    @staticmethod
    def _extract_usage_limited_message(raw_text: str) -> str:
        lowered = (raw_text or "").lower()
        if (
            "out of extra usage" in lowered
            or "rate limit" in lowered
            or "spending cap reached" in lowered
            or "spending cap" in lowered
        ):
            return (raw_text or "").strip() or "AI runtime usage is temporarily exhausted."
        return ""

    @staticmethod
    def _extract_error_response_text(exc: TradingError) -> str:
        metadata = getattr(exc.context, "metadata", {}) or {}
        nested = metadata.get("metadata") if isinstance(metadata, dict) else {}
        response_text = ""
        if isinstance(metadata, dict):
            response_text = str(metadata.get("response") or metadata.get("error") or metadata.get("provider_error") or "")
        if not response_text and isinstance(nested, dict):
            response_text = str(
                nested.get("response")
                or nested.get("error")
                or nested.get("provider_error")
                or ""
            )
        return response_text

    @classmethod
    def _build_runtime_blocker(cls, exc: TradingError, *, action: str) -> str:
        metadata = getattr(exc.context, "metadata", {}) or {}
        nested = metadata.get("metadata") if isinstance(metadata, dict) else {}
        runtime_state = ""
        if isinstance(metadata, dict):
            runtime_state = str(metadata.get("runtime_state") or "")
        if not runtime_state and isinstance(nested, dict):
            runtime_state = str(nested.get("runtime_state") or "")

        response_text = cls._extract_error_response_text(exc) or str(exc)
        lowered = response_text.lower()
        if runtime_state == "timed_out" or "timed out" in lowered or "timeout" in lowered:
            return f"AI runtime timed out during {action}. {response_text.strip()}"
        if runtime_state == "unavailable" or "runtime is unavailable" in lowered or "couldn't connect" in lowered:
            return f"AI runtime is currently unavailable for {action}. {response_text.strip()}"
        return ""

    @classmethod
    def _decision_market_data_blocker(cls, positions: List[Any]) -> str:
        stale_symbols: List[str] = []
        for position in positions:
            price_status = str(getattr(position, "market_price_status", "") or "").strip().lower()
            if price_status != "live":
                stale_symbols.append(str(getattr(position, "symbol", "UNKNOWN")))
                continue

            mark_timestamp = str(getattr(position, "market_price_timestamp", "") or "").strip()
            mark_age_seconds = cls._age_seconds(mark_timestamp)
            if mark_age_seconds is None or mark_age_seconds > cls.DECISION_MARK_FRESHNESS_THRESHOLD_SECONDS:
                stale_symbols.append(str(getattr(position, "symbol", "UNKNOWN")))

        if not stale_symbols:
            return ""

        affected = ", ".join(sorted(dict.fromkeys(stale_symbols)))
        return (
            "Decision generation requires live marks fresher than "
            f"{cls.DECISION_MARK_FRESHNESS_THRESHOLD_SECONDS}s. "
            f"Stale or missing marks detected for: {affected}."
        )

    @staticmethod
    def _clamp_confidence(value: Any) -> float:
        try:
            return round(max(0.0, min(float(value or 0.0), 1.0)), 2)
        except (TypeError, ValueError):
            return 0.0

    def _finalize_decision_packets(
        self,
        decisions: List[DecisionPacket],
        *,
        positions: List[Any],
    ) -> tuple[List[DecisionPacket], List[str], int]:
        normalized: List[DecisionPacket] = []
        blockers: List[str] = []
        position_by_symbol = {
            str(getattr(position, "symbol", "") or "").upper(): position for position in positions
        }

        for decision in decisions:
            symbol = str(decision.symbol or "").upper()
            decision.symbol = symbol
            decision.confidence = self._clamp_confidence(decision.confidence)
            position = position_by_symbol.get(symbol)

            if not decision.next_step:
                decision.next_step = "Refresh focused research and rerun decision review before changing the position."

            if decision.confidence < self.DECISION_READY_CONFIDENCE:
                if decision.confidence < self.DECISION_MIN_CONFIDENCE:
                    decision.action = "review_exit"
                    decision.next_step = (
                        "Do not change this position automatically; refresh research and review the exit manually."
                    )
                elif decision.action in {"tighten_stop", "take_profit"}:
                    decision.action = "hold"
                    decision.next_step = (
                        "Refresh focused research and rerun decision review before changing stops or taking profit."
                    )

                blocker = (
                    f"{symbol}: decision confidence {decision.confidence:.2f} is below the deterministic "
                    f"promotion threshold of {self.DECISION_READY_CONFIDENCE:.2f}."
                )
                blockers.append(blocker)
                risk_suffix = "Confidence is below the deterministic promotion threshold; operator review is required."
                if risk_suffix.lower() not in decision.risk_note.lower():
                    decision.risk_note = (
                        f"{decision.risk_note} {risk_suffix}".strip()
                        if decision.risk_note
                        else risk_suffix
                    )

            if position is not None:
                mark_status = str(getattr(position, "market_price_status", "") or "").strip().lower()
                if mark_status != "live":
                    blocker = f"{symbol}: live mark quality degraded to '{mark_status}' during decision review."
                    if blocker not in blockers:
                        blockers.append(blocker)

            normalized.append(decision)

        ready_decision_count = sum(
            1 for decision in normalized if decision.confidence >= self.DECISION_READY_CONFIDENCE
        )
        if normalized and ready_decision_count == 0:
            blockers.append("No decision packets cleared the deterministic confidence threshold.")

        deduped_blockers = list(dict.fromkeys(blockers))
        return normalized, deduped_blockers, ready_decision_count

    def _finalize_review_report(
        self,
        review: ReviewReport,
        *,
        snapshot: AgentPromptContext,
    ) -> tuple[ReviewReport, List[str]]:
        confidence = self._derive_review_confidence(snapshot=snapshot, review=review)
        review.confidence = confidence

        blockers: List[str] = []
        if confidence < self.REVIEW_READY_CONFIDENCE:
            blocker = (
                "Daily review confidence is below the promotion threshold; treat this review as observational until more realized outcomes accumulate."
            )
            blockers.append(blocker)
            if blocker not in review.risk_flags:
                review.risk_flags.append(blocker)

        return review, blockers

    def _derive_review_confidence(
        self,
        *,
        snapshot: AgentPromptContext,
        review: ReviewReport,
    ) -> float:
        confidence = 0.35
        if snapshot.positions:
            confidence += 0.15
        if snapshot.recent_trades:
            confidence += 0.20
        if (snapshot.learning_summary or {}).get("total_evaluations", 0):
            confidence += 0.10
        if review.top_lessons:
            confidence += 0.10
        if review.strengths or review.weaknesses or review.risk_flags:
            confidence += 0.05
        if review.strategy_proposals:
            confidence += 0.05

        if not snapshot.recent_trades:
            confidence = min(confidence, 0.58)
        elif len(snapshot.recent_trades) == 1:
            confidence = min(confidence, 0.67)

        return self._clamp_confidence(confidence)

    @staticmethod
    def _build_market_data_freshness(
        market_data: Any,
        historical_data: List[Dict[str, Any]],
    ) -> MarketDataFreshness:
        timestamp = getattr(market_data, "timestamp", "") if market_data else ""
        provider = getattr(market_data, "provider", "") if market_data else ""
        age_seconds = AgentArtifactService._age_seconds(timestamp)
        has_quote = market_data is not None and getattr(market_data, "ltp", None) is not None
        has_historical = bool(historical_data)

        if has_quote and age_seconds is not None and age_seconds <= 15 * 60:
            status = "fresh"
            summary = "Intraday quote is current enough for operator review."
        elif has_quote and age_seconds is not None and age_seconds <= 24 * 60 * 60:
            status = "delayed"
            summary = "Quote exists but is not intraday-fresh; use for context, not automation."
        elif has_historical:
            last_candle = historical_data[-1]
            candle_ts = str(last_candle.get("date") or "")
            age_seconds = AgentArtifactService._age_seconds(candle_ts)
            timestamp = candle_ts
            status = "stale"
            summary = "Only historical OHLCV context is available; live price confirmation is stale."
        else:
            status = "missing"
            summary = "No current market quote or historical context is available."

        return MarketDataFreshness(
            status=status,
            summary=summary,
            timestamp=timestamp,
            age_seconds=age_seconds,
            provider=provider,
            has_intraday_quote=has_quote,
            has_historical_data=has_historical,
        )

    @staticmethod
    def _build_technical_state(symbol: str, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not historical_data:
            return {}

        closes = [float(item.get("close") or 0.0) for item in historical_data if item.get("close") is not None]
        volumes = [float(item.get("volume") or 0.0) for item in historical_data if item.get("volume") is not None]
        if not closes:
            return {}

        latest = historical_data[-1]
        latest_close = closes[-1]
        five_day_base = closes[-5] if len(closes) >= 5 else closes[0]
        twenty_day_base = closes[-20] if len(closes) >= 20 else closes[0]
        average_volume = sum(volumes[-20:]) / max(len(volumes[-20:]), 1) if volumes else 0.0
        latest_volume = float(latest.get("volume") or 0.0)
        five_day_return = ((latest_close - five_day_base) / five_day_base * 100) if five_day_base else 0.0
        twenty_day_return = ((latest_close - twenty_day_base) / twenty_day_base * 100) if twenty_day_base else 0.0
        volume_ratio = (latest_volume / average_volume) if average_volume else 0.0
        trend = "uptrend" if twenty_day_return > 3 else "downtrend" if twenty_day_return < -3 else "range"

        return {
            "timestamp": str(latest.get("date") or ""),
            "window": f"{min(len(closes), 20)}d",
            "last_close": round(latest_close, 2),
            "five_day_return_pct": round(five_day_return, 2),
            "twenty_day_return_pct": round(twenty_day_return, 2),
            "volume_ratio_vs_20d": round(volume_ratio, 2),
            "trend": trend,
            "summary": (
                f"{symbol} is in {trend} with {five_day_return:.2f}% over 5d, "
                f"{twenty_day_return:.2f}% over 20d, and {volume_ratio:.2f}x 20d volume."
            ),
        }

    @staticmethod
    def _age_seconds(value: Any) -> Optional[float]:
        parsed = AgentArtifactService._parse_timestamp(value)
        if parsed is None:
            return None
        now = datetime.now(timezone.utc)
        return max((now - parsed).total_seconds(), 0.0)

    @staticmethod
    def _freshness_label(value: Any, *, fresh_after: timedelta) -> str:
        age_seconds = AgentArtifactService._age_seconds(value)
        if age_seconds is None:
            return "unknown"
        return "fresh" if age_seconds <= fresh_after.total_seconds() else "stale"

    @staticmethod
    def _parse_timestamp(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            return None
        return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    async def _build_prompt_context(
        self,
        account_id: str,
        positions_limit: int,
        trades_limit: int,
    ) -> AgentPromptContext:
        account_manager = await self.container.get("paper_trading_account_manager")
        capability_service = await self.container.get("trading_capability_service")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        positions = await account_manager.get_open_positions(account_id)
        closed_trades = await account_manager.get_closed_trades(account_id, limit=trades_limit)
        metrics = await account_manager.get_performance_metrics(account_id, period="month")
        capability_snapshot = await capability_service.get_snapshot(account_id=account_id)

        position_context = [
            {
                "symbol": position.symbol,
                "quantity": position.quantity,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "unrealized_pnl": position.unrealized_pnl,
                "unrealized_pnl_pct": position.unrealized_pnl_pct,
                "days_held": position.days_held,
                "stop_loss": position.stop_loss,
                "target_price": position.target_price,
                "mark_status": position.market_price_status,
            }
            for position in positions[:positions_limit]
        ]
        trade_context = [
            {
                "symbol": trade.symbol,
                "trade_type": trade.trade_type,
                "entry_price": trade.entry_price,
                "exit_price": trade.exit_price,
                "realized_pnl": trade.realized_pnl,
                "realized_pnl_pct": trade.realized_pnl_pct,
                "holding_period_days": trade.holding_period_days,
            }
            for trade in closed_trades[:trades_limit]
        ]

        learning_summary: Dict[str, Any] = {}
        try:
            learning_service = await self.container.get("paper_trading_learning_service")
            learning_summary = (await learning_service.get_learning_summary(account_id)).model_dump(mode="json")
        except Exception:
            learning_summary = {}

        improvement_report: Dict[str, Any] = {}
        try:
            improvement_service = await self.container.get("paper_trading_improvement_service")
            improvement_report = (
                await improvement_service.get_improvement_report(account_id, refresh=False)
            ).model_dump(mode="json")
        except Exception:
            improvement_report = {}

        return AgentPromptContext(
            account_id=account_id,
            account_summary={
                "balance": account.current_balance,
                "buying_power": account.buying_power,
                "monthly_pnl": account.monthly_pnl,
                "win_rate": metrics.get("win_rate", 0.0),
                "profit_factor": metrics.get("profit_factor", 0.0),
                "open_positions": len(positions),
                "recent_closed_trades": len(closed_trades),
            },
            positions=position_context,
            recent_trades=trade_context,
            capability_summary={
                "overall_status": capability_snapshot.overall_status.value,
                "automation_allowed": capability_snapshot.automation_allowed,
                "blockers": capability_snapshot.blockers,
            },
            learning_summary=learning_summary,
            improvement_report=improvement_report,
        )

    @staticmethod
    def _compact_learning_summary(learning_summary: Dict[str, Any]) -> Dict[str, Any]:
        if not learning_summary:
            return {}
        return {
            "total_evaluations": learning_summary.get("total_evaluations", 0),
            "wins": learning_summary.get("wins", 0),
            "losses": learning_summary.get("losses", 0),
            "flats": learning_summary.get("flats", 0),
            "average_pnl_percentage": learning_summary.get("average_pnl_percentage", 0.0),
            "top_lessons": list(learning_summary.get("top_lessons") or [])[:3],
            "improvement_focus": list(learning_summary.get("improvement_focus") or [])[:3],
        }

    @staticmethod
    def _compact_improvement_report(improvement_report: Dict[str, Any]) -> Dict[str, Any]:
        if not improvement_report:
            return {}

        def _compact_proposal(item: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "proposal_id": item.get("proposal_id", ""),
                "title": item.get("title", ""),
                "decision": item.get("decision", ""),
                "summary": item.get("summary", ""),
                "guardrail": item.get("guardrail", ""),
                "net_benefit_amount": item.get("net_benefit_amount", 0.0),
                "candidate_win_rate": item.get("candidate_win_rate", 0.0),
            }

        promotable = [
            _compact_proposal(item)
            for item in list(improvement_report.get("promotable_proposals") or [])[:2]
            if isinstance(item, dict)
        ]
        watch = [
            _compact_proposal(item)
            for item in list(improvement_report.get("watch_proposals") or [])[:2]
            if isinstance(item, dict)
        ]
        return {
            "baseline_trade_count": improvement_report.get("baseline_trade_count", 0),
            "evaluated_trade_count": improvement_report.get("evaluated_trade_count", 0),
            "promotable_proposals": promotable,
            "watch_proposals": watch,
        }

    @staticmethod
    def _compact_symbol_learning(symbol_learning: Dict[str, Any]) -> Dict[str, Any]:
        if not symbol_learning:
            return {}

        latest_research = symbol_learning.get("latest_research") or {}
        compact_latest_research = {}
        if isinstance(latest_research, dict) and latest_research:
            compact_latest_research = {
                "analysis_mode": latest_research.get("analysis_mode", ""),
                "actionability": latest_research.get("actionability", ""),
                "thesis": latest_research.get("thesis", ""),
                "why_now": latest_research.get("why_now", ""),
                "generated_at": latest_research.get("generated_at") or latest_research.get("created_at") or "",
            }

        return {
            "recent_lessons": list(symbol_learning.get("recent_lessons") or [])[:3],
            "recent_improvements": list(symbol_learning.get("recent_improvements") or [])[:3],
            "latest_research": compact_latest_research,
        }

    def _compact_research_context(
        self,
        *,
        candidate: Candidate,
        snapshot: AgentPromptContext,
        symbol_learning: Dict[str, Any],
        research_inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        return {
            "candidate": {
                "candidate_id": candidate.candidate_id,
                "symbol": candidate.symbol,
                "company_name": candidate.company_name,
                "priority": candidate.priority,
                "source": candidate.source,
                "confidence": candidate.confidence,
                "rationale": candidate.rationale,
                "next_step": candidate.next_step,
                "generated_at": candidate.generated_at,
            },
            "account_summary": snapshot.account_summary,
            "capability_summary": snapshot.capability_summary,
            "learning_summary": self._compact_learning_summary(snapshot.learning_summary),
            "improvement_report": self._compact_improvement_report(snapshot.improvement_report),
            "symbol_learning": self._compact_symbol_learning(symbol_learning),
            "open_positions": snapshot.positions[:2],
            "recent_trades": snapshot.recent_trades[:3],
            "focused_research_inputs": research_inputs,
        }

    @staticmethod
    def _deterministic_strategy_proposals(improvement_report: Dict[str, Any]) -> List[StrategyProposal]:
        promotable = improvement_report.get("promotable_proposals", []) if improvement_report else []
        proposals: List[StrategyProposal] = []
        for item in promotable[:3]:
            proposals.append(
                StrategyProposal(
                    proposal_id=item.get("proposal_id", ""),
                    title=item.get("title", "Benchmarked strategy improvement"),
                    recommendation=item.get("summary", item.get("rationale", "")),
                    rationale=item.get("rationale", ""),
                    guardrail=item.get("guardrail", ""),
                )
            )
        return proposals

    @staticmethod
    def _resolve_research_candidate(
        *,
        discovery: DiscoveryEnvelope,
        candidate_id: Optional[str],
        symbol: Optional[str],
    ) -> Optional[Candidate]:
        if candidate_id:
            for candidate in discovery.candidates:
                if candidate.candidate_id == candidate_id:
                    return candidate

        if symbol:
            normalized = symbol.upper()
            for candidate in discovery.candidates:
                if candidate.symbol.upper() == normalized:
                    return candidate
            return Candidate(
                candidate_id=candidate_id or f"symbol:{normalized.lower()}",
                symbol=normalized,
                source="operator_selected_symbol",
                priority="medium",
                confidence=0.5,
                rationale="Operator requested a focused research packet for this symbol.",
                next_step="Validate the thesis before generating a decision packet.",
            )

        if discovery.candidates:
            for candidate in discovery.candidates:
                if (
                    candidate.lifecycle_state == "fresh_queue"
                    and candidate.confidence >= AgentArtifactService.DISCOVERY_RESEARCH_READY_CONFIDENCE
                ):
                    return candidate
            for candidate in discovery.candidates:
                if candidate.lifecycle_state == "fresh_queue":
                    return candidate

        return None

    @staticmethod
    def _eligible_loop_candidates(
        discovery: DiscoveryEnvelope,
        *,
        preferred_candidate: Optional[Candidate] = None,
    ) -> List[Candidate]:
        candidates = [candidate for candidate in discovery.candidates if candidate.lifecycle_state == "fresh_queue"]
        ordered: List[Candidate] = []
        if preferred_candidate is not None:
            ordered.append(preferred_candidate)
        seen = {candidate.candidate_id for candidate in ordered}
        for candidate in candidates:
            if candidate.candidate_id not in seen:
                ordered.append(candidate)
        return ordered[: AgentArtifactService.MAX_RESEARCH_ATTEMPTS_PER_SESSION]

    def _get_cached_research(
        self,
        account_id: str,
        *,
        candidate_id: Optional[str],
        symbol: Optional[str],
    ) -> Optional[ResearchPacket]:
        cache = self._research_cache.get(account_id, {})
        if candidate_id and candidate_id in cache:
            return cache[candidate_id]
        if symbol:
            return cache.get(f"symbol:{symbol.upper()}")
        return cache.get("_latest")

    def _store_research(self, account_id: str, research: ResearchPacket) -> None:
        cache = self._research_cache.setdefault(account_id, {})
        cache["_latest"] = research
        if research.candidate_id:
            cache[research.candidate_id] = research
        if research.symbol:
            cache[f"symbol:{research.symbol.upper()}"] = research

    async def _run_structured_role(
        self,
        *,
        client_type: str,
        role_name: str,
        system_prompt: str,
        prompt: str,
        output_model: Type[T],
        allowed_tools: List[str],
        session_id: str,
        model: Optional[str] = None,
        max_turns: int = 2,
        max_budget_usd: Optional[float] = None,
        timeout_seconds: float = 45.0,
    ) -> tuple[T, Dict[str, Any]]:
        del client_type, allowed_tools, max_turns, max_budget_usd

        runtime_client = await self.container.get("codex_runtime_client")
        runtime_config = self.container.config.ai_runtime
        schema = _normalize_output_schema(output_model.model_json_schema())
        default_model_by_role = {
            "research": self.MODEL_ROUTE_RESEARCH,
            "review": self.MODEL_ROUTE_DECISION,
            "decision": self.MODEL_ROUTE_DECISION,
            "discovery": self.MODEL_ROUTE_DISCOVERY,
            "triage": self.MODEL_ROUTE_TRIAGE,
        }
        default_reasoning_by_role = {
            "research": "medium",
            "review": "low",
            "decision": "low",
            "discovery": "low",
            "triage": "minimal",
        }
        compact_models_supported = self._runtime_supports_compact_models(
            getattr(runtime_config, "mode", ""),
        )
        selected_model = (
            model
            if model and (model.startswith("gpt-") or model.startswith("codex"))
            else default_model_by_role.get(role_name, runtime_config.codex_model)
        )
        if (
            not compact_models_supported
            and selected_model in {"gpt-5-mini", "gpt-5-nano"}
        ):
            selected_model = runtime_config.codex_model
        reasoning = default_reasoning_by_role.get(role_name, runtime_config.codex_reasoning_light)
        strict_prompt = (
            f"{prompt}\n\n"
            "Return only valid JSON with no markdown, commentary, or code fences.\n"
            "The JSON must match the provided structured output schema exactly."
        )
        try:
            prompt_cache_key = f"paper-trading:{role_name}:{session_id.split(':')[0]}"
            request_payload = {
                "system_prompt": system_prompt,
                "prompt": strict_prompt,
                "output_schema": schema,
                "model": selected_model,
                "reasoning": reasoning,
                "prompt_cache_key": prompt_cache_key,
                "timeout_seconds": timeout_seconds,
                "working_directory": str(self.container.config.project_dir),
                "session_id": session_id,
            }
            if role_name == "research":
                response = await runtime_client.run_focused_research(request_payload)
                payload = response.get("research")
            elif role_name == "review":
                response = await runtime_client.run_improvement_review(request_payload)
                payload = response.get("review")
            else:
                response = await runtime_client.run_structured(
                    system_prompt=system_prompt,
                    prompt=strict_prompt,
                    output_schema=schema,
                    model=selected_model,
                    reasoning=reasoning,
                    prompt_cache_key=prompt_cache_key,
                    timeout_seconds=timeout_seconds,
                    web_search_enabled=False,
                    network_access_enabled=False,
                    working_directory=str(self.container.config.project_dir),
                        session_id=session_id,
                )
                payload = response.get("output")

            provider_metadata = response.get("provider_metadata") or {}
            usage = response.get("usage")
            if usage is not None and isinstance(provider_metadata, dict):
                provider_metadata = {
                    **provider_metadata,
                    "usage": usage,
                }

            return (
                output_model.model_validate(payload or {}),
                provider_metadata,
            )
        except CodexRuntimeError as exc:
            usage_limit_message = self._extract_usage_limited_message(str(exc))
            if usage_limit_message or exc.usage_limited:
                limit_message = usage_limit_message or str(exc)
                record_claude_runtime_limit(limit_message)
                raise TradingError(
                    f"AI runtime is usage-limited. {limit_message}",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={
                        "rate_limit_info": {
                            "status": "exhausted",
                            "message": limit_message,
                        }
                    },
                ) from exc
            if exc.timed_out:
                raise TradingError(
                    f"AI runtime timed out during {role_name} generation.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={
                        "runtime_state": "timed_out",
                        "provider_error": str(exc),
                    },
                ) from exc
            if not exc.authenticated or exc.status_code in {503, 504}:
                raise TradingError(
                    f"AI runtime is currently unavailable for {role_name} generation.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={
                        "runtime_state": "unavailable",
                        "provider_error": str(exc),
                    },
                ) from exc
            raise TradingError(
                f"{role_name.title()} agent runtime failed: {exc}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                metadata={"error": str(exc)},
            ) from exc

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _try_parse_embedded_json(response_text: str) -> Optional[Dict[str, Any]]:
        fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if fenced_match:
            try:
                return json.loads(fenced_match.group(1))
            except json.JSONDecodeError:
                pass

        object_start = response_text.find("{")
        if object_start < 0:
            return None

        try:
            payload, _ = json.JSONDecoder().raw_decode(response_text[object_start:])
            return payload if isinstance(payload, dict) else None
        except json.JSONDecodeError:
            return None


class DecisionEnvelopePayload(BaseModel):
    decisions: List[DecisionPacket]
