# Introspection Control Plane

Use this workflow before closing any meaningful Robo Trader session.

This control plane owns the repo-local contract for the project-specific `introspect` skill in
`.claude/skills/introspect/`.

## Goal

Turn meaningful sessions into durable, evidence-backed learning without turning closeout into
journaling or creating duplicate policy.

## When To Use

Run introspection when the session:

- changed code, docs, config, prompts, or workflow surfaces
- tested a manual operator flow end to end
- exposed a blocker, timeout, stale-data issue, or recovery path likely to recur
- created durable learning that should be routed into code, repo docs, ADRs, or Notion memory

Skip it for trivial chat, simple lookups, or sessions with no durable learning.

## Required Structure

Classify durable learnings with these lenses:

- `keep`
- `remove`
- `fix`
- `improve`

Prefer one strong item per lens over many weak ones.

Every item should include:

- evidence
- owner
- whether it should be applied now or only recorded

## Priority Standard

Prioritize by operator impact:

1. truthfulness
2. reliability
3. quality
4. speed

Examples of highest-priority issues:

- false readiness
- UI/API/DB mismatches
- hidden queue activity
- stale market data used as if it were live
- broker or AI runtime failures that are being masked

## Owner Routing

Route each durable item to exactly one owner:

- `code-now`: implementation, tests, instrumentation, runtime tuning
- `docs/workflow/`: repo-local workflow or operating contract
- `docs/adrs/`: material architecture or operator-model change
- Notion: incident memory, research notes, durable decision memory
- session-only: no durable owner needed

Use `docs/operations/workflow-setup-responsibility-map.md` when the correct owner is unclear.

## Promotion Rules

- Safe, repo-local operational fixes should be applied in the same session when practical.
- Do not turn a one-off outage into permanent workflow policy.
- Do not encode implementation bugs as process rules.
- Do not promote trading-policy, research-policy, or prompt-policy changes from one session alone.
- Trading or research strategy changes require repeated evidence, replay support, or benchmark support before promotion.

## Evidence Standard

Prefer primary repo-grounded evidence:

- test results
- API responses
- browser state
- log lines
- database queries
- inspected code paths

If evidence is weak, record the uncertainty instead of overstating the learning.

## Closeout Standard

A good session closeout should:

- state intended outcome versus actual outcome
- capture only durable learnings
- route each learning to one owner
- apply obvious safe fixes immediately when possible
- leave one highest-value next move

## Relationship To Other Control Planes

- Use `research-validation-loop.md` when the learning depends on technical uncertainty that still needs verification.
- Use `notion-memory-control-plane.md` when the outcome should become durable incident or research memory.
- Use `repo-governance.md` when the learning implies a larger workflow, feature, or architecture change.
