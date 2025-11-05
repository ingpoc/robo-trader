"""
Portfolio Intelligence Analyzer Service

Analyzes portfolio stocks with available data (earnings, news, fundamentals),
determines if data is sufficient/outdated, optimizes prompts, and provides recommendations.
All activity is logged to AI Transparency.
"""

import logging
import time
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Any, Optional
import json

from loguru import logger
from claude_agent_sdk import tool

from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout
from src.core.database_state.database_state import DatabaseStateManager
from src.core.database_state.configuration_state import ConfigurationState
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.services.claude_agent.analysis_logger import AnalysisLogger

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
        state_manager: DatabaseStateManager,
        config_state: ConfigurationState,
        analysis_logger: AnalysisLogger,
        broadcast_coordinator: Optional[Any] = None,
        status_coordinator: Optional[Any] = None
    ):
        self.state_manager = state_manager
        self.config_state = config_state
        self.analysis_logger = analysis_logger
        self.broadcast_coordinator = broadcast_coordinator
        self.status_coordinator = status_coordinator
        self.client_manager = None
        self._active_analyses: Dict[str, Any] = {}  # Track active analyses for logging
    
    async def initialize(self) -> None:
        """Initialize the analyzer with Claude SDK client."""
        try:
            self.client_manager = await ClaudeSDKClientManager.get_instance()
            logger.info("Portfolio Intelligence Analyzer initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Portfolio Intelligence Analyzer: {e}")
            raise
    
    async def analyze_portfolio_intelligence(
        self,
        agent_name: str,
        symbols: Optional[List[str]] = None,
        batch_info: Optional[Dict[str, Any]] = None
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
            print(f"DEBUG: PortfolioIntelligenceAnalyzer.analyze_portfolio_intelligence() called with agent_name={agent_name}, symbols={symbols}")
            logger.info(f"DEBUG: PortfolioIntelligenceAnalyzer.analyze_portfolio_intelligence() called with agent_name={agent_name}, symbols={symbols}")

            # Register active analysis
            PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id] = {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "symbols_count": 0,
                "agent_name": agent_name,
                "queued_for_batch_processing": True
            }
            PortfolioIntelligenceAnalyzer._active_analysis_count = len(PortfolioIntelligenceAnalyzer._active_analysis_tasks)

            # Broadcast analysis start
            await self._broadcast_analysis_status(
                status="analyzing",
                message=f"Starting portfolio intelligence analysis (will be queued for sequential execution)...",
                symbols_count=0,
                analysis_id=analysis_id
            )

            # Step 1: Get stocks with updates
            if symbols is None:
                print(f"DEBUG: Getting stocks with updates...")
                symbols = await self._get_stocks_with_updates()
                print(f"DEBUG: Found {len(symbols)} stocks with updates: {symbols[:5]}...")

            logger.info(f"Starting portfolio intelligence analysis for {len(symbols)} stocks: {symbols}")
            print(f"DEBUG: About to queue {len(symbols)} stocks for sequential analysis")

            # Update active analysis with symbol count
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["symbols_count"] = len(symbols)

            # Broadcast status update with symbol count
            await self._broadcast_analysis_status(
                status="analyzing",
                message=f"Queuing {len(symbols)} stocks for sequential analysis in AI_ANALYSIS queue",
                symbols_count=len(symbols),
                analysis_id=analysis_id
            )

            # Step 2: Get available data for each stock
            stocks_data = await self._gather_stocks_data(symbols)

            # Step 3: Create system prompt for Claude
            system_prompt = self._create_system_prompt(stocks_data)

            # Step 4: Create decision log for AI Transparency
            session_id = f"portfolio_intelligence_{int(datetime.now(timezone.utc).timestamp())}"
            decision_log = await self.analysis_logger.start_trade_analysis(
                session_id=session_id,
                symbol="PORTFOLIO",
                decision_id=analysis_id
            )
            self._active_analyses[analysis_id] = decision_log

            # Step 5: Create MCP server and tools for Claude (read/update prompts)
            mcp_server, tool_names = self._create_claude_tools()

            # Step 6: Get current prompts
            prompts = await self._get_current_prompts()

            # Step 7: Log initial analysis step
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="data_gathering",
                description=f"Gathered data for {len(symbols)} stocks with recent updates",
                input_data={"symbols": symbols, "stocks_data_summary": {s: d.get("data_summary", {}) for s, d in stocks_data.items()}},
                reasoning=f"Analyzing {len(symbols)} stocks with recent earnings, news, or fundamentals data",
                confidence_score=0.0,
                duration_ms=0
            )

            # Step 8: Execute Claude analysis
            print(f"DEBUG: About to execute Claude analysis for {len(stocks_data)} stocks...")
            logger.info(f"DEBUG: About to execute Claude analysis for {len(stocks_data)} stocks with analysis_id={analysis_id}")

            analysis_result = await self._execute_claude_analysis(
                system_prompt=system_prompt,
                stocks_data=stocks_data,
                prompts=prompts,
                analysis_id=analysis_id,
                mcp_server=mcp_server,
                tool_names=tool_names
            )

            print(f"DEBUG: Claude analysis completed. Result keys: {list(analysis_result.keys())}")
            logger.info(f"DEBUG: Claude analysis completed. Result keys: {list(analysis_result.keys())}")

            # Step 9: Log to AI Transparency
            await self._log_to_transparency(
                analysis_id=analysis_id,
                agent_name=agent_name,
                symbols=symbols,
                stocks_data=stocks_data,
                analysis_result=analysis_result
            )

            # Unregister active analysis
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["status"] = "completed"
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["recommendations_count"] = len(analysis_result.get("recommendations", []))
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["prompt_updates_count"] = len(analysis_result.get("prompt_updates", []))
                # Keep completed for a short time, then remove
                # (Cleanup happens in broadcast or after timeout)
            PortfolioIntelligenceAnalyzer._active_analysis_count = len([t for t in PortfolioIntelligenceAnalyzer._active_analysis_tasks.values() if t.get("status") == "running"])

            # Broadcast analysis complete
            await self._broadcast_analysis_status(
                status="idle",
                message=f"Portfolio intelligence analysis completed: {len(analysis_result.get('recommendations', []))} recommendations",
                symbols_count=len(symbols),
                analysis_id=analysis_id,
                recommendations_count=len(analysis_result.get("recommendations", [])),
                prompt_updates_count=len(analysis_result.get("prompt_updates", []))
            )

            return {
                "status": "success",
                "analysis_id": analysis_id,
                "symbols_analyzed": len(symbols),
                "recommendations_count": len(analysis_result.get("recommendations", [])),
                "prompt_updates": len(analysis_result.get("prompt_updates", [])),
                "analysis_result": analysis_result,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Portfolio intelligence analysis failed: {e}", exc_info=True)
            await self._log_error_to_transparency(analysis_id, agent_name, str(e))

            # Unregister failed analysis
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["status"] = "failed"
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["error"] = str(e)[:200]
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["failed_at"] = datetime.now(timezone.utc).isoformat()
            PortfolioIntelligenceAnalyzer._active_analysis_count = len([t for t in PortfolioIntelligenceAnalyzer._active_analysis_tasks.values() if t.get("status") == "running"])

            # Broadcast analysis failed
            await self._broadcast_analysis_status(
                status="idle",
                message=f"Portfolio intelligence analysis failed: {str(e)[:100]}",
                symbols_count=0,
                analysis_id=analysis_id,
                error=str(e)[:200]
            )

            raise TradingError(
                message=f"Portfolio intelligence analysis failed: {str(e)}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )
    
    async def _get_stocks_with_updates(self) -> List[str]:
        """Get stocks from portfolio that have recent updates (earnings, news, fundamentals)."""
        try:
            # Get portfolio holdings
            portfolio = await self.state_manager.get_portfolio()
            if not portfolio or not portfolio.holdings:
                logger.warning("No portfolio holdings found")
                return []
            
            portfolio_symbols = [
                holding.get("symbol") 
                for holding in portfolio.holdings 
                if holding.get("symbol")
            ]
            
            if not portfolio_symbols:
                return []
            
            # Get stock state store
            stock_state_store = self.state_manager.get_stock_state_store()
            await stock_state_store.initialize()
            
            # Find stocks with recent updates (within last 7 days)
            stocks_with_updates = []
            cutoff_date = date.today() - timedelta(days=7)
            
            for symbol in portfolio_symbols:
                state = await stock_state_store.get_state(symbol)
                
                # Check if any data type was updated recently
                # Convert date strings to date objects if needed
                news_check_date = state.last_news_check
                if isinstance(news_check_date, str):
                    try:
                        # Handle YYYY-MM-DD format from database
                        if len(news_check_date) == 10 and news_check_date.count('-') == 2:
                            from datetime import datetime
                            news_check_date = datetime.strptime(news_check_date, '%Y-%m-%d').date()
                        else:
                            # Handle ISO datetime format with timezone
                            news_check_date = datetime.fromisoformat(news_check_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        news_check_date = None

                earnings_check_date = state.last_earnings_check
                if isinstance(earnings_check_date, str):
                    try:
                        # Handle YYYY-MM-DD format from database
                        if len(earnings_check_date) == 10 and earnings_check_date.count('-') == 2:
                            from datetime import datetime
                            earnings_check_date = datetime.strptime(earnings_check_date, '%Y-%m-%d').date()
                        else:
                            # Handle ISO datetime format with timezone
                            earnings_check_date = datetime.fromisoformat(earnings_check_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        earnings_check_date = None

                fundamentals_check_date = state.last_fundamentals_check
                if isinstance(fundamentals_check_date, str):
                    try:
                        # Handle YYYY-MM-DD format from database
                        if len(fundamentals_check_date) == 10 and fundamentals_check_date.count('-') == 2:
                            from datetime import datetime
                            fundamentals_check_date = datetime.strptime(fundamentals_check_date, '%Y-%m-%d').date()
                        else:
                            # Handle ISO datetime format with timezone
                            fundamentals_check_date = datetime.fromisoformat(fundamentals_check_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        fundamentals_check_date = None
                
                has_recent_news = (
                    news_check_date and 
                    isinstance(news_check_date, date) and
                    news_check_date >= cutoff_date
                )
                has_recent_earnings = (
                    earnings_check_date and 
                    isinstance(earnings_check_date, date) and
                    earnings_check_date >= cutoff_date
                )
                has_recent_fundamentals = (
                    fundamentals_check_date and 
                    isinstance(fundamentals_check_date, date) and
                    fundamentals_check_date >= cutoff_date
                )
                
                if has_recent_news or has_recent_earnings or has_recent_fundamentals:
                    stocks_with_updates.append(symbol)
            
            # If no stocks with recent updates, return stocks that need updates (oldest first)
            if not stocks_with_updates:
                logger.info("No stocks with recent updates, selecting oldest stocks")
                news_stocks = await stock_state_store.get_oldest_news_stocks(portfolio_symbols, limit=5)
                earnings_stocks = await stock_state_store.get_oldest_earnings_stocks(portfolio_symbols, limit=5)
                fundamentals_stocks = await stock_state_store.get_oldest_fundamentals_stocks(portfolio_symbols, limit=5)
                stocks_with_updates = list(set(news_stocks + earnings_stocks + fundamentals_stocks))[:10]
            
            logger.info(f"Cutoff date: {cutoff_date}, Found {len(stocks_with_updates)} stocks with updates: {stocks_with_updates}")

            # Add debug info for first few stocks
            if portfolio_symbols:
                sample_symbol = portfolio_symbols[0]
                sample_state = await stock_state_store.get_state(sample_symbol)
                logger.info(f"Sample stock {sample_symbol}: news={sample_state.last_news_check}, earnings={sample_state.last_earnings_check}, fundamentals={sample_state.last_fundamentals_check}")

            return stocks_with_updates
            
        except Exception as e:
            logger.error(f"Error getting stocks with updates: {e}", exc_info=True)
            return []
    
    async def _gather_stocks_data(self, symbols: List[str]) -> Dict[str, Dict[str, Any]]:
        """Gather all available data (earnings, news, fundamentals) for each stock."""
        stocks_data = {}
        
        for symbol in symbols:
            try:
                # Get earnings data
                earnings = await self.state_manager.get_earnings_for_symbol(symbol, limit=5)
                
                # Get news data
                news = await self.state_manager.get_news_for_symbol(symbol, limit=10)
                
                # Get fundamental analysis (if available)
                fundamental_analysis = await self.state_manager.get_fundamental_analysis(symbol, limit=1)
                
                # Get stock state (last check dates)
                stock_state_store = self.state_manager.get_stock_state_store()
                await stock_state_store.initialize()
                state = await stock_state_store.get_state(symbol)
                
                stocks_data[symbol] = {
                    "symbol": symbol,
                    "earnings": earnings,
                    "news": news,
                    "fundamental_analysis": [fa.to_dict() if hasattr(fa, 'to_dict') else fa for fa in fundamental_analysis],
                    "last_news_check": state.last_news_check.isoformat() if state.last_news_check and hasattr(state.last_news_check, 'isoformat') else (str(state.last_news_check) if state.last_news_check else None),
                    "last_earnings_check": state.last_earnings_check.isoformat() if state.last_earnings_check and hasattr(state.last_earnings_check, 'isoformat') else (str(state.last_earnings_check) if state.last_earnings_check else None),
                    "last_fundamentals_check": state.last_fundamentals_check.isoformat() if state.last_fundamentals_check and hasattr(state.last_fundamentals_check, 'isoformat') else (str(state.last_fundamentals_check) if state.last_fundamentals_check else None),
                    "data_summary": {
                        "earnings_count": len(earnings),
                        "news_count": len(news),
                        "fundamental_count": len(fundamental_analysis)
                    }
                }
                
            except Exception as e:
                logger.error(f"Error gathering data for {symbol}: {e}")
                stocks_data[symbol] = {
                    "symbol": symbol,
                    "error": str(e),
                    "data_summary": {"earnings_count": 0, "news_count": 0, "fundamental_count": 0}
                }
        
        return stocks_data
    
    def _create_system_prompt(self, stocks_data: Dict[str, Dict[str, Any]]) -> str:
        """Create system prompt explaining the analysis task to Claude."""
        
        symbols_list = "\n".join([f"- {symbol}: {data.get('data_summary', {})}" for symbol, data in stocks_data.items()])
        
        system_prompt = f"""You are an expert financial analyst with access to comprehensive portfolio data analysis capabilities.

YOUR TASK:
Analyze the following stocks and their available data (earnings, news, fundamentals) to:
1. Evaluate if the available data is sufficient and current enough for making investment recommendations
2. Determine if any data is outdated or missing critical information
3. Review the prompts currently used to fetch data from Perplexity API
4. Optimize these prompts if they are not extracting sufficient or quality data
5. Provide investment recommendations based on the analysis

STOCKS TO ANALYZE:
{symbols_list}

AVAILABLE DATA FOR EACH STOCK:
- Earnings reports (EPS, revenue, guidance, dates)
- News items (headlines, sentiment, relevance scores, dates)
- Fundamental analysis (valuation, profitability, growth metrics, dates)
- Last update timestamps for each data type

YOUR PROCESS:

STEP 1: DATA QUALITY ASSESSMENT
For each stock, evaluate:
- Is the earnings data current (within last quarter)?
- Is the news data recent (within last week for major news)?
- Is the fundamental analysis comprehensive?
- Are there gaps in critical information?

STEP 2: PROMPT REVIEW AND OPTIMIZATION
- Review the current prompts used for fetching data from Perplexity:
  * earnings_processor: Used to fetch earnings and fundamental metrics
  * news_processor: Used to fetch market news and updates
  * deep_fundamental_processor: Used for comprehensive fundamental analysis
  
- For each prompt, evaluate:
  * Is it extracting all necessary data?
  * Is it requesting data in the right format?
  * Could it be improved to get better/more comprehensive data?
  
- If a prompt needs improvement:
  * Provide an optimized version
  * Explain why the change is needed
  * Ensure the optimized prompt maintains JSON structure compatibility

STEP 3: RECOMMENDATIONS
Based on your analysis, provide:
- Investment recommendations (BUY/HOLD/SELL) for each stock
- Confidence level (0-100%) for each recommendation
- Key reasons supporting each recommendation
- Risk factors to consider
- Suggested action if data is insufficient

IMPORTANT INSTRUCTIONS:
- Use the provided tools to read and update prompts in the database
- All your analysis and thinking should be transparent and logged
- If data is outdated, recommend fetching fresh data before making decisions
- Be conservative in recommendations if data quality is uncertain
- Focus on actionable insights, not generic advice

TOOLS AVAILABLE:
- read_prompt(prompt_name): Read current prompt from database
- update_prompt(prompt_name, new_content, description): Update prompt in database
- log_analysis_step(step_type, description, reasoning): Log your analysis steps
- log_recommendation(symbol, action, confidence, reasoning): Log investment recommendations

Begin your analysis now. Be thorough, transparent, and actionable."""

        return system_prompt
    
    def _create_claude_tools(self) -> tuple:
        """Create tools and MCP server for Claude to interact with prompts and logging."""
        
        @tool("read_prompt", "Read a prompt from the database by name", {
            "prompt_name": str
        })
        async def read_prompt_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Read prompt from database."""
            try:
                prompt_name = args.get("prompt_name")
                prompt_config = await self.config_state.get_prompt_config(prompt_name)
                
                return {
                    "content": [{"type": "text", "text": json.dumps(prompt_config, indent=2)}]
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error reading prompt: {str(e)}"}],
                    "is_error": True
                }
        
        @tool("update_prompt", "Update a prompt in the database", {
            "prompt_name": str,
            "new_content": str,
            "description": str
        })
        async def update_prompt_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Update prompt in database."""
            try:
                prompt_name = args.get("prompt_name")
                new_content = args.get("new_content")
                description = args.get("description", f"Optimized by Claude AI at {datetime.now(timezone.utc).isoformat()}")
                
                success = await self.config_state.update_prompt_config(
                    prompt_name=prompt_name,
                    prompt_content=new_content,
                    description=description
                )
                
                return {
                    "content": [{"type": "text", "text": f"Successfully updated prompt: {prompt_name}"}]
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error updating prompt: {str(e)}"}],
                    "is_error": True
                }
        
        @tool("log_analysis_step", "Log an analysis step for transparency", {
            "step_type": str,
            "description": str,
            "reasoning": str
        })
        async def log_analysis_step_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Log analysis step."""
            try:
                logger.info(f"Analysis step: {args.get('step_type')} - {args.get('description')}")
                return {
                    "content": [{"type": "text", "text": "Analysis step will be logged to AI Transparency"}]
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error logging step: {str(e)}"}],
                    "is_error": True
                }
        
        @tool("log_recommendation", "Log an investment recommendation", {
            "symbol": str,
            "action": str,
            "confidence": float,
            "reasoning": str
        })
        async def log_recommendation_tool(args: Dict[str, Any]) -> Dict[str, Any]:
            """Log recommendation."""
            try:
                logger.info(f"Recommendation: {args.get('symbol')} - {args.get('action')} (confidence: {args.get('confidence')})")
                return {
                    "content": [{"type": "text", "text": "Recommendation will be logged"}]
                }
            except Exception as e:
                return {
                    "content": [{"type": "text", "text": f"Error logging recommendation: {str(e)}"}],
                    "is_error": True
                }
        
        # Create MCP server with tools
        from claude_agent_sdk import create_sdk_mcp_server
        
        mcp_server = create_sdk_mcp_server(
            name="portfolio_intelligence",
            version="1.0.0",
            tools=[
                read_prompt_tool,
                update_prompt_tool,
                log_analysis_step_tool,
                log_recommendation_tool
            ]
        )
        
        # Return MCP server and tool names for allowed_tools
        tool_names = [
            "mcp__portfolio_intelligence__read_prompt",
            "mcp__portfolio_intelligence__update_prompt",
            "mcp__portfolio_intelligence__log_analysis_step",
            "mcp__portfolio_intelligence__log_recommendation"
        ]
        
        return mcp_server, tool_names
    
    async def _get_current_prompts(self) -> Dict[str, str]:
        """Get current prompts from database."""
        prompts = {}
        prompt_names = ["earnings_processor", "news_processor", "deep_fundamental_processor"]
        
        for prompt_name in prompt_names:
            try:
                prompt_config = await self.config_state.get_prompt_config(prompt_name)
                prompts[prompt_name] = prompt_config.get("content", "Prompt not found")
            except Exception as e:
                logger.warning(f"Could not get prompt {prompt_name}: {e}")
                prompts[prompt_name] = "Prompt not found"
        
        return prompts
    
    async def _execute_claude_analysis(
        self,
        system_prompt: str,
        stocks_data: Dict[str, Dict[str, Any]],
        prompts: Dict[str, str],
        analysis_id: str,
        mcp_server: Any,
        tool_names: List[str]
    ) -> Dict[str, Any]:
        """Execute Claude analysis with provided tools."""

        import time
        start_time = time.time()

        print(f"DEBUG: _execute_claude_analysis() called with {len(stocks_data)} stocks, analysis_id={analysis_id}")
        logger.info(f"DEBUG: _execute_claude_analysis() called with {len(stocks_data)} stocks, analysis_id={analysis_id}")

        try:
            # Initialize analysis logging for portfolio analysis (not a single trade)
            # Create a generic decision log for portfolio analysis
            from src.services.claude_agent.analysis_logger import TradeDecisionLog
            decision_log = TradeDecisionLog(
                decision_id=analysis_id,
                session_id=f"portfolio_{int(time.time())}",
                symbol="PORTFOLIO",  # Generic symbol for portfolio analysis
                action="ANALYZE"  # Portfolio analysis action
            )
            self.analysis_logger.active_decisions[analysis_id] = decision_log

            # Log Claude analysis start
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="ai_analysis",
                description="Starting Claude AI analysis of portfolio stocks",
                input_data={"stocks_count": len(stocks_data), "prompts_count": len(prompts)},
                reasoning="Using Claude AI to analyze data quality, optimize prompts, and provide recommendations",
                confidence_score=0.0,
                duration_ms=0
            )
            
            # Create Claude SDK client with MCP server
            from claude_agent_sdk import ClaudeAgentOptions
            options = ClaudeAgentOptions(
                system_prompt=system_prompt,
                mcp_servers={"portfolio_intelligence": mcp_server},
                allowed_tools=tool_names,
                max_turns=15
            )
            
            client = await self.client_manager.get_client("portfolio_analysis", options)
            
            # Create user prompt with data summary (limit size to avoid token limits)
            stocks_summary = {
                symbol: {
                    "data_summary": data.get("data_summary", {}),
                    "last_checks": {
                        "news": data.get("last_news_check"),
                        "earnings": data.get("last_earnings_check"),
                        "fundamentals": data.get("last_fundamentals_check")
                    },
                    "earnings_count": len(data.get("earnings", [])),
                    "news_count": len(data.get("news", [])),
                    "fundamental_count": len(data.get("fundamental_analysis", []))
                }
                for symbol, data in stocks_data.items()
            }
            
            user_prompt = f"""Analyze the following stocks and their data:

STOCKS SUMMARY:
{json.dumps(stocks_summary, indent=2)}

CURRENT PROMPTS USED FOR DATA FETCHING:
{json.dumps(prompts, indent=2)}

TASK:
1. Assess data quality and freshness for each stock
2. Review current prompts using the read_prompt tool
3. Optimize prompts if needed using the update_prompt tool
4. Provide investment recommendations for each stock
5. Use log_analysis_step to document your thinking process

Begin your analysis now."""

            # Execute query with streaming and real-time progress monitoring
            print(f"DEBUG: Starting Claude analysis with streaming (analysis_id={analysis_id})")
            logger.info(f"DEBUG: Starting Claude analysis with streaming for {len(stocks_data)} stocks")

            # Send query and monitor responses in real-time
            await client.query(user_prompt)

            response_chunks = []
            last_activity = time.time()
            message_timeout = 120.0  # Timeout if no message for 2 minutes (indicates hung state)

            print(f"DEBUG: Entering receive_messages() loop to monitor Claude progress")

            async for message in client.receive_messages():
                # Check for message timeout (indicates hung state)
                time_since_activity = time.time() - last_activity
                if time_since_activity > message_timeout:
                    error_msg = f"No activity from Claude for {int(time_since_activity)} seconds - analysis may be hung"
                    logger.error(error_msg)
                    print(f"DEBUG: {error_msg}")
                    raise TradingError(
                        error_msg,
                        category=ErrorCategory.SYSTEM,
                        severity=ErrorSeverity.HIGH,
                        recoverable=False
                    )

                last_activity = time.time()

                # Process message based on type for real-time progress tracking
                try:
                    from claude_agent_sdk import AssistantMessage, ToolUseBlock, TextBlock, ResultMessage, ToolResultBlock

                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, ToolUseBlock):
                                # Claude is ACTIVELY using a tool - RUNNING
                                print(f"DEBUG: Claude using tool: {block.name}")
                                logger.info(f"Claude executing tool: {block.name}")

                            elif isinstance(block, TextBlock):
                                # Claude is responding - RUNNING
                                response_chunks.append(block.text)
                                print(f"DEBUG: Received text chunk ({len(block.text)} chars, {len(response_chunks)} total chunks)")
                                logger.info(f"Claude text response ({len(response_chunks)} chunks total)")

                    elif isinstance(message, ToolResultBlock):
                        # Tool completed - STILL RUNNING
                        print(f"DEBUG: Tool result received")
                        logger.info("Tool execution result received")

                    elif isinstance(message, ResultMessage):
                        # Analysis complete - READY
                        print(f"DEBUG: Claude analysis complete (ResultMessage received)")
                        logger.info("Claude analysis completed - ResultMessage received")
                        break

                except Exception as e:
                    logger.warning(f"Error processing message type: {e}")
                    # Continue processing - don't fail on message type issues
                    pass

            print(f"DEBUG: Exit receive_messages() loop - received {len(response_chunks)} text chunks")
            logger.info(f"Claude analysis streaming complete: {len(response_chunks)} response chunks collected")

            # Assemble final response from chunks
            response = "\n".join(response_chunks) if response_chunks else ""
            execution_time_ms = int((time.time() - start_time) * 1000)

            print(f"DEBUG: Final response length: {len(response)} chars, execution time: {execution_time_ms}ms")
            
            # Log Claude analysis completion
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="ai_analysis",
                description="Completed Claude AI analysis",
                input_data={"response_length": len(str(response))},
                reasoning=f"Claude analyzed {len(stocks_data)} stocks and provided recommendations",
                confidence_score=0.0,
                duration_ms=execution_time_ms
            )
            
            # Parse response (Claude SDK returns structured response)
            # Extract recommendations and prompt updates from response

            # DEBUG: Log Claude's actual response
            print(f"DEBUG: Claude response type: {type(response)}")
            print(f"DEBUG: Claude response length: {len(response)}")
            print(f"DEBUG: Claude response (first 500 chars): {response[:500]}")
            logger.info(f"DEBUG: Claude response type: {type(response)}, length: {len(response)}")

            # Parse Claude's response to extract structured recommendations and updates
            recommendations = []
            prompt_updates = []
            data_assessment = {}

            # Extract Claude's actual thinking content (query_with_timeout already returns clean text)
            response_text = response  # query_with_timeout already returns Claude's actual thinking as string

            # Store analysis in database
            await self._store_analysis_results(analysis_id, stocks_data, response_text, recommendations)

            # Store recommendations if any were extracted
            for rec in recommendations:
                await self._store_recommendation(rec, analysis_id)

            analysis_result = {
                "recommendations": recommendations,
                "prompt_updates": prompt_updates,
                "data_assessment": data_assessment,
                "claude_response": response_text,
                "execution_time_ms": execution_time_ms
            }
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error executing Claude analysis: {e}", exc_info=True)
            # Log error to transparency
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="error",
                description=f"Claude analysis failed: {str(e)}",
                input_data={},
                reasoning="Error occurred during Claude AI analysis",
                confidence_score=0.0,
                duration_ms=int((time.time() - start_time) * 1000)
            )
            raise
    
    async def _log_analysis_step(
        self,
        step_type: str,
        description: str,
        reasoning: str,
        analysis_id: Optional[str] = None
    ) -> None:
        """Log analysis step to AI Transparency."""
        try:
            if not analysis_id:
                analysis_id = f"portfolio_analysis_{int(datetime.now(timezone.utc).timestamp())}"
            
            # Create decision log if it doesn't exist
            if analysis_id not in self._active_analyses:
                decision_log = await self.analysis_logger.start_trade_analysis(
                    session_id=f"portfolio_intelligence_{int(datetime.now(timezone.utc).timestamp())}",
                    symbol="PORTFOLIO",  # Portfolio-wide analysis
                    decision_id=analysis_id
                )
                self._active_analyses[analysis_id] = decision_log
            
            # Log the analysis step
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type=step_type,
                description=description,
                input_data={},
                reasoning=reasoning,
                confidence_score=0.0,
                duration_ms=0
            )
        except Exception as e:
            logger.warning(f"Error logging analysis step: {e}")
    
    async def _log_to_transparency(
        self,
        analysis_id: str,
        agent_name: str,
        symbols: List[str],
        stocks_data: Dict[str, Dict[str, Any]],
        analysis_result: Dict[str, Any]
    ) -> None:
        """Log complete analysis to AI Transparency."""
        try:
            # Final logging step
            await self.analysis_logger.log_analysis_step(
                decision_id=analysis_id,
                step_type="completion",
                description=f"Portfolio intelligence analysis completed for {len(symbols)} stocks",
                input_data={
                    "symbols": symbols,
                    "recommendations_count": len(analysis_result.get("recommendations", [])),
                    "prompt_updates_count": len(analysis_result.get("prompt_updates", []))
                },
                reasoning=f"Analysis complete. Check Claude's response for detailed recommendations and prompt optimizations.",
                confidence_score=0.0,
                duration_ms=analysis_result.get("execution_time_ms", 0)
            )

            # Complete the trade decision to save it to database
            completed_decision = await self.analysis_logger.complete_trade_decision(
                decision_id=analysis_id,
                executed=False,  # Portfolio analysis generates recommendations, not executed trades
                execution_result={
                    "analysis_type": "portfolio_intelligence",
                    "agent_name": agent_name,
                    "symbols_analyzed": len(symbols),
                    "recommendations_generated": len(analysis_result.get("recommendations", [])),
                    "prompt_updates_generated": len(analysis_result.get("prompt_updates", [])),
                    "execution_time_ms": analysis_result.get("execution_time_ms", 0),
                    "claude_response_length": len(analysis_result.get("claude_response", "")),
                    "data_assessment": analysis_result.get("data_assessment", {})
                }
            )

            if completed_decision:
                logger.info(f"Analysis {analysis_id} completed and saved to AI Transparency database")
            else:
                logger.warning(f"Failed to complete analysis decision {analysis_id}")

        except Exception as e:
            logger.warning(f"Error logging to transparency: {e}")
    
    async def _broadcast_analysis_status(
        self,
        status: str,
        message: str,
        symbols_count: int = 0,
        analysis_id: Optional[str] = None,
        recommendations_count: int = 0,
        prompt_updates_count: int = 0,
        error: Optional[str] = None
    ) -> None:
        """Broadcast analysis status via WebSocket."""
        if not self.broadcast_coordinator:
            return

        try:
            # Broadcast portfolio analysis activity update only
            # NOTE: Don't call broadcast_claude_status_update() as it conflicts with
            # the actual Claude SDK status managed by SessionCoordinator
            activity_message = {
                "type": "portfolio_analysis_update",
                "status": status,
                "message": message,
                "analysis_id": analysis_id,
                "symbols_count": symbols_count,
                "recommendations_count": recommendations_count,
                "prompt_updates_count": prompt_updates_count,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            await self.broadcast_coordinator.broadcast_to_ui(activity_message)

            # Trigger system health update via status coordinator
            # This ensures the System Health tab shows updated AI Analysis scheduler status
            if self.status_coordinator:
                try:
                    await self.status_coordinator.broadcast_status_change("ai_analysis", status)
                except Exception as e:
                    logger.warning(f"Failed to trigger system health update: {e}")

        except Exception as e:
            logger.warning(f"Failed to broadcast analysis status: {e}")
    
    @classmethod
    def get_active_analysis_status(cls) -> Dict[str, Any]:
        """Get status of active AI analysis tasks for system health."""
        running_tasks = [t for t in cls._active_analysis_tasks.values() if t.get("status") == "running"]
        
        if not running_tasks:
            return {
                "status": "idle",
                "active_count": 0,
                "last_activity": None
            }
        
        # Get most recent active task
        latest_task = max(running_tasks, key=lambda t: t.get("started_at", ""))
        
        return {
            "status": "running",
            "active_count": len(running_tasks),
            "current_task": {
                "analysis_id": latest_task.get("analysis_id"),
                "agent_name": latest_task.get("agent_name"),
                "symbols_count": latest_task.get("symbols_count", 0),
                "started_at": latest_task.get("started_at")
            },
            "last_activity": latest_task.get("started_at")
        }
    
    async def _log_error_to_transparency(
        self,
        analysis_id: str,
        agent_name: str,
        error_message: str
    ) -> None:
        """Log error to AI Transparency."""
        try:
            # Try to log error if analysis_id exists
            if analysis_id in self._active_analyses:
                await self.analysis_logger.log_analysis_step(
                    decision_id=analysis_id,
                    step_type="error",
                    description=f"Analysis failed: {error_message}",
                    input_data={"agent_name": agent_name},
                    reasoning="Error occurred during portfolio intelligence analysis",
                    confidence_score=0.0,
                    duration_ms=0
                )
            
            logger.error(f"Error in analysis {analysis_id}: {error_message}")
        except Exception as e:
            logger.warning(f"Error logging error to transparency: {e}")

    async def _store_analysis_results(self, analysis_id: str, stocks_data: Dict[str, Dict[str, Any]], response_text: str, recommendations: List[Dict[str, Any]]) -> None:
        """Store analysis results in the database using proper locked methods."""
        try:
            # Store analysis for each symbol
            current_time = datetime.now(timezone.utc).isoformat()

            for symbol in stocks_data.keys():
                analysis_data = {
                    "symbol": symbol,
                    "analysis_type": "portfolio_intelligence",
                    "claude_response": response_text,
                    "recommendations_count": len(recommendations),
                    "data_quality": {
                        "has_earnings": len(stocks_data[symbol].get("earnings", [])) > 0,
                        "has_news": len(stocks_data[symbol].get("news", [])) > 0,
                        "has_fundamentals": len(stocks_data[symbol].get("fundamental_analysis", [])) > 0,
                        "last_updates": stocks_data[symbol].get("data_summary", {})
                    },
                    "execution_metadata": {
                        "analysis_id": analysis_id,
                        "timestamp": current_time
                    }
                }

                # Use safe locked method instead of direct database access
                success = await self.config_state.store_analysis_history(
                    symbol=symbol,
                    timestamp=current_time,
                    analysis=json.dumps(analysis_data)
                )

                if success:
                    logger.debug(f"Stored analysis for {symbol}")
                else:
                    logger.warning(f"Failed to store analysis for {symbol}")

            logger.info(f"Stored analysis results for {len(stocks_data)} symbols in database")

        except Exception as e:
            logger.error(f"Failed to store analysis results: {e}", exc_info=True)

    async def _store_recommendation(self, recommendation: Dict[str, Any], analysis_id: str) -> None:
        """Store individual recommendation in the database using proper locked method."""
        try:
            # Use safe locked method instead of direct database access
            success = await self.config_state.store_recommendation(
                symbol=recommendation.get("symbol", "UNKNOWN"),
                recommendation_type=recommendation.get("action", "HOLD"),
                confidence_score=recommendation.get("confidence", 0.0),
                reasoning=recommendation.get("reasoning", ""),
                analysis_type="portfolio_intelligence"
            )

            if success:
                logger.debug(f"Stored recommendation for {recommendation.get('symbol', 'UNKNOWN')}")
            else:
                logger.warning(f"Failed to store recommendation for {recommendation.get('symbol', 'UNKNOWN')}")

        except Exception as e:
            logger.error(f"Failed to store recommendation: {e}", exc_info=True)