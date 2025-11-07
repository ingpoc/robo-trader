"""
Paper Trading MCP Server.

Model Context Protocol (MCP) server for paper trading operations.
Provides Claude with tools to perform market research, execute paper trades,
and check application status through a queue-based architecture.

Architecture: MCP Tools → Task Creation → Queue Processing → Workflow SDK → Database
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource, Tool, TextContent, ImageContent, EmbeddedResource,
    CallToolRequest, CallToolResult, ListToolsRequest, ListToolsResult
)

from src.core.di import DependencyContainer
from src.models.scheduler import QueueName, TaskType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity

logger = logging.getLogger(__name__)


class PaperTradingMCPServer:
    """
    MCP Server for paper trading operations.

    Provides Claude with tools to:
    - Research symbols using Perplexity API
    - Execute paper trades with strategy tracking
    - Check application status and performance
    - Analyze portfolio data
    - Optimize prompts for better data quality

    All operations go through the SequentialQueueManager to maintain
    workflow isolation and turn limit management.
    """

    def __init__(self, container: DependencyContainer):
        """Initialize MCP server with dependency container."""
        self.container = container
        self.server = Server("paper-trading")
        self._task_service = None
        self._workflow_manager = None
        self._paper_trading_state = None
        self._portfolio_analysis_state = None

        # Register MCP tools
        self._register_tools()

    async def initialize(self) -> None:
        """Initialize MCP server dependencies."""
        try:
            # Get required services from container
            self._task_service = await self.container.get("task_service")
            self._workflow_manager = await self.container.get("workflow_sdk_manager")
            database_state_manager = await self.container.get("database_state_manager")

            self._paper_trading_state = database_state_manager.paper_trading
            self._portfolio_analysis_state = database_state_manager.portfolio_analysis

            logger.info("Paper Trading MCP Server initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise TradingError(
                f"MCP Server initialization failed: {e}",
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.CRITICAL,
                recoverable=False
            )

    def _register_tools(self) -> None:
        """Register all MCP tools."""

        # Research Tools
        @self.server.list_tools()
        async def list_tools() -> ListToolsResult:
            """List all available MCP tools."""
            tools = [
                Tool(
                    name="research_symbol",
                    description="Research a stock symbol using Perplexity API and market data",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock symbol to research (e.g., RELIANCE, TCS)"
                            },
                            "query": {
                                "type": "string",
                                "description": "Research query or focus area"
                            },
                            "research_type": {
                                "type": "string",
                                "enum": ["market_overview", "financial_analysis", "technical_analysis", "news_sentiment"],
                                "description": "Type of research to perform",
                                "default": "market_overview"
                            },
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "description": "Task priority (1=low, 10=high)",
                                "default": 7
                            }
                        },
                        "required": ["symbol", "query"]
                    }
                ),
                Tool(
                    name="execute_paper_trade",
                    description="Execute a paper trade with strategy tracking",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "Stock symbol to trade"
                            },
                            "action": {
                                "type": "string",
                                "enum": ["BUY", "SELL"],
                                "description": "Trade action"
                            },
                            "quantity": {
                                "type": "integer",
                                "minimum": 1,
                                "description": "Number of shares"
                            },
                            "strategy_tag": {
                                "type": "string",
                                "description": "Strategy tag for performance tracking"
                            },
                            "confidence_score": {
                                "type": "number",
                                "minimum": 0.0,
                                "maximum": 1.0,
                                "description": "Confidence score (0-1)"
                            },
                            "entry_reason": {
                                "type": "string",
                                "description": "Reason for entering this trade"
                            },
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 9
                            }
                        },
                        "required": ["symbol", "action", "quantity", "strategy_tag", "entry_reason"]
                    }
                ),
                Tool(
                    name="check_paper_trading_status",
                    description="Get current paper trading account status and positions",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "include_positions": {
                                "type": "boolean",
                                "description": "Include current positions in response",
                                "default": True
                            },
                            "include_open_trades": {
                                "type": "boolean",
                                "description": "Include open trades in response",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="analyze_portfolio_data",
                    description="Analyze portfolio data and generate insights",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "analysis_type": {
                                "type": "string",
                                "enum": ["intelligence", "data_quality", "prompt_optimization"],
                                "description": "Type of portfolio analysis",
                                "default": "intelligence"
                            },
                            "symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific symbols to analyze (empty = all holdings)"
                            },
                            "priority": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 10,
                                "default": 6
                            }
                        }
                    }
                ),
                Tool(
                    name="optimize_prompt_template",
                    description="Optimize prompt templates for better data quality",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "template_type": {
                                "type": "string",
                                "enum": ["news", "earnings", "fundamentals"],
                                "description": "Type of prompt template to optimize"
                            },
                            "current_issues": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Current issues with data quality"
                            },
                            "sample_symbols": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Sample symbols to test optimization"
                            }
                        },
                        "required": ["template_type"]
                    }
                ),
                Tool(
                    name="get_strategy_performance",
                    description="Get strategy performance metrics and recommendations",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "days_back": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 365,
                                "description": "Number of days to analyze",
                                "default": 30
                            },
                            "strategy_tag": {
                                "type": "string",
                                "description": "Specific strategy to analyze (empty = all)"
                            }
                        }
                    }
                ),
                Tool(
                    name="calculate_monthly_pnl",
                    description="Calculate monthly P&L and performance metrics",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "year": {
                                "type": "integer",
                                "description": "Year to calculate (empty = current year)"
                            },
                            "month": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 12,
                                "description": "Month to calculate (empty = current month)"
                            }
                        }
                    }
                )
            ]

            return ListToolsResult(tools=tools)

        @self.server.call_tool()
        async def call_tool(name: str, arguments: Dict[str, Any]) -> CallToolResult:
            """Handle tool calls and route to appropriate handlers."""
            try:
                logger.info(f"MCP Tool called: {name} with arguments: {arguments}")

                if name == "research_symbol":
                    return await self._handle_research_symbol(arguments)
                elif name == "execute_paper_trade":
                    return await self._handle_execute_paper_trade(arguments)
                elif name == "check_paper_trading_status":
                    return await self._handle_check_status(arguments)
                elif name == "analyze_portfolio_data":
                    return await self._handle_analyze_portfolio(arguments)
                elif name == "optimize_prompt_template":
                    return await self._handle_optimize_prompt(arguments)
                elif name == "get_strategy_performance":
                    return await self._handle_get_strategy_performance(arguments)
                elif name == "calculate_monthly_pnl":
                    return await self._handle_calculate_monthly_pnl(arguments)
                else:
                    return CallToolResult(
                        content=[TextContent(type="text", text=f"Unknown tool: {name}")],
                        isError=True
                    )

            except Exception as e:
                logger.error(f"Error in tool {name}: {e}")
                return CallToolResult(
                    content=[TextContent(type="text", text=f"Error: {str(e)}")],
                    isError=True
                )

    async def _handle_research_symbol(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle market research requests."""
        try:
            symbol = args["symbol"].upper()
            query = args["query"]
            research_type = args.get("research_type", "market_overview")
            priority = args.get("priority", 7)

            # Create task for research queue
            task_id = await self._task_service.create_task(
                queue_name=QueueName.PAPER_TRADING_RESEARCH,
                task_type=TaskType.MARKET_RESEARCH_PERPLEXITY,
                payload={
                    "symbol": symbol,
                    "query": query,
                    "research_type": research_type,
                    "mcp_initiated": True,
                    "requested_at": datetime.utcnow().isoformat()
                },
                priority=priority
            )

            logger.info(f"Queued research task {task_id} for {symbol}: {query}")

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Research request queued successfully!\n\n"
                    f"Symbol: {symbol}\n"
                    f"Query: {query}\n"
                    f"Research Type: {research_type}\n"
                    f"Task ID: {task_id}\n"
                    f"Priority: {priority}\n\n"
                    f"Research will be processed through the PAPER_TRADING_RESEARCH queue. "
                    f"Results will be stored in the research log and available for future reference."
                )]
            )

        except Exception as e:
            logger.error(f"Error in research_symbol: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error queuing research: {str(e)}")],
                isError=True
            )

    async def _handle_execute_paper_trade(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle paper trade execution requests."""
        try:
            symbol = args["symbol"].upper()
            action = args["action"]
            quantity = args["quantity"]
            strategy_tag = args["strategy_tag"]
            confidence_score = args.get("confidence_score", 0.5)
            entry_reason = args["entry_reason"]
            priority = args.get("priority", 9)

            # Create task for execution queue
            task_id = await self._task_service.create_task(
                queue_name=QueueName.PAPER_TRADING_EXECUTION,
                task_type=TaskType.PAPER_TRADE_EXECUTION,
                payload={
                    "symbol": symbol,
                    "action": action,
                    "quantity": quantity,
                    "strategy_tag": strategy_tag,
                    "confidence_score": confidence_score,
                    "entry_reason": entry_reason,
                    "mcp_initiated": True,
                    "requested_at": datetime.utcnow().isoformat()
                },
                priority=priority
            )

            logger.info(f"Queued paper trade task {task_id}: {action} {quantity} {symbol}")

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Paper trade request queued successfully!\n\n"
                    f"Symbol: {symbol}\n"
                    f"Action: {action}\n"
                    f"Quantity: {quantity}\n"
                    f"Strategy: {strategy_tag}\n"
                    f"Confidence: {confidence_score:.2f}\n"
                    f"Reason: {entry_reason}\n"
                    f"Task ID: {task_id}\n"
                    f"Priority: {priority}\n\n"
                    f"Trade will be executed through the PAPER_TRADING_EXECUTION queue. "
                    f"Real market prices will be fetched from Zerodha API at execution time."
                )]
            )

        except Exception as e:
            logger.error(f"Error in execute_paper_trade: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error queuing paper trade: {str(e)}")],
                isError=True
            )

    async def _handle_check_status(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle status check requests."""
        try:
            include_positions = args.get("include_positions", True)
            include_open_trades = args.get("include_open_trades", True)

            # Get paper trading account status
            account = await self._paper_trading_state.get_account()
            if not account:
                return CallToolResult(
                    content=[TextContent(type="text", text="Paper trading account not found")],
                    isError=True
                )

            status_text = f"""📊 Paper Trading Account Status

💰 Financial Summary:
• Initial Capital: ₹{account.get('initial_capital', 0):,.2f}
• Current Cash: ₹{account.get('current_cash', 0):,.2f}
• Total Equity: ₹{account.get('total_equity', 0):,.2f}
• Total P&L: ₹{account.get('total_pnl', 0):,.2f}
• Daily P&L: ₹{account.get('day_pnl', 0):,.2f}
• Total Return: {account.get('total_return_percent', 0):.2f}%

"""

            if include_positions:
                # Get positions (this would need to be implemented in PaperTradingState)
                positions = await self._paper_trading_state.get_positions()
                if positions:
                    status_text += f"\n📈 Current Positions ({len(positions)}):\n"
                    for pos in positions[:5]:  # Show first 5 positions
                        status_text += f"• {pos['symbol']}: {pos['quantity']} @ ₹{pos['avg_cost_price']:.2f} (P&L: ₹{pos['unrealized_pnl']:.2f})\n"
                    if len(positions) > 5:
                        status_text += f"... and {len(positions) - 5} more positions\n"

            if include_open_trades:
                # Get open trades
                open_trades = await self._paper_trading_state.get_open_trades()
                if open_trades:
                    status_text += f"\n🔄 Open Trades ({len(open_trades)}):\n"
                    for trade in open_trades[:5]:  # Show first 5 trades
                        status_text += f"• {trade['symbol']} {trade['side']} {trade['quantity']} @ ₹{trade['entry_price']:.2f}\n"
                        status_text += f"  Strategy: {trade['strategy_tag']}, Confidence: {trade['confidence_score']:.2f}\n"
                    if len(open_trades) > 5:
                        status_text += f"... and {len(open_trades) - 5} more trades\n"

            status_text += f"\n📅 Last Updated: {account.get('last_updated', 'Unknown')}"

            return CallToolResult(content=[TextContent(type="text", text=status_text)])

        except Exception as e:
            logger.error(f"Error in check_paper_trading_status: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error checking status: {str(e)}")],
                isError=True
            )

    async def _handle_analyze_portfolio(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle portfolio analysis requests."""
        try:
            analysis_type = args.get("analysis_type", "intelligence")
            symbols = args.get("symbols", [])
            priority = args.get("priority", 6)

            # Create task for portfolio analysis queue
            task_id = await self._task_service.create_task(
                queue_name=QueueName.PORTFOLIO_ANALYSIS,
                task_type=TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS,
                payload={
                    "analysis_type": analysis_type,
                    "symbols": symbols,
                    "mcp_initiated": True,
                    "requested_at": datetime.utcnow().isoformat()
                },
                priority=priority
            )

            logger.info(f"Queued portfolio analysis task {task_id}: {analysis_type}")

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Portfolio analysis request queued successfully!\n\n"
                    f"Analysis Type: {analysis_type}\n"
                    f"Symbols: {symbols if symbols else 'All portfolio holdings'}\n"
                    f"Task ID: {task_id}\n"
                    f"Priority: {priority}\n\n"
                    f"Analysis will be processed through the PORTFOLIO_ANALYSIS queue. "
                    f"Results will focus on {analysis_type} and include recommendations for optimization."
                )]
            )

        except Exception as e:
            logger.error(f"Error in analyze_portfolio_data: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error queuing portfolio analysis: {str(e)}")],
                isError=True
            )

    async def _handle_optimize_prompt(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle prompt optimization requests."""
        try:
            template_type = args["template_type"]
            current_issues = args.get("current_issues", [])
            sample_symbols = args.get("sample_symbols", [])

            # Create task for prompt optimization
            task_id = await self._task_service.create_task(
                queue_name=QueueName.PORTFOLIO_ANALYSIS,
                task_type=TaskType.PROMPT_TEMPLATE_OPTIMIZATION,
                payload={
                    "template_type": template_type,
                    "current_issues": current_issues,
                    "sample_symbols": sample_symbols,
                    "mcp_initiated": True,
                    "requested_at": datetime.utcnow().isoformat()
                },
                priority=5
            )

            logger.info(f"Queued prompt optimization task {task_id}: {template_type}")

            return CallToolResult(
                content=[TextContent(
                    type="text",
                    text=f"Prompt optimization request queued successfully!\n\n"
                    f"Template Type: {template_type}\n"
                    f"Current Issues: {len(current_issues)} identified\n"
                    f"Sample Symbols: {len(sample_symbols)} for testing\n"
                    f"Task ID: {task_id}\n\n"
                    f"Optimization will analyze current template performance, "
                    f"test improvements with sample data, and implement the best version. "
                    f"Results will be stored for future use."
                )]
            )

        except Exception as e:
            logger.error(f"Error in optimize_prompt_template: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error queuing prompt optimization: {str(e)}")],
                isError=True
            )

    async def _handle_get_strategy_performance(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle strategy performance requests."""
        try:
            days_back = args.get("days_back", 30)
            strategy_tag = args.get("strategy_tag")

            # Get strategy performance data
            performance_data = await self._paper_trading_state.get_strategy_performance(days_back)

            if not performance_data:
                return CallToolResult(
                    content=[TextContent(type="text", text="No strategy performance data available")],
                    isError=True
                )

            # Filter by strategy if specified
            if strategy_tag:
                performance_data = [p for p in performance_data if p["strategy_tag"] == strategy_tag]

            # Format performance report
            report = f"📈 Strategy Performance Report (Last {days_back} days)\n\n"

            # Group by strategy
            strategies = {}
            for perf in performance_data:
                tag = perf["strategy_tag"]
                if tag not in strategies:
                    strategies[tag] = []
                strategies[tag].append(perf)

            for strategy_tag, data in strategies.items():
                # Get latest performance for this strategy
                latest = max(data, key=lambda x: x["performance_date"])

                report += f"🎯 {strategy_tag}\n"
                report += f"   Total Trades: {latest['total_trades']}\n"
                report += f"   Win Rate: {latest['win_rate']:.1f}%\n"
                report += f"   Total P&L: ₹{latest['total_pnl']:.2f}\n"
                report += f"   Profit Factor: {latest['profit_factor']:.2f}\n"
                report += f"   Effectiveness: {latest['effectiveness_score']:.1f}/100\n"
                report += f"   Recommendation: {latest['recommendation']}\n\n"

            return CallToolResult(content=[TextContent(type="text", text=report)])

        except Exception as e:
            logger.error(f"Error in get_strategy_performance: {e}")
            return CallToolResult(
                content=[TextContent(type="text", text=f"Error getting strategy performance: {str(e)}")],
                isError=True
            )

    async def _handle_calculate_monthly_pnl(self, args: Dict[str, Any]) -> CallToolResult:
        """Handle monthly P&L calculation requests."""
        try:
            # Default to current year and month
            now = datetime.utcnow()
            year = args.get("year", now.year)
            month = args.get("month", now.month)

            # Calculate monthly P&L
            summary = await self._paper_trading_state.calculate_monthly_pnl(year, month)

            if not summary:
                return CallToolResult(
                    content=[TextContent(type="text", text="No trading data available for the specified period")],
                    isError=True
                )

            report = f"""📊 Monthly P&L Summary - {year}-{month:02d}

💰 Financial Summary:
• Opening Equity: ₹{summary['opening_equity']:,.2f}
• Closing Equity: ₹{summary['closing_equity']:,.2f}
• Monthly P&L: ₹{summary['monthly_pnl']:,.2f}
• Monthly Return: {summary['monthly_pnl_percent']:.2f}%

📈 Trading Statistics:
• Total Trades: {summary['total_trades']}
• Winning Trades: {summary['winning_trades']}
• Win Rate: {summary.get('win_rate', 0):.1f}%
• Best Trade: ₹{summary['best_trade']:,.2f}
• Worst Trade: ₹{summary['worst_trade']:,.2f}

🎯 Strategy Breakdown:"""

            # Add strategy breakdown
            strategy_breakdown = summary.get('strategy_breakdown', {})
            if strategy_breakdown:
                for strategy, pnl in strategy_breakdown.items():
                    report += f"\n   {strategy}: ₹{pnl:,.2f}"

            # Add insights
            insights = summary.get('monthly_insights', [])
            if insights:
                report += f"\n\n💡 Key Insights:"
                for insight in insights:
                    report += f"\n• {insight}"

            return CallToolResult(content=[TextContent(type="text", text=report)])

        except Exception as e:
            logger.error(f"Error in calculate_monthly_pnl: {e}")
            return CallResult(
                content=[TextContent(type="text", text=f"Error calculating monthly P&L: {str(e)}")],
                isError=True
            )

    async def run(self) -> None:
        """Run the MCP server."""
        await self.initialize()

        # Run with stdio server
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="paper-trading",
                    server_version="1.0.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=None,
                        experimental_capabilities=None
                    )
                )
            )


# Global instance for the MCP server
_mcp_server: Optional[PaperTradingMCPServer] = None


async def create_paper_trading_mcp_server(container: DependencyContainer) -> PaperTradingMCPServer:
    """Create and initialize the paper trading MCP server."""
    global _mcp_server

    if _mcp_server is None:
        _mcp_server = PaperTradingMCPServer(container)
        await _mcp_server.initialize()

    return _mcp_server