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
        symbols_str = ", ".join(symbols)
        query = f"""For each stock ({symbols_str}), provide DETAILED earnings and financial fundamentals data in JSON format.

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
- Return on Assets (ROA %)
- Current ratio

VALUATION METRICS (required):
- Price-to-Earnings (P/E) ratio
- Price-to-Sales (P/S) ratio
- Price-to-Book (P/B) ratio
- PEG ratio (P/E relative to growth)
- Industry average P/E for comparison
- Whether stock is trading above/below industry average

GROWTH POTENTIAL:
- Earnings growth forecast for next 2-4 quarters (%)
- Revenue growth forecast (%)
- Industry growth rate comparison (%)
- Company's competitive position in industry

FINANCIAL HEALTH:
- Current ratio (liquidity)
- Debt levels and trend (increasing/stable/decreasing)
- Cash position relative to debt
- Operating cash flow trend

RISK FACTORS:
- Company-specific risks (competition, regulation, dependence)
- Market risks and volatility (Beta)
- Macroeconomic factors affecting the stock

Return ONLY valid JSON with numerical values where possible. Include all metrics even if marked "TBD" - data completeness is critical."""

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
        symbols_str = ", ".join(symbols)
        query = f"""For each stock ({symbols_str}), provide recent market-moving news in JSON format.

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
9. Market analyst commentary and price targets

Return ONLY valid JSON. Include at least 3-5 most recent news items for each stock."""

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
