"""
Execution Agent

Translates approved risk decisions into broker orders.
"""

import json
from typing import Any, Dict, List

from claude_agent_sdk import tool
from loguru import logger

from src.config import Config

from ..core.database_state import DatabaseStateManager
from ..core.state_models import ExecutionReport, Intent, OrderCommand


def create_execution_agent_tool(config: Config, state_manager: DatabaseStateManager):
    """Create execution agent tool with dependencies via closure."""

    @tool("execute_trade", "Execute approved trading intent", {"intent_id": str})
    async def execute_trade_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trading intent."""
        try:
            intent_id = args["intent_id"]
            intent = await state_manager.get_intent(intent_id)

            if not intent or not intent.risk_decision:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Intent {intent_id} not ready for execution",
                        }
                    ],
                    "is_error": True,
                }

            if intent.risk_decision.decision != "approve":
                return {
                    "content": [
                        {"type": "text", "text": f"Intent {intent_id} not approved"}
                    ],
                    "is_error": True,
                }

            # Create order commands
            order_commands = _create_order_commands(intent, config)

            # Simulate execution (in real implementation, call broker tools)
            execution_reports = await _simulate_execution(order_commands)

            # Update intent
            intent.order_commands = order_commands
            intent.execution_reports = execution_reports
            intent.status = "executed"
            await state_manager.update_intent(intent)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Execution completed for intent {intent_id}",
                    },
                    {
                        "type": "text",
                        "text": json.dumps(
                            {
                                "orders": [cmd.to_dict() for cmd in order_commands],
                                "executions": [
                                    rep.to_dict() for rep in execution_reports
                                ],
                            },
                            indent=2,
                        ),
                    },
                ]
            }

        except Exception as e:
            logger.error(f"Trade execution failed: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "is_error": True,
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
        client_tag=intent.id,
    )

    return [command]


async def _simulate_execution(
    order_commands: List[OrderCommand],
) -> List[ExecutionReport]:
    """Simulate order execution."""
    reports = []
    for cmd in order_commands:
        # Simulate partial fill
        filled_qty = cmd.qty
        avg_price = 1520.50  # Simulated
        slippage = 0.002  # 0.2%

        report = ExecutionReport(
            broker_order_id=f"sim_{cmd.client_tag}",
            status="COMPLETE",
            fills=[{"qty": filled_qty, "price": avg_price}],
            avg_price=avg_price,
            slippage_bps=slippage * 10000,
        )
        reports.append(report)

    return reports
