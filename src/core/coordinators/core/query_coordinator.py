"""
Query Coordinator (Refactored)

Thin orchestrator that delegates to focused query coordinators.
Refactored from 210-line monolith into focused coordinators.
"""

import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from loguru import logger

from src.config import Config
from ..base_coordinator import BaseCoordinator
from .session_coordinator import SessionCoordinator
from .query_processing_coordinator import QueryProcessingCoordinator


class QueryCoordinator(BaseCoordinator):
    """
    Coordinates query processing and AI responses.

    Responsibilities:
    - Orchestrate query operations from focused coordinators
    - Provide unified query API
    - Handle market alerts
    """

    def __init__(
        self,
        config: Config,
        session_coordinator: SessionCoordinator
    ):
        super().__init__(config)
        self.session_coordinator = session_coordinator
        
        # Focused coordinator
        self.processing_coordinator = QueryProcessingCoordinator(config)

    async def initialize(self) -> None:
        """Initialize query coordinator."""
        self._log_info("Initializing QueryCoordinator")
        
        await self.processing_coordinator.initialize()
        
        self._initialized = True

    async def process_query(self, query: str) -> List[Any]:
        """
        Process a user query and return responses.

        Args:
            query: User query string

        Returns:
            List of response blocks
        """
        client = self.session_coordinator.get_client()
        return await self.processing_coordinator.process_query(client, query)

    async def process_query_enhanced(self, query: str) -> Dict[str, Any]:
        """
        Process query with proper streaming and progressive updates.

        Args:
            query: User query string

        Returns:
            Dict with thinking, tool_uses, results, and optional error
        """
        client = self.session_coordinator.get_client()
        return await self.processing_coordinator.process_query_enhanced(client, query)

    async def handle_market_alert(
        self,
        symbol: str,
        alert_type: str,
        data: Dict[str, Any]
    ) -> List[Any]:
        """
        Handle real-time market alerts.

        Args:
            symbol: Stock symbol
            alert_type: Type of alert
            data: Alert data

        Returns:
            List of AI responses
        """
        query = f"""
        Market alert received for {symbol}:
        Type: {alert_type}
        Data: {json.dumps(data)}

        Evaluate the alert and determine if action is needed:
        1. Check current position in {symbol}
        2. Assess technical indicators
        3. Evaluate risk implications
        4. Suggest appropriate response (hold, adjust stops, exit, etc.)
        """

        responses = await self.process_query(query)
        self._log_info(f"Market alert handled for {symbol} with {len(responses)} responses")
        return responses

    async def cleanup(self) -> None:
        """Cleanup query coordinator resources."""
        await self.processing_coordinator.cleanup()
        self._log_info("QueryCoordinator cleanup complete")
