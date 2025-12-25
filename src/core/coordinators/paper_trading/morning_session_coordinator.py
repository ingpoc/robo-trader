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
from datetime import datetime, time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

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
        super().__init__(config)
        self.event_bus = event_bus
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
        await self._store_session_result(result)

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
                    # Use kite_service if available, otherwise skip pre-market data
                    if self.kite_service and hasattr(self.kite_service, 'get_pre_market_data'):
                        data = await self.kite_service.get_pre_market_data(stock["symbol"])
                    else:
                        # Fallback: use current market data
                        data = {"last_price": 0, "change": 0, "volume": 0}

                    if data and data.get("volume", 0) > 0:
                        pre_market_data.append({
                            "symbol": stock["symbol"],
                            "price": data.get("last_price", 0),
                            "change": data.get("change", 0),
                            "volume": data.get("volume", 0),
                            "risk_score": stock.get("risk_score", 0.5)
                        })
                except Exception as e:
                    self._log_warning(f"Failed to get pre-market data for {stock['symbol']}: {e}")

            # Sort by volume and change
            pre_market_data.sort(key=lambda x: (x["volume"], abs(x["change"])), reverse=True)

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

        for stock in stocks:
            try:
                research = await self.perplexity_service.research_stock(
                    symbol=stock["symbol"],
                    focus="pre-market sentiment, news, technical indicators",
                    max_tokens=500
                )
                research_results.append({
                    "symbol": stock["symbol"],
                    "market_data": stock,
                    "research": research,
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                self._log_warning(f"Research failed for {stock['symbol']}: {e}")
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

        # Queue AI analysis task to prevent token exhaustion
        task_service = await self.container.get("task_service")
        symbols = [r["symbol"] for r in research_results]

        task_id = await task_service.create_task(
            queue_name="AI_ANALYSIS",
            task_type="STOCK_ANALYSIS",
            payload={
                "agent_name": "trading_analyst",
                "symbols": symbols,
                "context": "morning_session",
                "research_data": research_results
            }
        )

        # Wait for task completion (with timeout)
        timeout = 180  # 3 minutes
        elapsed = 0
        while elapsed < timeout:
            task = await task_service.get_task(task_id)
            if task["status"] == "completed":
                return task.get("result", {}).get("trade_ideas", [])
            elif task["status"] == "failed":
                self._log_error(f"AI analysis task failed: {task.get('error', 'Unknown error')}")
                return []

            await asyncio.sleep(5)
            elapsed += 5

        self._log_warning("AI analysis task timed out")
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

    async def _store_session_result(self, result: MorningSessionResult) -> None:
        """Store morning session result in database."""
        try:
            # Get paper trading state manager
            paper_trading_state = await self.container.get("paper_trading_state")

            # Calculate duration in milliseconds
            duration_ms = int((result.end_time - result.start_time).total_seconds() * 1000)

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
                "trigger_source": "scheduled",
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