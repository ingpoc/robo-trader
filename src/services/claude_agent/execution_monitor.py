"""
Execution Monitor Service

Monitors and logs all AI trade execution activities, providing complete
transparency into how Claude executes trades, manages risk, and handles
order flow in real-time.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ...stores.claude_strategy_store import ClaudeStrategyStore

logger = logging.getLogger(__name__)


@dataclass
class ExecutionStep:
    """A single step in the trade execution process."""

    step_id: str
    step_type: str  # 'pre_trade_check', 'order_placement', 'risk_validation', 'execution', 'post_trade_analysis'
    description: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    success: bool = True
    error_message: Optional[str] = None
    timestamp: str = ""
    duration_ms: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradeExecutionLog:
    """Complete log of a trade execution process."""

    execution_id: str
    decision_id: str
    session_id: str
    symbol: str
    action: str  # 'BUY', 'SELL'
    quantity: int
    entry_price: float
    strategy_rationale: str
    execution_steps: List[ExecutionStep] = None
    risk_checks: Dict[str, Any] = None
    order_details: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    slippage_analysis: Optional[Dict[str, Any]] = None
    cost_analysis: Optional[Dict[str, Any]] = None
    execution_timestamp: str = ""
    total_duration_ms: int = 0
    success: bool = False

    def __post_init__(self):
        if self.execution_steps is None:
            self.execution_steps = []
        if self.risk_checks is None:
            self.risk_checks = {}
        if not self.execution_timestamp:
            self.execution_timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["execution_steps"] = [step.to_dict() for step in self.execution_steps]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "TradeExecutionLog":
        if "execution_steps" in data:
            data["execution_steps"] = [
                ExecutionStep(**step) for step in data["execution_steps"]
            ]
        return TradeExecutionLog(**data)


@dataclass
class RiskCheckResult:
    """Result of a risk check during execution."""

    check_type: (
        str  # 'buying_power', 'position_size', 'portfolio_risk', 'concentration'
    )
    passed: bool
    value: float
    threshold: float
    message: str
    severity: str = "low"  # 'low', 'medium', 'high', 'critical'

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExecutionMonitor:
    """
    Monitors and logs all trade execution activities for transparency.

    Provides complete visibility into:
    - Pre-trade risk checks and validations
    - Order placement and routing decisions
    - Execution quality and slippage analysis
    - Post-trade cost analysis
    - Error handling and recovery
    """

    def __init__(self, strategy_store: ClaudeStrategyStore):
        self.strategy_store = strategy_store
        self.active_executions: Dict[str, TradeExecutionLog] = {}

    async def start_execution_monitoring(
        self,
        decision_id: str,
        session_id: str,
        symbol: str,
        action: str,
        quantity: int,
        entry_price: float,
        strategy_rationale: str,
        execution_id: Optional[str] = None,
    ) -> TradeExecutionLog:
        """Start monitoring a trade execution."""

        if not execution_id:
            execution_id = (
                f"exec_{int(datetime.now(timezone.utc).timestamp())}_{symbol}"
            )

        execution_log = TradeExecutionLog(
            execution_id=execution_id,
            decision_id=decision_id,
            session_id=session_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            entry_price=entry_price,
            strategy_rationale=strategy_rationale,
        )

        self.active_executions[execution_id] = execution_log
        logger.info(
            f"Started execution monitoring: {execution_id} ({action} {quantity} {symbol} @ {entry_price})"
        )

        return execution_log

    async def log_execution_step(
        self,
        execution_id: str,
        step_type: str,
        description: str,
        input_data: Dict[str, Any],
        output_data: Optional[Dict[str, Any]] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        """Log a step in the execution process."""

        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found for step logging")
            return

        step = ExecutionStep(
            step_id=f"step_{len(self.active_executions[execution_id].execution_steps) + 1}",
            step_type=step_type,
            description=description,
            input_data=input_data,
            output_data=output_data,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
        )

        self.active_executions[execution_id].execution_steps.append(step)
        logger.debug(f"Logged execution step: {step_type} for execution {execution_id}")

    async def log_risk_checks(
        self, execution_id: str, risk_checks: List[RiskCheckResult]
    ) -> None:
        """Log risk validation results."""

        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found for risk checks")
            return

        execution = self.active_executions[execution_id]
        execution.risk_checks = {
            "checks": [check.to_dict() for check in risk_checks],
            "overall_passed": all(check.passed for check in risk_checks),
            "highest_severity": max(
                (check.severity for check in risk_checks), default="low"
            ),
        }

        logger.debug(f"Logged risk checks for execution {execution_id}")

    async def log_order_details(
        self, execution_id: str, order_details: Dict[str, Any]
    ) -> None:
        """Log order placement details."""

        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found for order details")
            return

        self.active_executions[execution_id].order_details = order_details
        logger.debug(f"Logged order details for execution {execution_id}")

    async def log_execution_result(
        self, execution_id: str, execution_result: Dict[str, Any]
    ) -> None:
        """Log the final execution result."""

        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found for execution result")
            return

        execution = self.active_executions[execution_id]
        execution.execution_result = execution_result
        execution.success = execution_result.get("success", False)

        logger.info(
            f"Logged execution result for {execution_id}: success={execution.success}"
        )

    async def analyze_slippage(
        self,
        execution_id: str,
        expected_price: float,
        actual_price: float,
        market_conditions: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Analyze execution slippage and quality."""

        slippage_bps = ((actual_price - expected_price) / expected_price) * 10000
        slippage_pct = (actual_price - expected_price) / expected_price * 100

        # Determine slippage quality
        if abs(slippage_bps) <= 50:  # Within 0.5%
            quality = "excellent"
        elif abs(slippage_bps) <= 100:  # Within 1%
            quality = "good"
        elif abs(slippage_bps) <= 200:  # Within 2%
            quality = "acceptable"
        else:
            quality = "poor"

        analysis = {
            "expected_price": expected_price,
            "actual_price": actual_price,
            "slippage_bps": slippage_bps,
            "slippage_pct": slippage_pct,
            "quality": quality,
            "market_conditions": market_conditions,
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if execution_id in self.active_executions:
            self.active_executions[execution_id].slippage_analysis = analysis

        logger.debug(
            f"Analyzed slippage for execution {execution_id}: {slippage_bps} bps ({quality})"
        )

        return analysis

    async def analyze_execution_costs(
        self,
        execution_id: str,
        trade_value: float,
        commissions: float = 0.0,
        fees: float = 0.0,
        slippage_cost: float = 0.0,
    ) -> Dict[str, Any]:
        """Analyze total execution costs."""

        total_cost = commissions + fees + slippage_cost
        cost_pct = (total_cost / trade_value) * 100 if trade_value > 0 else 0

        # Cost quality assessment
        if cost_pct <= 0.1:  # Less than 0.1%
            quality = "excellent"
        elif cost_pct <= 0.25:  # Less than 0.25%
            quality = "good"
        elif cost_pct <= 0.5:  # Less than 0.5%
            quality = "acceptable"
        else:
            quality = "high"

        analysis = {
            "trade_value": trade_value,
            "commissions": commissions,
            "fees": fees,
            "slippage_cost": slippage_cost,
            "total_cost": total_cost,
            "cost_pct": cost_pct,
            "quality": quality,
            "cost_breakdown": {
                "commissions_pct": (
                    (commissions / trade_value) * 100 if trade_value > 0 else 0
                ),
                "fees_pct": (fees / trade_value) * 100 if trade_value > 0 else 0,
                "slippage_pct": (
                    (slippage_cost / trade_value) * 100 if trade_value > 0 else 0
                ),
            },
            "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if execution_id in self.active_executions:
            self.active_executions[execution_id].cost_analysis = analysis

        logger.debug(
            f"Analyzed execution costs for {execution_id}: {cost_pct:.2f}% ({quality})"
        )

        return analysis

    async def complete_execution_monitoring(
        self, execution_id: str, total_duration_ms: int = 0
    ) -> Optional[TradeExecutionLog]:
        """Complete execution monitoring and save to storage."""

        if execution_id not in self.active_executions:
            logger.warning(f"Execution {execution_id} not found for completion")
            return None

        execution = self.active_executions[execution_id]
        execution.total_duration_ms = total_duration_ms

        # Save to database
        await self._save_execution_log(execution)

        # Remove from active executions
        del self.active_executions[execution_id]

        logger.info(
            f"Completed execution monitoring: {execution_id} (success: {execution.success}, duration: {total_duration_ms}ms)"
        )

        return execution

    async def get_execution_history(
        self,
        session_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50,
    ) -> List[TradeExecutionLog]:
        """Get historical execution logs."""

        # This would query the database for stored execution logs
        # For now, return active executions as example
        executions = list(self.active_executions.values())

        if session_id:
            executions = [e for e in executions if e.session_id == session_id]
        if symbol:
            executions = [e for e in executions if e.symbol == symbol]

        return executions[-limit:]  # Return most recent

    async def get_execution_quality_metrics(self, days: int = 7) -> Dict[str, Any]:
        """Get execution quality metrics over time."""

        # Get recent executions
        executions = await self.get_execution_history(limit=1000)

        # Filter by time period
        cutoff_time = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        recent_executions = [
            e
            for e in executions
            if datetime.fromisoformat(e.execution_timestamp).timestamp() > cutoff_time
        ]

        if not recent_executions:
            # Return default values instead of error dict
            return {
                "period_days": days,
                "total_executions": 0,
                "successful_executions": 0,
                "success_rate": 0.0,
                "avg_slippage_bps": 0.0,
                "avg_cost_pct": 0.0,
                "risk_checks_pass_rate": 1.0,
                "quality_score": 0.0,
            }

        # Calculate quality metrics
        total_executions = len(recent_executions)
        successful_executions = len([e for e in recent_executions if e.success])
        success_rate = (
            successful_executions / total_executions if total_executions > 0 else 0
        )

        # Analyze slippage
        slippage_data = []
        for execution in recent_executions:
            if execution.slippage_analysis:
                slippage_data.append(execution.slippage_analysis["slippage_bps"])

        avg_slippage_bps = (
            sum(slippage_data) / len(slippage_data) if slippage_data else 0
        )

        # Analyze costs
        cost_data = []
        for execution in recent_executions:
            if execution.cost_analysis:
                cost_data.append(execution.cost_analysis["cost_pct"])

        avg_cost_pct = sum(cost_data) / len(cost_data) if cost_data else 0

        # Risk check performance
        risk_check_performance = []
        for execution in recent_executions:
            if execution.risk_checks:
                risk_check_performance.append(
                    execution.risk_checks.get("overall_passed", False)
                )

        risk_checks_passed = (
            sum(risk_check_performance) / len(risk_check_performance)
            if risk_check_performance
            else 1.0
        )

        return {
            "period_days": days,
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": success_rate,
            "avg_slippage_bps": avg_slippage_bps,
            "avg_cost_pct": avg_cost_pct,
            "risk_checks_pass_rate": risk_checks_passed,
            "quality_score": self._calculate_quality_score(
                success_rate, avg_slippage_bps, avg_cost_pct, risk_checks_passed
            ),
        }

    def _calculate_quality_score(
        self,
        success_rate: float,
        avg_slippage_bps: float,
        avg_cost_pct: float,
        risk_checks_pass_rate: float,
    ) -> float:
        """Calculate overall execution quality score (0-100)."""

        # Success rate component (40% weight)
        success_score = success_rate * 40

        # Slippage component (30% weight) - lower slippage is better
        slippage_score = max(0, 30 - abs(avg_slippage_bps) * 0.3)

        # Cost component (20% weight) - lower cost is better
        cost_score = max(0, 20 - avg_cost_pct * 4)

        # Risk compliance component (10% weight)
        risk_score = risk_checks_pass_rate * 10

        return success_score + slippage_score + cost_score + risk_score

    async def _save_execution_log(self, execution: TradeExecutionLog) -> None:
        """Save execution log to database."""

        # This would extend the ClaudeStrategyStore to include execution logging
        # For now, we'll log the execution data
        execution_data = execution.to_dict()

        logger.info(f"Execution log saved: {execution.execution_id}")
        logger.debug(f"Execution data: {json.dumps(execution_data, indent=2)}")

    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Clean up old execution logs from memory."""

        cutoff_time = datetime.now(timezone.utc).timestamp() - (
            days_to_keep * 24 * 60 * 60
        )
        old_executions = []

        for execution_id, execution in self.active_executions.items():
            if (
                datetime.fromisoformat(execution.execution_timestamp).timestamp()
                < cutoff_time
            ):
                old_executions.append(execution_id)

        for execution_id in old_executions:
            del self.active_executions[execution_id]

        if old_executions:
            logger.info(f"Cleaned up {len(old_executions)} old execution logs")

        return len(old_executions)
