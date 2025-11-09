# Code Execution & Sandbox Guide

## Overview

The robo-trader MCP server provides two powerful code execution tools for AI agents:

1. **`execute_python`**: Execute arbitrary Python code with 98%+ token savings
2. **`execute_analysis`**: Pre-configured data analysis operations with 99%+ token savings

Both tools run in isolated subprocess sandboxes with strict security boundaries.

## Why Sandboxing?

Traditional multi-turn AI reasoning about data operations costs significant tokens:

**Traditional Approach** (Multi-turn Reasoning):
```
User:    "Analyze this stock portfolio data"
Claude:  "I'll filter for high-ROI stocks..."
Claude:  "Now I'll calculate averages..."
Claude:  "Let me determine the best performers..."
Claude:  "Finally, I'll format the results..."
Result:  ~7,600 tokens consumed
```

**Sandbox Approach** (Direct Execution):
```
Claude:  "I'll execute code directly to analyze portfolio"
execute_python() → result
Result:  ~200-300 tokens consumed (97.4% reduction)
```

## Tool #1: execute_python

Execute arbitrary Python code in isolated subprocess with import restrictions and timeouts.

### Basic Usage

```python
from src.tools.execution.execute_python import execute_python

# Simple calculation
code = """
numbers = [1, 2, 3, 4, 5]
result = {
    "sum": sum(numbers),
    "average": sum(numbers) / len(numbers),
    "count": len(numbers)
}
"""

response = execute_python(code)
# Response: {
#   "success": True,
#   "result": {"sum": 15, "average": 3.0, "count": 5},
#   "execution_time_ms": 45,
#   "token_efficiency": {...}
# }
```

### Context Injection

Pass variables into the execution environment:

```python
code = """
adjusted_prices = [p * multiplier for p in prices]
result = {
    "original": prices,
    "adjusted": adjusted_prices,
    "factor": multiplier
}
"""

response = execute_python(
    code,
    context={
        "prices": [100, 150, 200],
        "multiplier": 1.1
    }
)
# Result:
# {
#   "original": [100, 150, 200],
#   "adjusted": [110, 165, 220],
#   "factor": 1.1
# }
```

### Allowed Imports

Safe standard library modules for data analysis:

- **Math/Statistics**: `math`, `statistics`, `decimal`, `fractions`, `random`, `numbers`
- **Data Structures**: `json`, `collections`, `itertools`
- **Time**: `datetime`
- **Utilities**: `functools`, `copy`, `re`, `string`, `typing`, `types`, `abc`, `enum`
- **Internal (auto-used)**: `_io`, `_collections`, `_functools`, `_heapq`, `_operator`, etc.

### Restricted/Blocked

These are intentionally blocked:

- ❌ `os`, `sys` - No system access
- ❌ `subprocess` - No process spawning
- ❌ `socket`, `urllib` - No network access (except via context)
- ❌ `pickle` - No serialization vulnerabilities
- ❌ `eval()`, `exec()`, `compile()` - Dynamic code execution
- ❌ File I/O operations - No filesystem access

### Configuration Options

```python
response = execute_python(
    code="result = {'test': 1}",
    context=None,                    # Variables to inject
    timeout_seconds=30,              # Max 120 seconds
    isolation_level="production"     # or "hardened"
)
```

**Isolation Levels**:
- `production` (default): Balanced security/capability
- `hardened`: Maximum security, minimal imports
- `development`: Permissive for debugging

### Response Format

```python
{
    "success": True,                 # Execution succeeded
    "result": {...},                 # Output from 'result' variable
    "stdout": "...",                 # Standard output
    "stderr": "...",                 # Standard error
    "execution_time_ms": 45,         # Duration
    "token_efficiency": {
        "compression_ratio": "98%+",
        "estimated_traditional_tokens": "7600+",
        "estimated_sandbox_tokens": "200-300"
    },
    "error": None                    # Error if failed
}
```

### Use Cases

#### Portfolio Analysis
```python
code = """
import statistics

portfolio = {
    "AAPL": {"price": 150, "shares": 10, "sector": "Tech"},
    "JNJ": {"price": 160, "shares": 5, "sector": "Healthcare"},
    "XOM": {"price": 110, {"shares": 8, "sector": "Energy"}
}

# Calculate total value
total_value = sum(stock["price"] * stock["shares"] for stock in portfolio.values())

# Group by sector
sectors = {}
for symbol, data in portfolio.items():
    sector = data["sector"]
    if sector not in sectors:
        sectors[sector] = []
    sectors[sector].append({"symbol": symbol, "value": data["price"] * data["shares"]})

# Calculate statistics
sector_totals = {s: sum(item["value"] for item in stocks) for s, stocks in sectors.items()}
sector_percentages = {s: (v / total_value * 100) for s, v in sector_totals.items()}

result = {
    "total_portfolio_value": total_value,
    "sector_breakdown": sector_percentages,
    "sector_details": sectors
}
"""

response = execute_python(code, context={"portfolio": your_portfolio_data})
```

#### Data Transformation
```python
code = """
# Transform nested data structure
records = [
    {"id": 1, "name": "Alice", "email": "alice@example.com", "phone": "555-0001"},
    {"id": 2, "name": "Bob", "email": "bob@example.com", "phone": "555-0002"},
]

# Extract only needed fields
contacts = [
    {"id": r["id"], "name": r["name"], "email": r["email"]}
    for r in records
]

result = {
    "total_contacts": len(contacts),
    "contacts": contacts,
    "emails": [c["email"] for c in contacts]
}
"""
```

## Tool #2: execute_analysis

Pre-configured data analysis operations - the most token-efficient approach (99%+).

### Analysis Types

#### 1. Filter
Select records matching conditions:

```python
response = execute_analysis(
    analysis_type="filter",
    data={
        "stocks": [
            {"symbol": "AAPL", "sector": "Tech", "roi": 15.5},
            {"symbol": "JNJ", "sector": "Healthcare", "roi": 8.2},
            {"symbol": "GOOGL", "sector": "Tech", "roi": 12.3},
        ]
    },
    parameters={
        "data_field": "stocks",
        "conditions": [
            {"field": "sector", "operator": "==", "value": "Tech"},
            {"field": "roi", "operator": ">", "value": 10}
        ],
        "logic": "AND"  # or "OR"
    }
)

# Result includes filtered data and statistics
```

**Supported Operators**:
- Comparison: `==`, `!=`, `>`, `<`, `>=`, `<=`
- Containment: `in`, `contains`
- Logic: `AND`, `OR`

#### 2. Aggregate
Group data and compute statistics:

```python
response = execute_analysis(
    analysis_type="aggregate",
    data={
        "sales": [
            {"region": "North", "amount": 1000},
            {"region": "North", "amount": 1500},
            {"region": "South", "amount": 2000},
            {"region": "South", "amount": 1800},
        ]
    },
    parameters={
        "data_field": "sales",
        "group_by": "region"
    }
)

# Result: grouped data by region
```

#### 3. Transform
Select and rename fields:

```python
response = execute_analysis(
    analysis_type="transform",
    data={
        "users": [
            {"id": 1, "name": "Alice", "email": "alice@example.com", "phone": "555-0001"},
            {"id": 2, "name": "Bob", "email": "bob@example.com", "phone": "555-0002"},
        ]
    },
    parameters={
        "data_field": "users",
        "output_fields": ["id", "name", "email"],
        "rename": {"name": "full_name"}
    }
)

# Result: transformed data with selected fields renamed
```

#### 4. Validate
Check data quality and constraints:

```python
response = execute_analysis(
    analysis_type="validate",
    data={
        "records": [
            {"id": 1, "name": "Alice", "email": "alice@example.com"},
            {"id": 2, "name": "Bob"},  # Missing email
        ]
    },
    parameters={
        "data_field": "records",
        "validations": [
            {"field": "id", "type": "numeric", "required": True},
            {"field": "name", "type": "string", "required": True},
            {"field": "email", "type": "string", "required": True}
        ]
    }
)

# Result: validation report with issues
```

### Response Format

```python
{
    "success": True,
    "result": {
        "analysis_type": "filter",
        "filtered_count": 5,
        "total_count": 10,
        "filtered_percentage": 50.0,
        "data": [...]
    },
    "execution_time_ms": 12,
    "token_efficiency": {
        "compression_ratio": "99%+",
        "estimated_traditional_tokens": "5000+",
        "estimated_sandbox_tokens": "100-200"
    }
}
```

## Security Model

### Subprocess Isolation

Each execution runs in a separate Python subprocess:

```
Claude → SandboxManager → subprocess.run(["python3", temporary_script.py])
                         ↓
                    Restricted environment
                    Limited imports
                    Timeout protection
                    ↓
                    Returns JSON result
```

### Restricted Environment Variables

Sensitive credentials are stripped before subprocess execution:

- ❌ `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
- ❌ `ZERODHA_API_SECRET`, `API_KEY`
- ✓ `HOME`, `PATH`, `PYTHONUNBUFFERED`

### Code Validation

Pre-execution checks block dangerous patterns:

- ❌ `eval(`, `exec(`, `compile(`, `__import__(`
- ❌ `os.system`, `subprocess`, `open(`
- ❌ `pickle`

### Timeout Protection

All executions have configurable timeouts (1-120 seconds, default 30):

```python
response = execute_python(code, timeout_seconds=5)
# If code runs > 5 seconds, execution is terminated
```

## Performance Characteristics

### Execution Time

Typical execution times:

- Simple calculations: 10-20ms
- Data transformations: 20-50ms
- Complex analysis: 50-100ms
- Timeout scenarios: 1000-30000ms (at timeout limit)

### Token Savings

**Scenario**: Analyze 100-item dataset

Traditional multi-turn reasoning:
- Read data: 1500 tokens
- Reason about filtering: 2000 tokens
- Calculate aggregates: 2000 tokens
- Format results: 1100 tokens
- **Total: ~6,600 tokens**

Sandbox execution:
- Setup context: 50 tokens
- Execute code: 150 tokens
- Parse results: 100 tokens
- **Total: ~300 tokens**

**Savings: 95.5% token reduction**

## Best Practices

### 1. Assign to `result` Variable

Code MUST assign output to `result` variable:

```python
# ✓ CORRECT
code = """
data = [1, 2, 3]
result = {"sum": sum(data)}
"""

# ✗ WRONG - No result variable
code = """
data = [1, 2, 3]
print(sum(data))
"""
```

### 2. Use JSON-Serializable Data

Results must be JSON-serializable:

```python
# ✓ CORRECT
result = {
    "numbers": [1, 2, 3],
    "text": "hello",
    "flag": True,
    "empty": None
}

# ✗ WRONG - datetime not JSON-serializable
from datetime import datetime
result = {"timestamp": datetime.now()}
```

### 3. Filter Before Aggregation

For large datasets, filter first:

```python
# ✓ EFFICIENT
code = """
# Filter 1M items to 1K
filtered = [x for x in data if x["status"] == "active"]
# Aggregate 1K items
result = {"count": len(filtered), "sum": sum(x["value"] for x in filtered)}
"""

# ✗ LESS EFFICIENT
code = """
# Aggregate all 1M items
result = {
    "active_count": len([x for x in data if x["status"] == "active"]),
    "active_sum": sum(x["value"] for x in data if x["status"] == "active")
}
"""
```

### 4. Use execute_analysis for Standard Operations

For common operations, use pre-configured analysis:

```python
# ✓ TOKEN EFFICIENT (99%+)
execute_analysis("filter", data, parameters)

# ✓ WORKS BUT LESS EFFICIENT (98%+)
execute_python("filtered = [x for x in data if condition]")
```

### 5. Handle Large Results

For very large result sets, summarize:

```python
# ✓ EFFICIENT
code = """
result = {
    "count": len(data),
    "summary_stats": {
        "min": min(data),
        "max": max(data),
        "avg": sum(data) / len(data)
    },
    "sample": data[:10]  # First 10 items only
}
"""

# ✗ INEFFICIENT
code = """
result = data  # Return all 1M items
"""
```

## Troubleshooting

### Import Errors

**Error**: `"Module 'os' is not allowed"`

**Solution**: Use allowed imports only. For OS operations, pass data via context instead.

```python
# ✗ WRONG
code = """
import os
result = {"home": os.environ["HOME"]}
"""

# ✓ CORRECT
code = """
result = {"home": home_path}
"""
response = execute_python(code, context={"home_path": home_path})
```

### Timeout Errors

**Error**: `"Execution timed out after 30s"`

**Solution**: Increase timeout or optimize code:

```python
# ✓ INCREASE TIMEOUT
response = execute_python(code, timeout_seconds=60)

# ✓ OPTIMIZE - Filter before heavy computation
code = """
# Filter to smaller dataset first
small_set = [x for x in data if x["score"] > threshold]
# Now do expensive computation
result = expensive_analysis(small_set)
"""
```

### JSON Serialization Errors

**Error**: `"Code did not return JSON-serializable output"`

**Solution**: Ensure result contains only JSON-compatible types:

```python
# ✗ WRONG
result = {
    "set": {1, 2, 3},  # Sets aren't JSON-serializable
    "time": datetime.now()
}

# ✓ CORRECT
result = {
    "list": [1, 2, 3],
    "time": "2025-01-15T10:30:00"
}
```

## Advanced Usage

### Multi-Step Analysis

Break complex operations into steps:

```python
# Step 1: Filter
step1 = execute_analysis("filter", data, filter_params)
filtered_data = step1["result"]["data"]

# Step 2: Aggregate
step2 = execute_analysis("aggregate", {"items": filtered_data}, agg_params)
aggregated = step2["result"]["groups"]

# Step 3: Transform
step3 = execute_analysis("transform", {"items": aggregated}, transform_params)
final_result = step3["result"]["data"]
```

### Custom Analysis with execute_python

When pre-configured analysis isn't sufficient:

```python
code = """
import statistics
import json

# Complex analysis combining multiple operations
portfolio = context_data
roi_values = [stock["roi"] for stock in portfolio.values()]

result = {
    "count": len(portfolio),
    "avg_roi": statistics.mean(roi_values),
    "median_roi": statistics.median(roi_values),
    "min_roi": min(roi_values),
    "max_roi": max(roi_values),
    "volatility": statistics.stdev(roi_values) if len(roi_values) > 1 else 0,
    "high_performers": [
        {"symbol": s, "roi": data["roi"]}
        for s, data in portfolio.items()
        if data["roi"] > 10
    ]
}
"""

response = execute_python(code, context={"context_data": portfolio_data})
```

## API Reference

### execute_python()

```python
def execute_python(
    code: str,
    context: Optional[Dict[str, Any]] = None,
    timeout_seconds: int = 30,
    isolation_level: str = "production"
) -> Dict[str, Any]
```

**Parameters**:
- `code` (str): Python code to execute (must assign to `result` variable)
- `context` (dict): Variables to inject into execution environment
- `timeout_seconds` (int): Execution timeout (1-120, default 30)
- `isolation_level` (str): "production", "hardened", or "development"

**Returns**: Response dict with `success`, `result`, `execution_time_ms`, `token_efficiency`

### execute_analysis()

```python
def execute_analysis(
    analysis_type: str,
    data: Dict[str, Any],
    parameters: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]
```

**Parameters**:
- `analysis_type` (str): "filter", "aggregate", "transform", or "validate"
- `data` (dict): Data to analyze
- `parameters` (dict): Analysis-specific parameters

**Returns**: Response dict with structured analysis results

## See Also

- `src/sandbox/manager.py` - Sandbox implementation
- `src/sandbox/isolation.py` - Security policies
- `tests/test_execution_tools.py` - Test examples
