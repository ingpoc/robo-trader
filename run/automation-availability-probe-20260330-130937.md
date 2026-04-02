# Automation Availability Probe

- Run timestamp: 2026-03-30T13:09:37+0530
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
| AI runtime | unavailable | fail-loud dependency block | `POST /api/paper-trading/runtime/validate-ai?account_id=paper_swing_main` returned `ai_runtime.status=disconnected`, `authenticated=false`, and `Codex runtime is unavailable at http://127.0.0.1:8765. All connection attempts failed` at `2026-03-30T07:38:59.603422+00:00`; direct `GET http://127.0.0.1:8765/health` also failed earlier in this probe |
| Backend control plane | available | degraded dependency | `GET /api/health` returned `200 healthy` at `2026-03-30T07:39:39.706854+00:00`, but only after about `4.24s`; the paper-trading endpoints answered during this run, so the backend is reachable but sluggish |
| Broker auth | available | ready dependency | both `validate-ai` and `GET /api/paper-trading/capabilities?account_id=paper_swing_main` reported `broker_auth.status=ready` with `Zerodha broker session is authenticated`; the latest `kite_sessions` query returned no recent rows, so the live control plane is the stronger source of truth here |
| Quote stream | unavailable | fail-loud dependency block | capabilities and `/api/health` both reported `quote_stream.status=degraded`, `connected=false`, `active_symbols=5`, and `last_error=KiteTicker connection timeout - on_connect callback not received within 15s` |
| Market data | unavailable | fail-loud dependency block | capabilities and `/api/health` both reported `market_data.status=blocked` with `cached_symbols=0`; persisted `real_time_quotes` rows are stale from `2026-03-27T12:03:49+00:00` and do not cover the open-position set truthfully (`HDFC`, `RELIANCE`, `TCS`) |
| Operator readiness refresh | unavailable | deterministic policy gate | `POST /api/paper-trading/accounts/paper_swing_main/operator/refresh-readiness` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` with `missing_symbols=[HDFC, RELIANCE, TCS]`; the route is implemented in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2154) and currently refuses to synthesize a snapshot without truthful live marks |
| Operator snapshot | unavailable | deterministic policy gate | `GET /api/paper-trading/accounts/paper_swing_main/operator-snapshot` returned the same `500 MARKET_DATA_LIVE_QUOTES_REQUIRED`; snapshot assembly lives in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2130) |
| Operator incidents | unavailable | deterministic policy gate | `GET /api/paper-trading/accounts/paper_swing_main/operator-incidents` returned the same live-quote refusal because incidents are derived from the snapshot path, not from an independent incident store |
| Positions health | partially available | fail-loud dependency block | open trades and stale stored marks are readable from sqlite, but truthful live position health is unavailable because the snapshot path refuses to operate without live quotes for `HDFC`, `RELIANCE`, and `TCS` |
| Run history | available | deterministic read path | `GET /api/paper-trading/accounts/paper_swing_main/runs/history?limit=5` returned `200` with recent research runs from `2026-03-29`; those entries show the system was previously fully ready, then later degraded, so the current blocker is a regression rather than an unconfigured surface |
| Automation run surface | available with errors | deterministic read path | `GET /api/paper-trading/accounts/paper_swing_main/automation/runs` returned `200` with one recorded run, `autorun_improvement_eval_cycle_20260330054216_9cd2a0`, which failed on application error `'ImprovementReport' object has no attribute 'get'` rather than on transport failure |
| Decision / proposal path | unavailable | deterministic gate plus upstream dependency block | capabilities currently report `automation_allowed=false` with blockers `AI runtime is not ready.` and `Quote subscriptions exist but no market data has been cached.`; the proposal and preflight endpoints remain defined in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2742) but were not called because they would only restate already-proven blockers |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- the Codex runtime is unreachable on `127.0.0.1:8765`
- the quote stream is configured but not receiving ticks
- the live quote cache has `cached_symbols=0` and stale persisted rows only
- the backend is reachable but slower than expected on `/api/health`

Deterministic policy gates observed now:

- operator snapshot, incident synthesis, and readiness refresh refuse to proceed without truthful live quotes for open positions
- automation and proposal paths remain blocked by capability gating while runtime and market-data checks fail
- autonomous paper entry remains `NO-GO`
- no mutation was executed; the probe remained read-only

## Snapshot, Incidents, Positions, Runs

- Current operator snapshot is unavailable because the control plane truthfully refused to synthesize entry-price marks without live quotes.
- Current operator incidents are likewise unavailable because they derive from the same snapshot path.
- Store-backed position truth still shows three open paper trades:
  - `trade_a22a25e1` / `RELIANCE` / qty `5` / status `open`
  - `trade_d8378a2e` / `TCS` / qty `5` / status `open`
  - `trade_101b8405` / `HDFC` / qty `5` / status `open`
- Store-backed `paper_positions` remains stale:
  - `HDFC` / `current_price=2750.0` / `last_price_update=2025-12-26T17:26:16.858557+00:00`
  - `RELIANCE` / `current_price=2650.0` / `last_price_update=2025-12-26T17:26:12.505635+00:00`
  - `TCS` / `current_price=3450.0` / `last_price_update=2025-12-26T17:26:14.437326+00:00`
- Recent manual run history remains available and proves the system had a truthful ready state on `2026-03-29T06:53:05Z`, with runtime, quote stream, market data, and broker all previously `ready`.
- The newest automation run surface is also reachable, and its latest failure is application-level: [`run/improvement_eval_cycle-20260330-054432.md`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/run/improvement_eval_cycle-20260330-054432.md) records `'ImprovementReport' object has no attribute 'get'`.

## Dry-Run Proposal Path

- Skipped this run.
- Justification: `validate-ai`, `/api/health`, capabilities, snapshot, and readiness refresh already proved both hard blockers: runtime unreachability and missing live quotes for open positions. A proposal or preflight call would only restate `automation_allowed=false` and would not add higher-value evidence.

## Result

- Overall availability: `blocked`
- Top blocker: truthful operator state cannot be synthesized because the readiness boundary is broken on both required inputs: the Codex runtime is unreachable on `127.0.0.1:8765`, and live quotes are missing for the open-position set.
