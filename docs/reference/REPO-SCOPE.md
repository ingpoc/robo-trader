# Repo Scope

This is an implementation repo.

## Owns

- Backend application code under `src/`
- Frontend application code under `ui/`
- Repo-local tests, scripts, and CI wiring
- Repo-local architecture and workflow documentation
- Repo-local roadmap and ADRs

## Does Not Own

- Cross-project operating principles from the global Codex rules
- Workspace-wide governance policy
- Durable execution tracking outside GitHub and repo docs
- Durable memory that should live in Notion

## Systems Of Record

- Linear: active work, status, blockers, review readiness
- Notion: durable decisions, research context, incident notes, supersession chain
- GitHub: source, branches, PR reviews, merge history
- Repo docs: operating contract for this codebase

## Routing Rule

If a rule only matters for Robo Trader, it belongs here. If it applies across unrelated repos, it should not be authored here.
