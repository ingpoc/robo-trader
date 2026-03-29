"""
Paper-trading stock discovery service.

This service keeps discovery stateful and outcome-driven:
- start from a deterministic market universe
- use prior research and trade outcomes to avoid redundant AI work
- shortlist a small number of dark-horse candidates before spending tokens
- batch external research for the shortlist only
- score extracted features deterministically
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from ...auth.ai_runtime_auth import get_ai_runtime_status
from ...core.errors import ErrorCategory, ErrorSeverity, TradingError
from ...core.event_bus import Event, EventHandler


class StockDiscoveryService(EventHandler):
    """Stateful discovery funnel for paper-trading candidates."""

    def __init__(
        self,
        state_manager,
        market_research_service,
        event_bus,
        config: Dict[str, Any],
        feature_extractor,
        deterministic_scorer,
        *,
        learning_service=None,
        account_manager=None,
    ):
        self.state_manager = state_manager
        self.market_research_service = market_research_service
        self.event_bus = event_bus
        self.config = config
        self.feature_extractor = feature_extractor
        self.deterministic_scorer = deterministic_scorer
        self.learning_service = learning_service
        self.account_manager = account_manager

        self.default_criteria = {
            "min_market_cap": "small",
            "max_market_cap": "mega",
            "exclude_penny_stocks": True,
            "min_price": 50.0,
            "max_price": 5000.0,
            "sectors": [],
            "liquidity_min": "medium",
        }

        self.max_deep_research_candidates = 5
        self.shortlist_multiplier = 3
        self.research_cooldown = timedelta(days=3)
        self.watchlist_cooldown = timedelta(days=2)
        self.discovery_memory_limit = 24
        self._running = False

    async def initialize(self) -> None:
        logger.info("Initializing Stock Discovery Service")
        self._running = True
        logger.info("Stock Discovery Service initialized")

    async def cleanup(self) -> None:
        self._running = False
        logger.info("Stock Discovery Service cleaned up")

    async def run_discovery_session(
        self,
        session_type: str = "daily_screen",
        custom_criteria: Optional[Dict[str, Any]] = None,
        *,
        account_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run a stateful discovery session and refresh the watchlist."""
        session_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            logger.info("Starting stock discovery session %s for account=%s", session_id, account_id or "global")
            await self._create_discovery_session(session_id, session_type, custom_criteria)

            criteria = {**self.default_criteria, **(custom_criteria or {})}
            market_stocks = await self._load_market_universe(criteria)
            memory_context = await self._build_discovery_memory(account_id, market_stocks)
            runtime_blocker = await self._runtime_blocker_for_discovery()
            if runtime_blocker:
                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                blocked_insights = [runtime_blocker]
                await self._complete_discovery_session(
                    session_id,
                    duration_ms,
                    total_scanned=0,
                    analyzed=0,
                    high_potential=0,
                    key_insights=blocked_insights,
                    market_conditions={},
                )
                return {
                    "session_id": session_id,
                    "session_type": session_type,
                    "account_id": account_id,
                    "total_scanned": 0,
                    "shortlisted": 0,
                    "analyzed": 0,
                    "high_potential": 0,
                    "watchlist_updates": {"added": 0, "updated": 0, "removed": 0},
                    "top_candidates": [],
                    "market_conditions": {},
                    "key_insights": blocked_insights,
                    "duration_ms": duration_ms,
                    "status": "blocked",
                    "blockers": [runtime_blocker],
                }

            discovery_candidates, market_conditions, key_insights, scout_blocker = await self._discover_candidates_from_market(
                criteria=criteria,
                memory_context=memory_context,
                account_id=account_id,
            )
            if scout_blocker:
                fallback_candidates, fallback_market_conditions, fallback_insights = await self._screen_market(
                    criteria,
                    market_stocks,
                    memory_context,
                )
                fallback_candidates = fallback_candidates[: self.max_deep_research_candidates]
                if not fallback_candidates:
                    duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                    blocked_insights = [*key_insights, *fallback_insights, scout_blocker]
                    await self._complete_discovery_session(
                        session_id,
                        duration_ms,
                        total_scanned=len(market_stocks),
                        analyzed=0,
                        high_potential=0,
                        key_insights=list(dict.fromkeys(blocked_insights)),
                        market_conditions=market_conditions,
                    )
                    return {
                        "session_id": session_id,
                        "session_type": session_type,
                        "account_id": account_id,
                        "total_scanned": len(market_stocks),
                        "shortlisted": 0,
                        "analyzed": 0,
                        "high_potential": 0,
                        "watchlist_updates": {"added": 0, "updated": 0, "removed": 0},
                        "top_candidates": [],
                        "market_conditions": market_conditions,
                        "key_insights": list(dict.fromkeys(blocked_insights)),
                        "duration_ms": duration_ms,
                        "status": "blocked",
                        "blockers": [scout_blocker],
                    }

                fallback_market_conditions = {
                    **fallback_market_conditions,
                    "discovery_style": "deterministic_fallback",
                    "runtime_blocker": scout_blocker,
                }
                for candidate in fallback_candidates:
                    candidate.setdefault("recommendation", "WATCH")
                    candidate.setdefault("score", candidate.get("opportunity_score", 0.0))
                    candidate["discovery_reason"] = (
                        f"{candidate.get('discovery_reason', '').strip()} "
                        f"Live web scout degraded, so this candidate is coming from the deterministic paper-trading screen."
                    ).strip()

                watchlist_updates = await self._update_watchlist(fallback_candidates[: max(len(fallback_candidates), 10)])
                duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
                high_potential = len(
                    [stock for stock in fallback_candidates if float(stock.get("opportunity_score", 0.0)) > 70.0]
                )
                combined_insights = list(dict.fromkeys([*key_insights, *fallback_insights, scout_blocker]))
                await self._complete_discovery_session(
                    session_id,
                    duration_ms,
                    total_scanned=len(market_stocks),
                    analyzed=len(fallback_candidates),
                    high_potential=high_potential,
                    key_insights=combined_insights,
                    market_conditions=fallback_market_conditions,
                )
                return {
                    "session_id": session_id,
                    "session_type": session_type,
                    "account_id": account_id,
                    "total_scanned": len(market_stocks),
                    "shortlisted": len(fallback_candidates),
                    "analyzed": len(fallback_candidates),
                    "high_potential": high_potential,
                    "watchlist_updates": watchlist_updates,
                    "top_candidates": fallback_candidates[:10],
                    "market_conditions": fallback_market_conditions,
                    "key_insights": combined_insights,
                    "duration_ms": duration_ms,
                    "status": "completed",
                    "blockers": [scout_blocker],
                }
            research_limit = min(len(discovery_candidates), self.max_deep_research_candidates)
            analyzed_stocks = await self._analyze_candidates(
                discovery_candidates[:research_limit],
                criteria,
                memory_context=memory_context,
                market_conditions=market_conditions,
            )
            scored_stocks = await self._score_stocks(analyzed_stocks)
            watchlist_updates = await self._update_watchlist(scored_stocks[: max(research_limit, 10)])

            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            high_potential = len([stock for stock in scored_stocks if stock.get("score", 0) > 70])

            await self._complete_discovery_session(
                session_id,
                duration_ms,
                total_scanned=len(discovery_candidates),
                analyzed=len(analyzed_stocks),
                high_potential=high_potential,
                key_insights=key_insights,
                market_conditions=market_conditions,
            )

            return {
                "session_id": session_id,
                "session_type": session_type,
                "account_id": account_id,
                "total_scanned": len(discovery_candidates),
                "shortlisted": len(discovery_candidates),
                "analyzed": len(analyzed_stocks),
                "high_potential": high_potential,
                "watchlist_updates": watchlist_updates,
                "top_candidates": scored_stocks[:10],
                "market_conditions": market_conditions,
                "key_insights": key_insights,
                "duration_ms": duration_ms,
                "status": "completed",
            }
        except Exception as exc:
            logger.error("Stock discovery session %s failed: %s", session_id, exc)
            await self._fail_discovery_session(session_id, str(exc))
            raise TradingError(
                f"Stock discovery session failed: {exc}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
            ) from exc

    async def _load_market_universe(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Load the deterministic universe and apply coarse filters without AI."""
        try:
            universe_path = Path(__file__).parents[3] / "data" / "nse_universe.json"
            payload = json.loads(universe_path.read_text())
            market_stocks = payload.get("universe", [])
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to load NSE universe: %s", exc)
            market_stocks = []

        allowed_sectors = set(criteria.get("sectors", []))
        allowed_caps = set(criteria.get("market_cap_tiers", []))

        filtered: List[Dict[str, Any]] = []
        for stock in market_stocks:
            if allowed_sectors and stock.get("sector") not in allowed_sectors:
                continue
            if allowed_caps and stock.get("cap") not in allowed_caps:
                continue

            filtered.append(
                {
                    "symbol": stock["symbol"],
                    "name": stock.get("name", stock["symbol"]),
                    "sector": stock.get("sector", "Unknown"),
                    "cap": stock.get("cap", "unknown"),
                    "discovery_source": "stateful_opportunity_funnel",
                    "screening_criteria": criteria,
                }
            )

        return filtered

    async def _build_discovery_memory(
        self,
        account_id: Optional[str],
        market_stocks: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Assemble cheap local memory so discovery does not behave like a blank slate."""
        symbol_to_sector = {stock["symbol"]: stock.get("sector", "Unknown") for stock in market_stocks}
        memory_context: Dict[str, Any] = {
            "account_id": account_id,
            "recent_symbols": set(),
            "recently_blocked_symbols": set(),
            "held_symbols": set(),
            "watchlist_symbols": set(),
            "stale_watchlist_symbols": set(),
            "recent_research_by_symbol": {},
            "sector_scores": {},
            "sector_recent_counts": {},
            "friction_notes": [],
            "recent_lessons": [],
        }

        watchlist = await self.state_manager.paper_trading.get_discovery_watchlist(limit=100, status="ACTIVE")
        now = datetime.now(timezone.utc)
        for item in watchlist:
            symbol = item.get("symbol")
            if not symbol:
                continue
            memory_context["watchlist_symbols"].add(symbol)
            last_seen = item.get("last_analyzed") or item.get("created_at")
            if self._is_recent(last_seen, now=now, window=self.watchlist_cooldown):
                memory_context["stale_watchlist_symbols"].add(symbol)

        if not account_id or self.learning_service is None:
            return memory_context

        if self.account_manager is not None:
            try:
                positions = await self.account_manager.get_open_positions(account_id)
                memory_context["held_symbols"] = {position.symbol for position in positions if getattr(position, "symbol", None)}
            except Exception as exc:  # noqa: BLE001
                logger.warning("Failed to load open positions for discovery memory: %s", exc)

        try:
            learning_summary = await self.learning_service.get_learning_summary(account_id, refresh=True)
            memory_context["recent_lessons"] = list(learning_summary.top_lessons or [])[:3]

            discovery_memory = await self.learning_service.get_discovery_memory(
                account_id,
                limit=self.discovery_memory_limit,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to build discovery memory for %s: %s", account_id, exc)
            return memory_context

        for entry in discovery_memory.get("recent_research", []):
            symbol = entry.get("symbol")
            if not symbol:
                continue
            memory_context["recent_research_by_symbol"][symbol] = entry
            sector = entry.get("sector") or symbol_to_sector.get(symbol, "Unknown")
            if sector:
                memory_context["sector_recent_counts"][sector] = memory_context["sector_recent_counts"].get(sector, 0) + 1
            if self._is_recent(entry.get("generated_at"), now=now, window=self.research_cooldown):
                memory_context["recent_symbols"].add(symbol)
            if entry.get("actionability") == "blocked" or entry.get("analysis_mode") != "fresh_evidence":
                memory_context["recently_blocked_symbols"].add(symbol)
                if sector:
                    memory_context["sector_scores"][sector] = memory_context["sector_scores"].get(sector, 0.0) - 0.35
            elif entry.get("actionability") == "actionable":
                if sector:
                    memory_context["sector_scores"][sector] = memory_context["sector_scores"].get(sector, 0.0) + 0.25

            risk_fragments = [str(risk) for risk in (entry.get("risks") or []) if isinstance(risk, str)]
            if risk_fragments:
                memory_context["friction_notes"].extend(risk_fragments[:2])

        for evaluation in discovery_memory.get("recent_evaluations", []):
            symbol = evaluation.get("symbol")
            if not symbol:
                continue
            sector = symbol_to_sector.get(symbol) or memory_context["recent_research_by_symbol"].get(symbol, {}).get("sector")
            if not sector:
                continue
            outcome = evaluation.get("outcome")
            if outcome == "win":
                memory_context["sector_scores"][sector] = memory_context["sector_scores"].get(sector, 0.0) + 1.0
            elif outcome == "loss":
                memory_context["sector_scores"][sector] = memory_context["sector_scores"].get(sector, 0.0) - 1.0
            else:
                memory_context["sector_scores"][sector] = memory_context["sector_scores"].get(sector, 0.0) - 0.15

        memory_context["friction_notes"] = list(dict.fromkeys(memory_context["friction_notes"]))[:5]
        return memory_context

    async def _screen_market(
        self,
        criteria: Dict[str, Any],
        market_stocks: List[Dict[str, Any]],
        memory_context: Dict[str, Any],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str]]:
        """Turn the universe into a small stateful shortlist before any AI research."""
        shortlisted: List[Dict[str, Any]] = []
        sector_scores = memory_context.get("sector_scores", {})
        sector_recent_counts = memory_context.get("sector_recent_counts", {})
        recent_symbols = memory_context.get("recent_symbols", set())
        blocked_symbols = memory_context.get("recently_blocked_symbols", set())
        held_symbols = memory_context.get("held_symbols", set())
        recently_seen_watchlist = memory_context.get("stale_watchlist_symbols", set())

        for stock in market_stocks:
            symbol = stock["symbol"]
            if symbol in held_symbols:
                continue
            if symbol in recent_symbols:
                continue
            if symbol in recently_seen_watchlist:
                continue

            sector = stock.get("sector", "Unknown")
            cap = str(stock.get("cap", "unknown")).lower()
            sector_score = float(sector_scores.get(sector, 0.0))
            recent_sector_coverage = int(sector_recent_counts.get(sector, 0))

            opportunity_score = 50.0
            opportunity_score += sector_score * 12.0
            opportunity_score += self._cap_bonus(cap)
            opportunity_score += 10.0 if recent_sector_coverage == 0 else max(0.0, 6.0 - recent_sector_coverage * 1.5)
            if symbol not in memory_context.get("watchlist_symbols", set()):
                opportunity_score += 6.0
            if symbol in blocked_symbols:
                opportunity_score -= 18.0

            rationale_parts = []
            if sector_score > 0.5:
                rationale_parts.append(f"{sector} has been one of the stronger sectors in recent paper-trading outcomes.")
            elif sector_score < -0.5:
                rationale_parts.append(f"{sector} has been weak recently, so this name only survives if it looks like a genuine dark horse.")
            else:
                rationale_parts.append(f"{sector} is underfollowed in the recent research log, which makes this a discovery candidate instead of a repeat.")

            if cap in {"small", "mid"}:
                rationale_parts.append("The company sits in a smaller-cap bucket, which makes it more likely to be a dark-horse setup than a crowded large-cap leader.")
            elif cap == "large":
                rationale_parts.append("Large-cap quality keeps this name on the list, but it is not being prioritized as a dark horse.")

            latest_research = memory_context.get("recent_research_by_symbol", {}).get(symbol)
            if latest_research:
                actionability = latest_research.get("actionability", "watch_only")
                rationale_parts.append(f"Prior research ended as {actionability}; discovery is not repeating it immediately.")
            else:
                rationale_parts.append("The symbol has not been researched recently, so it qualifies as fresh discovery inventory.")

            shortlisted.append(
                {
                    **stock,
                    "discovery_source": "stateful_opportunity_funnel",
                    "discovery_reason": " ".join(rationale_parts[:3]),
                    "opportunity_score": round(opportunity_score, 2),
                }
            )

        shortlisted.sort(key=lambda item: item.get("opportunity_score", 0.0), reverse=True)
        shortlist_cap = self.max_deep_research_candidates * self.shortlist_multiplier
        shortlist = shortlisted[:shortlist_cap]

        favored_sectors = [
            sector
            for sector, _ in sorted(sector_scores.items(), key=lambda item: item[1], reverse=True)
            if sector and sector_scores.get(sector, 0.0) > 0
        ][:3]
        unfavored_sectors = [
            sector
            for sector, _ in sorted(sector_scores.items(), key=lambda item: item[1])
            if sector and sector_scores.get(sector, 0.0) < 0
        ][:3]
        market_conditions = {
            "discovery_style": "stateful_opportunity_funnel",
            "favored_sectors": favored_sectors,
            "unfavored_sectors": unfavored_sectors,
            "recent_research_count": len(memory_context.get("recent_research_by_symbol", {})),
            "held_symbols": sorted(memory_context.get("held_symbols", set())),
            "friction_notes": memory_context.get("friction_notes", []),
        }

        key_insights: List[str] = []
        if favored_sectors:
            key_insights.append(f"Discovery is leaning into under-researched strength in {', '.join(favored_sectors)}.")
        if unfavored_sectors:
            key_insights.append(f"Discovery is de-emphasizing sectors that recently failed paper trades: {', '.join(unfavored_sectors)}.")
        if memory_context.get("recent_symbols"):
            key_insights.append(
                f"Skipped {len(memory_context['recent_symbols'])} recently researched symbols to avoid redundant AI spend."
            )
        if memory_context.get("friction_notes"):
            key_insights.append(
                f"Prior frictions are being carried forward: {', '.join(memory_context['friction_notes'][:2])}."
            )

        logger.info(
            "Screened %s stocks into %s stateful candidates (favored sectors=%s)",
            len(market_stocks),
            len(shortlist),
            favored_sectors,
        )
        return shortlist, market_conditions, key_insights

    @staticmethod
    def _cap_bonus(cap: str) -> float:
        if cap == "small":
            return 12.0
        if cap == "mid":
            return 8.0
        if cap == "large":
            return 2.0
        return -2.0

    async def _analyze_candidates(
        self,
        stocks: List[Dict[str, Any]],
        criteria: Dict[str, Any],
        *,
        memory_context: Optional[Dict[str, Any]] = None,
        market_conditions: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Deep-research a small shortlist only, using one batched research request."""
        if not stocks:
            return []

        logger.info("Analyzing %s candidate stocks via batched research", len(stocks))
        symbols_to_fetch = [stock["symbol"] for stock in stocks if not stock.get("seed_research")]
        company_names = {stock["symbol"]: stock.get("name", stock["symbol"]) for stock in stocks if not stock.get("seed_research")}
        batch_research: Dict[str, Dict[str, Any]] = {}
        if symbols_to_fetch:
            batch_research = await self.market_research_service.collect_batch_symbol_research(
                symbols_to_fetch,
                company_names=company_names,
                research_brief=self._build_research_brief(stocks, criteria, memory_context or {}, market_conditions or {}),
                max_concurrent=len(symbols_to_fetch),
            )

        analyzed_stocks: List[Dict[str, Any]] = []
        for stock in stocks:
            try:
                external_research = dict(stock.get("seed_research") or batch_research.get(stock["symbol"], {}))
                if self._research_result_usage_limited(external_research):
                    analyzed_stocks.append(
                        {
                            **stock,
                            "external_research": external_research,
                            "analysis_error": self._extract_research_error(external_research),
                            "claude_analysis": {
                                "symbol": stock["symbol"],
                                "analysis_type": "blocked",
                                "recommendation": "HOLD",
                                "confidence": 0.0,
                                "score": 0.0,
                                "features": {},
                                "key_factors": [],
                                "risks": [self._extract_research_error(external_research)],
                                "opportunities": [],
                            },
                            "research_timestamp": external_research.get("research_timestamp")
                            or datetime.now(timezone.utc).isoformat(),
                        }
                    )
                    continue

                structured_analysis = await self._analyze_stock_features(stock, external_research)
                analyzed_stocks.append(
                    {
                        **stock,
                        "external_research": external_research,
                        "claude_analysis": structured_analysis,
                        "research_timestamp": external_research.get("research_timestamp")
                        or datetime.now(timezone.utc).isoformat(),
                    }
                )
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to analyze stock %s: %s", stock.get("symbol"), exc)
                analyzed_stocks.append(
                    {
                        **stock,
                        "analysis_error": str(exc),
                        "research_timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )

        return analyzed_stocks

    async def _discover_candidates_from_market(
        self,
        *,
        criteria: Dict[str, Any],
        memory_context: Dict[str, Any],
        account_id: Optional[str],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any], List[str], Optional[str]]:
        """Ask the runtime to scout current market/sector conditions for dark-horse ideas."""
        scout_result = await self.market_research_service.discover_market_opportunities(
            account_id=account_id,
            criteria=criteria,
            memory_context={
                "recent_symbols": sorted(memory_context.get("recent_symbols", set())),
                "recently_blocked_symbols": sorted(memory_context.get("recently_blocked_symbols", set())),
                "held_symbols": sorted(memory_context.get("held_symbols", set())),
                "watchlist_symbols": sorted(memory_context.get("watchlist_symbols", set())),
                "sector_scores": memory_context.get("sector_scores", {}),
                "sector_recent_counts": memory_context.get("sector_recent_counts", {}),
                "friction_notes": memory_context.get("friction_notes", []),
                "recent_lessons": memory_context.get("recent_lessons", []),
            },
            limit=self.max_deep_research_candidates,
        )

        favored_sectors = list(scout_result.get("favored_sectors") or [])
        caution_sectors = list(scout_result.get("caution_sectors") or [])
        key_insights = list(scout_result.get("key_insights") or [])
        scout_error = str(scout_result.get("error") or "").strip()
        market_conditions = {
            "discovery_style": "web_market_scout",
            "market_state_summary": scout_result.get("market_state_summary", ""),
            "favored_sectors": favored_sectors,
            "unfavored_sectors": caution_sectors,
            "friction_notes": memory_context.get("friction_notes", []),
            "recent_research_count": len(memory_context.get("recent_research_by_symbol", {})),
            "held_symbols": sorted(memory_context.get("held_symbols", set())),
        }

        candidates: List[Dict[str, Any]] = []
        seen_symbols = set()
        recent_symbols = memory_context.get("recent_symbols", set())
        blocked_symbols = memory_context.get("recently_blocked_symbols", set())
        held_symbols = memory_context.get("held_symbols", set())

        for raw in scout_result.get("candidates") or []:
            symbol = str(raw.get("symbol") or "").strip().upper()
            if not symbol or symbol in seen_symbols or symbol in held_symbols or symbol in recent_symbols:
                continue
            seen_symbols.add(symbol)
            if symbol in blocked_symbols and not raw.get("evidence"):
                continue
            candidates.append(
                {
                    "symbol": symbol,
                    "name": raw.get("company_name") or symbol,
                    "sector": raw.get("sector") or "Unknown",
                    "cap": raw.get("cap", "unknown"),
                    "discovery_source": "web_market_scout",
                    "discovery_reason": raw.get("discovery_reason") or raw.get("summary") or "Web discovery scout surfaced a timely setup.",
                    "opportunity_score": float(raw.get("opportunity_score") or 0.0),
                    "seed_research": {
                        "symbol": symbol,
                        "research_timestamp": raw.get("research_timestamp") or datetime.now(timezone.utc).isoformat(),
                        "summary": raw.get("summary", ""),
                        "research_summary": raw.get("research_summary") or raw.get("summary", ""),
                        "news": raw.get("news", ""),
                        "financial_data": raw.get("financial_data", ""),
                        "filings": raw.get("filings", ""),
                        "market_context": raw.get("market_context", ""),
                        "source_summary": list(raw.get("source_summary") or []),
                        "evidence_citations": list(raw.get("evidence_citations") or []),
                        "evidence": list(raw.get("evidence") or []),
                        "risks": list(raw.get("risks") or []),
                        "errors": list(raw.get("errors") or []),
                    },
                }
            )

        candidates.sort(key=lambda item: item.get("opportunity_score", 0.0), reverse=True)
        if not candidates and not key_insights:
            key_insights = ["Discovery scout did not find a current dark-horse candidate with adequate evidence."]
        blocker = f"AI runtime discovery scout failed. {scout_error}" if scout_error else None
        return candidates[: self.max_deep_research_candidates], market_conditions, key_insights, blocker

    async def _runtime_blocker_for_discovery(self) -> Optional[str]:
        """Return a user-facing blocker when the AI runtime is unavailable for discovery."""
        try:
            runtime_status = await get_ai_runtime_status()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to validate AI runtime before discovery: %s", exc)
            return None

        rate_limit_info = getattr(runtime_status, "rate_limit_info", {}) or {}
        if rate_limit_info.get("status") == "exhausted":
            message = rate_limit_info.get("message") or "AI runtime usage is temporarily exhausted."
            return f"AI runtime is usage-limited for discovery generation. {message}"
        validation_pending = "no explicit ai request has validated auth/quota" in str(runtime_status.error or "").lower()
        if validation_pending:
            return None
        if not runtime_status.is_valid:
            return f"AI runtime is not ready for discovery generation. {runtime_status.error or ''}".strip()
        return None

    @staticmethod
    def _extract_research_error(external_research: Dict[str, Any]) -> str:
        errors = external_research.get("errors") or []
        if errors:
            return str(errors[0])
        return "External research is unavailable."

    @classmethod
    def _research_result_usage_limited(cls, external_research: Dict[str, Any]) -> bool:
        error_text = cls._extract_research_error(external_research).lower()
        return (
            "usage limit" in error_text
            or "usage-limited" in error_text
            or "try again at" in error_text
            or "upgrade to plus" in error_text
        )

    def _build_research_brief(
        self,
        stocks: List[Dict[str, Any]],
        criteria: Dict[str, Any],
        memory_context: Dict[str, Any],
        market_conditions: Dict[str, Any],
    ) -> str:
        symbols = ", ".join(stock["symbol"] for stock in stocks)
        favored_sectors = ", ".join(market_conditions.get("favored_sectors", [])[:3]) or "none"
        recent_symbols = ", ".join(sorted(memory_context.get("recent_symbols", set()))[:5]) or "none"
        friction_notes = "; ".join(memory_context.get("friction_notes", [])[:3]) or "none"
        lessons = "; ".join(memory_context.get("recent_lessons", [])[:2]) or "none"
        sector_filter = ", ".join(criteria.get("sectors", [])) or "all sectors"

        return (
            "This is a dark-horse stock discovery pass. "
            "Do not rehash large-cap leaders unless the evidence is exceptional. "
            f"Symbols under review: {symbols}. "
            f"Preferred sectors from recent conditions: {favored_sectors}. "
            f"Allowed sector filter: {sector_filter}. "
            f"Recently researched symbols to avoid repeating: {recent_symbols}. "
            f"Prior frictions to avoid: {friction_notes}. "
            f"Recent paper-trading lessons: {lessons}. "
            "Focus on improving fundamentals, credible catalysts, and why the setup matters now."
        )

    async def _analyze_stock_features(
        self,
        stock: Dict[str, Any],
        external_research: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Extract factual features and score them deterministically.

        The model is only allowed to summarize evidence into features. The trade
        recommendation remains deterministic.
        """
        try:
            research_data = {
                "news": external_research.get("research_summary", "") or external_research.get("news", ""),
                "financials": external_research.get("financial_data", ""),
                "filings": external_research.get("filings", ""),
                "market_data": external_research.get("market_context", ""),
            }

            entry = await self.feature_extractor.extract_features(stock["symbol"], research_data)
            entry = self.deterministic_scorer.score(entry)

            return {
                "symbol": stock["symbol"],
                "analysis_type": "feature_extraction",
                "recommendation": entry.action or "HOLD",
                "confidence": entry.feature_confidence or 0.0,
                "score": entry.score or 0.0,
                "features": entry.to_flat_features(),
                "research_ledger_id": entry.id,
                "key_factors": [key for key, value in entry.to_flat_features().items() if value is not None],
                "risks": [],
                "opportunities": [],
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Feature extraction failed for %s: %s", stock["symbol"], exc)
            return {
                "symbol": stock["symbol"],
                "analysis_type": "fallback",
                "recommendation": "HOLD",
                "confidence": 0.0,
                "score": 0.0,
                "features": {},
                "key_factors": [],
                "risks": [f"Feature extraction failed: {exc}"],
                "opportunities": [],
            }

    async def _score_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        scored_stocks = []
        for stock in stocks:
            score = 0.0
            recommendation = "HOLD"

            if "claude_analysis" in stock:
                analysis = stock["claude_analysis"]
                score = analysis.get("score", 0.0)
                recommendation = analysis.get("recommendation", "HOLD")

            scored_stocks.append(
                {
                    **stock,
                    "score": score,
                    "recommendation": recommendation,
                    "scoring_timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        scored_stocks.sort(key=lambda item: item.get("score", 0.0), reverse=True)
        return scored_stocks

    async def get_watchlist(
        self,
        status: str = "ACTIVE",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        try:
            watchlist = await self.state_manager.paper_trading.get_discovery_watchlist(
                status=status,
                limit=limit,
            )
            logger.info("Retrieved %s stocks from discovery watchlist", len(watchlist))
            return watchlist
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to get discovery watchlist: %s", exc)
            return []

    async def _update_watchlist(self, stocks: List[Dict[str, Any]]) -> Dict[str, Any]:
        updates = {"added": 0, "updated": 0, "removed": 0, "skipped": 0}
        active_watchlist = await self.state_manager.paper_trading.get_discovery_watchlist(limit=200, status="ACTIVE")
        active_by_symbol = {item.get("symbol"): item for item in active_watchlist if item.get("symbol")}
        active_symbols = set(active_by_symbol)
        next_symbols = {stock["symbol"] for stock in stocks if stock.get("symbol")}
        now = datetime.now(timezone.utc).isoformat()

        for symbol in active_symbols - next_symbols:
            stale_item = active_by_symbol[symbol]
            try:
                await self.state_manager.paper_trading.delete_discovery_watchlist_entry(stale_item["id"])
                updates["removed"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to delete stale discovery watchlist entry for %s: %s", symbol, exc)
                updates["skipped"] += 1

        for stock in stocks:
            try:
                existing = await self.state_manager.paper_trading.get_discovery_watchlist_by_symbol(stock["symbol"])
                payload = {
                    "symbol": stock["symbol"],
                    "company_name": stock.get("name"),
                    "sector": stock.get("sector"),
                    "discovery_date": datetime.now(timezone.utc).date().isoformat(),
                    "discovery_source": stock.get("discovery_source", "stateful_opportunity_funnel"),
                    "discovery_reason": stock.get("discovery_reason", "Stateful discovery analysis"),
                    "current_price": stock.get("current_price"),
                    "recommendation": stock.get("recommendation", "WATCH"),
                    "confidence_score": stock.get("score", 0) / 100,
                    "research_summary": {
                        "external_research": stock.get("external_research"),
                        "structured_analysis": stock.get("claude_analysis"),
                        "discovery_reason": stock.get("discovery_reason", ""),
                        "opportunity_score": stock.get("opportunity_score"),
                    },
                    "technical_indicators": stock.get("claude_analysis", {}).get("features", {}),
                    "fundamental_metrics": stock.get("claude_analysis", {}).get("features", {}),
                    "last_analyzed": now,
                    "updated_at": now,
                    "status": "ACTIVE",
                }

                if existing:
                    await self.state_manager.paper_trading.update_discovery_watchlist(existing["id"], payload)
                    updates["updated"] += 1
                else:
                    payload["created_at"] = now
                    await self.state_manager.paper_trading.add_to_discovery_watchlist(payload)
                    updates["added"] += 1
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to update watchlist for %s: %s", stock.get("symbol"), exc)
                updates["skipped"] += 1

        return updates

    async def _create_discovery_session(
        self,
        session_id: str,
        session_type: str,
        custom_criteria: Optional[Dict[str, Any]],
    ) -> None:
        await self.state_manager.paper_trading.create_discovery_session(
            {
                "id": session_id,
                "session_date": datetime.now(timezone.utc).date().isoformat(),
                "session_type": session_type,
                "screening_criteria": custom_criteria or self.default_criteria,
                "total_stocks_scanned": 0,
                "stocks_discovered": 0,
                "high_potential_stocks": 0,
                "session_status": "RUNNING",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def _complete_discovery_session(
        self,
        session_id: str,
        duration_ms: int,
        total_scanned: int,
        analyzed: int,
        high_potential: int,
        *,
        key_insights: Optional[List[str]] = None,
        market_conditions: Optional[Dict[str, Any]] = None,
    ) -> None:
        await self.state_manager.paper_trading.update_discovery_session(
            session_id,
            {
                "total_stocks_scanned": total_scanned,
                "stocks_discovered": analyzed,
                "high_potential_stocks": high_potential,
                "session_duration_ms": duration_ms,
                "key_insights": key_insights or [],
                "market_conditions": market_conditions or {},
                "session_status": "COMPLETED",
            },
        )

    async def _fail_discovery_session(self, session_id: str, error_message: str) -> None:
        await self.state_manager.paper_trading.update_discovery_session(
            session_id,
            {
                "session_status": "FAILED",
                "error_message": error_message,
            },
        )

    async def handle_event(self, event: Event) -> None:
        if not self._running:
            return

        # Event-driven discovery remains intentionally disabled until the repo
        # has a stronger, deterministic reason to spend tokens automatically.
        _ = event

    async def _handle_market_news_event(self, event: Event) -> None:
        _ = event

    async def _handle_earnings_event(self, event: Event) -> None:
        _ = event

    async def _handle_sector_event(self, event: Event) -> None:
        _ = event

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            normalized = value.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        except ValueError:
            return None

    def _is_recent(
        self,
        value: Optional[str],
        *,
        now: datetime,
        window: timedelta,
    ) -> bool:
        parsed = self._parse_timestamp(value)
        if parsed is None:
            return False
        return now - parsed <= window
