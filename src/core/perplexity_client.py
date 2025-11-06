"""
Enhanced Perplexity AI Client for comprehensive stock analysis data fetching.

Features:
- Batch processing with intelligent rate limiting
- API key rotation and failover
- Circuit breaker pattern for API failures
- Enhanced query templates for fundamentals, earnings, and news
- Structured data parsing with fallback strategies
- Concurrent API calls within limits
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx
from loguru import logger
from openai import OpenAI
from pydantic import BaseModel, Field


class QueryType(Enum):
    """Types of queries supported by the client."""

    NEWS_SENTIMENT = "news_sentiment"
    FUNDAMENTALS = "fundamentals"
    EARNINGS_CALENDAR = "earnings_calendar"
    COMPREHENSIVE = "comprehensive"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker pattern."""

    failure_threshold: int = 5  # Failures before opening circuit
    recovery_timeout: int = 60  # Seconds to wait before trying again
    expected_exception: Tuple = (Exception,)  # Exception types to count as failures


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    requests_per_minute: int = 50  # Perplexity API limit
    burst_limit: int = 10  # Allow bursts up to this many requests
    cooldown_seconds: int = 60  # Cooldown period when limit exceeded


@dataclass
class APIKeyMetrics:
    """Metrics for API key performance tracking."""

    key_index: int
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    last_used: Optional[datetime] = None
    consecutive_failures: int = 0
    rate_limit_hits: int = 0


class StockFundamentalData(BaseModel):
    """Structured fundamental data for a stock."""

    symbol: str
    market_cap: Optional[float] = None
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    debt_to_equity: Optional[float] = None
    roe: Optional[float] = None
    roa: Optional[float] = None
    revenue_growth: Optional[float] = None
    earnings_growth: Optional[float] = None
    dividend_yield: Optional[float] = None
    beta: Optional[float] = None
    fifty_two_week_high: Optional[float] = None
    fifty_two_week_low: Optional[float] = None
    avg_volume: Optional[int] = None
    sector: Optional[str] = None
    industry: Optional[str] = None


class EarningsData(BaseModel):
    """Structured earnings data."""

    symbol: str
    fiscal_period: str
    report_date: str
    eps_actual: Optional[float] = None
    revenue_actual: Optional[float] = None
    eps_estimated: Optional[float] = None
    revenue_estimated: Optional[float] = None
    surprise_pct: Optional[float] = None
    guidance: Optional[str] = None
    next_earnings_date: Optional[str] = None


class NewsSentimentData(BaseModel):
    """Structured news and sentiment data."""

    symbol: str
    title: str
    content: str
    source: str = "Perplexity AI"
    sentiment: str = "neutral"
    published_date: Optional[str] = None
    url: Optional[str] = None


class BatchResponse(BaseModel):
    """Response structure for batch queries."""

    fundamentals: List[StockFundamentalData] = Field(default_factory=list)
    earnings: List[EarningsData] = Field(default_factory=list)
    news: List[NewsSentimentData] = Field(default_factory=list)


class PerplexityClient:
    """
    Enhanced Perplexity AI client with advanced features.

    Features:
    - Batch processing with rate limiting
    - API key rotation and failover
    - Circuit breaker pattern
    - Enhanced query templates
    - Structured data parsing
    """

    def __init__(self, api_keys: List[str], config: Optional[Dict[str, Any]] = None):
        self.api_keys = api_keys
        self.key_metrics: Dict[int, APIKeyMetrics] = {}

        # Initialize key metrics
        for i, key in enumerate(api_keys):
            self.key_metrics[i] = APIKeyMetrics(key_index=i)

        # Configuration
        self.config = config or {}
        self.model = self.config.get("model", "sonar-pro")
        self.api_timeout = self.config.get("api_timeout_seconds", 45)
        self.max_tokens = self.config.get("max_tokens", 4000)
        self.search_recency = self.config.get("search_recency_filter", "week")
        self.max_search_results = self.config.get("max_search_results", 20)

        # Rate limiting
        rate_config = self.config.get("rate_limit", {})
        self.rate_limiter = RateLimitConfig(**rate_config)

        # Circuit breaker
        circuit_config = self.config.get("circuit_breaker", {})
        self.circuit_breaker = CircuitBreakerConfig(**circuit_config)
        self.circuit_state = CircuitBreakerState.CLOSED
        self.last_failure_time = None
        self.failure_count = 0

        # Request tracking
        self.request_times: List[datetime] = []
        self.current_key_index = 0

        # Query templates
        self.query_templates = self._load_query_templates()

    def _load_query_templates(self) -> Dict[QueryType, str]:
        """Load enhanced query templates for different data types."""
        return {
            QueryType.NEWS_SENTIMENT: """
For each of these stocks ({symbols}), provide recent news and sentiment analysis.

Focus on:
- Latest news from the past 24-48 hours
- Major announcements, earnings reports, analyst upgrades/downgrades
- Market-moving events or regulatory news
- Overall sentiment analysis (positive/negative/neutral)
- Impact assessment on stock price

Return structured data for each stock with news summary, sentiment, and key highlights.
""",
            QueryType.FUNDAMENTALS: """
For each of these stocks ({symbols}), provide comprehensive fundamental analysis data.

Extract and calculate:
- Market capitalization
- Price-to-earnings (P/E) ratio
- Price-to-book (P/B) ratio
- Debt-to-equity ratio
- Return on equity (ROE)
- Return on assets (ROA)
- Revenue growth rate (YoY)
- Earnings growth rate (YoY)
- Dividend yield
- Beta coefficient
- 52-week high and low prices
- Average daily volume
- Sector and industry classification

Use the most recent available data and provide numerical values where possible.
""",
            QueryType.EARNINGS_CALENDAR: """
For each of these stocks ({symbols}), provide earnings calendar and recent results.

Include:
- Most recent earnings report details (EPS, revenue, guidance)
- Next scheduled earnings date
- Fiscal period information
- Analyst estimates vs actual results
- Earnings surprise percentage
- Future guidance and outlook
- Key financial metrics from the report

Focus on the most recent quarter and upcoming earnings dates.
""",
            QueryType.COMPREHENSIVE: """
For each of these stocks ({symbols}), provide comprehensive analysis including fundamentals, earnings, and news.

Include:
1. Fundamental metrics (market cap, P/E, P/B, ROE, growth rates, etc.)
2. Recent earnings results and next earnings date
3. Latest news and sentiment analysis
4. Overall investment outlook

Provide structured data with all available information for each stock.
""",
        }

    async def fetch_batch_data(
        self,
        symbols: List[str],
        query_type: QueryType = QueryType.COMPREHENSIVE,
        batch_size: int = 5,
        max_concurrent: int = 2,
    ) -> BatchResponse:
        """
        Fetch comprehensive data for multiple symbols using batch processing.

        Args:
            symbols: List of stock symbols to analyze
            query_type: Type of data to fetch
            batch_size: Number of symbols per batch
            max_concurrent: Maximum concurrent API calls

        Returns:
            BatchResponse with structured data
        """
        if not symbols:
            return BatchResponse()

        # Check circuit breaker
        if not self._can_make_request():
            logger.warning("Circuit breaker is open, skipping request")
            return BatchResponse()

        # Split symbols into batches
        batches = [
            symbols[i : i + batch_size] for i in range(0, len(symbols), batch_size)
        ]

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)

        async def process_batch(batch_symbols: List[str]) -> BatchResponse:
            async with semaphore:
                return await self._fetch_single_batch(batch_symbols, query_type)

        # Process batches concurrently
        tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        combined_response = BatchResponse()

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Batch processing failed: {result}")
                continue

            if isinstance(result, BatchResponse):
                combined_response.fundamentals.extend(result.fundamentals)
                combined_response.earnings.extend(result.earnings)
                combined_response.news.extend(result.news)

        return combined_response

    async def _fetch_single_batch(
        self, symbols: List[str], query_type: QueryType
    ) -> BatchResponse:
        """Fetch data for a single batch of symbols."""
        try:
            # Get API key with rotation
            api_key = self._get_next_api_key()
            if not api_key:
                logger.error("No available API keys")
                return BatchResponse()

            # Apply rate limiting
            await self._apply_rate_limiting()

            # Create query
            symbols_str = ", ".join(symbols)
            template = self.query_templates[query_type]
            query = template.format(symbols=symbols_str)

            # Make API call
            client = OpenAI(
                api_key=api_key,
                base_url="https://api.perplexity.ai",
                http_client=httpx.Client(timeout=self.api_timeout),
            )

            # Define response schema based on query type
            schema = self._get_response_schema(query_type)

            completion = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": query}],
                max_tokens=self.max_tokens,
                response_format={
                    "type": "json_schema",
                    "json_schema": {"schema": schema.model_json_schema()},
                },
                web_search_options={
                    "search_recency_filter": self.search_recency,
                    "max_search_results": self.max_search_results,
                },
            )

            response_content = completion.choices[0].message.content

            # Update metrics
            key_index = self.api_keys.index(api_key)
            self.key_metrics[key_index].total_requests += 1
            self.key_metrics[key_index].successful_requests += 1
            self.key_metrics[key_index].last_used = datetime.now()
            self.key_metrics[key_index].consecutive_failures = 0

            # Reset circuit breaker on success
            if self.circuit_state == CircuitBreakerState.HALF_OPEN:
                self.circuit_state = CircuitBreakerState.CLOSED
                self.failure_count = 0

            # Parse response
            return self._parse_response(response_content, query_type, symbols)

        except Exception as e:
            error_str = str(e).lower()

            # Update failure metrics
            key_index = self.current_key_index
            self.key_metrics[key_index].failed_requests += 1
            self.key_metrics[key_index].consecutive_failures += 1

            # Handle rate limiting
            if "rate limit" in error_str or "quota" in error_str:
                self.key_metrics[key_index].rate_limit_hits += 1
                self._handle_rate_limit_exceeded()

            # Update circuit breaker
            self._handle_api_failure(e)

            logger.error(f"Batch API call failed for {symbols}: {e}")
            return BatchResponse()

    def _get_response_schema(self, query_type: QueryType) -> BaseModel:
        """Get the appropriate response schema for the query type."""
        if query_type == QueryType.FUNDAMENTALS:

            class FundamentalsResponse(BaseModel):
                fundamentals: List[StockFundamentalData]

            return FundamentalsResponse

        elif query_type == QueryType.EARNINGS_CALENDAR:

            class EarningsResponse(BaseModel):
                earnings: List[EarningsData]

            return EarningsResponse

        elif query_type == QueryType.NEWS_SENTIMENT:

            class NewsResponse(BaseModel):
                news: List[NewsSentimentData]

            return NewsResponse

        else:  # COMPREHENSIVE
            return BatchResponse

    def _parse_response(
        self, content: str, query_type: QueryType, symbols: List[str]
    ) -> BatchResponse:
        """Parse API response into structured data."""
        try:
            data = json.loads(content)

            if query_type == QueryType.FUNDAMENTALS:
                fundamentals = [
                    StockFundamentalData(**item)
                    for item in data.get("fundamentals", [])
                ]
                return BatchResponse(fundamentals=fundamentals)

            elif query_type == QueryType.EARNINGS_CALENDAR:
                earnings = [EarningsData(**item) for item in data.get("earnings", [])]
                return BatchResponse(earnings=earnings)

            elif query_type == QueryType.NEWS_SENTIMENT:
                news = [NewsSentimentData(**item) for item in data.get("news", [])]
                return BatchResponse(news=news)

            else:  # COMPREHENSIVE
                fundamentals = [
                    StockFundamentalData(**item)
                    for item in data.get("fundamentals", [])
                ]
                earnings = [EarningsData(**item) for item in data.get("earnings", [])]
                news = [NewsSentimentData(**item) for item in data.get("news", [])]
                return BatchResponse(
                    fundamentals=fundamentals, earnings=earnings, news=news
                )

        except Exception as e:
            logger.error(f"Failed to parse response: {e}")
            return BatchResponse()

    def _get_next_api_key(self) -> Optional[str]:
        """Get the next API key using round-robin rotation with health checking."""
        if not self.api_keys:
            return None

        # Find the healthiest key (lowest consecutive failures, recent success)
        best_key_index = None
        best_score = float("inf")

        for i, metrics in self.key_metrics.items():
            # Skip keys with too many consecutive failures
            if metrics.consecutive_failures >= 3:
                continue

            # Score based on consecutive failures and recency
            score = metrics.consecutive_failures * 10
            if metrics.last_used:
                hours_since_used = (
                    datetime.now() - metrics.last_used
                ).total_seconds() / 3600
                score += hours_since_used  # Prefer recently used keys

            if score < best_score:
                best_score = score
                best_key_index = i

        if best_key_index is not None:
            self.current_key_index = best_key_index
            return self.api_keys[best_key_index]

        # Fallback to round-robin if no healthy keys
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return key

    async def _apply_rate_limiting(self) -> None:
        """Apply rate limiting to avoid API quota exhaustion."""
        now = datetime.now()

        # Clean old request times
        cutoff = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > cutoff]

        # Check if we're over the limit
        if len(self.request_times) >= self.rate_limiter.requests_per_minute:
            # Calculate wait time
            oldest_request = min(self.request_times)
            wait_seconds = (oldest_request + timedelta(minutes=1) - now).total_seconds()

            if wait_seconds > 0:
                logger.info(f"Rate limit reached, waiting {wait_seconds:.1f} seconds")
                await asyncio.sleep(wait_seconds)

        # Allow burst requests
        elif len(self.request_times) >= self.rate_limiter.burst_limit:
            await asyncio.sleep(1)  # Small delay for burst control

        self.request_times.append(now)

    def _handle_rate_limit_exceeded(self) -> None:
        """Handle rate limit exceeded by backing off."""
        logger.warning("Rate limit exceeded, increasing cooldown")
        # Could implement exponential backoff here
        pass

    def _can_make_request(self) -> bool:
        """Check if circuit breaker allows making requests."""
        if self.circuit_state == CircuitBreakerState.CLOSED:
            return True

        if self.circuit_state == CircuitBreakerState.OPEN:
            if self.last_failure_time:
                elapsed = (datetime.now() - self.last_failure_time).total_seconds()
                if elapsed >= self.circuit_breaker.recovery_timeout:
                    self.circuit_state = CircuitBreakerState.HALF_OPEN
                    logger.info("Circuit breaker moving to half-open state")
                    return True
            return False

        # Half-open: allow one request to test
        return True

    def _handle_api_failure(self, exception: Exception) -> None:
        """Handle API failure and update circuit breaker state."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.circuit_breaker.failure_threshold:
            if self.circuit_state == CircuitBreakerState.CLOSED:
                self.circuit_state = CircuitBreakerState.OPEN
                logger.warning(
                    f"Circuit breaker opened after {self.failure_count} failures"
                )

    def get_health_status(self) -> Dict[str, Any]:
        """Get client health status and metrics."""
        return {
            "circuit_breaker_state": self.circuit_state.value,
            "failure_count": self.failure_count,
            "last_failure_time": (
                self.last_failure_time.isoformat() if self.last_failure_time else None
            ),
            "api_keys_status": {
                f"key_{i}": {
                    "total_requests": metrics.total_requests,
                    "success_rate": metrics.successful_requests
                    / max(metrics.total_requests, 1),
                    "consecutive_failures": metrics.consecutive_failures,
                    "rate_limit_hits": metrics.rate_limit_hits,
                    "last_used": (
                        metrics.last_used.isoformat() if metrics.last_used else None
                    ),
                }
                for i, metrics in self.key_metrics.items()
            },
            "rate_limiting": {
                "requests_in_last_minute": len(self.request_times),
                "limit_per_minute": self.rate_limiter.requests_per_minute,
            },
        }
