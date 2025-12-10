"""Monthly Portfolio Analysis Coordinator.

Orchestrates monthly analysis of user's real portfolio stocks.
Fetches data via Perplexity API and generates KEEP/SELL recommendations.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from loguru import logger

from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import Event, EventType
from src.core.database_state.portfolio_monthly_analysis_state import PortfolioMonthlyAnalysisState
from src.core.database_state.configuration_state import ConfigurationState
from src.services.kite_portfolio_service import KitePortfolioService
from src.core.perplexity_client import PerplexityClient, QueryType
from src.models.scheduler import QueueName, TaskType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

# Import ClaudeSDKClient lazily to avoid circular imports
def get_claude_sdk_client():
    from claude_agent_sdk import ClaudeSDKClient
    return ClaudeSDKClient

logger = logging.getLogger(__name__)


class MonthlyPortfolioAnalysisCoordinator(BaseCoordinator):
    """Coordinates monthly portfolio analysis using Perplexity and Claude."""

    def __init__(
        self,
        config: Any,
        portfolio_analysis_state: PortfolioMonthlyAnalysisState,
        config_state: ConfigurationState,
        task_service: Any,
        kite_portfolio_service: Optional[KitePortfolioService] = None,
        perplexity_client: Optional[PerplexityClient] = None,
        claude_sdk_client: Optional[ClaudeSDKClient] = None
    ):
        """Initialize monthly portfolio analysis coordinator."""
        super().__init__(config, "MonthlyPortfolioAnalysisCoordinator")

        self.portfolio_analysis_state = portfolio_analysis_state
        self.config_state = config_state
        self.task_service = task_service
        self.kite_portfolio_service = kite_portfolio_service
        self.perplexity_client = perplexity_client
        self.claude_sdk_client = claude_sdk_client

        # Initialization tracking
        self._initialized = False
        self._initialization_complete = False
        self._initialization_error: Optional[Exception] = None

        # Analysis state
        self._analysis_lock = asyncio.Lock()
        self._current_analysis_id: Optional[str] = None

        # Configuration
        self._max_stocks_per_batch = 3  # For Claude analysis
        self._analysis_timeout = 300  # 5 minutes per stock

    async def initialize(self) -> None:
        """Initialize the monthly analysis coordinator."""
        try:
            if self._initialized:
                return

            self._initialized = True
            self._log_init_step("Starting Monthly Portfolio Analysis Coordinator initialization")

            # Initialize Perplexity client if not provided
            if not self.perplexity_client:
                self._log_init_step("Initializing Perplexity client")
                self.perplexity_client = PerplexityClient()
                await self.perplexity_client.initialize()
                self._log_init_step("Perplexity client initialized")

            # Initialize Claude SDK client if not provided
            if not self.claude_sdk_client:
                self._log_init_step("Initializing Claude SDK client")
                self.claude_sdk_client = get_claude_sdk_client()()
                self._log_init_step("Claude SDK client initialized")

            self._initialization_complete = True
            logger.info("Monthly Portfolio Analysis Coordinator initialized successfully")

        except Exception as e:
            self._initialized = False
            self._initialization_error = e
            self._log_init_step("Monthly Portfolio Analysis Coordinator initialization", success=False, error=e)
            raise RuntimeError(f"Monthly Portfolio Analysis Coordinator initialization failed: {e}") from e

    def _log_init_step(self, step: str, success: bool = True, error: Optional[Exception] = None) -> None:
        """Log initialization step."""
        if success:
            logger.info(f"  ✓ {step}")
        else:
            logger.error(f"  ✗ {step}: {error}")

    async def trigger_monthly_analysis(
        self,
        analysis_date: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Trigger monthly portfolio analysis.

        Args:
            analysis_date: Date for analysis (YYYY-MM-DD), defaults to today
            force: Force analysis even if already done for the month

        Returns:
            Analysis results
        """
        if not self._initialization_complete:
            raise RuntimeError("Coordinator not initialized")

        if not analysis_date:
            analysis_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        analysis_month = analysis_date[:7]  # YYYY-MM

        # Check if analysis already done for this month
        if not force:
            existing_summary = await self.portfolio_analysis_state.get_monthly_summary(analysis_month)
            if existing_summary:
                logger.info(f"Analysis already completed for month {analysis_month}")
                return {
                    "status": "already_completed",
                    "month": analysis_month,
                    "summary": existing_summary[0]
                }

        async with self._analysis_lock:
            try:
                # Generate analysis ID
                import uuid
                self._current_analysis_id = f"monthly_analysis_{analysis_month}_{uuid.uuid4().hex[:8]}"

                logger.info(f"Starting monthly portfolio analysis for {analysis_month}")
                start_time = datetime.now(timezone.utc)

                # Step 1: Fetch real portfolio from Kite
                portfolio_data = await self._fetch_real_portfolio()
                if not portfolio_data or not portfolio_data.get("holdings"):
                    logger.warning("No portfolio holdings found for analysis")
                    return {
                        "status": "no_holdings",
                        "message": "No portfolio holdings found",
                        "analysis_id": self._current_analysis_id
                    }

                holdings = portfolio_data["holdings"]
                symbols = [h["tradingsymbol"] for h in holdings]
                logger.info(f"Found {len(symbols)} stocks in portfolio for analysis")

                # Step 2: Analyze each stock
                analysis_results = []
                perplexity_calls = 0
                claude_tokens = 0

                for symbol in symbols:
                    try:
                        # Get stock data from Perplexity
                        stock_data = await self._fetch_stock_data(symbol)
                        perplexity_calls += 1

                        # Analyze with Claude
                        analysis = await self._analyze_stock_with_claude(symbol, stock_data)
                        claude_tokens += analysis.get("tokens_used", 0)

                        # Store analysis
                        await self.portfolio_analysis_state.store_analysis(
                            analysis_date=analysis_date,
                            symbol=symbol,
                            company_name=stock_data.get("company_name"),
                            sector=stock_data.get("sector"),
                            industry=stock_data.get("industry"),
                            fundamentals=stock_data.get("fundamentals"),
                            recent_earnings=stock_data.get("earnings"),
                            news_sentiment=stock_data.get("news_sentiment"),
                            industry_trends=stock_data.get("industry_trends"),
                            recommendation=analysis.get("recommendation", "KEEP"),
                            reasoning=analysis.get("reasoning", ""),
                            confidence_score=analysis.get("confidence_score", 0.0),
                            analysis_sources=stock_data.get("sources", []),
                            price_at_analysis=stock_data.get("current_price")
                        )

                        analysis_results.append({
                            "symbol": symbol,
                            "recommendation": analysis.get("recommendation"),
                            "confidence": analysis.get("confidence_score"),
                            "reasoning_summary": analysis.get("reasoning", "")[:200] + "..."
                        })

                    except Exception as e:
                        logger.error(f"Failed to analyze {symbol}: {e}")
                        analysis_results.append({
                            "symbol": symbol,
                            "error": str(e)
                        })

                # Step 3: Calculate summary statistics
                keep_count = sum(1 for r in analysis_results if r.get("recommendation") == "KEEP")
                sell_count = sum(1 for r in analysis_results if r.get("recommendation") == "SELL")

                # Calculate portfolio value
                portfolio_value = sum(
                    h.get("quantity", 0) * h.get("last_price", 0)
                    for h in holdings
                )

                # Step 4: Store monthly summary
                end_time = datetime.now(timezone.utc)
                duration = (end_time - start_time).total_seconds()

                await self.portfolio_analysis_state.store_monthly_summary(
                    analysis_month=analysis_month,
                    total_stocks=len(symbols),
                    keep_count=keep_count,
                    sell_count=sell_count,
                    portfolio_value=portfolio_value,
                    analysis_duration=duration,
                    perplexity_calls=perplexity_calls,
                    claude_tokens=claude_tokens
                )

                # Emit completion event
                await self.event_bus.publish(Event(
                    type=EventType.MONTHLY_ANALYSIS_COMPLETE,
                    data={
                        "analysis_id": self._current_analysis_id,
                        "month": analysis_month,
                        "total_stocks": len(symbols),
                        "keep_count": keep_count,
                        "sell_count": sell_count,
                        "duration": duration
                    }
                ))

                logger.info(f"Monthly analysis completed for {analysis_month}: {keep_count} KEEP, {sell_count} SELL")

                return {
                    "status": "completed",
                    "analysis_id": self._current_analysis_id,
                    "month": analysis_month,
                    "summary": {
                        "total_stocks": len(symbols),
                        "keep_recommendations": keep_count,
                        "sell_recommendations": sell_count,
                        "portfolio_value": portfolio_value,
                        "duration_seconds": duration,
                        "perplexity_calls": perplexity_calls,
                        "claude_tokens": claude_tokens
                    },
                    "results": analysis_results
                }

            except Exception as e:
                logger.error(f"Monthly analysis failed: {e}")
                raise TradingError(
                    f"Monthly portfolio analysis failed: {e}",
                    category=ErrorCategory.ANALYSIS,
                    severity=ErrorSeverity.HIGH
                ) from e
            finally:
                self._current_analysis_id = None

    async def _fetch_real_portfolio(self) -> Optional[Dict[str, Any]]:
        """Fetch real portfolio from Kite."""
        if not self.kite_portfolio_service:
            logger.warning("Kite portfolio service not configured")
            return None

        try:
            portfolio = await self.kite_portfolio_service.get_portfolio_holdings_and_positions()
            return portfolio
        except Exception as e:
            logger.error(f"Failed to fetch portfolio from Kite: {e}")
            return None

    async def _fetch_stock_data(self, symbol: str) -> Dict[str, Any]:
        """Fetch comprehensive stock data using Perplexity API."""
        try:
            # Fetch fundamentals
            fundamentals_query = f"""
            Get comprehensive fundamental analysis for {symbol} stock including:
            - P/E ratio, P/B ratio, ROE, debt-to-equity ratio
            - Current ratio, profit margins
            - Revenue growth, earnings growth, dividend yield
            - Market cap, sector, industry
            """

            fundamentals_result = await self.perplexity_client.query(
                query=fundamentals_query,
                query_type=QueryType.FUNDAMENTALS
            )

            # Fetch recent earnings
            earnings_query = f"""
            Get recent earnings data for {symbol} including:
            - Latest quarterly results
            - EPS and revenue figures
            - Year-over-year growth
            - Management commentary
            """

            earnings_result = await self.perplexity_client.query(
                query=earnings_query,
                query_type=QueryType.EARNINGS_CALENDAR
            )

            # Fetch news sentiment
            news_query = f"""
            Get recent news and sentiment analysis for {symbol} including:
            - Latest news headlines and impact
            - Market sentiment
            - Analyst recommendations
            - Recent price movements
            """

            news_result = await self.perplexity_client.query(
                query=news_query,
                query_type=QueryType.NEWS_SENTIMENT
            )

            # Combine all data
            return {
                "symbol": symbol,
                "fundamentals": fundamentals_result.get("structured_data", {}),
                "earnings": earnings_result.get("structured_data", {}),
                "news_sentiment": news_result.get("structured_data", {}),
                "sources": fundamentals_result.get("sources", []) +
                          earnings_result.get("sources", []) +
                          news_result.get("sources", [])
            }

        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            raise

    async def _analyze_stock_with_claude(self, symbol: str, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze stock using Claude SDK and provide recommendation."""
        try:
            # Build analysis prompt
            prompt = self._build_analysis_prompt(symbol, stock_data)

            # Query Claude with timeout
            response = await query_with_timeout(
                client=self.claude_sdk_client,
                prompt=prompt,
                timeout=self._analysis_timeout
            )

            # Parse response
            return self._parse_claude_response(response, symbol)

        except Exception as e:
            logger.error(f"Failed to analyze {symbol} with Claude: {e}")
            raise

    def _build_analysis_prompt(self, symbol: str, stock_data: Dict[str, Any]) -> str:
        """Build comprehensive analysis prompt for Claude."""
        fundamentals = stock_data.get("fundamentals", {})
        earnings = stock_data.get("earnings", {})
        news = stock_data.get("news_sentiment", {})

        prompt = f"""
As an expert investment analyst, please analyze {symbol} stock and provide a clear KEEP or SELL recommendation.

FUNDAMENTAL DATA:
{json.dumps(fundamentals, indent=2)}

RECENT EARNINGS:
{json.dumps(earnings, indent=2)}

NEWS & SENTIMENT:
{json.dumps(news, indent=2)}

ANALYSIS REQUIREMENTS:
1. Evaluate the company's financial health based on fundamentals
2. Assess recent earnings performance and trends
3. Consider market sentiment and news impact
4. Analyze industry trends and competitive position
5. Provide a clear recommendation: KEEP or SELL

RESPONSE FORMAT (JSON):
{{
    "recommendation": "KEEP|SELL",
    "reasoning": "Detailed explanation of your analysis and decision",
    "confidence_score": 0.0-1.0,
    "key_factors": ["factor1", "factor2", "factor3"],
    "risks": ["risk1", "risk2"],
    "time_horizon": "short|medium|long"
}}

Focus on providing actionable investment advice based on comprehensive analysis.
"""
        return prompt

    def _parse_claude_response(self, response: str, symbol: str) -> Dict[str, Any]:
        """Parse Claude's response and extract recommendation."""
        try:
            # Try to parse JSON response
            if response.strip().startswith("{"):
                return json.loads(response)
            else:
                # Extract JSON from response
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end != -1:
                    json_str = response[start:end]
                    return json.loads(json_str)

            # Fallback if no JSON found
            logger.warning(f"Could not parse JSON from Claude response for {symbol}")
            return {
                "recommendation": "KEEP",
                "reasoning": response[:500],
                "confidence_score": 0.5,
                "key_factors": [],
                "risks": ["Unable to parse structured response"],
                "time_horizon": "medium"
            }

        except Exception as e:
            logger.error(f"Failed to parse Claude response for {symbol}: {e}")
            return {
                "recommendation": "KEEP",
                "reasoning": f"Error parsing response: {str(e)}",
                "confidence_score": 0.0,
                "key_factors": [],
                "risks": ["Response parsing error"],
                "time_horizon": "medium"
            }

    async def get_analysis_history(
        self,
        symbol: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get analysis history."""
        try:
            analyses = await self.portfolio_analysis_state.get_analysis(
                symbol=symbol,
                limit=limit
            )

            # Filter by date range if provided
            if start_date or end_date:
                filtered = []
                for analysis in analyses:
                    analysis_date = analysis.get("analysis_date")
                    if start_date and analysis_date < start_date:
                        continue
                    if end_date and analysis_date > end_date:
                        continue
                    filtered.append(analysis)
                analyses = filtered

            return analyses

        except Exception as e:
            logger.error(f"Failed to get analysis history: {e}")
            return []

    async def get_monthly_summaries(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly analysis summaries."""
        try:
            return await self.portfolio_analysis_state.get_monthly_summary(limit=months)
        except Exception as e:
            logger.error(f"Failed to get monthly summaries: {e}")
            return []

    async def get_analysis_statistics(
        self,
        months: int = 12
    ) -> Dict[str, Any]:
        """Get analysis statistics for the last N months."""
        try:
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            start_date = datetime.now(timezone.utc).replace(day=1).strftime("%Y-%m-%d")

            # Go back N months
            for _ in range(months - 1):
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                if dt.month == 1:
                    dt = dt.replace(year=dt.year - 1, month=12)
                else:
                    dt = dt.replace(month=dt.month - 1)
                start_date = dt.strftime("%Y-%m-%d")

            return await self.portfolio_analysis_state.get_analysis_statistics(
                start_date=start_date,
                end_date=end_date
            )

        except Exception as e:
            logger.error(f"Failed to get analysis statistics: {e}")
            return {}