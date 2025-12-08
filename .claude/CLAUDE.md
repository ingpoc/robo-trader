# Robo Trader - Autonomous Paper Trading System

## First Thing: Check Progress

Before doing ANY work, read `.claude/progress/`:

| File | Purpose |
|------|---------|
| `feature-list.json` | What's done, what's pending, dependencies |
| `session-state.json` | Was there an abnormal exit? Current feature? |
| `claude-progress.txt` | Human-readable summary |

## Project Purpose

Build autonomous system:
1. Monthly AI analysis of user's real portfolio for keep/sell recommendations
2. Fully autonomous paper trading with ₹1L to test if Claude can be trusted with real money

Claude handles all research, trading, and strategy evolution.

## Startup Ritual

1. Read `.claude/progress/session-state.json` for abnormal exit
2. Read `.claude/progress/feature-list.json` for current state
3. Check git status for uncommitted changes
4. Run `curl -m 3 http://localhost:8000/api/health`
5. Resume current feature OR start next pending feature

## Critical Constraints

| Constraint | Rule |
|------------|------|
| Opus Role | Orchestrate and delegate, don't implement directly |
| Progress Updates | NON-NEGOTIABLE after every feature |
| Processes | Max 2 (port 8000, 3000). Kill ports only |
| AI analysis | MUST use AI_ANALYSIS queue (prevents token exhaustion) |
| Database access | Use locked state methods, never direct connection |
| Queues | 3 parallel, 20 max capacity, sequential tasks within each |

## Role Separation

| Role | Responsibility |
|------|----------------|
| Claude Code (Opus) | Orchestrate, delegate to coding-agent, verify |
| coding-agent (Sonnet) | Implement one feature at a time, update progress |
| Agent SDK Bot | Portfolio analysis, risk decisions, trade execution |

**I NEVER**: Make trading decisions, portfolio analysis, or invoke bot directly

## Two-Agent System

```
New project/complex task → initializer-agent (creates feature-list.json)
                                    ↓
              coding-agent (implements features one at a time)
```

| Situation | Agent |
|-----------|-------|
| New project, complex breakdown | `initializer-agent` |
| Implement feature from feature-list | `coding-agent` |
| Need codebase understanding | `Explore` (built-in) |
| Quick fix (<5 min) | Do directly (say "quick fix") |

## Component Locations

| Type | Location | Auto-Discovered By |
|------|----------|-------------------|
| Skills | `.claude/skills/NAME/SKILL.md` | Both Claude Code + Agent SDK |
| Agents | `~/.claude/agents/NAME.md` | Global (initializer + coding) |
| Progress | `.claude/progress/` | All agents |
| Hooks | `~/.claude/hooks/` | Native hooks (PreToolUse, etc.) |
| MCP Config | `.mcp.json` at root | Both (separate servers) |

## MCP & Debugging

- Use robo-trader-dev MCP: `list_categories` → `load_category`
- Native hooks enforce two-agent system automatically
- Debug with robo-trader-dev MCP first (95%+ token reduction)

## Session Recovery

If `session-state.json` shows `status: "active"` with stale heartbeat (>30 min):

1. Check git status for partial changes
2. Review what was completed vs. in-progress
3. Options: Complete partial work, rollback, or mark blocked
4. Update session state before resuming

## Documentation

- Read layer-specific CLAUDE.md before changes: `src/CLAUDE.md`, `src/core/CLAUDE.md`
- Update CLAUDE.md when discovering flaws
- Restart server and test UI after fixes
