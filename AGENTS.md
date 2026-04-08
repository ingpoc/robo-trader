# Robo Trader Repo Instructions

IMPORTANT: Prefer retrieval-led reasoning over pre-training-led reasoning for any workflow tasks.
[Robo Trader Workflow Index]|root: ./docs
|workflow:{autonomous-paper-entry-go-live-checklist.md,browser-testing-control-plane.md,codex-runtime-control-plane.md,git-governance-control-plane.md,introspection-control-plane.md,linear-issue-control-plane.md,mcp-auth-bootstrap.md,notion-memory-control-plane.md,operator-dashboard-control-plane.md,repo-governance.md,research-validation-loop.md,zerodha-broker-control-plane.md}
|paper_trading_loop:{paper-trading-loop-control-plane.md}
|operations:{workflow-setup-responsibility-map.md}
|reference:{MISSION.md,REPO-SCOPE.md}

Repo-local instructions only.
Global entrypoint: `/Users/gurusharan/.codex/AGENTS.md`

## Inheritance Contract

- Global baseline: `/Users/gurusharan/.codex/AGENTS.md`
- Global expansion: load only docs referenced by `/Users/gurusharan/.codex/AGENTS.md` when needed
- Global exclusion: do not inspect or rely on external publish baselines from repo-local policy
- Workspace parent: `none`
- Organization routing: `inherits_by_default`
- Local policy authority: `AGENTS.md`
- Local CLAUDE policy: `defer_to_agents`

## Scope

- This repository owns the implementation for the Robo Trader backend, UI, tests, and repo-local workflow docs.
- Active execution status belongs in Linear.
- Durable decisions, research notes, and incident memory belong in Notion.
- Code, branches, PRs, and merge history belong in GitHub.
- Repo docs own the operating contract for this codebase.

## Agent Behavior Contract

- Use independent technical judgment. If the requested direction is weaker than a clearly better option, say so and recommend the stronger path.
- For workflow tasks, explore the current project and runtime state first, then retrieve and apply the relevant owner doc or skill.
- Do not interpret "use the skill" or a trigger line as "read docs before building project context."
- Do not assume facts that can be checked in code, config, repo docs, or primary documentation.
- For architecture, governance, safety, broker, or API decisions, verify uncertain claims before finalizing direction.
- Say when something is known, inferred, or still unverified if that distinction affects the outcome.
- Fail loud on missing auth, MCP access, credentials, or tooling when they are required by the chosen workflow.
- Do not route around broken primary paths with fallback behavior and call the work complete. If the real path is failing, fix it or surface it as a blocker explicitly.
- Ground recommendations in inspected code, repo docs, and primary documentation; use MCP tools to reduce uncertainty rather than to justify guesses.
- Keep repo-local instructions specific to Robo Trader; do not import unrelated workspace-wide policy into this file.
- Inspect the current project state first, then act proactively. Do not confuse autonomy with skipping code, runtime, DB, log, or owner-doc inspection.
- Once the relevant local context and allowed execution posture are clear, continue discovery, research, review, proposal, and readiness work without waiting for another user prompt.
- When the operating path is blocked, fix the primary-path issue immediately rather than pausing for confirmation, unless the next step would change autonomous-entry posture or place a trade outside the current allowed mode.
- Keep the dashboard state moving forward each session so the next operator turn starts from explicit watchlist, review, proposal, or incident state rather than rediscovering prior work.
- Whenever a real workflow issue appears, resolve it on the primary path instead of stepping around it. Do not leave known friction in place waiting for another prompt.
- If repeated prompting would have been avoided by clearer repo doctrine, update the owning workflow-control doc in the same session after verifying the failure mode.
- Treat repeated operator friction as a repo issue, not just a session inconvenience: fix the code, script, test, or owning workflow doc that would prevent the same failure next time.

## Trigger Lines

- Trigger lines and skill references are retrieval aids after state inspection, not a substitute for inspecting the live codebase, runtime, logs, or data first.
- BEFORE claiming backend tests are green or debugging a failing backend PR check: run `./scripts/test_backend_ci.sh` from the repo root.
- BEFORE pushing changes that touch DI, app lifespan, schedulers, Docker boot, or runtime startup: run `./scripts/integration_startup_smoke.sh` from the repo root.
- BEFORE changing delivery workflow or issue hygiene: read `docs/workflow/linear-issue-control-plane.md`.
- BEFORE storing or superseding durable decisions or research: read `docs/workflow/notion-memory-control-plane.md`.
- BEFORE changing MCP server bootstrap, auth setup, or credential onboarding: read `docs/workflow/mcp-auth-bootstrap.md`.
- BEFORE changing Zerodha auth, broker session restore, quote-stream behavior, or broker readiness: read `docs/workflow/zerodha-broker-control-plane.md`.
- BEFORE changing the local Codex sidecar, `codex login` expectations, AI runtime validation, or runtime readiness semantics: read `docs/workflow/codex-runtime-control-plane.md`.
- BEFORE changing repo boundaries, ownership, or where a rule should live: read `docs/operations/workflow-setup-responsibility-map.md`.
- BEFORE starting new governance, feature, or enhancement planning: read `docs/workflow/repo-governance.md`.
- BEFORE deciding under technical uncertainty or recommending a dependency, protocol, or API change: read `docs/workflow/research-validation-loop.md`.
- BEFORE changing Overview, Health, Paper Trading, Configuration, operator visibility, stage status surfacing, or runtime truth display: read `docs/workflow/operator-dashboard-control-plane.md`.
- BEFORE browser testing, UI validation, or diagnosing state mismatches between UI and backend: read `docs/workflow/browser-testing-control-plane.md`.
- BEFORE changing discovery logic, research continuation, candidate lifecycle, or model routing for the paper-trading loop: read `docs/workflow/paper-trading-loop-control-plane.md`.
- BEFORE changing branching, review, or verification expectations: read `docs/workflow/git-governance-control-plane.md`.
- BEFORE closing a meaningful session or routing durable keep/remove/fix/improve learnings: read `docs/workflow/introspection-control-plane.md`.
- BEFORE changing autonomous paper-trading posture or allowing autonomous entries: read `docs/workflow/autonomous-paper-entry-go-live-checklist.md`.
- BEFORE making a material architecture decision: read `docs/reference/MISSION.md`, `docs/reference/REPO-SCOPE.md`, and `ROADMAP.md`, then capture the decision under `docs/adrs/`.

## Repo Rules

- Keep repo-local workflow rules in `docs/workflow/`; do not duplicate workspace governance docs.
- Keep architecture and product intent in repo docs, not in issue templates.
- When a new ADR or workflow doc supersedes an older local note, update the older note with an explicit pointer.
- Do not use Notion as a task board for this repo; execution tracking remains in Linear.
- Do not add long procedural text here; add or update the owning doc and keep this file compressed.
