---
name: use-mcp-intelligence-workflows
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (curl\s+-X\s+(POST|PUT)\s+localhost:8000/api/queue|for\s+.*in.*\{.*do.*curl.*\}|curl\s+.*api/(tasks|queue|workflow))
action: block
---

🚫 BLOCKED: Use MCP for workflow operations.
Run `search_tools(query="workflow", category_filter="orchestration")` to discover tools.
