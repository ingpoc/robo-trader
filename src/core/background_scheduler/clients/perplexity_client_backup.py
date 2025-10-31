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
from .retry_handler import RetryConfig, retry_on_rate_limit


class PerplexityClient:
    """Unified client for Perplexity API interactions with key rotation."""

    def __init__(
        self,
        api_key_rotator: Optional[APIKeyRotator] = None,
        model: str = "sonar-pro",
        timeout_seconds: int = 45,
        configuration_state: Optional[Any] = None
    ):
        """Initialize Perplexity client.

        Args:
            api_key_rotator: APIKeyRotator instance for key management
            model: Perplexity model to use (default: sonar-pro)
            timeout_seconds: API request timeout
            configuration_state: ConfigurationState for fetching prompts from database
        """
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.configuration_state = configuration_state

        if api_key_rotator is None:
            api_keys = self._load_api_keys_from_env()
            api_key_rotator = APIKeyRotator(api_keys)

        self.key_rotator = api_key_rotator

        # Cache for prompts to avoid repeated database calls
        self._prompt_cache: Dict[str, str] = {}

    async def _get_prompt_from_db(self, prompt_name: str) -> str:
        """Get prompt content from database, with fallback to hardcoded prompts."""
        # Check cache first
        if prompt_name in self._prompt_cache:
            return self._prompt_cache[prompt_name]

        # Try to fetch from database
        if self.configuration_state:
            try:
                prompt_data = await self.configuration_state.get_prompt_config(prompt_name)
                if prompt_data and prompt_data.get('content'):
                    self._prompt_cache[prompt_name] = prompt_data['content']
                    logger.info(f"Using database prompt for {prompt_name}")
                    return prompt_data['content']
            except Exception as e:
                logger.warning(f"Failed to fetch prompt {prompt_name} from database: {e}")

        # Fallback to hardcoded prompts
        logger.info(f"Using hardcoded fallback prompt for {prompt_name}")
        fallback_prompt = self._get_fallback_prompt(prompt_name)
        self._prompt_cache[prompt_name] = fallback_prompt
        return fallback_prompt

    def _get_fallback_prompt(self, prompt_name: str) -> str:
        """Get hardcoded fallback prompt for when database is unavailable."""
        if prompt_name == "earnings_processor":
            return """For each stock, provide DETAILED earnings and financial fundamentals data in JSON format.

EARNINGS DATA (required):
- Latest quarterly earnings report date and fiscal period
- EPS (Actual vs Estimated): include exact numbers
- Revenue (Actual vs Estimated): include exact numbers in millions/billions
- EPS Surprise percentage
- Management guidance and outlook
- Next earnings date
- Year-over-year earnings growth rate (%)
- Quarter-over-quarter earnings growth rate (%)
- Net profit margins (gross, operating, net %)
- Revenue growth rate (YoY and QoQ %)

FUNDAMENTAL METRICS (required):
- Net profit growth trend (last 3-4 quarters with percentages)
- Current quarter profit growth vs prior quarter (%)
- Debt-to-Equity ratio
- Return on Equity (ROE %)
- Profit margins: Gross %, Operating %, Net %
- Return on Assets (ROA %)"""

        elif prompt_name == "news_processor":
            return """For each stock, provide recent market-moving news in JSON format.

NEWS DATA (required for each item):
- News title
- News summary (2-3 sentences)
- Full content/detailed analysis
- News source and exact publication date
- Type: (earnings_announcement, product_launch, regulatory, merger, guidance, dividend, stock_split, bankruptcy, restructuring, industry_trend, analyst_rating_change, contract_win, other)
- Sentiment: (positive, negative, neutral)
- Impact level: (high, medium, low) on stock price
- Relevance to stock price: (direct_impact, indirect_impact, contextual)
- Key metrics mentioned: list any financial metrics, growth rates, or numbers mentioned
- Why this is important: brief explanation of significance

SPECIFIC FOCUS (priority order):
1. Earnings announcements or reports from last 7 days with beat/miss info
2. Analyst upgrades/downgrades/rating changes from last 7 days
3. Major product launches, approvals, or announcements
4. Regulatory approvals, challenges, or compliance issues
5. M&A activity (acquisitions, mergers, divestitures)
6. Dividend announcements or changes
7. Major contract wins or losses
8. Industry trends affecting multiple companies in sector
9. Market analyst commentary and price targets"""

        elif prompt_name == "fundamental_analyzer":
            return """Analyze fundamental data and provide comprehensive financial analysis in JSON format.

ANALYSIS REQUIREMENTS:
- Company financial health assessment
- Growth trajectory evaluation
- Valuation analysis with industry comparisons
- Risk assessment and investment recommendations
- Key financial ratios and metrics interpretation
- Future outlook based on current fundamentals"""

        else:
            return f"Provide analysis for {prompt_name}."

    @staticmethod
    def _load_api_keys_from_env() -> List[str]:
        """Load Perplexity API keys from environment variables.

        Supports both individual keys (PERPLEXITY_API_KEY_1, PERPLEXITY_API_KEY_2, etc.)
        and comma-separated keys (PERPLEXITY_API_KEYS).

        Returns:
            List of non-empty API keys
        """
        # First check for comma-separated keys
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
        # Get prompt from database
        prompt_template = await self._get_prompt_from_db("earnings_processor")

        # Format the query with symbols
        symbols_str = ", ".join(symbols)
        query = f"For each stock ({symbols_str}):\n\n{prompt_template}"

        return await self._call_perplexity_api(
            query=query,
            search_recency="week",
            max_search_results=15,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_market_news(
        self,
        symbols: List[str],
        max_tokens: int = 3000
    ) -> Optional[str]:
        """Fetch recent market-moving news and sentiment analysis.

        Requests categorized news with sentiment and impact assessment
        focused on events that affect stock price and investment decisions.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with news items, or None on failure
        """
        # Get prompt from database
        prompt_template = await self._get_prompt_from_db("news_processor")

        # Format the query with symbols
        symbols_str = ", ".join(symbols)
        query = f"For each stock ({symbols_str}):\n\n{prompt_template}"

        return await self._call_perplexity_api(
            query=query,
            search_recency="day",
            max_search_results=15,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_deep_fundamentals(
        self,
        symbols: List[str],
        max_tokens: int = 5000
    ) -> Optional[str]:
        """Fetch deep fundamental analysis for investment assessment.

        Provides comprehensive analysis of each stock's financial health,
        growth sustainability, competitive position, and investment rating.

        Args:
            symbols: List of stock symbols
            max_tokens: Maximum tokens in response

        Returns:
            JSON string with fundamental analysis, or None on failure
        """
        symbols_str = ", ".join(symbols)
        query = f"""Analyze and compare these stocks ({symbols_str}) on FUNDAMENTAL METRICS only. Return JSON.

For each stock provide complete analysis:

1. REVENUE & EARNINGS GROWTH:
   - Revenue growth: Last Q vs Q year-ago (%)
   - Earnings growth: Last Q vs Q year-ago (%)
   - Revenue trend: last 4 quarters (show direction and consistency)
   - Earnings trend: last 4 quarters (show direction and consistency)
   - Growth rate trajectory: accelerating/stable/decelerating

2. PROFITABILITY ASSESSMENT:
   - Gross margin (%) and trend
   - Operating margin (%) and trend
   - Net profit margin (%) and trend
   - Margin trend direction: improving/stable/declining

3. FINANCIAL POSITION ANALYSIS:
   - Debt-to-Equity ratio and assessment (healthy/moderate/risky)
   - Current Ratio (liquidity) and assessment
   - ROE (Return on Equity) % and assessment
   - ROA (Return on Assets) % and assessment
   - Cash-to-Debt ratio and strength

4. VALUATION ANALYSIS:
   - Current P/E ratio with industry average for context
   - Valuation assessment: expensive/fair/cheap with justification
   - PEG ratio assessment: undervalued/fairly valued/overvalued
   - Price-to-Book ratio and assessment

5. QUALITY METRICS:
   - Earnings quality score (1-10)
   - Cash flow to Net Income ratio (shows earnings quality)
   - Capex spending trends
   - Revenue quality (recurring vs one-time)

6. GROWTH SUSTAINABILITY ANALYSIS:
   - Can current growth rate be sustained? (yes/no with reasoning)
   - Major catalysts for future growth (2-3 catalysts)
   - Industry tailwinds (positive factors in sector)
   - Industry headwinds (negative factors in sector)
   - Competitive advantage strength: strong/moderate/weak
   - Competitive positioning vs peers

7. RISK ASSESSMENT:
   - Key risks to fundamental thesis (2-3 main risks)
   - Execution risks
   - Market/macro risks
   - Regulatory/compliance risks

8. INVESTMENT ASSESSMENT:
   - Fundamental score (1-100 scale, 75+ excellent, 50-75 good, below 50 weak)
   - Key strengths: top 2-3 positive factors
   - Key concerns: top 2-3 concerns or red flags
   - Fair value estimate if available (or "TBD")
   - Investment recommendation: STRONG_BUY/BUY/HOLD/SELL with confidence level (%)
   - Investment thesis: 2-3 sentence summary of why this recommendation

Scoring Rubric for Fundamental Score:
- 80-100: Exceptional fundamentals, strong moat, sustainable growth
- 65-79: Good fundamentals, solid growth, manageable risks
- 50-64: Adequate fundamentals, moderate growth, some concerns
- 35-49: Weak fundamentals, slowing growth, significant concerns
- Below 35: Poor fundamentals, declining performance, high risk

Use exact numerical values from recent reports. Mark fields as "TBD" only if data is genuinely unavailable - attempt to estimate where reasonable. Ensure all fields contain substantive information."""

        return await self._call_perplexity_api(
            query=query,
            search_recency="month",
            max_search_results=20,
            max_tokens=max_tokens,
            response_format="json"
        )

    async def fetch_news_and_earnings(
        self,
        symbols: List[str],
        search_recency: str = "day",
        max_search_results: int = 10,
        max_tokens: int = 2000
    ) -> Optional[str]:
        """Fetch news and earnings data for multiple symbols (legacy).

        DEPRECATED: Use fetch_earnings_fundamentals() and fetch_market_news() instead.
        This method kept for backward compatibility but provides incomplete data.

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
                # Create OpenAI client without specifying http_client - it will handle async automatically
                client = OpenAI(
                    api_key=api_key,
                    base_url="https://api.perplexity.ai"
                )

                response_format_config = {"type": "text"}
                if response_format == "json":
                    response_format_config = {
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
                                    },
                                    "required": ["stocks"]
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

            except AuthenticationError as e:
                logger.warning(f"Perplexity authentication error: {e}")
                self.key_rotator.rotate_on_error(api_key)
                raise RuntimeError(f"Authentication failed: {e}")

        try:
            # Use exponential backoff retry for rate limits
            return await retry_on_rate_limit(_make_request, max_retries=5)
        except Exception as e:
            logger.error(f"Perplexity API failed: {e}")
            return None
