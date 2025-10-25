"""
Deep fundamental analysis processor.

Processes comprehensive fundamental data from Perplexity API including:
- Revenue and earnings growth analysis
- Profitability assessment
- Financial position analysis
- Valuation metrics
- Growth sustainability
- Risk assessment
- Investment recommendations
"""

import json
from typing import Dict, List, Any, Optional

from loguru import logger


class DeepFundamentalProcessor:
    """Processes deep fundamental analysis data for investment assessment."""

    @staticmethod
    def parse_deep_fundamentals(response_text: str) -> Dict[str, Any]:
        """Parse deep fundamental analysis response from Perplexity.

        Args:
            response_text: Raw JSON response from Perplexity API

        Returns:
            Parsed fundamental data dictionary with all metrics
        """
        if not response_text or not isinstance(response_text, str):
            logger.warning("Empty or invalid fundamental data")
            return {}

        try:
            data = json.loads(response_text)

            if isinstance(data, dict) and 'data' in data:
                data = data['data']

            if not isinstance(data, dict):
                logger.warning(f"Unexpected data structure: {type(data)}")
                return {}

            return data

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error parsing fundamentals: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error parsing comprehensive fundamentals: {e}")
            return {}

    @staticmethod
    def extract_growth_analysis(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract revenue and earnings growth metrics.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Growth metrics with YoY, QoQ, and trends
        """
        growth = {
            "revenue_growth_yoy": None,
            "revenue_growth_qoq": None,
            "earnings_growth_yoy": None,
            "earnings_growth_qoq": None,
            "revenue_trend": None,
            "earnings_trend": None,
            "growth_trajectory": None
        }

        if not fund_data:
            return growth

        for key, value in fund_data.items():
            key_lower = key.lower()

            if "revenue_growth" in key_lower:
                if "yoy" in key_lower or "year" in key_lower:
                    growth["revenue_growth_yoy"] = DeepFundamentalProcessor._safe_float(value)
                elif "qoq" in key_lower or "quarter" in key_lower:
                    growth["revenue_growth_qoq"] = DeepFundamentalProcessor._safe_float(value)

            elif "earnings_growth" in key_lower:
                if "yoy" in key_lower or "year" in key_lower:
                    growth["earnings_growth_yoy"] = DeepFundamentalProcessor._safe_float(value)
                elif "qoq" in key_lower or "quarter" in key_lower:
                    growth["earnings_growth_qoq"] = DeepFundamentalProcessor._safe_float(value)

            elif "revenue_trend" in key_lower:
                growth["revenue_trend"] = value
            elif "earnings_trend" in key_lower:
                growth["earnings_trend"] = value
            elif "trajectory" in key_lower:
                growth["growth_trajectory"] = value

        return growth

    @staticmethod
    def extract_profitability(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract profitability metrics.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Profitability metrics
        """
        profitability = {
            "gross_margin": None,
            "operating_margin": None,
            "net_margin": None,
            "margin_trend": None,
            "roe": None,
            "roa": None
        }

        if not fund_data:
            return profitability

        for key, value in fund_data.items():
            key_lower = key.lower()

            if "gross_margin" in key_lower:
                profitability["gross_margin"] = DeepFundamentalProcessor._safe_float(value)
            elif "operating_margin" in key_lower:
                profitability["operating_margin"] = DeepFundamentalProcessor._safe_float(value)
            elif "net_margin" in key_lower or "net_profit_margin" in key_lower:
                profitability["net_margin"] = DeepFundamentalProcessor._safe_float(value)
            elif "margin_trend" in key_lower:
                profitability["margin_trend"] = value
            elif key_lower == "roe" or "return_on_equity" in key_lower:
                profitability["roe"] = DeepFundamentalProcessor._safe_float(value)
            elif key_lower == "roa" or "return_on_assets" in key_lower:
                profitability["roa"] = DeepFundamentalProcessor._safe_float(value)

        return profitability

    @staticmethod
    def extract_financial_position(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract financial position analysis.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Financial position metrics
        """
        position = {
            "debt_to_equity": None,
            "debt_assessment": None,
            "current_ratio": None,
            "liquidity_assessment": None,
            "cash_to_debt": None
        }

        if not fund_data:
            return position

        for key, value in fund_data.items():
            key_lower = key.lower()

            if "debt_to_equity" in key_lower or "debt-to-equity" in key_lower:
                position["debt_to_equity"] = DeepFundamentalProcessor._safe_float(value)
            elif "debt_assessment" in key_lower:
                position["debt_assessment"] = value
            elif "current_ratio" in key_lower:
                position["current_ratio"] = DeepFundamentalProcessor._safe_float(value)
            elif "liquidity_assessment" in key_lower:
                position["liquidity_assessment"] = value
            elif "cash_to_debt" in key_lower or "cash-to-debt" in key_lower:
                position["cash_to_debt"] = DeepFundamentalProcessor._safe_float(value)

        return position

    @staticmethod
    def extract_valuation(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract valuation metrics.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Valuation metrics
        """
        valuation = {
            "pe_ratio": None,
            "industry_avg_pe": None,
            "peg_ratio": None,
            "pb_ratio": None,
            "ps_ratio": None,
            "valuation_assessment": None
        }

        if not fund_data:
            return valuation

        for key, value in fund_data.items():
            key_lower = key.lower()

            if key_lower in ["pe", "p/e", "pe_ratio", "price_to_earnings"]:
                valuation["pe_ratio"] = DeepFundamentalProcessor._safe_float(value)
            elif "industry" in key_lower and ("pe" in key_lower or "p/e" in key_lower):
                valuation["industry_avg_pe"] = DeepFundamentalProcessor._safe_float(value)
            elif "peg" in key_lower:
                valuation["peg_ratio"] = DeepFundamentalProcessor._safe_float(value)
            elif key_lower in ["pb", "p/b", "pb_ratio", "price_to_book"]:
                valuation["pb_ratio"] = DeepFundamentalProcessor._safe_float(value)
            elif key_lower in ["ps", "p/s", "ps_ratio", "price_to_sales"]:
                valuation["ps_ratio"] = DeepFundamentalProcessor._safe_float(value)
            elif "valuation" in key_lower and "assessment" in key_lower:
                valuation["valuation_assessment"] = value

        return valuation

    @staticmethod
    def extract_sustainability(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract growth sustainability analysis.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Sustainability metrics
        """
        sustainability = {
            "growth_sustainable": None,
            "growth_catalysts": [],
            "industry_tailwinds": [],
            "industry_headwinds": [],
            "competitive_advantage": None
        }

        if not fund_data:
            return sustainability

        for key, value in fund_data.items():
            key_lower = key.lower()

            if "sustainable" in key_lower:
                sustainability["growth_sustainable"] = value
            elif "catalyst" in key_lower:
                if isinstance(value, list):
                    sustainability["growth_catalysts"] = value
                elif isinstance(value, str):
                    sustainability["growth_catalysts"] = [value]
            elif "tailwind" in key_lower:
                if isinstance(value, list):
                    sustainability["industry_tailwinds"] = value
                elif isinstance(value, str):
                    sustainability["industry_tailwinds"] = [value]
            elif "headwind" in key_lower:
                if isinstance(value, list):
                    sustainability["industry_headwinds"] = value
                elif isinstance(value, str):
                    sustainability["industry_headwinds"] = [value]
            elif "competitive_advantage" in key_lower:
                sustainability["competitive_advantage"] = value

        return sustainability

    @staticmethod
    def extract_risks(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract risk assessment.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Risk assessment metrics
        """
        risks = {
            "key_risks": [],
            "execution_risks": None,
            "market_risks": None,
            "regulatory_risks": None
        }

        if not fund_data:
            return risks

        for key, value in fund_data.items():
            key_lower = key.lower()

            if "key_risk" in key_lower:
                if isinstance(value, list):
                    risks["key_risks"] = value
                elif isinstance(value, str):
                    risks["key_risks"] = [value]
            elif "execution_risk" in key_lower:
                risks["execution_risks"] = value
            elif "market_risk" in key_lower:
                risks["market_risks"] = value
            elif "regulatory_risk" in key_lower:
                risks["regulatory_risks"] = value

        return risks

    @staticmethod
    def extract_investment_assessment(fund_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract investment assessment and recommendation.

        Args:
            fund_data: Fundamental data dictionary

        Returns:
            Investment assessment
        """
        assessment = {
            "fundamental_score": None,
            "key_strengths": [],
            "key_concerns": [],
            "fair_value_estimate": None,
            "investment_recommendation": None,
            "recommendation_confidence": None,
            "investment_thesis": None
        }

        if not fund_data:
            return assessment

        for key, value in fund_data.items():
            key_lower = key.lower()

            if "fundamental_score" in key_lower or (key_lower == "score" and value is not None):
                assessment["fundamental_score"] = DeepFundamentalProcessor._safe_int(value)
            elif "strength" in key_lower:
                if isinstance(value, list):
                    assessment["key_strengths"] = value
                elif isinstance(value, str):
                    assessment["key_strengths"] = [value]
            elif "concern" in key_lower or "red_flag" in key_lower:
                if isinstance(value, list):
                    assessment["key_concerns"] = value
                elif isinstance(value, str):
                    assessment["key_concerns"] = [value]
            elif "fair_value" in key_lower:
                assessment["fair_value_estimate"] = DeepFundamentalProcessor._safe_float(value)
            elif "recommendation" in key_lower:
                assessment["investment_recommendation"] = value
            elif "confidence" in key_lower:
                assessment["recommendation_confidence"] = DeepFundamentalProcessor._safe_int(value)
            elif "thesis" in key_lower:
                assessment["investment_thesis"] = value

        return assessment

    @staticmethod
    def calculate_comprehensive_score(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate comprehensive fundamental score.

        Args:
            fundamentals: Parsed fundamental data

        Returns:
            Score calculation with breakdown
        """
        score = {
            "total_score": 0,
            "growth_score": 0,
            "profitability_score": 0,
            "valuation_score": 0,
            "health_score": 0
        }

        try:
            growth = fundamentals.get("growth_analysis", {})
            revenue_growth = growth.get("revenue_growth_yoy") or 0
            earnings_growth = growth.get("earnings_growth_yoy") or 0

            if revenue_growth > 20 and earnings_growth > 20:
                score["growth_score"] = 25
            elif revenue_growth > 10 and earnings_growth > 10:
                score["growth_score"] = 18
            elif revenue_growth > 5 and earnings_growth > 5:
                score["growth_score"] = 12

            prof = fundamentals.get("profitability", {})
            net_margin = prof.get("net_margin") or 0
            roe = prof.get("roe") or 0

            if net_margin > 15 and roe > 15:
                score["profitability_score"] = 25
            elif net_margin > 10 and roe > 10:
                score["profitability_score"] = 15
            elif net_margin > 5 and roe > 5:
                score["profitability_score"] = 10

            val = fundamentals.get("valuation", {})
            valuation_assessment = str(val.get("valuation_assessment", "")).lower()

            if "cheap" in valuation_assessment or "undervalued" in valuation_assessment:
                score["valuation_score"] = 25
            elif "fair" in valuation_assessment:
                score["valuation_score"] = 15
            elif "expensive" in valuation_assessment:
                score["valuation_score"] = 5

            pos = fundamentals.get("financial_position", {})
            debt_to_equity = pos.get("debt_to_equity") or 10
            current_ratio = pos.get("current_ratio") or 0

            if debt_to_equity < 0.5 and current_ratio > 2:
                score["health_score"] = 25
            elif debt_to_equity < 1.5 and current_ratio > 1.5:
                score["health_score"] = 15
            elif debt_to_equity < 2.5 and current_ratio > 1:
                score["health_score"] = 10

            score["total_score"] = min(
                score["growth_score"] + score["profitability_score"] +
                score["valuation_score"] + score["health_score"],
                100
            )

        except Exception as e:
            logger.error(f"Error calculating fundamental score: {e}")

        return score

    @staticmethod
    def _safe_float(value: Any) -> Optional[float]:
        """Safely convert value to float.

        Args:
            value: Value to convert

        Returns:
            Float value or None if conversion fails
        """
        if value is None or value == "TBD":
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        """Safely convert value to int.

        Args:
            value: Value to convert

        Returns:
            Int value or None if conversion fails
        """
        if value is None or value == "TBD":
            return None
        try:
            return int(float(value))
        except (ValueError, TypeError):
            return None
