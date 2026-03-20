# Linear Issue Control Plane

Linear is the execution system of record for this repo.

## Required Issue Shape

Every material issue should include:

- problem statement
- affected repo scope
- desired outcome
- acceptance criteria
- constraints or risk notes
- links to durable Notion context when it exists

## Recommended Status Flow

1. `Backlog`
2. `Planned`
3. `In Progress`
4. `In Review`
5. `Done`

## Movement Rules

- Move to `In Progress` when implementation work has actually started on a branch.
- Move to `In Review` only after the issue has a reviewable branch or SHA and the required validation state is known.
- Move to `Done` only after merge and doc or memory sync are complete.

## Required Review-Readiness Update

Before or at `In Review`, add an update containing:

- branch name
- reviewable SHA
- verification state
- browser-testing mode if relevant
- blockers or follow-ups

Example:

```text
Branch: feature/paper-trading-account-reconciliation
SHA: abc1234
Verification: pytest tests/api/ passed; browser testing not run
Docs: workflow docs unchanged
Blockers: none
```

## Rules

- Do not use Notion to mirror Linear status fields.
- Do not mark work ready for review without verification state.
- Keep issues implementation-focused; long-term reasoning goes to Notion and, when architecture-shaping, to `docs/adrs/`.
