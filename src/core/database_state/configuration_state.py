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
        self._lock = asyncio.Lock()

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

                # Initialize default configuration data
                await self._initialize_default_config()

            except Exception as e:
                logger.error(f"Failed to initialize configuration tables: {e}")
                raise

    async def _initialize_default_config(self) -> None:
        """Initialize default configuration data if tables are empty."""
        try:
            # Check if background tasks table is empty
            cursor = await self.db.connection.execute(
                "SELECT COUNT(*) as count FROM background_tasks_config"
            )
            row = await cursor.fetchone()
            if row[0] == 0:
                logger.info("Initializing default background tasks configuration...")

                # Default background tasks configuration
                default_tasks = [
                    {
                        "task_name": "earnings_processor",
                        "enabled": True,
                        "frequency_seconds": 3600,  # 1 hour
                        "frequency_unit": "hours",
                        "use_claude": True,
                        "priority": "high"
                    },
                    {
                        "task_name": "news_processor",
                        "enabled": True,
                        "frequency_seconds": 1800,  # 30 minutes
                        "frequency_unit": "minutes",
                        "use_claude": True,
                        "priority": "medium"
                    },
                    {
                        "task_name": "fundamental_analyzer",
                        "enabled": False,
                        "frequency_seconds": 14400,  # 4 hours
                        "frequency_unit": "hours",
                        "use_claude": True,
                        "priority": "medium"
                    },
                    {
                        "task_name": "deep_fundamental_processor",
                        "enabled": False,
                        "frequency_seconds": 86400,  # 24 hours
                        "frequency_unit": "hours",
                        "use_claude": True,
                        "priority": "low"
                    }
                ]

                # Insert default background tasks
                for task in default_tasks:
                    await self.db.connection.execute("""
                        INSERT INTO background_tasks_config
                        (task_name, enabled, frequency_seconds, frequency_unit, use_claude, priority, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        task["task_name"],
                        task["enabled"],
                        task["frequency_seconds"],
                        task["frequency_unit"],
                        task["use_claude"],
                        task["priority"],
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat()
                    ))

                await self.db.connection.commit()
                logger.info("Default background tasks configuration initialized")

            # Check if AI agents table is empty
            cursor = await self.db.connection.execute(
                "SELECT COUNT(*) as count FROM ai_agents_config"
            )
            row = await cursor.fetchone()
            if row[0] == 0:
                logger.info("Initializing default AI agents configuration...")

                # Default AI agents configuration
                default_agents = [
                    {
                        "agent_name": "technical_analyst",
                        "enabled": True,
                        "use_claude": True,
                        "tools": '["analyze_chart_patterns", "calculate_indicators", "identify_support_resistance"]',
                        "response_frequency": 30,
                        "response_frequency_unit": "minutes",
                        "scope": "portfolio",
                        "max_tokens_per_request": 2000
                    },
                    {
                        "agent_name": "fundamental_screener",
                        "enabled": False,
                        "use_claude": True,
                        "tools": '["analyze_financials", "screen_stocks", "calculate_valuation"]',
                        "response_frequency": 2,
                        "response_frequency_unit": "hours",
                        "scope": "market",
                        "max_tokens_per_request": 3000
                    },
                    {
                        "agent_name": "risk_manager",
                        "enabled": True,
                        "use_claude": True,
                        "tools": '["assess_portfolio_risk", "calculate_position_size", "monitor_drawdown"]',
                        "response_frequency": 15,
                        "response_frequency_unit": "minutes",
                        "scope": "portfolio",
                        "max_tokens_per_request": 1500
                    },
                    {
                        "agent_name": "portfolio_analyzer",
                        "enabled": True,
                        "use_claude": True,
                        "tools": '["analyze_performance", "calculate_metrics", "identify_optimization"]',
                        "response_frequency": 1,
                        "response_frequency_unit": "hours",
                        "scope": "portfolio",
                        "max_tokens_per_request": 2500
                    }
                ]

                # Insert default AI agents
                for agent in default_agents:
                    await self.db.connection.execute("""
                        INSERT INTO ai_agents_config
                        (agent_name, enabled, use_claude, tools, response_frequency, response_frequency_unit, scope, max_tokens_per_request, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        agent["agent_name"],
                        agent["enabled"],
                        agent["use_claude"],
                        agent["tools"],
                        agent["response_frequency"],
                        agent["response_frequency_unit"],
                        agent["scope"],
                        agent["max_tokens_per_request"],
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat()
                    ))

                await self.db.connection.commit()
                logger.info("Default AI agents configuration initialized")

            # Check if prompts table is empty
            cursor = await self.db.connection.execute(
                "SELECT COUNT(*) as count FROM ai_prompts_config"
            )
            row = await cursor.fetchone()
            if row[0] == 0:
                logger.info("Initializing default AI prompts configuration...")

                # Default AI prompts configuration
                default_prompts = [
                    {
                        "prompt_name": "earnings_processor",
                        "prompt_content": """For each stock, provide DETAILED earnings and financial fundamentals data in JSON format.

EARNINGS DATA (required):
- Latest quarterly earnings report date and fiscal period
- EPS (Actual vs Estimated): include exact numbers
- Revenue (Actual vs Estimated): include exact numbers in millions/billions
- EPS Surprise percentage
- Management guidance and outlook
- Next earnings date
- Year-over-year earnings growth rate (%)
- Quarter-over-quarter earnings growth rate (%)
- Net profit margins (gross, operating, net %)
- Revenue growth rate (YoY and QoQ %)

FUNDAMENTAL METRICS (required):
- Net profit growth trend (last 3-4 quarters with percentages)
- Current quarter profit growth vs prior quarter (%)
- Debt-to-Equity ratio
- Return on Equity (ROE %)
- Profit margins: Gross %, Operating %, Net %
- Return on Assets (ROA %)
- Current ratio

VALUATION METRICS (required):
- Price-to-Earnings (P/E) ratio
- Price-to-Sales (P/S) ratio
- Price-to-Book (P/B) ratio
- PEG ratio (P/E relative to growth)
- Industry average P/E for comparison
- Whether stock is trading above/below industry average""",
                        "description": "Prompt for fetching earnings and fundamental data from Perplexity API"
                    },
                    {
                        "prompt_name": "news_processor",
                        "prompt_content": """For each stock, provide recent market-moving news in JSON format.

NEWS DATA (required for each item):
- News title
- News summary (2-3 sentences)
- Full content/detailed analysis
- News source and exact publication date
- Type: (earnings_announcement, product_launch, regulatory, merger, guidance, dividend, stock_split, bankruptcy, restructuring, industry_trend, analyst_rating_change, contract_win, other)
- Sentiment: (positive, negative, neutral)
- Impact level: (high, medium, low) on stock price
- Relevance to stock price: (direct_impact, indirect_impact, contextual)
- Key metrics mentioned: list any financial metrics, growth rates, or numbers mentioned
- Why this is important: brief explanation of significance

SPECIFIC FOCUS (priority order):
1. Earnings announcements or reports from last 7 days with beat/miss info
2. Analyst upgrades/downgrades/rating changes from last 7 days
3. Major product launches, approvals, or announcements
4. Regulatory approvals, challenges, or compliance issues
5. M&A activity (acquisitions, mergers, divestitures)
6. Dividend announcements or changes
7. Major contract wins or losses
8. Industry trends affecting multiple companies in sector
9. Market analyst commentary and price targets""",
                        "description": "Prompt for fetching market news from Perplexity API"
                    },
                    {
                        "prompt_name": "fundamental_analyzer",
                        "prompt_content": """Analyze fundamental data and provide comprehensive financial analysis in JSON format.

ANALYSIS REQUIREMENTS:
- Company financial health assessment
- Growth trajectory evaluation
- Valuation analysis with industry comparisons
- Risk assessment and investment recommendations
- Key financial ratios and metrics interpretation
- Future outlook based on current fundamentals""",
                        "description": "Prompt for fundamental analysis processing"
                    },
                    {
                        "prompt_name": "deep_fundamental_processor",
                        "prompt_content": """Perform deep fundamental analysis including:

DETAILED ANALYSIS:
- Multi-year financial trend analysis
- Industry position and competitive advantages
- Management quality assessment
- Risk factor identification
- Long-term investment thesis
- Quantitative valuation models
- Comparative analysis with peers
- Sustainability and ESG factors""",
                        "description": "Prompt for deep fundamental analysis processing"
                    }
                ]

                # Insert default AI prompts
                for prompt in default_prompts:
                    await self.db.connection.execute("""
                        INSERT INTO ai_prompts_config
                        (prompt_name, prompt_content, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        prompt["prompt_name"],
                        prompt["prompt_content"],
                        prompt["description"],
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat()
                    ))

                await self.db.connection.commit()
                logger.info("Default AI prompts configuration initialized")

            # Check if global settings table is empty
            cursor = await self.db.connection.execute(
                "SELECT COUNT(*) as count FROM global_settings_config"
            )
            row = await cursor.fetchone()
            if row[0] == 0:
                logger.info("Initializing default global settings configuration...")

                # Default global settings configuration
                default_settings = [
                    {
                        "setting_key": "claude_usage_enabled",
                        "setting_value": "true",
                        "setting_type": "boolean",
                        "category": "claude",
                        "description": "Master switch for all Claude AI usage"
                    },
                    {
                        "setting_key": "claude_daily_token_limit",
                        "setting_value": "50000",
                        "setting_type": "number",
                        "category": "claude",
                        "description": "Daily token limit for Claude AI usage"
                    },
                    {
                        "setting_key": "claude_cost_alerts",
                        "setting_value": "true",
                        "setting_type": "boolean",
                        "category": "claude",
                        "description": "Enable cost alerts for Claude usage"
                    },
                    {
                        "setting_key": "claude_cost_threshold",
                        "setting_value": "10.00",
                        "setting_type": "number",
                        "category": "claude",
                        "description": "Cost threshold for alerts in USD"
                    },
                    {
                        "setting_key": "scheduler_default_frequency",
                        "setting_value": "30",
                        "setting_type": "number",
                        "category": "scheduler",
                        "description": "Default frequency for background tasks"
                    },
                    {
                        "setting_key": "scheduler_default_frequency_unit",
                        "setting_value": "minutes",
                        "setting_type": "string",
                        "category": "scheduler",
                        "description": "Default frequency unit for background tasks"
                    },
                    {
                        "setting_key": "scheduler_market_hours_only",
                        "setting_value": "true",
                        "setting_type": "boolean",
                        "category": "scheduler",
                        "description": "Run schedulers only during market hours"
                    },
                    {
                        "setting_key": "scheduler_retry_attempts",
                        "setting_value": "3",
                        "setting_type": "number",
                        "category": "scheduler",
                        "description": "Number of retry attempts for failed tasks"
                    },
                    {
                        "setting_key": "scheduler_retry_delay_minutes",
                        "setting_value": "5",
                        "setting_type": "number",
                        "category": "scheduler",
                        "description": "Delay between retry attempts in minutes"
                    },
                    {
                        "setting_key": "max_turns",
                        "setting_value": "5",
                        "setting_type": "number",
                        "category": "system",
                        "description": "Maximum number of conversation turns allowed"
                    },
                    {
                        "setting_key": "risk_tolerance",
                        "setting_value": "5",
                        "setting_type": "number",
                        "category": "system",
                        "description": "Risk tolerance level (1-10)"
                    },
                    {
                        "setting_key": "daily_api_limit",
                        "setting_value": "25",
                        "setting_type": "number",
                        "category": "system",
                        "description": "Daily API call limit"
                    }
                ]

                # Insert default global settings
                for setting in default_settings:
                    await self.db.connection.execute("""
                        INSERT INTO global_settings_config
                        (setting_key, setting_value, setting_type, category, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        setting["setting_key"],
                        setting["setting_value"],
                        setting["setting_type"],
                        setting["category"],
                        setting["description"],
                        datetime.now(timezone.utc).isoformat(),
                        datetime.now(timezone.utc).isoformat()
                    ))

                await self.db.connection.commit()
                logger.info("Default global settings configuration initialized")

        except Exception as e:
            logger.error(f"Failed to initialize default configuration: {e}")
            # Don't raise here - default config is not critical for startup

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
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM background_tasks_config ORDER BY priority DESC, task_name"
                )
                rows = await cursor.fetchall()

                background_tasks = {}
                for row in rows:
                    background_tasks[row[1]] = {  # task_name is at index 1
                        "enabled": bool(row[2]),     # enabled at index 2
                        "frequency": row[3],         # frequency_seconds at index 3
                        "frequencyUnit": row[4],     # frequency_unit at index 4
                        "useClaude": bool(row[5]),   # use_claude at index 5
                        "priority": row[6]           # priority at index 6
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

            now = datetime.now(timezone.utc).isoformat()

            # Insert or update
            await self.db.connection.execute(
                """
                INSERT OR REPLACE INTO background_tasks_config
                (task_name, enabled, frequency_seconds, frequency_unit, use_claude, priority, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task_name,
                    config_data.get("enabled", False),
                    frequency_seconds,
                    frequency_unit,
                    config_data.get("use_claude", True),
                    config_data.get("priority", "medium"),
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
        async with self._lock:
            try:
                cursor = await self.db.connection.execute(
                    "SELECT * FROM ai_agents_config ORDER BY agent_name"
                )
                rows = await cursor.fetchall()

                ai_agents = {}
                for row in rows:
                    try:
                        tools_data = json.loads(row[4]) if row[4] else []
                        ai_agents[row[1]] = {  # agent_name at index 1
                            "enabled": bool(row[2]),     # enabled at index 2
                            "useClaude": bool(row[3]),   # use_claude at index 3
                            "tools": tools_data,         # tools at index 4
                            "responseFrequency": row[5],  # response_frequency at index 5
                            "responseFrequencyUnit": row[6],  # response_frequency_unit at index 6
                            "scope": row[7],            # scope at index 7
                            "maxTokensPerRequest": row[8]  # max_tokens_per_request at index 8
                        }
                    except Exception as e:
                        logger.error(f"Failed to parse AI agent {row[1]}: {e}, tools data: {row[4]}")
                        continue

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
        async with self._lock:
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
                    key = row[1]  # setting_key at index 1
                    value = row[2]  # setting_value at index 2
                    category = row[4]  # category at index 4
                    setting_type = row[3]  # setting_type at index 3

                    # Parse value based on type
                    if setting_type == "boolean":
                        parsed_value = value.lower() == "true"
                    elif setting_type == "integer":
                        parsed_value = int(value)
                    elif setting_type == "float":
                        parsed_value = float(value)
                    else:
                        parsed_value = value

                    # Organize by category - map the stored keys to the expected keys
                    if category == "claude":
                        if key == "claude_usage_enabled":
                            global_settings["claude_usage"]["enabled"] = parsed_value
                        elif key == "claude_daily_token_limit":
                            global_settings["claude_usage"]["dailyTokenLimit"] = parsed_value
                        elif key == "claude_cost_alerts":
                            global_settings["claude_usage"]["costAlerts"] = parsed_value
                        elif key == "claude_cost_threshold":
                            global_settings["claude_usage"]["costThreshold"] = parsed_value
                    elif category == "scheduler":
                        if key == "scheduler_default_frequency":
                            global_settings["scheduler_defaults"]["defaultFrequency"] = parsed_value
                        elif key == "scheduler_default_frequency_unit":
                            global_settings["scheduler_defaults"]["defaultFrequencyUnit"] = parsed_value
                        elif key == "scheduler_market_hours_only":
                            global_settings["scheduler_defaults"]["marketHoursOnly"] = parsed_value
                        elif key == "scheduler_retry_attempts":
                            global_settings["scheduler_defaults"]["retryAttempts"] = parsed_value
                        elif key == "scheduler_retry_delay_minutes":
                            global_settings["scheduler_defaults"]["retryDelayMinutes"] = parsed_value
                    elif category == "system":
                        if key in ["max_turns", "risk_tolerance", "daily_api_limit"]:
                            global_settings[key] = parsed_value

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

                    # Insert or update (preserve created_at for existing rows)
                    await self.db.connection.execute(
                        """
                        INSERT OR IGNORE INTO global_settings_config
                        (setting_key, setting_value, setting_type, category, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (key, value_str, setting_type, category, "", now, now)
                    )

                    # Update existing row
                    await self.db.connection.execute(
                        """
                        UPDATE global_settings_config
                        SET setting_value = ?, setting_type = ?, category = ?, description = ?, updated_at = ?
                        WHERE setting_key = ?
                        """,
                        (value_str, setting_type, category, "", now, key)
                    )

            await self.db.connection.commit()

            # Create backup
            await self._create_backup("global_settings", "all")

            logger.info("Updated global settings configuration")
            return True

        except Exception as e:
            logger.error(f"Failed to update global settings config: {e}")
            return False

    async def get_all_prompts_config(self) -> Dict[str, Any]:
        """
        Get all AI prompts configuration.

        Returns:
            Dictionary containing all prompts
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    SELECT prompt_name, prompt_content, description, created_at, updated_at
                    FROM ai_prompts_config
                    ORDER BY prompt_name
                """)

                rows = await cursor.fetchall()

                prompts = {}
                for row in rows:
                    prompts[row[0]] = {  # prompt_name at index 0
                        "content": row[1],      # prompt_content at index 1
                        "description": row[2],  # description at index 2
                        "created_at": row[3],   # created_at at index 3
                        "updated_at": row[4]    # updated_at at index 4
                    }

                return {"prompts": prompts}

            except Exception as e:
                logger.error(f"Failed to get all prompts config: {e}")
                return {"prompts": {}}

    async def get_prompt_config(self, prompt_name: str) -> Dict[str, Any]:
        """
        Get specific prompt configuration.

        Args:
            prompt_name: Name of the prompt to retrieve

        Returns:
            Prompt configuration or empty dict if not found
        """
        async with self._lock:
            try:
                cursor = await self.db.connection.execute("""
                    SELECT prompt_name, prompt_content, description, created_at, updated_at
                    FROM ai_prompts_config
                    WHERE prompt_name = ?
                """, (prompt_name,))

                row = await cursor.fetchone()

                if row:
                    return {
                        "prompt_name": row[0],
                        "content": row[1],
                        "description": row[2],
                        "created_at": row[3],
                        "updated_at": row[4]
                    }

                return {}

            except Exception as e:
                logger.error(f"Failed to get prompt config for {prompt_name}: {e}")
                return {}

    async def update_prompt_config(
        self,
        prompt_name: str,
        prompt_content: str,
        description: str = ""
    ) -> bool:
        """
        Update AI prompt configuration.

        Args:
            prompt_name: Name of the prompt
            prompt_content: The prompt content
            description: Optional description

        Returns:
            True if successful, False otherwise
        """
        async with self._lock:
            try:
                now = datetime.now(timezone.utc).isoformat()

                # Try to update first (if row exists)
                cursor = await self.db.connection.execute(
                    """
                    UPDATE ai_prompts_config
                    SET prompt_content = ?, description = ?, updated_at = ?
                    WHERE prompt_name = ?
                    """,
                    (prompt_content, description, now, prompt_name)
                )

                # If no row was updated, insert new row
                if cursor.rowcount == 0:
                    await self.db.connection.execute(
                        """
                        INSERT INTO ai_prompts_config
                        (prompt_name, prompt_content, description, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (prompt_name, prompt_content, description, now, now)
                    )

                await self.db.connection.commit()

                # Create backup
                await self._create_backup("prompts", prompt_name)

                logger.info(f"Updated prompt configuration for {prompt_name}")
                return True

            except Exception as e:
                logger.error(f"Failed to update prompt config for {prompt_name}: {e}")
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