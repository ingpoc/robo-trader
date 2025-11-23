---
name: use-mcp-intelligence-workflows
enabled: true
event: bash
conditions:
  - field: command
    operator: regex_match
    pattern: (curl\s+-X\s+(POST|PUT)\s+localhost:8000/api/queue|for\s+.*in.*\{.*do.*curl.*\}|curl\s+.*api/(tasks|queue|workflow))
action: warn
---

⚠️ **Manual API workflow detected**

Use MCP workflow orchestration tools for intelligent task chaining:

- `workflow_orchestrator` - Chain tools with shared context (87-90% token reduction)
- `smart_cache` - Intelligent caching with TTL and refresh
- `differential_analysis` - Show only changes since last check (99% token reduction)
- `knowledge_query` - Context-aware unified queries (95-98% token reduction)
- `session_context_injection` - Real-time progress tracking with 0 token overhead

Manual curl loops waste tokens and lack error handling.
