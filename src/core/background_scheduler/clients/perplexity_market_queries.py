"""
Market News Query Module for Perplexity API

Handles market news, earnings announcements, and daily news queries.
"""

from typing import Any, List, Optional


from .perplexity_prompt_manager import PromptManager


class MarketQueries:
    """Handles market news and news-related queries to Perplexity API."""

    def __init__(
        self,
        api_caller: Any,
        prompt_manager: PromptManager,
    ):
        """Initialize market queries handler.

        Args:
            api_caller: Callable API handler
            prompt_manager: PromptManager instance
        """
        self.api_caller = api_caller
        self.prompt_manager = prompt_manager

    async def fetch_market_news(
        self, symbols: List[str], max_tokens: int = 4000
    ) -> Optional[str]:
        """Fetch recent market-moving news for given stocks.

        Focuses on significant news events that impact stock prices.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with market news data, or None on failure
        """
        prompt_template = await self.prompt_manager.get_prompt("news_processor")

        symbols_str = ", ".join(symbols)
        query = f"For each stock ({symbols_str}):\n\n{prompt_template}"

        return await self.api_caller(
            query=query,
            search_recency="week",
            max_search_results=20,
            max_tokens=max_tokens,
            response_format="json",
        )

    async def fetch_daily_news(
        self, symbols: List[str], max_tokens: int = 3000
    ) -> Optional[str]:
        """Fetch daily news updates for market monitoring.

        Provides concise news for routine daily monitoring.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with daily news data
        """
        prompt_template = await self.prompt_manager.get_prompt("news_processor")

        symbols_str = ", ".join(symbols)
        query = f"""Provide today's market news for stocks: {symbols_str}

{prompt_template}

Focus on:
- News from the last 24 hours
- Significant market events only
- Clear impact on stock price (high impact items only)"""

        return await self.api_caller(
            query=query,
            search_recency="day",
            max_search_results=10,
            max_tokens=max_tokens,
            response_format="json",
        )
