# Robo Trader Repo Instructions

Repo-local instructions only. Global Codex policy stays in `~/.codex/*`; do not copy it here.

## Scope

- This repository owns the implementation for the Robo Trader backend, UI, tests, and repo-local workflow docs.
- Active execution status belongs in Linear.
- Durable decisions, research notes, and incident memory belong in Notion.
- Code, branches, PRs, and merge history belong in GitHub.
- Repo docs own the operating contract for this codebase.

## Agent Behavior Contract

- Use independent technical judgment. If the requested direction is weaker than a clearly better option, say so and recommend the stronger path.
- Do not assume facts that can be checked in code, config, repo docs, or primary documentation.
- For architecture, governance, safety, broker, or API decisions, verify uncertain claims before finalizing direction.
- Say when something is known, inferred, or still unverified if that distinction affects the outcome.
- Fail loud on missing auth, MCP access, credentials, or tooling when they are required by the chosen workflow.
- Do not route around broken primary paths with fallback behavior and call the work complete. If the real path is failing, fix it or surface it as a blocker explicitly.
- Ground recommendations in inspected code, repo docs, and primary documentation; use MCP tools to reduce uncertainty rather than to justify guesses.
- Keep repo-local instructions specific to Robo Trader; do not import workspace-wide policy into this file.

## Trigger Lines

- BEFORE changing delivery workflow or issue hygiene: read `docs/workflow/linear-issue-control-plane.md`.
- BEFORE storing or superseding durable decisions or research: read `docs/workflow/notion-memory-control-plane.md`.
- BEFORE changing MCP servers, auth setup, or credential expectations: read `docs/workflow/mcp-auth-bootstrap.md`.
- BEFORE changing repo boundaries, ownership, or where a rule should live: read `docs/operations/workflow-setup-responsibility-map.md`.
- BEFORE starting new governance, feature, or enhancement planning: read `docs/workflow/repo-governance.md`.
- BEFORE deciding under technical uncertainty or recommending a dependency, protocol, or API change: read `docs/workflow/research-validation-loop.md`.
- BEFORE browser testing, UI validation, or diagnosing state mismatches between UI and backend: read `docs/workflow/browser-testing-control-plane.md`.
- BEFORE changing branching, review, or verification expectations: read `docs/workflow/git-governance-control-plane.md`.
- BEFORE making a material architecture decision: read `docs/reference/MISSION.md`, `docs/reference/REPO-SCOPE.md`, and `ROADMAP.md`, then capture the decision under `docs/adrs/`.

## Repo Rules

- Keep repo-local workflow rules in `docs/workflow/`; do not duplicate workspace governance docs.
- Keep architecture and product intent in repo docs, not in issue templates.
- When a new ADR or workflow doc supersedes an older local note, update the older note with an explicit pointer.
- Do not use Notion as a task board for this repo; execution tracking remains in Linear.
- Do not add long procedural text here; add or update the owning doc and keep this file compressed.
