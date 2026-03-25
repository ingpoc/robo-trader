"""Claude Agent SDK web research service for paper-trading discovery and research."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from claude_agent_sdk import ClaudeAgentOptions
from claude_agent_sdk.types import AgentDefinition

from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout

logger = logging.getLogger(__name__)


class ClaudeMarketResearchService:
    """Collect fresh external market evidence using Claude's built-in web tools."""

    _URL_RE = re.compile(r"https?://\S+")
    _SPECIALIST_AGENTS = {
        "news-researcher": AgentDefinition(
            description="Use for fresh company, sector, and market-moving news research.",
            prompt=(
                "You are the news researcher for Robo Trader. Gather only fresh, factual news that matters "
                "for the symbol. Prefer official announcements, exchange disclosures, and reputable financial press."
            ),
            tools=["WebSearch", "WebFetch"],
            model="haiku",
        ),
        "fundamentals-researcher": AgentDefinition(
            description="Use for recent earnings, valuation, balance-sheet, and business-quality facts.",
            prompt=(
                "You are the fundamentals researcher for Robo Trader. Gather current factual data about "
                "earnings, margins, valuation, growth, and financial health. Do not write a trading thesis."
            ),
            tools=["WebSearch", "WebFetch"],
            model="haiku",
        ),
        "filings-researcher": AgentDefinition(
            description="Use for exchange filings, company disclosures, and other official notices.",
            prompt=(
                "You are the filings researcher for Robo Trader. Prioritize exchange filings, investor "
                "relations releases, and official company disclosures. Extract only verifiable facts."
            ),
            tools=["WebSearch", "WebFetch"],
            model="haiku",
        ),
        "market-context-researcher": AgentDefinition(
            description="Use for price action, analyst commentary, sector context, and relative-strength color.",
            prompt=(
                "You are the market-context researcher for Robo Trader. Gather concise factual market "
                "context and recent price-action framing without inventing levels or signals."
            ),
            tools=["WebSearch", "WebFetch"],
            model="haiku",
        ),
    }

    async def collect_symbol_research(
        self,
        symbol: str,
        *,
        company_name: Optional[str] = None,
        market: str = "Indian equities",
        research_brief: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Collect fresh research for a single symbol."""
        manager = await ClaudeSDKClientManager.get_instance()
        client_type = f"claude_market_research_{symbol.lower()}"
        fetched_at = datetime.now(timezone.utc).isoformat()
        subject = company_name or symbol
        prompt = self._build_research_prompt(
            symbol=symbol,
            subject=subject,
            market=market,
            research_brief=research_brief,
        )
        options = self._build_research_options()

        client = await manager.get_client(client_type, options, force_recreate=True)
        try:
            raw_text = await query_with_timeout(client, prompt, timeout=90.0)
            usage_limited_message = self._extract_usage_limited_message(raw_text)
            if usage_limited_message:
                return self._empty_result(
                    symbol=symbol,
                    fetched_at=fetched_at,
                    error=usage_limited_message,
                )
            return self._parse_research_result(
                symbol=symbol,
                fetched_at=fetched_at,
                raw_text=raw_text,
            )
        except Exception as exc:
            logger.warning("Claude market research failed for %s: %s", symbol, exc)
            return self._empty_result(
                symbol=symbol,
                fetched_at=fetched_at,
                error=str(exc),
            )
        finally:
            try:
                await manager.cleanup_client(client_type)
            except Exception:
                logger.debug("Failed cleaning up Claude market research client %s", client_type, exc_info=True)

    async def collect_batch_symbol_research(
        self,
        symbols: List[str],
        *,
        company_names: Optional[Dict[str, str]] = None,
        market: str = "Indian equities",
        research_brief: Optional[str] = None,
        max_concurrent: int = 3,
    ) -> Dict[str, Dict[str, Any]]:
        """Collect fresh research for multiple symbols concurrently."""
        if not symbols:
            return {}

        semaphore = asyncio.Semaphore(max(1, max_concurrent))
        names = company_names or {}

        async def _collect(one_symbol: str) -> tuple[str, Dict[str, Any]]:
            async with semaphore:
                result = await self.collect_symbol_research(
                    one_symbol,
                    company_name=names.get(one_symbol),
                    market=market,
                    research_brief=research_brief,
                )
                return one_symbol, result

        pairs = await asyncio.gather(*[_collect(symbol) for symbol in symbols])
        return {symbol: result for symbol, result in pairs}

    @classmethod
    def _build_research_prompt(
        cls,
        *,
        symbol: str,
        subject: str,
        market: str,
        research_brief: Optional[str],
    ) -> str:
        sections = [
            f"Research {subject} ({symbol}) for a {market} swing-trading workflow.",
            "Use WebSearch and WebFetch when needed.",
            (
                "Use the news-researcher, fundamentals-researcher, filings-researcher, and "
                "market-context-researcher subagents when they would improve coverage."
            ),
            "Gather fresh factual evidence only. Do not write a trade recommendation.",
        ]
        if research_brief:
            sections.append(f"Additional research brief:\n{research_brief.strip()}")
        sections.extend(
            [
                "Return plain text in exactly this format, keeping each field to one concise paragraph:",
                "SUMMARY: <overall synopsis>",
                "NEWS: <fresh company or sector news that matters now>",
                "FINANCIALS: <latest earnings, valuation, or balance-sheet facts>",
                "FILINGS: <recent exchange/company filing or disclosure facts>",
                "MARKET: <price action, analyst view, or sector/relative-strength context>",
                "FACT 1: <specific fact>",
                "URL 1: <https://...>",
                "FACT 2: <specific fact>",
                "URL 2: <https://...>",
                "FACT 3: <specific fact>",
                "URL 3: <https://...>",
                "RISK 1: <specific risk>",
                "RISK 2: <specific risk>",
                "Prefer official company, exchange, filing, or reputable financial-news sources.",
                "If a section is unavailable, leave it blank but keep the line.",
            ]
        )
        return "\n".join(sections)

    @classmethod
    def _build_research_options(cls) -> ClaudeAgentOptions:
        return ClaudeAgentOptions(
            allowed_tools=["Task", "WebSearch", "WebFetch"],
            agents=cls._SPECIALIST_AGENTS,
            max_turns=5,
            max_budget_usd=0.65,
            model="haiku",
            system_prompt=(
                "You are the External Market Research Agent for Robo Trader. "
                "Gather fresh factual evidence only. Do not write a trading thesis."
            ),
        )

    @classmethod
    def _parse_research_result(
        cls,
        *,
        symbol: str,
        fetched_at: str,
        raw_text: str,
    ) -> Dict[str, Any]:
        fields = {
            "summary": cls._extract_field(raw_text, "SUMMARY"),
            "news": cls._extract_field(raw_text, "NEWS"),
            "financial_data": cls._extract_field(raw_text, "FINANCIALS"),
            "filings": cls._extract_field(raw_text, "FILINGS"),
            "market_context": cls._extract_field(raw_text, "MARKET"),
        }

        source_summary: List[Dict[str, Any]] = []
        evidence_citations: List[Dict[str, Any]] = []
        evidence: List[str] = []
        risks: List[str] = []

        section_sources = (
            ("news", "claude_web_news", "Fresh news context"),
            ("financial_data", "claude_web_fundamentals", "Fresh fundamentals context"),
            ("filings", "claude_web_filings", "Fresh filing context"),
            ("market_context", "claude_web_market", "Fresh market context"),
        )
        for key, source_type, label in section_sources:
            value = fields.get(key, "")
            if value:
                source_summary.append(
                    {
                        "source_type": source_type,
                        "label": label,
                        "timestamp": fetched_at,
                        "freshness": "fresh",
                        "detail": value,
                    }
                )

        for idx in range(1, 4):
            fact = cls._extract_field(raw_text, f"FACT {idx}")
            url = cls._extract_field(raw_text, f"URL {idx}")
            if fact:
                evidence.append(fact)
            if fact or url:
                evidence_citations.append(
                    {
                        "reference": url,
                        "quote": fact,
                        "source_type": "claude_web_research",
                        "timestamp": fetched_at,
                    }
                )
                source_summary.append(
                    {
                        "source_type": "claude_web_research",
                        "label": f"Fresh cited research #{idx}",
                        "timestamp": fetched_at,
                        "freshness": "fresh",
                        "detail": fact or url,
                    }
                )

        for idx in range(1, 3):
            risk = cls._extract_field(raw_text, f"RISK {idx}")
            if risk:
                risks.append(risk)

        return {
            "symbol": symbol,
            "research_timestamp": fetched_at,
            "summary": fields["summary"],
            "research_summary": fields["news"] or fields["summary"],
            "news": fields["news"],
            "financial_data": fields["financial_data"],
            "filings": fields["filings"],
            "market_context": fields["market_context"],
            "sources": [item["reference"] for item in evidence_citations if item["reference"]],
            "source_summary": source_summary,
            "evidence_citations": evidence_citations,
            "evidence": evidence,
            "risks": risks,
            "errors": [],
            "raw_text": raw_text,
        }

    @staticmethod
    def _extract_field(raw_text: str, label: str) -> str:
        pattern = re.compile(rf"^{re.escape(label)}:\s*(.*)$", flags=re.MULTILINE)
        match = pattern.search(raw_text)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _extract_usage_limited_message(raw_text: str) -> str:
        lowered = (raw_text or "").lower()
        if (
            "out of extra usage" in lowered
            or "rate limit" in lowered
            or "spending cap reached" in lowered
            or "spending cap" in lowered
        ):
            match = ClaudeMarketResearchService._URL_RE.sub("", raw_text or "").strip()
            return match or "Claude usage is temporarily exhausted."
        return ""

    @staticmethod
    def _empty_result(*, symbol: str, fetched_at: str, error: str) -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "research_timestamp": fetched_at,
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
            "raw_text": "",
        }
