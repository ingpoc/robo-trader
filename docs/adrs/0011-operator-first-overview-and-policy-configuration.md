# ADR-0011: Operator-First Overview And Policy Configuration

- Status: Accepted
- Date: 2026-04-01
- Linear: Pending
- Notion: https://www.notion.so/33527fc6f5d381148560f4447e891991
- PR: Pending local changes
- Operating contract: `docs/workflow/operator-dashboard-control-plane.md`
- Notion: sync required for durable memory mirror; workflow owner remains repo-local

## Context

Robo Trader had reached a point where the active operator console and the supporting dashboard surfaces diverged:

- `Overview` still behaved like a portfolio summary page instead of an operator cockpit.
- `Configuration` mixed live runtime truth with editable settings and generic legacy knobs.
- The selected account's execution posture and risk guardrails were not exposed as an explicit account policy surface.
- The operator had to open Paper Trading to understand readiness, staleness, stage state, and mutation guardrails.

The repo mission and roadmap are narrower:

- truthful operator state
- deterministic execution boundaries
- selected-account-scoped paper-trading operation
- visible criteria and guardrails

## Decision

Robo Trader adopts an operator-first split:

1. `Overview` is a read-only operator cockpit built primarily from the selected account operator snapshot, health, and configuration-status truth.
2. `Configuration` is split into:
   - live runtime state
   - global policy
   - selected-account policy
   - stage criteria and guardrails
3. Selected-account operator policy becomes a first-class backend contract with dedicated `GET/PUT /api/paper-trading/accounts/{account_id}/policy` endpoints.
4. Operator snapshot publishes a compact `overview_summary` payload so the dashboard can render a cockpit without inventing frontend-only logic.
5. Stage envelopes remain the source of truth for visible criteria and considered items.
6. `docs/workflow/operator-dashboard-control-plane.md` owns the operator-surface rules for tab ownership, lane truth, stage memory, and anti-duplication.

## Consequences

### Easier

- the operator can assess readiness, blockers, queue state, and account posture without leaving `Overview`
- configuration editing is safer because live runtime truth is separated from editable policy
- account-specific execution posture and guardrails are explicit and inspectable

### Harder

- backend contracts now need to keep account policy and overview summary truthful
- frontend Overview and Configuration depend on richer selected-account state than before

### Risks

- if account policy evolves faster than deterministic enforcement, the UI could expose more guardrails than are currently enforced
- old dashboard helpers and mocks can drift unless tests stay aligned to operator snapshot truth

## Supersedes

- Any local UI assumptions that `Overview` is primarily a capital/performance summary.
