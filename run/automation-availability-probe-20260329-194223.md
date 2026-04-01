# Automation Availability Probe

- Run timestamp: 2026-03-29T19:42:23+0530
- Account: `paper_swing_main`
- Probe mode: `read-only`
- Trades placed: `none`
- Dry-run proposal attempted: `no`

## Mission Posture

- Repo mission remains paper-first and truth-first.
- Autonomous paper entry posture remains `NO-GO`.
- Active execution posture remains `operator_confirmed_execution`.

## Availability Matrix

| Surface | Status | Classification | Evidence |
| --- | --- | --- | --- |
| AI runtime shell reachability | available | ready dependency | `curl http://127.0.0.1:8765/health` returned `status=ready`, `authenticated=true`, `model=gpt-5.4`, `reasoning_profile=low` |
| Backend control plane | unavailable | transient dependency failure | `curl http://127.0.0.1:8000/health` failed with `curl: (7) Failed to connect`, and `lsof -nP -iTCP:8000 -sTCP:LISTEN` showed no listener |
| Broker auth | unavailable | deterministic persisted-state gap | `.env` still contains Zerodha credentials and token material, but `kite_sessions` has no rows, so no active broker session is persisted for operator use |
| Quote stream | unavailable | transient dependency failure | live quote-stream health cannot be refreshed because the backend control plane is down and no quote-stream route is reachable |
| Market data / live quote cache | unavailable | fail-loud dependency block | `real_time_quotes` only contains stale marks: `HDFCBANK`, `RELIANCE`, and `TCS` were last updated at `2026-03-27T12:03:49+00:00`, about `180465s` old, far beyond the 300s freshness gate in [`account_manager.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/services/paper_trading/account_manager.py#L17) |
| Paper account | available | deterministic read path | `paper_trading_accounts` still contains active account `paper_swing_main` with `current_balance=100000.0`, `buying_power=100000.0`, `is_active=1` |
| Operator snapshot | unavailable | transient dependency failure | the route exists in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2132) but cannot be reached while the backend is offline |
| Operator incidents | unavailable | transient dependency failure | the route exists in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2184) but depends on the unreachable operator snapshot path |
| Positions truth surface | partially available | fail-loud dependency block | `paper_trades` and `paper_positions` remain readable from storage, but position truth is not live because quotes are stale and the API surface is offline |
| Positions health | unavailable | transient dependency failure | the backend health route is down, and stored `paper_positions.last_price_update` values are still frozen at `2025-12-26`, so no live health judgment is trustworthy |
| Run history | available | deterministic read path | `manual_run_audit` contains recent run rows through `2026-03-29T06:53:57Z`, including research, decision review, and daily review outcomes |
| Learning readiness | partially available | deterministic read path with policy gate | storage shows `closed_trade_count=0`, one queued retrospective, and one promotable improvement, so learning state is inspectable but still below the go-live evidence window |
| Decision path | unavailable | transient dependency failure | current decision routes are unreachable because the backend is down; persisted run history shows earlier blocked runs with `AI runtime is not ready for decision generation.` before later successful review runs |
| Review path | unavailable | transient dependency failure | current review routes are unreachable because the backend is down; persisted run history shows earlier blocked runs with `AI runtime is not ready for review generation.` before later successful review runs |
| Dry-run proposal path | unavailable | transient dependency failure | not attempted this run because `localhost:8000` is unreachable; the deterministic proposal wrapper still exists in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2742), but a call would only re-prove transport failure |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- the backend control plane is not listening on `localhost:8000`
- live quote-stream health cannot be refreshed through the operator backend
- the persisted live-quote cache for the open-position set is stale by about 50 hours

Deterministic policy gates still in force:

- autonomous paper entries remain `NO-GO` because repo posture is still `operator_confirmed_execution`
- the 300-second market-data freshness gate remains active and should keep blocking snapshot, positions, and proposal truth surfaces until live quotes recover
- learning readiness remains below the required evidence window because there are `0` closed trades
- no mutation was executed; the probe remained read-only

## Snapshot, Incidents, Positions, Runs

- Current operator snapshot and incident routes are unavailable because the backend control plane is down.
- Store-backed position truth still shows three open paper trades:
  - `trade_a22a25e1` / `RELIANCE` / quantity `5` / status `open`
  - `trade_d8378a2e` / `TCS` / quantity `5` / status `open`
  - `trade_101b8405` / `HDFC` / quantity `5` / status `open`
- `paper_positions` is also stale and still reflects entry-price marks only, with `last_price_update` values from `2025-12-26T17:26:12Z` through `2025-12-26T17:26:16Z`.
- Recent run history remains available in `manual_run_audit`. The latest rows are research runs from `2026-03-29T06:44:26Z` through `2026-03-29T06:53:57Z`, mostly `ready` but explicitly degraded by missing fresh external evidence, plus earlier blocked decision/review runtime checks at `2026-03-29T06:41:55Z`.
- Latest retrospective remains available and still records `Quote freshness remains stale` as the queued fix.
- Promotable improvements still contain one entry: `Improve external evidence speed`, currently in `watch` state.

## Dry-Run Proposal Path

- Skipped this run.
- Justification: with `localhost:8000` unreachable, a dry-run proposal call would only reproduce transport failure and would not add new evidence about deterministic proposal gating.
- The deeper deterministic market-data gate remains visible anyway from storage: live quote freshness is far outside the 300-second threshold, so proposal truth should still fail loud even after the control plane is restored.

## Result

- Overall availability: `blocked`
- Top blocker: backend control-plane reachability is down on `localhost:8000`, which prevents live verification of operator snapshot, incidents, positions health, decision, review, and proposal surfaces; stale live quotes and the missing persisted broker session remain the next blockers after backend recovery.
