"""
Robo Trader Orchestrator

The central coordinator for the multi-agent trading system.
Refactored as a thin facade that delegates to focused coordinators.
"""

from typing import Dict, List, Optional, Any

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from loguru import logger

from src.config import Config
from ..auth.claude_auth import ClaudeAuthStatus


class RoboTraderOrchestrator:
    """
    Main orchestrator for the Robo Trader system - Thin Facade.

    Coordinates between multiple agents for autonomous trading by delegating
    to focused coordinators:
    - SessionCoordinator: Claude session lifecycle
    - QueryCoordinator: Query processing
    - TaskCoordinator: Analytics tasks
    - StatusCoordinator: Status aggregation
    - LifecycleCoordinator: Emergency stop/resume
    - BroadcastCoordinator: UI broadcasting
    """

    def __init__(self, config: Config):
        self.config = config

        self.session_coordinator = None
        self.query_coordinator = None
        self.task_coordinator = None
        self.status_coordinator = None
        self.lifecycle_coordinator = None
        self.broadcast_coordinator = None

        self.state_manager = None
        self.ai_planner = None
        self.background_scheduler = None
        self.conversation_manager = None
        self.learning_engine = None

        self.options: Optional[ClaudeAgentOptions] = None
        self.claude_status: Optional[ClaudeAuthStatus] = None

    async def initialize(self) -> None:
        """Initialize the orchestrator with MCP servers and hooks."""
        logger.info("Initializing Robo Trader Orchestrator")

        self.claude_status = await self.session_coordinator.validate_authentication()

        logger.info("MCP servers creation disabled")
        broker_server = None
        agents_server = None

        allowed_tools = self._get_allowed_tools()

        educational_tools = [
            "mcp__agents__explain_concept",
            "mcp__agents__explain_decision",
            "mcp__agents__explain_portfolio",
        ]
        allowed_tools.extend(educational_tools)

        alert_tools = [
            "mcp__agents__create_alert_rule",
            "mcp__agents__list_alert_rules",
            "mcp__agents__check_alerts",
            "mcp__agents__delete_alert_rule",
        ]
        allowed_tools.extend(alert_tools)

        strategy_tools = [
            "mcp__agents__list_strategies",
            "mcp__agents__compare_strategies",
            "mcp__agents__backtest_strategy",
            "mcp__agents__create_custom_strategy",
            "mcp__agents__get_strategy_education",
        ]
        allowed_tools.extend(strategy_tools)

        from ..core.hooks import create_safety_hooks
        hooks = create_safety_hooks(self.config, self.state_manager)

        mcp_servers_dict = {}
        if broker_server:
            mcp_servers_dict["broker"] = broker_server
        if agents_server:
            mcp_servers_dict["agents"] = agents_server

        self.options = ClaudeAgentOptions(
            allowed_tools=allowed_tools,
            permission_mode=self.config.permission_mode,
            mcp_servers=mcp_servers_dict,
            hooks=hooks,
            system_prompt=self._get_system_prompt(),
            cwd=self.config.project_dir,
            max_turns=self.config.max_turns,
            setting_sources=["user"],  # Load ~/.claude/settings.json for global CLI settings
        )

        self.session_coordinator.options = self.options

        await self.ai_planner.initialize()
        await self.conversation_manager.initialize()
        await self.learning_engine.initialize()

        self.background_scheduler._run_portfolio_scan = self.run_portfolio_scan
        self.background_scheduler._run_market_screening = self.run_market_screening
        self.background_scheduler._ai_planner_create_plan = self.ai_planner.create_daily_plan
        self.background_scheduler._orchestrator_get_claude_status = self.get_claude_status

        self.background_tasks = await self.background_scheduler.start()

        logger.info("Orchestrator initialized successfully")

    def _get_allowed_tools(self) -> List[str]:
        """Get allowed tools based on configuration and environment."""
        base_agent_tools = [
            "mcp__agents__analyze_portfolio",
            "mcp__agents__technical_analysis",
            "mcp__agents__fundamental_screening",
            "mcp__agents__risk_assessment",
            "mcp__agents__execute_trade",
            "mcp__agents__monitor_market",
        ]

        broker_read_only_tools = [
            "mcp__broker__get_portfolio",
            "mcp__broker__get_orders",
            "mcp__broker__get_instruments",
            "mcp__broker__quote",
        ]

        ticker_tools = [
            "mcp__broker__ticker_subscribe",
            "mcp__broker__ticker_unsubscribe",
            "mcp__broker__ticker_set_mode",
        ]

        execution_tools = [
            "mcp__broker__place_order",
            "mcp__broker__modify_order",
            "mcp__broker__cancel_order",
        ]

        allowed = []
        allowed.extend(base_agent_tools)
        allowed.extend(broker_read_only_tools)
        allowed.extend(ticker_tools)

        if self.config.environment in ["paper", "live"]:
            allowed.extend(execution_tools)

        return sorted(set(allowed))

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the orchestrator."""
        return f"""
You are the Robo Trader Orchestrator, a sophisticated multi-agent autonomous trading system.

Your role is to coordinate between specialized agents to make informed trading decisions:

1. **Portfolio Analyzer**: Monitors current holdings, P&L, and risk metrics
2. **Technical Analyst**: Computes indicators and generates trading signals
3. **Fundamental Screener**: Identifies attractive investment opportunities
4. **Risk Manager**: Enforces position sizing, stop-losses, and risk limits
5. **Execution Agent**: Translates approved trades into broker orders
6. **Market Monitor**: Watches real-time market data and triggers alerts

Environment: {self.config.environment}
- Dry-run: Simulate all operations
- Paper: Use paper trading environment
- Live: Execute real trades (requires explicit approval)

Always follow this workflow:
1. Analyze current portfolio state
2. Identify opportunities via screening and technical analysis
3. Assess risk for any proposed trades
4. Get approval before execution
5. Monitor and adjust as needed

Use the available tools to coordinate between agents. Maintain state and create checkpoints at critical points.
"""

    async def start_session(self) -> None:
        """Start an interactive session with the orchestrator."""
        await self.session_coordinator.start_session()

    async def end_session(self) -> None:
        """End the current session and cleanup resources."""
        logger.info("Ending orchestrator session and cleaning up resources")

        try:
            if self.ai_planner:
                await self.ai_planner.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up AI Planner: {e}")

        try:
            if self.conversation_manager:
                await self.conversation_manager.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up Conversation Manager: {e}")

        try:
            if self.learning_engine:
                await self.learning_engine.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up Learning Engine: {e}")

        await self.session_coordinator.end_session()

        logger.info("Orchestrator session ended successfully")

    async def process_query(self, query: str) -> List[Any]:
        """Process a user query and return responses."""
        return await self.query_coordinator.process_query(query)

    async def process_query_enhanced(self, query: str) -> Dict[str, Any]:
        """Process query with proper streaming and progressive updates."""
        return await self.query_coordinator.process_query_enhanced(query)

    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        return await self.status_coordinator.get_ai_status()

    async def trigger_market_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger market event for autonomous response."""
        await self.lifecycle_coordinator.trigger_market_event(event_type, event_data)

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for monitoring."""
        return await self.status_coordinator.get_system_status()

    async def emergency_stop(self) -> None:
        """Emergency stop all autonomous operations."""
        await self.lifecycle_coordinator.emergency_stop()

    async def resume_operations(self) -> None:
        """Resume autonomous operations after emergency stop."""
        await self.lifecycle_coordinator.resume_operations()

    async def session(self):
        """Context manager for single-query sessions."""
        if not self.options:
            await self.initialize()

        return ClaudeSDKClient(options=self.options)

    async def run_portfolio_scan(self) -> Dict[str, Any]:
        """Run a portfolio scan using live portfolio data."""
        portfolio_coordinator = getattr(self, 'portfolio_coordinator', None)
        if portfolio_coordinator:
            return await portfolio_coordinator.run_portfolio_scan()
        return {"error": "Portfolio coordinator not available"}

    async def run_market_screening(self) -> Dict[str, Any]:
        """Run market screening using current holdings analytics."""
        portfolio_coordinator = getattr(self, 'portfolio_coordinator', None)
        if portfolio_coordinator:
            return await portfolio_coordinator.run_market_screening()
        return {"error": "Portfolio coordinator not available"}

    async def run_strategy_review(self) -> Dict[str, Any]:
        """Run strategy review to derive actionable rebalance suggestions."""
        return await self.task_coordinator.run_strategy_review()

    async def handle_market_alert(self, symbol: str, alert_type: str, data: Dict) -> None:
        """Handle real-time market alerts."""
        await self.query_coordinator.handle_market_alert(symbol, alert_type, data)

    async def broadcast_to_ui(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients."""
        await self.broadcast_coordinator.broadcast_to_ui(message)

    async def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        return await self.status_coordinator.get_agents_status()

    async def get_claude_status(self) -> ClaudeAuthStatus:
        """Get current Claude API status."""
        return await self.session_coordinator.get_claude_status()
