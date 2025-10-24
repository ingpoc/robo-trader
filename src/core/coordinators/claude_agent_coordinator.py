"""Claude Agent SDK coordinator for autonomous trading with real tool execution."""

import logging
import uuid
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# Claude Agent SDK imports only - no direct Anthropic API
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
    ClaudeSDKError,
    CLINotFoundError,
    ProcessError,
    CLIJSONDecodeError
)

from ...models.claude_agent import (
    SessionType, ClaudeSessionResult, StrategyLearning, ToolCall, ToolCallType
)
from ...stores.claude_strategy_store import ClaudeStrategyStore
from ...services.claude_agent.tool_executor import ToolExecutor
from ...services.claude_agent.response_validator import ResponseValidator
from ..event_bus import EventBus, Event, EventType
from typing import TYPE_CHECKING
if TYPE_CHECKING:
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
                 container: "DependencyContainer"):
        """Initialize coordinator."""
        super().__init__(config, event_bus)
        self.strategy_store = strategy_store
        self.container = container
        self.client: Optional[ClaudeSDKClient] = None  # SDK client only
        self.mcp_server = None  # MCP server for tools
        self.tool_executor: Optional[ToolExecutor] = None
        self.validator: Optional[ResponseValidator] = None
        self._session_history: List[Dict] = []
        self._tools: List[Dict[str, Any]] = []
        self._token_input = 0
        self._token_output = 0

    async def initialize(self) -> None:
        """Initialize Claude Agent SDK coordinator with proper MCP server pattern."""
        try:
            self._log_info("Initializing ClaudeAgentCoordinator with SDK")

            # Create MCP server with tool functions (SDK best practice)
            @tool("execute_trade", "Execute a paper trade (buy/sell equity or option)", {
                "symbol": str, "action": str, "quantity": int, "entry_price": float, "strategy_rationale": str,
                "stop_loss": float, "target_price": float
            })
            async def execute_trade_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Execute trade tool for SDK."""
                try:
                    result = await self.tool_executor.execute("execute_trade", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Trade execution failed: {str(e)}"}],
                        "is_error": True
                    }

            @tool("close_position", "Close an open trading position", {
                "trade_id": str, "exit_price": float, "reason": str
            })
            async def close_position_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Close position tool for SDK."""
                try:
                    result = await self.tool_executor.execute("close_position", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Position close failed: {str(e)}"}],
                        "is_error": True
                    }

            @tool("check_balance", "Get current account balance and buying power", {})
            async def check_balance_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Check balance tool for SDK."""
                try:
                    result = await self.tool_executor.execute("check_balance", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Balance check failed: {str(e)}"}],
                        "is_error": True
                    }

            @tool("get_market_data", "Get current market data for a symbol", {"symbol": str})
            async def get_market_data_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Get market data tool for SDK."""
                try:
                    result = await self.tool_executor.execute("get_market_data", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Market data fetch failed: {str(e)}"}],
                        "is_error": True
                    }

            @tool("analyze_portfolio", "Analyze current portfolio composition and risk", {})
            async def analyze_portfolio_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Analyze portfolio tool for SDK."""
                try:
                    result = await self.tool_executor.execute("analyze_portfolio", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Portfolio analysis failed: {str(e)}"}],
                        "is_error": True
                    }

            @tool("get_open_positions", "Get all currently open trading positions", {})
            async def get_open_positions_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Get open positions tool for SDK."""
                try:
                    result = await self.tool_executor.execute("get_open_positions", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Open positions fetch failed: {str(e)}"}],
                        "is_error": True
                    }

            @tool("calculate_risk_metrics", "Calculate portfolio risk metrics", {})
            async def calculate_risk_metrics_tool(args: Dict[str, Any]) -> Dict[str, Any]:
                """Calculate risk metrics tool for SDK."""
                try:
                    result = await self.tool_executor.execute("calculate_risk_metrics", args)
                    return {
                        "content": [{"type": "text", "text": json.dumps(result)}]
                    }
                except Exception as e:
                    return {
                        "content": [{"type": "text", "text": f"Risk metrics calculation failed: {str(e)}"}],
                        "is_error": True
                    }

            # Create MCP server with all tools
            self.mcp_server = create_sdk_mcp_server(
                name="trading_tools",
                version="1.0.0",
                tools=[
                    execute_trade_tool,
                    close_position_tool,
                    check_balance_tool,
                    get_market_data_tool,
                    analyze_portfolio_tool,
                    get_open_positions_tool,
                    calculate_risk_metrics_tool
                ]
            )

            # Configure SDK options (SDK best practice)
            options = ClaudeAgentOptions(
                mcp_servers={"trading": self.mcp_server},
                allowed_tools=[
                    "mcp__trading__execute_trade",
                    "mcp__trading__close_position",
                    "mcp__trading__check_balance",
                    "mcp__trading__get_market_data",
                    "mcp__trading__analyze_portfolio",
                    "mcp__trading__get_open_positions",
                    "mcp__trading__calculate_risk_metrics"
                ],
                system_prompt=self._build_system_prompt("swing_trading"),
                max_turns=20
            )

            # Initialize SDK client
            self.client = ClaudeSDKClient(options=options)
            await self.client.__aenter__()

            # Initialize tool executor and validator
            risk_config = self.config.risk.__dict__ if hasattr(self.config, 'risk') else {}
            self.tool_executor = ToolExecutor(self.container, risk_config)
            await self.tool_executor.register_handlers()

            self.validator = ResponseValidator(risk_config)

            self._initialized = True
            self._log_info("ClaudeAgentCoordinator initialized successfully with SDK MCP server")

        except CLINotFoundError:
            self._log_error("Claude Code CLI not found. Please install Claude Code to use AI trading features.")
            raise TradingError(
                "Claude Code CLI not installed",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )
        except ClaudeSDKError as e:
            self._log_error(f"SDK initialization failed: {e}")
            raise TradingError(
                f"Claude SDK initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )
        except Exception as e:
            self._log_error(f"Failed to initialize ClaudeAgentCoordinator: {e}")
            raise

    async def run_morning_prep_session(
        self,
        account_type: str,
        context: Dict[str, Any]
    ) -> ClaudeSessionResult:
        """
        Execute morning preparation session using Claude SDK query pattern.

        SDK Best Practice: Use client.query() and client.receive_response() pattern
        - Tool results are automatically fed back by SDK
        - Multi-turn conversations handled by SDK
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

        try:
            # Build optimized context
            prompt = self._build_morning_prompt(account_type, context)

            # SDK query pattern (best practice)
            await self.client.query(prompt)

            # Collect responses and tool calls
            tool_calls_history = []
            all_decisions = []
            claude_responses = []
            total_input_tokens = 0
            total_output_tokens = 0

            # Process SDK responses
            async for response in self.client.receive_response():
                # Track response content
                if hasattr(response, 'content'):
                    claude_responses.append(str(response.content))

                # Track tool calls made by Claude
                if hasattr(response, 'tool_calls'):
                    for tool_call in response.tool_calls:
                        # SDK automatically executes tools and feeds results back
                        # We just track what happened
                        tool_call_record = ToolCall(
                            tool_name=ToolCallType(tool_call.name.replace("mcp__trading__", "")),
                            input_data=tool_call.input,
                            output_data=None,  # SDK handles execution
                            error=None
                        )
                        tool_calls_history.append(tool_call_record)

                        all_decisions.append({
                            "tool": tool_call.name,
                            "input": tool_call.input,
                            "result": "executed_by_sdk",
                            "turn": len(all_decisions) + 1
                        })

                # Track token usage if available
                if hasattr(response, 'usage'):
                    total_input_tokens += getattr(response.usage, 'input_tokens', 0)
                    total_output_tokens += getattr(response.usage, 'output_tokens', 0)

            # Calculate duration
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Create session result
            session_result = ClaudeSessionResult(
                session_id=session_id,
                session_type=SessionType.MORNING_PREP,
                account_type=account_type,
                context_provided=context,
                claude_response=" ".join(claude_responses) if claude_responses else "SDK session completed",
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
                    "turns": len(all_decisions),
                    "tool_calls": len(tool_calls_history),
                    "decisions": len(all_decisions)
                }
            ))

            self._log_info(f"Morning prep session completed: {session_id} ({len(all_decisions)} decisions, {len(tool_calls_history)} tools)")
            return session_result

        except ClaudeSDKError as e:
            self._log_error(f"SDK session failed: {e}")
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.SYSTEM_ERROR,
                source="ClaudeAgentCoordinator",
                data={"error": str(e), "session_id": session_id}
            ))
            raise
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
        Execute evening review session using Claude SDK query pattern.

        SDK Best Practice: Use client.query() for learning extraction
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

            # SDK query pattern for evening review
            await self.client.query(prompt)

            # Collect responses
            claude_responses = []
            total_input_tokens = 0
            total_output_tokens = 0

            # Process SDK responses
            async for response in self.client.receive_response():
                # Track response content
                if hasattr(response, 'content'):
                    claude_responses.append(str(response.content))

                # Track token usage if available
                if hasattr(response, 'usage'):
                    total_input_tokens += getattr(response.usage, 'input_tokens', 0)
                    total_output_tokens += getattr(response.usage, 'output_tokens', 0)

            # Extract learnings from responses
            response_text = " ".join(claude_responses) if claude_responses else ""
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
                token_input=total_input_tokens,
                token_output=total_output_tokens,
                total_cost_usd=self._calculate_cost(total_input_tokens, total_output_tokens),
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

        except ClaudeSDKError as e:
            self._log_error(f"SDK evening review failed: {e}")
            await self.event_bus.publish(Event(
                id=str(uuid.uuid4()),
                type=EventType.SYSTEM_ERROR,
                source="ClaudeAgentCoordinator",
                data={"error": str(e), "session_id": session_id}
            ))
            raise
        except Exception as e:
            self._log_error(f"Evening review session failed: {e}")
            raise

    # Tool definitions removed - now using MCP server pattern with @tool decorators
    # Tools are defined as functions above in initialize() method

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
        """Build token-optimized morning prompt with learning loop."""
        # Include historical learnings in prompt for continuous improvement
        historical_learnings = context.get('historical_learnings', [])
        learnings_text = ""
        if historical_learnings:
            learnings_text = "\n\nRECENT LEARNINGS FROM PAST SESSIONS:\n" + "\n".join(f"- {learning}" for learning in historical_learnings[:3])

        return f"""Morning Trading Session - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}

CURRENT STATE:
- Account: {account_type}
- Balance: ₹{context.get('acct', {}).get('bal', 100000)}
- Buying Power: ₹{context.get('acct', {}).get('bp', 100000)}
- Open Positions: {len(context.get('pos', []))}

OPEN POSITIONS:
{json.dumps(context.get('pos', [])[:5], indent=2)}

MARKET CONTEXT:
{context.get('mkt', 'No market data available')}

{learnings_text}

YOUR TASK:
1. Analyze open positions - should any be closed based on current conditions?
2. Review market opportunities considering past performance
3. Execute new trades if opportunities exist and align with successful strategies
4. Use tools to execute your decisions
5. Apply learnings from previous sessions to improve decision-making

Think strategically, learn from the past, and execute your trades."""

    def _build_evening_prompt(self, account_type: str, context: Dict[str, Any]) -> str:
        """Build evening review prompt with strategy analysis."""
        # Include strategy effectiveness analysis
        strategy_analysis = ""
        if context.get('strat'):
            strat = context['strat']
            if strat.get('worked'):
                strategy_analysis += f"\n\nWHAT WORKED WELL:\n" + "\n".join(f"- {item}" for item in strat['worked'][:2])
            if strat.get('failed'):
                strategy_analysis += f"\n\nWHAT FAILED:\n" + "\n".join(f"- {item}" for item in strat['failed'][:2])

        return f"""Evening Strategy Review - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}

TODAY'S PERFORMANCE:
- Account: {context.get('acct', account_type)}
- Trades Executed: {context.get('n_trades', 0)}
- Daily P&L: ₹{context.get('pnl', 0)}

TRADES TODAY:
{json.dumps(context.get('trades', [])[:10], indent=2)}

{strategy_analysis}

REFLECTION TASKS:
1. What strategies worked well today? What evidence supports this?
2. What failed and why? What patterns do you see?
3. What will you adjust for tomorrow based on today's results?
4. What do you want to research to improve future performance?
5. How can you apply today's learnings to avoid past mistakes?

Provide detailed, actionable insights for continuous improvement. Focus on specific, measurable changes you can implement."""

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
        if self.client:
            await self.client.__aexit__(None, None, None)
        self.client = None
        self.mcp_server = None
        self.tool_executor = None
        self.validator = None
