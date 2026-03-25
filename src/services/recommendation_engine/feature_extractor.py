"""
Feature Extractor Service

Replaces free-form "should I buy?" Claude prompts with specific factual questions.
Each extraction prompt asks targeted, independently verifiable questions.
Returns structured features — never buy/sell opinions.

Uses ClaudeSDKClientManager per project rules (never import anthropic directly).
"""

import json
import logging
import time
from typing import Dict, Any, Optional, List

from claude_agent_sdk import ClaudeAgentOptions

from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout
from src.models.research_ledger import (
    ResearchLedgerEntry,
    ManagementFeatures,
    FinancialFeatures,
    CatalystFeatures,
    MarketFeatures,
)

logger = logging.getLogger(__name__)

# Extraction timeout per prompt (seconds)
EXTRACTION_TIMEOUT = 30


class FeatureExtractor:
    """
    Extracts structured features from unstructured data using Claude.

    Instead of asking "should I buy?", asks specific factual questions
    and maps answers to typed Pydantic models.
    """

    def __init__(self):
        self.client_manager: Optional[ClaudeSDKClientManager] = None
        self.client_type = "feature_extractor"
        self.client_options = ClaudeAgentOptions(
            allowed_tools=[],
            max_turns=1,
            model="haiku",
            system_prompt=(
                "You are a financial data extraction assistant. "
                "Extract factual information and return only valid JSON. "
                "Use null for unknown values. Never provide opinions or recommendations."
            ),
        )

    async def initialize(self) -> None:
        """Initialize Claude SDK client."""
        self.client_manager = await ClaudeSDKClientManager.get_instance()
        logger.info("FeatureExtractor initialized with Claude SDK")

    async def extract_features(
        self,
        symbol: str,
        research_data: Dict[str, Any],
    ) -> ResearchLedgerEntry:
        """
        Extract structured features for a symbol from research data.

        Args:
            symbol: Stock symbol (e.g., "RELIANCE")
            research_data: Dict with keys like "news", "financials", "filings", "market_data"

        Returns:
            ResearchLedgerEntry with all feature groups populated
        """
        start_time = time.monotonic()

        entry = ResearchLedgerEntry(symbol=symbol, sources=[])

        # Extract each feature group independently — failure in one doesn't block others
        entry.management = await self._extract_management(symbol, research_data)
        entry.financial = await self._extract_financial(symbol, research_data)
        entry.catalyst = await self._extract_catalyst(symbol, research_data)
        entry.market = await self._extract_market(symbol, research_data)

        # Track sources
        if research_data.get("news"):
            entry.sources.append("claude_web_news")
        if research_data.get("financials"):
            entry.sources.append("financial_statements")
        if research_data.get("filings"):
            entry.sources.append("exchange_filings")
        if research_data.get("market_data"):
            entry.sources.append("market_data")

        entry.extraction_duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(f"Extracted features for {symbol} in {entry.extraction_duration_ms}ms")

        return entry

    async def _extract_management(
        self, symbol: str, data: Dict[str, Any]
    ) -> ManagementFeatures:
        """Extract management/governance features."""
        news = data.get("news", "No news available")
        filings = data.get("filings", "No filings available")

        prompt = f"""Analyze the following news and filings for {symbol} and answer each question as JSON.
If you cannot determine the answer, use null.

News: {_truncate(str(news), 3000)}
Filings: {_truncate(str(filings), 2000)}

Answer ONLY with this JSON (no other text):
{{
    "guidance_raised": true/false/null,
    "guidance_lowered": true/false/null,
    "promoter_pledge_change_pct": number/null,
    "dilution_signal": true/false/null,
    "insider_buying_net_90d": number/null,
    "ceo_cfo_change_recent": true/false/null,
    "auditor_flags": true/false/null
}}"""

        result = await self._query_claude(prompt)
        return _parse_features(result, ManagementFeatures)

    async def _extract_financial(
        self, symbol: str, data: Dict[str, Any]
    ) -> FinancialFeatures:
        """Extract financial metrics."""
        financials = data.get("financials", "No financial data available")

        prompt = f"""Analyze the following financial data for {symbol} and answer each question as JSON.
If you cannot determine the answer, use null.

Financial Data: {_truncate(str(financials), 4000)}

Answer ONLY with this JSON (no other text):
{{
    "revenue_growth_yoy_pct": number/null,
    "eps_growth_yoy_pct": number/null,
    "operating_margin_trend": "expanding"/"stable"/"contracting"/null,
    "free_cash_flow_positive": true/false/null,
    "debt_equity_ratio": number/null,
    "return_on_equity_pct": number/null,
    "revenue_surprise_pct": number/null,
    "eps_surprise_pct": number/null
}}"""

        result = await self._query_claude(prompt)
        return _parse_features(result, FinancialFeatures)

    async def _extract_catalyst(
        self, symbol: str, data: Dict[str, Any]
    ) -> CatalystFeatures:
        """Extract catalyst and event signals."""
        news = data.get("news", "No news available")
        filings = data.get("filings", "No filings available")

        prompt = f"""Analyze the following data for {symbol} and answer each question as JSON.
If you cannot determine the answer, use null.

News: {_truncate(str(news), 3000)}
Filings: {_truncate(str(filings), 2000)}

Answer ONLY with this JSON (no other text):
{{
    "results_date_in_window": true/false/null,
    "order_book_win": true/false/null,
    "regulatory_approval": true/false/null,
    "sector_tailwind": true/false/null,
    "story_crowded": true/false/null,
    "demerger_or_restructuring": true/false/null
}}"""

        result = await self._query_claude(prompt)
        return _parse_features(result, CatalystFeatures)

    async def _extract_market(
        self, symbol: str, data: Dict[str, Any]
    ) -> MarketFeatures:
        """Extract market and technical context."""
        market_data = data.get("market_data", "No market data available")

        prompt = f"""Analyze the following market data for {symbol} and answer each question as JSON.
If you cannot determine the answer, use null.

Market Data: {_truncate(str(market_data), 4000)}

Answer ONLY with this JSON (no other text):
{{
    "relative_strength_vs_nifty_90d": number/null,
    "sector_momentum": "expanding"/"stable"/"contracting"/null,
    "institutional_holding_change_pct": number/null,
    "delivery_pct_avg_20d": number/null,
    "base_breakout_setup": true/false/null,
    "volume_expansion": true/false/null
}}"""

        result = await self._query_claude(prompt)
        return _parse_features(result, MarketFeatures)

    async def _query_claude(self, prompt: str) -> Optional[str]:
        """Query Claude with timeout. Returns raw response text or None on failure."""
        if not self.client_manager:
            logger.warning("FeatureExtractor not initialized — returning None")
            return None

        try:
            client = await self.client_manager.get_client(
                self.client_type,
                self.client_options,
            )
            response = await query_with_timeout(
                client,
                prompt,
                timeout=EXTRACTION_TIMEOUT,
            )
            return response
        except Exception as e:
            logger.warning(f"Claude extraction failed: {e}")
            return None


def _truncate(text: str, max_len: int) -> str:
    """Truncate text to max length."""
    if len(text) <= max_len:
        return text
    return text[:max_len] + "... [truncated]"


def _parse_features(raw_response: Optional[str], model_class):
    """Parse Claude's JSON response into a Pydantic model. Returns defaults on failure."""
    if not raw_response:
        return model_class()

    try:
        # Extract JSON from response (Claude may wrap in markdown code blocks)
        text = raw_response.strip()
        if text.startswith("```"):
            # Remove code block markers
            lines = text.split("\n")
            text = "\n".join(
                line for line in lines
                if not line.strip().startswith("```")
            )

        parsed = json.loads(text)
        return model_class(**parsed)
    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse features into {model_class.__name__}: {e}")
        return model_class()
