# Automation Availability Probe

- Run timestamp: 2026-03-29T17:43:39+0530
- Account: `paper_swing_main`
- Probe mode: `read-only`
- Trades placed: `none`
- Dry-run proposal attempted: `yes`

## Mission Posture

- Repo mission remains paper-first and truth-first.
- Autonomous paper entry posture remains `NO-GO`.
- Active execution posture remains `operator_confirmed_execution`.

## Availability Matrix

| Surface | Status | Classification | Evidence |
| --- | --- | --- | --- |
| AI runtime shell reachability | available | transient/environment-specific mismatch | `curl http://127.0.0.1:8765/health` returned `status=ready`, `authenticated=true`, `model=gpt-5.4` |
| AI runtime backend reachability | unavailable | transient dependency failure | backend `POST /api/paper-trading/runtime/validate-ai?account_id=paper_swing_main` reported `status=disconnected` with `Codex runtime is unavailable at http://127.0.0.1:8765. All connection attempts failed`; direct Python `httpx` to the same URL failed with `ConnectError('[Errno 1] Operation not permitted')` |
| Broker auth | available | ready dependency | capability check `broker_auth=ready`: `Zerodha broker session is authenticated.` |
| Quote stream | degraded | transient dependency failure | capability check `quote_stream=degraded`: `KiteTicker connection timeout - on_connect callback not received within 15s` |
| Market data / live quote cache | unavailable | transient dependency failure | capability check `market_data=blocked`: `Quote subscriptions exist but no market data has been cached.` Zerodha quote fetches failed DNS resolution for `api.kite.trade` |
| Paper account | available | ready dependency | capability check `paper_account=ready` for `paper_swing_main` |
| Operator snapshot | unavailable | fail-loud dependency block | `GET /api/paper-trading/accounts/paper_swing_main/operator-snapshot` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` |
| Operator incidents | unavailable | fail-loud dependency block | `GET /api/paper-trading/accounts/paper_swing_main/operator-incidents` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` |
| Positions truth surface | unavailable | fail-loud dependency block | `GET /api/paper-trading/accounts/paper_swing_main/positions` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` for missing `HDFC`, `RELIANCE`, `TCS` live quotes |
| Positions health | unavailable | fail-loud dependency block | `GET /api/paper-trading/accounts/paper_swing_main/positions/health` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` |
| Learning readiness | available | deterministic read path | `GET /api/paper-trading/accounts/paper_swing_main/learning/readiness` returned `closed_trade_count=0`, `queued_promotable_count=1` |
| Decision path | unavailable | transient dependency failure | `GET /api/paper-trading/accounts/paper_swing_main/decisions` returned `status=blocked` with `AI runtime is not ready for decision generation.` |
| Review path | unavailable | transient dependency failure | `GET /api/paper-trading/accounts/paper_swing_main/review` returned `status=blocked` with `AI runtime is not ready for review generation.` |
| Dry-run proposal path | unavailable | fail-loud dependency block | `POST /api/paper-trading/accounts/paper_swing_main/execution/proposal` for close of `trade_a22a25e1` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` after ~45.6s |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- backend-side Codex runtime validation cannot reach the local sidecar even though shell `curl` can
- KiteTicker never reached `on_connect` within the operator deadline
- Zerodha quote fetches cannot resolve `api.kite.trade`
- live quote cache is empty for open positions `HDFC`, `RELIANCE`, and `TCS`

Deterministic policy gates observed now:

- autonomous paper entries remain `NO-GO` because repo posture is still `operator_confirmed_execution`
- no mutation was executed; the only proposal attempt stayed dry-run and failed loud before any execution contract could become usable

## Snapshot, Incidents, Positions, Runs

- Operator snapshot and incident surfaces are currently unavailable because the repo now refuses to synthesize entry-price marks when live quotes are missing.
- Open trades still exist in the paper-trading store:
  - `trade_a22a25e1` / `RELIANCE` / status `open`
  - `trade_d8378a2e` / `TCS` / status `open`
  - `trade_101b8405` / `HDFC` / status `open`
- Recent run history is still present; the latest visible entries are research runs, including repeated `Fresh external web evidence is unavailable for this research packet.` and one blocked runtime timeout.
- Latest retrospective remains available and still flags `Quote freshness remains stale`.

## Dry-Run Proposal Evidence

- Request: close `trade_a22a25e1` on `paper_swing_main` with `dry_run=true`
- Result: `500 MARKET_DATA_LIVE_QUOTES_REQUIRED`
- Interpretation: proposal path is truth-preserving under degraded market data and does not fabricate readiness or fallback marks

## Result

- Overall availability: `blocked`
- Top blocker: live market data is unavailable for the open-position set, which now correctly blocks snapshot, incidents, positions health, and proposal truth surfaces.
