"""
Robo Trader Orchestrator

The central coordinator for the multi-agent trading system.
Manages agent interactions, tool routing, permissions, and safety controls.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    HookMatcher,
    create_sdk_mcp_server,
    tool,
    AssistantMessage,
    TextBlock,
    ToolUseBlock
)
from loguru import logger

from ..config import Config
from ..mcp.broker import create_broker_mcp_server
from ..agents import create_agents_mcp_server
from ..core.hooks import create_safety_hooks
from ..core.state import StateManager
from ..core.ai_planner import AIPlanner
from ..core.background_scheduler import BackgroundScheduler
from ..services.analytics import (
    run_portfolio_scan as analytics_run_portfolio_scan,
    run_market_screening as analytics_run_market_screening,
    run_strategy_analysis,
)
from ..auth.claude_auth import validate_claude_api, ClaudeAuthStatus


class RoboTraderOrchestrator:
    """
    Main orchestrator for the Robo Trader system.

    Coordinates between multiple agents for autonomous trading:
    - Portfolio Analyzer
    - Technical Analyst
    - Fundamental Screener
    - Risk Manager
    - Execution Agent
    - Market Monitor
    """

    def __init__(self, config: Config):
        self.config = config
        self.state_manager = StateManager(config.state_dir)
        self.ai_planner = AIPlanner(config, self.state_manager)
        self.background_scheduler = BackgroundScheduler(config, self.state_manager, self)
        self.client: Optional[ClaudeSDKClient] = None
        self.options: Optional[ClaudeAgentOptions] = None
        self.claude_status: Optional[ClaudeAuthStatus] = None

        from .conversation_manager import ConversationManager
        from .learning_engine import LearningEngine

        self.conversation_manager = ConversationManager(config, self.state_manager)
        self.learning_engine = LearningEngine(config, self.state_manager)

    async def initialize(self) -> None:
        """Initialize the orchestrator with MCP servers and hooks."""
        logger.info("Initializing Robo Trader Orchestrator")

        # Check Claude API access (informational only - SDK handles actual auth)
        logger.info("Checking Claude authentication...")
        self.claude_status = await validate_claude_api(self.config.integration.anthropic_api_key)
        
        if self.claude_status.is_valid:
            auth_method = self.claude_status.account_info.get("auth_method", "unknown")
            logger.info(f"✓ Claude authenticated via {auth_method}")
        else:
            logger.info(f"ℹ️  Claude API pre-check: {self.claude_status.error}")
            logger.info("ℹ️  System will use Claude Agent SDK authentication (Claude Pro subscription)")
            # Create a status indicating SDK will handle auth
            self.claude_status = ClaudeAuthStatus(
                is_valid=True,  # Assume SDK will handle it
                api_key_present=False,
                account_info={"auth_method": "claude_agent_sdk", "note": "Using SDK built-in authentication"}
            )
        
        # Create MCP servers
        broker_server = await create_broker_mcp_server(self.config)
        agents_server = await create_agents_mcp_server(self.config, self.state_manager)

        # Define allowed tools based on environment
        allowed_tools = self._get_allowed_tools()

        # Add educational tools to all environments
        educational_tools = [
            "mcp__agents__explain_concept",
            "mcp__agents__explain_decision",
            "mcp__agents__explain_portfolio",
        ]
        allowed_tools.extend(educational_tools)

        # Add alert tools to all environments
        alert_tools = [
            "mcp__agents__create_alert_rule",
            "mcp__agents__list_alert_rules",
            "mcp__agents__check_alerts",
            "mcp__agents__delete_alert_rule",
        ]
        allowed_tools.extend(alert_tools)

        # Add strategy tools to all environments
        strategy_tools = [
            "mcp__agents__list_strategies",
            "mcp__agents__compare_strategies",
            "mcp__agents__backtest_strategy",
            "mcp__agents__create_custom_strategy",
            "mcp__agents__get_strategy_education",
        ]
        allowed_tools.extend(strategy_tools)

        # Create safety hooks
        hooks = create_safety_hooks(self.config, self.state_manager)

        # Configure Claude Agent options
        self.options = ClaudeAgentOptions(
            allowed_tools=allowed_tools,
            permission_mode=self.config.permission_mode,
            mcp_servers={
                "broker": broker_server,
                "agents": agents_server,
            },
            hooks=hooks,
            system_prompt=self._get_system_prompt(),
            cwd=self.config.project_dir,
            max_turns=self.config.max_turns,
        )

        # Initialize AI planner
        await self.ai_planner.initialize()

        # Initialize conversation manager
        await self.conversation_manager.initialize()

        # Initialize learning engine
        await self.learning_engine.initialize()

        # Initialize background scheduler and track tasks for lifecycle management
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
        """
        Start an interactive session with the orchestrator.
        
        For web applications, this maintains a long-lived client.
        For CLI applications, prefer using the session context manager.
        """
        if not self.options:
            await self.initialize()

        # Use context manager protocol properly
        self.client = ClaudeSDKClient(options=self.options)
        await self.client.__aenter__()

        logger.info("Orchestrator session started")

    async def end_session(self) -> None:
        """End the current session and cleanup resources."""
        if self.client:
            try:
                await self.client.__aexit__(None, None, None)
            except Exception as e:
                logger.warning(f"Error during session cleanup: {e}")
            finally:
                self.client = None
                logger.info("Orchestrator session ended")

    async def process_query(self, query: str) -> List[Any]:
        """
        Process a user query and return responses.

        For single queries, prefer using session() context manager.
        This method is for applications with persistent sessions.
        """
        if not self.client:
            raise RuntimeError("Session not started. Call start_session() first.")

        await self.client.query(query)

        responses = []
        async for response in self.client.receive_response():
            responses.append(response)

        return responses

    # NEW: Enhanced streaming intelligence processing
    async def process_query_enhanced(self, query: str):
        """
        Process query with proper streaming and progressive updates.

        Returns structured response with thinking, tool usage, and results.
        """
        if not self.client:
            raise RuntimeError("Session not started. Call start_session() first.")

        await self.client.query(query)

        thinking_content = []
        tool_uses = []
        results = []

        async for message in self.client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        thinking_content.append(block.text)
                        # Broadcast thinking to UI (would need WebSocket integration)
                        logger.info(f"AI Thinking: {block.text[:100]}...")
                    elif isinstance(block, ToolUseBlock):
                        tool_uses.append({
                            "id": block.id,
                            "name": block.name,
                            "status": "executing"
                        })
                        logger.info(f"Tool Use: {block.name}")

        return {
            "thinking": thinking_content,
            "tool_uses": tool_uses,
            "results": results
        }

    # NEW: AI Status for UI
    async def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI activity status for UI display."""
        return await self.ai_planner.get_current_task_status()

    # NEW: Autonomous Operations
    async def trigger_market_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Trigger market event for autonomous response."""
        await self.background_scheduler.trigger_event(event_type, event_data)

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status for monitoring."""
        ai_status = await self.get_ai_status()
        scheduler_status = await self.background_scheduler.get_scheduler_status()

        return {
            "ai_status": ai_status,
            "scheduler_status": scheduler_status,
            "claude_status": self.claude_status.to_dict() if self.claude_status else None,
            "portfolio_status": await self._get_portfolio_status(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def _get_portfolio_status(self) -> Dict[str, Any]:
        """Get portfolio health status."""
        try:
            portfolio = await self.state_manager.get_portfolio()
            if portfolio:
                return {
                    "holdings_count": len(portfolio.holdings),
                    "total_value": portfolio.exposure_total,
                    "last_updated": getattr(portfolio, 'last_updated', None)
                }
            return {"status": "no_portfolio"}
        except Exception:
            return {"status": "error"}

    async def emergency_stop(self) -> None:
        """Emergency stop all autonomous operations."""
        logger.warning("Emergency stop triggered - halting all operations")

        # Stop background scheduler
        await self.background_scheduler.stop()

        # Cancel any running tasks
        # This would need to be implemented based on current task management

        # Notify UI
        # This would broadcast to WebSocket clients

    async def resume_operations(self) -> None:
        """Resume autonomous operations after emergency stop."""
        logger.info("Resuming autonomous operations")

        # Restart background scheduler
        await self.background_scheduler.start()

        # Notify UI
        # This would broadcast to WebSocket clients
    
    async def session(self):
        """
        Context manager for single-query sessions.
        
        Example:
            async with orchestrator.session() as client:
                await client.query("Analyze portfolio")
                async for msg in client.receive_response():
                    print(msg)
        """
        if not self.options:
            await self.initialize()
        
        return ClaudeSDKClient(options=self.options)

    async def run_portfolio_scan(self) -> Dict[str, Any]:
        """Run a portfolio scan using live portfolio data."""
        results = await analytics_run_portfolio_scan(self.config, self.state_manager)
        logger.info(
            "Portfolio scan completed from %s with %d holdings",
            results["source"],
            len(results["portfolio"]["holdings"]),
        )

        # Generate AI recommendations from scan results
        await self._generate_recommendations_from_scan(results)

        return results

    async def run_market_screening(self) -> Dict[str, Any]:
        """Run market screening using current holdings analytics."""
        results = await analytics_run_market_screening(self.config, self.state_manager)
        logger.info(
            "Market screening completed from %s with %d momentum candidates",
            results["source"],
            len(results["screening"]["momentum"]),
        )
        return results

    async def run_strategy_review(self) -> Dict[str, Any]:
        """Run strategy review to derive actionable rebalance suggestions."""
        results = await run_strategy_analysis(self.config, self.state_manager)
        logger.info(
            "Strategy review completed from %s with %d recommended actions",
            results["source"],
            len(results["strategy"]["actions"]),
        )
        return results

    async def _generate_recommendations_from_scan(self, scan_results: Dict[str, Any]) -> None:
        """Generate AI recommendations from portfolio scan results."""
        try:
            portfolio = scan_results.get("portfolio", {})
            holdings = portfolio.get("holdings", [])

            if not holdings:
                logger.info("No holdings to generate recommendations for")
                return

            # Analyze each holding
            for holding in holdings:
                symbol = holding.get("symbol", "")
                if not symbol:
                    continue

                # Get key metrics
                pnl_pct = holding.get("pnl_pct", 0)
                exposure_pct = (holding.get("exposure", 0) / portfolio.get("exposure_total", 1)) * 100 if portfolio.get("exposure_total", 0) > 0 else 0

                # Simple recommendation logic (will be enhanced with AI later)
                recommendation = None

                # SELL if losing > 15%
                if pnl_pct < -15:
                    recommendation = {
                        "symbol": symbol,
                        "action": "SELL",
                        "confidence": 75,
                        "reasoning": f"Stock down {pnl_pct:.1f}%. Consider cutting losses.",
                        "analysis_type": "risk_management",
                        "current_price": holding.get("last_price"),
                        "stop_loss": holding.get("avg_price", 0) * 0.92,
                        "quantity": holding.get("qty"),
                        "potential_impact": f"Stop loss triggered at {pnl_pct:.1f}%",
                        "risk_level": "high",
                        "time_horizon": "immediate"
                    }

                # BOOK_PROFIT if up > 25%
                elif pnl_pct > 25:
                    recommendation = {
                        "symbol": symbol,
                        "action": "BOOK_PROFIT",
                        "confidence": 70,
                        "reasoning": f"Stock up {pnl_pct:.1f}%. Consider booking partial profits.",
                        "analysis_type": "profit_taking",
                        "current_price": holding.get("last_price"),
                        "target_price": holding.get("last_price", 0) * 1.1,
                        "stop_loss": holding.get("last_price", 0) * 0.95,
                        "quantity": int(holding.get("qty", 0) / 2),
                        "potential_impact": f"Lock in {pnl_pct/2:.1f}% profit on half position",
                        "risk_level": "low",
                        "time_horizon": "short_term"
                    }

                # REDUCE if overweight (>10% of portfolio)
                elif exposure_pct > 10:
                    recommendation = {
                        "symbol": symbol,
                        "action": "REDUCE",
                        "confidence": 65,
                        "reasoning": f"Position is {exposure_pct:.1f}% of portfolio. Reduce concentration risk.",
                        "analysis_type": "risk_management",
                        "current_price": holding.get("last_price"),
                        "quantity": int(holding.get("qty", 0) * 0.3),
                        "potential_impact": f"Reduce from {exposure_pct:.1f}% to {exposure_pct*0.7:.1f}%",
                        "risk_level": "medium",
                        "time_horizon": "medium_term"
                    }

                # Add recommendation to approval queue
                if recommendation:
                    await self.state_manager.add_to_approval_queue(recommendation)
                    logger.info(f"Generated {recommendation['action']} recommendation for {symbol}")

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")

    async def handle_market_alert(self, symbol: str, alert_type: str, data: Dict) -> None:
        """Handle real-time market alerts."""
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
        logger.info(f"Market alert handled for {symbol} with {len(responses)} responses")

    async def broadcast_to_ui(self, message: Dict[str, Any]) -> None:
        """Broadcast message to all connected WebSocket clients."""
        logger.info(f"UI Broadcast: {message.get('type', 'unknown')}")

    async def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents."""
        agents = {
            "portfolio_analyzer": {
                "name": "Portfolio Analyzer",
                "active": True,
                "status": "idle",
                "tools": ["analyze_portfolio"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "technical_analyst": {
                "name": "Technical Analyst",
                "active": True,
                "status": "idle",
                "tools": ["technical_analysis"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "fundamental_screener": {
                "name": "Fundamental Screener",
                "active": True,
                "status": "idle",
                "tools": ["fundamental_screening"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "risk_manager": {
                "name": "Risk Manager",
                "active": True,
                "status": "idle",
                "tools": ["risk_assessment"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "execution_agent": {
                "name": "Execution Agent",
                "active": True,
                "status": "idle",
                "tools": ["execute_trade"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "market_monitor": {
                "name": "Market Monitor",
                "active": True,
                "status": "idle",
                "tools": ["monitor_market"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "educational_agent": {
                "name": "Educational Agent",
                "active": True,
                "status": "idle",
                "tools": ["explain_concept", "explain_decision", "explain_portfolio"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            },
            "alert_agent": {
                "name": "Alert Agent",
                "active": True,
                "status": "idle",
                "tools": ["create_alert_rule", "list_alert_rules", "check_alerts", "delete_alert_rule"],
                "last_activity": datetime.now(timezone.utc).isoformat()
            }
        }

        return agents

    async def get_claude_status(self) -> ClaudeAuthStatus:
        """Get current Claude API status."""
        if self.claude_status is None:
            self.claude_status = await validate_claude_api(self.config.integration.anthropic_api_key)
        return self.claude_status


# Global orchestrator instance
_orchestrator: Optional[RoboTraderOrchestrator] = None


def get_orchestrator(config: Config) -> RoboTraderOrchestrator:
    """Get the global orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = RoboTraderOrchestrator(config)
    return _orchestrator


async def initialize_orchestrator(config: Config) -> RoboTraderOrchestrator:
    """Initialize and return the orchestrator."""
    orchestrator = get_orchestrator(config)
    await orchestrator.initialize()
    return orchestrator