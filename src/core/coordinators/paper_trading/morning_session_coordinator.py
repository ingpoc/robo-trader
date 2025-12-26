"""Morning Session Coordinator for Paper Trading

Implements autonomous morning trading session (9:00 AM - 9:30 AM):
1. Scan pre-market data
2. Research selected stocks using Perplexity API
3. Generate trade ideas
4. Apply risk safeguards
5. Execute approved trades via Kite Connect paper trading API
6. Log all decisions
"""

import asyncio
import uuid
import json
from datetime import datetime, time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from claude_agent_sdk import ClaudeAgentOptions

from src.config import Config

from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus, Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.services.paper_trading_execution_service import PaperTradingExecutionService
from src.services.autonomous_trading_safeguards import AutonomousTradingSafeguards
from src.services.claude_agent.decision_logger import ClaudeDecisionLogger
from src.services.kite_connect_service import KiteConnectService
from src.core.perplexity_client import PerplexityClient
from src.services.paper_trading.stock_discovery import StockDiscoveryService
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.di import DependencyContainer


@dataclass
class MorningSessionResult:
    """Result of morning trading session"""
    session_id: str
    start_time: datetime
    end_time: datetime
    pre_market_scanned: int
    stocks_researched: int
    trade_ideas_generated: int
    trades_executed: int
    total_amount_invested: float
    decisions_logged: int
    success: bool
    error_message: Optional[str] = None


class MorningSessionCoordinator(BaseCoordinator):
    """
    Coordinates morning autonomous trading session.

    Max 150 lines - single responsibility for morning session workflow.
    """

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container

        # Services to be initialized
        self.execution_service: Optional[PaperTradingExecutionService] = None
        self.safeguards: Optional[AutonomousTradingSafeguards] = None
        self.decision_logger: Optional[ClaudeDecisionLogger] = None
        self.kite_service: Optional[KiteConnectService] = None
        self.perplexity_service: Optional[PerplexityClient] = None
        self.stock_discovery: Optional[StockDiscoveryService] = None

        self._session_active = False

    async def initialize(self) -> None:
        """Initialize morning session coordinator and all required services."""
        self._log_info("Initializing MorningSessionCoordinator")

        # Get all required services from DI container
        self.execution_service = await self.container.get("paper_trading_execution_service")
        self.decision_logger = await self.container.get("trade_decision_logger")
        self.stock_discovery = await self.container.get("stock_discovery_service")

        # Optional services (may not be registered yet)
        try:
            self.safeguards = await self.container.get("autonomous_trading_safeguards")
        except ValueError:
            self._log_warning("autonomous_trading_safeguards not registered - safeguards disabled")
            self.safeguards = None

        try:
            self.kite_service = await self.container.get("kite_connect_service")
        except ValueError:
            self._log_warning("kite_connect_service not registered - using market_data_service")
            self.kite_service = await self.container.get("market_data_service")

        try:
            self.perplexity_service = await self.container.get("perplexity_service")
        except ValueError:
            self._log_warning("perplexity_service not registered - research disabled")
            self.perplexity_service = None

        # Subscribe to events
        self.event_bus.subscribe(EventType.MARKET_OPEN, self)

        self._initialized = True
        self._log_info("MorningSessionCoordinator initialized successfully")

    async def run_morning_session(self, trigger: str = "scheduled") -> MorningSessionResult:
        """
        Run complete morning autonomous trading session.

        Args:
            trigger: What triggered the session (scheduled, manual, test)

        Returns:
            MorningSessionResult with session summary
        """
        if not self._initialized:
            raise TradingError(
                "MorningSessionCoordinator not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL
            )

        if self._session_active:
            raise TradingError(
                "Morning session already in progress",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM
            )

        session_id = f"morning_{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow()

        # Initialize result
        result = MorningSessionResult(
            session_id=session_id,
            start_time=start_time,
            end_time=start_time,
            pre_market_scanned=0,
            stocks_researched=0,
            trade_ideas_generated=0,
            trades_executed=0,
            total_amount_invested=0.0,
            decisions_logged=0,
            success=True
        )

        self._session_active = True

        try:
            self._log_info(f"Starting morning session {session_id} (trigger: {trigger})")

            # Step 1: Scan pre-market data
            pre_market_stocks = await self._scan_pre_market_data()
            result.pre_market_scanned = len(pre_market_stocks)

            # Step 2: Research selected stocks (max 5 to stay within token limits)
            stocks_to_research = pre_market_stocks[:5] if pre_market_stocks else []
            research_results = await self._research_stocks(stocks_to_research)
            result.stocks_researched = len(stocks_to_research)

            # Step 3: Generate trade ideas using Claude
            trade_ideas = await self._generate_trade_ideas(research_results)
            result.trade_ideas_generated = len(trade_ideas)

            # Step 4: Apply risk safeguards
            approved_trades = await self._apply_safeguards(trade_ideas)

            # Step 5: Execute approved trades
            execution_results = await self._execute_trades(approved_trades)
            result.trades_executed = len(execution_results)
            result.total_amount_invested = sum(r.get("amount", 0) for r in execution_results)

            # Step 6: Log all decisions
            await self._log_session_decisions(session_id, trade_ideas, approved_trades, execution_results)
            result.decisions_logged = len(trade_ideas) + len(approved_trades) + len(execution_results)

            # Publish session completion event
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.MORNING_SESSION_COMPLETE,
                timestamp=datetime.utcnow().isoformat(),
                data={
                    "session_id": session_id,
                    "trigger": trigger,
                    "summary": {
                        "scanned": result.pre_market_scanned,
                        "researched": result.stocks_researched,
                        "ideas": result.trade_ideas_generated,
                        "executed": result.trades_executed,
                        "invested": result.total_amount_invested
                    }
                },
                source="morning_session_coordinator"
            ))

            self._log_info(f"Morning session {session_id} completed successfully")

        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self._log_error(f"Morning session {session_id} failed: {e}", exc_info=True)

            # Publish error event
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.MORNING_SESSION_ERROR,
                timestamp=datetime.utcnow().isoformat(),
                data={"session_id": session_id, "error": str(e)},
                source="morning_session_coordinator"
            ))

        finally:
            result.end_time = datetime.utcnow()
            self._session_active = False

        # Store session result
        await self._store_session_result(result, trigger)

        return result

    async def _scan_pre_market_data(self) -> List[Dict[str, Any]]:
        """Scan pre-market data for opportunities."""
        try:
            # Get watchlist from stock discovery service
            watchlist = await self.stock_discovery.get_watchlist(limit=20)

            # Get pre-market data from Kite Connect
            pre_market_data = []
            for stock in watchlist:
                try:
                    # Use kite_service if available, otherwise use stock discovery data
                    if self.kite_service and hasattr(self.kite_service, 'get_pre_market_data'):
                        data = await self.kite_service.get_pre_market_data(stock["symbol"])
                    else:
                        # Fallback: use stock from discovery with zero-volume market data
                        # For paper trading, we still want to research these stocks
                        data = {"last_price": 0, "change": 0, "volume": 0}

                    # Include stocks even with zero volume for paper trading research
                    # Filter only if we have stock data (symbol exists)
                    if stock.get("symbol"):
                        pre_market_data.append({
                            "symbol": stock["symbol"],
                            "price": data.get("last_price", 0),
                            "change": data.get("change", 0),
                            "volume": data.get("volume", 0),
                            "risk_score": stock.get("risk_score", 0.5)
                        })
                except Exception as e:
                    self._log_warning(f"Failed to get pre-market data for {stock.get('symbol', 'unknown')}: {e}")
                    # Still include the stock if we have basic info
                    if stock.get("symbol"):
                        pre_market_data.append({
                            "symbol": stock["symbol"],
                            "price": 0,
                            "change": 0,
                            "volume": 0,
                            "risk_score": stock.get("risk_score", 0.5)
                        })

            # Sort by risk_score (lower is better), then by volume, then by change magnitude
            # For paper trading, prioritize stocks with better risk scores
            pre_market_data.sort(key=lambda x: (-x.get("risk_score", 0.5), x["volume"], abs(x["change"])), reverse=True)

            return pre_market_data[:10]  # Return top 10

        except Exception as e:
            self._log_error(f"Pre-market scan failed: {e}")
            return []

    async def _research_stocks(self, stocks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Research selected stocks using Perplexity API."""
        research_results = []

        # Skip research if perplexity service is not available
        if not self.perplexity_service:
            self._log_warning("Perplexity service not available - skipping research")
            for stock in stocks:
                research_results.append({
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": {"note": "Research service not available"},
                    "timestamp": datetime.utcnow().isoformat()
                })
            return research_results

        try:
            # Use fetch_batch_data to research all stocks at once
            from src.core.perplexity_client import QueryType
            symbols = [stock["symbol"] for stock in stocks]
            batch_result = await self.perplexity_service.fetch_batch_data(
                symbols=symbols,
                query_type=QueryType.COMPREHENSIVE,
                batch_size=5,
                max_concurrent=2
            )

            # Map batch results to individual stocks
            fundamentals_map = {f.symbol: f for f in batch_result.fundamentals}
            news_map = {n.symbol: n for n in batch_result.news}

            for stock in stocks:
                symbol = stock["symbol"]
                research_data = {
                    "fundamentals": fundamentals_map.get(symbol).model_dump() if symbol in fundamentals_map else None,
                    "news": news_map.get(symbol).model_dump() if symbol in news_map else None,
                    "note": "Research completed successfully"
                }
                research_results.append({
                    "symbol": symbol,
                    "market_data": stock,
                    "research": research_data,
                    "timestamp": datetime.utcnow().isoformat()
                })

        except Exception as e:
            self._log_warning(f"Batch research failed: {e}")
            # Fallback: return empty research for all stocks
            for stock in stocks:
                research_results.append({
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": {"error": str(e)},
                    "timestamp": datetime.utcnow().isoformat()
                })

        return research_results

    async def _generate_trade_ideas(self, research_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate trade ideas using Claude analysis."""
        if not research_results:
            return []

        # Limit to max 3 stocks to prevent token exhaustion
        batch_size = min(3, len(research_results))
        research_batch = research_results[:batch_size]

        self._log_info(f"Generating trade ideas for {batch_size} stocks using Claude SDK")

        try:
            # Get Claude SDK client manager
            manager = await ClaudeSDKClientManager.get_instance()

            # Create client for trade analysis
            options = ClaudeAgentOptions(
                model="claude-sonnet-4-20250514",
                enable_reasoning=True,
                timeout=45.0
            )
            client = await manager.get_client("trade_analysis", options)

            # Build prompt with research data
            prompt = self._build_trade_analysis_prompt(research_batch)

            # Query with timeout
            response_text = await query_with_timeout(client, prompt, timeout=45.0)

            # Parse JSON response
            trade_ideas = self._parse_trade_ideas_response(response_text)

            # Filter by confidence threshold (>= 0.6)
            filtered_ideas = [
                idea for idea in trade_ideas
                if idea.get("confidence", 0) >= 0.6
            ]

            self._log_info(f"Generated {len(filtered_ideas)} trade ideas (confidence >= 0.6)")
            return filtered_ideas

        except Exception as e:
            self._log_warning(f"Trade idea generation failed: {e}")
            # Return empty list on failure - don't stop the session
            return []

    def _build_trade_analysis_prompt(self, research_results: List[Dict[str, Any]]) -> str:
        """Build prompt for Claude trade analysis."""
        stocks_data = []
        for result in research_results:
            stock_info = {
                "symbol": result.get("symbol"),
                "price": result.get("market_data", {}).get("price", 0),
                "fundamentals": result.get("research", {}).get("fundamentals", {}),
                "news": result.get("research", {}).get("news", {}),
                "timestamp": result.get("timestamp")
            }
            stocks_data.append(stock_info)

        prompt = f"""You are an expert stock trader analyzing stocks for potential trades.

RESEARCH DATA:
{json.dumps(stocks_data, indent=2)}

TASK:
Analyze each stock and generate trade ideas (BUY or SELL) based on:
1. Fundamental strength (P/E, ROE, debt ratios)
2. News sentiment and recent developments
3. Price momentum and market conditions
4. Risk-reward potential

REQUIREMENTS:
- Only recommend trades with confidence >= 0.6 (60%)
- Calculate realistic entry, target, and stop-loss prices
- Limit position size to 5% of capital per stock
- Provide clear reasoning for each recommendation

OUTPUT FORMAT (JSON array):
[
  {{
    "symbol": "STOCK_SYMBOL",
    "action": "BUY" or "SELL",
    "confidence": 0.75,
    "reasoning": "Clear 2-3 sentence explanation",
    "entry_price": 2450.0,
    "target_price": 2550.0,
    "stop_loss": 2380.0,
    "position_size_pct": 5.0,
    "risk_reward_ratio": 1.5
  }}
]

Return ONLY the JSON array, no additional text."""

        return prompt

    def _parse_trade_ideas_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse trade ideas from Claude's JSON response."""
        try:
            # Extract JSON from response (may have markdown code blocks)
            response_text = response_text.strip()

            # Remove markdown code blocks if present
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            # Parse JSON
            trade_ideas = json.loads(response_text)

            # Validate structure
            if not isinstance(trade_ideas, list):
                self._log_warning("Expected JSON array, got different type")
                return []

            # Validate each trade idea has required fields
            validated_ideas = []
            for idea in trade_ideas:
                if all(key in idea for key in ["symbol", "action", "confidence", "reasoning"]):
                    # Ensure numeric fields are floats
                    idea["confidence"] = float(idea.get("confidence", 0))
                    idea["entry_price"] = float(idea.get("entry_price", 0))
                    idea["target_price"] = float(idea.get("target_price", 0))
                    idea["stop_loss"] = float(idea.get("stop_loss", 0))
                    idea["position_size_pct"] = float(idea.get("position_size_pct", 5.0))
                    idea["risk_reward_ratio"] = float(idea.get("risk_reward_ratio", 1.0))
                    validated_ideas.append(idea)
                else:
                    self._log_warning(f"Skipping invalid trade idea: {idea}")

            return validated_ideas

        except json.JSONDecodeError as e:
            self._log_warning(f"Failed to parse JSON response: {e}")
            self._log_debug(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            self._log_warning(f"Error parsing trade ideas: {e}")
            return []

    async def _apply_safeguards(self, trade_ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply risk safeguards to trade ideas."""
        approved_trades = []

        # If safeguards service is not available, approve all trades with warning
        if not self.safeguards:
            self._log_warning("Safeguards service not available - approving all trades (RISKY)")
            for idea in trade_ideas:
                idea["safeguard_checks"] = {
                    "passed": True,
                    "note": "Safeguards service not available"
                }
                approved_trades.append(idea)
            return approved_trades

        for idea in trade_ideas:
            try:
                # Check if trade passes all safeguards
                can_trade = await self.safeguards.can_execute_trade(
                    symbol=idea["symbol"],
                    action=idea["action"],  # BUY or SELL
                    quantity=idea.get("quantity", 0),
                    price=idea.get("price", 0)
                )

                if can_trade:
                    # Add safeguard metadata
                    idea["safeguard_checks"] = {
                        "passed": True,
                        "daily_trades_remaining": await self.safeguards.get_remaining_daily_trades(),
                        "position_size_ok": True,
                        "confidence_met": idea.get("confidence", 0) >= 0.7
                    }
                    approved_trades.append(idea)
                else:
                    await self.decision_logger.log_decision(
                        decision_type="SAFEGUARD_REJECT",
                        symbol=idea["symbol"],
                        reasoning="Trade rejected by safeguards",
                        confidence=1.0,
                        context={"trade_idea": idea}
                    )

            except Exception as e:
                self._log_error(f"Safeguard check failed for {idea['symbol']}: {e}")

        return approved_trades

    async def _execute_trades(self, approved_trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute approved trades via paper trading."""
        execution_results = []

        for trade in approved_trades:
            try:
                if trade["action"] == "BUY":
                    result = await self.execution_service.execute_buy_trade(
                        account_id="paper_trading_main",
                        symbol=trade["symbol"],
                        quantity=trade["quantity"],
                        order_type="MARKET",
                        strategy_rationale=trade.get("rationale", "Morning session trade")
                    )
                elif trade["action"] == "SELL":
                    result = await self.execution_service.execute_sell_trade(
                        account_id="paper_trading_main",
                        symbol=trade["symbol"],
                        quantity=trade["quantity"],
                        order_type="MARKET",
                        strategy_rationale=trade.get("rationale", "Morning session trade")
                    )
                else:
                    continue

                result["original_idea"] = trade
                execution_results.append(result)

            except Exception as e:
                self._log_error(f"Trade execution failed for {trade['symbol']}: {e}")

                # Log failed execution
                await self.decision_logger.log_decision(
                    decision_type="EXECUTION_FAILED",
                    symbol=trade["symbol"],
                    reasoning=f"Execution failed: {str(e)}",
                    confidence=1.0,
                    context={"trade": trade}
                )

        return execution_results

    async def _log_session_decisions(
        self,
        session_id: str,
        trade_ideas: List[Dict[str, Any]],
        approved_trades: List[Dict[str, Any]],
        execution_results: List[Dict[str, Any]]
    ) -> None:
        """Log all decisions made during the session."""

        # Log trade ideas
        for idea in trade_ideas:
            await self.decision_logger.log_decision(
                decision_type="TRADE_IDEA",
                symbol=idea["symbol"],
                reasoning=idea.get("rationale", ""),
                confidence=idea.get("confidence", 0),
                context={
                    "session_id": session_id,
                    "action": idea.get("action"),
                    "quantity": idea.get("quantity"),
                    "price": idea.get("price")
                }
            )

        # Log approved trades
        for trade in approved_trades:
            await self.decision_logger.log_decision(
                decision_type="TRADE_APPROVED",
                symbol=trade["symbol"],
                reasoning="Passed all safeguards",
                confidence=trade.get("confidence", 0),
                context={
                    "session_id": session_id,
                    "safeguards": trade.get("safeguard_checks", {})
                }
            )

        # Log execution results
        for result in execution_results:
            await self.decision_logger.log_decision(
                decision_type="TRADE_EXECUTED",
                symbol=result["symbol"],
                reasoning=f"Trade executed at {result['price']}",
                confidence=1.0,
                context={
                    "session_id": session_id,
                    "trade_id": result["trade_id"],
                    "quantity": result["quantity"],
                    "side": result["side"]
                }
            )

    async def _store_session_result(self, result: MorningSessionResult, trigger: str = "scheduled") -> None:
        """Store morning session result in database."""
        try:
            # Get paper trading state manager
            paper_trading_state = await self.container.get("paper_trading_state")

            # Calculate duration in milliseconds
            duration_ms = int((result.end_time - result.start_time).total_seconds() * 1000)

            # Normalize trigger source to uppercase for database
            trigger_source = str(trigger).upper() if trigger else "MANUAL"

            # Store session data
            session_data = {
                "session_date": result.start_time.date().isoformat(),
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat(),
                "success": result.success,
                "error_message": result.error_message,
                "metrics": {
                    "pre_market_scanned": result.pre_market_scanned,
                    "stocks_researched": result.stocks_researched,
                    "trade_ideas_generated": result.trade_ideas_generated,
                    "trades_executed": result.trades_executed,
                    "total_amount_invested": result.total_amount_invested,
                    "decisions_logged": result.decisions_logged
                },
                "pre_market_data": [],  # Will be populated with actual data
                "trade_ideas": [],  # Will be populated with actual ideas
                "executed_trades": [],  # Will be populated with actual trades
                "session_context": {
                    "market_open": True,
                    "session_duration_minutes": duration_ms / 60000
                },
                "trigger_source": trigger_source,
                "total_duration_ms": duration_ms
            }

            await paper_trading_state.store_morning_session(result.session_id, session_data)

        except Exception as e:
            self._log_error(f"Failed to store session result: {e}")

    async def handle_event(self, event: Event) -> None:
        """Handle incoming events."""
        if event.type == EventType.MARKET_OPEN:
            # Market opened, start morning session if within time window
            now = datetime.utcnow().time()
            if time(9, 0) <= now <= time(9, 30):
                asyncio.create_task(self.run_morning_session(trigger="market_open"))

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._session_active:
            self._log_warning("Morning session active during cleanup")

        # Unsubscribe from events
        self.event_bus.unsubscribe(EventType.MARKET_OPEN, self)

        self._log_info("MorningSessionCoordinator cleanup complete")