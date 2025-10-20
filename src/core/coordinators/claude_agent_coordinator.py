"""Claude Agent SDK coordinator for autonomous trading with real tool execution."""

import logging
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from anthropic import Anthropic

from ...models.claude_agent import (
    SessionType, ClaudeSessionResult, StrategyLearning, ToolCall, ToolCallType
)
from ...stores.claude_strategy_store import ClaudeStrategyStore
from ...services.claude_agent.tool_executor import ToolExecutor
from ...services.claude_agent.response_validator import ResponseValidator
from ..event_bus import EventBus, Event, EventType
from ..di import DependencyContainer
from .base_coordinator import BaseCoordinator
from ..errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class ClaudeAgentCoordinator(BaseCoordinator):
    """
    Coordinates Claude Agent SDK autonomous trading sessions.

    Responsibilities:
    - Manage stateful agent sessions (morning prep, evening review)
    - Handle tool execution with safety validation
    - Maintain conversation context
    - Emit events for agent decisions
    """

    def __init__(self, config, event_bus: EventBus, strategy_store: ClaudeStrategyStore,
                 container: DependencyContainer):
        """Initialize coordinator."""
        super().__init__(config, event_bus)
        self.strategy_store = strategy_store
        self.container = container
        self.client: Optional[Anthropic] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.validator: Optional[ResponseValidator] = None
        self._session_history: List[Dict] = []
        self._tools: List[Dict[str, Any]] = []
        self._token_input = 0
        self._token_output = 0

    async def initialize(self) -> None:
        """Initialize Claude Agent SDK coordinator."""
        try:
            self._log_info("Initializing ClaudeAgentCoordinator")

            # Initialize Anthropic client
            api_key = self.config.integration.get("anthropic_api_key")
            if not api_key or api_key == "your_anthropic_api_key_here":
                raise TradingError(
                    "Anthropic API key not configured",
                    category=ErrorCategory.CONFIGURATION,
                    severity=ErrorSeverity.CRITICAL,
                    recoverable=False
                )

            self.client = Anthropic(api_key=api_key)

            # Initialize tool executor and validator
            risk_config = self.config.risk.__dict__ if hasattr(self.config, 'risk') else {}
            self.tool_executor = ToolExecutor(self.container, risk_config)
            await self.tool_executor.register_handlers()

            self.validator = ResponseValidator(risk_config)

            # Register tools
            self._tools = self._build_tool_definitions()

            self._initialized = True
            self._log_info("ClaudeAgentCoordinator initialized successfully")

        except Exception as e:
            self._log_error(f"Failed to initialize ClaudeAgentCoordinator: {e}")
            raise

    async def run_morning_prep_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """
        Execute morning preparation session with multi-turn conversation.

        CRITICAL FIX #1 & #2: Real tool execution + multi-turn support
        - Tool results fed back to Claude for refinement
        - Each tool execution triggers new Claude turn
        - Continues until Claude stops using tools
        """
        if not self.client or not self.tool_executor:
            raise TradingError(
                "Agent not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

        session_id = f"session_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()
        total_input_tokens = 0
        total_output_tokens = 0

        try:
            # Build optimized context
            initial_prompt = self._build_morning_prompt(account_type, context)

            # CRITICAL FIX #4: Enable prompt caching
            messages = [{"role": "user", "content": initial_prompt}]
            system_prompt = [
                {
                    "type": "text",
                    "text": self._build_system_prompt(account_type),
                    "cache_control": {"type": "ephemeral"}  # Cache system prompt
                }
            ]

            tool_calls_history = []
            all_decisions = []
            turn_count = 0
            max_turns = 10  # Prevent infinite loops

            # Multi-turn conversation loop
            while turn_count < max_turns:
                turn_count += 1

                # Call Claude API with tools
                response = self.client.messages.create(
                    model="claude-3-5-sonnet-20250219",
                    max_tokens=4096,
                    system=system_prompt,
                    tools=self._tools,
                    messages=messages
                )

                # Track tokens
                total_input_tokens += response.usage.input_tokens
                total_output_tokens += response.usage.output_tokens

                # Check if Claude wants to use tools
                has_tool_calls = any(block.type == "tool_use" for block in response.content)

                if not has_tool_calls:
                    # Conversation complete
                    logger.info(f"Claude finished trading session after {turn_count} turns")
                    break

                # Add assistant response to conversation
                messages.append({"role": "assistant", "content": response.content})

                # Execute all tool calls from this turn
                tool_results = []

                for content_block in response.content:
                    if content_block.type == "tool_use":
                        # CRITICAL FIX #1: Real tool execution with validation
                        execution_result = await self.tool_executor.execute(
                            tool_name=content_block.name,
                            tool_input=content_block.input
                        )

                        # Track tool call
                        tool_call = ToolCall(
                            tool_name=ToolCallType(content_block.name),
                            input_data=content_block.input,
                            output_data=execution_result.get("output"),
                            error=execution_result.get("error")
                        )
                        tool_calls_history.append(tool_call)

                        all_decisions.append({
                            "tool": content_block.name,
                            "input": content_block.input,
                            "result": execution_result,
                            "turn": turn_count
                        })

                        # Prepare tool result for Claude
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": json.dumps(execution_result)
                        })

                # Add tool results back to conversation
                messages.append({"role": "user", "content": tool_results})

            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Create session result
            session_result = ClaudeSessionResult(
                session_id=session_id,
                session_type=SessionType.MORNING_PREP,
                account_type=account_type,
                context_provided=context,
                claude_response="Multi-turn session completed",
                tool_calls=tool_calls_history,
                decisions_made=all_decisions,
                token_input=total_input_tokens,
                token_output=total_output_tokens,
                total_cost_usd=self._calculate_cost(total_input_tokens, total_output_tokens),
                duration_ms=duration_ms
            )

            # Save session
            await self.strategy_store.save_session(session_result)

            # Emit event
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.AI_RECOMMENDATION,
                source="ClaudeAgentCoordinator",
                data={
                    "session_id": session_id,
                    "session_type": "morning_prep",
                    "turns": turn_count,
                    "tool_calls": len(tool_calls_history),
                    "decisions": len(all_decisions)
                }
            ))

            self._log_info(f"Morning prep session completed: {session_id} ({turn_count} turns, {len(tool_calls_history)} tools)")
            return session_result

        except Exception as e:
            self._log_error(f"Morning prep session failed: {e}")
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.SYSTEM_ERROR,
                source="ClaudeAgentCoordinator",
                data={"error": str(e), "session_id": session_id}
            ))
            raise

    async def run_evening_review_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """
        Execute evening review session with real learning extraction.

        CRITICAL FIX #3: Real learning extraction (not hardcoded)
        """
        if not self.client or not self.validator:
            raise TradingError(
                "Agent not initialized",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

        session_id = f"session_{uuid.uuid4().hex[:16]}"
        start_time = datetime.utcnow()

        try:
            prompt = self._build_evening_prompt(account_type, context)

            # CRITICAL FIX #4: Enable prompt caching for evening session too
            system_prompt = [
                {
                    "type": "text",
                    "text": self._build_system_prompt(account_type),
                    "cache_control": {"type": "ephemeral"}
                }
            ]

            response = self.client.messages.create(
                model="claude-3-5-sonnet-20250219",
                max_tokens=3000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )

            self._token_input += response.usage.input_tokens
            self._token_output += response.usage.output_tokens

            # CRITICAL FIX #3: Use ResponseValidator to extract real learnings
            response_text = response.content[0].text if response.content else ""
            learnings = await self.validator.parse_learnings(response_text)

            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            session_result = ClaudeSessionResult(
                session_id=session_id,
                session_type=SessionType.EVENING_REVIEW,
                account_type=account_type,
                context_provided=context,
                claude_response=response_text,
                tool_calls=[],
                decisions_made=[],
                learnings=learnings,
                token_input=response.usage.input_tokens,
                token_output=response.usage.output_tokens,
                total_cost_usd=self._calculate_cost(response.usage.input_tokens, response.usage.output_tokens),
                duration_ms=duration_ms
            )

            await self.strategy_store.save_session(session_result)

            # Emit learning event
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.AI_LEARNING_UPDATE,
                source="ClaudeAgentCoordinator",
                data={
                    "session_id": session_id,
                    "learnings": learnings.to_dict() if learnings else None
                }
            ))

            self._log_info(f"Evening review session completed: {session_id}")
            return session_result

        except Exception as e:
            self._log_error(f"Evening review session failed: {e}")
            raise

    def _build_tool_definitions(self) -> List[Dict[str, Any]]:
        """Build tool definitions for Claude."""
        return [
            {
                "name": "execute_trade",
                "description": "Execute a paper trade (buy/sell equity or option)",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Stock symbol (e.g., SBIN)"},
                        "action": {"type": "string", "enum": ["buy", "sell"], "description": "Buy or sell"},
                        "quantity": {"type": "integer", "minimum": 1, "description": "Number of shares"},
                        "entry_price": {"type": "number", "minimum": 0, "description": "Entry/exit price"},
                        "strategy_rationale": {"type": "string", "description": "Why this trade?"},
                        "stop_loss": {"type": "number", "description": "Optional stop loss price"},
                        "target_price": {"type": "number", "description": "Optional target price"}
                    },
                    "required": ["symbol", "action", "quantity", "entry_price", "strategy_rationale"]
                }
            },
            {
                "name": "close_position",
                "description": "Close an open trading position",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "trade_id": {"type": "string", "description": "Trade ID to close"},
                        "exit_price": {"type": "number", "minimum": 0, "description": "Exit price"},
                        "reason": {"type": "string", "description": "Reason for closing"}
                    },
                    "required": ["trade_id", "exit_price", "reason"]
                }
            },
            {
                "name": "check_balance",
                "description": "Get current account balance and buying power",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]

    # NOTE: _execute_tool moved to ToolExecutor.execute()
    # Tool execution now happens in ToolExecutor with:
    # - Real validation (three-layer: schema, business rules, safety)
    # - Real execution (PaperTradeExecutor integration)
    # - Circuit breakers and rate limiting
    # - Error recovery with retries
    #
    # See: src/services/claude_agent/tool_executor.py

    def _build_system_prompt(self, account_type: str) -> str:
        """Build system prompt for Claude."""
        return f"""You are RoboTrader, an autonomous trading agent managing a {account_type} trading account.

Your responsibilities:
1. Analyze market conditions and trade setups
2. Execute trades autonomously using available tools
3. Monitor positions and close trades when appropriate
4. Manage risk according to portfolio constraints
5. Learn from previous trading decisions

You have access to trading tools. Use them wisely to execute your trading strategy.

Risk Management Rules:
- Max position size: 5% of portfolio
- Max portfolio risk: 10%
- Stop loss minimum: 2% below entry
- All trades must have clear rationale

Remember: Your decisions will be logged and analyzed. Trade responsibly."""

    def _build_morning_prompt(self, account_type: str, context: Dict[str, Any]) -> str:
        """Build token-optimized morning prompt."""
        return f"""Morning Trading Session - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}

CURRENT STATE:
- Account: {account_type}
- Balance: ₹{context.get('balance', 100000)}
- Buying Power: ₹{context.get('buying_power', 100000)}
- Open Positions: {len(context.get('open_positions', []))}

OPEN POSITIONS:
{json.dumps(context.get('open_positions', [])[:5], indent=2)}

MARKET CONTEXT:
{json.dumps(context.get('market_context', {}), indent=2)}

YOUR TASK:
1. Analyze open positions - should any be closed?
2. Review market opportunities
3. Execute new trades if opportunities exist
4. Use tools to execute your decisions

Think strategically and execute your trades."""

    def _build_evening_prompt(self, account_type: str, context: Dict[str, Any]) -> str:
        """Build evening review prompt."""
        return f"""Evening Strategy Review - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}

TODAY'S PERFORMANCE:
- Trades Executed: {len(context.get('trades_today', []))}
- Daily P&L: ₹{context.get('daily_pnl', 0)}
- Win Rate: {context.get('win_rate', 0)}%

TRADES TODAY:
{json.dumps(context.get('trades_today', [])[:10], indent=2)}

REFLECTION TASKS:
1. What strategies worked well today?
2. What failed and why?
3. What will you adjust for tomorrow?
4. What do you want to research?

Provide detailed insights for continuous improvement."""

    # NOTE: _parse_learnings moved to ResponseValidator.parse_learnings()
    # Learning extraction now uses:
    # - JSON parsing (if Claude returns structured JSON)
    # - Fallback text parsing (if Claude returns natural language)
    # - Multi-layer extraction to handle various formats
    #
    # See: src/services/claude_agent/response_validator.py:parse_learnings()

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API cost."""
        # Claude 3.5 Sonnet pricing
        cost_per_input = 0.000003  # $3 per 1M tokens
        cost_per_output = 0.000015  # $15 per 1M tokens
        return (input_tokens * cost_per_input) + (output_tokens * cost_per_output)

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._log_info("ClaudeAgentCoordinator cleanup")
        self.client = None
        self.tool_executor = None
        self.validator = None
