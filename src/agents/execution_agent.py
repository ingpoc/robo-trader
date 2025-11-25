"""
Execution Agent

Translates approved risk decisions into broker orders using Kite Connect.
"""

import json
from typing import Dict, List, Any, Optional

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config
from ..core.database_state import DatabaseStateManager
from ..core.state_models import OrderCommand, ExecutionReport, Intent
from ..services.kite_connect_service import KiteConnectService, OrderRequest


def create_execution_agent_tool(
    config: Config,
    state_manager: DatabaseStateManager,
    kite_service: Optional[KiteConnectService] = None
):
    """Create execution agent tool with dependencies via closure."""
    
    @tool("execute_trade", "Execute approved trading intent using real Kite Connect order placement", {"intent_id": str})
    async def execute_trade_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading intent using real Kite Connect."""
        try:
            intent_id = args["intent_id"]
            intent = await state_manager.get_intent(intent_id)

            if not intent or not intent.risk_decision:
                return {
                    "content": [{"type": "text", "text": f"Intent {intent_id} not ready for execution"}],
                    "is_error": True
                }

            if intent.risk_decision.decision != "approve":
                return {
                    "content": [{"type": "text", "text": f"Intent {intent_id} not approved by risk manager"}],
                    "is_error": True
                }

            if not kite_service:
                return {
                    "content": [{"type": "text", "text": "Error: Kite Connect service not available. Please authenticate with Zerodha first."}],
                    "is_error": True
                }

            # Check if Kite Connect is authenticated
            if not await kite_service.is_authenticated():
                return {
                    "content": [{"type": "text", "text": "Error: Kite Connect not authenticated. Please authenticate first."}],
                    "is_error": True
                }

            # Create order commands
            order_commands = _create_order_commands(intent, config)

            # Execute orders using real Kite Connect
            execution_reports = await _execute_orders(order_commands, kite_service, config)

            # Update intent
            intent.order_commands = order_commands
            intent.execution_reports = execution_reports
            intent.status = "executed"
            await state_manager.update_intent(intent)

            return {
                "content": [
                    {"type": "text", "text": f"Execution completed for intent {intent_id} using real Kite Connect"},
                    {"type": "text", "text": json.dumps({
                        "orders": [cmd.to_dict() for cmd in order_commands],
                        "executions": [rep.to_dict() for rep in execution_reports]
                    }, indent=2)}
                ]
            }

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True
            }
    
    return execute_trade_tool


def _create_order_commands(intent: Intent, config: Config) -> List[OrderCommand]:
    """Create order commands from risk decision."""
    decision = intent.risk_decision
    signal = intent.signal

    if not decision or not signal:
        return []

    # Determine side from signal
    entry_price = signal.entry.get("price", 1000)
    side = "BUY" if signal.confidence > 0.5 else "SELL"  # Simplified

    command = OrderCommand(
        type="place",
        side=side,
        symbol=intent.symbol,
        qty=decision.size_qty,
        order_type=config.execution.default_order_type,
        product=config.execution.default_product,
        variety=config.execution.default_variety,
        tif=config.execution.time_in_force,
        client_tag=intent.id
    )

    return [command]


async def _execute_orders(
    order_commands: List[OrderCommand],
    kite_service: KiteConnectService,
    config: Config
) -> List[ExecutionReport]:
    """Execute orders using real Kite Connect."""
    reports = []
    
    for cmd in order_commands:
        try:
            # Create order request for Kite Connect
            order_request = OrderRequest(
                tradingsymbol=cmd.symbol,
                exchange="NSE",  # Default to NSE, could be made configurable
                transaction_type=cmd.side,
                quantity=cmd.qty,
                product=cmd.product,
                order_type=cmd.order_type,
                price=cmd.price if cmd.order_type == "LIMIT" else None,
                trigger_price=cmd.trigger_price if cmd.order_type in ["SL", "SL-M"] else None,
                validity=cmd.tif,
                disclosed_quantity=cmd.disclosed_quantity,
                squareoff=cmd.squareoff,
                stoploss=cmd.stoploss,
                trailing_stoploss=cmd.trailing_stoploss
            )

            # Place order through Kite Connect
            logger.info(f"Placing order for {cmd.symbol}: {cmd.side} {cmd.qty} @ {cmd.price or 'MARKET'}")
            result = await kite_service.place_order(order_request)

            # Calculate slippage if we have expected vs actual price
            slippage_bps = 0
            if cmd.price and result.get("average_price"):
                price_diff = abs(result["average_price"] - cmd.price)
                slippage_bps = (price_diff / cmd.price) * 10000

            # Create execution report
            report = ExecutionReport(
                broker_order_id=result.get("order_id", ""),
                status=result.get("status", "PENDING"),
                fills=[{
                    "qty": result.get("filled_quantity", 0),
                    "price": result.get("average_price", 0.0)
                }] if result.get("filled_quantity", 0) > 0 else [],
                avg_price=result.get("average_price", 0.0),
                slippage_bps=int(slippage_bps)
            )
            reports.append(report)

            logger.info(f"Order placed successfully: {result.get('order_id')} for {cmd.symbol}")

        except Exception as e:
            logger.error(f"Failed to execute order for {cmd.symbol}: {e}")
            # Create error report
            report = ExecutionReport(
                broker_order_id="",
                status="ERROR",
                fills=[],
                avg_price=0.0,
                slippage_bps=0
            )
            reports.append(report)

    return reports