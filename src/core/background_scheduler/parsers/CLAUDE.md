# Background Scheduler Parsers - src/core/background_scheduler/parsers/

Data parsing functions. Transform raw API responses into structured, normalized data. Max 300 lines.

## Pattern
```python
# Multi-strategy parsing: JSON → Regex → Inference
def parse_categorized_news(response_text: str) -> Dict:
    try:
        data = json.loads(response_text)
        return normalize_articles(data["articles"])
    except json.JSONDecodeError:
        articles = extract_with_regex(response_text)
        if articles:
            return {"articles": articles}
    return {"articles": []}  # Never return None

# Normalize to consistent format
def normalize_article(article: Dict) -> Dict:
    return {
        "title": article.get("title", ""),
        "category": article.get("category", "general"),
        "timestamp": normalize_timestamp(article.get("timestamp")),
        "source": article.get("source", "unknown")
    }
```

## Parsers
| Parser | Parses |
|--------|--------|
| news.py | News articles (JSON/regex/inference) |
| earnings.py | Earnings data (symbol, quarter, revenue, EPS) |
| fundamental_analysis.py | Fundamentals (metrics, ratios, analysis) |

## Rules
| DO | DON'T |
|----|-------|
| Implement multiple strategies | Assume single format |
| Normalize to consistent format | Throw exceptions on parse errors |
| Handle null/missing data | Return None for failures |
| Return empty structures | Mix parsing with business logic |
| Log parsing errors | Skip validation |
| Use JSON/regex appropriately | Create dependencies |

## Dependencies
json, re, Logger, datetime

