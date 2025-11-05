"""
Factor Calculator for Recommendation Engine

Handles calculation of individual recommendation factors:
- Fundamental score
- Valuation score
- Growth score
- Risk score
- Qualitative score
"""

import logging
from typing import Optional, Dict, Any

from loguru import logger
from ..core.state_models import FundamentalAnalysis
from ..services.fundamental_service import FundamentalService
from ..services.risk_service import RiskService
from .models import RecommendationFactors

logger = logging.getLogger(__name__)


class FactorCalculator:
    """Calculates individual scoring factors for recommendations."""

    def __init__(
        self,
        fundamental_service: FundamentalService,
        risk_service: RiskService
    ):
        self.fundamental_service = fundamental_service
        self.risk_service = risk_service

    async def calculate_valuation_score(
        self,
        symbol: str,
        fundamental_data: Optional[FundamentalAnalysis]
    ) -> Optional[float]:
        """Calculate valuation score based on fundamental metrics."""
        try:
            if not fundamental_data:
                fundamental_data = await self.fundamental_service.get_fundamental_analysis(symbol)

            if not fundamental_data:
                logger.warning(f"No fundamental data available for valuation: {symbol}")
                return None

            valuation_score = 50.0  # Base score

            # P/E ratio analysis
            if hasattr(fundamental_data, 'pe_ratio') and fundamental_data.pe_ratio:
                pe = fundamental_data.pe_ratio
                if pe < 15:
                    valuation_score += 15  # Undervalued
                elif pe < 25:
                    valuation_score += 5   # Reasonable
                elif pe > 40:
                    valuation_score -= 15  # Overvalued

            # P/B ratio analysis
            if hasattr(fundamental_data, 'pb_ratio') and fundamental_data.pb_ratio:
                pb = fundamental_data.pb_ratio
                if pb < 1.0:
                    valuation_score += 10  # Below book value
                elif pb < 3.0:
                    valuation_score += 5   # Reasonable
                elif pb > 6.0:
                    valuation_score -= 10  # Overvalued

            # ROE analysis
            if hasattr(fundamental_data, 'roe') and fundamental_data.roe:
                roe = fundamental_data.roe
                if roe > 20:
                    valuation_score += 15  # High ROE
                elif roe > 15:
                    valuation_score += 10  # Good ROE
                elif roe < 8:
                    valuation_score -= 10  # Low ROE

            # Debt to Equity analysis
            if hasattr(fundamental_data, 'debt_to_equity') and fundamental_data.debt_to_equity:
                debt_ratio = fundamental_data.debt_to_equity
                if debt_ratio < 0.3:
                    valuation_score += 10  # Low debt
                elif debt_ratio > 1.0:
                    valuation_score -= 15  # High debt

            # Ensure score is within bounds
            return max(0, min(100, valuation_score))

        except Exception as e:
            logger.error(f"Error calculating valuation score for {symbol}: {e}")
            return None

    async def calculate_growth_score(
        self,
        symbol: str,
        fundamental_data: Optional[FundamentalAnalysis]
    ) -> Optional[float]:
        """Calculate growth score based on fundamental metrics."""
        try:
            if not fundamental_data:
                fundamental_data = await self.fundamental_service.get_fundamental_analysis(symbol)

            if not fundamental_data:
                logger.warning(f"No fundamental data available for growth: {symbol}")
                return None

            growth_score = 50.0  # Base score

            # Revenue growth analysis
            if (hasattr(fundamental_data, 'revenue_growth') and
                fundamental_data.revenue_growth is not None):
                revenue_growth = fundamental_data.revenue_growth
                if revenue_growth > 25:
                    growth_score += 20  # High growth
                elif revenue_growth > 15:
                    growth_score += 15  # Good growth
                elif revenue_growth > 5:
                    growth_score += 10  # Moderate growth
                elif revenue_growth < -5:
                    growth_score -= 20  # Declining

            # EPS growth analysis
            if (hasattr(fundamental_data, 'eps_growth') and
                fundamental_data.eps_growth is not None):
                eps_growth = fundamental_data.eps_growth
                if eps_growth > 20:
                    growth_score += 15  # High EPS growth
                elif eps_growth > 10:
                    growth_score += 10  # Good EPS growth
                elif eps_growth < 0:
                    growth_score -= 15  # EPS decline

            # Profit margin analysis
            if (hasattr(fundamental_data, 'profit_margin') and
                fundamental_data.profit_margin is not None):
                profit_margin = fundamental_data.profit_margin
                if profit_margin > 20:
                    growth_score += 10  # High margin
                elif profit_margin > 10:
                    growth_score += 5   # Good margin
                elif profit_margin < 5:
                    growth_score -= 10  # Low margin

            return max(0, min(100, growth_score))

        except Exception as e:
            logger.error(f"Error calculating growth score for {symbol}: {e}")
            return None

    async def calculate_risk_score(self, symbol: str) -> Optional[float]:
        """Calculate risk score based on volatility and market conditions."""
        try:
            # Get risk assessment from risk service
            risk_assessment = await self.risk_service.assess_portfolio_risk([symbol])

            if not risk_assessment or not risk_assessment.get(symbol):
                logger.warning(f"No risk assessment available for: {symbol}")
                return 50.0  # Neutral risk score

            symbol_risk = risk_assessment[symbol]
            risk_score = 50.0  # Base score

            # Volatility analysis
            if 'volatility' in symbol_risk:
                volatility = symbol_risk['volatility']
                if volatility < 0.15:
                    risk_score -= 15  # Low volatility = lower risk
                elif volatility > 0.35:
                    risk_score += 25  # High volatility = higher risk

            # Beta analysis
            if 'beta' in symbol_risk:
                beta = symbol_risk['beta']
                if beta < 0.8:
                    risk_score -= 10  # Low beta = lower risk
                elif beta > 1.3:
                    risk_score += 15  # High beta = higher risk

            # Risk level from service
            if 'risk_level' in symbol_risk:
                risk_level = symbol_risk['risk_level']
                if risk_level == 'LOW':
                    risk_score -= 20
                elif risk_level == 'HIGH':
                    risk_score += 20

            # Risk score: Lower is better, so we invert
            risk_score = 100 - max(0, min(100, risk_score))
            return risk_score

        except Exception as e:
            logger.error(f"Error calculating risk score for {symbol}: {e}")
            return None

    async def calculate_qualitative_score(self, symbol: str) -> Optional[float]:
        """Calculate qualitative score based on market sentiment and news."""
        try:
            # This would integrate with news analysis and market sentiment
            # For now, return a neutral score
            qualitative_score = 60.0  # Slightly positive default

            # TODO: Integrate with:
            # - News sentiment analysis
            # - Management quality assessment
            # - Industry outlook
            # - Competitive positioning
            # - Regulatory environment

            return qualitative_score

        except Exception as e:
            logger.error(f"Error calculating qualitative score for {symbol}: {e}")
            return None

    async def calculate_all_factors(
        self,
        symbol: str,
        fundamental_data: Optional[FundamentalAnalysis] = None
    ) -> RecommendationFactors:
        """Calculate all recommendation factors for a symbol."""
        if not fundamental_data:
            fundamental_data = await self.fundamental_service.get_fundamental_analysis(symbol)

        fundamental_score = getattr(fundamental_data, 'fundamental_score', 65.0) if fundamental_data else 50.0

        # Calculate all scores
        valuation_score = await self.calculate_valuation_score(symbol, fundamental_data)
        growth_score = await self.calculate_growth_score(symbol, fundamental_data)
        risk_score = await self.calculate_risk_score(symbol)
        qualitative_score = await self.calculate_qualitative_score(symbol)

        return RecommendationFactors(
            fundamental_score=fundamental_score,
            valuation_score=valuation_score,
            growth_score=growth_score,
            risk_score=risk_score,
            qualitative_score=qualitative_score
        )