"""Context-bounded Claude agent artifact generation for paper trading."""

from __future__ import annotations

import json
import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import AgentDefinition
from pydantic import BaseModel

from src.auth.claude_auth import get_claude_status_cached
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.core.sdk_helpers import query_with_timeout
from src.models.agent_artifacts import (
    AgentPromptContext,
    Candidate,
    DecisionEnvelope,
    DecisionPacket,
    DiscoveryEnvelope,
    ResearchEnvelope,
    ResearchPacket,
    ReviewEnvelope,
    ReviewReport,
)
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

        claude_status = await get_claude_status_cached()
        if not claude_status.is_valid:
            return ResearchEnvelope(
                status="blocked",
                context_mode="single_candidate_research",
                blockers=["Claude runtime is not ready for research generation."],
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
        serialized_context = json.dumps(
            {
                "candidate": candidate.model_dump(mode="json"),
                "account_summary": snapshot.account_summary,
                "capability_summary": snapshot.capability_summary,
                "open_positions": snapshot.positions,
                "recent_trades": snapshot.recent_trades,
            },
            indent=2,
        )
        prompt = (
            "Create a compact research packet for a single swing-trading candidate.\n"
            "Use only the provided context. Do not invent catalysts, prices, or filings.\n"
            "Explain the thesis, supporting evidence, key risks, invalidation, and the next operator step.\n"
            f"Context:\n{serialized_context}"
        )

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
        )

        if not research.candidate_id:
            research.candidate_id = candidate.candidate_id
        if not research.account_id:
            research.account_id = account_id
        if not research.symbol:
            research.symbol = candidate.symbol
        if not research.next_step:
            research.next_step = "Use this packet as the basis for a decision packet."

        self._store_research(account_id, research)

        return ResearchEnvelope(
            status="ready",
            context_mode="single_candidate_research",
            blockers=[],
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

        claude_status = await get_claude_status_cached()
        if not claude_status.is_valid:
            return DecisionEnvelope(
                status="blocked",
                context_mode="delta_position_review",
                blockers=["Claude runtime is not ready for decision generation."],
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

        claude_status = await get_claude_status_cached()
        if not claude_status.is_valid:
            return ReviewEnvelope(
                status="blocked",
                context_mode="delta_daily_review",
                blockers=["Claude runtime is not ready for review generation."],
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
            "The output must highlight strengths, weaknesses, risk flags, and bounded strategy proposals.\n"
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

        envelope = ReviewEnvelope(
            status="ready",
            context_mode="delta_daily_review",
            blockers=[],
            artifact_count=1,
            review=review,
        )
        self._review_cache[account_id] = envelope
        return envelope

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
        )

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
            max_turns=2,
            model="haiku",
            output_format=schema,
            agents={
                role_name: AgentDefinition(
                    description=f"{role_name.title()} role for Robo Trader",
                    prompt=system_prompt,
                    tools=allowed_tools,
                    model="haiku",
                )
            },
            system_prompt=system_prompt,
        )
        # Structured artifact runs are short-lived and schema-specific. Reuse across
        # requests can poison later runs after an SDK session error, so recreate and
        # clean up the client on every run.
        client = await manager.get_client(client_type, options, force_recreate=True)
        try:
            response_text = await query_with_timeout(client, strict_prompt, timeout=45.0)
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
        stripped = response_text.strip()
        if stripped.startswith("```"):
            stripped = re.sub(r"^```(?:json)?\s*", "", stripped, count=1)
            stripped = re.sub(r"\s*```$", "", stripped, count=1)
            try:
                return json.loads(stripped)
            except json.JSONDecodeError:
                pass

        match = re.search(r"(\{[\s\S]*\})", response_text)
        if not match:
            return None

        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None


class DecisionEnvelopePayload(BaseModel):
    decisions: List[DecisionPacket]
