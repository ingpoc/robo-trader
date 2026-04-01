# Automation Availability Probe

- Run timestamp: 2026-03-29T18:42:19+0530
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
| AI runtime shell reachability | available | ready dependency | `curl http://127.0.0.1:8765/health` returned `status=ready`, `authenticated=true`, `model=gpt-5.4` at `2026-03-29T12:20:27.439Z` |
| Backend control plane | unavailable | transient dependency failure | `curl http://localhost:8000/health` and `curl http://localhost:8000/api/paper-trading/capabilities?account_id=paper_swing_main` both failed with `curl: (7) Failed to connect to localhost port 8000` and `lsof -iTCP:8000 -sTCP:LISTEN` showed no listener |
| Broker auth | unavailable | transient dependency failure | broker auth could not be live-verified because the backend service is down; persisted config still contains Zerodha credentials, but `kite_sessions` currently has no active stored session row |
| Quote stream | unavailable | transient dependency failure | live stream could not be validated with the backend offline; persisted quote settings still point at `quoteStreamProvider=zerodha_kite`, but no live-control-plane evidence is reachable |
| Market data / live quote cache | unavailable | fail-loud dependency block | `real_time_quotes` only has stale marks for open symbols: `RELIANCE`, `TCS`, and `HDFCBANK` all last updated at `2026-03-27T12:03:49+00:00` (about `176910s` old, far beyond the 300s freshness threshold) |
| Paper account | available | deterministic read path | `paper_trading_accounts` still contains active account `paper_swing_main` |
| Operator snapshot | unavailable | transient dependency failure | current route is unreachable because the backend is down; source path in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L981) assembles this through backend routes that also depend on fresh live quotes |
| Operator incidents | unavailable | transient dependency failure | current route is unreachable because the backend is down; source path derives incidents from operator snapshot state rather than an independent store |
| Positions truth surface | partially available | fail-loud dependency block | open positions are readable from `paper_trades`, but the API truth surface is unavailable; current open trades remain `trade_101b8405/HDFC`, `trade_d8378a2e/TCS`, and `trade_a22a25e1/RELIANCE` |
| Positions health | unavailable | transient dependency failure | route unreachable while backend is down; when the backend was reachable earlier today this surface failed loud on missing live quotes |
| Run history | available | deterministic read path | `manual_run_audit` remains readable; recent entries include research runs with `Fresh external web evidence is unavailable for this research packet.` plus earlier runtime blocked states |
| Learning readiness | available | deterministic read path | storage shows `closed_trade_count=0`, one retrospective (`retro_2553b5390a1849e0`), and one promotable improvement already marked `watch` |
| Decision path | unavailable | transient dependency failure | current route unreachable because backend is down; recent persisted run history also shows `AI runtime is not ready for decision generation.` on earlier attempts |
| Review path | unavailable | transient dependency failure | current route unreachable because backend is down; recent persisted run history also shows `AI runtime is not ready for review generation.` on earlier attempts |
| Dry-run proposal path | unavailable | transient dependency failure | not attempted this run because `localhost:8000` is unreachable; route definition in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2363) is present, but transport failure would not add new evidence |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- the backend control plane is not listening on `localhost:8000`
- broker auth and quote-stream status cannot be live-verified while the backend is absent
- the persisted live-quote cache for the open-position set is stale by roughly 49 hours

Deterministic policy gates still in force:

- autonomous paper entries remain `NO-GO` because repo posture is still `operator_confirmed_execution`
- the proposal path is a deterministic preflight wrapper and should remain blocked when live quote freshness is weak
- no mutation was executed; the probe remained read-only

## Snapshot, Incidents, Positions, Runs

- Current operator snapshot and incidents are unavailable because the backend control plane is down.
- The store-backed position truth still shows three open paper trades:
  - `trade_101b8405` / `HDFC` / status `open`
  - `trade_d8378a2e` / `TCS` / status `open`
  - `trade_a22a25e1` / `RELIANCE` / status `open`
- Recent run history is still present in storage. The newest visible entries are research runs around `2026-03-29T06:44:26Z` to `2026-03-29T06:53:05Z`, mostly `ready` with weak external evidence, plus blocked decision/review attempts at `2026-03-29T06:41:55Z`.
- Latest retrospective remains available and still records `Quote freshness remains stale` as a fix item.

## Dry-Run Proposal Path

- Skipped this run.
- Justification: with `localhost:8000` unreachable, a dry-run proposal call would only re-prove transport failure and would not add new information about deterministic proposal gating.
- Source inspection confirms the proposal path is still implemented as a deterministic preflight wrapper in [`paper_trading.py`](/Users/gurusharan/Documents/remote-claude/active/apps/robo-trader/src/web/routes/paper_trading.py#L2363).

## Result

- Overall availability: `blocked`
- Top blocker: backend control-plane reachability is down on `localhost:8000`, which prevents live verification of broker, quote stream, snapshot, incidents, decision, review, and proposal surfaces; stale quote cache remains the next blocking dependency even after backend recovery.
