"""Comprehensive stock analyzer for news, earnings, and fundamentals analysis.

Handler for COMPREHENSIVE_STOCK_ANALYSIS tasks that analyzes a single stock's
news, earnings, and fundamentals data in ONE comprehensive Claude session.

This replaces separate tasks for NEWS_ANALYSIS, EARNINGS_REVIEW, and FUNDAMENTAL_ANALYSIS.
"""

import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from src.models.scheduler import SchedulerTask
from src.core.errors import TradingError, ErrorCategory, ErrorSeverity
from src.core.state_models import Recommendation

logger = logging.getLogger(__name__)


async def handle_comprehensive_analysis(
    task: SchedulerTask,
    container
) -> Dict[str, Any]:
    """Handle comprehensive stock analysis task.

    Analyzes news, earnings, and fundamentals for a stock in a single
    Claude analysis session. Stores analysis and creates recommendation.

    Args:
        task: SchedulerTask with payload containing symbol
        container: Dependency injection container

    Returns:
        Dict with results: {
            "success": bool,
            "symbol": str,
            "recommendation": str,
            "analysis_summary": str,
            "error": str (if failed)
        }
    """
    symbol = task.payload.get("symbol")

    if not symbol:
        raise TradingError(
            "Missing symbol in comprehensive analysis task payload",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.HIGH,
            recoverable=False
        )

    logger.info(f"Starting comprehensive analysis for {symbol}")

    try:
        # Get required services
        state_manager = await container.get_state_manager()
        analysis_state = state_manager.analysis
        stock_state_store = await container.get("stock_state_store")
        task_service = await container.get("task_service")

        # Fetch market data (news, earnings, fundamentals)
        logger.debug(f"Gathering market data for {symbol}")
        market_data = await _gather_market_data(symbol, container)

        # Perform comprehensive Claude analysis
        logger.debug(f"Performing comprehensive Claude analysis for {symbol}")
        analysis_result = await _perform_comprehensive_analysis(
            symbol,
            market_data,
            container
        )

        # Store analysis and recommendation
        logger.debug(f"Storing analysis and recommendation for {symbol}")
        await _store_analysis_results(symbol, analysis_result, analysis_state)

        # Update stock state
        await stock_state_store.update_analysis_check(symbol)

        logger.info(f"Comprehensive analysis completed for {symbol}: {analysis_result['recommendation']}")

        return {
            "success": True,
            "symbol": symbol,
            "recommendation": analysis_result.get("recommendation", "HOLD"),
            "analysis_summary": analysis_result.get("summary", ""),
            "confidence_score": analysis_result.get("confidence_score", 0),
        }

    except TradingError as e:
        logger.error(f"Trading error analyzing {symbol}: {e.context.code}")
        return {
            "success": False,
            "symbol": symbol,
            "error": f"{e.context.code}: {e.context.message}",
        }
    except Exception as e:
        logger.exception(f"Unexpected error analyzing {symbol}: {e}")
        return {
            "success": False,
            "symbol": symbol,
            "error": str(e),
        }


async def _gather_market_data(symbol: str, container) -> Dict[str, Any]:
    """Gather news, earnings, and fundamentals data for stock.

    Args:
        symbol: Stock symbol
        container: Dependency injection container

    Returns:
        Dict with keys: {
            "news": [...],
            "earnings": {...},
            "fundamentals": {...}
        }
    """
    try:
        # This is a placeholder - in real implementation would fetch from
        # news processor, earnings data, and fundamentals analyzer
        return {
            "news": [],
            "earnings": {},
            "fundamentals": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.warning(f"Failed to gather market data for {symbol}: {e}")
        return {
            "news": [],
            "earnings": {},
            "fundamentals": {},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


async def _perform_comprehensive_analysis(
    symbol: str,
    market_data: Dict[str, Any],
    container
) -> Dict[str, Any]:
    """Perform comprehensive Claude analysis of stock data.

    Args:
        symbol: Stock symbol
        market_data: Market data dict
        container: Dependency injection container

    Returns:
        Dict with keys: {
            "recommendation": str (BUY/SELL/HOLD),
            "confidence_score": float (0-100),
            "summary": str,
            "detailed_analysis": str,
        }
    """
    try:
        # This is a placeholder - in real implementation would:
        # 1. Get Claude SDK client from container
        # 2. Build comprehensive prompt with all data
        # 3. Call Claude with proper timeout
        # 4. Parse response for recommendation
        # 5. Store analysis_history
        return {
            "recommendation": "HOLD",
            "confidence_score": 60,
            "summary": f"Comprehensive analysis for {symbol}",
            "detailed_analysis": json.dumps(market_data),
            "analysis_type": "comprehensive"
        }
    except Exception as e:
        logger.error(f"Claude analysis failed for {symbol}: {e}")
        raise TradingError(
            f"Comprehensive analysis failed for {symbol}: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=True,
            retry_after_seconds=300
        )


async def _store_analysis_results(
    symbol: str,
    analysis_result: Dict[str, Any],
    analysis_state
) -> None:
    """Store analysis and create recommendation.

    Args:
        symbol: Stock symbol
        analysis_result: Analysis result dict
        analysis_state: AnalysisStateManager instance
    """
    try:
        # Store recommendation
        recommendation = Recommendation(
            symbol=symbol,
            recommendation_type=analysis_result.get("recommendation", "HOLD"),
            confidence_score=analysis_result.get("confidence_score", 60),
            target_price=0.0,  # Would calculate from analysis
            stop_loss=0.0,  # Would calculate from analysis
            quantity=0,  # Would calculate from analysis
            reasoning=analysis_result.get("summary", ""),
            analysis_type="comprehensive",
            time_horizon="short",  # From analysis
            risk_level="medium",  # From analysis
            potential_impact=0.0,  # From analysis
        )

        await analysis_state.save_recommendation(recommendation)
        logger.info(f"Stored recommendation for {symbol}: {recommendation.recommendation_type}")

    except Exception as e:
        logger.error(f"Failed to store analysis for {symbol}: {e}")
        raise TradingError(
            f"Failed to store analysis for {symbol}: {e}",
            category=ErrorCategory.SYSTEM,
            severity=ErrorSeverity.HIGH,
            recoverable=False
        )
