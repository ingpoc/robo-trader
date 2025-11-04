"""AI agents configuration store."""

import json
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from loguru import logger

from .base_store import BaseConfigStore


class AIAgentsStore(BaseConfigStore):
    """Manages AI agents configuration in database."""

    async def get(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get AI agent configuration by name.

        Args:
            agent_name: Name of the AI agent

        Returns:
            Agent configuration dict or None if not found
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM ai_agents_config WHERE agent_name = ?",
                    (agent_name,)
                )
                row = await cursor.fetchone()

                if row:
                    tools = json.loads(row["tools"]) if row["tools"] else []
                    return {
                        "agent_name": row["agent_name"],
                        "enabled": bool(row["enabled"]),
                        "use_claude": bool(row["use_claude"]),
                        "tools": tools,
                        "response_frequency": row["response_frequency"],
                        "response_frequency_unit": row["response_frequency_unit"],
                        "scope": row["scope"],
                        "max_tokens_per_request": row["max_tokens_per_request"]
                    }
                return None
            except Exception as e:
                self._log_error(f"get({agent_name})", e)
                return None

    async def get_all(self) -> Dict[str, Any]:
        """
        Get all AI agents configuration.

        Returns:
            Dict with all AI agents configuration
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM ai_agents_config ORDER BY agent_name"
                )
                rows = await cursor.fetchall()

                agents = {}
                for row in rows:
                    tools = json.loads(row[3]) if row[3] else []
                    agents[row[1]] = {
                        "enabled": bool(row[2]),
                        "useClaude": bool(row[3]),
                        "tools": tools,
                        "responseFrequency": row[4],
                        "responseFrequencyUnit": row[5],
                        "scope": row[6],
                        "maxTokensPerRequest": row[7]
                    }

                return {"ai_agents": agents}
            except Exception as e:
                self._log_error("get_all", e)
                return {"ai_agents": {}}

    async def update(self, agent_name: str, config_data: Dict[str, Any]) -> bool:
        """
        Update AI agent configuration.

        Args:
            agent_name: Name of the AI agent
            config_data: Configuration data to update

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                tools = json.dumps(config_data.get("tools", []))
                now = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """
                    INSERT OR REPLACE INTO ai_agents_config
                    (agent_name, enabled, use_claude, tools, response_frequency,
                     response_frequency_unit, scope, max_tokens_per_request, updated_at, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE(
                        (SELECT created_at FROM ai_agents_config WHERE agent_name = ?), ?
                    ))
                    """,
                    (
                        agent_name,
                        config_data.get("enabled", False),
                        config_data.get("use_claude", True),
                        tools,
                        config_data.get("response_frequency", 30),
                        config_data.get("response_frequency_unit", "minutes"),
                        config_data.get("scope", "portfolio"),
                        config_data.get("max_tokens_per_request", 2000),
                        now,
                        agent_name,
                        now
                    )
                )

                await self.db.connection.commit()
                logger.info(f"Updated AI agent configuration for {agent_name}")
                return True

            except Exception as e:
                self._log_error(f"update({agent_name})", e)
                return False
