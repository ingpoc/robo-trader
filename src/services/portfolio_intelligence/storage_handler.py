"""
Storage Handler for Portfolio Intelligence

Handles:
- Analysis results storage
- Recommendation storage
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Any

logger = logging.getLogger(__name__)


class PortfolioStorageHandler:
    """Handles storage operations for portfolio intelligence analysis."""

    def __init__(self, config_state):
        self.config_state = config_state

    async def store_analysis_results(
        self,
        analysis_id: str,
        stocks_data: Dict[str, Dict[str, Any]],
        response_text: str,
        recommendations: List[Dict[str, Any]]
    ) -> None:
        """Store analysis results in the database using proper locked methods."""
        try:
            # Store analysis for each symbol
            current_time = datetime.now(timezone.utc).isoformat()

            for symbol in stocks_data.keys():
                analysis_data = {
                    "symbol": symbol,
                    "analysis_type": "portfolio_intelligence",
                    "claude_response": response_text,
                    "recommendations_count": len(recommendations),
                    "data_quality": {
                        "has_earnings": len(stocks_data[symbol].get("earnings", [])) > 0,
                        "has_news": len(stocks_data[symbol].get("news", [])) > 0,
                        "has_fundamentals": len(stocks_data[symbol].get("fundamental_analysis", [])) > 0,
                        "last_updates": stocks_data[symbol].get("data_summary", {})
                    },
                    "execution_metadata": {
                        "analysis_id": analysis_id,
                        "timestamp": current_time
                    }
                }

                # Use safe locked method instead of direct database access
                success = await self.config_state.store_analysis_history(
                    symbol=symbol,
                    timestamp=current_time,
                    analysis=json.dumps(analysis_data)
                )

                if success:
                    logger.debug(f"Stored analysis for {symbol}")
                else:
                    logger.warning(f"Failed to store analysis for {symbol}")

            logger.info(f"Stored analysis results for {len(stocks_data)} symbols in database")

        except Exception as e:
            logger.error(f"Failed to store analysis results: {e}", exc_info=True)

    async def store_recommendation(
        self,
        recommendation: Dict[str, Any],
        analysis_id: str
    ) -> None:
        """Store individual recommendation in the database using proper locked method."""
        try:
            # Use safe locked method instead of direct database access
            success = await self.config_state.store_recommendation(
                symbol=recommendation.get("symbol", "UNKNOWN"),
                recommendation_type=recommendation.get("action", "HOLD"),
                confidence_score=recommendation.get("confidence", 0.0),
                reasoning=recommendation.get("reasoning", ""),
                analysis_type="portfolio_intelligence"
            )

            if success:
                logger.debug(f"Stored recommendation for {recommendation.get('symbol', 'UNKNOWN')}")
            else:
                logger.warning(f"Failed to store recommendation for {recommendation.get('symbol', 'UNKNOWN')}")

        except Exception as e:
            logger.error(f"Failed to store recommendation: {e}", exc_info=True)
