# Claude Code Guidelines

## Core Principles

- Fix real issues, not tests. Verify logic works.
- Be concise. Use Context7 MCP when uncertain.
- Read patterns before changing. Test UI with Playwright before concluding.

## My Role: Development Only (NOT Trading)

Claude Code: Debug, fix bugs, review logs, analyze what bot did
Agent SDK Bot: Portfolio analysis, risk decisions, trade execution
I NEVER: Make trading decisions, portfolio analysis, or invoke bot

## Critical Constraints

| Constraint | Rule |
|-----------|------|
| Processes | Max 2 (port 8000, 3000). Kill ports only. |
| Health checks | 5sec timeout on /api/health. Check logs first. |
| AI analysis | MUST use AI_ANALYSIS queue (prevents token exhaustion) |
| Database access | Use locked state methods, never direct connection |
| Queues | 3 parallel, 20 max capacity, sequential tasks within each |

## File Management

- Delete test files after testing. Remove unwanted files from root.
- No summary/analysis docs—present findings directly.
- No new *.md files except CLAUDE.md or README.md updates.

## Code & Testing

- Verify immediately: read-back, syntax check (no batching).
- Test from UI. Use robo-trader-dev MCP tools for debugging.

## Component Creation Locations

`.claude/` is shared by both Claude Code and Agent SDK bot (same agent harness):

| Type | Location | Auto-Discovered By |
|------|----------|-------------------|
| Skills | `.claude/skills/NAME/SKILL.md` | Both Claude Code + Agent SDK |
| Agents | `.claude/agents/NAME.md` | Agent SDK bot |
| Hooks | `.claude/settings.json` + `.claude/hooks/` | Both systems |
| MCP Config | `.mcp.json` at root | Both (separate servers) |
| Dev tools | `shared/robotrader_mcp/` | Claude Code debugging only |
| Internal | `src/` | Not auto-discovered |

## MCP & Debugging

- Use robo-trader-dev MCP: `list_categories` → `load_category`
- Hookify rules prevent mistakes automatically
- Debug with robo-trader-dev MCP first (95%+ token reduction)

## Documentation

- Read layer-specific CLAUDE.md before changes
- Update CLAUDE.md when discovering flaws
- Restart server and test UI after fixes
