"""
Unified Perplexity API Client for Background Scheduler

Consolidates all Perplexity API interactions using modular query handlers.
Includes API key rotation, rate limit handling, and automatic retry logic.
"""

import os
from typing import List, Optional, Any

from openai import OpenAI, AuthenticationError
from loguru import logger

from .api_key_rotator import APIKeyRotator
from .retry_handler import RetryConfig, retry_on_rate_limit
from .perplexity_prompt_manager import PromptManager
from .perplexity_earnings_queries import EarningsQueries
from .perplexity_market_queries import MarketQueries
from .perplexity_analysis_queries import AnalysisQueries


class PerplexityClient:
    """Unified client for Perplexity API interactions with key rotation."""

    def __init__(
        self,
        api_key_rotator: Optional[APIKeyRotator] = None,
        model: str = "sonar-pro",
        timeout_seconds: int = 45,
        configuration_state: Optional[Any] = None
    ):
        """Initialize Perplexity client with modular query handlers.

        Args:
            api_key_rotator: APIKeyRotator instance for key management
            model: Perplexity model to use (default: sonar-pro)
            timeout_seconds: API request timeout
            configuration_state: ConfigurationState for fetching prompts from database
        """
        self.model = model
        self.timeout_seconds = timeout_seconds

        if api_key_rotator is None:
            api_keys = self._load_api_keys_from_env()
            api_key_rotator = APIKeyRotator(api_keys)

        self.key_rotator = api_key_rotator

        # Initialize modular query handlers
        self.prompt_manager = PromptManager(configuration_state)
        self.earnings = EarningsQueries(self._call_perplexity_api, self.prompt_manager)
        self.market = MarketQueries(self._call_perplexity_api, self.prompt_manager)
        self.analysis = AnalysisQueries(self._call_perplexity_api, self.prompt_manager)

    @staticmethod
    def _load_api_keys_from_env() -> List[str]:
        """Load Perplexity API keys from environment variables.

        Supports both individual keys (PERPLEXITY_API_KEY_1, etc.)
        and comma-separated keys (PERPLEXITY_API_KEYS).

        Returns:
            List of non-empty API keys
        """
        keys_str = os.getenv('PERPLEXITY_API_KEYS', '')
        logger.info(f"Checking PERPLEXITY_API_KEYS: {repr(keys_str)}")
        if keys_str:
            keys = [key.strip() for key in keys_str.split(',') if key.strip()]
            logger.info(f"Parsed {len(keys)} keys from PERPLEXITY_API_KEYS")
            if keys:
                return keys

        # Fall back to individual key variables
        keys = [
            os.getenv('PERPLEXITY_API_KEY_1'),
            os.getenv('PERPLEXITY_API_KEY_2'),
            os.getenv('PERPLEXITY_API_KEY_3')
        ]
        filtered_keys = [key for key in keys if key]
        logger.info(f"Found {len(filtered_keys)} keys from individual variables")
        return filtered_keys

    async def _call_perplexity_api(
        self,
        query: str,
        search_recency: str = "day",
        max_search_results: int = 10,
        max_tokens: int = 2000,
        response_format: str = "text"
    ) -> Optional[str]:
        """Make a call to Perplexity API with exponential backoff retry.

        Uses retry_on_rate_limit for automatic exponential backoff on rate limits.
        Rotates API keys on authentication failures.

        Args:
            query: User query
            search_recency: Recency filter for search
            max_search_results: Max search results
            max_tokens: Max tokens in response
            response_format: Response format ('text' or 'json')

        Returns:
            API response content, or None on failure
        """
        async def _make_request() -> str:
            """Inner function for retry wrapper."""
            api_key = self.key_rotator.get_next_key()
            if not api_key:
                logger.error("No Perplexity API keys available")
                raise RuntimeError("No API keys available")

            try:
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.perplexity.ai"
                )

                response_format_config = self._get_response_format_config(response_format)

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

            except AuthenticationError as e:
                logger.warning(f"Perplexity authentication error: {e}")
                self.key_rotator.rotate_on_error(api_key)
                raise RuntimeError(f"Authentication failed: {e}")

        try:
            return await retry_on_rate_limit(_make_request, max_retries=5)
        except Exception as e:
            logger.error(f"Perplexity API failed: {e}")
            return None

    @staticmethod
    def _get_response_format_config(response_format: str) -> dict:
        """Get response format configuration for API call.

        Args:
            response_format: Format type ('text' or 'json')

        Returns:
            Response format configuration dict
        """
        if response_format != "json":
            return {"type": "text"}

        return {
            "type": "json_schema",
            "json_schema": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "stocks": {
                            "type": "object",
                            "patternProperties": {
                                ".*": {
                                    "type": "object",
                                    "properties": {
                                        "earnings": {
                                            "type": "object",
                                            "properties": {
                                                "latest_quarter": {"type": "object"},
                                                "growth_rates": {"type": "object"},
                                                "margins": {"type": "object"},
                                                "next_earnings_date": {"type": "string"}
                                            },
                                            "required": ["latest_quarter", "growth_rates", "margins"]
                                        },
                                        "fundamentals": {
                                            "type": "object",
                                            "properties": {
                                                "valuation": {"type": "object"},
                                                "profitability": {"type": "object"},
                                                "financial_health": {"type": "object"},
                                                "growth": {"type": "object"}
                                            }
                                        },
                                        "analysis": {
                                            "type": "object",
                                            "properties": {
                                                "recommendation": {"type": "string"},
                                                "confidence_score": {"type": "number"},
                                                "risk_level": {"type": "string"},
                                                "key_drivers": {"type": "array"},
                                                "risk_factors": {"type": "array"}
                                            }
                                        }
                                    },
                                    "required": ["earnings", "fundamentals", "analysis"]
                                }
                            }
                        }
                    },
                    "required": ["stocks"]
                }
            }
        }
