# Git Governance Control Plane

This document defines the default git operating model for Robo Trader.

## Primary Judgments

1. `main` must remain releasable.
2. Material changes land through short-lived review branches, not direct pushes to `main`.
3. Branches should be issue-sized.
4. Deterministic checks come before browser testing, and review comes before merge.
5. Local hooks are guardrails, not the final merge gate.

## Branching Standard

- Prefer one Linear issue to one review branch.
- Use short-lived branches scoped to one reviewable change.
- If a branch ends up solving a different problem than the issue describes, update the issue rather than letting branch and issue drift apart.

## Merge Standard

- Prefer PR-based review into `main`.
- Prefer squash merge when it keeps `main` readable and aligned to issue-sized work.
- Do not bypass protected-branch or CI requirements just because the local branch looks correct.

## Verification Gates

### Before a Reviewable Commit

Run the fastest deterministic checks that prove the edited surface is still sane.

Examples:

- affected unit or API tests
- lint, typecheck, or compile/import validation
- targeted runtime checks for touched integrations

### Before Review

All of the following should be true:

- relevant deterministic checks are green
- required browser validation is complete for UI-critical work
- branch name and reviewable SHA are available
- issue status reflects reality

### Before Merge

All of the following should be true:

- required CI checks are green
- review blockers are resolved
- docs and durable memory are synced where required

## Failure Standard

- A failing required check is a blocker.
- Do not route around failing validation by narrowing the claim of completion unless the issue scope is explicitly changed.
- If the merge path depends on a broken tool or environment, fix it before calling the work done.
