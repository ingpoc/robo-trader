"""
Portfolio Intelligence Analyzer Service

Main orchestrator that delegates to focused modules:
- DataGatherer: Stock selection and data gathering
- PromptBuilder: Prompt and tool creation
- AnalysisExecutor: Claude execution
- LoggerHelper: Logging and transparency
- StorageHandler: Database operations

This maintains 100% backward compatibility with the original API.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from loguru import logger

from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.errors import ErrorCategory, ErrorSeverity, TradingError
from src.services.portfolio_intelligence.analysis_executor import \
    PortfolioAnalysisExecutor
from src.services.portfolio_intelligence.analysis_logger_helper import \
    PortfolioAnalysisLoggerHelper
# Import focused modules
from src.services.portfolio_intelligence.data_gatherer import \
    PortfolioDataGatherer
from src.services.portfolio_intelligence.prompt_builder import \
    PortfolioPromptBuilder
from src.services.portfolio_intelligence.storage_handler import \
    PortfolioStorageHandler

logger = logging.getLogger(__name__)


class PortfolioIntelligenceAnalyzer:
    """
    Analyzes portfolio stocks using Claude AI with intelligent prompt optimization.

    Responsibilities:
    - Identifies stocks with recent updates (earnings, news, fundamentals)
    - Analyzes available data quality and freshness
    - Optimizes prompts for Perplexity API queries
    - Provides investment recommendations
    - Logs all activity to AI Transparency
    """

    # Class-level tracking for active analysis tasks (accessed by StatusCoordinator)
    _active_analysis_tasks: Dict[str, Dict[str, Any]] = {}
    _active_analysis_count = 0

    def __init__(
        self,
        state_manager,
        config_state,
        analysis_logger,
        broadcast_coordinator: Optional[Any] = None,
        status_coordinator: Optional[Any] = None,
    ):
        self.state_manager = state_manager
        self.config_state = config_state
        self.analysis_logger = analysis_logger
        self.broadcast_coordinator = broadcast_coordinator
        self.status_coordinator = status_coordinator
        self.client_manager = None

        # Initialize focused modules
        self.data_gatherer = PortfolioDataGatherer(state_manager, config_state)
        self.prompt_builder = PortfolioPromptBuilder(config_state)
        self.logger_helper = PortfolioAnalysisLoggerHelper(
            analysis_logger, broadcast_coordinator, status_coordinator
        )
        self.storage_handler = PortfolioStorageHandler(config_state)
        self.analysis_executor = None  # Will be initialized after client_manager

    async def initialize(self) -> None:
        """Initialize the analyzer with Claude SDK client."""
        try:
            self.client_manager = await ClaudeSDKClientManager.get_instance()
            self.analysis_executor = PortfolioAnalysisExecutor(
                self.client_manager, self.analysis_logger
            )
            logger.info("Portfolio Intelligence Analyzer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Portfolio Intelligence Analyzer: {e}")
            raise

    async def analyze_portfolio_intelligence(
        self,
        agent_name: str,
        symbols: Optional[List[str]] = None,
        batch_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Main entry point for portfolio intelligence analysis.

        This method is now integrated with the queue system.
        Individual batches of 2-3 stocks are queued as separate AI_ANALYSIS tasks
        and executed sequentially by the queue manager.

        Args:
            agent_name: Name of the AI agent (e.g., "portfolio_analyzer")
            symbols: Optional list of symbols to analyze. If None, uses portfolio stocks with updates.

        Returns:
            Analysis results with recommendations and prompt updates
        """
        analysis_id = f"analysis_{int(datetime.now(timezone.utc).timestamp())}"

        try:
            # DEBUG: Log entry point
            logger.debug(
                f"PortfolioIntelligenceAnalyzer.analyze_portfolio_intelligence() called with agent_name={agent_name}, symbols={symbols}"
            )

            # Register active analysis
            PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id] = {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "symbols_count": 0,
                "agent_name": agent_name,
                "queued_for_batch_processing": True,
            }
            PortfolioIntelligenceAnalyzer._active_analysis_count = len(
                PortfolioIntelligenceAnalyzer._active_analysis_tasks
            )

            # Broadcast analysis start
            await self.logger_helper.broadcast_analysis_status(
                status="analyzing",
                message="Starting portfolio intelligence analysis (will be queued for sequential execution)...",
                symbols_count=0,
                analysis_id=analysis_id,
            )

            # Step 1: Get stocks with updates
            if symbols is None:
                logger.debug("Getting stocks with updates...")
                symbols = await self.data_gatherer.get_stocks_with_updates()
                logger.debug(
                    f"Found {len(symbols)} stocks with updates: {symbols[:5]}..."
                )

            logger.info(
                f"Starting portfolio intelligence analysis for {len(symbols)} stocks: {symbols}"
            )
            logger.debug(
                f"About to queue {len(symbols)} stocks for sequential analysis"
            )

            # Update active analysis with symbol count
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "symbols_count"
                ] = len(symbols)

            # Broadcast status update with symbol count
            await self.logger_helper.broadcast_analysis_status(
                status="analyzing",
                message=f"Queuing {len(symbols)} stocks for sequential analysis in AI_ANALYSIS queue",
                symbols_count=len(symbols),
                analysis_id=analysis_id,
            )

            # Step 2: Get available data for each stock
            stocks_data = await self.data_gatherer.gather_stocks_data(symbols)

            # Step 3: Create system prompt for Claude
            system_prompt = self.prompt_builder.create_system_prompt(stocks_data)

            # Step 4: Create decision log for AI Transparency
            session_id = (
                f"portfolio_intelligence_{int(datetime.now(timezone.utc).timestamp())}"
            )
            decision_log = await self.analysis_logger.start_trade_analysis(
                session_id=session_id, symbol="PORTFOLIO", decision_id=analysis_id
            )
            self.logger_helper._active_analyses[analysis_id] = decision_log

            # Step 5: Create MCP server and tools for Claude (read/update prompts)
            mcp_server, tool_names = self.prompt_builder.create_claude_tools()

            # Step 6: Get current prompts
            prompts = await self.prompt_builder.get_current_prompts()

            # Step 7: Log initial analysis step
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="data_gathering",
                description=f"Gathered data for {len(symbols)} stocks with recent updates",
                input_data={
                    "symbols": symbols,
                    "stocks_data_summary": {
                        s: d.get("data_summary", {}) for s, d in stocks_data.items()
                    },
                },
                reasoning=f"Analyzing {len(symbols)} stocks with recent earnings, news, or fundamentals data",
                confidence_score=0.0,
                duration_ms=0,
            )

            # Step 8: Execute Claude analysis
            logger.debug(
                f"About to execute Claude analysis for {len(stocks_data)} stocks with analysis_id={analysis_id}"
            )

            analysis_result = await self.analysis_executor.execute_claude_analysis(
                system_prompt=system_prompt,
                stocks_data=stocks_data,
                prompts=prompts,
                analysis_id=analysis_id,
                mcp_server=mcp_server,
                tool_names=tool_names,
            )

            logger.debug(
                f"Claude analysis completed. Result keys: {list(analysis_result.keys())}"
            )

            # Step 9: Store results in database
            await self.storage_handler.store_analysis_results(
                analysis_id,
                stocks_data,
                analysis_result.get("claude_response", ""),
                analysis_result.get("recommendations", []),
            )

            # Store recommendations if any were extracted
            for rec in analysis_result.get("recommendations", []):
                await self.storage_handler.store_recommendation(rec, analysis_id)

            # Step 10: Log to AI Transparency
            await self.logger_helper.log_to_transparency(
                analysis_id=analysis_id,
                agent_name=agent_name,
                symbols=symbols,
                stocks_data=stocks_data,
                analysis_result=analysis_result,
            )

            # Unregister active analysis
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "status"
                ] = "completed"
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "completed_at"
                ] = datetime.now(timezone.utc).isoformat()
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "recommendations_count"
                ] = len(analysis_result.get("recommendations", []))
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "prompt_updates_count"
                ] = len(analysis_result.get("prompt_updates", []))
            PortfolioIntelligenceAnalyzer._active_analysis_count = len(
                [
                    t
                    for t in PortfolioIntelligenceAnalyzer._active_analysis_tasks.values()
                    if t.get("status") == "running"
                ]
            )

            # Broadcast analysis complete
            await self.logger_helper.broadcast_analysis_status(
                status="idle",
                message=f"Portfolio intelligence analysis completed: {len(analysis_result.get('recommendations', []))} recommendations",
                symbols_count=len(symbols),
                analysis_id=analysis_id,
                recommendations_count=len(analysis_result.get("recommendations", [])),
                prompt_updates_count=len(analysis_result.get("prompt_updates", [])),
            )

            return {
                "status": "success",
                "analysis_id": analysis_id,
                "symbols_analyzed": len(symbols),
                "recommendations_count": len(
                    analysis_result.get("recommendations", [])
                ),
                "prompt_updates": len(analysis_result.get("prompt_updates", [])),
                "analysis_result": analysis_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

        except Exception as e:
            logger.error(f"Portfolio intelligence analysis failed: {e}", exc_info=True)
            await self.logger_helper.log_error_to_transparency(
                analysis_id, agent_name, str(e)
            )

            # Unregister failed analysis
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "status"
                ] = "failed"
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "error"
                ] = str(e)[:200]
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id][
                    "failed_at"
                ] = datetime.now(timezone.utc).isoformat()
            PortfolioIntelligenceAnalyzer._active_analysis_count = len(
                [
                    t
                    for t in PortfolioIntelligenceAnalyzer._active_analysis_tasks.values()
                    if t.get("status") == "running"
                ]
            )

            # Broadcast analysis failed
            await self.logger_helper.broadcast_analysis_status(
                status="idle",
                message=f"Portfolio intelligence analysis failed: {str(e)[:100]}",
                symbols_count=0,
                analysis_id=analysis_id,
                error=str(e)[:200],
            )

            raise TradingError(
                message=f"Portfolio intelligence analysis failed: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False,
            )

    @classmethod
    def get_active_analysis_status(cls) -> Dict[str, Any]:
        """Get status of active AI analysis tasks for system health."""
        running_tasks = [
            t
            for t in cls._active_analysis_tasks.values()
            if t.get("status") == "running"
        ]

        if not running_tasks:
            return {"status": "idle", "active_count": 0, "last_activity": None}

        # Get most recent active task
        latest_task = max(running_tasks, key=lambda t: t.get("started_at", ""))

        return {
            "status": "running",
            "active_count": len(running_tasks),
            "current_task": {
                "analysis_id": latest_task.get("analysis_id"),
                "agent_name": latest_task.get("agent_name"),
                "symbols_count": latest_task.get("symbols_count", 0),
                "started_at": latest_task.get("started_at"),
            },
            "last_activity": latest_task.get("started_at"),
        }
