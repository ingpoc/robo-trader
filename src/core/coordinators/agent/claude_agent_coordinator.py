"""
Claude Agent Coordinator (Refactored)

Thin orchestrator that delegates to focused coordinators.
Refactored from 614-line monolith into focused coordinators.
"""

import logging
from typing import TYPE_CHECKING, Optional

from claude_agent_sdk import ClaudeSDKClient, ClaudeSDKError, CLINotFoundError

from src.models.claude_agent import ClaudeSessionResult

from ....stores.claude_strategy_store import ClaudeStrategyStore
from ...event_bus import EventBus
from ..base_coordinator import BaseCoordinator

if TYPE_CHECKING:
    from .agent_prompt_builder import AgentPromptBuilder
    from .agent_tool_coordinator import AgentToolCoordinator

logger = logging.getLogger(__name__)


class ClaudeAgentCoordinator(BaseCoordinator):
    """
    Coordinates Claude Agent SDK autonomous trading sessions.

    Responsibilities:
    - Orchestrate agent sessions and tools
    - Initialize SDK client and MCP server
    - Delegate to focused coordinators
    """

    def __init__(
        self,
        config,
        event_bus: EventBus,
        strategy_store: ClaudeStrategyStore,
        container: "DependencyContainer",
    ):
        """Initialize coordinator."""
        super().__init__(config, event_bus)
        self.strategy_store = strategy_store
        self.container = container
        self.client: Optional[ClaudeSDKClient] = None
        self.tool_executor: Optional[ToolExecutor] = None
        self.validator: Optional[ResponseValidator] = None

        # Focused coordinators
        self.session_coordinator: Optional[AgentSessionCoordinator] = None
        self.tool_coordinator: Optional[AgentToolCoordinator] = None
        self.prompt_builder: Optional[AgentPromptBuilder] = None

    async def initialize(self) -> None:
        """Initialize Claude Agent SDK coordinator with focused coordinators."""
        try:
            self._log_info("Initializing ClaudeAgentCoordinator with SDK")

            # Initialize tool executor and validator
            risk_config = (
                self.config.risk.__dict__ if hasattr(self.config, "risk") else {}
            )
            self.tool_executor = ToolExecutor(self.container, risk_config)
            await self.tool_executor.register_handlers()

            self.validator = ResponseValidator(risk_config)

            # Initialize focused coordinators
            self.prompt_builder = AgentPromptBuilder(self.config)

            self.tool_coordinator = AgentToolCoordinator(
                self.config, self.tool_executor
            )
            await self.tool_coordinator.initialize()

            self.session_coordinator = AgentSessionCoordinator(
                self.config,
                self.event_bus,
                self.strategy_store,
                self.tool_executor,
                self.validator,
                None,  # Client will be set after initialization
                self.prompt_builder,
            )
            await self.session_coordinator.initialize()

            # Get SDK options from tool coordinator
            options = self.tool_coordinator.get_sdk_options()

            # Validate system prompt size
            system_prompt_text = self.prompt_builder.build_system_prompt(
                "swing_trading"
            )
            is_valid, token_count = validate_system_prompt_size(system_prompt_text)
            if not is_valid:
                self._log_warning(
                    f"System prompt is {token_count} tokens, may cause initialization issues"
                )

            # Initialize SDK client using client manager
            try:
                client_manager = await self.container.get("claude_sdk_client_manager")
                self.client = await client_manager.get_client("trading", options)
                self.session_coordinator.set_client(self.client)
                self._log_info(
                    "ClaudeAgentCoordinator using shared trading client from manager"
                )
            except Exception as e:
                self._log_warning(f"Failed to get client from manager: {e}")
                raise

            self._initialized = True
            self._log_info(
                "ClaudeAgentCoordinator initialized successfully with SDK MCP server"
            )

        except CLINotFoundError:
            self._log_error(
                "Claude Code CLI not found. Please install Claude Code to use AI trading features."
            )
            raise TradingError(
                "Claude Code CLI not installed",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False,
            )
        except ClaudeSDKError as e:
            self._log_error(f"SDK initialization failed: {e}")
            raise TradingError(
                f"Claude SDK initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False,
            )
        except Exception as e:
            self._log_error(f"Failed to initialize ClaudeAgentCoordinator: {e}")
            raise

    async def run_morning_prep_session(
        self, account_type: str, context: dict
    ) -> ClaudeSessionResult:
        """Execute morning preparation session."""
        return await self.session_coordinator.run_morning_prep_session(
            account_type, context
        )

    async def run_evening_review_session(
        self, account_type: str, context: dict
    ) -> ClaudeSessionResult:
        """Execute evening review session."""
        return await self.session_coordinator.run_evening_review_session(
            account_type, context
        )

    async def cleanup(self) -> None:
        """Cleanup coordinator resources."""
        self._log_info("ClaudeAgentCoordinator cleanup")
        # Client manager handles cleanup of shared clients
        self.client = None
        if self.tool_coordinator:
            await self.tool_coordinator.cleanup()
        if self.session_coordinator:
            await self.session_coordinator.cleanup()
        self.tool_executor = None
        self.validator = None
        self._initialized = False
