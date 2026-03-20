"""
Enhanced Paper Trading MCP Server using Claude Agent SDK.

Model Context Protocol (MCP) server with progressive discovery and token efficiency.
Provides Claude with tools to perform market research, execute paper trades,
and check application status through SDK-based architecture.

Architecture: SDK @tools → Task Creation → Queue Processing → Workflow SDK → Database
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from claude_agent_sdk import tool, create_sdk_mcp_server
from src.core.di import DependencyContainer
from src.models.scheduler import QueueName, TaskType
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from .progressive_discovery_manager import ProgressiveDiscoveryManager

logger = logging.getLogger(__name__)


def _parse_month_value(month_value: Any) -> int:
    """Parse a month name or number into a numeric month."""
    if isinstance(month_value, int):
        if 1 <= month_value <= 12:
            return month_value
        raise ValueError("Month integer must be between 1 and 12")

    if not month_value:
        return datetime.now().month

    if isinstance(month_value, str) and month_value.isdigit():
        month_number = int(month_value)
        if 1 <= month_number <= 12:
            return month_number
        raise ValueError("Month string must be between 1 and 12")

    normalized = str(month_value).strip().lower()
    month_map = {
        "january": 1, "jan": 1,
        "february": 2, "feb": 2,
        "march": 3, "mar": 3,
        "april": 4, "apr": 4,
        "may": 5,
        "june": 6, "jun": 6,
        "july": 7, "jul": 7,
        "august": 8, "aug": 8,
        "september": 9, "sep": 9, "sept": 9,
        "october": 10, "oct": 10,
        "november": 11, "nov": 11,
        "december": 12, "dec": 12,
    }
    if normalized not in month_map:
        raise ValueError(f"Unsupported month value: {month_value}")
    return month_map[normalized]


async def _resolve_single_account_id(container: DependencyContainer) -> str:
    """Resolve a single active paper account or fail loud."""
    account_manager = await container.get("paper_trading_account_manager")
    accounts = await account_manager.get_all_accounts()
    if not accounts:
        raise TradingError(
            "Monthly P&L analysis cannot run because no paper trading account exists",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
        )

    if len(accounts) > 1:
        account_ids = ", ".join(account.account_id for account in accounts)
        raise TradingError(
            f"Monthly P&L analysis requires an explicit paper trading account selection; available accounts: {account_ids}",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
        )

    return accounts[0].account_id


# Tool implementations using SDK @tool decorator

@tool(
    "research_symbol",
    "Research a stock symbol using Perplexity API and market data",
    {
        "symbol": str,
        "query": str,
        "research_type": str,
        "priority": int
    }
)
async def research_symbol(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Research a stock symbol with progressive discovery.

    Args:
        args: Tool arguments including symbol, query, research_type, priority
        container: DI container for services

    Returns:
        Research results with discovery suggestions
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        symbol = args.get("symbol", "").upper()
        query = args.get("query", "")
        research_type = args.get("research_type", "market_overview")
        priority = args.get("priority", 7)

        if not symbol:
            return {
                "content": [{"type": "text", "text": "Error: Symbol is required"}],
                "is_error": True
            }

        if not query:
            return {
                "content": [{"type": "text", "text": "Error: Research query is required"}],
                "is_error": True
            }

        # Get task service
        task_service = await container.get("task_service")

        # Create research task
        task = await task_service.create_task(
            queue_name=QueueName.PAPER_TRADING_RESEARCH,
            task_type=TaskType.MARKET_RESEARCH_PERPLEXITY,
            payload={
                "symbol": symbol,
                "query": query,
                "research_type": research_type,
                "discovery_context": {
                    "tool_name": "research_symbol",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            priority=priority
        )

        result_text = f"Research task created for {symbol}\n"
        result_text += f"Task ID: {task.task_id}\n"
        result_text += f"Research Type: {research_type}\n"
        result_text += f"Query: {query}\n\n"
        result_text += "Suggested next steps:\n"
        result_text += "- Use 'analyze_portfolio_data' to include in portfolio analysis\n"
        result_text += "- Use 'execute_paper_trade' if research indicates trading opportunity\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "analyze_portfolio_data", "reason": "Include research in portfolio analysis"},
                {"tool": "execute_paper_trade", "reason": "Execute trade based on research"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in research_symbol tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "execute_paper_trade",
    "Execute a paper trade with strategy tracking and discovery",
    {
        "account_id": str,
        "symbol": str,
        "action": str,
        "quantity": int,
        "strategy_tag": str,
        "confidence_score": float,
        "entry_reason": str,
        "priority": int
    }
)
async def execute_paper_trade(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Execute a paper trade with progressive discovery.

    Args:
        args: Tool arguments for trade execution
        container: DI container for services

    Returns:
        Trade execution results with discovery suggestions
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        account_id = args.get("account_id", "").strip()
        symbol = args.get("symbol", "").upper()
        action = args.get("action", "").upper()
        quantity = args.get("quantity", 0)
        strategy_tag = args.get("strategy_tag", "")
        confidence_score = args.get("confidence_score", 0.0)
        entry_reason = args.get("entry_reason", "")
        priority = args.get("priority", 9)

        # Validation
        if not account_id:
            return {
                "content": [{"type": "text", "text": "Error: account_id is required"}],
                "is_error": True
            }

        if not symbol:
            return {
                "content": [{"type": "text", "text": "Error: Symbol is required"}],
                "is_error": True
            }

        if action not in ["BUY", "SELL"]:
            return {
                "content": [{"type": "text", "text": "Error: Action must be BUY or SELL"}],
                "is_error": True
            }

        if quantity <= 0:
            return {
                "content": [{"type": "text", "text": "Error: Quantity must be positive"}],
                "is_error": True
            }

        if not strategy_tag:
            return {
                "content": [{"type": "text", "text": "Error: Strategy tag is required"}],
                "is_error": True
            }

        if not entry_reason:
            return {
                "content": [{"type": "text", "text": "Error: Entry reason is required"}],
                "is_error": True
            }

        capability_service = await container.get("trading_capability_service")
        capability_snapshot = await capability_service.get_snapshot(account_id=account_id)
        if not capability_snapshot.automation_allowed:
            blocker = capability_snapshot.blockers[0] if capability_snapshot.blockers else "Trading readiness is blocked"
            return {
                "content": [{"type": "text", "text": f"Error: {blocker}"}],
                "is_error": True
            }

        # Get task service
        task_service = await container.get("task_service")

        # Create trade execution task
        task = await task_service.create_task(
            queue_name=QueueName.PAPER_TRADING_EXECUTION,
            task_type=TaskType.PAPER_TRADE_EXECUTION,
            payload={
                "account_id": account_id,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "strategy_tag": strategy_tag,
                "confidence_score": confidence_score,
                "entry_reason": entry_reason,
                "discovery_context": {
                    "tool_name": "execute_paper_trade",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            priority=priority
        )

        result_text = "Paper trade execution task created\n"
        result_text += f"Task ID: {task.task_id}\n"
        result_text += f"Account: {account_id}\n"
        result_text += f"Symbol: {symbol}\n"
        result_text += f"Action: {action} {quantity} shares\n"
        result_text += f"Strategy: {strategy_tag}\n"
        result_text += f"Confidence: {confidence_score:.2f}\n"
        result_text += f"Reason: {entry_reason}\n\n"
        result_text += "Suggested next steps:\n"
        result_text += "- Use 'get_strategy_performance' to track strategy effectiveness\n"
        result_text += "- Use 'monitor_positions' to watch trade progress\n"
        result_text += "- Use 'calculate_monthly_pnl' for performance analysis\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "get_strategy_performance", "reason": "Track strategy effectiveness"},
                {"tool": "check_paper_trading_status", "reason": "Monitor account status"},
                {"tool": "calculate_monthly_pnl", "reason": "Analyze performance"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in execute_paper_trade tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "check_paper_trading_status",
    "Get current paper trading account status and positions",
    {
        "account_id": str,
        "include_positions": bool,
        "include_open_trades": bool
    }
)
async def check_paper_trading_status(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Check paper trading account status.

    Args:
        args: Tool arguments for status check
        container: DI container for services

    Returns:
        Account status information
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        account_id = args.get("account_id", "").strip()
        include_positions = args.get("include_positions", True)
        include_open_trades = args.get("include_open_trades", True)

        account_manager = await container.get("paper_trading_account_manager")
        store = await container.get("paper_trading_store")
        all_accounts = await account_manager.get_all_accounts()

        if not all_accounts:
            return {
                "content": [{"type": "text", "text": "Error: No paper trading account exists"}],
                "is_error": True
            }

        if not account_id:
            result_text = "Paper Trading Account Status\n"
            result_text += f"Accounts: {len(all_accounts)}\n\n"
            for account in all_accounts[:5]:
                balance = await account_manager.get_account_balance(account.account_id)
                result_text += f"- {account.account_id}: ₹{balance['current_balance']:,.2f} balance, ₹{balance['buying_power']:,.2f} buying power\n"

            result_text += "\nProvide account_id for detailed status on a specific trading account.\n"
            return {
                "content": [{"type": "text", "text": result_text}],
                "discovery_suggestions": [
                    {"tool": "execute_paper_trade", "reason": "Run trades against a specific account"},
                    {"tool": "analyze_portfolio_data", "reason": "Review portfolio state"}
                ]
            }

        account = await account_manager.get_account(account_id)
        if account is None:
            return {
                "content": [{"type": "text", "text": f"Error: Paper trading account '{account_id}' was not found"}],
                "is_error": True
            }

        balance = await account_manager.get_account_balance(account_id)
        positions = await account_manager.get_open_positions(account_id) if include_positions else []
        open_trades = await store.get_open_trades(account_id) if include_open_trades else []

        result_text = "Paper Trading Account Status\n"
        result_text += f"Account: {account.account_id}\n"
        result_text += f"Balance: ₹{balance['current_balance']:,.2f}\n"
        result_text += f"Buying Power: ₹{balance['buying_power']:,.2f}\n"
        result_text += f"Locked Capital: ₹{balance['locked_capital']:,.2f}\n"

        if include_positions:
            result_text += f"\nPositions: {len(positions)}\n"
            result_text += "Top positions:\n"
            for pos in positions[:5]:
                result_text += f"  {pos.symbol}: {pos.quantity} @ ₹{pos.entry_price:,.2f}\n"

        if include_open_trades:
            result_text += f"\nOpen Trades: {len(open_trades)}\n"

        result_text += "\nSuggested next steps:\n"
        result_text += "- Use 'analyze_portfolio_data' for detailed analysis\n"
        result_text += "- Use 'get_strategy_performance' to evaluate strategies\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "analyze_portfolio_data", "reason": "Detailed portfolio analysis"},
                {"tool": "get_strategy_performance", "reason": "Evaluate trading strategies"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in check_paper_trading_status tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "analyze_portfolio_data",
    "Analyze portfolio data and generate insights with progressive discovery",
    {
        "analysis_type": str,
        "symbols": List[str],
        "priority": int
    }
)
async def analyze_portfolio_data(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Analyze portfolio data with progressive discovery.

    Args:
        args: Tool arguments for portfolio analysis
        container: DI container for services

    Returns:
        Portfolio analysis results with discovery suggestions
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        analysis_type = args.get("analysis_type", "intelligence")
        symbols = args.get("symbols", [])
        priority = args.get("priority", 7)

        # Get task service
        task_service = await container.get("task_service")

        # Create portfolio analysis task
        task = await task_service.create_task(
            queue_name=QueueName.PORTFOLIO_ANALYSIS,
            task_type=TaskType.PORTFOLIO_INTELLIGENCE_ANALYSIS,
            payload={
                "analysis_type": analysis_type,
                "symbols": symbols,
                "discovery_context": {
                    "tool_name": "analyze_portfolio_data",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            priority=priority
        )

        result_text = "Portfolio analysis task created\n"
        result_text += f"Task ID: {task.task_id}\n"
        result_text += f"Analysis Type: {analysis_type}\n"

        if symbols:
            result_text += f"Symbols: {', '.join(symbols)}\n"
        else:
            result_text += "Symbols: All portfolio holdings\n"

        result_text += "\nSuggested next steps:\n"
        result_text += "- Use 'optimize_prompt_template' to improve data quality\n"
        result_text += "- Use 'research_symbol' for deeper analysis of specific holdings\n"
        result_text += "- Use 'execute_paper_trade' based on analysis insights\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "optimize_prompt_template", "reason": "Improve data quality for future analysis"},
                {"tool": "research_symbol", "reason": "Deep dive into specific holdings"},
                {"tool": "execute_paper_trade", "reason": "Act on analysis insights"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in analyze_portfolio_data tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "get_strategy_performance",
    "Get strategy performance metrics and insights",
    {}
)
async def get_strategy_performance(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Get strategy performance metrics.

    Args:
        args: Tool arguments (empty for this tool)
        container: DI container for services

    Returns:
        Strategy performance information
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        # Get strategy context (mock implementation for now)
        strategies = {
            "RSI_oversold": {"win_rate": 0.72, "total_trades": 25, "avg_pnl": 2.3},
            "MACD_divergence": {"win_rate": 0.65, "total_trades": 20, "avg_pnl": 1.8},
            "Support_bounce": {"win_rate": 0.78, "total_trades": 18, "avg_pnl": 1.5}
        }

        result_text = "Strategy Performance Overview\n\n"

        for strategy, metrics in strategies.items():
            result_text += f"{strategy}:\n"
            result_text += f"  Win Rate: {metrics['win_rate']:.1%}\n"
            result_text += f"  Total Trades: {metrics['total_trades']}\n"
            result_text += f"  Avg P&L: ₹{metrics['avg_pnl']:.1f}%\n\n"

        # Find best performer
        best_strategy = max(strategies.items(), key=lambda x: x[1]['win_rate'])
        result_text += f"🏆 Best Performer: {best_strategy[0]} ({best_strategy[1]['win_rate']:.1%} win rate)\n\n"

        result_text += "Suggested next steps:\n"
        result_text += "- Use 'analyze_portfolio_data' with insights from top strategies\n"
        result_text += "- Use 'execute_paper_trade' with winning strategies\n"
        result_text += "- Use 'calculate_monthly_pnl' for detailed performance analysis\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "analyze_portfolio_data", "reason": "Apply strategy insights to portfolio"},
                {"tool": "execute_paper_trade", "reason": "Execute trades with winning strategies"},
                {"tool": "calculate_monthly_pnl", "reason": "Detailed performance analysis"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in get_strategy_performance tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "optimize_prompt_template",
    "Optimize prompt templates for better data quality",
    {
        "template_type": str,
        "optimization_goal": str,
        "priority": int
    }
)
async def optimize_prompt_template(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Optimize prompt templates for better data quality.

    Args:
        args: Tool arguments for prompt optimization
        container: DI container for services

    Returns:
        Prompt optimization results
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        template_type = args.get("template_type", "market_research")
        optimization_goal = args.get("optimization_goal", "data_quality")
        priority = args.get("priority", 6)

        # Get task service
        task_service = await container.get("task_service")

        # Create prompt optimization task
        task = await task_service.create_task(
            queue_name=QueueName.PORTFOLIO_ANALYSIS,
            task_type=TaskType.PROMPT_TEMPLATE_OPTIMIZATION,
            payload={
                "template_type": template_type,
                "optimization_goal": optimization_goal,
                "discovery_context": {
                    "tool_name": "optimize_prompt_template",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            },
            priority=priority
        )

        result_text = "Prompt optimization task created\n"
        result_text += f"Task ID: {task.task_id}\n"
        result_text += f"Template Type: {template_type}\n"
        result_text += f"Optimization Goal: {optimization_goal}\n\n"

        result_text += "This will improve:\n"
        result_text += "- Data quality for future research\n"
        result_text += "- Analysis accuracy for portfolio insights\n"
        result_text += "- Strategy effectiveness evaluation\n\n"

        result_text += "Suggested next steps:\n"
        result_text += "- Use 'research_symbol' with optimized prompts\n"
        result_text += "- Use 'analyze_portfolio_data' for better quality analysis\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "research_symbol", "reason": "Test optimized prompts on market research"},
                {"tool": "analyze_portfolio_data", "reason": "Apply improved analysis quality"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in optimize_prompt_template tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "calculate_monthly_pnl",
    "Calculate monthly P&L and performance metrics",
    {
        "month": str,
        "year": int,
        "include_details": bool
    }
)
async def calculate_monthly_pnl(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Calculate monthly P&L and performance metrics.

    Args:
        args: Tool arguments for P&L calculation
        container: DI container for services

    Returns:
        Monthly P&L analysis
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        month = args.get("month", "")
        year = args.get("year", datetime.now().year)
        include_details = args.get("include_details", True)

        month_number = _parse_month_value(month)
        month_label = datetime(year, month_number, 1).strftime("%B")
        account_id = await _resolve_single_account_id(container)

        store = await container.get("paper_trading_store")
        monthly_data = await store.calculate_monthly_pnl(account_id, year, month_number)

        result_text = f"Monthly P&L Analysis - {month_label} {year}\n\n"
        result_text += f"Account: {account_id}\n"
        result_text += f"Total P&L: ₹{monthly_data.get('total_pnl', 0):,.2f}\n"
        result_text += f"Win Rate: {monthly_data.get('win_rate', 0):.1f}%\n"
        result_text += f"Total Trades: {monthly_data.get('total_trades', 0)}\n"
        result_text += f"Best Trade: ₹{monthly_data.get('best_trade', 0):,.2f}\n"
        result_text += f"Worst Trade: ₹{monthly_data.get('worst_trade', 0):,.2f}\n\n"

        if include_details:
            result_text += "Top performing strategies:\n"
            top_strategies = monthly_data.get('top_strategies', [])
            if not top_strategies:
                result_text += "  No closed trades in the selected month.\n"
            else:
                for strategy in top_strategies[:3]:
                    result_text += (
                        f"  {strategy['name']}: ₹{strategy['pnl']:,.2f} "
                        f"({strategy['win_rate']:.1f}% win rate, {strategy['trades']} trades)\n"
                    )

        result_text += "\nSuggested next steps:\n"
        result_text += "- Use 'get_strategy_performance' for detailed strategy analysis\n"
        result_text += "- Use 'analyze_portfolio_data' for portfolio optimization\n"
        result_text += "- Use 'execute_paper_trade' based on profitable patterns\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "get_strategy_performance", "reason": "Analyze winning strategies in detail"},
                {"tool": "analyze_portfolio_data", "reason": "Optimize portfolio based on performance"},
                {"tool": "execute_paper_trade", "reason": "Apply profitable trading patterns"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in calculate_monthly_pnl tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


@tool(
    "get_market_status",
    "Get current market status and trading session information",
    {}
)
async def get_market_status(args: Dict[str, Any], container: Optional[DependencyContainer] = None) -> Dict[str, Any]:
    """
    Get current market status and trading session information.

    Args:
        args: Tool arguments (empty for this tool)
        container: DI container for services

    Returns:
        Market status information
    """
    try:
        if not container:
            return {
                "content": [{"type": "text", "text": "Error: Container not available"}],
                "is_error": True
            }

        now = datetime.now()

        # Simple market status logic
        is_weekend = now.weekday() >= 5  # Saturday=5, Sunday=6
        is_market_hours = 9 <= now.hour < 16 and not is_weekend

        result_text = "Market Status\n\n"

        if is_market_hours:
            result_text += "🟢 Market is OPEN\n"
            result_text += f"Current Time: {now.strftime('%I:%M %p')}\n"
            result_text += "Session: Regular Trading Hours\n"
        else:
            result_text += "🔴 Market is CLOSED\n"
            result_text += f"Current Time: {now.strftime('%I:%M %p')}\n"

            if is_weekend:
                result_text += "Weekend - Market resumes Monday 9:15 AM\n"
            else:
                if now.hour < 9:
                    result_text += "Pre-market opens at 9:00 AM\n"
                    result_text += "Regular trading opens at 9:15 AM\n"
                else:
                    result_text += "Market resumes tomorrow at 9:15 AM\n"

        result_text += f"\nDate: {now.strftime('%A, %B %d, %Y')}\n"

        result_text += "\nSuggested next steps:\n"
        if is_market_hours:
            result_text += "- Use 'research_symbol' for real-time analysis\n"
            result_text += "- Use 'execute_paper_trade' for active trading\n"
        else:
            result_text += "- Use 'analyze_portfolio_data' for portfolio review\n"
            result_text += "- Use 'optimize_prompt_template' for strategy improvement\n"

        return {
            "content": [{"type": "text", "text": result_text}],
            "discovery_suggestions": [
                {"tool": "research_symbol", "reason": "Real-time market analysis"},
                {"tool": "execute_paper_trade", "reason": "Active trading opportunities"},
                {"tool": "analyze_portfolio_data", "reason": "Portfolio review and optimization"}
            ]
        }

    except Exception as e:
        logger.error(f"Error in get_market_status tool: {e}")
        return {
            "content": [{"type": "text", "text": f"Error: {str(e)}"}],
            "is_error": True
        }


# Create the enhanced MCP server with progressive discovery
async def create_enhanced_paper_trading_server(
    container: DependencyContainer,
    discovery_context: Optional[Dict[str, Any]] = None
):
    """
    Create enhanced MCP server with progressive discovery capabilities.

    Args:
        container: DI container for services
        discovery_context: Optional context for tool discovery

    Returns:
        Enhanced MCP server instance
    """

    # Initialize discovery manager
    discovery_manager = ProgressiveDiscoveryManager(container)
    await discovery_manager.initialize()

    # Update discovery context if provided
    if discovery_context:
        await discovery_manager.update_discovery_context(discovery_context)

    # Get available tools based on current context
    available_tool_names = await discovery_manager.get_available_tools()

    # Map tool names to actual tool functions
    tool_name_map = {
        "research_symbol": research_symbol,
        "execute_paper_trade": execute_paper_trade,
        "check_paper_trading_status": check_paper_trading_status,
        "analyze_portfolio_data": analyze_portfolio_data,
        "get_strategy_performance": get_strategy_performance,
        "optimize_prompt_template": optimize_prompt_template,
        "calculate_monthly_pnl": calculate_monthly_pnl,
        "get_market_status": get_market_status
    }

    # Filter tools based on discovery context
    available_tools = []
    for tool_name in available_tool_names:
        if tool_name in tool_name_map:
            available_tools.append(tool_name_map[tool_name])

    # Create SDK MCP server with available tools
    server = create_sdk_mcp_server(
        name="enhanced-paper-trading",
        version="2.0.0",
        tools=available_tools
    )

    logger.info(f"Enhanced Paper Trading MCP Server created with {len(available_tools)} tools")
    logger.info(f"Available tools: {available_tool_names}")

    # Return both server and discovery manager for later updates
    return server, discovery_manager


# Server factory function for DI container
async def create_enhanced_paper_trading_mcp_server():
    """Factory function for DI container registration."""

    async def server_factory(container: DependencyContainer):
        """Create enhanced MCP server instance."""
        discovery_context = {
            "workflow_stage": "research",
            "portfolio_value": 0,
            "trades_executed": 0
        }

        return await create_enhanced_paper_trading_server(container, discovery_context)

    return server_factory
