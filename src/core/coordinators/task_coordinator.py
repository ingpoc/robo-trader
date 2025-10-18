"""
Task Coordinator

Manages analytics tasks including portfolio scans, market screening,
and recommendation generation.
Extracted from RoboTraderOrchestrator lines 462-573.
"""

from datetime import datetime, timezone
from typing import Dict, Any

from loguru import logger

from ...config import Config
from ...core.database_state import DatabaseStateManager
from ...services.analytics import (
    run_portfolio_scan as analytics_run_portfolio_scan,
    run_market_screening as analytics_run_market_screening,
    run_strategy_analysis,
)
from .base_coordinator import BaseCoordinator


class TaskCoordinator(BaseCoordinator):
    """
    Coordinates analytics and background tasks.

    Responsibilities:
    - Run portfolio scans
    - Execute market screening
    - Run strategy reviews
    - Generate recommendations from scan results
    """

    def __init__(
        self,
        config: Config,
        state_manager: DatabaseStateManager
    ):
        super().__init__(config)
        self.state_manager = state_manager

    async def initialize(self) -> None:
        """Initialize task coordinator."""
        self._log_info("Initializing TaskCoordinator")
        self._initialized = True

    async def run_portfolio_scan(self) -> Dict[str, Any]:
        """Run a portfolio scan using live portfolio data."""
        results = await analytics_run_portfolio_scan(self.config, self.state_manager)
        holdings_count = len(results["portfolio"]["holdings"])
        self._log_info(
            f"Portfolio scan completed from {results['source']} with {holdings_count} holdings"
        )

        await self._generate_recommendations_from_scan(results)

        return results

    async def run_market_screening(self) -> Dict[str, Any]:
        """Run market screening using current holdings analytics."""
        results = await analytics_run_market_screening(self.config, self.state_manager)
        momentum_count = len(results["screening"]["momentum"])
        self._log_info(
            f"Market screening completed from {results['source']} with {momentum_count} momentum candidates"
        )
        return results

    async def run_strategy_review(self) -> Dict[str, Any]:
        """Run strategy review to derive actionable rebalance suggestions."""
        results = await run_strategy_analysis(self.config, self.state_manager)
        actions_count = len(results["strategy"]["actions"])
        self._log_info(
            f"Strategy review completed from {results['source']} with {actions_count} recommended actions"
        )
        return results

    async def _generate_recommendations_from_scan(self, scan_results: Dict[str, Any]) -> None:
        """Generate AI recommendations from portfolio scan results."""
        try:
            portfolio = scan_results.get("portfolio", {})
            holdings = portfolio.get("holdings", [])

            if not holdings:
                self._log_info("No holdings to generate recommendations for")
                return

            for holding in holdings:
                symbol = holding.get("symbol", "")
                if not symbol:
                    continue

                pnl_pct = holding.get("pnl_pct", 0)
                exposure = holding.get("exposure", 0)
                exposure_total = portfolio.get("exposure_total", 1)
                exposure_pct = (exposure / exposure_total) * 100 if exposure_total > 0 else 0

                recommendation = None

                if pnl_pct < -15:
                    recommendation = {
                        "symbol": symbol,
                        "action": "SELL",
                        "confidence": 75,
                        "reasoning": f"Stock down {pnl_pct:.1f}%. Consider cutting losses.",
                        "analysis_type": "risk_management",
                        "current_price": holding.get("last_price"),
                        "stop_loss": holding.get("avg_price", 0) * 0.92,
                        "quantity": holding.get("qty"),
                        "potential_impact": f"Stop loss triggered at {pnl_pct:.1f}%",
                        "risk_level": "high",
                        "time_horizon": "immediate"
                    }
                elif pnl_pct > 25:
                    recommendation = {
                        "symbol": symbol,
                        "action": "BOOK_PROFIT",
                        "confidence": 70,
                        "reasoning": f"Stock up {pnl_pct:.1f}%. Consider booking partial profits.",
                        "analysis_type": "profit_taking",
                        "current_price": holding.get("last_price"),
                        "target_price": holding.get("last_price", 0) * 1.1,
                        "stop_loss": holding.get("last_price", 0) * 0.95,
                        "quantity": int(holding.get("qty", 0) / 2),
                        "potential_impact": f"Lock in {pnl_pct/2:.1f}% profit on half position",
                        "risk_level": "low",
                        "time_horizon": "short_term"
                    }
                elif exposure_pct > 10:
                    recommendation = {
                        "symbol": symbol,
                        "action": "REDUCE",
                        "confidence": 65,
                        "reasoning": f"Position is {exposure_pct:.1f}% of portfolio. Reduce concentration risk.",
                        "analysis_type": "risk_management",
                        "current_price": holding.get("last_price"),
                        "quantity": int(holding.get("qty", 0) * 0.3),
                        "potential_impact": f"Reduce from {exposure_pct:.1f}% to {exposure_pct*0.7:.1f}%",
                        "risk_level": "medium",
                        "time_horizon": "medium_term"
                    }

                if recommendation:
                    await self.state_manager.add_to_approval_queue(recommendation)
                    self._log_info(f"Generated {recommendation['action']} recommendation for {symbol}")

        except Exception as e:
            self._log_error(f"Failed to generate recommendations: {e}", exc_info=True)

    async def cleanup(self) -> None:
        """Cleanup task coordinator resources."""
        self._log_info("TaskCoordinator cleanup complete")
