"""
Portfolio Status Coordinator

Focused coordinator for portfolio status.
Extracted from StatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from src.config import Config
from ...database_state.database_state import DatabaseStateManager
from ..base_coordinator import BaseCoordinator


class PortfolioStatusCoordinator(BaseCoordinator):
    """
    Coordinates portfolio status.
    
    Responsibilities:
    - Get portfolio status
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager
    ):
        super().__init__(config)
        self.state_manager = state_manager

    async def initialize(self) -> None:
        """Initialize portfolio status coordinator."""
        self._log_info("Initializing PortfolioStatusCoordinator")
        self._initialized = True

    async def get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio health status."""
        try:
            portfolio = await self.state_manager.get_portfolio()
            if portfolio:
                return {
                    "holdings_count": len(portfolio.holdings),
                    "total_value": portfolio.exposure_total,
                    "last_updated": getattr(portfolio, 'last_updated', None)
                }
            return {"status": "no_portfolio"}
        except Exception:
            return {"status": "error"}

    async def cleanup(self) -> None:
        """Cleanup portfolio status coordinator resources."""
        self._log_info("PortfolioStatusCoordinator cleanup complete")

