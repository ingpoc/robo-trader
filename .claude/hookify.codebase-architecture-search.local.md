---
name: codebase-architecture-search
enabled: true
event: prompt
pattern: (how|what|where).*(architecture|designed|structured|pattern|organized)|(find|search).*(all|every).*(class|function|method|coordinator|service)
action: warn
---

🔍 **Architectural Query Detected**

You're asking about codebase architecture or searching for patterns.

Instead of using grep/find repeatedly:
1. Use `@feature-dev:code-architect` skill for architectural questions
2. Use `mcp__robo-trader-dev__find_related_files(reference="ClassName", relation_type="all")` (88% savings)
3. Use `mcp__robo-trader-dev__smart_file_read(file_path="...", context="summary")` for overviews (85% savings)
4. Use Context7 MCP for framework-specific patterns

**I'll route this to the appropriate resource.**
