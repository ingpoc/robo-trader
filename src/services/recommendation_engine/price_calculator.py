"""
Target Price Calculator for Recommendation Engine

Handles:
- Target price calculations
- Stop loss calculations
- Price analysis
"""

import logging
from typing import Any, Dict, Optional, Tuple

from loguru import logger

from src.core.state_models import FundamentalAnalysis

logger = logging.getLogger(__name__)


class TargetPriceCalculator:
    """Calculates target prices and stop losses for recommendations."""

    def __init__(self, claude_analyzer):
        self.claude_analyzer = claude_analyzer

    async def calculate_target_prices(
        self,
        symbol: str,
        fundamental_data: Optional[FundamentalAnalysis],
        recommendation_type: str,
        claude_analysis: Optional[Dict[str, Any]],
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate target price and stop loss based on analysis."""
        try:
            target_price = None
            stop_loss = None

            # Get current price
            current_price = await self._get_current_price(symbol, fundamental_data)

            if current_price:
                # Use Claude's target prices if available
                if claude_analysis and claude_analysis.get("target_price"):
                    target_prices = claude_analysis["target_price"]
                    if target_prices.get("base_case"):
                        target_price = target_prices["base_case"]

                if claude_analysis and claude_analysis.get("stop_loss"):
                    stop_losses = claude_analysis["stop_loss"]
                    if stop_losses.get("moderate"):
                        stop_loss = stop_losses["moderate"]

                # Fallback calculations if Claude analysis not available
                if not target_price and fundamental_data:
                    target_price = self._calculate_fundamental_target_price(
                        fundamental_data, recommendation_type, current_price
                    )

                if not stop_loss:
                    stop_loss = self._calculate_default_stop_loss(
                        current_price, recommendation_type
                    )

            return target_price, stop_loss

        except Exception as e:
            logger.error(f"Error calculating target prices for {symbol}: {e}")
            return None, None

    async def _get_current_price(
        self, symbol: str, fundamental_data: Optional[FundamentalAnalysis]
    ) -> Optional[float]:
        """Get current price for symbol."""
        try:
            # Get from Claude analyzer
            current_price = await self.claude_analyzer.get_current_price(symbol)

            # Fallback to fundamental data
            if (
                not current_price
                and fundamental_data
                and hasattr(fundamental_data, "current_price")
            ):
                current_price = fundamental_data.current_price

            return current_price

        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    def _calculate_fundamental_target_price(
        self,
        fundamental_data: FundamentalAnalysis,
        recommendation_type: str,
        current_price: float,
    ) -> Optional[float]:
        """Calculate target price based on fundamental analysis."""
        try:
            if (
                not hasattr(fundamental_data, "pe_ratio")
                or not fundamental_data.pe_ratio
            ):
                return None

            # Simple target price based on P/E ratio
            target_pe = fundamental_data.pe_ratio

            if recommendation_type == "BUY":
                target_pe *= 1.2  # 20% P/E expansion
            elif recommendation_type == "SELL":
                target_pe *= 0.9  # 10% P/E contraction
            else:  # HOLD
                target_pe *= 1.05  # 5% P/E expansion

            if hasattr(fundamental_data, "eps") and fundamental_data.eps:
                return target_pe * fundamental_data.eps

            return None

        except Exception as e:
            logger.error(f"Error calculating fundamental target price: {e}")
            return None

    def _calculate_default_stop_loss(
        self, current_price: float, recommendation_type: str
    ) -> float:
        """Calculate default stop loss based on recommendation type."""
        if recommendation_type == "BUY":
            return current_price * 0.92  # 8% stop loss
        elif recommendation_type == "HOLD":
            return current_price * 0.85  # 15% stop loss
        else:  # SELL
            return current_price * 0.95  # 5% stop loss (tight exit)

    def build_reasoning(
        self,
        factors,
        decision: Dict[str, Any],
        claude_analysis: Optional[Dict[str, Any]],
    ) -> str:
        """Build comprehensive reasoning for recommendation."""
        try:
            reasoning_parts = []

            # Add factor-based reasoning
            if hasattr(factors, "fundamental_score") and factors.fundamental_score:
                reasoning_parts.append(
                    f"Fundamental score: {factors.fundamental_score:.1f}/100"
                )
            if hasattr(factors, "valuation_score") and factors.valuation_score:
                reasoning_parts.append(
                    f"Valuation score: {factors.valuation_score:.1f}/100"
                )
            if hasattr(factors, "growth_score") and factors.growth_score:
                reasoning_parts.append(f"Growth score: {factors.growth_score:.1f}/100")
            if hasattr(factors, "risk_score") and factors.risk_score:
                reasoning_parts.append(f"Risk score: {factors.risk_score:.1f}/100")

            # Add Claude's qualitative analysis
            if claude_analysis and claude_analysis.get("reasoning"):
                reasoning_parts.append(
                    f"AI Analysis: {claude_analysis['reasoning'][:300]}..."
                )

            # Combine reasoning
            if reasoning_parts:
                return " | ".join(reasoning_parts)
            else:
                return "Based on multi-factor analysis and AI-powered insights"

        except Exception as e:
            logger.error(f"Error building reasoning: {e}")
            return "Multi-factor analysis with AI-powered insights"
