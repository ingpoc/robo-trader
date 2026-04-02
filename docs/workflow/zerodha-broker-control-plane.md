# Zerodha Broker Control Plane

Use this document when changing Zerodha auth, broker session restore, quote-stream behavior, or broker-backed readiness.

## Owns

- Zerodha OAuth login, callback, status, and logout behavior
- token expiry and session-restore truth
- account-context expectations for broker-backed paper trading
- quote-stream and live market-data readiness semantics
- failure classification for user re-auth vs repo/runtime fixes

## Primary Surfaces

- `src/services/zerodha_oauth_service.py`
- `src/web/routes/zerodha_auth.py`
- `src/services/kite_connect_service.py`
- `src/services/trading_capability_service.py`
- `src/web/routes/paper_trading.py`

## Broker Auth Truth

- Broker auth is not ready because an env token exists.
- Expired env tokens are expired input, not active broker state.
- `GET /api/auth/zerodha/status` is the direct auth surface for whether a valid stored Zerodha session exists.
- `POST /api/paper-trading/runtime/validate-ai?account_id=...` and `POST /api/paper-trading/accounts/{account_id}/operator/refresh-readiness` are the execution truth surfaces for whether broker auth is usable in the live paper-trading path.

## OAuth Flow

1. `GET /api/auth/zerodha/login` returns the authorization URL when auth is required.
2. Zerodha redirects to `GET /api/auth/zerodha/callback`.
3. The callback must exchange the request token, persist the fresh token, bind the live broker session, and refresh market-data state.
4. `GET /api/auth/zerodha/status` must show `authenticated: true` before broker-backed actions are considered ready.

## Callback Ports

- Development redirect default: `http://localhost:8010/api/auth/zerodha/callback`
- Docker redirect default: `http://robo-trader-app:8000/api/auth/zerodha/callback`
- Production redirect placeholder: update `src/services/zerodha_oauth_service.py` before claiming production support
- A temporary listener on `8010` is acceptable only to receive the browser callback when the development redirect is already configured that way
- Do not silently change redirect expectations in code, `.env`, and operator instructions independently
- If the browser callback is handled by a temporary listener on `8010`, treat the long-lived main backend on `8000` as stale until it has explicitly rebound its in-memory broker and quote-stream services to the fresh stored token.
- Do not claim the stack is ready just because the callback listener succeeded. Broker auth must be valid in the main backend process that serves the dashboard.

## Account Context

- Broker-backed flows must resolve account context from `PAPER_TRADING_ACCOUNT_ID`, `ZERODHA_ACCOUNT_ID`, or `ZERODHA_USER_ID`.
- Missing account context is a readiness blocker even when Zerodha auth itself succeeds.

## Quote-Stream Truth

- Broker auth alone is insufficient for readiness.
- Quote-stream readiness requires a live KiteTicker connection plus fresh cached ticks for active subscriptions.
- Market-data readiness is blocked when subscriptions exist but the cache is empty or stale.
- Operator truth surfaces must fail loud on invalid auth, disconnected quote stream, or stale live marks.

## Failure Classification

User-action-required:

- expired or missing Zerodha login
- interactive OAuth or 2FA needed
- account is valid but the user has not completed the browser callback

Code-or-runtime-fix-required:

- redirect URL mismatch
- token restore accepts expired credentials as ready
- callback succeeds but the live broker session is not rebound
- quote stream is disconnected or live marks are not refreshing
- the temporary callback listener refreshes stored auth but the main backend serving the dashboard is still running an old in-memory broker session

## Main Backend Rebind Rule

- When development OAuth completes on `8010`, verify readiness from the main dashboard backend on `8000`, not from the callback listener.
- Required truth surfaces after callback:
  - `GET /api/auth/zerodha/status` on `8000` shows `authenticated: true`
  - `GET /api/health` on `8000` shows quote stream `ready` and market data `ready`
  - `GET /api/paper-trading/accounts/{account_id}/positions` on `8000` returns live marks, not `quote_unavailable`
- If stored auth is fresh but the main backend still reports disconnected quote stream or missing live marks, do not side-step the issue. Rebind or restart the main backend so its in-memory Kite session picks up the fresh token, then verify the three truth surfaces above before resuming operator work.

Do not route around quote-stream or broker-auth blockers and call the system ready.

## Change Rule

If Zerodha auth, callback routing, token truth, or quote-stream readiness changes:

- update this file
- update `docs/workflow/mcp-auth-bootstrap.md` only if first-run setup changed
- update autonomous trading docs only if execution posture changed
