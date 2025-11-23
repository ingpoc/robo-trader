# Token Optimization Plan - Progressive Discovery Pattern

**Based on**: [Anthropic's Research Paper on Code Execution with MCP](https://www.anthropic.com/engineering/code-execution-with-mcp)

## Executive Summary

Current token waste: **~3,000-4,000 tokens/session**
Target reduction: **98%** (matching Anthropic's benchmark: 150,000 → 2,000 tokens)

## Key Principles from Anthropic's Research

### 1. Progressive Discovery (Not Upfront Dump)
Instead of loading all tool definitions upfront, use filesystem-like discovery:
- Tools exposed as discoverable entities
- `search_tools(query, detail_level)` function with configurable detail
- Detail levels: `name_only`, `with_description`, `full_schema`

### 2. Context Filtering (Process Before Return)
Large datasets should be filtered in execution environment BEFORE returning to model:
```python
# BAD: Return all rows
return all_positions  # 10,000 tokens

# GOOD: Filter first
pending = [p for p in positions if p["status"] == "open"]
return pending[:5]  # 50 tokens
```

### 3. Code Execution Pattern
Native code patterns replace chained tool calls - conditionals execute in environment, not model.

### 4. Minimal Tool Definitions
- Tool name: 2-3 words
- Description: Omit unless requested
- Schema: Only on `full_schema` request

---

## Implementation Phases

### Phase 1: Progressive Tool Discovery (HIGH IMPACT)

**Current State** (mcp_server.py lines 72-150):
```python
"execute_trade": {
    "name": "execute_trade",
    "description": "Execute a paper trade (buy/sell equity or option)",
    "input_schema": {
        "type": "object",
        "properties": {
            "symbol": {"type": "string", "description": "Stock symbol (e.g., SBIN)"},
            # ... 8 more fields with descriptions
        }
    }
}
```
**Token cost**: ~100 tokens per tool × 6 tools = **600 tokens**

**Target State**:
```python
# Minimal tool registry (name only)
_tool_names = {
    "execute_trade": "Trade",
    "close_position": "Close",
    "check_balance": "Balance",
    "get_strategy_learnings": "Learnings",
    "get_monthly_performance": "Performance",
    "analyze_position": "Analyze"
}
# Token cost: ~30 tokens total

# Full definitions loaded on-demand via search_tools()
async def search_tools(query: str, detail: str = "name_only") -> List[Dict]:
    if detail == "name_only":
        return [{"name": n, "brief": b} for n, b in _tool_names.items() if query in n]
    elif detail == "with_description":
        return [{"name": n, "description": _full_tools[n]["description"]} for n in matches]
    else:  # full_schema
        return [_full_tools[n] for n in matches]
```

**Savings**: ~570 tokens/session (95% reduction in tool definitions)

---

### Phase 2: Compress System Prompt (MEDIUM IMPACT)

**Current State** (agent_prompt_builder.py lines 28-47):
```python
"""You are RoboTrader, an autonomous trading agent managing a {account_type} trading account.

Your responsibilities:
1. Analyze market conditions and trade setups
2. Execute trades autonomously using available tools
3. Monitor positions and close trades when appropriate
4. Manage risk according to portfolio constraints
5. Learn from previous trading decisions

You have access to trading tools. Use them wisely to execute your trading strategy.

Risk Management Rules:
- Max position size: 5% of portfolio
- Max portfolio risk: 10%
- Stop loss minimum: 2% below entry
- All trades must have clear rationale

Remember: Your decisions will be logged and analyzed. Trade responsibly."""
```
**Token cost**: ~250 tokens

**Target State**:
```python
"""RoboTrader ({account_type}). Rules: max_pos=5%, max_risk=10%, min_sl=2%. Tools: search_tools to discover. Log all rationale."""
```
**Token cost**: ~30 tokens

**Savings**: ~220 tokens/session (88% reduction)

---

### Phase 3: Remove JSON Indentation (QUICK WIN)

**Current State**:
```python
json.dumps(result.get("output", {}), indent=2)  # Lines 228, 301
json.dumps(data, indent=2, default=str)         # Line 301
json.dumps(context, indent=2)                   # agent_prompt_builder.py
```

**Target State**:
```python
json.dumps(result.get("output", {}))            # No indent
json.dumps(data, default=str)                   # No indent
json.dumps(context, separators=(',', ':'))      # Compact
```

**Savings**: ~100-150 tokens/session (10-15% reduction on JSON outputs)

---

### Phase 4: Context Filtering Enhancement (HIGH IMPACT)

**Current State** (agent_prompt_builder.py):
```python
OPEN POSITIONS:
{json.dumps(context.get('pos', [])[:5], indent=2)}

TRADES TODAY:
{json.dumps(context.get('trades', [])[:10], indent=2)}
```
Each position: ~80-120 tokens × 5 = **400-600 tokens**
Each trade: ~80-120 tokens × 10 = **800-1200 tokens**

**Target State**:
```python
# Ultra-compact format
POSITIONS: {pos_summary}  # "RELIANCE:+2.3%,TCS:-1.1%,INFY:+0.5%"
TRADES: {trades_summary}  # "3 buys, 2 sells, net +₹1,234"
```
**Token cost**: ~30 tokens for positions, ~20 tokens for trades = **50 tokens**

**Savings**: ~1,500 tokens/session (95% reduction on context)

---

### Phase 5: Differential Updates (STRATEGIC)

**Concept**: Only send changed data in subsequent calls.

```python
class DifferentialContext:
    def __init__(self):
        self._last_context = {}

    def get_delta(self, current: Dict) -> Dict:
        delta = {}
        for key, value in current.items():
            if key not in self._last_context or self._last_context[key] != value:
                delta[key] = value
        self._last_context = current.copy()
        return delta
```

**Impact**: 40-60% reduction on subsequent calls within same session

---

## Implementation Priority

| Phase | Impact | Effort | Priority |
|-------|--------|--------|----------|
| Phase 1: Progressive Discovery | HIGH (~570 tokens) | Medium | 1 |
| Phase 4: Context Filtering | HIGH (~1500 tokens) | Low | 2 |
| Phase 2: System Prompt | MEDIUM (~220 tokens) | Low | 3 |
| Phase 3: Remove Indentation | LOW (~100 tokens) | Very Low | 4 |
| Phase 5: Differential Updates | MEDIUM (~200 tokens) | Medium | 5 |

**Total Potential Savings: ~2,590 tokens/session (65-75% reduction)**

---

## Files to Modify

1. `src/services/claude_agent/mcp_server.py` - Progressive discovery
2. `src/core/coordinators/agent/agent_prompt_builder.py` - Compact prompts
3. `src/services/claude_agent/context_builder.py` - Ultra-compact context
4. `src/core/hooks.py` - Minimal session start injection

---

## Verification Metrics

After implementation, measure:
- Token count per session (target: <1,000)
- Response latency (should decrease with fewer tokens)
- Accuracy of agent decisions (should not degrade)
