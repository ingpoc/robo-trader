"""AI prompts configuration store."""

from datetime import datetime, timezone
from typing import Any, Dict

from loguru import logger

from .base_store import BaseConfigStore


class PromptsStore(BaseConfigStore):
    """Manages AI prompts configuration in database."""

    async def get(self, prompt_name: str) -> Dict[str, Any]:
        """
        Get prompt configuration by name.

        Args:
            prompt_name: Name of the prompt

        Returns:
            Prompt configuration dict
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT prompt_content, description FROM ai_prompts_config WHERE prompt_name = ?",
                    (prompt_name,),
                )
                row = await cursor.fetchone()

                if row:
                    return {"content": row[0], "description": row[1] if row[1] else ""}
                return {"content": "", "description": ""}
            except Exception as e:
                self._log_error(f"get({prompt_name})", e)
                return {"content": "", "description": ""}

    async def get_all(self) -> Dict[str, Any]:
        """
        Get all prompts configuration.

        Returns:
            Dict with all prompts
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM ai_prompts_config ORDER BY prompt_name"
                )
                rows = await cursor.fetchall()

                prompts = {}
                for row in rows:
                    prompts[row[1]] = {  # prompt_name at index 1
                        "content": row[2],  # prompt_content at index 2
                        "description": (
                            row[3] if row[3] else ""
                        ),  # description at index 3
                    }

                return {"ai_prompts": prompts}
            except Exception as e:
                self._log_error("get_all", e)
                return {"ai_prompts": {}}

    async def update(
        self, prompt_name: str, prompt_content: str, description: str = ""
    ) -> bool:
        """
        Update prompt configuration.

        Args:
            prompt_name: Name of the prompt
            prompt_content: Prompt content
            description: Optional description

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """
                    INSERT OR REPLACE INTO ai_prompts_config
                    (prompt_name, prompt_content, description, updated_at, created_at)
                    VALUES (?, ?, ?, ?, COALESCE(
                        (SELECT created_at FROM ai_prompts_config WHERE prompt_name = ?), ?
                    ))
                    """,
                    (prompt_name, prompt_content, description, now, prompt_name, now),
                )

                await self.db.connection.commit()
                logger.info(f"Updated prompt configuration for {prompt_name}")
                return True

            except Exception as e:
                self._log_error(f"update({prompt_name})", e)
                return False
