"""
Enhanced Workflow SDK Client Manager.

Provides contextual tool selection and dynamic client creation for different
workflow stages, optimizing Claude Agent SDK usage for progressive discovery.
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
from src.core.di import DependencyContainer
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.workflow_sdk_client_manager import WorkflowSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout, validate_system_prompt_size
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

from .progressive_discovery_manager import ProgressiveDiscoveryManager, DiscoveryContext
from .workflow_state_tracker import WorkflowStateTracker, WorkflowStage

logger = logging.getLogger(__name__)


@dataclass
class ClientConfiguration:
    """Configuration for SDK client creation."""
    client_name: str
    workflow_stage: WorkflowStage
    instructions: str
    allowed_tools: List[str]
    tool_categories: List[str]
    max_turns: int
    timeout_seconds: int
    temperature: float = 0.7
    mcp_servers: Dict[str, Any] = field(default_factory=dict)
    discovery_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClientSession:
    """Active client session with metadata."""
    client: ClaudeSDKClient
    configuration: ClientConfiguration
    created_at: datetime
    last_used: datetime
    usage_count: int = 0
    total_tokens_used: int = 0
    session_duration_minutes: int = 0
    is_active: bool = True


class EnhancedWorkflowSDKClientManager:
    """
    Enhanced workflow SDK client manager with progressive discovery integration.

    Features:
    - Contextual tool selection based on workflow stage
    - Dynamic client creation with optimized configurations
    - Session management and cleanup
    - Integration with progressive discovery system
    - Token usage optimization
    - Performance monitoring
    """

    def __init__(self, container: DependencyContainer):
        """Initialize enhanced workflow SDK client manager."""
        self.container = container
        self.base_client_manager: Optional[ClaudeSDKClientManager] = None
        self.workflow_client_manager: Optional[WorkflowSDKClientManager] = None

        # Progressive discovery integration
        self.discovery_manager: Optional[ProgressiveDiscoveryManager] = None
        self.workflow_tracker: Optional[WorkflowStateTracker] = None

        # Enhanced client management
        self._active_sessions: Dict[str, ClientSession] = {}
        self._client_configurations: Dict[str, ClientConfiguration] = {}
        self._session_cleanup_task: Optional[asyncio.Task] = None

        # Performance metrics
        self._metrics = {
            "total_sessions_created": 0,
            "active_sessions": 0,
            "total_client_creations": 0,
            "avg_session_duration_minutes": 0.0,
            "token_efficiency_score": 0.0,
            "context_switches": 0,
            "tool_relevance_scores": {}
        }

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize enhanced workflow SDK client manager."""
        if self._initialized:
            return

        try:
            # Get base client manager
            self.base_client_manager = await self.container.get("claude_sdk_client_manager")

            # Get workflow client manager
            self.workflow_client_manager = await self.container.get("workflow_sdk_client_manager")

            # Get progressive discovery components
            mcp_server_data = await self.container.get("enhanced_paper_trading_mcp_server")
            self.discovery_manager = mcp_server_data["discovery_manager"]

            mcp_integration = await self.container.get("mcp_integration_service")
            self.workflow_tracker = WorkflowStateTracker(self.container)
            await self.workflow_tracker.initialize()

            # Initialize client configurations
            await self._initialize_client_configurations()

            # Start session cleanup task
            self._session_cleanup_task = asyncio.create_task(self._background_session_cleanup())

            self._initialized = True
            logger.info("Enhanced Workflow SDK Client Manager initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize Enhanced Workflow SDK Client Manager: {e}")
            raise TradingError(
                f"Enhanced SDK Client Manager initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    async def _initialize_client_configurations(self) -> None:
        """Initialize client configurations for different workflow stages."""
        stages = [
            WorkflowStage.IDLE,
            WorkflowStage.RESEARCH,
            WorkflowStage.ANALYSIS,
            WorkflowStage.EXECUTION,
            WorkflowStage.MONITORING,
            WorkflowStage.OPTIMIZATION
        ]

        for stage in stages:
            config = self._create_client_configuration(stage)
            self._client_configurations[stage.value] = config

    def _create_client_configuration(self, stage: WorkflowStage) -> ClientConfiguration:
        """Create client configuration for specific workflow stage."""

        # Base configuration
        config = ClientConfiguration(
            client_name=f"enhanced_workflow_{stage.value}",
            workflow_stage=stage,
            instructions=self._get_stage_instructions(stage),
            allowed_tools=self._get_stage_tools(stage),
            tool_categories=self._get_stage_categories(stage),
            max_turns=self._get_stage_max_turns(stage),
            timeout_seconds=self._get_stage_timeout(stage),
            temperature=self._get_stage_temperature(stage)
        )

        return config

    def _get_stage_instructions(self, stage: WorkflowStage) -> str:
        """Get system instructions for specific workflow stage."""
        instructions = {
            WorkflowStage.IDLE: """You are an intelligent trading assistant. Monitor the system status and be ready to assist with trading operations when needed. Keep responses concise and focused on readiness.""",

            WorkflowStage.RESEARCH: """You are a market research specialist. Focus on gathering comprehensive market data using available tools. Be thorough but efficient. Prioritize recent and relevant information. Structure your research findings clearly.""",

            WorkflowStage.ANALYSIS: """You are a portfolio analysis expert. Analyze available data to identify patterns, risks, and opportunities. Use analytical tools to derive actionable insights. Be objective and data-driven in your analysis.""",

            WorkflowStage.EXECUTION: """You are a trade execution specialist. Focus on making informed trading decisions based on available analysis. Be decisive but cautious. Execute trades according to strategy guidelines and risk parameters.""",

            WorkflowStage.MONITORING: """You are a portfolio monitoring expert. Track active positions and market conditions. Alert to significant changes or opportunities. Provide timely updates on portfolio performance.""",

            WorkflowStage.OPTIMIZATION: """You are a strategy optimization specialist. Identify areas for improvement in trading approaches. Test and refine strategies for better performance. Focus on long-term efficiency gains."""
        }

        return instructions.get(stage, instructions[WorkflowStage.IDLE])

    def _get_stage_tools(self, stage: WorkflowStage) -> List[str]:
        """Get allowed tools for specific workflow stage."""
        # This would be dynamically updated from discovery manager
        base_tools = {
            WorkflowStage.IDLE: ["get_market_status", "check_paper_trading_status"],
            WorkflowStage.RESEARCH: ["research_symbol", "get_market_status"],
            WorkflowStage.ANALYSIS: ["analyze_portfolio_data", "get_strategy_performance", "research_symbol"],
            WorkflowStage.EXECUTION: ["execute_paper_trade", "get_market_status", "analyze_portfolio_data"],
            WorkflowStage.MONITORING: ["check_paper_trading_status", "get_strategy_performance", "calculate_monthly_pnl"],
            WorkflowStage.OPTIMIZATION: ["optimize_prompt_template", "analyze_portfolio_data", "get_strategy_performance"]
        }

        return base_tools.get(stage, base_tools[WorkflowStage.IDLE])

    def _get_stage_categories(self, stage: WorkflowStage) -> List[str]:
        """Get tool categories for specific workflow stage."""
        categories = {
            WorkflowStage.IDLE: ["core", "monitoring"],
            WorkflowStage.RESEARCH: ["core", "research"],
            WorkflowStage.ANALYSIS: ["core", "contextual", "analysis"],
            WorkflowStage.EXECUTION: ["core", "contextual", "execution"],
            WorkflowStage.MONITORING: ["core", "contextual", "monitoring"],
            WorkflowStage.OPTIMIZATION: ["core", "contextual", "optimization"]
        }

        return categories.get(stage, ["core"])

    def _get_stage_max_turns(self, stage: WorkflowStage) -> int:
        """Get maximum turns for specific workflow stage."""
        turn_limits = {
            WorkflowStage.IDLE: 10,
            WorkflowStage.RESEARCH: 25,
            WorkflowStage.ANALYSIS: 20,
            WorkflowStage.EXECUTION: 15,
            WorkflowStage.MONITORING: 10,
            WorkflowStage.OPTIMIZATION: 30
        }

        return turn_limits.get(stage, 20)

    def _get_stage_timeout(self, stage: WorkflowStage) -> int:
        """Get timeout for specific workflow stage."""
        timeouts = {
            WorkflowStage.IDLE: 120,  # 2 minutes
            WorkflowStage.RESEARCH: 300,  # 5 minutes
            WorkflowStage.ANALYSIS: 240,  # 4 minutes
            WorkflowStage.EXECUTION: 180,  # 3 minutes
            WorkflowStage.MONITORING: 120,  # 2 minutes
            WorkflowStage.OPTIMIZATION: 300  # 5 minutes
        }

        return timeouts.get(stage, 240)

    def _get_stage_temperature(self, stage: WorkflowStage) -> float:
        """Get temperature for specific workflow stage."""
        temperatures = {
            WorkflowStage.IDLE: 0.3,
            WorkflowStage.RESEARCH: 0.5,
            WorkflowStage.ANALYSIS: 0.4,
            WorkflowStage.EXECUTION: 0.7,
            WorkflowStage.MONITORING: 0.2,
            WorkflowStage.OPTIMIZATION: 0.6
        }

        return temperatures.get(stage, 0.5)

    async def get_contextual_client(self, context: Optional[DiscoveryContext] = None,
                                     stage: Optional[WorkflowStage] = None) -> ClaudeSDKClient:
        """
        Get contextual client with optimized configuration.

        Args:
            context: Discovery context for tool selection
            stage: Specific workflow stage

        Returns:
            Configured Claude SDK client
        """
        if not self._initialized:
            raise RuntimeError("Enhanced SDK Client Manager not initialized")

        # Determine target stage
        target_stage = stage or (context.workflow_stage if context else WorkflowStage.IDLE)

        # Check for existing session
        session_key = self._generate_session_key(context, target_stage)
        existing_session = self._active_sessions.get(session_key)

        if existing_session and existing_session.is_active:
            # Update session usage
            existing_session.last_used = datetime.utcnow()
            existing_session.usage_count += 1
            existing_session.session_duration_minutes = int(
                (datetime.utcnow() - existing_session.created_at).total_seconds() / 60
            )
            logger.debug(f"Reusing existing session: {session_key}")
            return existing_session.client

        # Create new session
        return await self._create_contextual_client(context, target_stage)

    def _generate_session_key(self, context: Optional[DiscoveryContext],
                          stage: WorkflowStage) -> str:
        """Generate session key based on context and stage."""
        context_id = "default"
        if context:
            context_id = f"{context.workflow_stage.value}_{context.trades_executed}_{len(context.current_positions)}"

        return f"{stage.value}_{context_id}_{datetime.utcnow().strftime('%H%M')}"

    async def _create_contextual_client(self, context: Optional[DiscoveryContext],
                                       stage: WorkflowStage) -> ClaudeSDKClient:
        """Create new contextual client."""
        try:
            # Get base configuration
            base_config = self._client_configurations.get(stage.value)
            if not base_config:
                raise ValueError(f"No configuration found for stage: {stage.value}")

            # Customize configuration based on context
            customized_config = self._customize_configuration(base_config, context)

            # Create Claude agent options
            options = ClaudeAgentOptions(
                name=customized_config.client_name,
                instructions=customized_config.instructions,
                allowed_tools=customized_config.allowed_tools,
                mcp_servers=customized_config.mcp_servers,
                max_turns=customized_config.max_turns,
                temperature=customized_config.temperature,
                timeout_seconds=customized_config.timeout_seconds
            )

            # Validate system prompt size
            is_valid, token_count = validate_system_prompt_size(customized_config.instructions)
            if not is_valid:
                logger.warning(f"System prompt too large ({token_count} tokens), truncating")
                customized_config.instructions = customized_config.instructions[:4000] + "..."

            # Get client from base manager
            client = await self.base_client_manager.get_client(
                customized_config.client_name, options
            )

            # Create session
            session = ClientSession(
                client=client,
                configuration=customized_config,
                created_at=datetime.utcnow(),
                last_used=datetime.utcnow(),
                is_active=True
            )

            # Store session
            session_key = self._generate_session_key(context, stage)
            self._active_sessions[session_key] = session

            # Update metrics
            self._metrics["total_sessions_created"] += 1
            self._metrics["active_sessions"] = len(self._active_sessions)
            self._metrics["total_client_creations"] += 1

            logger.info(f"Created contextual client: {customized_config.client_name} for stage {stage.value}")
            return client

        except Exception as e:
            logger.error(f"Error creating contextual client: {e}")
            raise TradingError(
                f"Failed to create contextual client: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    def _customize_configuration(self, base_config: ClientConfiguration,
                             context: Optional[DiscoveryContext]) -> ClientConfiguration:
        """Customize configuration based on context."""
        customized = ClientConfiguration(
            **asdict(base_config)
        )

        if context:
            # Adjust based on user expertise
            if context.user_expertise_level == "beginner":
                customized.max_turns = min(customized.max_turns, 15)
                customized.temperature = 0.3
                customized.instructions += "\nKeep explanations simple and clear. Avoid jargon."
            elif context.user_expertise_level == "advanced":
                customized.max_turns = min(customized.max_turns + 10, 50)
                customized.temperature = 0.8
                customized.instructions += "\nYou can use advanced analytical techniques and trading strategies."

            # Adjust based on portfolio complexity
            if context.portfolio_value > 500000:
                customized.instructions += "\nConsider diversification and risk management for large portfolios."
            elif context.trades_executed > 20:
                customized.instructions += "\nLeverage your trading experience to refine strategies."

            # Add context to discovery context
            customized.discovery_context = asdict(context)

        return customized

    async def update_client_session(self, session_key: str, usage_data: Dict[str, Any]) -> bool:
        """Update client session with usage data."""
        session = self._active_sessions.get(session_key)
        if not session:
            return False

        try:
            session.last_used = datetime.utcnow()
            session.usage_count += 1
            session.total_tokens_used += usage_data.get("tokens_used", 0)
            session.session_duration_minutes = int(
                (datetime.utcnow() - session.created_at).total_seconds() / 60
            )

            # Update metrics
            self._metrics["context_switches"] += usage_data.get("context_switches", 0)

            logger.debug(f"Updated session: {session_key}")
            return True

        except Exception as e:
            logger.error(f"Error updating client session: {e}")
            return False

    async def get_client_analytics(self) -> Dict[str, Any]:
        """Get comprehensive client analytics."""
        if not self._initialized:
            return {"error": "Enhanced SDK Client Manager not initialized"}

        # Calculate session metrics
        total_sessions = self._metrics["total_sessions_created"]
        active_sessions = len(self._active_sessions)

        if self._active_sessions:
            avg_duration = sum(s.session_duration_minutes for s in self._active_sessions.values()) / len(self._active_sessions)
            total_tokens = sum(s.total_tokens_used for s in self._active_sessions.values())
            avg_tokens_per_session = total_tokens / max(1, active_sessions)
        else:
            avg_duration = 0
            total_tokens = 0
            avg_tokens_per_session = 0

        # Calculate efficiency score
        efficiency_score = min(1.0, avg_tokens_per_session / 100)  # Target: 100 tokens per session

        return {
            "client_metrics": {
                **self._metrics,
                "avg_session_duration_minutes": round(avg_duration, 1),
                "avg_tokens_per_session": round(avg_tokens_per_session),
                "token_efficiency_score": round(efficiency_score, 3)
            },
            "active_sessions": active_sessions,
            "total_sessions": total_sessions,
            "client_configurations": {
                stage: config.client_name for stage, config in self._client_configurations.items()
            },
            "integration_status": {
                "base_client_manager": self.base_client_manager is not None,
                "workflow_client_manager": self.workflow_client_manager is not None,
                "discovery_manager": self.discovery_manager is not None,
                "workflow_tracker": self.workflow_tracker is not None
            }
        }

    async def _background_session_cleanup(self) -> None:
        """Background task for session cleanup."""
        while True:
            try:
                await asyncio.sleep(300)  # Check every 5 minutes
                await self._cleanup_inactive_sessions()
            except asyncio.CancelledError:
                logger.info("Session cleanup task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in session cleanup: {e}")

    async def _cleanup_inactive_sessions(self) -> None:
        """Clean up inactive sessions."""
        inactive_threshold = timedelta(minutes=10)
        current_time = datetime.utcnow()

        inactive_sessions = []
        for session_key, session in self._active_sessions.items():
            if current_time - session.last_used > inactive_threshold:
                inactive_sessions.append(session_key)

        if inactive_sessions:
            for session_key in inactive_sessions:
                session = self._active_sessions[session_key]
                session.is_active = False
                del self._active_sessions[session_key]

            # Update metrics
            self._metrics["active_sessions"] = len(self._active_sessions)
            logger.info(f"Cleaned up {len(inactive_sessions)} inactive sessions")

    async def cleanup(self) -> None:
        """Cleanup enhanced SDK client manager resources."""
        try:
            # Cancel background task
            if self._session_cleanup_task:
                self._session_cleanup_task.cancel()
                try:
                    await self._session_cleanup_task
                except asyncio.CancelledError:
                    pass

            # Close all active sessions
            for session_key, session in self._active_sessions.items():
                session.is_active = False
                # Note: We don't close the client as it's managed by the base manager

            self._active_sessions.clear()
            self._client_configurations.clear()

            self._initialized = False
            logger.info("Enhanced Workflow SDK Client Manager cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during enhanced SDK client manager cleanup: {e}")