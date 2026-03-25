"""
Paper Trading Stock Discovery Service

Implements autonomous stock discovery for paper trading using:
- Claude Agent SDK web research for fresh market evidence
- Claude Agent SDK feature extraction
- Sector and market cap screening
- Deterministic technical and fundamental scoring
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from loguru import logger

from ...core.event_bus import EventHandler, Event
from ...core.errors import TradingError, ErrorCategory, ErrorSeverity


class StockDiscoveryService(EventHandler):
    """
    Implements autonomous stock discovery for paper trading.

    Features:
    - Market-wide stock screening
    - Sector-focused discovery
    - Event-driven discovery (earnings, news, etc.)
    - Claude-powered analysis
    - Watchlist management
    """

    def __init__(
        self,
        state_manager,
        market_research_service,
        event_bus,
        config: Dict[str, Any],
        feature_extractor,
        deterministic_scorer,
    ):
        self.state_manager = state_manager
        self.market_research_service = market_research_service
        self.event_bus = event_bus
        self.config = config
        self.feature_extractor = feature_extractor
        self.deterministic_scorer = deterministic_scorer

        # Default discovery criteria
        self.default_criteria = {
            "min_market_cap": "small",  # small, mid, large, mega
            "max_market_cap": "mega",
            "exclude_penny_stocks": True,
            "min_price": 50.0,
            "max_price": 5000.0,
            "sectors": [],  # Empty means all sectors
            "liquidity_min": "medium"  # low, medium, high
        }

        self._running = False

    async def initialize(self) -> None:
        """Initialize the stock discovery service."""
        logger.info("Initializing Stock Discovery Service")

        # Note: Event subscriptions deferred until EventType enums are defined
        # For now, service can be triggered manually via API

        self._running = True
        logger.info("Stock Discovery Service initialized")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Note: Event subscriptions deferred until EventType enums are defined
        self._running = False
        logger.info("Stock Discovery Service cleaned up")

    async def run_discovery_session(
        self,
        session_type: str = "daily_screen",
        custom_criteria: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Run a stock discovery session.

        Args:
            session_type: Type of discovery session
            custom_criteria: Override default criteria

        Returns:
            Session results with discovered stocks
        """
        session_id = str(uuid.uuid4())
        start_time = datetime.now(timezone.utc)

        try:
            logger.info(f"Starting stock discovery session: {session_id}")

            # Create session record
            await self._create_discovery_session(session_id, session_type, custom_criteria)

            # Get discovery criteria
            criteria = {**self.default_criteria, **(custom_criteria or {})}

            # Step 1: Market-wide screening
            screened_stocks = await self._screen_market(criteria)

            # Step 2: Deep analysis of top candidates
            analyzed_stocks = await self._analyze_candidates(screened_stocks[:50], criteria)

            # Step 3: Score and rank stocks
            scored_stocks = await self._score_stocks(analyzed_stocks)

            # Step 4: Update watchlist with top candidates
            watchlist_updates = await self._update_watchlist(scored_stocks[:20])

            # Complete session
            duration_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)

            await self._complete_discovery_session(
                session_id,
                duration_ms,
                len(screened_stocks),
                len(analyzed_stocks),
                len([s for s in scored_stocks if s.get('score', 0) > 70])
            )

            return {
                "session_id": session_id,
                "session_type": session_type,
                "total_scanned": len(screened_stocks),
                "analyzed": len(analyzed_stocks),
                "high_potential": len([s for s in scored_stocks if s.get('score', 0) > 70]),
                "watchlist_updates": watchlist_updates,
                "top_candidates": scored_stocks[:10],
                "duration_ms": duration_ms,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"Stock discovery session failed: {e}")
            await self._fail_discovery_session(session_id, str(e))
            raise TradingError(
                f"Stock discovery failed: {e}",
                category=ErrorCategory.ANALYSIS,
                severity=ErrorSeverity.HIGH
            )

    async def _screen_market(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Screen the market for potential stocks using the Nifty 500 universe.

        Loads from data/nse_universe.json (updateable periodically).
        Applies sector and market cap filters from criteria.
        """
        logger.info("Screening market for stocks from NSE universe")

        # Load universe from JSON file
        universe_path = Path(__file__).parents[3] / "data" / "nse_universe.json"
        try:
            with open(universe_path) as f:
                universe_data = json.load(f)
            market_stocks = universe_data.get("universe", [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load NSE universe from {universe_path}: {e}")
            market_stocks = []

        # Apply filters
        filtered_stocks = []
        allowed_sectors = criteria.get("sectors", [])
        allowed_caps = criteria.get("market_cap_tiers", [])  # e.g., ["large", "mid"]

        for stock in market_stocks:
            # Skip if sector filter is set and stock doesn't match
            if allowed_sectors and stock.get("sector") not in allowed_sectors:
                continue
            # Skip if cap tier filter is set and stock doesn't match
            if allowed_caps and stock.get("cap") not in allowed_caps:
                continue

            filtered_stocks.append({
                "symbol": stock["symbol"],
                "name": stock.get("name", stock["symbol"]),
                "sector": stock.get("sector", "Unknown"),
                "cap": stock.get("cap", "unknown"),
                "discovery_source": "nse_universe",
                "screening_criteria": criteria
            })

        logger.info(f"Screened {len(market_stocks)} stocks, found {len(filtered_stocks)} candidates")
        return filtered_stocks

    async def _analyze_candidates(
        self,
        stocks: List[Dict[str, Any]],
        criteria: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Analyze candidate stocks using Claude web research and feature extraction.
        """
        logger.info(f"Analyzing {len(stocks)} candidate stocks")

        analyzed_stocks = []

        # Process in batches to avoid overwhelming the API
        batch_size = 3
        for i in range(0, len(stocks), batch_size):
            batch = stocks[i:i + batch_size]

            for stock in batch:
                try:
                    external_research = await self._research_stock_external(stock)

                    # Claude analysis
                    claude_analysis = await self._analyze_stock_claude(stock, external_research)

                    analyzed_stock = {
                        **stock,
                        "external_research": external_research,
                        "claude_analysis": claude_analysis,
                        "research_timestamp": datetime.now(timezone.utc).isoformat()
                    }

                    analyzed_stocks.append(analyzed_stock)

                except Exception as e:
                    logger.error(f"Failed to analyze stock {stock.get('symbol')}: {e}")
                    # Add with basic info only
                    analyzed_stocks.append({
                        **stock,
                        "analysis_error": str(e),
                        "research_timestamp": datetime.now(timezone.utc).isoformat()
                    })

        return analyzed_stocks

    async def _research_stock_external(self, stock: Dict[str, Any]) -> Dict[str, Any]:
        """
        Research a stock using Claude's built-in web tools.
        """
        try:
            symbol = stock["symbol"]
            response = await self.market_research_service.collect_symbol_research(
                symbol,
                company_name=stock.get("name"),
            )
            return {
                "symbol": symbol,
                "research_timestamp": response.get("research_timestamp")
                or datetime.now(timezone.utc).isoformat(),
                "research_summary": response.get("research_summary", ""),
                "summary": response.get("summary", ""),
                "news": response.get("news", ""),
                "financial_data": response.get("financial_data", ""),
                "filings": response.get("filings", ""),
                "market_context": response.get("market_context", ""),
                "sources": response.get("sources", []),
                "source_summary": response.get("source_summary", []),
                "evidence_citations": response.get("evidence_citations", []),
                "evidence": response.get("evidence", []),
                "risks": response.get("risks", []),
                "errors": response.get("errors", []),
            }

        except Exception as e:
            logger.error(f"Claude web research failed for {stock.get('symbol')}: {e}")
            return {
                "symbol": stock.get("symbol"),
                "error": str(e),
                "research_timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _analyze_stock_claude(
        self,
        stock: Dict[str, Any],
        external_research: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze stock using structured feature extraction via FeatureExtractor.

        Instead of asking Claude "should I buy?", extracts specific factual features
        and scores them deterministically. The LLM is a feature extractor, not a trader.
        """
        try:
            # Build research data dict from Claude web research
            research_data = {
                "news": external_research.get("research_summary", "") or external_research.get("news", ""),
                "financials": external_research.get("financial_data", ""),
                "filings": external_research.get("filings", ""),
                "market_data": external_research.get("market_context", ""),
            }

            # Extract structured features via Claude (factual questions, not opinions)
            entry = await self.feature_extractor.extract_features(stock["symbol"], research_data)

            # Score deterministically from features
            entry = self.deterministic_scorer.score(entry)

            return {
                "symbol": stock["symbol"],
                "analysis_type": "feature_extraction",
                "recommendation": entry.action or "HOLD",
                "confidence": entry.feature_confidence or 0.0,
                "score": entry.score or 0.0,
                "features": entry.to_flat_features(),
                "research_ledger_id": entry.id,
                "key_factors": [k for k, v in entry.to_flat_features().items() if v is not None],
                "risks": [],
                "opportunities": [],
            }
        except Exception as e:
            logger.warning(f"Feature extraction failed for {stock['symbol']}, using minimal analysis: {e}")
            return {
                "symbol": stock["symbol"],
                "analysis_type": "fallback",
                "recommendation": "HOLD",
                "confidence": 0.0,
                "score": 0.0,
                "features": {},
                "key_factors": [],
                "risks": [f"Feature extraction failed: {e}"],
                "opportunities": [],
            }

    async def _score_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Score and rank stocks based on deterministic feature extraction scores.

        Scores come from the DeterministicScorer applied during _analyze_stock_claude().
        This method just extracts the pre-computed scores and sorts.
        """
        scored_stocks = []

        for stock in stocks:
            score = 0.0
            recommendation = "HOLD"

            if "claude_analysis" in stock:
                analysis = stock["claude_analysis"]
                # Use the deterministic score computed by DeterministicScorer
                score = analysis.get("score", 0.0)
                recommendation = analysis.get("recommendation", "HOLD")

            scored_stocks.append({
                **stock,
                "score": score,
                "recommendation": recommendation,
                "scoring_timestamp": datetime.now(timezone.utc).isoformat()
            })

        # Sort by score (descending)
        scored_stocks.sort(key=lambda x: x.get("score", 0), reverse=True)

        return scored_stocks

    async def get_watchlist(
        self,
        status: str = "ACTIVE",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get stocks from the discovery watchlist.

        Args:
            status: Filter by status (ACTIVE, ARCHIVED, etc.)
            limit: Maximum number of stocks to return

        Returns:
            List of watchlist stocks with their analysis data
        """
        try:
            watchlist = await self.state_manager.paper_trading.get_discovery_watchlist(
                status=status,
                limit=limit
            )
            logger.info(f"Retrieved {len(watchlist)} stocks from watchlist")
            return watchlist
        except Exception as e:
            logger.error(f"Failed to get watchlist: {e}")
            return []

    async def _update_watchlist(
        self,
        stocks: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Update the watchlist with new discoveries.
        """
        updates = {"added": 0, "updated": 0, "skipped": 0}

        for stock in stocks:
            try:
                # Check if already in watchlist
                existing = await self.state_manager.paper_trading.get_discovery_watchlist_by_symbol(stock["symbol"])

                if existing:
                    # Update existing record
                    await self.state_manager.paper_trading.update_discovery_watchlist(
                        stock["symbol"],
                        {
                            "current_price": stock.get("current_price"),
                            "recommendation": stock.get("recommendation", "WATCH"),
                            "confidence_score": stock.get("score", 0) / 100,
                            "research_summary": json.dumps({
                                "external_research": stock.get("external_research"),
                                "claude_web_research": stock.get("external_research"),
                                "claude": stock.get("claude_analysis")
                            }),
                            "last_analyzed": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    updates["updated"] += 1
                else:
                    # Add new record
                    await self.state_manager.paper_trading.add_to_discovery_watchlist({
                        "symbol": stock["symbol"],
                        "company_name": stock.get("name"),
                        "sector": stock.get("sector"),
                        "discovery_date": datetime.now(timezone.utc).date().isoformat(),
                        "discovery_source": stock.get("discovery_source", "autonomous"),
                        "discovery_reason": "Stock discovery analysis",
                        "current_price": stock.get("current_price"),
                        "recommendation": stock.get("recommendation", "WATCH"),
                        "confidence_score": stock.get("score", 0) / 100,
                        "research_summary": json.dumps({
                            "external_research": stock.get("external_research"),
                            "claude_web_research": stock.get("external_research"),
                            "claude": stock.get("claude_analysis")
                        }),
                        "status": "ACTIVE",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    updates["added"] += 1

            except Exception as e:
                logger.error(f"Failed to update watchlist for {stock.get('symbol')}: {e}")
                updates["skipped"] += 1

        return updates

    async def _create_discovery_session(
        self,
        session_id: str,
        session_type: str,
        custom_criteria: Optional[Dict[str, Any]]
    ) -> None:
        """Create a discovery session record."""
        await self.state_manager.paper_trading.create_discovery_session({
            "id": session_id,
            "session_date": datetime.now(timezone.utc).date().isoformat(),
            "session_type": session_type,
            "screening_criteria": json.dumps(custom_criteria or self.default_criteria),
            "total_stocks_scanned": 0,
            "stocks_discovered": 0,
            "high_potential_stocks": 0,
            "session_status": "RUNNING",
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    async def _complete_discovery_session(
        self,
        session_id: str,
        duration_ms: int,
        total_scanned: int,
        analyzed: int,
        high_potential: int
    ) -> None:
        """Complete a discovery session."""
        await self.state_manager.paper_trading.update_discovery_session(session_id, {
            "total_stocks_scanned": total_scanned,
            "stocks_discovered": analyzed,
            "high_potential_stocks": high_potential,
            "session_duration_ms": duration_ms,
            "session_status": "COMPLETED",
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

    async def _fail_discovery_session(self, session_id: str, error_message: str) -> None:
        """Mark a discovery session as failed."""
        await self.state_manager.paper_trading.update_discovery_session(session_id, {
            "session_status": "FAILED",
            "error_message": error_message,
            "completed_at": datetime.now(timezone.utc).isoformat()
        })

    async def handle_event(self, event: Event) -> None:
        """Handle market events for reactive discovery."""
        if not self._running:
            return

        # Event-driven discovery temporarily disabled due to missing EventType enums
        # if event.type == EventType.MARKET_NEWS:
        #     # Trigger discovery if news is significant
        #     await self._handle_market_news_event(event)
        # elif event.type == EventType.MARKET_EARNINGS:  # Use existing enum
        #     # Research companies announcing earnings
        #     await self._handle_earnings_event(event)
        # elif event.type == EventType.SECTOR_UPDATE:  # TODO: Add this enum if needed
        #     # Screen sector for opportunities
        #     await self._handle_sector_event(event)

    async def _handle_market_news_event(self, event: Event) -> None:
        """Handle significant market news."""
        data = event.data
        if data.get("significance") == "high":
            # Trigger focused discovery on affected sectors
            pass

    async def _handle_earnings_event(self, event: Event) -> None:
        """Handle earnings announcements."""
        data = event.data
        symbol = data.get("symbol")
        if symbol:
            # Research the announcing company
            pass

    async def _handle_sector_event(self, event: Event) -> None:
        """Handle sector updates."""
        data = event.data
        sector = data.get("sector")
        if sector:
            # Screen sector for opportunities
            pass
