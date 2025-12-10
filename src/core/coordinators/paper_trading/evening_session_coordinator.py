"""
Evening Session Coordinator for Paper Trading

Implements PT-004: Evening Performance Review
Daily evening session (4:00 PM - 4:30 PM) to review trades, calculate P&L, generate insights.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from loguru import logger

from src.config import Config
from src.core.event_bus import EventBus, Event, EventType
from ..base_coordinator import BaseCoordinator
# DependencyContainer accessed via self.container
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.core.perplexity_client import PerplexityClient
from src.services.kite_connect_service import KiteConnectService
from src.services.autonomous_trading_safeguards import AutonomousTradingSafeguards
# State managers accessed through state_manager


class EveningSessionCoordinator(BaseCoordinator):
    """
    Coordinates evening performance review sessions for paper trading.

    Responsibilities:
    - Review executed trades from the day
    - Calculate daily P&L and performance metrics
    - Generate trading insights using Perplexity API
    - Store learnings for strategy evolution
    - Prepare next day's watchlist
    """

    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        container: Any  # DependencyContainer
    ):
        super().__init__(config)
        self.event_bus = event_bus
        self.container = container
        self._running_sessions: Dict[str, Dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize evening session coordinator."""
        self._log_info("Initializing EveningSessionCoordinator")

        # Get required services
        self.perplexity = await self.container.get("perplexity_service")
        self.kite_service = await self.container.get("kite_connect_service")
        self.safeguards = await self.container.get("autonomous_trading_safeguards")

        # Get state managers
        self.state_manager = await self.container.get("state_manager")
        self.paper_trading_state = self.state_manager.paper_trading
        self.real_time_state = self.state_manager.real_time_trading

        self._initialized = True
        self._log_info("EveningSessionCoordinator initialized successfully")

    async def run_evening_review(
        self,
        trigger_source: str = "SCHEDULED",
        review_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run the evening performance review session.

        Args:
            trigger_source: Source of the trigger (SCHEDULED, MANUAL)
            review_date: Date to review (defaults to today)

        Returns:
            Dictionary with review results
        """
        if not self._initialized:
            raise TradingError(
                "EveningSessionCoordinator not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL
            )

        session_id = f"evening_review_{uuid.uuid4().hex[:16]}"
        review_date = review_date or datetime.now(timezone.utc).strftime('%Y-%m-%d')

        start_time = datetime.now(timezone.utc)
        self._log_info(f"Starting evening review session {session_id} for {review_date}")

        try:
            # Initialize session tracking
            self._running_sessions[session_id] = {
                "start_time": start_time,
                "status": "running",
                "review_date": review_date
            }

            # Step 1: Calculate daily performance metrics
            self._log_info("Calculating daily performance metrics...")
            performance_metrics = await self.paper_trading_state.calculate_daily_performance_metrics(
                review_date
            )

            # Step 2: Get current positions
            self._log_info("Fetching current positions...")
            open_positions = await self.paper_trading_state.get_open_trades()

            # Step 3: Analyze trading patterns with Perplexity
            self._log_info("Analyzing trading patterns with AI...")
            trading_insights = await self._generate_trading_insights(
                performance_metrics,
                open_positions
            )

            # Step 4: Review strategy effectiveness
            self._log_info("Evaluating strategy performance...")
            strategy_analysis = await self._analyze_strategy_performance(
                performance_metrics.get("strategy_performance", {})
            )

            # Step 5: Generate next day's watchlist
            self._log_info("Preparing next day's watchlist...")
            watchlist = await self._prepare_next_day_watchlist(
                performance_metrics,
                trading_insights
            )

            # Step 6: Compile market observations
            self._log_info("Compiling market observations...")
            market_observations = await self._compile_market_observations()

            # Step 7: Generate learning insights
            self._log_info("Generating learning insights...")
            learning_insights = await self._generate_learning_insights(
                performance_metrics,
                trading_insights,
                strategy_analysis
            )

            # Compile session data
            end_time = datetime.now(timezone.utc)
            total_duration_ms = int((end_time - start_time).total_seconds() * 1000)

            session_data = {
                "review_id": session_id,
                "review_date": review_date,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "success": True,
                "error_message": None,
                "review_data": {
                    "session_summary": {
                        "total_trades": len(performance_metrics.get("trades_reviewed", [])),
                        "daily_pnl": performance_metrics.get("daily_pnl", 0.0),
                        "daily_pnl_percent": performance_metrics.get("daily_pnl_percent", 0.0),
                        "win_rate": performance_metrics.get("win_rate", 0.0),
                        "session_duration_minutes": total_duration_ms / 60000
                    }
                },
                "trades_reviewed": performance_metrics.get("trades_reviewed", []),
                "daily_pnl": performance_metrics.get("daily_pnl", 0.0),
                "daily_pnl_percent": performance_metrics.get("daily_pnl_percent", 0.0),
                "open_positions_count": performance_metrics.get("open_positions_count", 0),
                "closed_positions_count": performance_metrics.get("closed_positions_count", 0),
                "win_rate": performance_metrics.get("win_rate", 0.0),
                "trading_insights": trading_insights,
                "strategy_performance": strategy_analysis,
                "market_observations": market_observations,
                "next_day_watchlist": watchlist,
                "session_context": {
                    "trigger_source": trigger_source,
                    "market_hours": "regular",
                    "session_type": "evening_review"
                },
                "trigger_source": trigger_source,
                "total_duration_ms": total_duration_ms
            }

            # Store review results
            await self.paper_trading_state.store_evening_performance_review(
                session_id,
                session_data
            )

            # Update trading safeguards with daily performance
            await self._update_safeguards(performance_metrics)

            # Publish completion event
            await self.event_bus.publish(Event(
                event_type=EventType.EVENING_REVIEW_COMPLETE,
                data={
                    "session_id": session_id,
                    "review_date": review_date,
                    "daily_pnl": performance_metrics.get("daily_pnl", 0.0),
                    "trades_count": len(performance_metrics.get("trades_reviewed", [])),
                    "win_rate": performance_metrics.get("win_rate", 0.0)
                },
                source="evening_session_coordinator"
            ))

            self._log_info(f"Evening review {session_id} completed successfully")
            return session_data

        except Exception as e:
            self._log_error(f"Evening review {session_id} failed: {e}", exc_info=True)

            # Store failure record
            error_data = {
                "review_id": session_id,
                "review_date": review_date,
                "start_time": start_time.isoformat(),
                "end_time": datetime.now(timezone.utc).isoformat(),
                "success": False,
                "error_message": str(e),
                "trigger_source": trigger_source
            }
            await self.paper_trading_state.store_evening_performance_review(
                session_id,
                error_data
            )

            raise TradingError(
                f"Evening review failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                context={"session_id": session_id, "review_date": review_date}
            )

        finally:
            # Clean up session tracking
            if session_id in self._running_sessions:
                del self._running_sessions[session_id]

    async def _generate_trading_insights(
        self,
        performance_metrics: Dict[str, Any],
        open_positions: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate trading insights using Perplexity API."""
        try:
            # Prepare context for AI analysis
            context = {
                "daily_performance": {
                    "pnl": performance_metrics.get("daily_pnl", 0.0),
                    "pnl_percent": performance_metrics.get("daily_pnl_percent", 0.0),
                    "win_rate": performance_metrics.get("win_rate", 0.0),
                    "trades_count": len(performance_metrics.get("trades_reviewed", []))
                },
                "open_positions": len(open_positions),
                "strategy_breakdown": performance_metrics.get("strategy_performance", {})
            }

            # Create research query for Perplexity
            query = f"""
            Analyze today's paper trading performance and provide actionable insights:

            Daily P&L: ₹{performance_metrics.get('daily_pnl', 0):.2f} ({performance_metrics.get('daily_pnl_percent', 0):.2f}%)
            Win Rate: {performance_metrics.get('win_rate', 0):.1f}%
            Total Trades: {len(performance_metrics.get('trades_reviewed', []))}
            Open Positions: {len(open_positions)}

            Strategy Performance:
            {self._format_strategy_performance(performance_metrics.get('strategy_performance', {}))}

            Provide 3-5 key insights about:
            1. What worked well today
            2. What didn't work and why
            3. Risk management observations
            4. Market condition impacts
            5. Recommendations for tomorrow
            """

            # Query Perplexity for analysis
            response = await self.perplexity.query_perplexity(
                query=query,
                context=context,
                max_tokens=500
            )

            # Extract insights from response
            insights = []
            if response and "content" in response:
                # Parse numbered list from response
                content = response["content"]
                lines = content.split('\n')
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-')):
                        # Clean up the insight
                        insight = line.lstrip('0123456789.- ').strip()
                        if insight:
                            insights.append(insight)

            # Ensure we have at least some insights
            if not insights:
                if performance_metrics.get("daily_pnl", 0) > 0:
                    insights.append("Positive day - consider analyzing winning trades for patterns")
                else:
                    insights.append("Negative day - review loss management and entry criteria")

                if performance_metrics.get("win_rate", 0) < 50:
                    insights.append("Win rate below 50% - tighten entry criteria or improve exit timing")

            return insights[:5]  # Limit to 5 insights

        except Exception as e:
            self._log_error(f"Failed to generate trading insights: {e}")
            return ["Insights generation failed - please check system logs"]

    async def _analyze_strategy_performance(
        self,
        strategy_performance: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze and evaluate strategy performance."""
        try:
            analysis = {
                "top_strategies": [],
                "underperforming_strategies": [],
                "recommendations": []
            }

            # Sort strategies by P&L
            sorted_strategies = sorted(
                strategy_performance.items(),
                key=lambda x: x[1].get("total_pnl", 0),
                reverse=True
            )

            # Identify top and underperforming strategies
            for strategy, metrics in sorted_strategies:
                strategy_info = {
                    "strategy": strategy,
                    "pnl": metrics.get("total_pnl", 0),
                    "trades": metrics.get("trades", 0),
                    "win_rate": metrics.get("win_rate", 0)
                }

                if metrics.get("total_pnl", 0) > 0 and metrics.get("win_rate", 0) > 60:
                    analysis["top_strategies"].append(strategy_info)
                elif metrics.get("total_pnl", 0) < 0 or metrics.get("win_rate", 0) < 40:
                    analysis["underperforming_strategies"].append(strategy_info)

            # Generate recommendations
            if analysis["top_strategies"]:
                analysis["recommendations"].append(
                    f"Increase allocation to top performers: {', '.join([s['strategy'] for s in analysis['top_strategies'][:2]])}"
                )

            if analysis["underperforming_strategies"]:
                analysis["recommendations"].append(
                    f"Review or reduce usage of: {', '.join([s['strategy'] for s in analysis['underperforming_strategies'][:2]])}"
                )

            if not analysis["top_strategies"] and not analysis["underperforming_strategies"]:
                analysis["recommendations"].append("No clear strategy differentiation - consider longer evaluation period")

            return analysis

        except Exception as e:
            self._log_error(f"Failed to analyze strategy performance: {e}")
            return {
                "top_strategies": [],
                "underperforming_strategies": [],
                "recommendations": ["Strategy analysis failed - check logs"]
            }

    async def _prepare_next_day_watchlist(
        self,
        performance_metrics: Dict[str, Any],
        trading_insights: List[str]
    ) -> List[Dict[str, Any]]:
        """Prepare watchlist for next trading day."""
        try:
            watchlist = []

            # Get symbols from today's trades for monitoring
            traded_symbols = set()
            for trade in performance_metrics.get("trades_reviewed", []):
                traded_symbols.add(trade["symbol"])

            # Get current positions
            open_positions = await self.paper_trading_state.get_open_trades()
            position_symbols = set(pos["symbol"] for pos in open_positions)

            # Combine for monitoring
            watch_symbols = traded_symbols.union(position_symbols)

            # Add symbols from discovery watchlist
            discovery_watchlist = await self.paper_trading_state.get_discovery_watchlist(limit=20)
            for item in discovery_watchlist:
                if item["recommendation"] in ["BUY", "STRONG_BUY"]:
                    watch_symbols.add(item["symbol"])

            # Create watchlist entries
            for symbol in list(watch_symbols)[:15]:  # Limit to 15 symbols
                watchlist.append({
                    "symbol": symbol,
                    "reason": "Active trading or high potential",
                    "priority": "HIGH" if symbol in position_symbols else "MEDIUM",
                    "source": "trading_activity"
                })

            return watchlist

        except Exception as e:
            self._log_error(f"Failed to prepare next day watchlist: {e}")
            return []

    async def _compile_market_observations(self) -> Dict[str, Any]:
        """Compile market observations and conditions."""
        try:
            observations = {
                "market_sentiment": "NEUTRAL",
                "volatility": "NORMAL",
                "key_events": [],
                "sector_notes": []
            }

            # Get recent news for context
            cursor = await self.state_manager.news_earnings_state.get_recent_news(days=1, limit=10)
            if cursor:
                news_items = await cursor.fetchall()

                # Analyze sentiment from news
                positive_count = sum(1 for item in news_items if item[5] == "positive")  # sentiment column
                negative_count = sum(1 for item in news_items if item[5] == "negative")

                if positive_count > negative_count * 1.5:
                    observations["market_sentiment"] = "BULLISH"
                elif negative_count > positive_count * 1.5:
                    observations["market_sentiment"] = "BEARISH"

                # Extract key events
                for item in news_items[:5]:
                    observations["key_events"].append({
                        "title": item[2],  # title column
                        "sentiment": item[5],  # sentiment column
                        "impact": "HIGH" if abs(item[6] or 0) > 0.7 else "MEDIUM"  # relevance_score
                    })

            return observations

        except Exception as e:
            self._log_error(f"Failed to compile market observations: {e}")
            return {
                "market_sentiment": "UNKNOWN",
                "volatility": "UNKNOWN",
                "key_events": [],
                "sector_notes": []
            }

    async def _generate_learning_insights(
        self,
        performance_metrics: Dict[str, Any],
        trading_insights: List[str],
        strategy_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate learning insights for strategy evolution."""
        try:
            learnings = []

            # Performance-based learnings
            daily_pnl = performance_metrics.get("daily_pnl", 0)
            win_rate = performance_metrics.get("win_rate", 0)

            if daily_pnl > 0 and win_rate > 60:
                learnings.append("Strong performance day - document successful patterns for replication")
            elif daily_pnl < 0 and win_rate < 40:
                learnings.append("Poor performance day - identify and address systematic issues")
            elif win_rate < 50:
                learnings.append("Low win rate suggests need for stricter entry criteria")
            elif daily_pnl < 0 and win_rate > 60:
                learnings.append("Win rate good but P&L negative - review risk/reward ratios")

            # Strategy-based learnings
            top_strategies = strategy_analysis.get("top_strategies", [])
            if top_strategies:
                learnings.append(f"Top performing strategy: {top_strategies[0]['strategy']} - analyze key success factors")

            # Market condition learnings
            if "market conditions" in strategy_analysis:
                learnings.append("Document market conditions impact on strategy performance")

            return learnings[:3]  # Limit to 3 key learnings

        except Exception as e:
            self._log_error(f"Failed to generate learning insights: {e}")
            return ["Learning analysis failed - check system logs"]

    async def _update_safeguards(self, performance_metrics: Dict[str, Any]) -> None:
        """Update trading safeguards with daily performance."""
        try:
            # Update daily P&L in safeguards
            daily_pnl = performance_metrics.get("daily_pnl", 0)
            await self.safeguards.update_daily_pnl(daily_pnl)

        except Exception as e:
            self._log_error(f"Failed to update safeguards: {e}")

    def _format_strategy_performance(self, strategy_performance: Dict[str, Any]) -> str:
        """Format strategy performance for display."""
        lines = []
        for strategy, metrics in strategy_performance.items():
            pnl = metrics.get("total_pnl", 0)
            win_rate = metrics.get("win_rate", 0)
            trades = metrics.get("trades", 0)
            lines.append(f"  {strategy}: ₹{pnl:.2f} ({win_rate:.1f}% win rate, {trades} trades)")
        return "\n".join(lines) if lines else "No strategy data available"

    async def get_running_sessions(self) -> List[Dict[str, Any]]:
        """Get list of currently running evening review sessions."""
        return [
            {
                "session_id": session_id,
                "start_time": data["start_time"],
                "status": data["status"],
                "review_date": data["review_date"]
            }
            for session_id, data in self._running_sessions.items()
        ]

    async def cleanup(self) -> None:
        """Cleanup evening session coordinator resources."""
        self._log_info("EveningSessionCoordinator cleanup complete")
        self._running_sessions.clear()