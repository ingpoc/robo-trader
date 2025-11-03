# Background Scheduler Parsers Directory Guidelines

> **Scope**: Applies to `src/core/background_scheduler/parsers/` directory. Read `src/core/background_scheduler/CLAUDE.md` for context.
> **Last Updated**: 2025-11-04 | **Status**: Active | **Tier**: Reference

## Purpose

The `parsers/` directory contains data parsing functions that transform raw API responses into structured, normalized data formats. Parsers handle multiple parsing strategies and data format variations.

## Architecture Pattern

### Multi-Strategy Parsing Pattern

Parsers implement multiple parsing strategies to handle different API response formats and data structures. They normalize data to a consistent internal format.

### Directory Structure

```
parsers/
├── news.py                    # News data parsing
├── earnings.py                # Earnings data parsing
└── fundamental_analysis.py   # Fundamental analysis parsing
```

## Rules

### ✅ DO

- ✅ Implement multiple parsing strategies
- ✅ Normalize data to consistent format
- ✅ Handle missing/null data gracefully
- ✅ Use regex/JSON parsing as appropriate
- ✅ Return empty structures for invalid data
- ✅ Log parsing errors for debugging
- ✅ Validate parsed data structure

### ❌ DON'T

- ❌ Assume single data format
- ❌ Throw exceptions on parse errors
- ❌ Return None for parse failures
- ❌ Skip data validation
- ❌ Mix parsing logic with business logic
- ❌ Create parsing dependencies

## Parser Pattern

```python
from src.core.background_scheduler.parsers.news import parse_categorized_news

# Parse news data from API response
response_text = """{
    "articles": [
        {"title": "News 1", "category": "financial"},
        {"title": "News 2", "category": "market"}
    ]
}"""

parsed_data = parse_categorized_news(response_text)

# Parsed data structure:
# {
#     "articles": [
#         {
#             "title": "News 1",
#             "category": "financial",
#             "timestamp": "2024-01-01T12:00:00Z",
#             "source": "unknown"
#         },
#         ...
#     ]
# }
```

## Multi-Strategy Parsing

Parsers handle multiple response formats:

```python
def parse_categorized_news(response_text: str) -> Dict[str, Any]:
    """Parse news with multiple strategies."""
    if not response_text:
        return {"articles": []}
    
    # Strategy 1: Try JSON parsing
    try:
        data = json.loads(response_text)
        if "articles" in data:
            return normalize_articles(data["articles"])
    except json.JSONDecodeError:
        pass
    
    # Strategy 2: Try regex extraction
    articles = extract_with_regex(response_text)
    if articles:
        return {"articles": articles}
    
    # Strategy 3: Try structure inference
    articles = infer_articles_structure(response_text)
    return {"articles": articles}
```

## Normalization Pattern

Normalize data to consistent format:

```python
def normalize_article(article: Dict) -> Dict:
    """Normalize article to standard format."""
    return {
        "title": article.get("title", ""),
        "category": article.get("category", "general"),
        "timestamp": normalize_timestamp(article.get("timestamp")),
        "source": article.get("source", "unknown"),
        "url": article.get("url", ""),
        "content": article.get("content", "")
    }
```

## Error Handling

Parsers handle errors gracefully:

```python
def parse_categorized_news(response_text: str) -> Dict[str, Any]:
    """Parse news with error handling."""
    try:
        # Attempt parsing
        data = json.loads(response_text)
        return normalize_articles(data)
    except json.JSONDecodeError as e:
        logger.warning(f"JSON parse error: {e}")
        return {"articles": []}  # Return empty structure
    except Exception as e:
        logger.error(f"Parse error: {e}", exc_info=True)
        return {"articles": []}  # Never return None
```

## Earnings Parser Pattern

```python
from src.core.background_scheduler.parsers.earnings import parse_comprehensive_earnings

# Parse earnings data
response_text = """Earnings data from API"""

parsed_earnings = parse_comprehensive_earnings(response_text)

# Parsed structure:
# {
#     "symbol": "AAPL",
#     "quarter": "Q1 2024",
#     "revenue": 123456,
#     "earnings": 12345,
#     "date": "2024-01-01"
# }
```

## Fundamental Analysis Parser Pattern

```python
from src.core.background_scheduler.parsers.fundamental_analysis import parse_deep_fundamentals

# Parse fundamental analysis
response_text = """Fundamental analysis data"""

parsed_fundamentals = parse_deep_fundamentals(response_text)

# Parsed structure:
# {
#     "symbol": "AAPL",
#     "metrics": {...},
#     "ratios": {...},
#     "analysis": "..."
# }
```

## Dependencies

Parser components depend on:
- `json` - For JSON parsing
- `re` - For regex parsing
- `Logger` - For error logging
- `datetime` - For timestamp normalization

## Testing

Test parser strategies:

```python
import pytest
from src.core.background_scheduler.parsers.news import parse_categorized_news

def test_parse_json_format():
    """Test JSON format parsing."""
    response = '{"articles": [{"title": "News 1"}]}'
    result = parse_categorized_news(response)
    
    assert len(result['articles']) == 1
    assert result['articles'][0]['title'] == "News 1"

def test_parse_empty_response():
    """Test empty response parsing."""
    result = parse_categorized_news("")
    assert result['articles'] == []
```

## Maintenance

When adding new parsers:

1. Implement multiple parsing strategies
2. Normalize to consistent format
3. Handle errors gracefully (return empty structure)
4. Log parsing errors
5. Update this CLAUDE.md file

