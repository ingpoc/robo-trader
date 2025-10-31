"""
Earnings and Fundamentals Query Module for Perplexity API

Handles earnings announcements, financial fundamentals, and deep analysis queries.
"""

from typing import List, Optional, Any
from loguru import logger

from .perplexity_prompt_manager import PromptManager


class EarningsQueries:
    """Handles earnings and fundamental analysis queries to Perplexity API."""

    def __init__(
        self,
        api_caller: Any,
        prompt_manager: PromptManager,
    ):
        """Initialize earnings queries handler.

        Args:
            api_caller: Callable API handler (e.g., _call_perplexity_api)
            prompt_manager: PromptManager instance
        """
        self.api_caller = api_caller
        self.prompt_manager = prompt_manager

    async def fetch_earnings_fundamentals(
        self,
        symbols: List[str],
        max_tokens: int = 4000
    ) -> Optional[str]:
        """Fetch comprehensive earnings and financial fundamentals data.

        Requests detailed metrics needed for fundamental analysis including
        growth rates, profitability, valuation, and financial health.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with earnings and fundamentals data, or None on failure
        """
        prompt_template = await self.prompt_manager.get_prompt("earnings_processor")

        symbols_str = ", ".join(symbols)
        query = f"For each stock ({symbols_str}):\n\n{prompt_template}"

        return await self.api_caller(
            query=query,
            search_recency="week",
            max_search_results=15,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_news_and_earnings(
        self,
        symbols: List[str],
        max_tokens: int = 4000
    ) -> Optional[str]:
        """Fetch both news and earnings data in a single query.

        Combines news and earnings processing to reduce API calls.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with combined news and earnings data
        """
        earnings_prompt = await self.prompt_manager.get_prompt("earnings_processor")
        news_prompt = await self.prompt_manager.get_prompt("news_processor")

        symbols_str = ", ".join(symbols)
        query = f"""For each stock ({symbols_str}), provide:

EARNINGS DATA:
{earnings_prompt}

NEWS DATA:
{news_prompt}

Format as JSON with 'earnings' and 'news' keys."""

        return await self.api_caller(
            query=query,
            search_recency="week",
            max_search_results=20,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_deep_fundamentals(
        self,
        symbols: List[str],
        max_tokens: int = 6000
    ) -> Optional[str]:
        """Fetch deep fundamental analysis for comprehensive evaluation.

        Provides extended analysis with additional metrics and comparisons.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response (higher for deep analysis)

        Returns:
            JSON string with deep fundamental analysis data
        """
        prompt_template = await self.prompt_manager.get_prompt("earnings_processor")

        symbols_str = ", ".join(symbols)
        query = f"""Provide DEEP FUNDAMENTAL ANALYSIS for stocks: {symbols_str}

{prompt_template}

ADDITIONAL ANALYSIS:
- Peer comparison metrics
- Historical trend analysis (last 3 years)
- Key catalysts and risk factors
- Industry positioning and competitive advantage
- Management quality assessment
- Dividend sustainability analysis
- Debt maturity schedule and refinancing risk"""

        return await self.api_caller(
            query=query,
            search_recency="month",
            max_search_results=25,
            max_tokens=max_tokens,
            response_format="json"
        )
