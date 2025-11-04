"""
News data parsing and processing.

Handles news data fetching, parsing (3 strategies), and categorization.
"""

import re
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import json
from loguru import logger


def parse_categorized_news(response_text: str) -> Dict[str, Any]:
    """Parse categorized news data from API response.

    Args:
        response_text: Raw response from news API

    Returns:
        Dictionary with articles array containing news items
    """
    if not response_text or not isinstance(response_text, str):
        logger.warning("Empty or invalid news data")
        return {"articles": []}

    try:
        # Try to parse as JSON first
        data = json.loads(response_text)

        if isinstance(data, dict):
            # If data has articles key, use it directly
            if "articles" in data:
                articles = data["articles"]
            elif "news" in data:
                articles = data["news"]
            else:
                # Try to extract articles from other keys
                articles = []
                for key, value in data.items():
                    if isinstance(value, list) and len(value) > 0:
                        articles = value
                        break

            # Ensure articles is a list
            if not isinstance(articles, list):
                articles = [articles] if articles else []

            # Standardize article format
            standardized_articles = []
            for article in articles:
                if isinstance(article, dict):
                    standardized_articles.append(_standardize_news_article(article))
                else:
                    # Try to parse string articles
                    standardized_articles.append(_parse_string_article(str(article)))

            return {"articles": standardized_articles}

    except json.JSONDecodeError as e:
        logger.debug(f"JSON decode error parsing news: {e}")
        # Fall back to text parsing
        return _parse_text_news(response_text)

    except Exception as e:
        logger.error(f"Error parsing categorized news: {e}")
        return {"articles": []}


def _standardize_news_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """Standardize a news article to common format.

    Args:
        article: Raw article dictionary

    Returns:
        Standardized article dictionary
    """
    return {
        "symbol": article.get("symbol", article.get("ticker", "")),
        "headline": article.get("headline", article.get("title", "")),
        "content": article.get("content", article.get("summary", article.get("description", ""))),
        "source": article.get("source", article.get("publisher", "Unknown")),
        "article_type": article.get("article_type", article.get("type", "news")),
        "category": article.get("category", "general"),
        "sentiment": article.get("sentiment", "neutral"),
        "impact_score": article.get("impact_score", article.get("score", 0.5)),
        "relevance_score": article.get("relevance_score", 0.5),
        "key_points": article.get("key_points", article.get("points", [])),
        "url": article.get("url", article.get("link", "")),
        "published_at": article.get("published_at", article.get("date", ""))
    }


def _parse_string_article(article_text: str) -> Dict[str, Any]:
    """Parse a string representation of an article.

    Args:
        article_text: String containing article information

    Returns:
        Standardized article dictionary
    """
    # Try to extract headline and content
    lines = article_text.strip().split('\n', 1)
    headline = lines[0].strip() if lines else ""
    content = lines[1].strip() if len(lines) > 1 else headline

    return {
        "symbol": "",
        "headline": headline,
        "content": content,
        "source": "Unknown",
        "article_type": "news",
        "category": "general",
        "sentiment": "neutral",
        "impact_score": 0.5,
        "relevance_score": 0.5,
        "key_points": [],
        "url": "",
        "published_at": ""
    }


def _parse_text_news(text: str) -> Dict[str, Any]:
    """Parse news from plain text response.

    Args:
        text: Plain text containing news information

    Returns:
        Dictionary with articles array
    """
    articles = []

    # Split by common delimiters
    sections = re.split(r'\n\s*(?=\d+\.|•|-)', text)

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # Try to extract headline and content
        lines = section.split('\n', 1)
        headline = lines[0].strip() if lines else ""
        content = lines[1].strip() if len(lines) > 1 else ""

        if headline:
            articles.append({
                "symbol": "",
                "headline": headline,
                "content": content,
                "source": "Perplexity",
                "article_type": "news",
                "category": "general",
                "sentiment": "neutral",
                "impact_score": 0.5,
                "relevance_score": 0.5,
                "key_points": [],
                "url": "",
                "published_at": ""
            })

    return {"articles": articles}


def categorize_news_by_impact(articles: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """Categorize news articles by impact level.

    Args:
        articles: List of news articles

    Returns:
        Dictionary with high, medium, low impact articles
    """
    categorized = {
        "high_impact": [],
        "medium_impact": [],
        "low_impact": []
    }

    for article in articles:
        impact_score = article.get("impact_score", 0.5)

        if impact_score >= 0.8:
            categorized["high_impact"].append(article)
        elif impact_score >= 0.6:
            categorized["medium_impact"].append(article)
        else:
            categorized["low_impact"].append(article)

    return categorized


def filter_news_by_sentiment(articles: List[Dict[str, Any]], sentiment_filter: str) -> List[Dict[str, Any]]:
    """Filter news articles by sentiment.

    Args:
        articles: List of news articles
        sentiment_filter: Sentiment to filter by ('positive', 'negative', 'neutral')

    Returns:
        Filtered list of articles
    """
    return [
        article for article in articles
        if article.get("sentiment", "neutral").lower() == sentiment_filter.lower()
    ]

