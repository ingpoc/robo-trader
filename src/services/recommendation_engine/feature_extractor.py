"""
Feature Extractor Service

Uses one structured Codex call per symbol to extract the research-ledger features
needed by the deterministic scorer. This keeps discovery token-efficient and
avoids redundant multi-prompt extraction passes.
"""

import logging
import time
from typing import Any, Dict, Optional

from src.models.research_ledger import (
    CatalystFeatures,
    FinancialFeatures,
    ManagementFeatures,
    MarketFeatures,
    ResearchLedgerEntry,
)
from src.services.codex_runtime_client import CodexRuntimeClient, CodexRuntimeError

logger = logging.getLogger(__name__)

EXTRACTION_TIMEOUT = 30

FEATURE_EXTRACTION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "management": ManagementFeatures.model_json_schema(),
        "financial": FinancialFeatures.model_json_schema(),
        "catalyst": CatalystFeatures.model_json_schema(),
        "market": MarketFeatures.model_json_schema(),
        "sources": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["management", "financial", "catalyst", "market", "sources"],
}


class FeatureExtractor:
    """
    Extracts the structured research-ledger fields in one runtime call.

    The model is used only as a factual extractor. Deterministic scoring still
    decides BUY/HOLD/AVOID downstream.
    """

    def __init__(
        self,
        *,
        runtime_client: Optional[CodexRuntimeClient] = None,
        model: str = "gpt-5.4",
        reasoning: str = "low",
        working_directory: Optional[str] = None,
    ):
        self.runtime_client = runtime_client
        self.model = model
        self.reasoning = reasoning
        self.working_directory = working_directory

    async def initialize(self) -> None:
        """Initialize runtime dependencies."""
        logger.info("FeatureExtractor initialized with Codex runtime")

    async def extract_features(
        self,
        symbol: str,
        research_data: Dict[str, Any],
    ) -> ResearchLedgerEntry:
        """Extract all structured features for one symbol."""
        start_time = time.monotonic()
        entry = ResearchLedgerEntry(symbol=symbol, sources=[])

        payload = await self._extract_feature_bundle(symbol, research_data)
        if payload:
            entry.management = ManagementFeatures(**(payload.get("management") or {}))
            entry.financial = FinancialFeatures(**(payload.get("financial") or {}))
            entry.catalyst = CatalystFeatures(**(payload.get("catalyst") or {}))
            entry.market = MarketFeatures(**(payload.get("market") or {}))
            entry.sources = list(payload.get("sources") or [])
        else:
            if research_data.get("news"):
                entry.sources.append("codex_research_news")
            if research_data.get("financials"):
                entry.sources.append("financial_statements")
            if research_data.get("filings"):
                entry.sources.append("exchange_filings")
            if research_data.get("market_data"):
                entry.sources.append("market_data")

        entry.extraction_model = self.model
        entry.extraction_duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.info("Extracted features for %s in %sms", symbol, entry.extraction_duration_ms)
        return entry

    async def _extract_feature_bundle(
        self,
        symbol: str,
        research_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Extract all research-ledger groups in one structured runtime call."""
        if not self.runtime_client:
            logger.warning("FeatureExtractor runtime client not initialized — returning None")
            return None

        prompt = f"""Extract structured swing-trading features for {symbol}.
Use only the provided evidence.
If a field cannot be determined, use null.
Do not provide recommendations or narrative outside the schema.

News:
{_truncate(str(research_data.get("news", "")), 3500)}

Financials:
{_truncate(str(research_data.get("financials", "")), 3500)}

Filings:
{_truncate(str(research_data.get("filings", "")), 2500)}

Market Data:
{_truncate(str(research_data.get("market_data", "")), 2500)}

Populate management, financial, catalyst, and market fields.
For sources, include only simple identifiers from this set when supported by the evidence:
- codex_research_news
- financial_statements
- exchange_filings
- market_data
"""

        try:
            response = await self.runtime_client.run_structured(
                system_prompt=(
                    "You are a financial data extraction assistant. "
                    "Extract factual information and return only valid structured JSON. "
                    "Use null for unknown values. Never provide opinions or recommendations."
                ),
                prompt=prompt,
                output_schema=FEATURE_EXTRACTION_SCHEMA,
                model=self.model,
                reasoning=self.reasoning,
                timeout_seconds=EXTRACTION_TIMEOUT,
                web_search_enabled=False,
                network_access_enabled=False,
                working_directory=self.working_directory,
            )
            output = response.get("output") or {}
            if isinstance(output, dict):
                return output
            return None
        except CodexRuntimeError as e:
            logger.warning("Codex bundled extraction failed: %s", e)
            return None
        except Exception as e:
            logger.warning("Bundled feature extraction failed: %s", e)
            return None


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "... [truncated]"
