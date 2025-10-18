"""
Unified Perplexity API client for Background Scheduler.

Consolidates all Perplexity API interactions in a single module with:
- API key rotation
- Rate limit handling
- Automatic retry logic
- Structured response parsing
"""

import asyncio
import os
from typing import Dict, List, Optional, Any

import httpx
from loguru import logger
from openai import OpenAI, RateLimitError, AuthenticationError

from .api_key_rotator import APIKeyRotator


class PerplexityClient:
    """Unified client for Perplexity API interactions with key rotation."""

    def __init__(
        self,
        api_key_rotator: Optional[APIKeyRotator] = None,
        model: str = "sonar-pro",
        timeout_seconds: int = 45
    ):
        """Initialize Perplexity client.

        Args:
            api_key_rotator: APIKeyRotator instance for key management
            model: Perplexity model to use (default: sonar-pro)
            timeout_seconds: API request timeout
        """
        self.model = model
        self.timeout_seconds = timeout_seconds

        if api_key_rotator is None:
            api_keys = self._load_api_keys_from_env()
            api_key_rotator = APIKeyRotator(api_keys)

        self.key_rotator = api_key_rotator

    @staticmethod
    def _load_api_keys_from_env() -> List[str]:
        """Load Perplexity API keys from environment variables.

        Returns:
            List of non-empty API keys
        """
        keys = [
            os.getenv('PERPLEXITY_API_KEY_1'),
            os.getenv('PERPLEXITY_API_KEY_2'),
            os.getenv('PERPLEXITY_API_KEY_3')
        ]
        return [key for key in keys if key]

    async def fetch_news_and_earnings(
        self,
        symbols: List[str],
        search_recency: str = "day",
        max_search_results: int = 10,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """Fetch news and earnings data for multiple symbols.

        Args:
            symbols: List of stock symbols
            search_recency: Recency filter for search ('day', 'week', 'month')
            max_search_results: Maximum search results to return
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with news and earnings data, or None on failure
        """
        symbols_str = ", ".join(symbols)
        query = f"""For each of these stocks ({symbols_str}), provide the latest news and earnings information.

Focus on:
- Recent news from last 24 hours (earnings, major announcements, market-moving events)
- Latest earnings report details (EPS, revenue, guidance)
- Next earnings date if available
- Overall sentiment (positive/negative/neutral)

Return structured data for each stock."""

        return await self._call_perplexity_api(
            query=query,
            search_recency=search_recency,
            max_search_results=max_search_results,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_daily_news(
        self,
        symbols: List[str],
        max_tokens: int = 3000
    ) -> Optional[str]:
        """Fetch daily news summary for symbols.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with daily news, or None on failure
        """
        symbols_str = ", ".join(symbols)
        query = f"""Provide a comprehensive daily news summary for these stocks: {symbols_str}

Include:
- Major news and events affecting each stock
- Earnings announcements or reports
- Price movements and market impact
- Analyst updates or ratings changes
- Overall sentiment

Format as structured JSON with stock symbols as keys."""

        return await self._call_perplexity_api(
            query=query,
            search_recency="day",
            max_search_results=15,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def analyze_sentiment(
        self,
        content: str,
        context: str = ""
    ) -> Optional[str]:
        """Analyze sentiment of provided content.

        Args:
            content: Content to analyze
            context: Additional context for analysis

        Returns:
            Sentiment analysis result, or None on failure
        """
        query = f"""Analyze the sentiment of this financial content about stocks:

{content}

{f'Context: {context}' if context else ''}

Provide:
1. Overall sentiment (positive/negative/neutral)
2. Key positive points
3. Key negative points
4. Confidence level (0-100%)

Return as structured JSON."""

        return await self._call_perplexity_api(
            query=query,
            search_recency="day",
            max_search_results=5,
            max_tokens=1000,
            response_format="json"
        )

    async def generate_recommendations(
        self,
        analysis_context: Dict[str, Any]
    ) -> Optional[str]:
        """Generate trading recommendations based on analysis context.

        Args:
            analysis_context: Dict with 'news', 'earnings', 'technicals' keys

        Returns:
            Recommendations as JSON string, or None on failure
        """
        query = f"""Based on the following financial analysis, generate trading recommendations:

News Sentiment: {analysis_context.get('news', 'Not provided')}
Earnings Data: {analysis_context.get('earnings', 'Not provided')}
Technical Analysis: {analysis_context.get('technicals', 'Not provided')}

Provide:
1. Recommended action (BUY/HOLD/SELL)
2. Confidence level (0-100%)
3. Key risk factors
4. Time horizon
5. Target price or range

Return as structured JSON."""

        return await self._call_perplexity_api(
            query=query,
            search_recency="week",
            max_search_results=10,
            max_tokens=1500,
            response_format="json"
        )

    async def _call_perplexity_api(
        self,
        query: str,
        search_recency: str = "day",
        max_search_results: int = 10,
        max_tokens: int = 2000,
        response_format: str = "text"
    ) -> Optional[str]:
        """Make a call to Perplexity API with retry logic.

        Args:
            query: User query
            search_recency: Recency filter for search
            max_search_results: Max search results
            max_tokens: Max tokens in response
            response_format: Response format ('text' or 'json')

        Returns:
            API response content, or None on failure
        """
        max_retries = 3
        attempt = 0

        while attempt < max_retries:
            try:
                api_key = self.key_rotator.get_next_key()
                if not api_key:
                    logger.error("No Perplexity API keys available")
                    return None

                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.perplexity.ai",
                    http_client=httpx.Client(timeout=self.timeout_seconds)
                )

                response_format_config = {
                    "type": "text"
                }

                if response_format == "json":
                    response_format_config = {
                        "type": "json_schema",
                        "json_schema": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "data": {"type": "object"}
                                }
                            }
                        }
                    }

                completion = client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": query}],
                    max_tokens=max_tokens,
                    response_format=response_format_config if response_format == "json" else None,
                    web_search_options={
                        "search_recency_filter": search_recency,
                        "max_search_results": max_search_results
                    }
                )

                response_content = completion.choices[0].message.content
                logger.info(f"Perplexity API call succeeded (model: {self.model})")
                return response_content

            except RateLimitError as e:
                attempt += 1
                logger.warning(f"Perplexity rate limit (attempt {attempt}/{max_retries}): {e}")
                self.key_rotator.rotate_on_error(self.key_rotator.get_current_key())

                if attempt < max_retries:
                    backoff_delay = min(30, 2 ** (attempt - 1))
                    logger.info(f"Rate limited, waiting {backoff_delay} seconds")
                    await asyncio.sleep(backoff_delay)
                continue

            except AuthenticationError as e:
                attempt += 1
                logger.warning(f"Perplexity authentication error (attempt {attempt}/{max_retries}): {e}")
                self.key_rotator.rotate_on_error(self.key_rotator.get_current_key())

                if attempt < max_retries:
                    await asyncio.sleep(1)
                continue

            except Exception as e:
                attempt += 1
                logger.error(f"Perplexity API error (attempt {attempt}/{max_retries}): {e}")

                if attempt < max_retries:
                    await asyncio.sleep(1)
                continue

        logger.error(f"Perplexity API failed after {max_retries} attempts")
        return None
