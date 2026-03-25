"""Context-bounded Claude agent artifact generation for paper trading."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import AgentDefinition
from pydantic import BaseModel

from src.auth.claude_auth import get_claude_status, record_claude_runtime_limit
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.core.sdk_helpers import (
    query_only_with_timeout,
    receive_response_with_timeout,
)
from src.models.agent_artifacts import (
    AgentPromptContext,
    Candidate,
    DecisionEnvelope,
    DecisionPacket,
    DiscoveryEnvelope,
    MarketDataFreshness,
    ResearchEnvelope,
    ResearchEvidenceCitation,
    ResearchPacket,
    ResearchSourceSummary,
    ReviewEnvelope,
    ReviewReport,
    StrategyProposal,
)
from src.models.market_data import MarketData
from src.services.claude_agent.context_builder import ContextBuilder

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class AgentArtifactService:
    """Produce typed paper-trading artifacts with bounded Claude context."""

    def __init__(self, container: "DependencyContainer"):
        self.container = container
        self.context_builder = ContextBuilder(token_limit=1800)
        self._decision_cache: Dict[str, DecisionEnvelope] = {}
        self._review_cache: Dict[str, ReviewEnvelope] = {}
        self._research_cache: Dict[str, Dict[str, ResearchPacket]] = {}

    @staticmethod
    def _claude_usage_exhausted(claude_status: Any) -> bool:
        """Return whether Claude is authenticated but temporarily usage-limited."""
        rate_limit_info = getattr(claude_status, "rate_limit_info", {}) or {}
        return rate_limit_info.get("status") == "exhausted"

    @staticmethod
    def _claude_blockers(claude_status: Any, *, action: str) -> List[str]:
        """Build a truthful blocker message for Claude-dependent workflows."""
        rate_limit_info = getattr(claude_status, "rate_limit_info", {}) or {}
        if rate_limit_info.get("status") == "exhausted":
            message = rate_limit_info.get("message") or "Claude usage is temporarily exhausted."
            return [f"Claude runtime is usage-limited for {action}. {message}"]
        return [f"Claude runtime is not ready for {action}."]

    async def get_discovery_view(self, account_id: str, limit: int = 10) -> DiscoveryEnvelope:
        """Return watchlist-backed discovery candidates without inflating Claude context."""
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
                context_mode="watchlist_only",
                blockers=["Stock discovery service is unavailable."],
                artifact_count=0,
                candidates=[],
            )

        watchlist = await discovery_service.get_watchlist(limit=limit)
        open_positions = await account_manager.get_open_positions(account_id)
        held_symbols = {position.symbol for position in open_positions}

        candidates: List[Candidate] = []
        for item in watchlist:
            symbol = item.get("symbol")
            if not symbol or symbol in held_symbols:
                continue
            confidence = float(item.get("confidence_score") or 0.0)
            recommendation = str(item.get("recommendation") or "WATCH").upper()
            if recommendation in {"BUY", "ACCUMULATE"}:
                priority = "high"
            elif confidence >= 0.6:
                priority = "medium"
            else:
                priority = "low"

            candidates.append(
                Candidate(
                    candidate_id=str(item.get("id") or uuid.uuid4()),
                    symbol=symbol,
                    company_name=item.get("company_name"),
                    sector=item.get("sector"),
                    source=str(item.get("discovery_source") or "watchlist"),
                    priority=priority,
                    confidence=max(0.0, min(confidence, 1.0)),
                    rationale=str(item.get("discovery_reason") or item.get("recommendation") or "Discovery watchlist candidate"),
                    next_step="Open a focused research packet before making any trade decision.",
                    generated_at=str(item.get("updated_at") or item.get("created_at") or self._utc_now()),
                )
            )

        status = "ready" if candidates else "empty"
        blockers = [] if candidates else ["No active discovery candidates are available in the watchlist."]

        return DiscoveryEnvelope(
            status=status,
            context_mode="watchlist_only",
            blockers=blockers,
            artifact_count=len(candidates),
            candidates=candidates[:limit],
        )

    async def get_research_view(
        self,
        account_id: str,
        *,
        candidate_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 10,
        refresh: bool = False,
    ) -> ResearchEnvelope:
        """Generate a focused research packet for one candidate only."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        if not refresh:
            cached = self._get_cached_research(account_id, candidate_id=candidate_id, symbol=symbol)
            if cached is not None:
                return ResearchEnvelope(
                    status="ready",
                    context_mode="single_candidate_research",
                    blockers=[],
                    artifact_count=1,
                    research=cached,
                )

        claude_status = await get_claude_status()
        if not claude_status.is_valid or self._claude_usage_exhausted(claude_status):
            return ResearchEnvelope(
                status="blocked",
                context_mode="single_candidate_research",
                blockers=self._claude_blockers(claude_status, action="research generation"),
                artifact_count=0,
                research=None,
            )

        if not refresh:
            return ResearchEnvelope(
                status="empty",
                context_mode="single_candidate_research",
                blockers=["Run research from Discovery to create a focused research packet."],
                artifact_count=0,
                research=None,
            )

        discovery = await self.get_discovery_view(account_id, limit=limit)
        candidate = self._resolve_research_candidate(
            discovery=discovery,
            candidate_id=candidate_id,
            symbol=symbol,
        )
        logger.info(
            "Focused research requested for account=%s candidate_id=%s symbol=%s resolved_symbol=%s",
            account_id,
            candidate_id,
            symbol,
            getattr(candidate, "symbol", None),
        )
        if candidate is None:
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
                research=None,
            )

        snapshot = await self._build_prompt_context(account_id, positions_limit=3, trades_limit=4)
        try:
            learning_service = await self.container.get("paper_trading_learning_service")
            symbol_learning = await learning_service.get_symbol_learning_context(account_id, candidate.symbol)
        except Exception:
            learning_service = None
            symbol_learning = {}
        research_inputs = await self._build_focused_research_inputs(
            account_id=account_id,
            candidate=candidate,
            snapshot=snapshot,
            symbol_learning=symbol_learning,
        )
        logger.info(
            "Focused research inputs prepared for account=%s symbol=%s with %s sources",
            account_id,
            candidate.symbol,
            len(research_inputs.get("source_summary", [])),
        )
        serialized_context = json.dumps(
            {
                "candidate": candidate.model_dump(mode="json"),
                "account_summary": snapshot.account_summary,
                "capability_summary": snapshot.capability_summary,
                "learning_summary": snapshot.learning_summary,
                "improvement_report": snapshot.improvement_report,
                "symbol_learning": symbol_learning,
                "open_positions": snapshot.positions,
                "recent_trades": snapshot.recent_trades,
                "focused_research_inputs": research_inputs,
            },
            indent=2,
        )
        prompt = (
            "Create a focused research packet for a single swing-trading candidate.\n"
            "Use only the provided context. Fresh external web research has already been captured in the context when available.\n"
            "Do not invent catalysts, prices, filings, or technical levels.\n"
            "Separate discovery screening confidence from thesis confidence.\n"
            "Base the thesis on verifiable evidence, then state clearly when evidence is stale or missing.\n"
            "The packet must answer why_now, supporting evidence, key risks, invalidation, actionability, and the next operator step.\n"
            "If evidence is thin or stale, downgrade actionability instead of bluffing certainty.\n"
            f"Context:\n{serialized_context}"
        )

        try:
            research = await self._run_structured_role(
                client_type=f"agent_research_{account_id}",
                role_name="research",
                system_prompt=(
                    "You are the Research Agent for Robo Trader. "
                    "Produce a single-candidate research packet with explicit evidence and clear invalidation."
                ),
                prompt=prompt,
                output_model=ResearchPacket,
                allowed_tools=[],
                session_id=f"research:{account_id}:{candidate.candidate_id}",
                model="haiku",
                max_turns=3,
                max_budget_usd=0.75,
                timeout_seconds=45.0,
            )
        except TradingError as exc:
            usage_limit_message = self._extract_usage_limited_message(str(exc))
            if not usage_limit_message:
                metadata = getattr(exc.context, "metadata", {}) or {}
                nested = metadata.get("metadata") if isinstance(metadata, dict) else {}
                response_text = ""
                if isinstance(metadata, dict):
                    response_text = str(metadata.get("response") or metadata.get("error") or "")
                if not response_text and isinstance(nested, dict):
                    response_text = str(nested.get("response") or nested.get("error") or "")
                usage_limit_message = self._extract_usage_limited_message(response_text)
            if usage_limit_message:
                record_claude_runtime_limit(usage_limit_message)
                return ResearchEnvelope(
                    status="blocked",
                    context_mode="single_candidate_research",
                    blockers=[f"Claude runtime is usage-limited for research generation. {usage_limit_message}"],
                    artifact_count=0,
                    research=None,
                )
            raise
        logger.info(
            "Focused research synthesis completed for account=%s symbol=%s actionability=%s",
            account_id,
            candidate.symbol,
            getattr(research, "actionability", None),
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

        self._store_research(account_id, research)
        if learning_service is not None:
            await learning_service.record_research_packet(account_id, candidate.candidate_id, research)

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
            research=research,
        )

    async def get_decision_view(self, account_id: str, limit: int = 3, refresh: bool = False) -> DecisionEnvelope:
        """Generate compact position-level decision packets via Claude."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        if not refresh and account_id in self._decision_cache:
            return self._decision_cache[account_id]

        claude_status = await get_claude_status()
        if not claude_status.is_valid or self._claude_usage_exhausted(claude_status):
            return DecisionEnvelope(
                status="blocked",
                context_mode="delta_position_review",
                blockers=self._claude_blockers(claude_status, action="decision generation"),
                artifact_count=0,
                decisions=[],
            )

        if not refresh:
            return DecisionEnvelope(
                status="empty",
                context_mode="delta_position_review",
                blockers=["Run decision review to generate current position guidance."],
                artifact_count=0,
                decisions=[],
            )

        positions = await account_manager.get_open_positions(account_id)
        if not positions:
            return DecisionEnvelope(
                status="empty",
                context_mode="delta_position_review",
                blockers=["No open positions are available for decision review."],
                artifact_count=0,
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

        response = await self._run_structured_role(
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

        envelope = DecisionEnvelope(
            status="ready" if response.decisions else "empty",
            context_mode="delta_position_review",
            blockers=[] if response.decisions else ["Claude returned no decision packets."],
            artifact_count=len(response.decisions),
            decisions=response.decisions,
        )
        self._decision_cache[account_id] = envelope
        return envelope

    async def get_review_view(self, account_id: str, refresh: bool = False) -> ReviewEnvelope:
        """Generate a compact end-of-day style review report via Claude."""
        account_manager = await self.container.get("paper_trading_account_manager")
        account = await account_manager.get_account(account_id)
        if account is None:
            raise TradingError(
                f"Paper trading account '{account_id}' was not found.",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

        if not refresh and account_id in self._review_cache:
            return self._review_cache[account_id]

        claude_status = await get_claude_status()
        if not claude_status.is_valid or self._claude_usage_exhausted(claude_status):
            return ReviewEnvelope(
                status="blocked",
                context_mode="delta_daily_review",
                blockers=self._claude_blockers(claude_status, action="review generation"),
                artifact_count=0,
                review=None,
            )

        if not refresh:
            return ReviewEnvelope(
                status="empty",
                context_mode="delta_daily_review",
                blockers=["Run daily review to generate a fresh review report."],
                artifact_count=0,
                review=None,
            )

        snapshot = await self._build_prompt_context(account_id, positions_limit=5, trades_limit=10)
        if not snapshot.positions and not snapshot.recent_trades:
            return ReviewEnvelope(
                status="empty",
                context_mode="delta_daily_review",
                blockers=["No positions or recent trades are available for review."],
                artifact_count=0,
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

        review = await self._run_structured_role(
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

        envelope = ReviewEnvelope(
            status="ready",
            context_mode="delta_daily_review",
            blockers=[],
            artifact_count=1,
            review=review,
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
    ) -> Dict[str, Any]:
        symbol = candidate.symbol.upper()
        watchlist_entry = await self._load_watchlist_entry(symbol)
        research_ledger = await self._load_research_ledger_entry(symbol)
        external_research = await self._load_fresh_external_research(
            symbol,
            company_name=candidate.company_name,
        )
        market_context = await self._load_market_context(symbol)

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
        logger.info("Starting Claude web research for symbol=%s", symbol)
        try:
            market_research_service = await self.container.get("claude_market_research_service")
            result = await market_research_service.collect_symbol_research(
                symbol,
                company_name=company_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("Claude web research unavailable for %s: %s", symbol, exc)
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
                "errors": ["Fresh Claude web research is unavailable right now."],
            }
        logger.info(
            "Claude web research completed for symbol=%s with %s evidence items and %s citations",
            symbol,
            len(result.get("evidence", [])),
            len(result.get("evidence_citations", [])),
        )
        return result

    async def _load_market_context(self, symbol: str) -> Dict[str, Any]:
        market_data = None
        historical_data: List[Dict[str, Any]] = []
        kite_service = None

        try:
            market_data_service = await self.container.get("market_data_service")
            market_data = await market_data_service.get_market_data(symbol)
        except Exception as exc:
            logger.debug("Market data unavailable for %s: %s", symbol, exc)

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
            if "market data" in blocker.lower() and blocker not in blockers:
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
        market_data_freshness = MarketDataFreshness.model_validate(
            research_inputs.get("market_data_freshness") or {}
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
        if fresh_source_count < 2:
            thesis_confidence = min(thesis_confidence, 0.58)
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
        elif thesis_confidence < 0.55 or research_blockers:
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
        research.source_summary = source_summary
        research.evidence_citations = evidence_citations
        research.market_data_freshness = market_data_freshness
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
            "claude_web_news",
            "claude_web_fundamentals",
            "exchange_disclosure",
            "company_filing",
            "company_ir",
            "reputable_financial_news",
        }:
            return True
        return normalized.startswith("claude_web_")

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
            return (raw_text or "").strip() or "Claude usage is temporarily exhausted."
        return ""

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
            return discovery.candidates[0]

        return None

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
        model: str = "haiku",
        max_turns: int = 2,
        max_budget_usd: Optional[float] = None,
        timeout_seconds: float = 45.0,
    ) -> T:
        manager = await ClaudeSDKClientManager.get_instance()
        schema = output_model.model_json_schema()
        strict_prompt = (
            f"{prompt}\n\n"
            "Return only valid JSON with no markdown, commentary, or code fences.\n"
            "The JSON must validate against this schema:\n"
            f"{json.dumps(schema, indent=2)}"
        )
        options = ClaudeAgentOptions(
            allowed_tools=allowed_tools,
            max_turns=max_turns,
            max_budget_usd=max_budget_usd,
            model=model,
            output_format={"type": "json_schema", "schema": schema},
            agents={
                role_name: AgentDefinition(
                    description=f"{role_name.title()} role for Robo Trader",
                    prompt=system_prompt,
                    tools=allowed_tools,
                    model=model,
                )
            },
            system_prompt=system_prompt,
        )
        # Structured artifact runs are short-lived and schema-specific. Reuse across
        # requests can poison later runs after an SDK session error, so recreate and
        # clean up the client on every run.
        client = await manager.get_client(client_type, options, force_recreate=True)
        try:
            await query_only_with_timeout(client, strict_prompt, timeout=min(timeout_seconds, 30.0))
            response_parts: List[str] = []
            async for message in receive_response_with_timeout(client, timeout=timeout_seconds):
                structured_output = getattr(message, "structured_output", None)
                if structured_output is not None:
                    return output_model.model_validate(structured_output)

                subtype = getattr(message, "subtype", None)
                if subtype == "error_max_structured_output_retries":
                    raise TradingError(
                        f"{role_name.title()} agent exhausted structured-output retries.",
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        recoverable=True,
                    )

                if hasattr(message, "content"):
                    for content_block in message.content:
                        if hasattr(content_block, "text"):
                            response_parts.append(content_block.text)
                elif getattr(message, "result", None):
                    response_parts.append(str(message.result))

            response_text = "\n".join(part for part in response_parts if part).strip()
            usage_limit_message = self._extract_usage_limited_message(response_text)
            if usage_limit_message:
                record_claude_runtime_limit(usage_limit_message)
                raise TradingError(
                    f"Claude runtime is usage-limited. {usage_limit_message}",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.MEDIUM,
                    recoverable=True,
                    metadata={
                        "rate_limit_info": {
                            "status": "exhausted",
                            "message": usage_limit_message,
                        }
                    },
                )
            try:
                payload = json.loads(response_text)
            except json.JSONDecodeError as exc:
                payload = self._try_parse_embedded_json(response_text)
                if payload is not None:
                    return output_model.model_validate(payload)
                raise TradingError(
                    f"{role_name.title()} agent did not return valid JSON.",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True,
                    metadata={"response": response_text, "error": str(exc)},
                ) from exc
            return output_model.model_validate(payload)
        finally:
            await manager.cleanup_client(client_type)

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
