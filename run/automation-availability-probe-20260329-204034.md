# Automation Availability Probe

- Run timestamp: 2026-03-29T20:40:11+0530
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
| Backend control plane | unavailable | transient dependency failure | `curl http://127.0.0.1:8000/api/health` failed with `curl: (7) Failed to connect to 127.0.0.1 port 8000` |
| Broker auth | unavailable | deterministic persisted-state gap | `kite_sessions` in `state/robo_trader.db` is empty, so no active Zerodha broker session is persisted for operator use |
| Quote stream | unavailable | transient dependency failure | live quote-stream health cannot be refreshed because the backend control plane is down and no operator readiness route is reachable |
| Market data / live quote cache | unavailable | fail-loud dependency block | `real_time_quotes` is stale: latest visible marks were last updated at `2026-03-27T12:03:49+00:00`, about `183991s` old, far beyond the 300-second freshness gate |
| Paper account | available | deterministic read path | `paper_trading_accounts` still contains active account `paper_swing_main` with `current_balance=100000.0`, `buying_power=100000.0`, `is_active=1` |
| Operator snapshot | unavailable | transient dependency failure | route exists in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2132) but is unreachable while the backend is offline |
| Operator incidents | unavailable | transient dependency failure | route exists in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2184) but depends on the unreachable operator snapshot path |
| Positions truth surface | partially available | fail-loud dependency block | store-backed `paper_trades` and `paper_positions` remain readable, but live mark truth is unavailable because the quote cache is stale and the API surface is down |
| Positions health | unavailable | transient dependency failure plus stale-data gate | health is normally assembled through operator snapshot; current `paper_positions.last_price_update` values remain from `2025-12-26`, so even after backend recovery freshness would still block truthful health |
| Run history | available | deterministic read path | `manual_run_audit` remains readable in `state/robo_trader.db` |
| Learning readiness | available | deterministic read path | storage still shows `0` closed trades, one retrospective, and one promotable improvement in `watch`; the evidence window remains incomplete |
| Decision / proposal paths | unavailable | justified skip due transport failure | proposal route exists in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2742), but a live call would only reproduce backend transport failure |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- the backend control plane is not listening on `localhost:8000`
- live quote-stream health cannot be refreshed through the operator backend
- operator snapshot, incidents, positions health, and proposal surfaces are unreachable through the control plane

Deterministic policy gates still in force:

- autonomous paper entries remain `NO-GO` because repo posture is still `operator_confirmed_execution`
- the live market-data freshness gate still fails loud because quote cache timestamps are about 184k seconds stale
- learning readiness is still below the required evidence window because there are `0` closed trades
- no mutation was executed; the probe remained read-only

## Snapshot, Incidents, Positions, Runs

- Current operator snapshot and incident routes are unavailable because the backend control plane is down.
- Store-backed paper trades still show three open positions:
  - `trade_a22a25e1` / `RELIANCE` / quantity `5` / status `open`
  - `trade_d8378a2e` / `TCS` / quantity `5` / status `open`
  - `trade_101b8405` / `HDFC` / quantity `5` / status `open`
- `paper_positions` remains stale and still reflects entry-price marks only:
  - `HDFC` / qty `5` / `current_price=2750.0` / `last_price_update=2025-12-26T17:26:16.858557+00:00`
  - `RELIANCE` / qty `5` / `current_price=2650.0` / `last_price_update=2025-12-26T17:26:12.505635+00:00`
  - `TCS` / qty `5` / `current_price=3450.0` / `last_price_update=2025-12-26T17:26:14.437326+00:00`
- Recent run history remains available in `manual_run_audit`. Latest rows are:
  - `paper_trading.research` / `ready` / `2026-03-29T06:53:05.363961+00:00` / fresh external web evidence unavailable
  - `paper_trading.research` / `ready` / `2026-03-29T06:51:01.303359+00:00` / fresh external web evidence unavailable
  - `paper_trading.research` / `ready` / `2026-03-29T06:48:49.523578+00:00` / fresh external web evidence unavailable
  - `paper_trading.research` / `ready` / `2026-03-29T06:44:26.204376+00:00` / fresh external web evidence unavailable
  - earlier `decision_review` and `daily_review` runs also show AI runtime blocked states at `2026-03-29T06:41:55Z`
- Latest retrospective remains `retro_2553b5390a1849e0`, with `fix_json` still including `Quote freshness remains stale`.
- Promotable improvements still contain `impr_8915a1a28de84551` / `Improve external evidence speed` / decision `watch`.

## Dry-Run Proposal Path

- Skipped this run.
- Justification: with `localhost:8000` unreachable, a dry-run proposal call would only reproduce transport failure and would not add new evidence about deterministic proposal gating.
- The deeper deterministic gate remains visible anyway from storage: quote freshness is far outside the allowed threshold, so a truthful proposal path should still fail loud after backend recovery until live quotes are refreshed.

## Result

- Overall availability: `blocked`
- Top blocker: backend control-plane reachability is still down on `localhost:8000`, which prevents live verification of operator snapshot, incidents, positions health, and proposal surfaces.
- Next blockers after backend recovery: missing persisted broker session and severely stale live quotes.
