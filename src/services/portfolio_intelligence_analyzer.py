"""
Portfolio Intelligence Analyzer Service

Analyzes portfolio stocks with available data (earnings, news, fundamentals),
determines if data is sufficient/outdated, optimizes prompts, and provides recommendations.
All activity is logged to AI Transparency.
"""

import logging
from datetime import datetime, timezone, timedelta, date
from typing import Dict, List, Any, Optional
import json

from loguru import logger
from claude_agent_sdk import tool

from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout
from src.core.database_state import DatabaseStateManager
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
    
    def __init__(
        self,
        state_manager: DatabaseStateManager,
        config_state: ConfigurationState,
        analysis_logger: AnalysisLogger,
        broadcast_coordinator: Optional[Any] = None
    ):
        self.state_manager = state_manager
        self.config_state = config_state
        self.analysis_logger = analysis_logger
        self.broadcast_coordinator = broadcast_coordinator
        self.client_manager = None
        self._active_analyses: Dict[str, Any] = {}  # Track active analyses for logging
        
        # Class-level tracking for active analyses (shared across instances)
        if not hasattr(PortfolioIntelligenceAnalyzer, '_active_analysis_tasks'):
            PortfolioIntelligenceAnalyzer._active_analysis_tasks: Dict[str, Dict[str, Any]] = {}
            PortfolioIntelligenceAnalyzer._active_analysis_count = 0
    
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
        symbols: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Main entry point for portfolio intelligence analysis.
        
        Args:
            agent_name: Name of the AI agent (e.g., "portfolio_analyzer")
            symbols: Optional list of symbols to analyze. If None, uses portfolio stocks with updates.
        
        Returns:
            Analysis results with recommendations and prompt updates
        """
        analysis_id = f"analysis_{int(datetime.now(timezone.utc).timestamp())}"
        
        try:
            # Register active analysis
            PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id] = {
                "status": "running",
                "started_at": datetime.now(timezone.utc).isoformat(),
                "symbols_count": 0,
                "agent_name": agent_name
            }
            PortfolioIntelligenceAnalyzer._active_analysis_count = len(PortfolioIntelligenceAnalyzer._active_analysis_tasks)
            
            # Broadcast analysis start
            await self._broadcast_analysis_status(
                status="analyzing",
                message=f"Starting portfolio intelligence analysis...",
                symbols_count=0,
                analysis_id=analysis_id
            )
            
            # Step 1: Get stocks with updates
            if symbols is None:
                symbols = await self._get_stocks_with_updates()
            
            logger.info(f"Starting portfolio intelligence analysis for {len(symbols)} stocks: {symbols}")
            
            # Update active analysis with symbol count
            if analysis_id in PortfolioIntelligenceAnalyzer._active_analysis_tasks:
                PortfolioIntelligenceAnalyzer._active_analysis_tasks[analysis_id]["symbols_count"] = len(symbols)
            
            # Broadcast status update with symbol count
            await self._broadcast_analysis_status(
                status="analyzing",
                message=f"Analyzing {len(symbols)} stocks with recent updates",
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
            analysis_result = await self._execute_claude_analysis(
                system_prompt=system_prompt,
                stocks_data=stocks_data,
                prompts=prompts,
                analysis_id=analysis_id,
                mcp_server=mcp_server,
                tool_names=tool_names
            )
            
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
                        news_check_date = datetime.fromisoformat(news_check_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        news_check_date = None
                
                earnings_check_date = state.last_earnings_check
                if isinstance(earnings_check_date, str):
                    try:
                        earnings_check_date = datetime.fromisoformat(earnings_check_date.replace('Z', '+00:00')).date()
                    except (ValueError, AttributeError):
                        earnings_check_date = None
                
                fundamentals_check_date = state.last_fundamentals_check
                if isinstance(fundamentals_check_date, str):
                    try:
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
            
            logger.info(f"Found {len(stocks_with_updates)} stocks with updates: {stocks_with_updates}")
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
        
        try:
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
            
            # Execute query with timeout
            response = await query_with_timeout(
                client=client,
                prompt=user_prompt,
                timeout=300.0  # 5 minutes for comprehensive analysis
            )
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
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
            analysis_result = {
                "recommendations": [],
                "prompt_updates": [],
                "data_assessment": {},
                "claude_response": str(response),
                "execution_time_ms": execution_time_ms
            }
            
            # TODO: Parse Claude's response to extract structured recommendations and updates
            # For now, return the raw response for user review
            
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
            
            decision_log = self._active_analyses.get(analysis_id)
            steps_count = len(decision_log.analysis_steps) if decision_log and hasattr(decision_log, 'analysis_steps') else 0
            logger.info(f"Analysis {analysis_id} logged to AI Transparency with {steps_count} steps")
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
            # Broadcast Claude status update
            status_data = {
                "status": status,  # "analyzing" or "idle"
                "message": message,
                "current_task": f"portfolio_intelligence_{analysis_id}" if analysis_id else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "data": {
                    "analysis_id": analysis_id,
                    "symbols_count": symbols_count,
                    "recommendations_count": recommendations_count,
                    "prompt_updates_count": prompt_updates_count,
                    "error": error
                }
            }
            
            await self.broadcast_coordinator.broadcast_claude_status_update(status_data)
            
            # Also broadcast portfolio analysis activity update
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
            
            # Trigger system health update when status changes
            # This ensures System Health tab shows updated AI Analysis scheduler status
            # The status coordinator will automatically pick up the change via get_system_status()
            # which calls _get_ai_analysis_status() which reads from PortfolioIntelligenceAnalyzer
            
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

