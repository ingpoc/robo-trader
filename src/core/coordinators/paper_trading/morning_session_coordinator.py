"""Morning Session Coordinator - thin orchestrator delegating to sub-coordinators."""
import asyncio
import os
import uuid
from datetime import datetime, time
from typing import Optional, TYPE_CHECKING
from dataclasses import dataclass

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus, Event, EventType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from .morning_premarket_coordinator import MorningPremarketCoordinator
from .morning_research_coordinator import MorningResearchCoordinator
from .morning_trade_idea_coordinator import MorningTradeIdeaCoordinator
from .morning_safeguard_coordinator import MorningSafeguardCoordinator
from .morning_execution_coordinator import MorningExecutionCoordinator

if TYPE_CHECKING:
    from src.core.di import DependencyContainer


@dataclass
class MorningSessionResult:
    """Result of morning trading session."""
    session_id: str
    start_time: datetime
    end_time: datetime
    pre_market_scanned: int = 0
    stocks_researched: int = 0
    trade_ideas_generated: int = 0
    trades_executed: int = 0
    total_amount_invested: float = 0.0
    decisions_logged: int = 0
    success: bool = True
    error_message: Optional[str] = None


class MorningSessionCoordinator(BaseCoordinator):
    """Orchestrates morning autonomous trading session via sub-coordinators."""

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container
        self._session_active = False
        self._auto_run_enabled = os.getenv("AUTO_RUN_MORNING_SESSION", "false").lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        self.premarket = MorningPremarketCoordinator(config, event_bus, container)
        self.research = MorningResearchCoordinator(config, event_bus, container)
        self.trade_ideas = MorningTradeIdeaCoordinator(config, event_bus, container)
        self.safeguards = MorningSafeguardCoordinator(config, event_bus, container)
        self.execution = MorningExecutionCoordinator(config, event_bus, container)

    async def initialize(self) -> None:
        self._log_info("Initializing MorningSessionCoordinator")
        await asyncio.gather(
            self.premarket.initialize(), self.research.initialize(),
            self.trade_ideas.initialize(), self.safeguards.initialize(),
            self.execution.initialize(),
        )
        if self._auto_run_enabled:
            self.event_bus.subscribe(EventType.MARKET_OPEN, self)
            self._log_info("MorningSessionCoordinator auto-run on MARKET_OPEN enabled")
        else:
            self._log_info("MorningSessionCoordinator auto-run on MARKET_OPEN disabled by default")
        self._initialized = True
        self._log_info("MorningSessionCoordinator initialized successfully")

    async def run_morning_session(self, trigger: str = "scheduled") -> MorningSessionResult:
        """Run complete morning autonomous trading session."""
        if not self._initialized:
            raise TradingError("MorningSessionCoordinator not initialized",
                               category=ErrorCategory.SYSTEM, severity=ErrorSeverity.CRITICAL)
        if self._session_active:
            raise TradingError("Morning session already in progress",
                               category=ErrorCategory.SYSTEM, severity=ErrorSeverity.MEDIUM)

        session_id = f"morning_{uuid.uuid4().hex[:12]}"
        start_time = datetime.utcnow()
        result = MorningSessionResult(session_id=session_id, start_time=start_time, end_time=start_time)
        self._session_active = True
        try:
            self._log_info(f"Starting morning session {session_id} (trigger: {trigger})")
            pre_market = await self.premarket.scan_pre_market_data()
            result.pre_market_scanned = len(pre_market)
            to_research = pre_market[:5] if pre_market else []
            research = await self.research.research_stocks(to_research)
            result.stocks_researched = len(to_research)
            ideas = await self.trade_ideas.generate_trade_ideas(research)
            result.trade_ideas_generated = len(ideas)
            approved = await self.safeguards.apply_safeguards(ideas)
            exec_results = await self.execution.execute_trades(approved)
            result.trades_executed = len(exec_results)
            result.total_amount_invested = sum(r.get("amount", 0) for r in exec_results)
            await self.execution.log_session_decisions(session_id, ideas, approved, exec_results)
            result.decisions_logged = len(ideas) + len(approved) + len(exec_results)
            await self._publish_event(EventType.MORNING_SESSION_COMPLETE, {
                "session_id": session_id, "trigger": trigger, "summary": {
                    "scanned": result.pre_market_scanned, "researched": result.stocks_researched,
                    "ideas": result.trade_ideas_generated, "executed": result.trades_executed,
                    "invested": result.total_amount_invested}})
            self._log_info(f"Morning session {session_id} completed successfully")
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            self._log_error(f"Morning session {session_id} failed: {e}", exc_info=True)
            await self._publish_event(EventType.MORNING_SESSION_ERROR,
                                      {"session_id": session_id, "error": str(e)})
        finally:
            result.end_time = datetime.utcnow()
            self._session_active = False
        await self._store_result(result, trigger)
        return result

    async def _publish_event(self, event_type: EventType, data: dict) -> None:
        await self.event_bus.publish(Event(
            id=str(uuid.uuid4()), type=event_type,
            timestamp=datetime.utcnow().isoformat(),
            source="morning_session_coordinator", data=data))

    async def _store_result(self, result: MorningSessionResult, trigger: str) -> None:
        try:
            state = await self.container.get("paper_trading_state")
            dur = int((result.end_time - result.start_time).total_seconds() * 1000)
            await state.store_morning_session(result.session_id, {
                "session_date": result.start_time.date().isoformat(),
                "start_time": result.start_time.isoformat(),
                "end_time": result.end_time.isoformat(),
                "success": result.success, "error_message": result.error_message,
                "metrics": {"pre_market_scanned": result.pre_market_scanned,
                            "stocks_researched": result.stocks_researched,
                            "trade_ideas_generated": result.trade_ideas_generated,
                            "trades_executed": result.trades_executed,
                            "total_amount_invested": result.total_amount_invested,
                            "decisions_logged": result.decisions_logged},
                "pre_market_data": [], "trade_ideas": [], "executed_trades": [],
                "session_context": {"market_open": True, "session_duration_minutes": dur / 60000},
                "trigger_source": str(trigger).upper() if trigger else "MANUAL",
                "total_duration_ms": dur})
        except Exception as e:
            self._log_error(f"Failed to store session result: {e}")

    async def handle_event(self, event: Event) -> None:
        if event.type == EventType.MARKET_OPEN:
            now = datetime.utcnow().time()
            if time(9, 0) <= now <= time(9, 30):
                asyncio.create_task(self.run_morning_session(trigger="market_open"))

    async def cleanup(self) -> None:
        if self._session_active:
            self._log_warning("Morning session active during cleanup")
        if self._auto_run_enabled:
            self.event_bus.unsubscribe(EventType.MARKET_OPEN, self)
        await asyncio.gather(
            self.premarket.cleanup(), self.research.cleanup(),
            self.trade_ideas.cleanup(), self.safeguards.cleanup(),
            self.execution.cleanup())
        self._log_info("MorningSessionCoordinator cleanup complete")
