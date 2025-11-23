"""
Safety hooks and guardrails for Robo Trader

Implements PreToolUse hooks for:
- Risk validation
- Approval workflows
- Environment-specific restrictions
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone

from claude_agent_sdk import HookMatcher
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import Intent, RiskDecision


async def pre_tool_use_hook(input_data: Dict[str, Any], tool_use_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main PreToolUse hook that delegates to specific validators.
    """
    tool_name = input_data.get("tool_name", "")
    tool_input = input_data.get("tool_input", {})

    # Get config and state from context (injected by orchestrator)
    config: Config = context.get("config")
    state_manager: DatabaseStateManager = context.get("state_manager")

    if not config or not state_manager:
        return {"hookSpecificOutput": {"permissionDecision": "deny", "permissionDecisionReason": "Missing context"}}

    # Route to appropriate validator
    if tool_name.startswith("mcp__broker__"):
        return await _validate_broker_tool(tool_name, tool_input, config, state_manager)
    elif tool_name.startswith("mcp__agents__"):
        return await _validate_agent_tool(tool_name, tool_input, config, state_manager)
    else:
        # Allow other tools
        return {}


async def _validate_broker_tool(tool_name: str, tool_input: Dict[str, Any], config: Config, state_manager: DatabaseStateManager) -> Dict[str, Any]:
    """Validate broker-related tools (orders, portfolio, etc.)."""

    # In dry-run mode, deny all execution tools
    if config.environment == "dry-run":
        if tool_name in ["mcp__broker__place_order", "mcp__broker__modify_order", "mcp__broker__cancel_order"]:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Execution tools denied in dry-run mode"
                }
            }

    # In live mode, require explicit approval for execution tools
    if config.environment == "live" and config.execution.require_manual_approval_live:
        if tool_name in ["mcp__broker__place_order", "mcp__broker__modify_order", "mcp__broker__cancel_order"]:
            # Check if this order has been approved
            client_tag = tool_input.get("client_tag", "")
            if not client_tag:
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": "Live orders require client_tag for approval tracking"
                    }
                }

            # Check intent approval
            intent = await state_manager.get_intent(client_tag)
            if not intent or intent.status != "approved":
                return {
                    "hookSpecificOutput": {
                        "hookEventName": "PreToolUse",
                        "permissionDecision": "deny",
                        "permissionDecisionReason": f"Intent {client_tag} not approved for execution"
                    }
                }

    # Validate order parameters
    if tool_name == "mcp__broker__place_order":
        validation = await _validate_order_parameters(tool_input, config, state_manager)
        if not validation["valid"]:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": validation["reason"]
                }
            }

    # Check market hours
    if tool_name in ["mcp__broker__place_order", "mcp__broker__modify_order"]:
        if not _is_market_open():
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": "Orders not allowed outside market hours"
                }
            }

    return {}


async def _validate_agent_tool(tool_name: str, tool_input: Dict[str, Any], config: Config, state_manager: DatabaseStateManager) -> Dict[str, Any]:
    """Validate agent-related tools."""

    # Validate execution agent calls
    if tool_name == "mcp__agents__execute_trade":
        intent_id = tool_input.get("intent_id", "")
        intent = await state_manager.get_intent(intent_id)
        if not intent:
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Intent {intent_id} not found"
                }
            }

        if not intent.risk_decision or intent.risk_decision.decision != "approve":
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Intent {intent_id} not approved by risk manager"
                }
            }

    return {}


async def _validate_order_parameters(tool_input: Dict[str, Any], config: Config, state_manager: DatabaseStateManager) -> Dict[str, bool]:
    """Validate order parameters against risk limits."""

    symbol = tool_input.get("symbol", "")
    qty = tool_input.get("qty", 0)
    side = tool_input.get("side", "")

    # Get current portfolio
    portfolio = await state_manager.get_portfolio()
    if not portfolio:
        return {"valid": False, "reason": "Portfolio state not available"}

    # Check symbol blacklist
    if symbol in config.screening.symbols_blacklist:
        return {"valid": False, "reason": f"Symbol {symbol} is blacklisted"}

    # Get current position
    current_qty = 0
    current_value = 0
    for holding in portfolio.holdings:
        if holding["symbol"] == symbol:
            current_qty = holding["qty"]
            current_value = holding["exposure"]
            break

    # Calculate new position
    if side == "BUY":
        new_qty = current_qty + qty
    elif side == "SELL":
        new_qty = current_qty - qty
    else:
        return {"valid": False, "reason": "Invalid order side"}

    if new_qty < 0:
        return {"valid": False, "reason": "Cannot sell more than current position"}

    # Check position size limits
    portfolio_value = portfolio.exposure_total + portfolio.cash.get("free", 0)
    if portfolio_value == 0:
        return {"valid": False, "reason": "Invalid portfolio value"}

    # Estimate order value (rough approximation)
    estimated_price = tool_input.get("price", 0) or _get_last_price(symbol, portfolio)
    if estimated_price == 0:
        return {"valid": False, "reason": "Cannot estimate order price"}

    order_value = qty * estimated_price
    new_position_percent = (order_value / portfolio_value) * 100

    if new_position_percent > config.risk.max_position_size_percent:
        return {
            "valid": False,
            "reason": f"Order size {new_position_percent:.1f}% exceeds max position size {config.risk.max_position_size_percent}%"
        }

    # Check single symbol exposure
    new_symbol_exposure = (abs(new_qty) * estimated_price / portfolio_value) * 100
    if new_symbol_exposure > config.risk.max_single_symbol_exposure_percent:
        return {
            "valid": False,
            "reason": f"Symbol exposure {new_symbol_exposure:.1f}% exceeds max {config.risk.max_single_symbol_exposure_percent}%"
        }

    return {"valid": True}


def _get_last_price(symbol: str, portfolio: Any) -> float:
    """Get last known price for symbol."""
    for holding in portfolio.holdings:
        if holding["symbol"] == symbol:
            return holding.get("last_price", 0)
    return 0


def _is_market_open() -> bool:
    """Check if market is currently open."""
    # Simple implementation - in production, use proper market calendar
    now = datetime.now(timezone.utc)
    # Convert to IST (UTC+5:30)
    ist_hour = (now.hour + 5) % 24
    ist_minute = now.minute + 30
    if ist_minute >= 60:
        ist_hour = (ist_hour + 1) % 24
        ist_minute -= 60

    current_time = ist_hour * 100 + ist_minute

    market_open = 915  # 9:15 AM IST
    market_close = 1530  # 3:30 PM IST

    # Check if weekday (0=Monday, 6=Sunday)
    if now.weekday() >= 5:  # Saturday/Sunday
        return False

    return market_open <= current_time <= market_close


async def session_start_hook(session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    """
    SessionStart hook - automatically inject trading context at session start.

    Provides Claude with:
    - Current portfolio state
    - Market conditions
    - Trading rules and constraints
    - Paper trading mode flag
    """
    config: Config = context.get("config")
    state_manager: DatabaseStateManager = context.get("state_manager")

    if not config or not state_manager:
        logger.warning("SessionStart hook: Missing config or state_manager in context")
        return {}

    try:
        # Get portfolio state
        portfolio_data = {}
        try:
            paper_trading_state = getattr(state_manager, 'paper_trading_state', None)
            if paper_trading_state:
                account = await paper_trading_state.get_account()
                if account:
                    portfolio_data = {
                        "cash_balance": account.get("current_cash", 0),
                        "total_equity": account.get("total_equity", 0),
                        "total_pnl": account.get("total_pnl", 0),
                        "day_pnl": account.get("day_pnl", 0)
                    }

                open_trades = await paper_trading_state.get_open_trades()
                portfolio_data["open_positions"] = len(open_trades) if open_trades else 0
        except Exception as e:
            logger.warning(f"SessionStart: Failed to get portfolio: {e}")

        # Get market conditions
        market_context = {
            "is_market_open": _is_market_open(),
            "session_type": "regular" if _is_market_open() else "closed",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        # Get trading rules from config
        trading_rules = {
            "paper_trading_only": True,  # Always paper trading
            "max_position_size_pct": getattr(config.execution, 'max_position_percent', 15),
            "require_stop_loss": getattr(config.execution, 'require_stop_loss', True),
            "environment": config.environment
        }

        logger.info(f"SessionStart hook: Injected context for session {session_id}")

        return {
            "portfolio_context": portfolio_data,
            "market_context": market_context,
            "trading_rules": trading_rules,
            "session_id": session_id
        }

    except Exception as e:
        logger.error(f"SessionStart hook error: {e}")
        return {}


async def post_tool_use_hook(
    tool_name: str,
    tool_input: Dict[str, Any],
    tool_output: Dict[str, Any],
    context: Dict[str, Any]
) -> Dict[str, Any]:
    """
    PostToolUse hook - automatic logging and event emission after tool execution.

    Responsibilities:
    - Log tool executions for transparency/audit
    - Emit events for UI updates
    - Track token usage
    """
    config: Config = context.get("config")
    state_manager: DatabaseStateManager = context.get("state_manager")

    if not config or not state_manager:
        return {}

    try:
        # Log tool execution for transparency
        execution_log = {
            "tool": tool_name,
            "input_summary": _summarize_input(tool_input),
            "success": "error" not in str(tool_output).lower(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        logger.debug(f"PostToolUse: {tool_name} executed successfully={execution_log['success']}")

        # Could emit events here for real-time UI updates
        # await event_bus.publish(Event(type=EventType.MCP_TOOL_EXECUTED, data=execution_log))

        return {"logged": True, "execution_log": execution_log}

    except Exception as e:
        logger.error(f"PostToolUse hook error: {e}")
        return {}


def _summarize_input(tool_input: Dict[str, Any]) -> str:
    """Create a brief summary of tool input for logging."""
    if not tool_input:
        return "(empty)"

    # Extract key fields for summary
    summary_parts = []
    for key in ["symbol", "action", "quantity", "account_id"]:
        if key in tool_input:
            summary_parts.append(f"{key}={tool_input[key]}")

    return ", ".join(summary_parts) if summary_parts else f"{len(tool_input)} params"


def create_safety_hooks(config: Config, state_manager: DatabaseStateManager) -> Dict[str, List[HookMatcher]]:
    """Create safety hooks configuration with PreToolUse, SessionStart, and PostToolUse hooks."""

    # Inject context into PreToolUse hook function
    async def pre_tool_hook_with_context(input_data: Dict[str, Any], tool_use_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        context = context or {}
        context.update({"config": config, "state_manager": state_manager})
        return await pre_tool_use_hook(input_data, tool_use_id, context)

    # Inject context into SessionStart hook
    async def session_start_hook_with_context(session_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        context = context or {}
        context.update({"config": config, "state_manager": state_manager})
        return await session_start_hook(session_id, context)

    # Inject context into PostToolUse hook
    async def post_tool_hook_with_context(tool_name: str, tool_input: Dict[str, Any], tool_output: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        context = context or {}
        context.update({"config": config, "state_manager": state_manager})
        return await post_tool_use_hook(tool_name, tool_input, tool_output, context)

    return {
        "PreToolUse": [
            HookMatcher(matcher="mcp__broker__*", hooks=[pre_tool_hook_with_context]),
            HookMatcher(matcher="mcp__agents__*", hooks=[pre_tool_hook_with_context]),
        ],
        "SessionStart": [
            HookMatcher(matcher="", hooks=[session_start_hook_with_context]),
        ],
        "PostToolUse": [
            HookMatcher(matcher="mcp__*", hooks=[post_tool_hook_with_context]),
        ],
    }