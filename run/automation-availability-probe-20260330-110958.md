# Automation Availability Probe

- Run timestamp: 2026-03-30T11:09:58+0530
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
| AI runtime reachability | unavailable | fail-loud dependency block | `/api/health` and `POST /api/paper-trading/runtime/validate-ai?account_id=paper_swing_main` both reported Codex runtime unavailable at `http://127.0.0.1:8765`; direct `GET http://127.0.0.1:8765/health` returned `curl: (7) Failed to connect` at `2026-03-30T11:09:58+0530` |
| Backend control plane | degraded | transient dependency failure | backend listener existed on `*:8000` (`python3.1` PID `1306`), `/api/health` returned `200 healthy` earlier in the run, but later `GET /api/health` timed out after 3s with `HTTP 000`; the control plane is flapping rather than cleanly down |
| Broker auth | available | transiently observed dependency | `POST /api/paper-trading/runtime/validate-ai?account_id=paper_swing_main` returned `broker_auth.status=ready` and `summary=Zerodha broker session is authenticated.` at `2026-03-30T05:39:26Z`; direct durable session rows were not visible in `kite_sessions` during this probe |
| Quote stream | unavailable | fail-loud dependency block | `/api/health` and `validate-ai` both reported `quote_stream.status=degraded`, `connected=false`, `active_symbols=5`, and no ticks; latest errors were `403 - Forbidden` and then `KiteTicker connection timeout - on_connect callback not received within 15s` |
| Market data | unavailable | fail-loud dependency block | `/api/health` and `validate-ai` both reported `market_data.status=blocked` with `cached_symbols=0`; `real_time_quotes` had stale rows only for `RELIANCE` and `TCS` at `2026-03-27T12:03:49+00:00`, and no visible row for `HDFC` |
| Operator readiness refresh | unavailable | transient dependency failure plus upstream gates | route exists at `POST /api/paper-trading/accounts/{account_id}/operator/refresh-readiness`, but this probe did not call it because runtime reachability and live quotes were already blocked and backend responsiveness was unstable |
| Operator snapshot | unavailable | deterministic policy gate | `GET /api/paper-trading/accounts/paper_swing_main/operator-snapshot` returned `500 MARKET_DATA_LIVE_QUOTES_REQUIRED` while the backend was responsive, then later timed out with `HTTP 000`; when it did answer, it refused to synthesize entry-price marks for missing symbols `HDFC`, `RELIANCE`, `TCS` |
| Operator incidents | unavailable | deterministic policy gate exposed through snapshot dependency | `GET /api/paper-trading/accounts/paper_swing_main/operator-incidents` returned the same `MARKET_DATA_LIVE_QUOTES_REQUIRED` error while the backend was serving, because incidents are derived from the snapshot path |
| Positions health | unavailable | transient dependency failure plus fail-loud data gate | route exists at `GET /api/paper-trading/accounts/{account_id}/positions/health`; by the time it was probed the backend had dropped to `curl: (7) Failed to connect`, and store-backed positions still show stale entry-price marks only |
| Run history | available | deterministic read path | `manual_run_audit` is readable in `state/robo_trader.db`; newest rows remain `paper_trading.research`, `paper_trading.decision_review`, and `paper_trading.daily_review` entries from `2026-03-29T06:41:55Z` to `2026-03-29T06:53:57Z` |
| Proposal / decision paths | unavailable | deterministic readiness gate | proposal and preflight routes exist at `POST /api/paper-trading/accounts/{account_id}/execution/proposal` and `.../execution/preflight`; current capability snapshot had `automation_allowed=false` with blockers `AI runtime is not ready.` and `Quote subscriptions exist but no market data has been cached.` |
| Automation run surface | available | deterministic read path | `GET /api/paper-trading/accounts/paper_swing_main/automation/runs` returned `200` with `count=0`; global pause is `false` and all configured job types are enabled, but runtime readiness is `blocked` |

## Deterministic Gates vs Dependency Failures

Dependency failures observed now:

- AI runtime is unreachable on `127.0.0.1:8765`
- backend `127.0.0.1:8000` is unstable: it served health and validation once, then timed out and later connection behavior changed again
- quote stream is configured but cannot establish a usable live tick channel

Deterministic policy gates still in force:

- operator snapshot and incident synthesis refuse to proceed without truthful live quotes for open positions
- execution proposal and preflight remain non-runnable in practice because quote freshness and runtime gates are currently failing
- autonomous paper entry remains `NO-GO`, and active execution posture remains `operator_confirmed_execution`
- no mutation path was executed; this probe remained read-only

## Snapshot, Incidents, Positions, Runs

- Open paper trades remain:
  - `trade_a22a25e1` / `RELIANCE` / qty `5` / status `open`
  - `trade_d8378a2e` / `TCS` / qty `5` / status `open`
  - `trade_101b8405` / `HDFC` / qty `5` / status `open`
- `paper_positions` remains stale and still reflects old store-backed marks:
  - `HDFC` / `current_price=2750.0` / `last_price_update=2025-12-26T17:26:16.858557+00:00`
  - `RELIANCE` / `current_price=2650.0` / `last_price_update=2025-12-26T17:26:12.505635+00:00`
  - `TCS` / `current_price=3450.0` / `last_price_update=2025-12-26T17:26:14.437326+00:00`
- `queue_tasks` has no active backlog; only `completed=633` was present.
- Latest retrospective remains `retro_2553b5390a1849e0` with fix item `Quote freshness remains stale`.
- Latest promotable improvement remains `impr_8915a1a28de84551` / `Improve external evidence speed` / decision `watch`.

## Dry-Run Proposal Path

- Skipped this run.
- Justification: `validate-ai` already established `automation_allowed=false` because the AI runtime is unreachable and no market data has been cached. A proposal or preflight call would only restate those blockers and would not add higher-value evidence while the backend itself is flapping.

## Result

- Overall availability: `blocked`
- Top blocker: readiness core is broken on both sides of the deterministic boundary: the Codex runtime is unreachable on `127.0.0.1:8765`, and the live quote path has zero cached symbols for the open-position set, so truthful operator state cannot be synthesized.
