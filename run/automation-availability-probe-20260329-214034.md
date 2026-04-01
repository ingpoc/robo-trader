# Automation Availability Probe

- Run timestamp: 2026-03-29T21:40:34+0530
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
| AI runtime reachability | available | ready dependency | `curl http://127.0.0.1:8765/health` returned `status=ready`, `authenticated=true`, `provider=codex`, `model=gpt-5.4`, `checked_at=2026-03-29T12:20:27.439Z` |
| Backend control plane | unavailable | transient dependency failure | `curl http://127.0.0.1:8000/health` failed with `curl: (7) Failed to connect`; `lsof -nP -iTCP:8000 -sTCP:LISTEN` showed no listener |
| Broker auth | unavailable | transient dependency failure | current broker auth cannot be live-verified with the backend offline; `kite_sessions` has no rows in `state/robo_trader.db`; last known good capability snapshot at `2026-03-29T06:53:05.363970+00:00` reported broker auth `ready` |
| Quote stream | unavailable | fail-loud dependency block | no live quote-stream surface is reachable while the backend is down; last known good capability snapshot at `2026-03-29T06:53:05.363970+00:00` reported quote stream `ready`, but that is historical only |
| Market data / live quote cache | unavailable | fail-loud dependency block | open-position quote cache is not currently trade-safe: `RELIANCE` and `TCS` are stale at `2026-03-27T12:03:49+00:00` (about `187561s` old), and `HDFC` has no `real_time_quotes` row for the open position set |
| Paper account | available | deterministic read path | `paper_trading_accounts` still contains active account `paper_swing_main` with `is_active=1` |
| Operator readiness refresh | unavailable | transient dependency failure | refresh route exists in [`src/web/routes/paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2154), but the backend control plane is not serving requests |
| Operator snapshot | unavailable | transient dependency failure | snapshot route exists in [`src/web/routes/paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2131), but there is no backend listener on `127.0.0.1:8000` |
| Operator incidents | unavailable | transient dependency failure | incidents route exists in [`src/web/routes/paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2184), but current incidents cannot be derived without the operator snapshot surface |
| Positions truth surface | partially available | fail-loud dependency block | persistent open positions are readable from `paper_trades`, but positions health is not currently trustworthy because fresh marks are stale or missing for the open symbol set |
| Run history | available | deterministic read path | `manual_run_audit` remains readable and shows recent research, decision review, and daily review history |
| Decision path | unavailable | transient dependency failure | live decision route is not reachable with the backend offline; persisted run history also records a blocked decision review with `AI runtime is not ready for decision generation.` at `2026-03-29T06:41:55.200610+00:00` |
| Review path | unavailable | transient dependency failure | live review route is not reachable with the backend offline; persisted run history also records a blocked daily review with `AI runtime is not ready for review generation.` at `2026-03-29T06:41:55.202759+00:00` |
| Dry-run proposal path | unavailable | transient dependency failure | skipped this run because `127.0.0.1:8000` is unreachable; source route exists in [`src/web/routes/paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2363), but a transport failure would not add new evidence |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- the backend control plane is still down on `127.0.0.1:8000`
- current broker auth, quote stream, operator snapshot, incidents, decision, review, and proposal surfaces cannot be live-verified without the backend
- live quote coverage for open positions is not trade-safe: two symbols are stale and one symbol is missing entirely

Deterministic policy gates still in force:

- autonomous paper entry remains `NO-GO` under the go-live checklist until evidence windows are met
- the active execution mode is still `operator_confirmed_execution` in [`src/web/routes/paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L544)
- no mutation path was executed; this probe remained read-only

## Snapshot, Incidents, Positions, Runs

- Current operator readiness refresh, snapshot, and incidents are unavailable because the backend control plane is absent.
- Persistent state still shows one active paper account and three open paper trades:
  - `trade_101b8405` / `HDFC` / status `open`
  - `trade_d8378a2e` / `TCS` / status `open`
  - `trade_a22a25e1` / `RELIANCE` / status `open`
- Queue backlog is currently clear in storage: `queue_tasks` has `0` rows in `pending`, `active`, `running`, or `queued` state.
- Recent run history remains available in `manual_run_audit`. The newest entries remain research runs from `2026-03-29T06:44:26Z` through `2026-03-29T06:53:57Z`, mostly `ready` but still marked with `Fresh external web evidence is unavailable for this research packet.`
- Latest retrospective remains available and queued with fix item `Quote freshness remains stale`.

## Dry-Run Proposal Path

- Skipped this run.
- Justification: the backend transport is down, so a dry-run proposal request would only reconfirm the same connection failure and would not produce new evidence about deterministic preflight behavior.

## Result

- Overall availability: `blocked`
- Top blocker: backend control-plane reachability is down on `127.0.0.1:8000`; even after transport recovery, stale and missing live quotes for open positions remain the next fail-loud blocker.
