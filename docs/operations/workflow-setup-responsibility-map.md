# Workflow Setup Responsibility Map

This document defines which surface owns which kind of truth for the Robo Trader repo.

## Ownership Map

| Surface | Owns | Does Not Own |
| --- | --- | --- |
| Linear | Active execution, status, blockers, review readiness | Durable architecture memory, research archives |
| Notion | Durable decisions, research notes, incident notes, superseded-memory links | Day-to-day execution status |
| GitHub | Code, branches, PRs, review comments, merge history | Durable product memory, task board state |
| Repo docs | Repo-local operating contract, architecture scope, workflow instructions | Workspace-wide policy |

## Repo-Local Files

| Artifact | Owner | Purpose |
| --- | --- | --- |
| `AGENTS.md` | Repo docs | Compressed trigger file for repo-local instructions |
| `ROADMAP.md` | Repo docs | Repo-local direction and priorities |
| `docs/reference/MISSION.md` | Repo docs | Product intent for this implementation repo |
| `docs/reference/REPO-SCOPE.md` | Repo docs | Boundary and ownership rules |
| `docs/workflow/zerodha-broker-control-plane.md` | Repo docs | Zerodha auth, quote-stream, and broker readiness truth |
| `docs/workflow/codex-runtime-control-plane.md` | Repo docs | Local Codex sidecar and AI runtime readiness truth |
| `docs/workflow/browser-testing-control-plane.md` | Repo docs | Browser-testing method and evidence rules |
| `docs/workflow/mcp-auth-bootstrap.md` | Repo docs | First-run MCP and auth bootstrap only |
| `docs/workflow/*.md` | Repo docs | Repo-local workflow control planes and operating rules |
| `docs/adrs/*` | Repo docs + Notion pointer | Architecture decisions that shape the implementation |
| `tests/services/VALIDATION_STRATEGY.md` | Tests | Short implementation reference that points to owning workflow docs |
| `tests/validator/README.md` | Tests | Application-specific validation inventory and endpoint reference |

## Anti-Drift Rules

- Do not let the same workflow rule be fully authored in both repo docs and Notion.
- Do not let Linear become the durable memory store for architecture or research.
- Do not let test docs become control-plane owners for browser method, broker truth, or runtime readiness.
- When a local doc becomes obsolete, add a superseded note pointing to the replacement.
- When a decision matters beyond one PR, capture it as an ADR and link the corresponding Notion page.

## Failure Modes

- If Linear is unavailable, keep execution notes in the PR or commit history temporarily, then backfill Linear.
- If Notion is unavailable, capture blocking architecture decisions under `docs/adrs/` and sync them into Notion later.
- If MCP/auth setup is incomplete, record the missing dependency in Linear and do not silently rely on developer-local state.
