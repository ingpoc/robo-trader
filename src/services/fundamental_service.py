"""
Fundamental Analysis Service for Robo Trader

Handles fetching, processing, and storing fundamental data using Perplexity AI.
Provides comprehensive fundamental analysis capabilities with batch processing.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict

from loguru import logger
from ..config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import FundamentalAnalysis
from ..core.perplexity_client import (
    PerplexityClient,
    QueryType,
    StockFundamentalData,
    EarningsData,
    NewsSentimentData,
    BatchResponse
)


class FundamentalService:
    """
    Service for fundamental analysis data fetching and processing.

    Features:
    - Batch processing of fundamental data
    - Earnings calendar management
    - Structured data parsing and validation
    - Integration with state management
    - Performance optimization with concurrent requests
    """

    def __init__(self, config: Config, state_manager: DatabaseStateManager):
        self.config = config
        self.state_manager = state_manager

        # Initialize Perplexity client with API keys
        perplexity_keys = config.integration.perplexity_api_keys
        if not perplexity_keys:
            logger.warning("No Perplexity API keys configured - fundamental service will be limited")

        client_config = {
            'model': getattr(config, 'news_monitoring', {}).get('perplexity_model', 'sonar-pro'),
            'api_timeout_seconds': getattr(config, 'news_monitoring', {}).get('api_timeout_seconds', 45),
            'max_tokens': getattr(config, 'news_monitoring', {}).get('max_tokens', 4000),
            'search_recency_filter': getattr(config, 'news_monitoring', {}).get('search_recency_filter', 'week'),
            'max_search_results': getattr(config, 'news_monitoring', {}).get('max_search_results', 20),
            'rate_limit': getattr(config, 'news_monitoring', {}).get('rate_limit', {}),
            'circuit_breaker': getattr(config, 'news_monitoring', {}).get('circuit_breaker', {})
        }

        self.perplexity_client = PerplexityClient(perplexity_keys, client_config)

        # Configuration
        self.batch_size = getattr(config, 'fundamental_monitoring', {}).get('batch_size', 3)
        self.max_concurrent_batches = getattr(config, 'fundamental_monitoring', {}).get('max_concurrent_batches', 2)
        self.update_frequency_days = getattr(config, 'fundamental_monitoring', {}).get('update_frequency_days', 7)

    async def fetch_fundamentals_batch(
        self,
        symbols: List[str],
        force_refresh: bool = False
    ) -> Dict[str, FundamentalAnalysis]:
        """
        Fetch fundamental data for multiple symbols using batch processing.

        Args:
            symbols: List of stock symbols to analyze
            force_refresh: Force refresh even if data is recent

        Returns:
            Dictionary mapping symbols to FundamentalAnalysis objects
        """
        if not symbols:
            return {}

        logger.info(f"Fetching fundamental data for {len(symbols)} symbols (batch_size={self.batch_size})")

        # Filter symbols that need updating
        symbols_to_update = await self._filter_symbols_needing_update(symbols, force_refresh)

        if not symbols_to_update:
            logger.info("All symbols have recent fundamental data")
            # Return existing data
            existing_data = {}
            for symbol in symbols:
                analyses = await self.state_manager.get_fundamental_analysis(symbol, 1)
                if analyses:
                    existing_data[symbol] = analyses[0]
            return existing_data

        # Split into batches for processing
        batches = [symbols_to_update[i:i + self.batch_size]
                  for i in range(0, len(symbols_to_update), self.batch_size)]

        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def process_batch(batch_symbols: List[str]) -> BatchResponse:
            async with semaphore:
                return await self.perplexity_client.fetch_batch_data(
                    batch_symbols,
                    QueryType.FUNDAMENTALS
                )

        # Process batches concurrently
        logger.info(f"Processing {len(batches)} batches with max {self.max_concurrent_batches} concurrent")
        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process results and save to database
        saved_analyses = {}

        for i, result in enumerate(batch_results):
            batch_symbols = batches[i]

            if isinstance(result, Exception):
                logger.error(f"Batch {i} failed: {result}")
                continue

            if isinstance(result, BatchResponse):
                batch_saved = await self._process_fundamental_batch_result(result, batch_symbols)
                saved_analyses.update(batch_saved)

        # Return combined results (existing + newly fetched)
        all_results = {}
        for symbol in symbols:
            if symbol in saved_analyses:
                all_results[symbol] = saved_analyses[symbol]
            else:
                # Get existing data for symbols not updated
                analyses = await self.state_manager.get_fundamental_analysis(symbol, 1)
                if analyses:
                    all_results[symbol] = analyses[0]

        logger.info(f"Fundamental data fetch completed: {len(saved_analyses)} updated, {len(all_results)} total")
        return all_results

    async def fetch_earnings_calendar(
        self,
        symbols: List[str],
        include_historical: bool = False
    ) -> Dict[str, List[EarningsData]]:
        """
        Fetch earnings calendar data for multiple symbols.

        Args:
            symbols: List of stock symbols
            include_historical: Include historical earnings data

        Returns:
            Dictionary mapping symbols to lists of earnings data
        """
        if not symbols:
            return {}

        logger.info(f"Fetching earnings calendar for {len(symbols)} symbols")

        # Split into batches
        batches = [symbols[i:i + self.batch_size]
                  for i in range(0, len(symbols), self.batch_size)]

        # Process batches concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def process_batch(batch_symbols: List[str]) -> BatchResponse:
            async with semaphore:
                return await self.perplexity_client.fetch_batch_data(
                    batch_symbols,
                    QueryType.EARNINGS_CALENDAR
                )

        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process results
        earnings_data = {}

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Earnings batch failed: {result}")
                continue

            if isinstance(result, BatchResponse):
                for earnings_item in result.earnings:
                    symbol = earnings_item.symbol
                    if symbol not in earnings_data:
                        earnings_data[symbol] = []
                    earnings_data[symbol].append(earnings_item)

                    # Save to database
                    await self._save_earnings_data(earnings_item)

        logger.info(f"Earnings calendar fetch completed: {sum(len(v) for v in earnings_data.values())} reports saved")
        return earnings_data

    async def fetch_comprehensive_data(
        self,
        symbols: List[str],
        force_refresh: bool = False
    ) -> Dict[str, Dict[str, Any]]:
        """
        Fetch comprehensive data (fundamentals + earnings + news) for symbols.

        Args:
            symbols: List of stock symbols
            force_refresh: Force refresh of all data

        Returns:
            Dictionary with comprehensive data per symbol
        """
        if not symbols:
            return {}

        logger.info(f"Fetching comprehensive data for {len(symbols)} symbols")

        # Split into batches
        batches = [symbols[i:i + self.batch_size]
                  for i in range(0, len(symbols), self.batch_size)]

        # Process batches concurrently
        semaphore = asyncio.Semaphore(self.max_concurrent_batches)

        async def process_batch(batch_symbols: List[str]) -> BatchResponse:
            async with semaphore:
                return await self.perplexity_client.fetch_batch_data(
                    batch_symbols,
                    QueryType.COMPREHENSIVE
                )

        batch_tasks = [process_batch(batch) for batch in batches]
        batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

        # Process comprehensive results
        comprehensive_data = {}

        for result in batch_results:
            if isinstance(result, Exception):
                logger.error(f"Comprehensive batch failed: {result}")
                continue

            if isinstance(result, BatchResponse):
                batch_comprehensive = await self._process_comprehensive_batch_result(result)
                comprehensive_data.update(batch_comprehensive)

        logger.info(f"Comprehensive data fetch completed for {len(comprehensive_data)} symbols")
        return comprehensive_data

    async def _filter_symbols_needing_update(
        self,
        symbols: List[str],
        force_refresh: bool = False
    ) -> List[str]:
        """Filter symbols that need fundamental data updates."""
        if force_refresh:
            return symbols

        symbols_needing_update = []

        for symbol in symbols:
            # Check if we have recent fundamental data
            analyses = await self.state_manager.get_fundamental_analysis(symbol, 1)

            needs_update = True
            if analyses:
                latest_analysis = analyses[0]
                analysis_date = datetime.fromisoformat(latest_analysis.analysis_date)
                days_since_update = (datetime.now(timezone.utc) - analysis_date).days

                if days_since_update < self.update_frequency_days:
                    needs_update = False

            if needs_update:
                symbols_needing_update.append(symbol)

        return symbols_needing_update

    async def _process_fundamental_batch_result(
        self,
        batch_result: BatchResponse,
        batch_symbols: List[str]
    ) -> Dict[str, FundamentalAnalysis]:
        """Process fundamental data batch result and save to database."""
        saved_analyses = {}

        for fundamental_data in batch_result.fundamentals:
            symbol = fundamental_data.symbol.upper()

            if symbol not in batch_symbols:
                continue

            # Convert to FundamentalAnalysis model
            analysis = self._convert_to_fundamental_analysis(fundamental_data)

            # Save to database
            try:
                analysis_id = await self.state_manager.save_fundamental_analysis(analysis)
                saved_analyses[symbol] = analysis
                logger.debug(f"Saved fundamental analysis for {symbol} (ID: {analysis_id})")
            except Exception as e:
                logger.error(f"Failed to save fundamental analysis for {symbol}: {e}")

        return saved_analyses

    async def _process_comprehensive_batch_result(
        self,
        batch_result: BatchResponse
    ) -> Dict[str, Dict[str, Any]]:
        """Process comprehensive batch result with all data types."""
        comprehensive_data = {}

        # Process fundamentals
        for fundamental_data in batch_result.fundamentals:
            symbol = fundamental_data.symbol.upper()
            if symbol not in comprehensive_data:
                comprehensive_data[symbol] = {}

            analysis = self._convert_to_fundamental_analysis(fundamental_data)
            comprehensive_data[symbol]['fundamentals'] = analysis

            # Save to database
            try:
                await self.state_manager.save_fundamental_analysis(analysis)
            except Exception as e:
                logger.error(f"Failed to save fundamental analysis for {symbol}: {e}")

        # Process earnings
        for earnings_data in batch_result.earnings:
            symbol = earnings_data.symbol.upper()
            if symbol not in comprehensive_data:
                comprehensive_data[symbol] = {}

            if 'earnings' not in comprehensive_data[symbol]:
                comprehensive_data[symbol]['earnings'] = []

            comprehensive_data[symbol]['earnings'].append(earnings_data)

            # Save to database
            await self._save_earnings_data(earnings_data)

        # Process news
        for news_data in batch_result.news:
            symbol = news_data.symbol.upper()
            if symbol not in comprehensive_data:
                comprehensive_data[symbol] = {}

            if 'news' not in comprehensive_data[symbol]:
                comprehensive_data[symbol]['news'] = []

            comprehensive_data[symbol]['news'].append(news_data)

            # Save to database
            await self._save_news_data(news_data)

        return comprehensive_data

    def _convert_to_fundamental_analysis(
        self,
        fundamental_data: StockFundamentalData
    ) -> FundamentalAnalysis:
        """Convert StockFundamentalData to FundamentalAnalysis model."""
        # Calculate overall score based on available metrics
        overall_score = self._calculate_fundamental_score(fundamental_data)

        # Generate recommendation based on score
        recommendation = self._generate_recommendation(overall_score, fundamental_data)

        analysis_data = {
            'beta': fundamental_data.beta,
            'fifty_two_week_high': fundamental_data.fifty_two_week_high,
            'fifty_two_week_low': fundamental_data.fifty_two_week_low,
            'avg_volume': fundamental_data.avg_volume,
            'sector': fundamental_data.sector,
            'industry': fundamental_data.industry,
            'revenue_growth': fundamental_data.revenue_growth,
            'earnings_growth': fundamental_data.earnings_growth
        }

        return FundamentalAnalysis(
            symbol=fundamental_data.symbol.upper(),
            analysis_date=datetime.now(timezone.utc).isoformat(),
            pe_ratio=fundamental_data.pe_ratio,
            pb_ratio=fundamental_data.pb_ratio,
            roe=fundamental_data.roe,
            roa=fundamental_data.roa,
            debt_to_equity=fundamental_data.debt_to_equity,
            dividend_yield=fundamental_data.dividend_yield,
            market_cap=fundamental_data.market_cap,
            overall_score=overall_score,
            recommendation=recommendation,
            analysis_data=analysis_data
        )

    def _calculate_fundamental_score(self, data: StockFundamentalData) -> Optional[float]:
        """Calculate overall fundamental score (0-100)."""
        score_components = []
        weights = []

        # P/E Ratio (lower is better, target < 20)
        if data.pe_ratio is not None:
            pe_score = max(0, min(100, 100 - (data.pe_ratio - 10) * 5))
            score_components.append(pe_score)
            weights.append(0.25)

        # P/B Ratio (lower is better, target < 3)
        if data.pb_ratio is not None:
            pb_score = max(0, min(100, 100 - (data.pb_ratio - 1) * 20))
            score_components.append(pb_score)
            weights.append(0.20)

        # ROE (higher is better, target > 15%)
        if data.roe is not None:
            roe_score = max(0, min(100, data.roe * 2))
            score_components.append(roe_score)
            weights.append(0.25)

        # Debt-to-Equity (lower is better, target < 1.0)
        if data.debt_to_equity is not None:
            de_score = max(0, min(100, 100 - data.debt_to_equity * 50))
            score_components.append(de_score)
            weights.append(0.15)

        # Dividend Yield (moderate is better, target 2-4%)
        if data.dividend_yield is not None:
            if data.dividend_yield < 2:
                dy_score = data.dividend_yield * 25  # 0-50 for 0-2%
            elif data.dividend_yield <= 4:
                dy_score = 50 + (data.dividend_yield - 2) * 25  # 50-100 for 2-4%
            else:
                dy_score = max(0, 100 - (data.dividend_yield - 4) * 50)  # Decrease after 4%
            score_components.append(dy_score)
            weights.append(0.15)

        if not score_components:
            return None

        # Weighted average
        total_weight = sum(weights)
        if total_weight == 0:
            return None

        weighted_score = sum(s * w for s, w in zip(score_components, weights)) / total_weight
        return round(weighted_score, 2)

    def _generate_recommendation(self, score: Optional[float], data: StockFundamentalData) -> Optional[str]:
        """Generate investment recommendation based on score."""
        if score is None:
            return None

        if score >= 80:
            return "STRONG_BUY"
        elif score >= 65:
            return "BUY"
        elif score >= 45:
            return "HOLD"
        elif score >= 30:
            return "SELL"
        else:
            return "STRONG_SELL"

    async def _save_earnings_data(self, earnings_data: EarningsData) -> None:
        """Save earnings data to database."""
        try:
            await self.state_manager.save_earnings_report(
                symbol=earnings_data.symbol.upper(),
                fiscal_period=earnings_data.fiscal_period,
                report_date=earnings_data.report_date,
                eps_actual=earnings_data.eps_actual,
                revenue_actual=earnings_data.revenue_actual,
                eps_estimated=earnings_data.eps_estimated,
                revenue_estimated=earnings_data.revenue_estimated,
                guidance=earnings_data.guidance,
                next_earnings_date=earnings_data.next_earnings_date
            )
        except Exception as e:
            logger.error(f"Failed to save earnings data for {earnings_data.symbol}: {e}")

    async def _save_news_data(self, news_data: NewsSentimentData) -> None:
        """Save news data to database."""
        try:
            await self.state_manager.save_news_item(
                symbol=news_data.symbol.upper(),
                title=news_data.title,
                summary=news_data.content,  # Use content as summary
                content=news_data.content,
                source=news_data.source,
                sentiment=news_data.sentiment,
                published_at=news_data.published_date,
                citations=None
            )
        except Exception as e:
            logger.error(f"Failed to save news data for {news_data.symbol}: {e}")

    def get_client_health_status(self) -> Dict[str, Any]:
        """Get health status of the Perplexity client."""
        return self.perplexity_client.get_health_status()

    async def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """Clean up old fundamental analysis data."""
        # This would be implemented in the state manager
        # For now, return 0 as placeholder
        logger.info(f"Fundamental data cleanup: keeping last {days_to_keep} days")
        return 0