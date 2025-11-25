---
name: api-response-validation
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (curl.*\|.*jq|jq.*\|.*grep|curl.*\|.*grep.*\|.*awk|grep.*JSON.*\|)
action: block
---

🚫 BLOCKED: Complex JSON parsing chains detected.

Instead of: `curl API | jq '.data' | grep pattern | awk '{print $1}'`

Use MCP tools:
- `mcp__robo-trader-dev__context_aware_summarize(data_source="api", user_context="...")` (95% token savings)
- `mcp__robo-trader-dev__execute_analysis(analysis_type="filter", data={...}, parameters={...})` (99% savings)
- `mcp__robo-trader-dev__knowledge_query(query_type="insights")` for unified analysis

These provide structured JSON output with intelligent filtering.
