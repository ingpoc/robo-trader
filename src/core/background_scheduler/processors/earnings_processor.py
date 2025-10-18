"""
Earnings data processing and analysis.

Handles earnings data fetching, parsing (3 strategies), and analysis.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

from loguru import logger


class EarningsProcessor:
    """Processes earnings data from various sources."""

    @staticmethod
    def parse_earnings_data(earnings_text: str) -> Dict[str, Any]:
        """Parse earnings data with multiple fallback strategies.

        Args:
            earnings_text: Raw earnings text from API

        Returns:
            Parsed earnings data dictionary
        """
        if not earnings_text or not isinstance(earnings_text, str):
            return {}

        try:
            return EarningsProcessor._parse_structured_earnings(earnings_text)
        except Exception as e:
            logger.debug(f"Structured parsing failed: {e}")

        try:
            return EarningsProcessor._parse_regex_earnings(earnings_text)
        except Exception as e:
            logger.debug(f"Regex parsing failed: {e}")

        try:
            return EarningsProcessor._basic_earnings_extraction(earnings_text)
        except Exception as e:
            logger.debug(f"Basic extraction failed: {e}")

        return {}

    @staticmethod
    def _parse_structured_earnings(text: str) -> Dict[str, Any]:
        """Parse earnings data assuming structured format.

        Args:
            text: Earnings text to parse

        Returns:
            Structured earnings data
        """
        result = {}

        fiscal_patterns = [
            r'(Q[1-4]\s+\d{4})',
            r'(FY\d{4}\s+Q[1-4])',
            r'(\d{4}\s+Q[1-4])'
        ]

        for pattern in fiscal_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['fiscal_period'] = match.group(1)
                break

        eps_patterns = [
            r'EPS[:\s]+[\$]?(\d+\.?\d*)\s*(?:\((?:est|estimated)[:\s]+[\$]?(\d+\.?\d*))?',
            r'earnings per share[:\s]+[\$]?(\d+\.?\d*)',
            r'EPS of[\s]+[\$]?(\d+\.?\d*)'
        ]

        for pattern in eps_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['eps_actual'] = float(match.group(1))
                if len(match.groups()) > 1 and match.group(2):
                    result['eps_estimated'] = float(match.group(2))
                break

        revenue_patterns = [
            r'Revenue[:\s]+[\$]?(\d+(?:\.\d+)?)\s*(million|billion|M|B)',
            r'revenue of[\s]+[\$]?(\d+(?:\.\d+)?)\s*(million|billion|M|B)',
            r'sales[:\s]+[\$]?(\d+(?:\.\d+)?)\s*(million|billion|M|B)'
        ]

        for pattern in revenue_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                revenue_val = float(match.group(1))
                unit = match.group(2).lower()
                multiplier = 1000000 if unit in ['million', 'm'] else 1000000000
                result['revenue_actual'] = revenue_val * multiplier
                break

        surprise_patterns = [
            r'surprise[:\s]+([+-]?\d+\.?\d*)%',
            r'beat.*by[:\s]+([+-]?\d+\.?\d*)%',
            r'missed.*by[:\s]+([+-]?\d+\.?\d*)%'
        ]

        for pattern in surprise_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result['surprise_pct'] = float(match.group(1))
                break

        guidance_indicators = ['guidance', 'outlook', 'expects', 'forecast', 'projects']
        for indicator in guidance_indicators:
            if indicator in text.lower():
                sentences = text.split('.')
                for sentence in sentences:
                    if indicator in sentence.lower():
                        result['guidance'] = sentence.strip()
                        break
                break

        return result

    @staticmethod
    def _parse_regex_earnings(text: str) -> Dict[str, Any]:
        """Fallback regex parsing for earnings data.

        Args:
            text: Earnings text to parse

        Returns:
            Parsed earnings data
        """
        result = {}

        eps_match = re.search(r'(\d+\.?\d*)\s*EPS', text, re.IGNORECASE)
        if eps_match:
            result['eps_actual'] = float(eps_match.group(1))

        revenue_match = re.search(r'(\d+(?:\.\d+)?)\s*(M|B)', text, re.IGNORECASE)
        if revenue_match:
            val = float(revenue_match.group(1))
            multiplier = 1000000 if revenue_match.group(2).upper() == 'M' else 1000000000
            result['revenue_actual'] = val * multiplier

        return result

    @staticmethod
    def _basic_earnings_extraction(text: str) -> Dict[str, Any]:
        """Basic extraction as final fallback.

        Args:
            text: Earnings text to parse

        Returns:
            Extracted earnings data
        """
        result = {}

        dollar_matches = re.findall(r'\$([0-9,]+\.?\d*)', text)
        if dollar_matches:
            if len(dollar_matches) >= 1:
                eps_str = dollar_matches[0].replace(',', '')
                try:
                    result['eps_actual'] = float(eps_str)
                except ValueError:
                    pass

        result['guidance'] = text[:500]

        return result

    @staticmethod
    def extract_next_earnings_date(content: str, symbol: str) -> Optional[str]:
        """Extract next earnings date from content.

        Args:
            content: Content containing earnings date
            symbol: Stock symbol

        Returns:
            Earnings date string or None
        """
        date_patterns = [
            r'(\d{1,2}/\d{1,2}/\d{4})',
            r'(\d{4}-\d{1,2}-\d{1,2})',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),?\s+(\d{4})'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(0)

        return None

    @staticmethod
    def calculate_business_day(start_date: datetime, days_ahead: int) -> datetime:
        """Calculate the nth business day after a given date.

        Args:
            start_date: Starting date
            days_ahead: Number of business days to add

        Returns:
            Date after adding business days
        """
        current_date = start_date
        business_days_added = 0

        while business_days_added < days_ahead:
            current_date += timedelta(days=1)
            if current_date.weekday() < 5:
                business_days_added += 1

        return current_date

    @staticmethod
    def analyze_earnings_impact(earnings_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze earnings impact based on parsed data.

        Args:
            earnings_data: Parsed earnings dictionary

        Returns:
            Impact analysis
        """
        impact = {
            "eps_surprise": None,
            "revenue_surprise": None,
            "guidance_sentiment": None,
            "overall_impact": "neutral"
        }

        if "surprise_pct" in earnings_data:
            pct = earnings_data["surprise_pct"]
            if pct > 5:
                impact["overall_impact"] = "positive"
            elif pct < -5:
                impact["overall_impact"] = "negative"
            impact["eps_surprise"] = pct

        if "guidance" in earnings_data:
            guidance = earnings_data["guidance"].lower()
            if any(word in guidance for word in ["beat", "exceed", "strong", "growth"]):
                impact["guidance_sentiment"] = "positive"
            elif any(word in guidance for word in ["miss", "below", "weak", "decline"]):
                impact["guidance_sentiment"] = "negative"

        return impact
