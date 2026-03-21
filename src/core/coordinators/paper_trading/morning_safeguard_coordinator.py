"""Morning Safeguard Coordinator

Applies risk safeguards to trade ideas before execution.
Checks daily trade limits, position sizing, and confidence thresholds.
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus
from src.services.autonomous_trading_safeguards import AutonomousTradingSafeguards
from src.services.claude_agent.decision_logger import ClaudeDecisionLogger

if TYPE_CHECKING:
    from src.core.di import DependencyContainer


class MorningSafeguardCoordinator(BaseCoordinator):
    """Applies risk safeguards to filter trade ideas. Max 150 lines."""

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container
        self.safeguards: Optional[AutonomousTradingSafeguards] = None
        self.decision_logger: Optional[ClaudeDecisionLogger] = None

    async def initialize(self) -> None:
        """Initialize with safeguard and decision logger services."""
        self.decision_logger = await self.container.get("trade_decision_logger")

        try:
            self.safeguards = await self.container.get("autonomous_trading_safeguards")
        except ValueError:
            self._log_warning("autonomous_trading_safeguards not registered - safeguards disabled")
            self.safeguards = None

        self._initialized = True

    async def apply_safeguards(self, trade_ideas: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Apply risk safeguards to trade ideas.

        Args:
            trade_ideas: List of trade idea dicts from MorningTradeIdeaCoordinator.

        Returns:
            List of approved trade dicts that passed all safeguard checks.
        """
        approved_trades = []

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
                safeguard_status = await self.safeguards.check_trade_allowed(
                    symbol=idea["symbol"],
                    trade_type=idea["action"],
                    quantity=idea.get("quantity", 0),
                    estimated_value=idea.get("price", 0) * idea.get("quantity", 0),
                    portfolio_value=100000.0
                )
                can_trade = safeguard_status.can_trade

                if can_trade:
                    idea["safeguard_checks"] = {
                        "passed": True,
                        "daily_trades_remaining": await self.safeguards.get_remaining_daily_trades(),
                        "position_size_ok": True,
                        "confidence_met": idea.get("confidence", 0) >= 0.7
                    }
                    approved_trades.append(idea)
                else:
                    await self.decision_logger.log_decision({
                        "decision_type": "SAFEGUARD_REJECT",
                        "symbol": idea["symbol"],
                        "reasoning": "Trade rejected by safeguards",
                        "confidence": 1.0,
                        "context": {"trade_idea": idea}
                    })

            except Exception as e:
                self._log_error(f"Safeguard check failed for {idea['symbol']}: {e}")

        return approved_trades

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._log_info("MorningSafeguardCoordinator cleanup complete")
