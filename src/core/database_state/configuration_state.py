"""
Configuration state management for Robo Trader.

Manages all configuration data in the database with backup to JSON files.
This is a facade that delegates to focused configuration stores.
"""

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger

from src.core.database_state.base import DatabaseConnection
from src.core.database_state.config_storage import (
    BackgroundTasksStore,
    AIAgentsStore,
    GlobalSettingsStore,
    PromptsStore
)
from src.core.database_state.config_backup import ConfigBackupManager


class ConfigurationState:
    """
    Manages configuration data in database with JSON backup.

    This facade delegates to focused stores for better organization:
    - BackgroundTasksStore: Background tasks configuration
    - AIAgentsStore: AI agents configuration
    - GlobalSettingsStore: Global settings configuration
    - PromptsStore: AI prompts configuration
    - ConfigBackupManager: Backup and restore operations
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
        self._lock = asyncio.Lock()

        # Initialize focused stores
        self.background_tasks = BackgroundTasksStore(db_connection)
        self.ai_agents = AIAgentsStore(db_connection)
        self.global_settings = GlobalSettingsStore(db_connection)
        self.prompts = PromptsStore(db_connection)
        self.backup_manager = ConfigBackupManager(db_connection, self.backup_dir)

    async def initialize(self) -> None:
        """Initialize configuration tables in database."""
        async with self._lock:
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

            -- AI Prompts Configuration
            CREATE TABLE IF NOT EXISTS ai_prompts_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name TEXT NOT NULL UNIQUE,
                prompt_content TEXT NOT NULL,
                description TEXT DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            -- Configuration Backup History
            CREATE TABLE IF NOT EXISTS configuration_backups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                backup_type TEXT NOT NULL,
                backup_data TEXT NOT NULL,
                backup_file TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT DEFAULT 'system'
            );

            -- Analysis History (for AI transparency)
            CREATE TABLE IF NOT EXISTS analysis_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                analysis TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            -- Recommendations (for AI transparency)
            CREATE TABLE IF NOT EXISTS recommendations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                recommendation_type TEXT NOT NULL,
                confidence_score REAL NOT NULL,
                reasoning TEXT NOT NULL,
                analysis_type TEXT NOT NULL,
                created_at TEXT NOT NULL
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
            CREATE INDEX IF NOT EXISTS idx_analysis_history_symbol ON analysis_history(symbol);
            CREATE INDEX IF NOT EXISTS idx_analysis_history_created ON analysis_history(created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_recommendations_symbol ON recommendations(symbol);
            CREATE INDEX IF NOT EXISTS idx_recommendations_created ON recommendations(created_at DESC);
            """

            try:
                await self.db.connection.executescript(schema)
                await self.db.connection.commit()
                logger.info("Configuration tables initialized successfully")

                # Initialize default configuration data
                await self._initialize_default_config()

            except Exception as e:
                logger.error(f"Failed to initialize configuration tables: {e}")
                raise

    async def _initialize_default_config(self) -> None:
        """Initialize default configuration data if tables are empty."""
        # Default data initialization is now handled by each store if needed
        # For now, keep empty to maintain backward compatibility
        pass

    # ===== Background Tasks Configuration =====
    async def get_background_task_config(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get background task configuration by name."""
        return await self.background_tasks.get(task_name)

    async def get_all_background_tasks_config(self) -> Dict[str, Any]:
        """Get all background tasks configuration."""
        return await self.background_tasks.get_all()

    async def update_background_task_config(self, task_name: str, config_data: Dict[str, Any]) -> bool:
        """Update background task configuration."""
        result = await self.background_tasks.update(task_name, config_data)
        if result:
            await self.backup_manager.create_backup("background_tasks", task_name)
        return result

    # ===== AI Agents Configuration =====
    async def get_ai_agent_config(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get AI agent configuration by name."""
        return await self.ai_agents.get(agent_name)

    async def get_all_ai_agents_config(self) -> Dict[str, Any]:
        """Get all AI agents configuration."""
        return await self.ai_agents.get_all()

    async def update_ai_agent_config(self, agent_name: str, config_data: Dict[str, Any]) -> bool:
        """Update AI agent configuration."""
        result = await self.ai_agents.update(agent_name, config_data)
        if result:
            await self.backup_manager.create_backup("ai_agents", agent_name)
        return result

    # ===== Global Settings Configuration =====
    async def get_global_settings_config(self) -> Dict[str, Any]:
        """Get all global settings configuration."""
        return await self.global_settings.get_all()

    async def update_global_settings_config(self, settings_data: Dict[str, Any]) -> bool:
        """Update global settings configuration."""
        result = await self.global_settings.update(settings_data)
        if result:
            await self.backup_manager.create_backup("global_settings")
        return result

    # ===== AI Prompts Configuration =====
    async def get_prompt_config(self, prompt_name: str) -> Dict[str, Any]:
        """Get prompt configuration by name."""
        return await self.prompts.get(prompt_name)

    async def get_all_prompts_config(self) -> Dict[str, Any]:
        """Get all prompts configuration."""
        return await self.prompts.get_all()

    async def update_prompt_config(self, prompt_name: str, prompt_content: str, description: str = "") -> bool:
        """Update prompt configuration."""
        result = await self.prompts.update(prompt_name, prompt_content, description)
        if result:
            await self.backup_manager.create_backup("ai_prompts", prompt_name)
        return result

    # ===== Backup & Restore =====
    async def get_backup_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get backup history."""
        return await self.backup_manager.get_backup_history(limit)

    async def restore_from_backup(self, backup_id: int) -> bool:
        """Restore configuration from backup."""
        return await self.backup_manager.restore_from_backup(backup_id)

    async def migrate_from_config_json(self, config_path: Path) -> bool:
        """Migrate configuration from JSON file (legacy support)."""
        logger.warning("migrate_from_config_json is deprecated - configuration is now database-first")
        return False

    # ===== Analysis & Recommendations (for AI Transparency) =====
    async def store_analysis_history(self, symbol: str, timestamp: str, analysis: str) -> bool:
        """
        Safely store analysis history with proper locking.

        Args:
            symbol: Stock symbol
            timestamp: Analysis timestamp
            analysis: Analysis data as JSON string

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """INSERT INTO analysis_history
                       (symbol, timestamp, analysis, created_at)
                       VALUES (?, ?, ?, ?)""",
                    (symbol, timestamp, analysis, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store analysis history for {symbol}: {e}")
                return False

    async def store_recommendation(self, symbol: str, recommendation_type: str,
                                  confidence_score: float, reasoning: str,
                                  analysis_type: str) -> bool:
        """
        Safely store recommendation with proper locking.

        Args:
            symbol: Stock symbol
            recommendation_type: Type of recommendation
            confidence_score: Confidence score
            reasoning: Reasoning text
            analysis_type: Type of analysis

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                current_time = datetime.now(timezone.utc).isoformat()

                await self.db.connection.execute(
                    """INSERT INTO recommendations
                       (symbol, recommendation_type, confidence_score, reasoning, analysis_type, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (symbol, recommendation_type, confidence_score, reasoning, analysis_type, current_time)
                )

                await self.db.connection.commit()
                return True

            except Exception as e:
                logger.error(f"Failed to store recommendation for {symbol}: {e}")
                return False
