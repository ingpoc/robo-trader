"""
Fundamental analysis processor.

Handles fundamental data analysis and interpretation.
"""

from typing import Dict, List, Any, Optional

from loguru import logger


class FundamentalAnalyzer:
    """Analyzes fundamental financial data."""

    @staticmethod
    def calculate_valuation_metrics(financial_data: Dict[str, Any]) -> Dict[str, float]:
        """Calculate key valuation metrics from financial data.

        Args:
            financial_data: Dictionary with financial data

        Returns:
            Dictionary of calculated metrics
        """
        metrics = {}

        try:
            earnings = financial_data.get('earnings', 0)
            revenue = financial_data.get('revenue', 0)
            market_cap = financial_data.get('market_cap', 0)
            book_value = financial_data.get('book_value', 0)

            if market_cap and earnings:
                metrics['pe_ratio'] = market_cap / earnings
            if market_cap and revenue:
                metrics['ps_ratio'] = market_cap / revenue
            if market_cap and book_value:
                metrics['pb_ratio'] = market_cap / book_value

        except Exception as e:
            logger.error(f"Error calculating valuation metrics: {e}")

        return metrics

    @staticmethod
    def analyze_profitability(financial_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze profitability metrics.

        Args:
            financial_data: Dictionary with financial data

        Returns:
            Dictionary with profitability assessment
        """
        assessment = {
            "net_profit_margin": "unknown",
            "operating_margin": "unknown",
            "roe": "unknown",
            "roa": "unknown"
        }

        try:
            net_income = financial_data.get('net_income', 0)
            revenue = financial_data.get('revenue', 1)
            operating_income = financial_data.get('operating_income', 0)
            equity = financial_data.get('equity', 1)
            assets = financial_data.get('assets', 1)

            if revenue:
                npm = (net_income / revenue) * 100
                assessment['net_profit_margin'] = "strong" if npm > 15 else "moderate" if npm > 5 else "weak"

                opm = (operating_income / revenue) * 100
                assessment['operating_margin'] = "strong" if opm > 15 else "moderate" if opm > 5 else "weak"

            if equity:
                roe = (net_income / equity) * 100
                assessment['roe'] = "strong" if roe > 15 else "moderate" if roe > 5 else "weak"

            if assets:
                roa = (net_income / assets) * 100
                assessment['roa'] = "strong" if roa > 5 else "moderate" if roa > 2 else "weak"

        except Exception as e:
            logger.error(f"Error analyzing profitability: {e}")

        return assessment

    @staticmethod
    def analyze_growth(
        current_data: Dict[str, Any],
        previous_data: Dict[str, Any]
    ) -> Dict[str, float]:
        """Analyze year-over-year growth metrics.

        Args:
            current_data: Current period financial data
            previous_data: Previous period financial data

        Returns:
            Dictionary with growth rates
        """
        growth = {}

        try:
            current_revenue = current_data.get('revenue', 0)
            previous_revenue = previous_data.get('revenue', 1)
            growth['revenue_growth'] = ((current_revenue - previous_revenue) / previous_revenue * 100) if previous_revenue else 0

            current_earnings = current_data.get('earnings', 0)
            previous_earnings = previous_data.get('earnings', 1)
            growth['earnings_growth'] = ((current_earnings - previous_earnings) / previous_earnings * 100) if previous_earnings else 0

            current_margin = current_data.get('profit_margin', 0)
            previous_margin = previous_data.get('profit_margin', 0)
            growth['margin_expansion'] = current_margin - previous_margin

        except Exception as e:
            logger.error(f"Error analyzing growth: {e}")

        return growth

    @staticmethod
    def analyze_financial_health(financial_data: Dict[str, Any]) -> Dict[str, str]:
        """Analyze overall financial health.

        Args:
            financial_data: Dictionary with financial data

        Returns:
            Dictionary with health assessment
        """
        assessment = {
            "liquidity": "unknown",
            "solvency": "unknown",
            "debt_level": "unknown",
            "cash_position": "unknown"
        }

        try:
            current_assets = financial_data.get('current_assets', 0)
            current_liabilities = financial_data.get('current_liabilities', 1)
            total_debt = financial_data.get('total_debt', 0)
            total_equity = financial_data.get('total_equity', 1)
            cash = financial_data.get('cash', 0)
            revenue = financial_data.get('revenue', 1)

            if current_liabilities:
                current_ratio = current_assets / current_liabilities
                assessment['liquidity'] = "strong" if current_ratio > 2 else "moderate" if current_ratio > 1 else "weak"

            if total_equity:
                debt_to_equity = total_debt / total_equity
                assessment['solvency'] = "strong" if debt_to_equity < 0.5 else "moderate" if debt_to_equity < 2 else "weak"

            if revenue:
                debt_to_revenue = total_debt / revenue
                assessment['debt_level'] = "low" if debt_to_revenue < 1 else "moderate" if debt_to_revenue < 3 else "high"

                cash_to_revenue = cash / revenue
                assessment['cash_position'] = "strong" if cash_to_revenue > 0.2 else "moderate" if cash_to_revenue > 0.05 else "weak"

        except Exception as e:
            logger.error(f"Error analyzing financial health: {e}")

        return assessment

    @staticmethod
    def generate_overall_assessment(financial_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate overall fundamental assessment.

        Args:
            financial_data: Complete financial data

        Returns:
            Overall assessment with recommendations
        """
        assessment = {
            "overall_score": 0,
            "valuation": "unknown",
            "profitability": "unknown",
            "growth": "unknown",
            "health": "unknown",
            "recommendation": "neutral"
        }

        try:
            valuation_metrics = FundamentalAnalyzer.calculate_valuation_metrics(financial_data)
            profitability = FundamentalAnalyzer.analyze_profitability(financial_data)
            health = FundamentalAnalyzer.analyze_financial_health(financial_data)

            score = 0

            if valuation_metrics.get('pe_ratio', 100) < 20:
                score += 25
                assessment['valuation'] = "attractive"
            else:
                assessment['valuation'] = "expensive"

            strong_profitability = sum(1 for v in profitability.values() if v == "strong")
            if strong_profitability >= 2:
                score += 25
                assessment['profitability'] = "strong"
            else:
                assessment['profitability'] = "moderate"

            revenue_growth = financial_data.get('revenue_growth', 0)
            if revenue_growth > 10:
                score += 25
                assessment['growth'] = "strong"
            else:
                assessment['growth'] = "moderate"

            strong_health = sum(1 for v in health.values() if v == "strong")
            if strong_health >= 2:
                score += 25
                assessment['health'] = "strong"
            else:
                assessment['health'] = "moderate"

            assessment['overall_score'] = score

            if score >= 75:
                assessment['recommendation'] = "strong_buy"
            elif score >= 60:
                assessment['recommendation'] = "buy"
            elif score >= 40:
                assessment['recommendation'] = "hold"
            else:
                assessment['recommendation'] = "sell"

        except Exception as e:
            logger.error(f"Error generating overall assessment: {e}")

        return assessment
