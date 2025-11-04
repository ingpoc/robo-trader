"""
Morning Session Coordinator

Focused coordinator for morning preparation sessions.
Extracted from AgentSessionCoordinator for single responsibility.
"""

import uuid
from datetime import datetime
from typing import Dict, Any

from claude_agent_sdk import ClaudeSDKError

from src.config import Config
from src.models.claude_agent import SessionType, ClaudeSessionResult, ToolCall, ToolCallType
from src.stores.claude_strategy_store import ClaudeStrategyStore
from src.services.claude_agent.tool_executor import ToolExecutor
from src.services.claude_agent.response_validator import ResponseValidator
from ....event_bus import EventBus
from ...base_coordinator import BaseCoordinator


class MorningSessionCoordinator(BaseCoordinator):
    """
    Coordinates morning preparation sessions.
    
    Responsibilities:
    - Run morning prep sessions
    - Handle morning session state
    - Process morning tool calls
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
    
    async def initialize(self) -> None:
        """Initialize morning session coordinator."""
        self._log_info("Initializing MorningSessionCoordinator")
        self._initialized = True
    
    def set_client(self, client) -> None:
        """Set Claude SDK client."""
        self.client = client
    
    def set_prompt_builder(self, prompt_builder) -> None:
        """Set prompt builder."""
        self._prompt_builder = prompt_builder
    
    async def run_morning_prep_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """Execute morning preparation session using Claude SDK."""
        if not self.client or not self.tool_executor:
            raise TradingError(
                "Agent not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )
        
        session_id = f"session_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()
        
        try:
            prompt = self._prompt_builder.build_morning_prompt(account_type, context) if self._prompt_builder else ""
            await query_with_timeout(self.client, prompt, timeout=90.0)
            
            tool_calls_history = []
            all_decisions = []
            claude_responses = []
            total_input_tokens = 0
            total_output_tokens = 0
            
            async for response in receive_response_with_timeout(self.client, timeout=180.0):
                claude_responses, tokens = self._process_response(response, tool_calls_history)
                if claude_responses:
                    claude_responses.extend(claude_responses)
                total_input_tokens += tokens[0]
                total_output_tokens += tokens[1]
                
                if hasattr(response, 'decisions'):
                    all_decisions.extend(response.decisions)
            
            end_time = datetime.utcnow()
            
            result = ClaudeSessionResult(
                session_id=session_id,
                session_type=SessionType.MORNING_PREP,
                success=True,
                tool_calls=tool_calls_history,
                decisions=all_decisions,
                claude_responses=claude_responses,
                start_time=start_time,
                end_time=end_time,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens
            )
            
            await self.validator.validate_session_result(result)
            await self.strategy_store.save_session(result)
            
            await self.event_bus.publish(Event(
                event_type=EventType.TASK_COMPLETED,
                data={"session_id": session_id, "session_type": SessionType.MORNING_PREP.value},
                source="morning_session_coordinator"
            ))
            
            return result
            
        except ClaudeSDKError as e:
            self._log_error(f"Claude SDK error in morning session: {e}", exc_info=True)
            raise TradingError(
                f"Morning session failed: {e}",
                category=ErrorCategory.INTEGRATION,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )
        except Exception as e:
            self._log_error(f"Error in morning session: {e}", exc_info=True)
            raise TradingError(
                f"Morning session failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )
    
    async def _process_response(self, response, tool_calls_history):
        """Process a single response and update tool calls history."""
        claude_responses = []
        tokens = [0, 0]
        
        if hasattr(response, 'content'):
            claude_responses.append(str(response.content))
        
        if hasattr(response, 'tool_calls'):
            for tool_call in response.tool_calls:
                tool_call_record = ToolCall(
                    tool_name=ToolCallType(tool_call.name.replace("mcp__trading__", "")),
                    input_data=tool_call.input,
                    output_data=None,
                    timestamp=datetime.utcnow()
                )
                
                result = await self.tool_executor.execute_tool(tool_call.name, tool_call.input)
                tool_call_record.output_data = result
                tool_calls_history.append(tool_call_record)
        
        if hasattr(response, 'input_tokens'):
            tokens[0] = response.input_tokens or 0
        if hasattr(response, 'output_tokens'):
            tokens[1] = response.output_tokens or 0
        
        return claude_responses, tokens
    
    async def cleanup(self) -> None:
        """Cleanup morning session coordinator resources."""
        self._log_info("MorningSessionCoordinator cleanup complete")

