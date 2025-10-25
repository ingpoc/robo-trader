"""
Query Coordinator

Processes user queries and manages Claude SDK query/response flow.
Extracted from RoboTraderOrchestrator lines 281-317, 320-385, 575-590.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional

from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock
)
from loguru import logger

from src.config import Config
from .base_coordinator import BaseCoordinator
from .session_coordinator import SessionCoordinator


class QueryCoordinator(BaseCoordinator):
    """
    Coordinates query processing and AI responses.

    Responsibilities:
    - Process user queries
    - Handle streaming responses
    - Parse AI thinking, tool usage, and results
    - Handle market alerts
    """

    def __init__(
        self,
        config: Config,
        session_coordinator: SessionCoordinator
    ):
        super().__init__(config)
        self.session_coordinator = session_coordinator

    async def initialize(self) -> None:
        """Initialize query coordinator."""
        self._log_info("Initializing QueryCoordinator")
        self._initialized = True

    async def process_query(self, query: str) -> List[Any]:
        """
        Process a user query and return responses.

        For single queries, prefer using session() context manager.
        This method is for applications with persistent sessions.

        Args:
            query: User query string

        Returns:
            List of response blocks
        """
        client = self.session_coordinator.get_client()

        if not client:
            self._log_warning("Claude client not available - cannot process query")
            return [{
                "type": "error",
                "message": "AI assistant is not available. Please check Claude authentication.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]

        try:
            await asyncio.wait_for(client.query(query), timeout=30.0)

            responses = []
            async for response in client.receive_response():
                responses.append(response)

            return responses

        except asyncio.TimeoutError:
            self._log_error(f"Query timed out after 30 seconds: {query[:100]}...")
            return [{
                "type": "error",
                "message": "Query timed out. Please try again or simplify your request.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]
        except Exception as e:
            self._log_error(f"Error processing query: {e}", exc_info=True)
            return [{
                "type": "error",
                "message": f"Failed to process query: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]

    async def process_query_enhanced(self, query: str) -> Dict[str, Any]:
        """
        Process query with proper streaming and progressive updates.

        Returns structured response with thinking, tool usage, and results.

        Args:
            query: User query string

        Returns:
            Dict with thinking, tool_uses, results, and optional error
        """
        client = self.session_coordinator.get_client()

        try:
            if not client:
                self._log_warning("Claude client not available - cannot process enhanced query")
                return {
                    "thinking": [],
                    "tool_uses": [],
                    "results": [],
                    "error": "AI assistant is not available. Please check Claude authentication."
                }

            await client.query(query)

            thinking_content = []
            tool_uses = []
            results = []

            async for message in client.receive_response():
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            thinking_content.append(block.text)
                            self._log_info(f"AI Thinking: {block.text[:100]}...")
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append({
                                "id": block.id,
                                "name": block.name,
                                "status": "executing"
                            })
                            self._log_info(f"Tool Use: {block.name}")
                        elif isinstance(block, ToolResultBlock):
                            tool_uses.append({
                                "id": block.tool_use_id,
                                "name": "tool_result",
                                "status": "completed",
                                "result": block.content,
                                "is_error": block.is_error
                            })
                            results.append({
                                "tool_use_id": block.tool_use_id,
                                "content": block.content,
                                "is_error": block.is_error
                            })
                            status = 'error' if block.is_error else 'success'
                            self._log_info(f"Tool Result: {block.tool_use_id} - {status}")

            return {
                "thinking": thinking_content,
                "tool_uses": tool_uses,
                "results": results
            }

        except Exception as e:
            self._log_error(f"Error in enhanced query processing: {e}", exc_info=True)
            return {
                "thinking": [],
                "tool_uses": [],
                "results": [],
                "error": f"Query processing failed: {str(e)}"
            }

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
        self._log_info("QueryCoordinator cleanup complete")
