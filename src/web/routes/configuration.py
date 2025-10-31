"""Configuration management routes."""

import logging
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.core.di import DependencyContainer
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.models.scheduler import TaskType, QueueName
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

        return global_settings

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


@router.get("/configuration/prompts")
@limiter.limit(config_limit)
async def get_all_prompts(
    request: Request,
    container: DependencyContainer = Depends(get_container)
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
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Get specific prompt configuration from database."""
    try:
        config_state = await container.get("configuration_state")
        prompt = await config_state.get_prompt_config(prompt_name)
        if not prompt:
            raise HTTPException(status_code=404, detail=f"Prompt {prompt_name} not found")
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
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Update prompt configuration in database."""
    try:
        config_state = await container.get("configuration_state")
        success = await config_state.update_prompt_config(
            prompt_name=prompt_name,
            prompt_content=prompt_data.get("content", ""),
            description=prompt_data.get("description", "")
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
    container: DependencyContainer = Depends(get_container)
) -> Dict[str, Any]:
    """Manually execute a scheduler task.
    
    Optional request body: {"symbols": ["SYMBOL1", "SYMBOL2", ...]}
    If provided, uses these symbols. Otherwise, selects from portfolio.
    """
    import sys
    import time
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*80}\n[{timestamp}] [ENDPOINT CALLED] execute_scheduler_manually with task_name={task_name}\n{'='*80}\n", file=sys.stderr, flush=True)
    print(f"[ENDPOINT DEBUG] execute_scheduler_manually called with task_name={task_name}", flush=True)
    logger.info(f"Manual execution endpoint called for: {task_name}")
    
    # Try to get symbols from request body
    provided_symbols = None
    try:
        body = await request.json()
        if isinstance(body, dict) and "symbols" in body:
            provided_symbols = body.get("symbols")
            if isinstance(provided_symbols, list) and len(provided_symbols) > 0:
                logger.info(f"Received symbols from request body: {provided_symbols}")
    except Exception as e:
        logger.debug(f"Could not parse request body for symbols (this is OK if body is empty): {e}")
    
    try:
        logger.info(f"Manual execution requested for scheduler: {task_name}")

        # Get the background scheduler
        logger.info("Getting background scheduler...")
        background_scheduler = await container.get("background_scheduler")
        logger.info(f"Got background scheduler: {background_scheduler is not None}")

        # Create fundamental executor directly (simpler than DI registration issues)
        logger.info("Creating fundamental executor...")
        from src.core.background_scheduler.clients.perplexity_client import PerplexityClient
        from src.core.background_scheduler.executors.fundamental_executor import FundamentalExecutor

        state_manager = await container.get("state_manager")
        event_bus = await container.get("event_bus")
        configuration_state = await container.get("configuration_state")
        execution_tracker = await container.get("execution_tracker")

        perplexity_client = PerplexityClient(configuration_state=configuration_state)
        fundamental_executor = FundamentalExecutor(
            perplexity_client,
            state_manager.db.connection,
            event_bus,
            execution_tracker
        )
        logger.info("Fundamental executor created successfully")

        # Map task names to execution methods
        execution_map = {
            "earnings_processor": "execute_earnings_fundamentals",
            "news_processor": "execute_market_news_analysis",
            "fundamental_analyzer": "execute_deep_fundamental_analysis",
            "deep_fundamental_processor": "execute_deep_fundamental_analysis",
        }

        # Map scheduler names to queue task creation
        scheduler_map = {
            "portfolio_sync_scheduler": "trigger_portfolio_sync",
            "data_fetcher_scheduler": "trigger_data_fetch",
            "ai_analysis_scheduler": "trigger_ai_analysis",
        }

        if task_name in execution_map:
            # Handle processor execution
            execution_method = execution_map[task_name]
            is_processor = True
        elif task_name in scheduler_map:
            # Handle scheduler triggering
            scheduler_action = scheduler_map[task_name]
            is_processor = False
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown scheduler task: {task_name}. Available processors: {list(execution_map.keys())}, schedulers: {list(scheduler_map.keys())}"
            )

        # Check if the executor has the method (only for processors)
        if is_processor and not hasattr(fundamental_executor, execution_method):
            raise HTTPException(
                status_code=500,
                detail=f"Executor does not have method: {execution_method}"
            )

        # Use provided symbols if available, otherwise get from portfolio
        if provided_symbols and isinstance(provided_symbols, list) and len(provided_symbols) > 0:
            sample_symbols = provided_symbols
            logger.info(f"✅ Using provided symbols: {sample_symbols}")
            # Skip portfolio selection if symbols are provided
        else:
            # Get symbols from user's portfolio instead of hardcoded ones
            sample_symbols = ["RELIANCE", "TCS", "INFY", "HDFC", "ICICIBANK"]  # Default fallback
            logger.info("Starting portfolio-based symbol selection")

            # Get portfolio from orchestrator state manager (same as dashboard)
            try:
                orchestrator = await container.get_orchestrator()
                if orchestrator and orchestrator.state_manager:
                    portfolio_state = await orchestrator.state_manager.get_portfolio()
                    logger.info(f"Portfolio loaded with {len(portfolio_state.holdings) if portfolio_state and portfolio_state.holdings else 0} holdings")

                    # Extract symbols from portfolio holdings
                    if portfolio_state and portfolio_state.holdings:
                        portfolio_symbols = [holding.get("symbol") for holding in portfolio_state.holdings if holding.get("symbol")]
                        logger.info(f"Extracted {len(portfolio_symbols)} symbols from portfolio holdings")

                        if portfolio_symbols:
                            # Try to use stock state store for intelligent prioritization
                            try:
                                state_manager = await container.get("state_manager")
                                stock_state_store = state_manager.get_stock_state_store()
                                await stock_state_store.initialize()

                                # Select stocks based on scheduler type using oldest-first logic
                                if task_name == "news_processor":
                                    sample_symbols = await stock_state_store.get_oldest_news_stocks(portfolio_symbols, limit=5)
                                    logger.info(f"Selected {len(sample_symbols)} oldest news stocks: {sample_symbols}")
                                elif task_name == "earnings_processor":
                                    sample_symbols = await stock_state_store.get_oldest_earnings_stocks(portfolio_symbols, limit=5)
                                    logger.info(f"Selected {len(sample_symbols)} oldest earnings stocks: {sample_symbols}")
                                elif task_name in ["fundamental_analyzer", "deep_fundamental_processor"]:
                                    sample_symbols = await stock_state_store.get_oldest_fundamentals_stocks(portfolio_symbols, limit=5)
                                    logger.info(f"Selected {len(sample_symbols)} oldest fundamentals stocks: {sample_symbols}")
                                else:
                                    # Fallback: use first 5 portfolio symbols
                                    sample_symbols = portfolio_symbols[:5]
                                    logger.info(f"Using first 5 portfolio symbols for {task_name}: {sample_symbols}")

                            except Exception as e:
                                # Fallback: use portfolio symbols without prioritization
                                logger.warning(f"Failed to use stock state store for prioritization: {e}, using portfolio symbols directly")
                                sample_symbols = portfolio_symbols[:5]
                        else:
                            logger.warning("No symbols found in portfolio holdings")
                    else:
                        logger.warning("Portfolio state is empty or has no holdings")
                else:
                    logger.warning("Orchestrator or state_manager not available")

            except Exception as e:
                logger.error(f"Failed to get portfolio-based symbols: {e}, using default symbols", exc_info=True)

        logger.info(f"Final symbols for execution: {sample_symbols}")
        metadata = {
            "manual_execution": True,
            "requested_by": "user",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source": "configuration_api"
        }

        # Execute the task based on type
        import time
        start_time = time.time()

        if is_processor:
            # Execute processor method
            execution_func = getattr(fundamental_executor, execution_method)
            result = await execution_func(sample_symbols, metadata)
        else:
            # Trigger scheduler by calling BackgroundScheduler method
            if scheduler_action == "trigger_portfolio_sync":
                await background_scheduler._trigger_portfolio_sync()
                result = {"status": "success", "message": "Portfolio sync triggered"}
            elif scheduler_action == "trigger_data_fetch":
                await background_scheduler._trigger_data_fetch_sequence(sample_symbols)
                result = {"status": "success", "message": "Data fetch triggered"}
            elif scheduler_action == "trigger_ai_analysis":
                for symbol in sample_symbols[:3]:  # Limit to 3 symbols for AI analysis
                    await background_scheduler._trigger_ai_analysis(symbol, "manual")
                result = {"status": "success", "message": "AI analysis triggered"}
            else:
                result = {"status": "failed", "error": f"Unknown scheduler action: {scheduler_action}"}

        execution_time = time.time() - start_time

        logger.info(f"Manual execution completed for {task_name}: {result}")

        # Determine execution status
        execution_status = "completed" if result.get("status") == "success" else "failed"
        error_message = None if execution_status == "completed" else str(result.get("error", "Unknown error"))

        # Update stock state if execution was successful
        if execution_status == "completed":
            try:
                state_manager = await container.get("state_manager")
                stock_state_store = state_manager.get_stock_state_store()
                await stock_state_store.initialize()

                # Update last check date for executed stocks
                for symbol in sample_symbols:
                    if task_name == "news_processor":
                        await stock_state_store.update_news_check(symbol)
                        logger.info(f"Updated news check date for {symbol}")
                    elif task_name == "earnings_processor":
                        await stock_state_store.update_earnings_check(symbol)
                        logger.info(f"Updated earnings check date for {symbol}")
                    elif task_name in ["fundamental_analyzer", "deep_fundamental_processor"]:
                        await stock_state_store.update_fundamentals_check(symbol)
                        logger.info(f"Updated fundamentals check date for {symbol}")
            except Exception as e:
                logger.warning(f"Failed to update stock state after execution: {e}")

        # Record execution in background scheduler
        try:
            task_id = f"manual_{task_name}_{int(datetime.now(timezone.utc).timestamp())}"
            await background_scheduler.record_execution(
                task_name=task_name,
                task_id=task_id,
                execution_type="manual",
                user="user",
                symbols=sample_symbols,
                status=execution_status,
                error_message=error_message,
                execution_time=execution_time
            )
        except Exception as e:
            logger.warning(f"Failed to record manual execution: {e}")

        return {
            "status": execution_status,
            "task_name": task_name,
            "execution_method": execution_method,
            "symbols_processed": len(sample_symbols),
            "symbols": sample_symbols,
            "execution_time_seconds": execution_time,
            "result": result,
            "message": f"Manual execution {execution_status} for {task_name}",
            "timestamp": metadata["timestamp"]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to execute scheduler manually: {e}")
        return await handle_unexpected_error(e, "execute_scheduler_manually")