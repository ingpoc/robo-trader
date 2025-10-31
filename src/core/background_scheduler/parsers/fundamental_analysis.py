"""
Fundamental analysis data parsing and processing.

Handles fundamental data parsing, analysis, and valuation metrics.
"""

import re
from datetime import datetime
from typing import Dict, List, Any, Optional
import json
from loguru import logger


def parse_fundamentals(response_text: str) -> Dict[str, Any]:
    """Parse fundamental analysis data from API response.

    Args:
        response_text: Raw response from fundamentals API

    Returns:
        Dictionary with fundamental data
    """
    if not response_text or not isinstance(response_text, str):
        logger.warning("Empty or invalid fundamental data")
        return {}

    try:
        # Try to parse as JSON first
        data = json.loads(response_text)

        if isinstance(data, dict):
            return _standardize_fundamental_data(data)

    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode error parsing fundamentals: {e}")
        # Fall back to text parsing
        return _parse_text_fundamentals(response_text)

    except Exception as e:
        logger.error(f"Error parsing fundamentals: {e}")
        return {}


def parse_deep_fundamentals(response_text: str) -> Dict[str, Any]:
    """Parse deep fundamental analysis data from API response.

    Args:
        response_text: Raw response from deep fundamentals API

    Returns:
        Dictionary with deep fundamental analysis
    """
    if not response_text or not isinstance(response_text, str):
        logger.warning("Empty or invalid deep fundamental data")
        return {}

    try:
        # Try to parse as JSON first
        data = json.loads(response_text)

        if isinstance(data, dict):
            return _standardize_deep_fundamental_data(data)

    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode error parsing deep fundamentals: {e}")
        # Fall back to text parsing
        return _parse_text_deep_fundamentals(response_text)

    except Exception as e:
        logger.error(f"Error parsing deep fundamentals: {e}")
        return {}


def _standardize_fundamental_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize fundamental data to common format.

    Args:
        data: Raw fundamental data dictionary

    Returns:
        Standardized fundamental data
    """
    standardized = {}

    # Financial metrics
    standardized["revenue"] = data.get("revenue", data.get("total_revenue"))
    standardized["net_income"] = data.get("net_income", data.get("profit"))
    standardized["eps"] = data.get("eps", data.get("earnings_per_share"))
    standardized["pe_ratio"] = data.get("pe_ratio", data.get("price_to_earnings"))
    standardized["pb_ratio"] = data.get("pb_ratio", data.get("price_to_book"))
    standardized["debt_to_equity"] = data.get("debt_to_equity", data.get("leverage"))
    standardized["roe"] = data.get("roe", data.get("return_on_equity"))
    standardized["roa"] = data.get("roa", data.get("return_on_assets"))

    # Growth metrics
    standardized["revenue_growth"] = data.get("revenue_growth", data.get("revenue_growth_rate"))
    standardized["earnings_growth"] = data.get("earnings_growth", data.get("eps_growth"))

    # Valuation
    standardized["fair_value"] = data.get("fair_value", data.get("intrinsic_value"))
    standardized["margin_of_safety"] = data.get("margin_of_safety")

    # Analysis
    standardized["strengths"] = data.get("strengths", [])
    standardized["weaknesses"] = data.get("weaknesses", [])
    standardized["opportunities"] = data.get("opportunities", [])
    standardized["threats"] = data.get("threats", [])
    standardized["recommendation"] = data.get("recommendation", data.get("rating"))

    return standardized


def _standardize_deep_fundamental_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize deep fundamental analysis data.

    Args:
        data: Raw deep fundamental data dictionary

    Returns:
        Standardized deep fundamental data
    """
    standardized = _standardize_fundamental_data(data)

    # Add deep analysis specific fields
    standardized["industry_analysis"] = data.get("industry_analysis", {})
    standardized["competitive_position"] = data.get("competitive_position", {})
    standardized["management_quality"] = data.get("management_quality", {})
    standardized["risk_factors"] = data.get("risk_factors", [])
    standardized["future_prospects"] = data.get("future_prospects", {})
    standardized["valuation_models"] = data.get("valuation_models", {})

    # DCF specific
    standardized["dcf_valuation"] = data.get("dcf_valuation", {})
    standardized["sensitivity_analysis"] = data.get("sensitivity_analysis", {})

    return standardized


def _parse_text_fundamentals(text: str) -> Dict[str, Any]:
    """Parse fundamental data from plain text.

    Args:
        text: Plain text containing fundamental information

    Returns:
        Dictionary with fundamental data
    """
    data = {}

    # Extract numerical values with labels
    patterns = {
        "revenue": r"revenue[:\s]*\$?([\d,]+\.?\d*)\s*(million|billion|M|B)?",
        "net_income": r"net income[:\s]*\$?([\d,]+\.?\d*)\s*(million|billion|M|B)?",
        "eps": r"EPS[:\s]*\$?([\d,]+\.?\d*)",
        "pe_ratio": r"P/E[:\s]*([\d,]+\.?\d*)",
        "pb_ratio": r"P/B[:\s]*([\d,]+\.?\d*)",
        "debt_to_equity": r"debt.*equity[:\s]*([\d,]+\.?\d*)",
        "roe": r"ROE[:\s]*([\d,]+\.?\d*)%",
        "roa": r"ROA[:\s]*([\d,]+\.?\d*)%"
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value_str = match.group(1).replace(',', '')
            try:
                value = float(value_str)
                # Apply multiplier for millions/billions
                if key in ["revenue", "net_income"] and len(match.groups()) > 1:
                    unit = match.group(2)
                    if unit and unit.lower() in ['billion', 'b']:
                        value *= 1000
                data[key] = value
            except ValueError:
                pass

    # Extract growth rates
    growth_patterns = {
        "revenue_growth": r"revenue growth[:\s]*([+-]?[\d,]+\.?\d*)%",
        "earnings_growth": r"earnings growth[:\s]*([+-]?[\d,]+\.?\d*)%"
    }

    for key, pattern in growth_patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                data[key] = float(match.group(1).replace(',', ''))
            except ValueError:
                pass

    return data


def _parse_text_deep_fundamentals(text: str) -> Dict[str, Any]:
    """Parse deep fundamental analysis from plain text.

    Args:
        text: Plain text containing deep fundamental analysis

    Returns:
        Dictionary with deep fundamental data
    """
    data = _parse_text_fundamentals(text)

    # Add deep analysis specific parsing
    sections = {
        "strengths": r"strengths?:?\s*(.*?)(?:\n\n|\n\w)",
        "weaknesses": r"weaknesses?:?\s*(.*?)(?:\n\n|\n\w)",
        "opportunities": r"opportunities?:?\s*(.*?)(?:\n\n|\n\w)",
        "threats": r"threats?:?\s*(.*?)(?:\n\n|\n\w)"
    }

    for key, pattern in sections.items():
        match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
        if match:
            section_text = match.group(1).strip()
            # Split by bullet points or numbers
            items = re.split(r'\n\s*(?:\d+\.|\•|-)\s*', section_text)
            items = [item.strip() for item in items if item.strip()]
            if items:
                data[key] = items

    # Extract recommendation
    rec_match = re.search(r'recommendation[:\s]*(.*?)(?:\n|$)', text, re.IGNORECASE)
    if rec_match:
        data["recommendation"] = rec_match.group(1).strip()

    return data


def calculate_fair_value(fundamentals: Dict[str, Any]) -> Optional[float]:
    """Calculate fair value using simple multiples approach.

    Args:
        fundamentals: Fundamental data dictionary

    Returns:
        Fair value estimate or None if insufficient data
    """
    try:
        eps = fundamentals.get("eps")
        pe_ratio = fundamentals.get("pe_ratio")

        if eps and pe_ratio:
            # Simple valuation: EPS * industry average P/E
            # This is a simplified approach
            industry_avg_pe = 15.0  # Conservative estimate
            return eps * industry_avg_pe
    except Exception as e:
        logger.debug(f"Could not calculate fair value: {e}")

    return None


def assess_investment_quality(fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    """Assess overall investment quality based on fundamentals.

    Args:
        fundamentals: Fundamental data dictionary

    Returns:
        Dictionary with quality assessment
    """
    assessment = {
        "overall_rating": "neutral",
        "scores": {},
        "recommendation": "hold"
    }

    # Profitability score
    roe = fundamentals.get("roe")
    roa = fundamentals.get("roa")
    profitability_score = 0

    if roe and roe > 15:
        profitability_score += 1
    if roa and roa > 5:
        profitability_score += 1

    assessment["scores"]["profitability"] = profitability_score

    # Valuation score
    pe_ratio = fundamentals.get("pe_ratio")
    pb_ratio = fundamentals.get("pb_ratio")
    valuation_score = 0

    if pe_ratio and pe_ratio < 20:
        valuation_score += 1
    if pb_ratio and pb_ratio < 3:
        valuation_score += 1

    assessment["scores"]["valuation"] = valuation_score

    # Overall rating based on scores
    total_score = sum(assessment["scores"].values())
    if total_score >= 3:
        assessment["overall_rating"] = "attractive"
        assessment["recommendation"] = "buy"
    elif total_score <= 1:
        assessment["overall_rating"] = "expensive"
        assessment["recommendation"] = "avoid"

    return assessment

