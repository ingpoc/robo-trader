"""Morning Trade Idea Coordinator - generates trade ideas via Claude SDK analysis."""

import json
from typing import Dict, List, Any, TYPE_CHECKING

from claude_agent_sdk import ClaudeAgentOptions

from src.config import Config
from src.core.coordinators.base_coordinator import BaseCoordinator
from src.core.event_bus import EventBus
from src.core.claude_sdk_client_manager import ClaudeSDKClientManager
from src.core.sdk_helpers import query_with_timeout

if TYPE_CHECKING:
    from src.core.di import DependencyContainer

_TRADE_PROMPT = (
    "You are an expert stock trader. Analyze each stock and generate BUY/SELL ideas.\n\n"
    "RESEARCH DATA:\n{stocks_json}\n\n"
    "REQUIREMENTS:\n"
    "- Only recommend trades with confidence >= 0.6\n"
    "- Calculate realistic entry, target, stop-loss prices (null if price unavailable)\n"
    "- Max 5% of capital per stock. Clear 2-3 sentence reasoning per trade.\n"
    "- If price=0/missing: base confidence on fundamentals/news only, set prices to null\n"
    "- Work ONLY with provided data, do NOT fetch additional data\n\n"
    'OUTPUT: JSON array only. Each object: {{"symbol","action","confidence","reasoning",'
    '"entry_price","target_price","stop_loss","position_size_pct","risk_reward_ratio"}}'
)


class MorningTradeIdeaCoordinator(BaseCoordinator):
    """Generates trade ideas from research data via Claude SDK."""

    def __init__(self, config: Config, event_bus: EventBus, container: 'DependencyContainer'):
        super().__init__(config, event_bus)
        self.container = container

    async def initialize(self) -> None:
        self._initialized = True

    async def generate_trade_ideas(
        self, research_results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate trade ideas using Claude analysis. Returns ideas with confidence >= 0.6."""
        if not research_results:
            return []
        batch = research_results[:min(3, len(research_results))]
        self._log_info(f"Generating trade ideas for {len(batch)} stocks using Claude SDK")
        try:
            manager = await ClaudeSDKClientManager.get_instance()
            client = await manager.get_client(
                "trade_analysis", ClaudeAgentOptions(model="claude-sonnet-4-20250514"))
            prompt = self._build_prompt(batch)
            response = await query_with_timeout(client, prompt, timeout=45.0)
            ideas = self._parse_response(response)
            filtered = [i for i in ideas if i.get("confidence", 0) >= 0.6]
            self._log_info(f"Generated {len(filtered)} trade ideas (confidence >= 0.6)")
            return filtered
        except Exception as e:
            self._log_warning(f"Trade idea generation failed: {e}")
            return []

    def _build_prompt(self, research_results: List[Dict[str, Any]]) -> str:
        stocks_data = [{
            "symbol": r.get("symbol"),
            "price": r.get("market_data", {}).get("price", 0),
            "fundamentals": r.get("research", {}).get("fundamentals", {}),
            "news": r.get("research", {}).get("news", {}),
            "timestamp": r.get("timestamp")
        } for r in research_results]
        return _TRADE_PROMPT.format(stocks_json=json.dumps(stocks_data, indent=2))

    def _parse_response(self, response_text: str) -> List[Dict[str, Any]]:
        """Parse trade ideas from Claude's JSON response."""
        try:
            text = response_text.strip()
            for prefix in ["```json", "```"]:
                if text.startswith(prefix):
                    text = text[len(prefix):]
            if text.endswith("```"):
                text = text[:-3]
            ideas = json.loads(text.strip())
            if not isinstance(ideas, list):
                self._log_warning("Expected JSON array, got different type")
                return []
            validated = []
            for idea in ideas:
                if not all(k in idea for k in ["symbol", "action", "confidence", "reasoning"]):
                    self._log_warning(f"Skipping invalid trade idea: {idea}")
                    continue
                idea["confidence"] = float(idea.get("confidence", 0))
                for f in ["entry_price", "target_price", "stop_loss", "risk_reward_ratio"]:
                    v = idea.get(f)
                    idea[f] = float(v) if v is not None else None
                idea["position_size_pct"] = float(idea.get("position_size_pct", 5.0))
                validated.append(idea)
            return validated
        except json.JSONDecodeError as e:
            self._log_warning(f"Failed to parse JSON response: {e}")
            self._log_debug(f"Response text: {response_text[:500]}")
            return []
        except Exception as e:
            self._log_warning(f"Error parsing trade ideas: {e}")
            return []

    async def cleanup(self) -> None:
        self._log_info("MorningTradeIdeaCoordinator cleanup complete")
