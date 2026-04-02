# Autonomous Paper Trader Run

- Run timestamp: 2026-03-29T17:25:50+0530
- Account: `paper_swing_main`
- Execution mode: `operator_confirmed_execution`
- Autonomous paper-entry posture: `NO-GO`
- Dashboard mode: `backend_only`
- Readiness forced refresh: `yes`

## Readiness Summary

- Forced operator-readiness refresh returned a healthy capability snapshot.
- AI runtime is now `ready`.
- Quote stream is now `ready`.
- Market data is now `ready`.
- Broker auth remains `ready`.
- Automation eligibility in the capability snapshot is `true`, but autonomous entries remain `NO-GO` because runtime posture is still `operator_confirmed_execution` and the go-live checklist has not been promoted.

## Actions Taken

1. Revalidated local Codex runtime reachability from both `curl` and Python `httpx`.
2. Revalidated external Zerodha reachability from Python `httpx`.
3. Re-ran the paper-trading operator control plane in-process via FastAPI `TestClient`.
4. Confirmed live marks for all 3 open positions.
5. Re-ran one dry-run close proposal using the fixed preflight logic.

## Positions Observed

- `RELIANCE`: live mark `1348.1`, unrealized P&L `-6509.5`, trade `trade_a22a25e1`
- `TCS`: live mark `2389.8`, unrealized P&L `-5301.0`, trade `trade_d8378a2e`
- `HDFC`: live mark `756.2`, unrealized P&L `-9969.0`, trade `trade_101b8405`

## Trades Executed

- None

## Trades Proposed But Blocked

- Dry-run target: close `HDFC` trade `trade_101b8405`
- Proposal outcome: `allowed=false`
- Blocking reason:
  - `HDFC does not have a recent high-confidence decision packet authorizing this mutation.`

## Dry-Run Proposal Evidence

- Recovery artifact: `/tmp/autonomous-paper-trader-recovery.json`
- Proposal evidence:
  - `freshness.status=fresh`
  - `risk_checks.trade_open=true`
  - `risk_checks.quote_fresh=true`
  - `risk_checks.queue_clean=true`
  - `decision_gate.required=true`
  - `decision_gate.passed=false`

## Learning Updates

- No learning-state mutation was made.
- No improvement decision was made.

## Introspection Summary

Outcome
- Intended: resolve the previously observed runtime and quote blockers, then verify that the deterministic mutation gate behaves truthfully.
- Actual: runtime reachability and live quote readiness recovered, the preflight truthfulness bug remained fixed, and the dry-run mutation path now blocks only for the expected missing decision packet.

Keep
- Deterministic execution gating remained truthful once runtime and market data recovered. | evidence: [fresh quote in proposal payload, `trade_open=true`, only decision gate blocked action] | owner: `session-only`

Fix
- None newly identified in this recovery pass.

Improve
- Separate transient environment outages from repo-local bugs during automation closeout so the next run can retry recovered paths instead of assuming the old blockers still hold. | evidence: [current readiness fully recovered while earlier run captured blocked runtime and stale marks] | owner: `session-only`

Next
- Run or inspect a fresh decision-review/exit-check cycle for `RELIANCE`, `TCS`, and `HDFC` so close actions can be evaluated against actual decision packets rather than platform blockers.
