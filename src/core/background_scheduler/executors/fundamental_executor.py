"""
Fundamental analysis task executor.

Orchestrates data flow: Perplexity API → Processor → Store
Handles task execution, error management, and event emission.
"""

from typing import Dict, List, Any, Optional
import uuid
from datetime import datetime, timezone

import aiosqlite
from loguru import logger

from ..clients.perplexity_client import PerplexityClient
from ..parsers.earnings import parse_comprehensive_earnings
from ..parsers.news import parse_categorized_news
from ..parsers.fundamental_analysis import parse_deep_fundamentals
from ..stores.fundamental_store import FundamentalStore
from ...event_bus import EventBus, Event, EventType


class FundamentalExecutor:
    """Executes fundamental analysis tasks with full error handling."""

    def __init__(
        self,
        perplexity_client: PerplexityClient,
        db_connection: aiosqlite.Connection,
        event_bus: EventBus,
        execution_tracker=None
    ):
        """Initialize executor with dependencies.

        Args:
            perplexity_client: Perplexity API client
            db_connection: Database connection
            event_bus: Event bus for broadcasting completion
            execution_tracker: Optional execution tracker for logging
        """
        self.perplexity_client = perplexity_client
        self.store = FundamentalStore(db_connection)
        self.event_bus = event_bus
        self.execution_tracker = execution_tracker

    async def execute_earnings_fundamentals(
        self, symbols: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch and store earnings fundamentals.

        Args:
            symbols: List of stock symbols
            metadata: Task metadata with context

        Returns:
            Status dict with success/failure information
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Executing earnings fundamentals for {symbols}")

            response = await self.perplexity_client.earnings.fetch_earnings_fundamentals(
                symbols
            )

            if not response:
                logger.warning("Empty response from Perplexity API")
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="earnings_fundamentals",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Empty API response",
                        execution_time=time.time() - start_time
                    )
                return {"status": "failed", "error": "Empty API response"}

            parsed_data = parse_comprehensive_earnings(response)

            if not parsed_data:
                logger.warning("Failed to parse earnings data")
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="earnings_fundamentals",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Parse failure",
                        execution_time=time.time() - start_time
                    )
                return {"status": "failed", "error": "Parse failure"}

            success = await self.store.store_earnings_fundamentals(symbols, parsed_data)

            execution_time = time.time() - start_time

            if success:
                # Record successful execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="earnings_fundamentals",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="completed",
                        execution_time=execution_time
                    )
                return {"status": "success", "symbols": symbols}
            else:
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="earnings_fundamentals",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Storage failure",
                        execution_time=execution_time
                    )
                return {"status": "failed", "error": "Storage failure"}

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing earnings fundamentals: {e}")
            # Record failed execution
            if self.execution_tracker:
                await self.execution_tracker.record_execution(
                    task_name="earnings_fundamentals",
                    task_id=metadata.get("task_id", ""),
                    execution_type=metadata.get("execution_type", "scheduled"),
                    user=metadata.get("user", "system"),
                    symbols=symbols,
                    status="failed",
                    error_message=str(e),
                    execution_time=execution_time
                )
            return {"status": "failed", "error": str(e)}

    async def execute_market_news_analysis(
        self, symbols: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch and store categorized market news.

        Args:
            symbols: List of stock symbols
            metadata: Task metadata with context

        Returns:
            Status dict with success/failure information
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Executing market news analysis for {symbols}")

            response = await self.perplexity_client.market.fetch_market_news(symbols)

            if not response:
                logger.warning("Empty response from Perplexity API")
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="news_processor",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Empty API response",
                        execution_time=time.time() - start_time
                    )
                return {"status": "failed", "error": "Empty API response"}

            parsed_data = parse_categorized_news(response)

            if not parsed_data:
                logger.warning("Failed to parse news data")
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="news_processor",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Parse failure",
                        execution_time=time.time() - start_time
                    )
                return {"status": "failed", "error": "Parse failure"}

            news_items = self._transform_news_items(parsed_data, symbols)

            success = await self.store.store_market_news(news_items)

            execution_time = time.time() - start_time

            if success:
                await self.event_bus.publish(
                    Event(
                        id=str(uuid.uuid4()),
                        type=EventType.MARKET_NEWS,  # TODO: Define proper MARKET_DATA_UPDATE event type
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source="FundamentalExecutor",
                        data={
                            "task_type": "market_news_analysis",
                            "symbols": symbols,
                            "status": "completed",
                        },
                    )
                )
                # Record successful execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="news_processor",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="completed",
                        execution_time=execution_time
                    )
                return {"status": "success", "symbols": symbols, "items": len(news_items)}
            else:
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="news_processor",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Storage failure",
                        execution_time=execution_time
                    )
                return {"status": "failed", "error": "Storage failure"}

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing market news analysis: {e}")
            # Record failed execution
            if self.execution_tracker:
                await self.execution_tracker.record_execution(
                    task_name="news_processor",
                    task_id=metadata.get("task_id", ""),
                    execution_type=metadata.get("execution_type", "scheduled"),
                    user=metadata.get("user", "system"),
                    symbols=symbols,
                    status="failed",
                    error_message=str(e),
                    execution_time=execution_time
                )
            return {"status": "failed", "error": str(e)}

    async def execute_deep_fundamental_analysis(
        self, symbols: List[str], metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Fetch and store deep fundamental analysis.

        Args:
            symbols: List of stock symbols
            metadata: Task metadata with context

        Returns:
            Status dict with success/failure information
        """
        import time
        start_time = time.time()

        try:
            logger.info(f"Executing deep fundamental analysis for {symbols}")

            response = await self.perplexity_client.earnings.fetch_deep_fundamentals(symbols)

            if not response:
                logger.warning("Empty response from Perplexity API")
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="fundamental_analyzer",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Empty API response",
                        execution_time=time.time() - start_time
                    )
                return {"status": "failed", "error": "Empty API response"}

            parsed_data = parse_deep_fundamentals(response)

            if not parsed_data:
                logger.warning("Failed to parse deep fundamentals")
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="fundamental_analyzer",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Parse failure",
                        execution_time=time.time() - start_time
                    )
                return {"status": "failed", "error": "Parse failure"}

            success = await self.store.store_deep_fundamentals(symbols, parsed_data)

            execution_time = time.time() - start_time

            if success:
                await self.event_bus.publish(
                    Event(
                        id=str(uuid.uuid4()),
                        type=EventType.MARKET_NEWS,  # TODO: Define proper MARKET_DATA_UPDATE event type
                        timestamp=datetime.now(timezone.utc).isoformat(),
                        source="FundamentalExecutor",
                        data={
                            "task_type": "deep_fundamental_analysis",
                            "symbols": symbols,
                            "status": "completed",
                        },
                    )
                )
                # Record successful execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="fundamental_analyzer",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="completed",
                        execution_time=execution_time
                    )
                return {"status": "success", "symbols": symbols}
            else:
                # Record failed execution
                if self.execution_tracker:
                    await self.execution_tracker.record_execution(
                        task_name="fundamental_analyzer",
                        task_id=metadata.get("task_id", ""),
                        execution_type=metadata.get("execution_type", "scheduled"),
                        user=metadata.get("user", "system"),
                        symbols=symbols,
                        status="failed",
                        error_message="Storage failure",
                        execution_time=execution_time
                    )
                return {"status": "failed", "error": "Storage failure"}

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error executing deep fundamental analysis: {e}")
            # Record failed execution
            if self.execution_tracker:
                await self.execution_tracker.record_execution(
                    task_name="fundamental_analyzer",
                    task_id=metadata.get("task_id", ""),
                    execution_type=metadata.get("execution_type", "scheduled"),
                    user=metadata.get("user", "system"),
                    symbols=symbols,
                    status="failed",
                    error_message=str(e),
                    execution_time=execution_time
                )
            return {"status": "failed", "error": str(e)}

    @staticmethod
    def _transform_news_items(
        parsed_data: Dict[str, Any], symbols: List[str]
    ) -> List[Dict[str, Any]]:
        """Transform parsed news data to storage format.

        Args:
            parsed_data: Parsed news data from API
            symbols: Original symbols requested

        Returns:
            List of formatted news items
        """
        news_items = []

        if isinstance(parsed_data, dict):
            articles = parsed_data.get("articles", [])
            if isinstance(articles, list):
                for article in articles:
                    news_items.append(
                        {
                            "symbol": article.get("symbol", symbols[0] if symbols else ""),
                            "headline": article.get("headline", article.get("title", "")),
                            "content": article.get("content", article.get("summary", "")),
                            "source": article.get("source", "Perplexity"),
                            "article_type": article.get("type", "news"),
                            "category": article.get("category", "general"),
                            "sentiment": article.get("sentiment", "neutral"),
                            "impact_score": article.get("impact_score", 0.5),
                            "relevance_score": article.get("relevance_score", 0.5),
                            "key_points": article.get("key_points", []),
                        }
                    )

        return news_items
