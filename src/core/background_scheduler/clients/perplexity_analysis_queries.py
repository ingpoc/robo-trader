"""
Analysis Query Module for Perplexity API

Handles sentiment analysis, recommendations, and general analysis queries.
"""

from typing import List, Optional, Any
from loguru import logger

from .perplexity_prompt_manager import PromptManager


class AnalysisQueries:
    """Handles analysis-related queries to Perplexity API."""

    def __init__(
        self,
        api_caller: Any,
        prompt_manager: PromptManager,
    ):
        """Initialize analysis queries handler.

        Args:
            api_caller: Callable API handler
            prompt_manager: PromptManager instance
        """
        self.api_caller = api_caller
        self.prompt_manager = prompt_manager

    async def analyze_sentiment(
        self,
        symbols: List[str],
        max_tokens: int = 2000
    ) -> Optional[str]:
        """Analyze market sentiment for given stocks.

        Provides sentiment analysis from news and analyst commentary.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with sentiment analysis data
        """
        symbols_str = ", ".join(symbols)
        query = f"""Analyze current market sentiment for stocks: {symbols_str}

Provide sentiment analysis including:
- Overall sentiment score (-1 to 1)
- Bullish vs bearish indicators
- Key sentiment drivers (earnings, news, analyst ratings)
- Short-term vs long-term sentiment
- Momentum indicators
- Institutional vs retail sentiment

Format as JSON."""

        return await self.api_caller(
            query=query,
            search_recency="week",
            max_search_results=15,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def generate_recommendations(
        self,
        symbols: List[str],
        analysis_data: Optional[str] = None,
        max_tokens: int = 3000
    ) -> Optional[str]:
        """Generate trading recommendations based on analysis.

        Combines technical, fundamental, and sentiment data for recommendations.

        Args:
            symbols: List of stock symbols
            analysis_data: Optional pre-computed analysis data
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with recommendations
        """
        symbols_str = ", ".join(symbols)

        if analysis_data:
            query = f"""Based on the following analysis data for {symbols_str}:

{analysis_data}

Generate trading recommendations including:
- Buy/Hold/Sell rating with confidence level
- Price targets (12-month, 6-month, 3-month)
- Key catalysts to watch
- Risk factors to monitor
- Position sizing recommendations
- Entry and exit points

Format as JSON."""
        else:
            query = f"""Generate comprehensive trading recommendations for {symbols_str} including:
- Current price targets and rating (Buy/Hold/Sell)
- Technical analysis and support/resistance levels
- Fundamental valuation assessment
- Sentiment analysis
- Key catalysts and events
- Risk assessment
- Suitable position sizes based on risk profile

Format as JSON with recommendations for each stock."""

        return await self.api_caller(
            query=query,
            search_recency="week",
            max_search_results=20,
            max_tokens=max_tokens,
            response_format="json"
        )
