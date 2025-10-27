"""Configuration management routes."""

import logging
import json
import os
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["configuration"])
limiter = Limiter(key_func=get_remote_address)

config_limit = os.getenv("RATE_LIMIT_CONFIG", "30/minute")

# Configuration file paths
CONFIG_PATH = Path("config/config.json")
BACKGROUND_TASKS_CONFIG = Path("config/background_tasks.json")
AI_AGENTS_CONFIG = Path("config/ai_agents.json")
GLOBAL_SETTINGS_CONFIG = Path("config/global_settings.json")


@router.get("/configuration/background-tasks")
@limiter.limit(config_limit)
async def get_background_tasks_config(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get background tasks configuration from database."""
    try:
        # Get configuration state from database
        config_state = await container.get("configuration_state")
        background_tasks = await config_state.get_background_tasks_config()

        return {"background_tasks": background_tasks}
    except Exception as e:
        return await handle_unexpected_error(e, "get_background_tasks_config")


@router.put("/configuration/background-tasks/{task_name}")
@limiter.limit(config_limit)
async def update_background_task_config(
    request: Request,
    task_name: str,
    config_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Update background task configuration in database."""
    try:
        # Convert user-friendly frequency to seconds
        frequency_seconds = config_data.get("frequency", 3600)
        frequency_unit = config_data.get("frequency_unit", "seconds")

        # Convert to seconds
        if frequency_unit == "minutes":
            frequency_seconds = frequency_seconds * 60
        elif frequency_unit == "hours":
            frequency_seconds = frequency_seconds * 3600
        elif frequency_unit == "days":
            frequency_seconds = frequency_seconds * 86400

        # Get configuration state and update database
        config_state = await container.get("configuration_state")
        await config_state.update_background_task_config(
            task_name=task_name,
            enabled=config_data.get("enabled", False),
            frequency_seconds=frequency_seconds,
            frequency_unit=frequency_unit,
            use_claude=config_data.get("use_claude", True),
            priority=config_data.get("priority", "medium"),
            stock_symbols=config_data.get("stock_symbols", [])
        )

        # Backup to JSON after database update
        await config_state.backup_to_json()

        logger.info(f"Updated background task configuration for {task_name} in database")

        # If the feature management service is available, also update it
        feature_management = await container.get("feature_management_service")
        if feature_management:
            try:
                await feature_management.update_feature(
                    task_name,
                    {
                        "enabled": config_data.get("enabled", False),
                        "use_claude": config_data.get("use_claude", True),
                        "frequency_seconds": frequency_seconds,
                        "priority": config_data.get("priority", "medium")
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to update feature management for {task_name}: {e}")

        return {"status": "Configuration updated", "task": task_name}

    except Exception as e:
        return await handle_unexpected_error(e, "update_background_task_config")


@router.get("/configuration/ai-agents")
@limiter.limit(config_limit)
async def get_ai_agents_config(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get AI agents configuration from database."""
    try:
        # Get configuration state from database
        config_state = await container.get("configuration_state")
        ai_agents = await config_state.get_ai_agents_config()

        return {"ai_agents": ai_agents}

    except Exception as e:
        return await handle_unexpected_error(e, "get_ai_agents_config")


@router.put("/configuration/ai-agents/{agent_name}")
@limiter.limit(config_limit)
async def update_ai_agent_config(
    request: Request,
    agent_name: str,
    config_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Update AI agent configuration in database."""
    try:
        # Get configuration state and update database
        config_state = await container.get("configuration_state")
        await config_state.update_ai_agent_config(
            agent_name=agent_name,
            enabled=config_data.get("enabled", False),
            use_claude=config_data.get("useClaude", True),
            tools=config_data.get("tools", []),
            response_frequency=config_data.get("responseFrequency", 30),
            response_frequency_unit=config_data.get("responseFrequencyUnit", "minutes"),
            scope=config_data.get("scope", "portfolio"),
            max_tokens_per_request=config_data.get("maxTokensPerRequest", 2000)
        )

        # Backup to JSON after database update
        await config_state.backup_to_json()

        logger.info(f"Updated AI agent configuration for {agent_name} in database")
        return {"status": "Configuration updated", "agent": agent_name}

    except Exception as e:
        return await handle_unexpected_error(e, "update_ai_agent_config")


@router.get("/configuration/global-settings")
@limiter.limit(config_limit)
async def get_global_settings(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get global configuration settings from database."""
    try:
        # Get configuration state from database
        config_state = await container.get("configuration_state")
        global_settings = await config_state.get_global_settings_config()

        return {"global_settings": global_settings}

    except Exception as e:
        return await handle_unexpected_error(e, "get_global_settings")


@router.put("/configuration/global-settings")
@limiter.limit(config_limit)
async def update_global_settings(
    request: Request,
    settings_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Update global configuration settings in database."""
    try:
        # Get configuration state and update database
        config_state = await container.get("configuration_state")
        await config_state.update_global_settings_config(settings_data)

        # Backup to JSON after database update
        await config_state.backup_to_json()

        logger.info("Updated global configuration settings in database")
        return {"status": "Global settings updated"}

    except Exception as e:
        return await handle_unexpected_error(e, "update_global_settings")


@router.post("/configuration/backup")
@limiter.limit(config_limit)
async def backup_configuration(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Create a backup of all configuration from database."""
    try:
        # Get configuration state and create backup
        config_state = await container.get("configuration_state")
        timestamp = await config_state.create_backup()

        logger.info(f"Configuration backup created from database: {timestamp}")
        return {"status": "Backup created", "timestamp": timestamp}

    except Exception as e:
        return await handle_unexpected_error(e, "backup_configuration")


@router.post("/configuration/restore")
@limiter.limit(config_limit)
async def restore_configuration(
    request: Request,
    restore_data: Dict[str, str],
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Restore configuration from backup to database."""
    try:
        timestamp = restore_data.get("timestamp")
        if not timestamp:
            raise HTTPException(status_code=400, detail="Timestamp is required")

        # Get configuration state and restore from backup
        config_state = await container.get("configuration_state")
        await config_state.restore_from_backup(timestamp)

        logger.info(f"Configuration restored from backup to database: {timestamp}")
        return {"status": "Configuration restored", "timestamp": timestamp}

    except Exception as e:
        return await handle_unexpected_error(e, "restore_configuration")


@router.post("/configuration/migrate-to-db")
@limiter.limit(config_limit)
async def migrate_configuration_to_db(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Migrate existing configuration from JSON files to database."""
    try:
        # Get configuration state and migrate from JSON
        config_state = await container.get("configuration_state")
        await config_state.migrate_from_json()

        logger.info("Configuration migrated from JSON to database")
        return {"status": "Configuration migrated to database successfully"}

    except Exception as e:
        return await handle_unexpected_error(e, "migrate_configuration_to_db")


@router.get("/configuration/status")
@limiter.limit(config_limit)
async def get_configuration_status(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get configuration system status."""
    try:
        config_state = await container.get("configuration_state")
        status = await config_state.get_system_status()

        return {"configuration_status": status}

    except Exception as e:
        return await handle_unexpected_error(e, "get_configuration_status")