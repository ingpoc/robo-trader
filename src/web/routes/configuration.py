"""Configuration management routes."""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.models.scheduler import QueueName, TaskType

from ..dependencies import get_container
from ..utils.error_handlers import (handle_unexpected_error)

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
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get background tasks configuration from database."""
    try:
        # Get configuration state from database
        config_state = await container.get("configuration_state")
        background_tasks = await config_state.get_all_background_tasks_config()

        return background_tasks
    except Exception as e:
        return await handle_unexpected_error(e, "get_background_tasks_config")


@router.put("/configuration/background-tasks/{task_name}")
@limiter.limit(config_limit)
async def update_background_task_config(
    request: Request,
    task_name: str,
    config_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container),
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
            stock_symbols=config_data.get("stock_symbols", []),
        )

        # Backup to JSON after database update
        await config_state.backup_to_json()

        logger.info(
            f"Updated background task configuration for {task_name} in database"
        )

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
                        "priority": config_data.get("priority", "medium"),
                    },
                )
            except Exception as e:
                logger.warning(
                    f"Failed to update feature management for {task_name}: {e}"
                )

        return {"status": "Configuration updated", "task": task_name}

    except Exception as e:
        return await handle_unexpected_error(e, "update_background_task_config")


@router.get("/configuration/ai-agents")
@limiter.limit(config_limit)
async def get_ai_agents_config(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get AI agents configuration from database."""
    try:
        # Get configuration state from database
        config_state = await container.get("configuration_state")
        ai_agents = await config_state.get_all_ai_agents_config()

        logger.info(
            f"AI agents config retrieved: {len(ai_agents.get('ai_agents', {}))} agents"
        )
        return ai_agents

    except Exception as e:
        return await handle_unexpected_error(e, "get_ai_agents_config")


@router.put("/configuration/ai-agents/{agent_name}")
@limiter.limit(config_limit)
async def update_ai_agent_config(
    request: Request,
    agent_name: str,
    config_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container),
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
            max_tokens_per_request=config_data.get("maxTokensPerRequest", 2000),
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
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get global configuration settings from database."""
    try:
        # Get configuration state from database
        config_state = await container.get("configuration_state")
        global_settings = await config_state.get_global_settings_config()

        return global_settings

    except Exception as e:
        return await handle_unexpected_error(e, "get_global_settings")


@router.put("/configuration/global-settings")
@limiter.limit(config_limit)
async def update_global_settings(
    request: Request,
    settings_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container),
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
    request: Request, container: DependencyContainer = Depends(get_container)
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
    container: DependencyContainer = Depends(get_container),
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
    request: Request, container: DependencyContainer = Depends(get_container)
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
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get configuration system status."""
    try:
        config_state = await container.get("configuration_state")
        status = await config_state.get_system_status()

        return {"configuration_status": status}

    except Exception as e:
        return await handle_unexpected_error(e, "get_configuration_status")


@router.get("/configuration/prompts")
@limiter.limit(config_limit)
async def get_all_prompts(
    request: Request, container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get all AI prompts configuration from database."""
    try:
        config_state = await container.get("configuration_state")
        prompts = await config_state.get_all_prompts_config()
        return prompts
    except Exception as e:
        return await handle_unexpected_error(e, "get_all_prompts")


@router.get("/configuration/prompts/{prompt_name}")
@limiter.limit(config_limit)
async def get_prompt(
    request: Request,
    prompt_name: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Get specific prompt configuration from database."""
    try:
        config_state = await container.get("configuration_state")
        prompt = await config_state.get_prompt_config(prompt_name)
        if not prompt:
            raise HTTPException(
                status_code=404, detail=f"Prompt {prompt_name} not found"
            )
        return prompt
    except HTTPException:
        raise
    except Exception as e:
        return await handle_unexpected_error(e, "get_prompt")


@router.put("/configuration/prompts/{prompt_name}")
@limiter.limit(config_limit)
async def update_prompt(
    request: Request,
    prompt_name: str,
    prompt_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Update prompt configuration in database."""
    try:
        config_state = await container.get("configuration_state")
        success = await config_state.update_prompt_config(
            prompt_name=prompt_name,
            prompt_content=prompt_data.get("content", ""),
            description=prompt_data.get("description", ""),
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update prompt")
        return {"status": "success", "prompt": prompt_name}
    except HTTPException:
        raise
    except Exception as e:
        return await handle_unexpected_error(e, "update_prompt")


@router.post("/configuration/schedulers/{task_name}/execute")
# @limiter.limit("10/minute")  # Stricter limit for manual execution - temporarily disabled for testing
async def execute_scheduler_manually(
    request: Request,
    task_name: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Manually execute a scheduler task via queue.

    Maps scheduler names to queue-based task creation.
    Returns immediately after queueing task.

    Optional request body: {"symbols": ["SYMBOL1", "SYMBOL2", ...]}
    """
    logger.info(f"Manual execution endpoint called for: {task_name}")

    # Map scheduler names to queue task creation
    scheduler_map = {
        "portfolio_sync_scheduler": (
            "trigger_portfolio_sync",
            QueueName.PORTFOLIO_SYNC,
            TaskType.SYNC_ACCOUNT_BALANCES,
        ),
        "data_fetcher_scheduler": (
            "trigger_data_fetch",
            QueueName.DATA_FETCHER,
            TaskType.FUNDAMENTALS_UPDATE,
        ),
        "ai_analysis_scheduler": (
            "trigger_ai_analysis",
            QueueName.AI_ANALYSIS,
            TaskType.RECOMMENDATION_GENERATION,
        ),
        "portfolio_analyzer": (
            "trigger_ai_analysis",
            QueueName.AI_ANALYSIS,
            TaskType.RECOMMENDATION_GENERATION,
        ),
    }

    # Check if this is a known scheduler
    if task_name not in scheduler_map:
        return {
            "status": "error",
            "message": f"Unknown scheduler: {task_name}",
            "available": list(scheduler_map.keys()),
        }

    # Get queue configuration
    scheduler_action, queue_name, task_type = scheduler_map[task_name]

    # Try to get symbols from request body
    symbols = ["AAPL", "MSFT"]  # Default symbols
    try:
        body = await request.json()
        if (
            isinstance(body, dict)
            and "symbols" in body
            and isinstance(body["symbols"], list)
        ):
            if len(body["symbols"]) > 0:
                symbols = body["symbols"]
                logger.info(f"Using provided symbols: {symbols}")
    except Exception as e:
        logger.debug(f"Could not parse request body: {e}")

    # Queue the task using task_service from DI container
    try:
        task_service = await container.get("task_service")
        task = await task_service.create_task(
            queue_name=queue_name,
            task_type=task_type,
            payload={"symbols": symbols, "manual_trigger": True},
            priority=8,
        )
        logger.info(f"✅ Task queued: {task_type} with symbols={symbols}")
        return {
            "status": "success",
            "message": f"{scheduler_action} queued",
            "task_id": task.task_id,
            "task_name": task_name,
            "task_type": task_type.value,
            "queue_name": queue_name.value,
            "symbols": symbols,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Failed to queue task: {e}", exc_info=True)
        return {
            "status": "error",
            "message": f"Failed to queue task: {str(e)}",
            "task_name": task_name,
        }


@router.post("/configuration/ai-agents/{agent_name}/execute")
@limiter.limit("5/minute")  # Stricter limit for AI agent execution
async def execute_ai_agent_manually(
    request: Request,
    agent_name: str,
    container: DependencyContainer = Depends(get_container),
) -> Dict[str, Any]:
    """Manually execute an AI agent for portfolio intelligence analysis.

    This endpoint:
    1. Finds stocks with recent updates (earnings, news, fundamentals)
    2. Gathers all available data for those stocks
    3. Uses Claude AI to analyze data quality and freshness
    4. Reviews and optimizes prompts if needed
    5. Provides investment recommendations
    6. Logs all activity to AI Transparency tab
    """
    import time

    timestamp = datetime.now(timezone.utc).isoformat()
    start_time = time.time()

    try:
        logger.info(f"Manual execution requested for AI agent: {agent_name}")

        # Only support portfolio_analyzer for now
        if agent_name != "portfolio_analyzer":
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported AI agent: {agent_name}. Only 'portfolio_analyzer' is currently supported.",
            )

        # Get task service for queuing
        task_service = await container.get("task_service")

        # Queue the analysis task instead of executing directly
        task = await task_service.create_task(
            queue_name=QueueName.AI_ANALYSIS,
            task_type=TaskType.RECOMMENDATION_GENERATION,
            payload={"agent_name": agent_name, "symbols": None},
            priority=7,  # High priority for manual requests
        )

        execution_time = time.time() - start_time

        logger.info(
            f"AI agent {agent_name} queued for execution in {execution_time:.2f} seconds. Task ID: {task.task_id}"
        )

        return {
            "status": "queued",
            "agent_name": agent_name,
            "task_id": task.task_id,
            "message": f"Portfolio analysis queued for execution. Task ID: {task.task_id}. Check AI Transparency tab for results.",
            "timestamp": timestamp,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing AI agent {agent_name}: {e}", exc_info=True)
        return await handle_unexpected_error(e, "execute_ai_agent_manually")
