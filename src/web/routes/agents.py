"""Agent management routes."""

import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError
from ..dependencies import get_container
from ..utils.error_handlers import (
    handle_trading_error,
    handle_unexpected_error,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["agents"])
limiter = Limiter(key_func=get_remote_address)

agents_limit = os.getenv("RATE_LIMIT_AGENTS", "20/minute")


@router.get("/agents/status")
@limiter.limit(agents_limit)
async def get_agents_status(
    request: Request,
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get all agents' status."""
    try:
        orchestrator = await container.get_orchestrator()
        agents_status = await orchestrator.get_agents_status()
        return agents_status or {"agents": []}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_agents_status")


@router.get("/agents")
@limiter.limit(agents_limit)
async def get_agents(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get all agents from orchestrator."""
    try:
        # Use the real orchestrator to get agents status
        orchestrator = await container.get_orchestrator()
        agents_data = await orchestrator.get_agents_status()

        # Transform to frontend format
        agents_list = []
        if agents_data and isinstance(agents_data, dict):
            for agent_name, agent_info in agents_data.items():
                agents_list.append({
                    "name": agent_name,
                    "status": agent_info.get("status", "idle"),
                    "lastAction": agent_info.get("last_activity", "unknown"),
                    "tasksCompleted": 0,  # TODO: Track in database
                    "currentTask": None  # TODO: Track current task
                })

        return {"agents": agents_list}
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_agents")


@router.get("/agents/{agent_name}/tools")
@limiter.limit(agents_limit)
async def get_agent_tools(request: Request, agent_name: str, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get tools available to an agent."""
    try:
        # Get agent info from orchestrator
        orchestrator = await container.get_orchestrator()
        agents_data = await orchestrator.get_agents_status()

        tools = []
        if agents_data and agent_name in agents_data:
            # Get tools from agent info
            tools_list = agents_data[agent_name].get("tools", [])
            tools = [{"name": t, "description": f"{t} tool"} for t in tools_list]

        return {
            "agent": agent_name,
            "tools": tools
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_agent_tools")


@router.get("/agents/{agent_name}/config")
@limiter.limit(agents_limit)
async def get_agent_config(request: Request, agent_name: str, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get agent configuration from config."""
    try:
        config = await container.get("config")

        # Get agent config from config.json
        agent_config = None
        if config and hasattr(config, 'agents'):
            agent_config = getattr(config.agents, agent_name, None)

        if agent_config:
            return {
                "agent": agent_name,
                "enabled": getattr(agent_config, 'enabled', False),
                "use_claude": getattr(agent_config, 'use_claude', True),
                "frequency_seconds": getattr(agent_config, 'frequency_seconds', 300),
                "priority": getattr(agent_config, 'priority', "medium")
            }

        return {
            "agent": agent_name,
            "enabled": False,
            "use_claude": True,
            "frequency_seconds": 300,
            "priority": "medium"
        }
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "get_agent_config")


@router.post("/agents/{agent_name}/config")
@limiter.limit(agents_limit)
async def update_agent_config(
    request: Request,
    agent_name: str,
    config_data: Dict[str, Any],
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, str]:
    """Update agent configuration."""
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
    except TradingError as e:
        return await handle_trading_error(e)
    except Exception as e:
        return await handle_unexpected_error(e, "update_agent_config")


@router.get("/agents/features")
@limiter.limit(agents_limit)
async def get_agent_features(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get all agent features from config."""
    try:
        config = await container.get("config")

        features = {}
        if config and hasattr(config, 'agents'):
            # Get all agent configs from config.json
            agents_config = config.agents
            if hasattr(agents_config, '__dict__'):
                for agent_name, agent_cfg in agents_config.__dict__.items():
                    if hasattr(agent_cfg, 'enabled'):
                        features[agent_name] = {
                            "enabled": getattr(agent_cfg, 'enabled', False),
                            "use_claude": getattr(agent_cfg, 'use_claude', True)
                        }

        return {"agents": features}
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/agents/features/{feature_name}")
@limiter.limit(agents_limit)
async def get_agent_feature(request: Request, feature_name: str, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get specific agent feature."""

    try:
        config = await container.get("config")

        if not config or not hasattr(config, 'agents'):
            return {"feature": feature_name, "found": False}

        feature = getattr(config.agents, feature_name, None)
        if feature:
            return {"feature": feature_name, **feature.to_dict()}

        return {"feature": feature_name, "found": False}
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.put("/agents/features/{feature_name}")
@limiter.limit(agents_limit)
async def update_agent_feature(request: Request, feature_name: str, feature_data: Dict[str, Any], container: DependencyContainer = Depends(get_container)) -> Dict[str, str]:
    """Update agent feature configuration."""

    try:
        feature_management = await container.get("feature_management_service")

        if feature_management:
            await feature_management.update_feature(feature_name, feature_data)

        logger.info(f"Updated feature {feature_name}")
        return {"status": "Feature updated", "feature": feature_name}
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/claude-agent/token-budget")
@limiter.limit(agents_limit)
async def get_token_budget(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude AI token budget information from database."""
    try:
        # TODO: Implement token tracking from claude_token_usage table
        # For now, return empty/default structure
        config = await container.get("config")
        daily_budget = 15000
        if config and hasattr(config, 'claude_agent'):
            daily_budget = getattr(config.claude_agent, 'daily_token_budget', 15000)

        return {
            "dailyBudget": daily_budget,
            "usedToday": 0,
            "remainingToday": daily_budget,
            "allocations": {},
            "usage": {},
            "warningLevel": 70,
            "criticalLevel": 90,
            "status": "normal"
        }
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/scheduler/queue-status")
@limiter.limit(agents_limit)
async def get_queue_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get scheduler queue status from queue coordinator."""
    try:
        # TODO: Implement real queue status from QueueCoordinator
        # For now, return empty queues
        return {
            "dataFetcherQueue": {
                "inProgress": None,
                "queued": [],
                "avgTaskTime": "0 seconds",
                "successRate": "0%"
            },
            "aiAnalysisQueue": {
                "inProgress": None,
                "queued": [],
                "avgTaskTime": "0 seconds",
                "successRate": "0%"
            }
        }
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/queues/status")
@limiter.limit(agents_limit)
async def get_queues_status(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get queues status from queue coordinator."""
    try:
        # TODO: Implement real queue status from QueueCoordinator
        # For now, return empty queues
        return {
            "queues": {
                "dataFetcherQueue": {
                    "inProgress": None,
                    "queued": [],
                    "avgTaskTime": "0 seconds",
                    "successRate": "0%"
                },
                "aiAnalysisQueue": {
                    "inProgress": None,
                    "queued": [],
                    "avgTaskTime": "0 seconds",
                    "successRate": "0%"
                }
            }
        }
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/claude-agent/plans")
@limiter.limit(agents_limit)
async def get_claude_plans(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's daily and weekly plans from database."""
    try:
        # TODO: Implement plans storage in database table: claude_plans
        # For now, return empty plans
        return {
            "dailyPlan": {
                "date": datetime.now(timezone.utc).date().isoformat(),
                "time": datetime.now(timezone.utc).time().isoformat(),
                "focus": [],
                "tasks": []
            },
            "weeklyPlan": {
                "week": f"Week of {datetime.now(timezone.utc).date().isoformat()}",
                "day": datetime.now(timezone.utc).strftime("%A"),
                "time": datetime.now(timezone.utc).time().isoformat(),
                "focus": [],
                "tasks": []
            }
        }
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/claude-agent/trade-logs")
@limiter.limit(agents_limit)
async def get_trade_logs(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's trade decision logs from database."""
    try:
        # TODO: Implement trade logs from database table: claude_trade_logs
        # For now, return empty logs
        return {
            "tradeLogs": []
        }
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")


@router.get("/claude-agent/strategy-reflections")
@limiter.limit(agents_limit)
async def get_strategy_reflections(request: Request, container: DependencyContainer = Depends(get_container)) -> Dict[str, Any]:
    """Get Claude's strategy reflections from database."""
    try:
        # TODO: Implement strategy reflections from claude_strategy_logs table
        # This table already exists, need to query it properly
        # For now, return empty reflections
        return {
            "reflections": []
        }
    except Exception as e:
        return await handle_trading_error(e) if isinstance(e, TradingError) else await handle_unexpected_error(e, "endpoint")
