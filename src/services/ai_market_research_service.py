"""Codex-backed market research service for paper-trading discovery and research."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.auth.claude_auth import record_claude_runtime_limit
from src.services.codex_runtime_client import CodexRuntimeClient, CodexRuntimeError

logger = logging.getLogger(__name__)


class AIMarketResearchService:
    """Collect fresh external market evidence through the local Codex runtime."""

    MAX_MANUAL_RESEARCH_TIMEOUT_SECONDS = 35.0
    MAX_MANUAL_DISCOVERY_TIMEOUT_SECONDS = 45.0
    DISCOVERY_MODEL = "gpt-5-mini"
    DISCOVERY_REASONING = "low"
    TRIAGE_MODEL = "gpt-5-mini"
    TRIAGE_REASONING = "minimal"
    SYNTHESIS_MODEL = "gpt-5.4"
    SYNTHESIS_REASONING = "medium"

    def __init__(
        self,
        runtime_client: CodexRuntimeClient,
        *,
        default_model: str = "gpt-5.4",
        reasoning: str = "low",
        timeout_seconds: float = 12.0,
        discovery_timeout_seconds: Optional[float] = None,
        supports_compact_models: bool = True,
    ) -> None:
        self.runtime_client = runtime_client
        self.default_model = default_model or self.SYNTHESIS_MODEL
        self.reasoning = reasoning or self.SYNTHESIS_REASONING
        self.supports_compact_models = supports_compact_models
        requested_timeout_seconds = timeout_seconds
        self.timeout_seconds = min(timeout_seconds, self.MAX_MANUAL_RESEARCH_TIMEOUT_SECONDS)
        requested_discovery_timeout = (
            discovery_timeout_seconds
            if discovery_timeout_seconds is not None
            else max(requested_timeout_seconds, self.MAX_MANUAL_RESEARCH_TIMEOUT_SECONDS)
        )
        self.discovery_timeout_seconds = min(
            requested_discovery_timeout,
            self.MAX_MANUAL_DISCOVERY_TIMEOUT_SECONDS,
        )

    def _model_for(self, stage: str) -> str:
        if self.supports_compact_models:
            if stage == "discovery":
                return self.DISCOVERY_MODEL
            if stage == "triage":
                return self.TRIAGE_MODEL
        return self.default_model

    def _reasoning_for(self, stage: str) -> str:
        if stage == "discovery":
            return self.DISCOVERY_REASONING
        if stage == "triage":
            return self.TRIAGE_REASONING if self.supports_compact_models else "low"
        return self.reasoning

    async def collect_symbol_research(
        self,
        symbol: str,
        *,
        company_name: Optional[str] = None,
        research_brief: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = await self.collect_batch_symbol_research(
            [symbol],
            company_names={symbol: company_name} if company_name else None,
            research_brief=research_brief or self._default_symbol_research_brief(symbol, company_name),
            max_concurrent=1,
        )
        return result.get(symbol, self._empty_result(symbol, "Codex batch research returned no result for the symbol."))

    async def discover_market_opportunities(
        self,
        *,
        account_id: Optional[str] = None,
        criteria: Optional[Dict[str, Any]] = None,
        memory_context: Optional[Dict[str, Any]] = None,
        limit: int = 5,
    ) -> Dict[str, Any]:
        try:
            payload = await self.runtime_client.discover_market_opportunities(
                {
                    "account_id": account_id,
                    "criteria": criteria or {},
                    "memory_context": memory_context or {},
                    "limit": limit,
                    "model": self._model_for("discovery"),
                    "reasoning": self._reasoning_for("discovery"),
                    "prompt_cache_key": f"paper-trading:discovery:{account_id or 'global'}",
                    "timeout_seconds": self.discovery_timeout_seconds,
                }
            )
        except CodexRuntimeError as exc:
            if exc.usage_limited:
                record_claude_runtime_limit(str(exc))
            logger.warning("Codex discovery scout failed: %s", exc)
            return {
                "market_state_summary": "",
                "favored_sectors": [],
                "caution_sectors": [],
                "key_insights": [str(exc)],
                "candidates": [],
                "provider_metadata": {},
                "error": str(exc),
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected Codex discovery scout failure: %s", exc)
            return {
                "market_state_summary": "",
                "favored_sectors": [],
                "caution_sectors": [],
                "key_insights": [str(exc)],
                "candidates": [],
                "provider_metadata": {},
                "error": str(exc),
            }

        return {
            "market_state_summary": payload.get("market_state_summary", ""),
            "favored_sectors": list(payload.get("favored_sectors") or []),
            "caution_sectors": list(payload.get("caution_sectors") or []),
            "key_insights": list(payload.get("key_insights") or []),
            "candidates": list(payload.get("candidates") or []),
            "provider_metadata": payload.get("provider_metadata") or {},
            "error": "",
        }

    async def collect_batch_symbol_research(
        self,
        symbols: List[str],
        *,
        company_names: Optional[Dict[str, str]] = None,
        research_brief: Optional[str] = None,
        max_concurrent: int = 3,
    ) -> Dict[str, Dict[str, Any]]:
        del max_concurrent  # Sidecar controls concurrency internally via one thread per request.
        if not symbols:
            return {}

        try:
            payload = await self.runtime_client.collect_batch_research(
                {
                    "symbols": symbols,
                    "company_names": company_names or {},
                    "research_brief": research_brief,
                    "model": self._model_for("triage"),
                    "reasoning": self._reasoning_for("triage"),
                    "prompt_cache_key": f"paper-trading:batch-research:{'-'.join(sorted(symbols)[:3])}",
                    "timeout_seconds": self.timeout_seconds,
                }
            )
        except CodexRuntimeError as exc:
            if exc.usage_limited:
                record_claude_runtime_limit(str(exc))
            logger.warning("Codex batch research failed for %s symbols: %s", len(symbols), exc)
            return {symbol: self._empty_result(symbol, str(exc)) for symbol in symbols}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Unexpected Codex batch research failure: %s", exc)
            return {symbol: self._empty_result(symbol, str(exc)) for symbol in symbols}

        results = payload.get("results") or {}
        normalized: Dict[str, Dict[str, Any]] = {}
        for symbol in symbols:
            raw = results.get(symbol) or {}
            normalized[symbol] = self._normalize_result(symbol, raw, payload.get("provider_metadata") or {})
        return normalized

    @staticmethod
    def _normalize_result(symbol: str, raw: Dict[str, Any], provider_metadata: Dict[str, Any]) -> Dict[str, Any]:
        source_summary = AIMarketResearchService._normalize_source_summary(raw.get("source_summary") or [])
        evidence_citations = AIMarketResearchService._normalize_evidence_citations(raw.get("evidence_citations") or [])
        external_evidence_status = str(raw.get("external_evidence_status") or "").strip().lower()
        if external_evidence_status not in {"fresh", "partial", "missing"}:
            if source_summary or evidence_citations:
                external_evidence_status = "partial" if raw.get("errors") else "fresh"
            else:
                external_evidence_status = "missing"
        result = {
            "symbol": symbol,
            "research_timestamp": raw.get("research_timestamp") or datetime.now(timezone.utc).isoformat(),
            "summary": raw.get("summary", ""),
            "research_summary": raw.get("research_summary") or raw.get("summary", ""),
            "news": raw.get("news", ""),
            "financial_data": raw.get("financial_data", ""),
            "filings": raw.get("filings", ""),
            "market_context": raw.get("market_context", ""),
            "sources": list(raw.get("sources") or []),
            "source_summary": source_summary,
            "evidence_citations": evidence_citations,
            "evidence": list(raw.get("evidence") or []),
            "risks": list(raw.get("risks") or []),
            "errors": list(raw.get("errors") or []),
            "external_evidence_status": external_evidence_status,
            "provider_metadata": provider_metadata,
        }
        return result

    @staticmethod
    def _default_symbol_research_brief(symbol: str, company_name: Optional[str]) -> str:
        company_label = company_name or symbol
        return (
            f"For {company_label} ({symbol}), gather only the freshest swing-trading evidence. "
            "Prioritize at most one fresh company-specific catalyst or material news item, "
            "one fresh filing or management disclosure, one concrete fundamentals datapoint if recent, "
            "and one concrete risk. Skip generic company background, sector primers, and long narratives. "
            "If no fresh evidence exists, return explicit unavailability instead of filler."
        )

    @staticmethod
    def _empty_result(symbol: str, error: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "research_timestamp": datetime.now(timezone.utc).isoformat(),
            "summary": "",
            "research_summary": "",
            "news": "",
            "financial_data": "",
            "filings": "",
            "market_context": "",
            "sources": [],
            "source_summary": [],
            "evidence_citations": [],
            "evidence": [],
            "risks": [],
            "errors": [error],
            "external_evidence_status": "missing",
            "provider_metadata": {},
        }

    @staticmethod
    def _normalize_source_summary(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in items:
            source_type = str(item.get("source_type") or "")
            normalized.append(
                {
                    **item,
                    "tier": item.get("tier") or AIMarketResearchService._tier_for_source_type(source_type),
                }
            )
        return normalized

    @staticmethod
    def _normalize_evidence_citations(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in items:
            source_type = str(item.get("source_type") or "")
            normalized.append(
                {
                    **item,
                    "tier": item.get("tier") or AIMarketResearchService._tier_for_source_type(source_type),
                }
            )
        return normalized

    @staticmethod
    def _tier_for_source_type(source_type: str) -> str:
        normalized = source_type.strip().lower()
        if normalized in {"exchange_disclosure", "company_filing", "company_ir"}:
            return "primary"
        if normalized in {"reputable_financial_news", "claude_web_news", "codex_web_research"}:
            return "secondary"
        return "derived"
