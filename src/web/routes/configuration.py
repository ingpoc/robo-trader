"""Configuration management routes."""

import logging
import os
from typing import Dict, Any

from fastapi import APIRouter, Request, Depends
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_unexpected_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["configuration"])
limiter = Limiter(key_func=get_remote_address)

config_limit = os.getenv("RATE_LIMIT_CONFIG", "30/minute")


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
        ai_agents = await config_state.get_all_ai_agents_config()

        logger.info(f"AI agents config retrieved: {len(ai_agents.get('ai_agents', {}))} agents")
        return ai_agents

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
        settings = global_settings.get("global_settings", {})
        settings.setdefault("quoteStreamProvider", container.config.integration.quote_stream_provider or "upstox")
        settings.setdefault("quoteStreamMode", container.config.integration.upstox_stream_mode or "ltpc")
        settings.setdefault("quoteStreamSymbolLimit", 50)

        return {"global_settings": settings}

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

        if any(key in settings_data for key in {"quoteStreamProvider", "quoteStreamMode"}):
            market_data_service = await container.get("market_data_service")
            if market_data_service is not None:
                await market_data_service.apply_runtime_preferences(
                    provider=settings_data.get("quoteStreamProvider"),
                    mode=settings_data.get("quoteStreamMode"),
                )

        logger.info("Updated global configuration settings in database")
        return {"status": "Global settings updated"}

    except Exception as e:
        return await handle_unexpected_error(e, "update_global_settings")


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
