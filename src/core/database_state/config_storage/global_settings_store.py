"""Global settings configuration store."""

from datetime import datetime, timezone
from typing import Any, Dict

from loguru import logger

from .base_store import BaseConfigStore


class GlobalSettingsStore(BaseConfigStore):
    """Manages global settings configuration in database."""

    async def get_all(self) -> Dict[str, Any]:
        """
        Get all global settings configuration.

        Returns:
            Dict with all global settings
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM global_settings_config ORDER BY category, setting_key"
                )
                rows = await cursor.fetchall()

                settings = {}
                for row in rows:
                    key = row[1]  # setting_key at index 1
                    value = row[2]  # setting_value at index 2
                    setting_type = row[3]  # setting_type at index 3

                    # Convert value based on type
                    if setting_type == "boolean":
                        settings[key] = value.lower() == "true"
                    elif setting_type == "integer":
                        settings[key] = int(value)
                    elif setting_type == "float":
                        settings[key] = float(value)
                    else:
                        settings[key] = value

                return {"global_settings": settings}
            except Exception as e:
                self._log_error("get_all", e)
                return {"global_settings": {}}

    async def update(self, settings_data: Dict[str, Any]) -> bool:
        """
        Update global settings configuration.

        Args:
            settings_data: Settings data to update

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()

                for key, value in settings_data.items():
                    # Determine type
                    if isinstance(value, bool):
                        setting_type = "boolean"
                        setting_value = str(value).lower()
                    elif isinstance(value, int):
                        setting_type = "integer"
                        setting_value = str(value)
                    elif isinstance(value, float):
                        setting_type = "float"
                        setting_value = str(value)
                    else:
                        setting_type = "string"
                        setting_value = str(value)

                    await self.db.connection.execute(
                        """
                        INSERT OR REPLACE INTO global_settings_config
                        (setting_key, setting_value, setting_type, category, updated_at, created_at)
                        VALUES (?, ?, ?, ?, ?, COALESCE(
                            (SELECT created_at FROM global_settings_config WHERE setting_key = ?), ?
                        ))
                        """,
                        (key, setting_value, setting_type, "general", now, key, now),
                    )

                await self.db.connection.commit()
                logger.info(
                    f"Updated global settings configuration ({len(settings_data)} settings)"
                )
                return True

            except Exception as e:
                self._log_error("update", e)
                return False
