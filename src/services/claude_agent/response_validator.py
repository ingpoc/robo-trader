"""Response validation and decision parsing for Claude Agent SDK."""

import logging
import json
from typing import Dict, Any, List, Optional, Tuple

from ...models.claude_agent import TradeDecision, AnalysisRecommendation, StrategyLearning

logger = logging.getLogger(__name__)


class ResponseValidator:
    """Validate Claude responses before execution."""

    def __init__(self, config: Dict[str, Any]):
        """Initialize validator."""
        self.max_position_size = config.get("max_position_size_pct", 5.0)
        self.max_daily_trades = config.get("max_daily_trades", 10)
        self.min_stop_loss_pct = config.get("min_stop_loss_pct", 2.0)

    async def validate_tool_call(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        account_balance: float,
        current_positions: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate tool call before execution.

        Three-layer validation:
        1. Schema validation (type checking)
        2. Business rule validation (risk limits)
        3. Safety validation (account constraints)
        """
        # Layer 1: Schema validation
        validation_error = self._validate_schema(tool_name, tool_input)
        if validation_error:
            return False, validation_error

        # Layer 2: Business rule validation
        if tool_name == "execute_trade":
            validation_error = self._validate_trade_business_rules(
                tool_input, account_balance, current_positions
            )
            if validation_error:
                return False, validation_error

        # Layer 3: Safety validation (passed via config)
        # This would integrate with existing RiskService
        return True, None

    def _validate_schema(self, tool_name: str, tool_input: Dict[str, Any]) -> Optional[str]:
        """Validate input against tool schema."""
        if tool_name == "execute_trade":
            required = ["symbol", "action", "quantity", "entry_price", "strategy_rationale"]
            missing = [f for f in required if f not in tool_input]
            if missing:
                return f"Missing fields: {missing}"

            if tool_input.get("action") not in ["buy", "sell"]:
                return f"Invalid action: {tool_input.get('action')}"

            if tool_input.get("quantity", 0) <= 0:
                return "Quantity must be positive"

            if tool_input.get("entry_price", 0) <= 0:
                return "Entry price must be positive"

        elif tool_name == "close_position":
            required = ["trade_id", "exit_price", "reason"]
            missing = [f for f in required if f not in tool_input]
            if missing:
                return f"Missing fields: {missing}"

            if tool_input.get("exit_price", 0) <= 0:
                return "Exit price must be positive"

        return None

    def _validate_trade_business_rules(
        self,
        tool_input: Dict[str, Any],
        account_balance: float,
        current_positions: int
    ) -> Optional[str]:
        """Validate trade against business rules."""
        # Check position size limit
        trade_value = tool_input.get("quantity", 0) * tool_input.get("entry_price", 0)
        max_allowed = account_balance * (self.max_position_size / 100)

        if trade_value > max_allowed:
            return f"Trade value {trade_value} exceeds limit {max_allowed}"

        # Check if stop loss is reasonable
        if tool_input.get("stop_loss"):
            entry = tool_input.get("entry_price", 0)
            stop = tool_input.get("stop_loss", 0)
            loss_pct = abs(entry - stop) / entry * 100

            if loss_pct < self.min_stop_loss_pct:
                return f"Stop loss too tight ({loss_pct}%), minimum {self.min_stop_loss_pct}%"

        return None

    async def parse_trade_decision(self, response_text: str) -> Optional[List[TradeDecision]]:
        """
        Parse trade decisions from Claude response.

        Handles both JSON and natural language responses.
        """
        try:
            # Try JSON parsing first
            decisions_data = json.loads(response_text)
            if isinstance(decisions_data, list):
                return [TradeDecision.from_dict(d) for d in decisions_data]
            else:
                return [TradeDecision.from_dict(decisions_data)]
        except json.JSONDecodeError:
            # Fall back to text parsing
            return self._parse_text_trades(response_text)

    def _parse_text_trades(self, text: str) -> List[TradeDecision]:
        """Parse trades from natural language response."""
        trades = []

        # Look for patterns like "BUY SBIN 100 @ 450"
        import re
        pattern = r"(BUY|SELL)\s+([A-Z0-9]+)\s+(\d+)\s+@\s*([\d.]+)"

        for match in re.finditer(pattern, text, re.IGNORECASE):
            action, symbol, qty, price = match.groups()
            trades.append(TradeDecision(
                symbol=symbol,
                action=action.lower(),
                quantity=int(qty),
                reason="Parsed from Claude response",
                confidence=0.7
            ))

        return trades

    async def parse_analysis_recommendation(
        self,
        response_text: str
    ) -> Optional[AnalysisRecommendation]:
        """
        Parse analysis recommendation from Claude response.

        Looks for JSON or structured text patterns.
        """
        try:
            rec_data = json.loads(response_text)
            return AnalysisRecommendation.from_dict(rec_data)
        except json.JSONDecodeError:
            return self._parse_text_recommendation(response_text)

    def _parse_text_recommendation(self, text: str) -> Optional[AnalysisRecommendation]:
        """Parse recommendation from natural language."""
        import re

        # Look for key phrases
        lower_text = text.lower()
        if "buy" in lower_text:
            recommendation = "buy"
        elif "sell" in lower_text:
            recommendation = "sell"
        elif "hold" in lower_text:
            recommendation = "hold"
        else:
            return None

        # Try to extract confidence (0-100% or 0-1)
        confidence = 0.65  # default
        conf_match = re.search(r'confidence[:\s]+(\d+)\s*%', lower_text)
        if conf_match:
            confidence = int(conf_match.group(1)) / 100

        return AnalysisRecommendation(
            symbol="UNKNOWN",
            recommendation=recommendation,
            confidence=confidence,
            rationale="Parsed from Claude response"
        )

    async def parse_learnings(self, response_text: str) -> Optional[StrategyLearning]:
        """Parse strategy learnings from evening review response."""
        try:
            learning_data = json.loads(response_text)
            return StrategyLearning(
                what_worked=learning_data.get("what_worked", []),
                what_failed=learning_data.get("what_failed", []),
                strategy_changes=learning_data.get("strategy_changes", []),
                research_topics=learning_data.get("research_topics", []),
                confidence_level=learning_data.get("confidence_level", 0.5)
            )
        except json.JSONDecodeError:
            return self._parse_text_learnings(response_text)

    def _parse_text_learnings(self, text: str) -> Optional[StrategyLearning]:
        """Parse learnings from natural language response."""
        import re

        worked = []
        failed = []
        changes = []

        # Simple pattern matching
        if "worked" in text.lower():
            worked_match = re.search(r"what.*?worked[:\s]+([^.]+)", text, re.IGNORECASE | re.DOTALL)
            if worked_match:
                worked_text = worked_match.group(1)
                worked = [s.strip() for s in worked_text.split(",") if s.strip()]

        if "failed" in text.lower():
            failed_match = re.search(r"what.*?failed[:\s]+([^.]+)", text, re.IGNORECASE | re.DOTALL)
            if failed_match:
                failed_text = failed_match.group(1)
                failed = [s.strip() for s in failed_text.split(",") if s.strip()]

        return StrategyLearning(
            what_worked=worked[:5],
            what_failed=failed[:5],
            strategy_changes=changes,
            research_topics=[],
            confidence_level=0.6
        )


class DecisionParser:
    """Parse and structure Claude decisions for execution."""

    @staticmethod
    def extract_tool_calls(response_content: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract tool calls from Claude response."""
        tool_calls = []

        for block in response_content:
            if block.get("type") == "tool_use":
                tool_calls.append({
                    "tool_name": block.get("name"),
                    "input": block.get("input"),
                    "id": block.get("id")
                })

        return tool_calls

    @staticmethod
    def extract_text(response_content: List[Dict[str, Any]]) -> str:
        """Extract text response from Claude."""
        text_parts = []

        for block in response_content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        return "\n".join(text_parts)
