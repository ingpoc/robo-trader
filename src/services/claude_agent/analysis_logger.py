"""
Analysis Logger Service

Logs all AI analysis activities, reasoning processes, and decision-making
transparently for client visibility into Claude's trading thought process.
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from ...core.errors import TradingError, ErrorCategory, ErrorSeverity
from ...stores.claude_strategy_store import ClaudeStrategyStore

logger = logging.getLogger(__name__)


@dataclass
class AnalysisStep:
    """A single step in the AI's analysis process."""

    step_id: str
    step_type: str  # 'market_analysis', 'technical_analysis', 'fundamental_analysis', 'risk_assessment', 'decision_making'
    description: str
    input_data: Dict[str, Any]
    reasoning: str
    confidence_score: float = 0.0
    timestamp: str = ""
    duration_ms: int = 0

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TradeDecisionLog:
    """Complete log of a trade decision and its reasoning."""

    decision_id: str
    session_id: str
    symbol: str
    action: str  # 'BUY', 'SELL', 'HOLD'
    quantity: Optional[int] = None
    entry_price: Optional[float] = None
    strategy_rationale: str = ""
    risk_assessment: Dict[str, Any] = None
    market_context: Dict[str, Any] = None
    technical_signals: List[str] = None
    fundamental_factors: List[str] = None
    analysis_steps: List[AnalysisStep] = None
    confidence_score: float = 0.0
    decision_timestamp: str = ""
    executed: bool = False
    execution_result: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.risk_assessment is None:
            self.risk_assessment = {}
        if self.market_context is None:
            self.market_context = {}
        if self.technical_signals is None:
            self.technical_signals = []
        if self.fundamental_factors is None:
            self.fundamental_factors = []
        if self.analysis_steps is None:
            self.analysis_steps = []
        if not self.decision_timestamp:
            self.decision_timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['analysis_steps'] = [step.to_dict() for step in self.analysis_steps]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'TradeDecisionLog':
        if 'analysis_steps' in data:
            data['analysis_steps'] = [AnalysisStep(**step) for step in data['analysis_steps']]
        return TradeDecisionLog(**data)


@dataclass
class StrategyEvaluation:
    """Evaluation of a trading strategy's performance."""

    evaluation_id: str
    strategy_name: str
    evaluation_period: str  # 'daily', 'weekly', 'monthly'
    start_date: str
    end_date: str
    performance_metrics: Dict[str, Any]
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    confidence_score: float = 0.0
    next_evaluation_date: Optional[str] = None
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AnalysisLogger:
    """
    Logs all AI analysis activities for complete transparency.

    Provides detailed visibility into:
    - Step-by-step analysis process
    - Decision-making reasoning
    - Risk assessments
    - Strategy evaluations
    - Performance analysis
    """

    def __init__(self, strategy_store: ClaudeStrategyStore):
        self.strategy_store = strategy_store
        self.active_decisions: Dict[str, TradeDecisionLog] = {}

    async def start_trade_analysis(
        self,
        session_id: str,
        symbol: str,
        decision_id: Optional[str] = None
    ) -> TradeDecisionLog:
        """Start logging a trade analysis and decision process."""

        if not decision_id:
            decision_id = f"decision_{int(datetime.now(timezone.utc).timestamp())}_{symbol}"

        decision_log = TradeDecisionLog(
            decision_id=decision_id,
            session_id=session_id,
            symbol=symbol,
            action="HOLD"  # Default, will be updated
        )

        self.active_decisions[decision_id] = decision_log
        logger.info(f"Started trade analysis logging: {decision_id} for {symbol}")

        return decision_log

    async def log_analysis_step(
        self,
        decision_id: str,
        step_type: str,
        description: str,
        input_data: Dict[str, Any],
        reasoning: str,
        confidence_score: float = 0.0,
        duration_ms: int = 0
    ) -> None:
        """Log a single step in the analysis process."""

        if decision_id not in self.active_decisions:
            logger.warning(f"Decision {decision_id} not found for step logging")
            return

        step = AnalysisStep(
            step_id=f"step_{len(self.active_decisions[decision_id].analysis_steps) + 1}",
            step_type=step_type,
            description=description,
            input_data=input_data,
            reasoning=reasoning,
            confidence_score=confidence_score,
            duration_ms=duration_ms
        )

        self.active_decisions[decision_id].analysis_steps.append(step)
        logger.debug(f"Logged analysis step: {step.step_type} for decision {decision_id}")

    async def update_decision_details(
        self,
        decision_id: str,
        action: str,
        quantity: Optional[int] = None,
        entry_price: Optional[float] = None,
        strategy_rationale: str = "",
        confidence_score: float = 0.0
    ) -> None:
        """Update the final decision details."""

        if decision_id not in self.active_decisions:
            logger.warning(f"Decision {decision_id} not found for update")
            return

        decision = self.active_decisions[decision_id]
        decision.action = action
        decision.quantity = quantity
        decision.entry_price = entry_price
        decision.strategy_rationale = strategy_rationale
        decision.confidence_score = confidence_score

        logger.info(f"Updated decision details: {decision_id} -> {action}")

    async def log_risk_assessment(
        self,
        decision_id: str,
        risk_assessment: Dict[str, Any]
    ) -> None:
        """Log risk assessment details."""

        if decision_id not in self.active_decisions:
            logger.warning(f"Decision {decision_id} not found for risk assessment")
            return

        self.active_decisions[decision_id].risk_assessment = risk_assessment
        logger.debug(f"Logged risk assessment for decision {decision_id}")

    async def log_market_context(
        self,
        decision_id: str,
        market_context: Dict[str, Any]
    ) -> None:
        """Log market context used in analysis."""

        if decision_id not in self.active_decisions:
            logger.warning(f"Decision {decision_id} not found for market context")
            return

        self.active_decisions[decision_id].market_context = market_context
        logger.debug(f"Logged market context for decision {decision_id}")

    async def log_signals_and_factors(
        self,
        decision_id: str,
        technical_signals: List[str] = None,
        fundamental_factors: List[str] = None
    ) -> None:
        """Log technical signals and fundamental factors."""

        if decision_id not in self.active_decisions:
            logger.warning(f"Decision {decision_id} not found for signals/factors")
            return

        decision = self.active_decisions[decision_id]
        if technical_signals:
            decision.technical_signals.extend(technical_signals)
        if fundamental_factors:
            decision.fundamental_factors.extend(fundamental_factors)

        logger.debug(f"Logged signals and factors for decision {decision_id}")

    async def complete_trade_decision(
        self,
        decision_id: str,
        executed: bool = False,
        execution_result: Optional[Dict[str, Any]] = None
    ) -> Optional[TradeDecisionLog]:
        """Complete a trade decision and save to storage."""

        if decision_id not in self.active_decisions:
            logger.warning(f"Decision {decision_id} not found for completion")
            return None

        decision = self.active_decisions[decision_id]
        decision.executed = executed
        decision.execution_result = execution_result or {}

        # Save to database
        await self._save_trade_decision(decision)

        # Remove from active decisions
        del self.active_decisions[decision_id]

        logger.info(f"Completed trade decision: {decision_id} ({decision.action}, executed: {executed})")

        return decision

    async def log_strategy_evaluation(
        self,
        strategy_name: str,
        evaluation_period: str,
        start_date: str,
        end_date: str,
        performance_metrics: Dict[str, Any],
        strengths: List[str],
        weaknesses: List[str],
        recommendations: List[str],
        confidence_score: float = 0.0
    ) -> StrategyEvaluation:
        """Log a strategy evaluation."""

        evaluation = StrategyEvaluation(
            evaluation_id=f"eval_{int(datetime.now(timezone.utc).timestamp())}_{strategy_name}",
            strategy_name=strategy_name,
            evaluation_period=evaluation_period,
            start_date=start_date,
            end_date=end_date,
            performance_metrics=performance_metrics,
            strengths=strengths,
            weaknesses=weaknesses,
            recommendations=recommendations,
            confidence_score=confidence_score
        )

        # Save to database
        await self._save_strategy_evaluation(evaluation)

        logger.info(f"Logged strategy evaluation: {strategy_name} ({evaluation_period})")

        return evaluation

    async def get_decision_history(
        self,
        session_id: Optional[str] = None,
        symbol: Optional[str] = None,
        limit: int = 50
    ) -> List[TradeDecisionLog]:
        """Get historical trade decisions."""

        # This would query the database for stored decisions
        # For now, return active decisions as example
        decisions = list(self.active_decisions.values())

        if session_id:
            decisions = [d for d in decisions if d.session_id == session_id]
        if symbol:
            decisions = [d for d in decisions if d.symbol == symbol]

        return decisions[-limit:]  # Return most recent

    async def get_strategy_evaluations(
        self,
        strategy_name: Optional[str] = None,
        evaluation_period: Optional[str] = None,
        limit: int = 20
    ) -> List[StrategyEvaluation]:
        """Get historical strategy evaluations."""

        # This would query the database for stored evaluations
        # For now, return empty list as example
        return []

    async def get_analysis_effectiveness(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """Analyze the effectiveness of AI analysis over time."""

        # Get recent decisions
        decisions = await self.get_decision_history(limit=1000)

        # Filter by time period
        cutoff_time = datetime.now(timezone.utc).timestamp() - (days * 24 * 60 * 60)
        recent_decisions = [
            d for d in decisions
            if datetime.fromisoformat(d.decision_timestamp).timestamp() > cutoff_time
        ]

        if not recent_decisions:
            return {"error": "No decisions found in the specified period"}

        # Calculate effectiveness metrics
        total_decisions = len(recent_decisions)
        executed_decisions = len([d for d in recent_decisions if d.executed])
        avg_confidence = sum(d.confidence_score for d in recent_decisions) / total_decisions
        avg_analysis_steps = sum(len(d.analysis_steps) for d in recent_decisions) / total_decisions

        # Group by action type
        actions = {}
        for decision in recent_decisions:
            if decision.action not in actions:
                actions[decision.action] = []
            actions[decision.action].append(decision)

        action_stats = {}
        for action, action_decisions in actions.items():
            action_stats[action] = {
                "count": len(action_decisions),
                "avg_confidence": sum(d.confidence_score for d in action_decisions) / len(action_decisions),
                "executed": len([d for d in action_decisions if d.executed])
            }

        return {
            "period_days": days,
            "total_decisions": total_decisions,
            "executed_decisions": executed_decisions,
            "execution_rate": executed_decisions / total_decisions if total_decisions > 0 else 0,
            "avg_confidence_score": avg_confidence,
            "avg_analysis_steps": avg_analysis_steps,
            "action_breakdown": action_stats
        }

    async def _save_trade_decision(self, decision: TradeDecisionLog) -> None:
        """Save trade decision to database."""

        # This would extend the ClaudeStrategyStore to include decision logging
        # For now, we'll log the decision data
        decision_data = decision.to_dict()

        logger.info(f"Trade decision saved: {decision.decision_id}")
        logger.debug(f"Decision data: {json.dumps(decision_data, indent=2)}")

    async def _save_strategy_evaluation(self, evaluation: StrategyEvaluation) -> None:
        """Save strategy evaluation to database."""

        # This would save to a dedicated strategy_evaluations table
        # For now, we'll log the evaluation data
        evaluation_data = evaluation.to_dict()

        logger.info(f"Strategy evaluation saved: {evaluation.evaluation_id}")
        logger.debug(f"Evaluation data: {json.dumps(evaluation_data, indent=2)}")

    async def cleanup_old_logs(self, days_to_keep: int = 30) -> int:
        """Clean up old analysis logs from memory."""

        cutoff_time = datetime.now(timezone.utc).timestamp() - (days_to_keep * 24 * 60 * 60)
        old_decisions = []

        for decision_id, decision in self.active_decisions.items():
            if datetime.fromisoformat(decision.decision_timestamp).timestamp() < cutoff_time:
                old_decisions.append(decision_id)

        for decision_id in old_decisions:
            del self.active_decisions[decision_id]

        if old_decisions:
            logger.info(f"Cleaned up {len(old_decisions)} old decision logs")

        return len(old_decisions)