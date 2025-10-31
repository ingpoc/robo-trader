"""
Claude SDK and AI Services Registration for Dependency Injection Container

Handles registration of Claude Agent SDK services:
- SDK client manager
- MCP servers and tools
- Claude agent services
- Strategy tracking and analysis
"""

import logging

logger = logging.getLogger(__name__)


async def register_sdk_services(container: 'DependencyContainer') -> None:
    """Register all Claude Agent SDK and AI services."""

    # Claude Agent Services
    async def create_tool_executor():
        from src.services.claude_agent.tool_executor import ToolExecutor
        risk_config = container.config.risk.__dict__ if hasattr(container.config, 'risk') else {}
        return ToolExecutor(container, risk_config)

    container._register_singleton("tool_executor", create_tool_executor)

    async def create_response_validator():
        from src.services.claude_agent.response_validator import ResponseValidator
        risk_config = container.config.risk.__dict__ if hasattr(container.config, 'risk') else {}
        return ResponseValidator(risk_config)

    container._register_singleton("response_validator", create_response_validator)

    async def create_claude_strategy_store():
        from src.stores.claude_strategy_store import ClaudeStrategyStore
        store = ClaudeStrategyStore(container.config)
        await store.initialize()
        return store

    container._register_singleton("claude_strategy_store", create_claude_strategy_store)

    # Claude SDK Authentication
    async def create_claude_sdk_auth():
        from src.services.claude_agent.sdk_auth import ClaudeSDKAuth
        sdk_auth = ClaudeSDKAuth(container)
        await sdk_auth.initialize()
        return sdk_auth

    container._register_singleton("claude_sdk_auth", create_claude_sdk_auth)

    # Claude SDK Client Manager - singleton (manages shared SDK clients)
    async def create_claude_sdk_client_manager():
        from .claude_sdk_client_manager import ClaudeSDKClientManager
        manager = await ClaudeSDKClientManager.get_instance()
        await manager.initialize()
        return manager

    container._register_singleton("claude_sdk_client_manager", create_claude_sdk_client_manager)

    # Claude Agent MCP Server
    async def create_claude_agent_mcp_server():
        from src.services.claude_agent.mcp_server import ClaudeAgentMCPServer
        mcp_server = ClaudeAgentMCPServer(container)
        await mcp_server.initialize()
        return mcp_server

    container._register_singleton("claude_agent_mcp_server", create_claude_agent_mcp_server)

    # Research Tracker Service
    async def create_research_tracker():
        from src.services.claude_agent.research_tracker import ResearchTracker
        strategy_store = await container.get("claude_strategy_store")
        return ResearchTracker(strategy_store)

    container._register_singleton("research_tracker", create_research_tracker)

    # Analysis Logger Service
    async def create_analysis_logger():
        from src.services.claude_agent.analysis_logger import AnalysisLogger
        strategy_store = await container.get("claude_strategy_store")
        return AnalysisLogger(strategy_store)

    container._register_singleton("analysis_logger", create_analysis_logger)

    # Execution Monitor Service
    async def create_execution_monitor():
        from src.services.claude_agent.execution_monitor import ExecutionMonitor
        strategy_store = await container.get("claude_strategy_store")
        return ExecutionMonitor(strategy_store)

    container._register_singleton("execution_monitor", create_execution_monitor)

    # Daily Strategy Evaluator Service
    async def create_daily_strategy_evaluator():
        from src.services.claude_agent.daily_strategy_evaluator import DailyStrategyEvaluator
        strategy_store = await container.get("claude_strategy_store")
        performance_calculator = await container.get("paper_trade_executor")
        return DailyStrategyEvaluator(strategy_store, performance_calculator)

    container._register_singleton("daily_strategy_evaluator", create_daily_strategy_evaluator)

    # Activity Summarizer Service
    async def create_activity_summarizer():
        from src.services.claude_agent.activity_summarizer import ActivitySummarizer
        strategy_store = await container.get("claude_strategy_store")
        return ActivitySummarizer(strategy_store)

    container._register_singleton("activity_summarizer", create_activity_summarizer)

    # Trade Decision Logger Service
    async def create_trade_decision_logger():
        from src.services.claude_agent.trade_decision_logger import TradeDecisionLogger
        trade_decision_logger = TradeDecisionLogger()
        await trade_decision_logger.initialize()
        return trade_decision_logger

    container._register_singleton("trade_decision_logger", create_trade_decision_logger)

    # Prompt Optimization Service
    async def create_prompt_optimization_service():
        from src.core.background_scheduler.clients.perplexity_client import PerplexityClient
        from src.services.prompt_optimization_service import PromptOptimizationService
        event_bus = await container.get("event_bus")
        configuration_state = await container.get("configuration_state")

        perplexity_client = PerplexityClient(configuration_state=configuration_state)

        prompt_service = PromptOptimizationService(
            config=container.config.get("prompt_optimization", {}),
            event_bus=event_bus,
            container=container,
            perplexity_client=perplexity_client
        )
        await prompt_service.initialize()
        return prompt_service

    container._register_singleton("prompt_optimization_service", create_prompt_optimization_service)

    # Prompt Optimization Tools for Claude MCP
    async def create_prompt_optimization_tools():
        from src.services.claude_agent.prompt_optimization_tools import PromptOptimizationTools
        prompt_service = await container.get("prompt_optimization_service")
        return PromptOptimizationTools(prompt_service)

    container._register_singleton("prompt_optimization_tools", create_prompt_optimization_tools)
