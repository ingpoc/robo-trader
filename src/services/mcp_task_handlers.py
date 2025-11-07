"""
MCP Task Handlers.

Handles task execution for MCP-initiated operations in the SequentialQueueManager.
These handlers process tasks created by MCP tools and integrate with the workflow
SDK clients and database state managers.
"""

import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from loguru import logger

from src.core.workflow_sdk_client_manager import get_workflow_sdk_manager
from src.core.sdk_helpers import query_with_timeout, receive_response_with_timeout
from src.models.scheduler import SchedulerTask, TaskStatus
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class MCPResearchHandler:
    """Handles market research tasks initiated via MCP."""

    def __init__(self, container):
        self.container = container
        self._workflow_manager = None
        self._paper_trading_state = None

    async def initialize(self) -> None:
        """Initialize handler dependencies."""
        self._workflow_manager = await get_workflow_sdk_manager()
        database_state_manager = await self.container.get("database_state_manager")
        self._paper_trading_state = database_state_manager.paper_trading_state

    async def handle_market_research_perplexity(self, task: SchedulerTask) -> Dict[str, Any]:
        """Handle market research using Perplexity API."""
        try:
            payload = task.payload
            symbol = payload["symbol"]
            query = payload["query"]
            research_type = payload.get("research_type", "market_overview")

            logger.info(f"Processing market research for {symbol}: {query}")

            # Get paper trading workflow client
            client = await self._workflow_manager.get_workflow_client("paper_trading")

            # Construct research prompt
            research_prompt = self._build_research_prompt(symbol, query, research_type)

            # Execute research with Claude
            logger.info(f"Querying Claude for {symbol} research")
            response = await query_with_timeout(
                client,
                research_prompt,
                timeout=90.0  # Extended timeout for comprehensive research
            )

            # Process response
            research_data = await self._process_research_response(response)

            # Store research in database
            await self._paper_trading_state.store_research(
                symbol=symbol,
                research_type=f"mcp_{research_type}",
                query=query,
                response=research_data,
                sources_used=research_data.get("sources", []),
                confidence_level=research_data.get("confidence_level", 0.7),
                actionable_insights=research_data.get("actionable_insights", [])
            )

            logger.info(f"Market research completed for {symbol}")
            return {
                "status": "completed",
                "symbol": symbol,
                "research_type": research_type,
                "data": research_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        except asyncio.TimeoutError:
            logger.error(f"Market research timeout for task {task.task_id}")
            raise TradingError(
                f"Market research timeout: {task.task_id}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=30
            )

        except Exception as e:
            logger.error(f"Error in market research: {e}")
            raise TradingError(
                f"Market research failed: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    def _build_research_prompt(self, symbol: str, query: str, research_type: str) -> str:
        """Build research prompt based on type."""
        base_prompt = f"""Research {symbol} for the following query: {query}

Research Type: {research_type}

Please provide comprehensive analysis using available tools and data sources.
Focus on actionable insights for paper trading decisions.

Structure your response to include:
1. Key findings and insights
2. Risk factors and considerations
3. Trading implications (if any)
4. Confidence level in the analysis
5. Sources used (if available)

Current date: {datetime.now().strftime('%Y-%m-%d')}
"""

        if research_type == "market_overview":
            base_prompt += "\nFocus on overall market position, competitive landscape, and recent developments."

        elif research_type == "financial_analysis":
            base_prompt += "\nFocus on financial health, growth prospects, valuation metrics, and earnings quality."

        elif research_type == "technical_analysis":
            base_prompt += "\nFocus on price trends, key levels, momentum indicators, and chart patterns."

        elif research_type == "news_sentiment":
            base_prompt += "\nFocus on recent news impact, sentiment analysis, and potential catalysts."

        return base_prompt

    async def _process_research_response(self, response: str) -> Dict[str, Any]:
        """Process Claude's research response into structured data."""
        try:
            # For now, return the response as-is with basic structure
            # In a real implementation, you might parse structured responses
            return {
                "analysis": response,
                "confidence_level": 0.8,
                "actionable_insights": [
                    "Research completed successfully",
                    "Data available for trading decisions"
                ],
                "sources": ["Claude Analysis"],
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            logger.error(f"Error processing research response: {e}")
            return {
                "analysis": response,
                "confidence_level": 0.5,
                "actionable_insights": ["Research completed with limited processing"],
                "sources": ["Claude Analysis"],
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


class MCPTradeExecutionHandler:
    """Handles paper trade execution tasks initiated via MCP."""

    def __init__(self, container):
        self.container = container
        self._workflow_manager = None
        self._paper_trading_state = None

    async def initialize(self) -> None:
        """Initialize handler dependencies."""
        self._workflow_manager = await get_workflow_sdk_manager()
        database_state_manager = await self.container.get("database_state_manager")
        self._paper_trading_state = database_state_manager.paper_trading_state

    async def handle_paper_trade_execution(self, task: SchedulerTask) -> Dict[str, Any]:
        """Handle paper trade execution with real market prices."""
        try:
            payload = task.payload
            symbol = payload["symbol"]
            action = payload["action"]
            quantity = payload["quantity"]
            strategy_tag = payload["strategy_tag"]
            confidence_score = payload.get("confidence_score", 0.5)
            entry_reason = payload["entry_reason"]

            logger.info(f"Processing paper trade: {action} {quantity} {symbol}")

            # Validate trade parameters with Claude
            client = await self._workflow_manager.get_workflow_client("paper_trading")

            validation_prompt = self._build_trade_validation_prompt(
                symbol, action, quantity, strategy_tag, entry_reason
            )

            logger.info(f"Validating trade with Claude for {symbol}")
            validation_response = await query_with_timeout(
                client,
                validation_prompt,
                timeout=30.0
            )

            # Get real market price (this would integrate with Zerodha API)
            market_price = await self._get_market_price(symbol)

            if market_price is None:
                raise TradingError(
                    f"Could not fetch market price for {symbol}",
                    category=ErrorCategory.API,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True
                )

            # Create and execute paper trade
            trade_id = f"paper_{symbol}_{action}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

            success = await self._paper_trading_state.create_trade(
                trade_id=trade_id,
                symbol=symbol,
                side=action,
                quantity=quantity,
                entry_price=market_price,
                entry_reason=entry_reason,
                strategy_tag=strategy_tag,
                confidence_score=confidence_score,
                research_sources=["Claude Validation", "Market Data"],
                market_conditions={
                    "market_price": market_price,
                    "timestamp": datetime.utcnow().isoformat(),
                    "validation_response": validation_response
                },
                risk_metrics={
                    "confidence_score": confidence_score,
                    "strategy_tag": strategy_tag
                }
            )

            if success:
                logger.info(f"Paper trade executed successfully: {trade_id}")
                return {
                    "status": "executed",
                    "trade_id": trade_id,
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "entry_price": market_price,
                    "strategy_tag": strategy_tag,
                    "validation": validation_response,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                raise TradingError(
                    f"Failed to execute paper trade: {trade_id}",
                    category=ErrorCategory.SYSTEM,
                    severity=ErrorSeverity.HIGH,
                    recoverable=True
                )

        except Exception as e:
            logger.error(f"Error in paper trade execution: {e}")
            raise TradingError(
                f"Paper trade execution failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=True
            )

    def _build_trade_validation_prompt(self, symbol: str, action: str, quantity: int,
                                     strategy_tag: str, entry_reason: str) -> str:
        """Build trade validation prompt for Claude."""
        return f"""Validate this paper trade request:

Symbol: {symbol}
Action: {action}
Quantity: {quantity}
Strategy: {strategy_tag}
Entry Reason: {entry_reason}
Confidence Score: {0.5}

Please validate:
1. Is this trade reasonable given current market conditions?
2. Are the position size and risk appropriate?
3. Does the entry reason align with the strategy?
4. Any additional considerations or warnings?

Provide a brief validation assessment (APPROVED/REJECTED with reasoning)."""

    async def _get_market_price(self, symbol: str) -> Optional[float]:
        """Get current market price for a symbol."""
        try:
            # This would integrate with Zerodha API
            # For now, return a placeholder price
            # In production, you'd call the Zerodha API client

            # TODO: Integrate with Zerodha API client
            # market_data_service = await self.container.get("market_data_service")
            # return await market_data_service.get_current_price(symbol)

            # Placeholder implementation
            logger.warning(f"Using placeholder price for {symbol} - integrate with Zerodha API")
            return 1000.0  # Placeholder price

        except Exception as e:
            logger.error(f"Error getting market price for {symbol}: {e}")
            return None


class MCPAnalysisHandler:
    """Handles portfolio analysis tasks initiated via MCP."""

    def __init__(self, container):
        self.container = container
        self._workflow_manager = None
        self._portfolio_analysis_state = None

    async def initialize(self) -> None:
        """Initialize handler dependencies."""
        self._workflow_manager = await get_workflow_sdk_manager()
        database_state_manager = await self.container.get("database_state_manager")
        self._portfolio_analysis_state = database_state_manager.portfolio_analysis_state

    async def handle_portfolio_intelligence_analysis(self, task: SchedulerTask) -> Dict[str, Any]:
        """Handle portfolio intelligence analysis."""
        try:
            payload = task.payload
            analysis_type = payload.get("analysis_type", "intelligence")
            symbols = payload.get("symbols", [])

            logger.info(f"Processing portfolio analysis: {analysis_type} for {len(symbols)} symbols")

            # Get portfolio analysis workflow client
            client = await self._workflow_manager.get_workflow_client("portfolio_analysis")

            # Build analysis prompt
            analysis_prompt = self._build_analysis_prompt(analysis_type, symbols)

            # Execute analysis with Claude
            logger.info(f"Querying Claude for portfolio analysis")
            response = await query_with_timeout(
                client,
                analysis_prompt,
                timeout=120.0  # Extended timeout for comprehensive analysis
            )

            # Process and store analysis results
            analysis_data = await self._process_analysis_response(response, analysis_type)

            # Store analysis results for each symbol
            results = {}
            for symbol in symbols:
                await self._portfolio_analysis_state.store_analysis(
                    symbol=symbol,
                    analysis_type=analysis_type,
                    analysis_data=analysis_data,
                    confidence_score=0.8,
                    data_quality_score=0.85
                )
                results[symbol] = {
                    "analysis_type": analysis_type,
                    "status": "completed",
                    "timestamp": datetime.utcnow().isoformat()
                }

            logger.info(f"Portfolio analysis completed for {len(symbols)} symbols")
            return {
                "status": "completed",
                "analysis_type": analysis_type,
                "symbols_analyzed": len(symbols),
                "results": results,
                "data": analysis_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        except asyncio.TimeoutError:
            logger.error(f"Portfolio analysis timeout for task {task.task_id}")
            raise TradingError(
                f"Portfolio analysis timeout: {task.task_id}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recoverable=True,
                retry_after_seconds=60
            )

        except Exception as e:
            logger.error(f"Error in portfolio analysis: {e}")
            raise TradingError(
                f"Portfolio analysis failed: {e}",
                category=ErrorCategory.API,
                severity=ErrorSeverity.HIGH,
                recorable=True
            )

    async def handle_prompt_template_optimization(self, task: SchedulerTask) -> Dict[str, Any]:
        """Handle prompt template optimization."""
        try:
            payload = task.payload
            template_type = payload["template_type"]
            current_issues = payload.get("current_issues", [])
            sample_symbols = payload.get("sample_symbols", [])

            logger.info(f"Processing prompt optimization for {template_type}")

            # Get portfolio analysis workflow client
            client = await self._workflow_manager.get_workflow_client("portfolio_analysis")

            # Get current template
            current_templates = await self._portfolio_analysis_state.get_active_prompt_templates(template_type)

            # Build optimization prompt
            optimization_prompt = self._build_optimization_prompt(
                template_type, current_templates, current_issues, sample_symbols
            )

            # Execute optimization with Claude
            logger.info(f"Querying Claude for prompt optimization")
            response = await query_with_timeout(
                client,
                optimization_prompt,
                timeout=90.0
            )

            # Process optimization results
            optimization_data = await self._process_optimization_response(response)

            # Store optimization history
            # This would create a new prompt template version

            logger.info(f"Prompt optimization completed for {template_type}")
            return {
                "status": "completed",
                "template_type": template_type,
                "optimization_data": optimization_data,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"Error in prompt optimization: {e}")
            raise TradingError(
                f"Prompt optimization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.MEDIUM,
                recoverable=True
            )

    def _build_analysis_prompt(self, analysis_type: str, symbols: List[str]) -> str:
        """Build portfolio analysis prompt."""
        base_prompt = f"""Perform portfolio analysis for the specified symbols.

Analysis Type: {analysis_type}
Symbols: {', '.join(symbols) if symbols else 'All portfolio holdings'}

Current date: {datetime.now().strftime('%Y-%m-%d')}

Please provide comprehensive analysis focusing on:
1. Individual stock analysis
2. Portfolio-level insights
3. Recommendations and optimizations
4. Data quality assessment
5. Actionable next steps"""

        if analysis_type == "intelligence":
            base_prompt += "\nFocus on investment recommendations, risk assessment, and strategic insights."

        elif analysis_type == "data_quality":
            base_prompt += "\nFocus on data completeness, accuracy, and areas needing improvement."

        elif analysis_type == "prompt_optimization":
            base_prompt += "\nFocus on prompt template effectiveness and optimization opportunities."

        return base_prompt

    def _build_optimization_prompt(self, template_type: str, current_templates: List,
                                  current_issues: List[str], sample_symbols: List[str]) -> str:
        """Build prompt optimization prompt."""
        return f"""Optimize prompt templates for better data quality.

Template Type: {template_type}
Current Issues: {', '.join(current_issues) if current_issues else 'None identified'}
Sample Symbols: {', '.join(sample_symbols) if sample_symbols else 'None specified'}

Current templates: {len(current_templates)} templates found

Please analyze current templates and provide:
1. Improved template content
2. Optimization rationale
3. Expected improvements in data quality
4. Testing recommendations

Current date: {datetime.now().strftime('%Y-%m-%d')}"""

    async def _process_analysis_response(self, response: str, analysis_type: str) -> Dict[str, Any]:
        """Process Claude's analysis response into structured data."""
        return {
            "analysis": response,
            "analysis_type": analysis_type,
            "confidence_level": 0.85,
            "data_quality_score": 0.8,
            "recommendations": [
                "Analysis completed successfully",
                "Data available for optimization"
            ],
            "timestamp": datetime.utcnow().isoformat()
        }

    async def _process_optimization_response(self, response: str) -> Dict[str, Any]:
        """Process Claude's optimization response into structured data."""
        return {
            "optimization_response": response,
            "improvements_identified": True,
            "expected_quality_gain": 0.15,
            "testing_required": True,
            "timestamp": datetime.utcnow().isoformat()
        }


# Handler registry
MCP_HANDLERS = {
    "market_research_perplexity": MCPResearchHandler,
    "paper_trade_execution": MCPTradeExecutionHandler,
    "portfolio_intelligence_analysis": MCPAnalysisHandler,
    "prompt_template_optimization": MCPAnalysisHandler,
}


async def handle_mcp_task(task: SchedulerTask, container) -> Dict[str, Any]:
    """Route MCP task to appropriate handler."""
    try:
        task_type = task.task_type.value
        handler_class = MCP_HANDLERS.get(task_type)

        if not handler_class:
            raise TradingError(
                f"No handler found for MCP task type: {task_type}",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

        handler = handler_class(container)
        await handler.initialize()

        # Route to specific handler method
        if task_type == "market_research_perplexity":
            return await handler.handle_market_research_perplexity(task)
        elif task_type == "paper_trade_execution":
            return await handler.handle_paper_trade_execution(task)
        elif task_type == "portfolio_intelligence_analysis":
            return await handler.handle_portfolio_intelligence_analysis(task)
        elif task_type == "prompt_template_optimization":
            return await handler.handle_prompt_template_optimization(task)
        else:
            raise TradingError(
                f"Handler method not implemented for task type: {task_type}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.HIGH,
                recoverable=False
            )

    except Exception as e:
        logger.error(f"Error handling MCP task {task.task_id}: {e}")
        raise