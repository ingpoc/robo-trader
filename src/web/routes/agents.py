"""Agent management routes."""

import logging
import os
from typing import Dict, Any
from datetime import datetime, timezone
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
    try:
        # Return default config for any agent
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
    container = request.app.state.container

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
    try:
        # Return default features
        return {
            "features": {
                "chat_interface": {"enabled": True, "use_claude": True},
                "portfolio_scan": {"enabled": True, "use_claude": True},
                "market_screening": {"enabled": True, "use_claude": True},
                "market_monitoring": {"enabled": True, "use_claude": True},
                "stop_loss_monitor": {"enabled": True, "use_claude": False},
                "earnings_check": {"enabled": True, "use_claude": True},
                "news_monitoring": {"enabled": True, "use_claude": True},
                "ai_daily_planning": {"enabled": True, "use_claude": True},
                "health_check": {"enabled": True, "use_claude": False},
                "trade_execution": {"enabled": True, "use_claude": True},
                "fundamental_monitoring": {"enabled": True, "use_claude": False},
            }
        }
    except Exception as e:
        logger.error(f"Agent features failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/agents/features/{feature_name}")
@limiter.limit(agents_limit)
async def get_agent_feature(request: Request, feature_name: str) -> Dict[str, Any]:
    """Get specific agent feature."""
    container = request.app.state.container

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
    container = request.app.state.container

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


@router.get("/claude-agent/token-budget")
@limiter.limit(agents_limit)
async def get_token_budget(request: Request) -> Dict[str, Any]:
    """Get Claude AI token budget information."""
    try:
        return {
            "dailyBudget": 15000,
            "usedToday": 8500,
            "remainingToday": 6500,
            "allocations": {
                "swing": {"percentage": 40, "tokens": 6000},
                "options": {"percentage": 35, "tokens": 5250},
                "analysis": {"percentage": 25, "tokens": 3750}
            },
            "usage": {
                "swingPrep": 2500,
                "optionsPrep": 2000,
                "newsAnalysis": 1500,
                "recommendations": 1200,
                "learningLogs": 800
            },
            "warningLevel": 70,
            "criticalLevel": 90,
            "status": "normal"
        }
    except Exception as e:
        logger.error(f"Token budget retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/scheduler/queue-status")
@limiter.limit(agents_limit)
async def get_queue_status(request: Request) -> Dict[str, Any]:
    """Get scheduler queue status."""
    try:
        return {
            "dataFetcherQueue": {
                "inProgress": {
                    "task": "Fetch news for TCS, INFY, HDFC",
                    "progress": 65,
                    "timeRemaining": "2 minutes"
                },
                "queued": [
                    {"task": "Fetch earnings for SBIN", "position": 1},
                    {"task": "Fetch fundamentals for LT", "position": 2},
                    {"task": "Fetch recommendations for MARUTI", "position": 3}
                ],
                "avgTaskTime": "45 seconds",
                "successRate": "98.5%"
            },
            "aiAnalysisQueue": {
                "inProgress": {
                    "task": "Analyze market sentiment",
                    "progress": 45,
                    "timeRemaining": "3 minutes"
                },
                "queued": [
                    {"task": "Generate daily plan", "position": 1},
                    {"task": "Evaluate strategies", "position": 2},
                    {"task": "Calculate risk metrics", "position": 3},
                    {"task": "Generate recommendations", "position": 4}
                ],
                "avgTaskTime": "2 minutes",
                "successRate": "97.2%"
            }
        }
    except Exception as e:
        logger.error(f"Queue status retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/claude-agent/plans")
@limiter.limit(agents_limit)
async def get_claude_plans(request: Request) -> Dict[str, Any]:
    """Get Claude's daily and weekly plans."""
    try:
        return {
            "dailyPlan": {
                "date": "2025-10-24",
                "time": "09:15 IST",
                "focus": [
                    "Focus on momentum breakouts in large-cap stocks",
                    "Monitor NIFTY for 23000 breakout confirmation",
                    "Check earnings announcements for TCS and INFY today",
                    "Rebalance portfolio if options expire today"
                ],
                "tasks": [
                    "Scan portfolio for gap opportunities",
                    "Review news for material updates",
                    "Generate trade recommendations",
                    "Execute pre-approved trades"
                ]
            },
            "weeklyPlan": {
                "week": "Week of 2025-10-20",
                "day": "Monday",
                "time": "09:15 IST",
                "focus": [
                    "Weekly trend analysis across all holdings",
                    "Earnings calendar review for next 30 days",
                    "Risk assessment and hedging strategy",
                    "Token budget allocation review"
                ],
                "tasks": [
                    "Update fundamental analysis for all holdings",
                    "Review performance of strategies",
                    "Optimize portfolio allocation",
                    "Plan weekly trading approach"
                ]
            }
        }
    except Exception as e:
        logger.error(f"Plans retrieval failed: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
