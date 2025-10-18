"""
News data processing and analysis.

Handles news fetching, sentiment analysis, and relevance scoring.
"""

import re
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from loguru import logger


class NewsProcessor:
    """Processes news data from various sources."""

    @staticmethod
    def calculate_news_relevance(
        news_content: str,
        earnings_content: str,
        focus_significant: bool = False
    ) -> float:
        """Calculate relevance score for news content.

        Args:
            news_content: News text to score
            earnings_content: Related earnings content
            focus_significant: Weight towards significant events

        Returns:
            Relevance score from 0.0 to 1.0
        """
        if not news_content and not earnings_content:
            return 0.0

        content = (news_content + " " + earnings_content).lower()
        score = 0.5

        high_relevance_keywords = [
            'earnings', 'profit', 'revenue', 'eps', 'guidance', 'forecast',
            'merger', 'acquisition', 'dividend', 'split', 'buyback',
            'lawsuit', 'regulation', 'fda', 'approval', 'launch',
            'bankruptcy', 'restructure', 'layoff', 'strike'
        ]

        medium_relevance_keywords = [
            'announcement', 'update', 'report', 'results', 'quarter',
            'year', 'growth', 'decline', 'increase', 'decrease'
        ]

        high_matches = sum(1 for keyword in high_relevance_keywords if keyword in content)
        medium_matches = sum(1 for keyword in medium_relevance_keywords if keyword in content)

        score += high_matches * 0.2
        score += medium_matches * 0.1

        if earnings_content and len(earnings_content.strip()) > 50:
            score += 0.3

        total_length = len(news_content) + len(earnings_content)
        if total_length > 200:
            score += 0.1

        return min(score, 1.0)

    @staticmethod
    def extract_news_for_symbol(content: str, symbol: str) -> str:
        """Extract news content related to a specific symbol.

        Args:
            content: Full content text
            symbol: Stock symbol to extract for

        Returns:
            Extracted news content for symbol
        """
        return content.strip()

    @staticmethod
    def extract_earnings_for_symbol(content: str, symbol: str) -> str:
        """Extract earnings content related to a specific symbol.

        Args:
            content: Full content text
            symbol: Stock symbol to extract for

        Returns:
            Extracted earnings content or empty string
        """
        earnings_keywords = [
            'earnings', 'profit', 'revenue', 'eps', 'quarter',
            'results', 'q1', 'q2', 'q3', 'q4', 'fy'
        ]
        content_lower = content.lower()

        if any(keyword in content_lower for keyword in earnings_keywords):
            return content.strip()

        return ""

    @staticmethod
    def extract_next_earnings_date(content: str, symbol: str) -> Optional[str]:
        """Extract next earnings date from content.

        Args:
            content: Content to search for dates
            symbol: Stock symbol

        Returns:
            Earnings date string or None
        """
        date_patterns = [
            r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}',
            r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2},?\s+\d{4}'
        ]

        for pattern in date_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1)

        return None

    @staticmethod
    def analyze_sentiment(content: str, symbol: str = "") -> str:
        """Analyze sentiment from content.

        Args:
            content: Content to analyze
            symbol: Optional stock symbol for context

        Returns:
            Sentiment ('positive', 'negative', or 'neutral')
        """
        content_lower = content.lower()

        positive_words = [
            'rise', 'increase', 'gain', 'beat', 'surprise', 'positive',
            'strong', 'growth', 'up', 'higher', 'improved', 'excellent',
            'outperform', 'bullish', 'upgrade'
        ]

        negative_words = [
            'fall', 'decrease', 'loss', 'miss', 'decline', 'negative',
            'weak', 'down', 'lower', 'worse', 'drop', 'poor',
            'underperform', 'bearish', 'downgrade'
        ]

        positive_count = sum(1 for word in positive_words if word in content_lower)
        negative_count = sum(1 for word in negative_words if word in content_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    @staticmethod
    def detect_duplicate_news(
        news_content: str,
        existing_news_list: list,
        similarity_threshold: float = 0.8
    ) -> bool:
        """Detect if news content is a duplicate.

        Args:
            news_content: News content to check
            existing_news_list: List of existing news items
            similarity_threshold: Similarity threshold for duplicates

        Returns:
            True if duplicate detected, False otherwise
        """
        if not news_content or len(news_content.strip()) < 20:
            return False

        try:
            news_lower = news_content.lower().strip()

            for existing in existing_news_list:
                existing_content = existing.get('content', '').lower().strip()
                existing_title = existing.get('title', '').lower().strip()

                if (news_lower == existing_content or
                    news_lower == existing_title or
                    existing_content in news_lower or
                    existing_title in news_lower):
                    return True

                news_words = set(news_lower.split())
                existing_words = set(existing_content.split())

                if news_words and existing_words:
                    intersection = news_words.intersection(existing_words)
                    union = news_words.union(existing_words)
                    similarity = len(intersection) / len(union) if union else 0

                    if similarity > similarity_threshold:
                        return True

            return False

        except Exception as e:
            logger.error(f"Error detecting news duplicate: {e}")
            return False

    @staticmethod
    def detect_duplicate_earnings(
        earnings_content: str,
        existing_earnings_list: list,
        hours_window: int = 24
    ) -> bool:
        """Detect if earnings content is a duplicate.

        Args:
            earnings_content: Earnings content to check
            existing_earnings_list: List of existing earnings items
            hours_window: Time window in hours to check for recent duplicates

        Returns:
            True if duplicate detected, False otherwise
        """
        if not earnings_content or len(earnings_content.strip()) < 20:
            return False

        try:
            earnings_lower = earnings_content.lower().strip()

            for existing in existing_earnings_list:
                existing_guidance = existing.get('guidance', '').lower().strip()

                if existing_guidance and (
                    earnings_lower == existing_guidance or
                    existing_guidance in earnings_lower
                ):
                    created_at = existing.get('created_at', '')
                    if created_at:
                        try:
                            created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                            time_diff = (datetime.now(timezone.utc) - created_dt).total_seconds()
                            if time_diff < (hours_window * 3600):
                                return True
                        except ValueError:
                            pass

            return False

        except Exception as e:
            logger.error(f"Error detecting earnings duplicate: {e}")
            return False

    @staticmethod
    def extract_symbols_from_content(content: str) -> list:
        """Extract stock symbols from content.

        Args:
            content: Content to search for symbols

        Returns:
            List of stock symbols found
        """
        symbol_pattern = r'\b[A-Z]{1,5}\b'
        matches = re.findall(symbol_pattern, content)
        return list(set(matches))

    @staticmethod
    def categorize_news(content: str) -> str:
        """Categorize news by type.

        Args:
            content: News content to categorize

        Returns:
            Category ('earnings', 'market_news', 'company_news', or 'other')
        """
        content_lower = content.lower()

        if any(word in content_lower for word in ['earnings', 'eps', 'revenue', 'guidance']):
            return "earnings"
        elif any(word in content_lower for word in ['market', 'dow', 'sp500', 'nasdaq', 'fed', 'interest rate']):
            return "market_news"
        elif any(word in content_lower for word in ['merger', 'acquisition', 'announcement', 'launch', 'product']):
            return "company_news"
        else:
            return "other"
