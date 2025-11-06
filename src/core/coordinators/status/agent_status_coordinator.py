"""
Agent Status Coordinator

Focused coordinator for trading agent status.
Extracted from StatusCoordinator for single responsibility.
"""

from datetime import datetime, timezone
from typing import Any, Dict

from src.config import Config

from ..base_coordinator import BaseCoordinator


class AgentStatusCoordinator(BaseCoordinator):
    """
    Coordinates trading agent status.

    Responsibilities:
    - Get status of all trading agents from database
    """

    def __init__(self, config: Config):
        super().__init__(config)
        self.ai_agents_store = None

    async def initialize(self) -> None:
        """Initialize agent status coordinator."""
        self._log_info("Initializing AgentStatusCoordinator")
        self._initialized = True

    def set_container(self, container) -> None:
        """Set the dependency container for accessing AI agents store."""
        self.container = container

    async def get_agents_status(self) -> Dict[str, Any]:
        """Get status of all agents from database."""
        try:
            # Get AI agents store from container
            if not hasattr(self, "container") or not self.container:
                self._log_warning(
                    "No container available, returning empty agents status"
                )
                return {}

            config_state = await self.container.get("configuration_state")
            if not config_state:
                self._log_warning(
                    "No config_state available, returning empty agents status"
                )
                return {}

            # Get AI agents from database
            ai_agents_data = await config_state.get_all_ai_agents_config()

            if not ai_agents_data or "ai_agents" not in ai_agents_data:
                self._log_info("No AI agents found in database")
                return {}

            agents = {}
            current_time = datetime.now(timezone.utc).isoformat()

            for agent_name, agent_config in ai_agents_data["ai_agents"].items():
                # Determine status based on enabled flag
                status = "active" if agent_config.get("enabled", False) else "idle"

                agents[agent_name] = {
                    "name": agent_name.replace("_", " ").title(),
                    "active": agent_config.get("enabled", False),
                    "status": status,
                    "tools": agent_config.get("tools", []),
                    "use_claude": agent_config.get("useClaude", True),
                    "response_frequency": agent_config.get("responseFrequency", 30),
                    "response_frequency_unit": agent_config.get(
                        "responseFrequencyUnit", "minutes"
                    ),
                    "scope": agent_config.get("scope", "portfolio"),
                    "max_tokens_per_request": agent_config.get(
                        "maxTokensPerRequest", 2000
                    ),
                    "last_activity": current_time,
                }

            self._log_info(f"Retrieved {len(agents)} AI agents from database")
            return agents

        except Exception as e:
            self._log_error(f"Failed to get agents status from database: {e}")
            # Return empty dict on error to avoid breaking the UI
            return {}

    async def cleanup(self) -> None:
        """Cleanup agent status coordinator resources."""
        self._log_info("AgentStatusCoordinator cleanup complete")
