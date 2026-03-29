# Robo Trader Roadmap

This roadmap is repo-local. It tracks implementation direction for this codebase only.

## Mission Alignment

Robo Trader is being built as a trustworthy autonomous paper-trading operator, not as an unconstrained trading bot.

The roadmap therefore optimizes for:

- truthful operator state
- deterministic execution boundaries
- bounded AI workflows
- paper-trading reliability before any live-trading expansion
- governed learning and promotion

## Current State

- Backend: FastAPI monolith with persistent state, market-data services, paper-trading services, AI artifact generation, and operator APIs.
- Frontend: React/Vite operator console with paper-trading workflows, readiness surfaces, AI transparency, and WebMCP registration for agent operation.
- Runtime posture: manual-first, request-driven, and scheduler-disabled.
- Maturity: discovery, research, decision review, and daily review are now bounded and more truthful, but external evidence latency and broader autonomous control-plane hardening still limit production-grade confidence.

## Target State

The next target state is production-grade paper trading with an autonomous agent acting as the primary operator under deterministic controls.

That means:

- the agent can observe, validate, research, review, and operate through approved APIs and WebMCP tools
- the backend remains the source of truth for state, risk, persistence, and execution gating
- stale or weak evidence causes downgrade or refusal instead of silent promotion
- the system learns from outcomes through benchmarked promotion, not silent drift

This roadmap does not treat unattended live-money trading as the current target.

## Near-Term Priorities

1. Eliminate the remaining weak links in focused research quality and latency.
2. Expand the agent control plane so the autonomous operator can validate, inspect, and repair the system directly.
3. Harden execution and risk boundaries so every mutating action remains deterministic and auditable.
4. Turn introspection and learning into a governed improvement loop tied to outcomes and replay.

## Delivery Streams

### 1. Research Reliability

- Make external evidence fetches faster, narrower, and more source-prioritized.
- Preserve fresh quote and technical context for researched symbols through bounded market-data preflight.
- Ensure research confidence reflects evidence quality, freshness, and source tier.
- Reduce degraded `watch_only` packets caused by avoidable runtime and fetch overhead.

### 2. Autonomous Control Plane

- Expand WebMCP from manual convenience tools into a real operator control plane.
- Add tools for run history, incidents, readiness validation, repair actions, and retrospective capture.
- Keep the autonomous agent operating through typed tools and backend contracts rather than DOM inference.
- Make operator state fully inspectable across positions, artifacts, incidents, and dependency health.

### 3. Deterministic Execution Boundary

- Keep paper-trading account state, risk rules, and trade mutations in deterministic backend code.
- Add stricter preflight checks before trade entry, exit, or risk edits.
- Enforce fresh quotes, valid research/decision thresholds, and idempotent action semantics.
- Separate `observe`, `propose`, and `operator-confirmed execution` modes clearly in code and UI.

### 4. Learning And Promotion

- Persist every discovery, research, decision, review, and outcome artifact with lineage.
- Link trade outcomes back to the exact artifacts and prompts that produced them.
- Use session introspection, outcome review, and replay-backed evaluation to propose improvements.
- Promote prompt, policy, and threshold changes only after measured improvement.

### 5. Platform Health

- Keep AI runtime, market-data, broker, and queue status explicit and testable.
- Improve repair and validation paths for degraded dependencies.
- Remove hidden fallback behavior that can be mistaken for success.
- Keep runtime startup token-silent and free of accidental autonomous background work.

### 6. Product Clarity

- Keep the repo narrative honest: autonomous paper-trading operations are the active target.
- Document what the agent can do, what requires operator confirmation, and what remains out of scope.
- Align repo docs, ADRs, UI labels, and API contracts with the actual operating model.

## Exit Signals For The Next Cycle

- Focused research returns fresh, high-signal packets more often and degrades only for genuinely missing external evidence.
- The autonomous agent can operate through a stable WebMCP control plane without relying on browser guesswork.
- Every mutating paper-trading action has deterministic preflight, auditability, and refusal semantics.
- Learning outputs are connected to trade outcomes and governed by replay or benchmark-based promotion.
- Repo docs, ADRs, and implementation all describe the same autonomy model and operating boundary.
