"""Agent management routes."""

import logging
import os
from typing import Dict, Any
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agents"])
limiter = Limiter(key_func=get_remote_address)

agents_limit = os.getenv("RATE_LIMIT_AGENTS", "20/minute")


@router.get("/agents/status")
@limiter.limit(agents_limit)
async def get_agents_status(request: Request) -> Dict[str, Any]:
    """Get all agents' status."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        agents_status = await orchestrator.get_agents_status()
        return agents_status or {"agents": []}
    except Exception as e:
        logger.error(f"Agents status failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/agents/{agent_name}/tools")
@limiter.limit(agents_limit)
async def get_agent_tools(request: Request, agent_name: str) -> Dict[str, Any]:
    """Get tools available to an agent."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        # Return mock tool definitions
        tools_map = {
            "market_analyzer": ["analyze_stock", "get_sector_analysis", "technical_scan"],
            "portfolio_manager": ["rebalance", "add_position", "remove_position", "review_allocation"],
            "risk_manager": ["assess_trade", "monitor_positions", "set_alerts"],
            "news_monitor": ["check_headlines", "analyze_sentiment", "track_events"],
        }

        tools = tools_map.get(agent_name, [])
        return {
            "agent": agent_name,
            "tools": [{"name": t, "description": f"{t} tool"} for t in tools]
        }
    except Exception as e:
        logger.error(f"Agent tools failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/agents/{agent_name}/config")
@limiter.limit(agents_limit)
async def get_agent_config(request: Request, agent_name: str) -> Dict[str, Any]:
    """Get agent configuration."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        orchestrator = await container.get_orchestrator()
        config = await container.get("config")

        if not config or not hasattr(config, 'agents'):
            return {
                "agent": agent_name,
                "enabled": True,
                "use_claude": True,
                "frequency_seconds": 300,
                "priority": "medium"
            }

        # Get agent config from config object
        agent_config = getattr(config.agents, agent_name, None)
        if agent_config:
            return {
                "agent": agent_name,
                **agent_config.to_dict()
            }

        return {
            "agent": agent_name,
            "enabled": True,
            "use_claude": True,
            "frequency_seconds": 300,
            "priority": "medium"
        }
    except Exception as e:
        logger.error(f"Agent config failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/agents/{agent_name}/config")
@limiter.limit(agents_limit)
async def update_agent_config(request: Request, agent_name: str, config_data: Dict[str, Any]) -> Dict[str, str]:
    """Update agent configuration."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        feature_management = await container.get("feature_management_service")

        if feature_management:
            # Update agent feature config
            await feature_management.update_feature(
                f"agent_{agent_name}",
                {
                    "enabled": config_data.get("enabled", True),
                    "use_claude": config_data.get("use_claude", True),
                    "frequency_seconds": config_data.get("frequency_seconds", 300),
                    "priority": config_data.get("priority", "medium")
                }
            )

        logger.info(f"Updated config for agent {agent_name}")
        return {"status": "Configuration updated", "agent": agent_name}
    except Exception as e:
        logger.error(f"Config update failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/agents/features")
@limiter.limit(agents_limit)
async def get_agent_features(request: Request) -> Dict[str, Any]:
    """Get all agent features."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        config = await container.get("config")

        if not config or not hasattr(config, 'agents'):
            return {"features": {}}

        features = config.agents.to_dict()
        return {"features": features}
    except Exception as e:
        logger.error(f"Agent features failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/agents/features/{feature_name}")
@limiter.limit(agents_limit)
async def get_agent_feature(request: Request, feature_name: str) -> Dict[str, Any]:
    """Get specific agent feature."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        config = await container.get("config")

        if not config or not hasattr(config, 'agents'):
            return {"feature": feature_name, "found": False}

        feature = getattr(config.agents, feature_name, None)
        if feature:
            return {"feature": feature_name, **feature.to_dict()}

        return {"feature": feature_name, "found": False}
    except Exception as e:
        logger.error(f"Agent feature failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/agents/features/{feature_name}")
@limiter.limit(agents_limit)
async def update_agent_feature(request: Request, feature_name: str, feature_data: Dict[str, Any]) -> Dict[str, str]:
    """Update agent feature configuration."""
    from ..app import container

    if not container:
        return JSONResponse({"error": "System not initialized"}, status_code=500)

    try:
        feature_management = await container.get("feature_management_service")

        if feature_management:
            await feature_management.update_feature(feature_name, feature_data)

        logger.info(f"Updated feature {feature_name}")
        return {"status": "Feature updated", "feature": feature_name}
    except Exception as e:
        logger.error(f"Feature update failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
