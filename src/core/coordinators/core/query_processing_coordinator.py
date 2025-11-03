"""
Query Processing Coordinator

Focused coordinator for query processing logic.
Extracted from QueryCoordinator for single responsibility.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

from claude_agent_sdk import (
    AssistantMessage,
    TextBlock,
    ToolUseBlock,
    ToolResultBlock
)
from loguru import logger

from src.config import Config
from ..base_coordinator import BaseCoordinator
from ...sdk_helpers import query_only_with_timeout, query_with_timeout, receive_response_with_timeout


class QueryProcessingCoordinator(BaseCoordinator):
    """
    Coordinates query processing logic.
    
    Responsibilities:
    - Process user queries
    - Handle streaming responses
    - Parse AI thinking, tool usage, and results
    """

    def __init__(self, config: Config):
        super().__init__(config)

    async def initialize(self) -> None:
        """Initialize query processing coordinator."""
        self._log_info("Initializing QueryProcessingCoordinator")
        self._initialized = True

    async def process_query(self, client, query: str) -> List[Any]:
        """
        Process a user query and return responses.

        Args:
            client: Claude SDK client
            query: User query string

        Returns:
            List of response blocks
        """
        if not client:
            self._log_warning("Claude client not available - cannot process query")
            return [{
                "type": "error",
                "message": "AI assistant is not available. Please check Claude authentication.",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]

        try:
            # Send query with timeout protection
            await query_only_with_timeout(client, query, timeout=30.0)
            
            # Receive responses with timeout helper
            responses = []
            async for response in receive_response_with_timeout(client, timeout=60.0):
                responses.append(response)

            return responses

        except Exception as e:
            self._log_error(f"Error processing query: {e}", exc_info=True)
            return [{
                "type": "error",
                "message": f"Failed to process query: {str(e)}",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }]

    async def process_query_enhanced(self, client, query: str) -> Dict[str, Any]:
        """
        Process query with proper streaming and progressive updates.

        Args:
            client: Claude SDK client
            query: User query string

        Returns:
            Dict with thinking, tool_uses, results, and optional error
        """
        try:
            if not client:
                self._log_warning("Claude client not available - cannot process enhanced query")
                return {
                    "thinking": [],
                    "tool_uses": [],
                    "results": [],
                    "error": "AI assistant is not available. Please check Claude authentication."
                }

            # Send query with timeout protection
            await query_with_timeout(client, query, timeout=60.0)

            thinking_content = []
            tool_uses = []
            results = []

            # Receive responses with timeout helper
            async for message in receive_response_with_timeout(client, timeout=120.0):
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

    async def cleanup(self) -> None:
        """Cleanup query processing coordinator resources."""
        self._log_info("QueryProcessingCoordinator cleanup complete")

