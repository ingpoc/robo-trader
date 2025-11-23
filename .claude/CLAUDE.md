# Claude Code Guidelines

## Core Principles
- Fix real issues, not tests. Verify logic works.
- Be concise. Use Context7 MCP when uncertain.
- Read patterns before changing. Test UI with Playwright before concluding.

## Critical Constraints
| Constraint | Rule |
|-----------|------|
| Processes | Max 2 (port 8000, 3000). Kill ports only. |
| Health checks | 5sec timeout on /api/health. Check logs first. |
| AI analysis | MUST use AI_ANALYSIS queue (prevents token exhaustion) |
| Database access | Use locked state methods, never direct connection |
| Queues | 3 parallel, sequential tasks within each |

## File Management
- Delete test files after testing. Remove unwanted files from root.
- No summary/analysis docs—present findings directly.
- No new *.md files except CLAUDE.md or README.md updates.

## Code & Testing
- Verify immediately: read-back, syntax check (no batching).
- Test from UI. Use robo-trader-dev MCP tools for debugging.

## MCP & Architecture
- MCP discovery: `list_categories` → `load_category`
- MCP execution: via `/mcp` commands, not bash subprocesses
- Architecture questions: Consult `@feature-dev:code-architect`
- Bugs: Debug with robo-trader-dev MCP first

## Documentation
- Read layer-specific CLAUDE.md before changes
- Update CLAUDE.md when discovering flaws
- Restart server and test UI after fixes