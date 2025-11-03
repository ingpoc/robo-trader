"""
Agent Session Coordinator (Refactored)

Thin orchestrator that delegates to focused session coordinators.
Refactored from 256-line monolith into focused coordinators.
"""

from typing import Dict, Any

from src.config import Config
from src.models.claude_agent import SessionType, ClaudeSessionResult
from src.stores.claude_strategy_store import ClaudeStrategyStore
from src.services.claude_agent.tool_executor import ToolExecutor
from src.services.claude_agent.response_validator import ResponseValidator
from ....event_bus import EventBus
from ...base_coordinator import BaseCoordinator
from .morning_session_coordinator import MorningSessionCoordinator
from .evening_session_coordinator import EveningSessionCoordinator


class AgentSessionCoordinator(BaseCoordinator):
    """
    Coordinates Claude agent session lifecycle.
    
    Responsibilities:
    - Orchestrate session operations from focused coordinators
    - Provide unified session API
    """
    
    def __init__(
        self,
        config: Config,
        event_bus: EventBus,
        strategy_store: ClaudeStrategyStore,
        tool_executor: ToolExecutor,
        validator: ResponseValidator,
        client = None,
        prompt_builder = None
    ):
        super().__init__(config)
        self.strategy_store = strategy_store
        self.tool_executor = tool_executor
        self.validator = validator
        self.client = client
        self._prompt_builder = prompt_builder
        
        # Focused coordinators
        self.morning_coordinator = MorningSessionCoordinator(
            config, event_bus, strategy_store, tool_executor, validator, client, prompt_builder
        )
        self.evening_coordinator = EveningSessionCoordinator(
            config, event_bus, strategy_store, tool_executor, validator, client, prompt_builder
        )
    
    async def initialize(self) -> None:
        """Initialize agent session coordinator."""
        self._log_info("Initializing AgentSessionCoordinator")
        
        await self.morning_coordinator.initialize()
        await self.evening_coordinator.initialize()
        
        self._initialized = True
    
    def set_client(self, client) -> None:
        """Set Claude SDK client."""
        self.client = client
        self.morning_coordinator.set_client(client)
        self.evening_coordinator.set_client(client)
    
    def set_prompt_builder(self, prompt_builder) -> None:
        """Set prompt builder."""
        self._prompt_builder = prompt_builder
        self.morning_coordinator.set_prompt_builder(prompt_builder)
        self.evening_coordinator.set_prompt_builder(prompt_builder)
    
    async def run_morning_prep_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """Execute morning preparation session."""
        return await self.morning_coordinator.run_morning_prep_session(account_type, context)
    
    async def run_evening_review_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """Execute evening review session."""
        return await self.evening_coordinator.run_evening_review_session(account_type, context)
    
    async def cleanup(self) -> None:
        """Cleanup agent session coordinator resources."""
        await self.morning_coordinator.cleanup()
        await self.evening_coordinator.cleanup()
        self._log_info("AgentSessionCoordinator cleanup complete")

