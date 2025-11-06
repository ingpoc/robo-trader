import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import aiofiles

logger = logging.getLogger(__name__)


class TradeDecisionLogger:
    """Log and retrieve Claude's trade decisions for transparency."""

    def __init__(self, data_file: str = "data/trade_decisions.jsonl"):
        self.data_file = data_file
        self._decisions: List[Dict[str, Any]] = []
        self._initialized = False

    async def initialize(self) -> None:
        """Load existing decisions from file."""
        try:
            async with aiofiles.open(self.data_file, "r") as f:
                content = await f.read()
                if content.strip():
                    lines = content.strip().split("\n")
                    self._decisions = [
                        json.loads(line) for line in lines if line.strip()
                    ]
        except FileNotFoundError:
            self._decisions = []
        self._initialized = True
        logger.info(
            f"TradeDecisionLogger initialized with {len(self._decisions)} decisions"
        )

    async def log_decision(self, decision: Dict[str, Any]) -> Dict[str, Any]:
        """Log a new trade decision."""
        if not self._initialized:
            await self.initialize()
        if "logged_at" not in decision:
            decision["logged_at"] = datetime.now(timezone.utc).isoformat()
        self._decisions.append(decision)
        async with aiofiles.open(self.data_file, "a") as f:
            await f.write(json.dumps(decision) + "\n")
        logger.info(
            f"Trade decision logged: {decision.get('trade_id')} - {decision.get('symbol')} {decision.get('action')}"
        )
        return decision

    async def get_recent_decisions(
        self, limit: int = 20, symbol: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get recent trade decisions, optionally filtered by symbol."""
        if not self._initialized:
            await self.initialize()
        decisions = self._decisions.copy()
        if symbol:
            decisions = [d for d in decisions if d.get("symbol") == symbol]
        return decisions[-limit:][::-1]

    async def get_decision_stats(self) -> Dict[str, Any]:
        """Get statistics about trade decisions."""
        if not self._initialized:
            await self.initialize()
        total = len(self._decisions)
        buy_decisions = sum(1 for d in self._decisions if d.get("action") == "BUY")
        sell_decisions = sum(1 for d in self._decisions if d.get("action") == "SELL")
        avg_confidence = (
            sum(d.get("confidence", 0) for d in self._decisions) / total
            if total > 0
            else 0
        )
        symbols = set(d.get("symbol") for d in self._decisions if d.get("symbol"))
        return {
            "total_decisions": total,
            "buy_decisions": buy_decisions,
            "sell_decisions": sell_decisions,
            "avg_confidence": round(avg_confidence, 3),
            "symbols_traded": len(symbols),
            "unique_symbols": sorted(list(symbols)),
        }

    async def cleanup(self) -> None:
        """Cleanup resources."""
        self._initialized = False
