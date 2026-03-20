"""
Stock Discovery Coordinator

Triggers and manages autonomous stock discovery sessions for paper trading.
Implements PT-002: Autonomous Stock Discovery.
"""

import asyncio
from datetime import datetime, timezone, time
from typing import Dict, Any, Optional
from loguru import logger

from ..base_coordinator import BaseCoordinator
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.models.scheduler import TaskType, QueueName


class StockDiscoveryCoordinator(BaseCoordinator):
    """
    Coordinates autonomous stock discovery for paper trading.

    Features:
    - Daily market screening at market open
    - Sector-focused discovery
    - Event-driven discovery (earnings, news)
    - Integration with StockDiscoveryService
    """

    def __init__(self, config, task_service, stock_discovery_service=None):
        super().__init__(config)
        self.task_service = task_service
        self.stock_discovery_service = stock_discovery_service
        self._discovery_running = False

    async def initialize(self) -> None:
        """Initialize the stock discovery coordinator."""
        try:
            # Get StockDiscoveryService from container if not provided
            if not self.stock_discovery_service:
                from src.core.di import get_container
                container = await get_container()
                self.stock_discovery_service = await container.get("stock_discovery_service")

            # Initialize the service
            await self.stock_discovery_service.initialize()

            self._log_info("StockDiscoveryCoordinator initialized with StockDiscoveryService")

        except Exception as e:
            self._log_error(f"Failed to initialize StockDiscoveryCoordinator: {e}")
            raise TradingError(
                f"Stock discovery coordinator initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def trigger_daily_discovery(self) -> Dict[str, Any]:
        """
        Trigger a daily stock discovery session.

        This is the main entry point for PT-002: Autonomous Stock Discovery.
        Screens the market for high-potential stocks using Perplexity API.
        """
        if self._discovery_running:
            return {
                "success": False,
                "message": "Discovery session already in progress",
                "session_id": None
            }

        try:
            self._discovery_running = True

            # Run discovery using StockDiscoveryService
            result = await self.stock_discovery_service.run_discovery_session(
                session_type="daily_screen",
                custom_criteria={
                    "sectors": [],  # Empty means all sectors
                    "min_market_cap": "small",
                    "max_market_cap": "mega",
                    "exclude_penny_stocks": True,
                    "min_price": 50.0,
                    "max_price": 5000.0
                }
            )

            self._discovery_running = False
            self._log_info(f"Daily stock discovery completed: {result}")

            return {
                "success": True,
                "message": "Daily discovery session completed",
                "session_id": result.get("session_id"),
                "session_type": result.get("session_type"),
                "total_scanned": result.get("total_scanned"),
                "analyzed": result.get("analyzed"),
                "high_potential": result.get("high_potential"),
                "watchlist_updates": result.get("watchlist_updates")
            }

        except Exception as e:
            self._log_error(f"Failed to trigger daily discovery: {e}")
            self._discovery_running = False
            return {
                "success": False,
                "message": f"Failed to trigger discovery: {str(e)}",
                "session_id": None
            }

    async def trigger_sector_discovery(self, sector: str) -> Dict[str, Any]:
        """Trigger sector-focused stock discovery."""
        if self._discovery_running:
            return {
                "success": False,
                "message": "Discovery session already in progress",
                "session_id": None
            }

        try:
            self._discovery_running = True

            session_id = f"sector_discovery_{sector}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

            session_data = {
                "id": session_id,
                "session_date": datetime.now(timezone.utc).strftime('%Y-%m-%d'),
                "session_type": "sector_focus",
                "screening_criteria": {
                    "sectors": [sector],
                    "market_cap_min": 200_000_000,  # Lower threshold for sector focus
                    "volume_min": 500_000,
                    "exclude_penny_stocks": False
                },
                "session_status": "RUNNING"
            }

            await self.task_service.create_task(
                queue_name=QueueName.AI_ANALYSIS,
                task_type=TaskType.STOCK_ANALYSIS,
                payload={
                    "agent_name": "stock_discovery",
                    "session_id": session_id,
                    "session_data": session_data
                },
                priority=2
            )

            self._log_info(f"Sector discovery session queued for {sector}: {session_id}")

            return {
                "success": True,
                "message": f"Sector discovery initiated for {sector}",
                "session_id": session_id,
                "sector": sector
            }

        except Exception as e:
            self._log_error(f"Failed to trigger sector discovery for {sector}: {e}")
            self._discovery_running = False
            return {
                "success": False,
                "message": f"Failed to trigger sector discovery: {str(e)}",
                "session_id": None
            }

    async def get_discovery_status(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of discovery sessions."""
        try:
            if not self.stock_discovery_service:
                return {
                    "status": "not_initialized",
                    "message": "StockDiscoveryService not initialized",
                    "discovery_running": self._discovery_running
                }

            # Get recent discovery sessions
            from src.core.di import get_container
            container = await get_container()
            state_manager = await container.get("state_manager")

            # Get discovery sessions from database
            sessions = await state_manager.paper_trading.get_discovery_sessions(limit=10)

            # Find running session if any
            running_session = None
            completed_sessions = 0
            total_scanned = 0
            total_discovered = 0

            for session in sessions:
                if session.get("session_status") == "RUNNING":
                    running_session = session
                elif session.get("session_status") == "COMPLETED":
                    completed_sessions += 1
                    total_scanned += session.get("total_stocks_scanned", 0)
                    total_discovered += session.get("stocks_discovered", 0)

            return {
                "discovery_running": running_session is not None,
                "current_session": running_session,
                "total_sessions": len(sessions),
                "completed_sessions": completed_sessions,
                "total_stocks_scanned": total_scanned,
                "total_stocks_discovered": total_discovered,
                "recent_sessions": sessions[:5]  # Return 5 most recent sessions
            }

        except Exception as e:
            self._log_error(f"Failed to get discovery status: {e}")
            return {
                "discovery_running": False,
                "error": str(e)
            }

    async def get_discovery_watchlist(self, limit: int = 50) -> Dict[str, Any]:
        """Get the current discovery watchlist."""
        try:
            if not self.stock_discovery_service:
                return {
                    "watchlist": [],
                    "total_stocks": 0,
                    "message": "StockDiscoveryService not initialized"
                }

            # Get watchlist from paper trading state
            from src.core.di import get_container
            container = await get_container()
            state_manager = await container.get("state_manager")

            # Get discovery watchlist from database
            watchlist_items = await state_manager.paper_trading.get_discovery_watchlist(limit=limit)

            # Format response
            watchlist = []
            for item in watchlist_items:
                watchlist.append({
                    "symbol": item.get("symbol"),
                    "company_name": item.get("company_name"),
                    "sector": item.get("sector"),
                    "recommendation": item.get("recommendation"),
                    "confidence_score": item.get("confidence_score"),
                    "discovery_date": item.get("discovery_date"),
                    "current_price": item.get("current_price"),
                    "status": item.get("status"),
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at")
                })

            return {
                "watchlist": watchlist,
                "total_stocks": len(watchlist)
            }

        except Exception as e:
            self._log_error(f"Failed to get discovery watchlist: {e}")
            return {
                "watchlist": [],
                "total_stocks": 0,
                "error": str(e)
            }

    # Event Handlers

    async def _handle_market_open(self, event) -> None:
        """Handle market open event to trigger daily discovery."""
        try:
            self._log_info("Market open detected - triggering daily stock discovery")
            await self.trigger_daily_discovery()
        except Exception as e:
            self._log_error(f"Failed to handle market open event: {e}")

    async def _handle_discovery_trigger(self, event) -> None:
        """Handle manual discovery trigger event."""
        try:
            discovery_type = event.data.get("type", "daily")
            sector = event.data.get("sector")

            if discovery_type == "sector" and sector:
                await self.trigger_sector_discovery(sector)
            else:
                await self.trigger_daily_discovery()

        except Exception as e:
            self._log_error(f"Failed to handle discovery trigger event: {e}")

    async def handle_discovery_complete(self, session_id: str, results: Optional[Dict[str, Any]] = None) -> None:
        """Handle completion of a discovery session."""
        try:
            self._discovery_running = False

            stocks_discovered = results.get("stocks_discovered", 0) if results else 0
            high_potential = results.get("high_potential_stocks", 0) if results else 0

            self._log_info(
                f"Discovery session {session_id} completed: "
                f"{stocks_discovered} stocks discovered, "
                f"{high_potential} high potential"
            )

            # Emit event for other components
            await self.event_bus.publish(
                "stock_discovery_complete",
                {
                    "session_id": session_id,
                    "stocks_discovered": stocks_discovered,
                    "high_potential": high_potential
                }
            )

        except Exception as e:
            self._log_error(f"Failed to handle discovery completion: {e}")
            self._discovery_running = False

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        try:
            if self.event_bus:
                await self.event_bus.unsubscribe("market_open", self._handle_market_open)
                await self.event_bus.unsubscribe("trigger_stock_discovery", self._handle_discovery_trigger)

            self._log_info("StockDiscoveryCoordinator cleaned up")

        except Exception as e:
            self._log_error(f"Failed to cleanup StockDiscoveryCoordinator: {e}")