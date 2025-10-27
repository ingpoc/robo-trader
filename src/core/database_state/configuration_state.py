"""
Configuration state management for Robo Trader.

Manages all configuration data in the database with backup to JSON files.
This replaces file-based configuration with database-first approach.
"""

import asyncio
import json
import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.database_state.base import DatabaseConnection


class ConfigurationState:
    """
    Manages configuration data in database with JSON backup.

    This class provides database-first configuration management with
    automatic backup to JSON files for redundancy and migration purposes.
    """

    def __init__(self, db_connection: DatabaseConnection):
        """
        Initialize configuration state manager.

        Args:
            db_connection: Database connection instance
        """
        self.db = db_connection
        self.backup_dir = Path("config/backups")
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Initialize configuration tables in database."""
        schema = """
        -- Background Tasks Configuration
        CREATE TABLE IF NOT EXISTS background_tasks_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL UNIQUE,
            enabled BOOLEAN NOT NULL DEFAULT FALSE,
            frequency_seconds INTEGER NOT NULL,
            frequency_unit TEXT NOT NULL DEFAULT 'seconds',
            use_claude BOOLEAN NOT NULL DEFAULT TRUE,
            priority TEXT NOT NULL DEFAULT 'medium',
            stock_symbols TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- AI Agents Configuration
        CREATE TABLE IF NOT EXISTS ai_agents_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_name TEXT NOT NULL UNIQUE,
            enabled BOOLEAN NOT NULL DEFAULT FALSE,
            use_claude BOOLEAN NOT NULL DEFAULT TRUE,
            tools TEXT DEFAULT '[]',
            response_frequency INTEGER NOT NULL DEFAULT 30,
            response_frequency_unit TEXT NOT NULL DEFAULT 'minutes',
            scope TEXT NOT NULL DEFAULT 'portfolio',
            max_tokens_per_request INTEGER NOT NULL DEFAULT 2000,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Global Settings Configuration
        CREATE TABLE IF NOT EXISTS global_settings_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            setting_key TEXT NOT NULL UNIQUE,
            setting_value TEXT NOT NULL,
            setting_type TEXT NOT NULL DEFAULT 'string',
            category TEXT NOT NULL DEFAULT 'general',
            description TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        -- Configuration Backup History
        CREATE TABLE IF NOT EXISTS configuration_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            backup_type TEXT NOT NULL, -- 'full', 'background_tasks', 'ai_agents', 'global_settings'
            backup_data TEXT NOT NULL,  -- JSON data
            backup_file TEXT,  -- Path to backup file
            created_at TEXT NOT NULL,
            created_by TEXT DEFAULT 'system'
        );

        -- Indexes for performance
        CREATE INDEX IF NOT EXISTS idx_background_tasks_task_name ON background_tasks_config(task_name);
        CREATE INDEX IF NOT EXISTS idx_background_tasks_updated ON background_tasks_config(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_ai_agents_agent_name ON ai_agents_config(agent_name);
        CREATE INDEX IF NOT EXISTS idx_ai_agents_updated ON ai_agents_config(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_global_settings_key ON global_settings_config(setting_key);
        CREATE INDEX IF NOT EXISTS idx_global_settings_updated ON global_settings_config(updated_at DESC);
        CREATE INDEX IF NOT EXISTS idx_config_backups_type ON configuration_backups(backup_type);
        CREATE INDEX IF NOT EXISTS idx_config_backups_created ON configuration_backups(created_at DESC);
        """

        try:
            await self.db.connection.executescript(schema)
            await self.db.connection.commit()
            logger.info("Configuration tables initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize configuration tables: {e}")
            raise

    async def get_background_task_config(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Get background task configuration by name.

        Args:
            task_name: Name of the background task

        Returns:
            Task configuration dict or None if not found
        """
        try:
            cursor = await self.db.connection.execute(
                "SELECT * FROM background_tasks_config WHERE task_name = ?",
                (task_name,)
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "task_name": row["task_name"],
                    "enabled": bool(row["enabled"]),
                    "frequency": row["frequency_seconds"],
                    "frequency_unit": row["frequency_unit"],
                    "use_claude": bool(row["use_claude"]),
                    "priority": row["priority"],
                    "stock_symbols": row["stock_symbols"].split(",") if row["stock_symbols"] else []
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get background task config for {task_name}: {e}")
            return None

    async def get_all_background_tasks_config(self) -> Dict[str, Any]:
        """
        Get all background tasks configuration.

        Returns:
            Dict with all background tasks configuration
        """
        try:
            cursor = await self.db.connection.execute(
                "SELECT * FROM background_tasks_config ORDER BY priority DESC, task_name"
            )
            rows = await cursor.fetchall()

            background_tasks = {}
            for row in rows:
                background_tasks[row["task_name"]] = {
                    "enabled": bool(row["enabled"]),
                    "frequency": row["frequency_seconds"],
                    "frequency_unit": row["frequency_unit"],
                    "use_claude": bool(row["use_claude"]),
                    "priority": row["priority"],
                    "stock_symbols": row["stock_symbols"].split(",") if row["stock_symbols"] else []
                }

            return {"background_tasks": background_tasks}
        except Exception as e:
            logger.error(f"Failed to get all background tasks config: {e}")
            return {"background_tasks": {}}

    async def update_background_task_config(
        self,
        task_name: str,
        config_data: Dict[str, Any]
    ) -> bool:
        """
        Update background task configuration.

        Args:
            task_name: Name of the background task
            config_data: Configuration data to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert frequency to seconds
            frequency_seconds = config_data.get("frequency", 3600)
            frequency_unit = config_data.get("frequency_unit", "seconds")

            if frequency_unit == "minutes":
                frequency_seconds = frequency_seconds * 60
            elif frequency_unit == "hours":
                frequency_seconds = frequency_seconds * 3600
            elif frequency_unit == "days":
                frequency_seconds = frequency_seconds * 86400

            # Prepare stock symbols
            stock_symbols = config_data.get("stock_symbols", [])
            if isinstance(stock_symbols, list):
                stock_symbols = ",".join(filter(None, stock_symbols))

            now = datetime.now(timezone.utc).isoformat()

            # Insert or update
            await self.db.connection.execute(
                """
                INSERT OR REPLACE INTO background_tasks_config
                (task_name, enabled, frequency_seconds, frequency_unit, use_claude, priority, stock_symbols, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name,
                    config_data.get("enabled", False),
                    frequency_seconds,
                    frequency_unit,
                    config_data.get("use_claude", True),
                    config_data.get("priority", "medium"),
                    stock_symbols,
                    now
                )
            )

            await self.db.connection.commit()

            # Create backup
            await self._create_backup("background_tasks", task_name)

            logger.info(f"Updated background task configuration for {task_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update background task config for {task_name}: {e}")
            return False

    async def get_ai_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Get AI agent configuration by name.

        Args:
            agent_name: Name of the AI agent

        Returns:
            Agent configuration dict or None if not found
        """
        try:
            cursor = await self.db.connection.execute(
                "SELECT * FROM ai_agents_config WHERE agent_name = ?",
                (agent_name,)
            )
            row = await cursor.fetchone()

            if row:
                return {
                    "agent_name": row["agent_name"],
                    "enabled": bool(row["enabled"]),
                    "use_claude": bool(row["use_claude"]),
                    "tools": json.loads(row["tools"]) if row["tools"] else [],
                    "response_frequency": row["response_frequency"],
                    "response_frequency_unit": row["response_frequency_unit"],
                    "scope": row["scope"],
                    "max_tokens_per_request": row["max_tokens_per_request"]
                }
            return None
        except Exception as e:
            logger.error(f"Failed to get AI agent config for {agent_name}: {e}")
            return None

    async def get_all_ai_agents_config(self) -> Dict[str, Any]:
        """
        Get all AI agents configuration.

        Returns:
            Dict with all AI agents configuration
        """
        try:
            cursor = await self.db.connection.execute(
                "SELECT * FROM ai_agents_config ORDER BY agent_name"
            )
            rows = await cursor.fetchall()

            ai_agents = {}
            for row in rows:
                ai_agents[row["agent_name"]] = {
                    "enabled": bool(row["enabled"]),
                    "use_claude": bool(row["use_claude"]),
                    "tools": json.loads(row["tools"]) if row["tools"] else [],
                    "response_frequency": row["response_frequency"],
                    "response_frequency_unit": row["response_frequency_unit"],
                    "scope": row["scope"],
                    "max_tokens_per_request": row["max_tokens_per_request"]
                }

            return {"ai_agents": ai_agents}
        except Exception as e:
            logger.error(f"Failed to get all AI agents config: {e}")
            return {"ai_agents": {}}

    async def update_ai_agent_config(
        self,
        agent_name: str,
        config_data: Dict[str, Any]
    ) -> bool:
        """
        Update AI agent configuration.

        Args:
            agent_name: Name of the AI agent
            config_data: Configuration data to update

        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert response frequency to seconds
            response_frequency = config_data.get("responseFrequency", 30)
            response_frequency_unit = config_data.get("responseFrequencyUnit", "minutes")

            if response_frequency_unit == "hours":
                response_frequency = response_frequency * 60
            elif response_frequency_unit == "days":
                response_frequency = response_frequency * 1440

            now = datetime.now(timezone.utc).isoformat()

            # Prepare tools as JSON
            tools = config_data.get("tools", [])
            if isinstance(tools, list):
                tools = json.dumps(tools)

            # Insert or update
            await self.db.connection.execute(
                """
                INSERT OR REPLACE INTO ai_agents_config
                (agent_name, enabled, use_claude, tools, response_frequency, response_frequency_unit, scope, max_tokens_per_request, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    agent_name,
                    config_data.get("enabled", False),
                    config_data.get("useClaude", True),
                    tools,
                    response_frequency,
                    response_frequency_unit,
                    config_data.get("scope", "portfolio"),
                    config_data.get("maxTokensPerRequest", 2000),
                    now
                )
            )

            await self.db.connection.commit()

            # Create backup
            await self._create_backup("ai_agents", agent_name)

            logger.info(f"Updated AI agent configuration for {agent_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to update AI agent config for {agent_name}: {e}")
            return False

    async def get_global_settings_config(self) -> Dict[str, Any]:
        """
        Get all global settings configuration.

        Returns:
            Dict with global settings configuration
        """
        try:
            cursor = await self.db.connection.execute(
                "SELECT * FROM global_settings_config ORDER BY category, setting_key"
            )
            rows = await cursor.fetchall()

            # Organize settings by category
            global_settings = {
                "claude_usage": {},
                "scheduler_defaults": {}
            }

            for row in rows:
                key = row["setting_key"]
                value = row["setting_value"]
                category = row["category"]
                setting_type = row["setting_type"]

                # Parse value based on type
                if setting_type == "boolean":
                    parsed_value = value.lower() == "true"
                elif setting_type == "integer":
                    parsed_value = int(value)
                elif setting_type == "float":
                    parsed_value = float(value)
                else:
                    parsed_value = value

                # Organize by category
                if category == "claude_usage" and key in ["enabled", "daily_token_limit", "cost_alerts", "cost_threshold"]:
                    global_settings["claude_usage"][key] = parsed_value
                elif category == "scheduler_defaults" and key in ["default_frequency", "default_frequency_unit", "market_hours_only", "retry_attempts", "retry_delay_minutes"]:
                    global_settings["scheduler_defaults"][key] = parsed_value
                else:
                    # For backward compatibility
                    if category not in global_settings:
                        global_settings[category] = {}
                    global_settings[category][key] = parsed_value

            return {"global_settings": global_settings}
        except Exception as e:
            logger.error(f"Failed to get global settings config: {e}")
            return {"global_settings": {}}

    async def update_global_settings_config(
        self,
        settings_data: Dict[str, Any]
    ) -> bool:
        """
        Update global settings configuration.

        Args:
            settings_data: Settings data to update

        Returns:
            True if successful, False otherwise
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            # Update each setting
            for category, settings in settings_data.items():
                if not isinstance(settings, dict):
                    continue

                for key, value in settings.items():
                    # Determine setting type
                    if isinstance(value, bool):
                        setting_type = "boolean"
                        value_str = str(value).lower()
                    elif isinstance(value, int):
                        setting_type = "integer"
                        value_str = str(value)
                    elif isinstance(value, float):
                        setting_type = "float"
                        value_str = str(value)
                    else:
                        setting_type = "string"
                        value_str = str(value)

                    # Insert or update
                    await self.db.connection.execute(
                        """
                        INSERT OR REPLACE INTO global_settings_config
                        (setting_key, setting_value, setting_type, category, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (key, value_str, setting_type, category, now)
                    )

            await self.db.connection.commit()

            # Create backup
            await self._create_backup("global_settings", "all")

            logger.info("Updated global settings configuration")
            return True

        except Exception as e:
            logger.error(f"Failed to update global settings config: {e}")
            return False

    async def _create_backup(self, backup_type: str, identifier: str = "all") -> None:
        """
        Create backup of configuration to JSON file.

        Args:
            backup_type: Type of backup ('background_tasks', 'ai_agents', 'global_settings', 'full')
            identifier: Specific item identifier or 'all'
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            if backup_type == "full":
                backup_data = {
                    "background_tasks": await self.get_all_background_tasks_config(),
                    "ai_agents": await self.get_all_ai_agents_config(),
                    "global_settings": await self.get_global_settings_config(),
                    "timestamp": timestamp
                }
                filename = f"config_backup_{timestamp}.json"
            elif backup_type == "background_tasks":
                if identifier == "all":
                    backup_data = await self.get_all_background_tasks_config()
                else:
                    backup_data = {identifier: await self.get_background_task_config(identifier)}
                filename = f"background_tasks_backup_{timestamp}.json"
            elif backup_type == "ai_agents":
                if identifier == "all":
                    backup_data = await self.get_all_ai_agents_config()
                else:
                    backup_data = {identifier: await self.get_ai_agent_config(identifier)}
                filename = f"ai_agents_backup_{timestamp}.json"
            elif backup_type == "global_settings":
                backup_data = await self.get_global_settings_config()
                filename = f"global_settings_backup_{timestamp}.json"
            else:
                logger.warning(f"Unknown backup type: {backup_type}")
                return

            backup_file = self.backup_dir / filename

            # Write backup file
            async with aiosqlite.connect(str(backup_file)) as backup_db:
                await backup_db.execute(
                    "CREATE TABLE IF NOT EXISTS backup_data (data TEXT)"
                )
                await backup_db.execute(
                    "INSERT INTO backup_data (data) VALUES (?)",
                    (json.dumps(backup_data, indent=2),)
                )
                await backup_db.commit()

            # Record backup in database
            await self.db.connection.execute(
                """
                INSERT INTO configuration_backups
                (backup_type, backup_data, backup_file, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (backup_type, json.dumps(backup_data, indent=2), str(backup_file), timestamp)
            )
            await self.db.connection.commit()

            logger.info(f"Created {backup_type} backup: {filename}")

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")

    async def get_backup_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get backup history.

        Args:
            limit: Maximum number of backups to return

        Returns:
            List of backup records
        """
        try:
            cursor = await self.db.connection.execute(
                """
                SELECT * FROM configuration_backups
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (limit,)
            )
            rows = await cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "backup_type": row["backup_type"],
                    "backup_file": row["backup_file"],
                    "created_at": row["created_at"],
                    "created_by": row["created_by"]
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"Failed to get backup history: {e}")
            return []

    async def restore_from_backup(self, backup_id: int) -> bool:
        """
        Restore configuration from backup.

        Args:
            backup_id: ID of the backup to restore

        Returns:
            True if successful, False otherwise
        """
        try:
            cursor = await self.db.connection.execute(
                "SELECT * FROM configuration_backups WHERE id = ?",
                (backup_id,)
            )
            row = await cursor.fetchone()

            if not row:
                return False

            backup_file = Path(row["backup_file"])
            if not backup_file.exists():
                logger.error(f"Backup file not found: {backup_file}")
                return False

            # Load backup data
            async with aiosqlite.connect(str(backup_file)) as backup_db:
                cursor = await backup_db.execute("SELECT data FROM backup_data LIMIT 1")
                backup_row = await cursor.fetchone()

                if backup_row:
                    backup_data = json.loads(backup_row["data"])

                    # Restore based on backup type
                    if row["backup_type"] == "full":
                        # Restore all configurations
                        await self._restore_full_config(backup_data)
                    elif row["backup_type"] == "background_tasks":
                        await self._restore_background_tasks_config(backup_data)
                    elif row["backup_type"] == "ai_agents":
                        await self._restore_ai_agents_config(backup_data)
                    elif row["backup_type"] == "global_settings":
                        await self._restore_global_settings_config(backup_data)

                    logger.info(f"Restored configuration from backup ID {backup_id}")
                    return True

        except Exception as e:
            logger.error(f"Failed to restore from backup {backup_id}: {e}")
            return False

    async def _restore_full_config(self, backup_data: Dict[str, Any]) -> None:
        """Restore full configuration from backup data."""
        if "background_tasks" in backup_data:
            await self._restore_background_tasks_config(backup_data["background_tasks"])
        if "ai_agents" in backup_data:
            await self._restore_ai_agents_config(backup_data["ai_agents"])
        if "global_settings" in backup_data:
            await self._restore_global_settings_config(backup_data["global_settings"])

    async def _restore_background_tasks_config(self, config_data: Dict[str, Any]) -> None:
        """Restore background tasks configuration from backup data."""
        if "background_tasks" in config_data:
            for task_name, task_config in config_data["background_tasks"].items():
                await self.update_background_task_config(task_name, task_config)

    async def _restore_ai_agents_config(self, config_data: Dict[str, Any]) -> None:
        """Restore AI agents configuration from backup data."""
        if "ai_agents" in config_data:
            for agent_name, agent_config in config_data["ai_agents"].items():
                await self.update_ai_agent_config(agent_name, agent_config)

    async def _restore_global_settings_config(self, config_data: Dict[str, Any]) -> None:
        """Restore global settings configuration from backup data."""
        if "global_settings" in config_data:
            await self.update_global_settings_config(config_data["global_settings"])

    async def migrate_from_config_json(self, config_path: Path) -> bool:
        """
        Migrate existing configuration from JSON file to database.

        Args:
            config_path: Path to the existing config.json file

        Returns:
            True if successful, False otherwise
        """
        try:
            if not config_path.exists():
                logger.warning(f"Config file not found: {config_path}")
                return False

            # Read existing config
            async with aiofiles.open(config_path, 'r') as f:
                config_data = json.loads(await f.read())

            migrated = False

            # Migrate background tasks
            if "agents" in config_data:
                for task_name, task_config in config_data["agents"].items():
                    if isinstance(task_config, dict):
                        # Convert to new format
                        db_config = {
                            "enabled": task_config.get("enabled", False),
                            "frequency": task_config.get("frequency_seconds", 3600),
                            "frequency_unit": "seconds",
                            "use_claude": task_config.get("use_claude", True),
                            "priority": task_config.get("priority", "medium"),
                            "stock_symbols": task_config.get("stock_symbols", [])
                        }
                        await self.update_background_task_config(task_name, db_config)
                        migrated = True

            # Create backup before migration
            if migrated:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backup_dir / f"pre_migration_backup_{timestamp}.json"

                # Copy original config to backup
                async with aiofiles.open(config_path, 'r') as src:
                    original_config = await src.read()

                async with aiofiles.open(backup_file, 'w') as dst:
                    await dst.write(original_config)

                logger.info(f"Migrated configuration from {config_path} to database")
                logger.info(f"Original config backed up to {backup_file}")

            return migrated

        except Exception as e:
            logger.error(f"Failed to migrate from config.json: {e}")
            return False