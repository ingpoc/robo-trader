# Autonomous Paper Trader Run Artifact

- Timestamp: `2026-03-29T17:50:39+0530`
- Mode: `diagnostic`
- Scope: `off-hours availability audit`

## Question

What should still be available outside market hours and is not?

## Checks Run

- In-process FastAPI `TestClient` matrix against:
  - `/api/paper-trading/accounts`
  - `/api/paper-trading/runtime/validate-ai`
  - `/api/paper-trading/accounts/paper_swing_main/operator-snapshot`
  - `/api/paper-trading/accounts/paper_swing_main/operator-incidents`
  - `/api/paper-trading/accounts/paper_swing_main/positions`
  - `/api/paper-trading/accounts/paper_swing_main/positions/health`
  - `/api/paper-trading/accounts/paper_swing_main/learning/readiness`
  - `/api/paper-trading/accounts/paper_swing_main/runs/history`
  - `/api/paper-trading/accounts/paper_swing_main/retrospectives/latest`

## Result

- Available now (`200`):
  - `validate-ai`
  - `operator-snapshot`
  - `operator-incidents`
  - `positions`
  - `positions-health`
  - `learning-readiness`
  - `runs/history`
  - `retrospectives/latest`
- Not available but should still be:
  - `/api/paper-trading/accounts`
  - current failure: `500`
  - error: `Live market data is unavailable for one or more open positions. Refusing to synthesize entry-price marks.`

## Interpretation

- Sunday/off-hours correctly explains absent fresh quote streaming.
- That should not break basic account discovery.
- The current fail-loud contract is too broad at the account-list boundary.
- Direct per-account read surfaces remain usable, so the main regression is top-level account enumeration/navigation.

## Next Fix Target

- Decouple `/api/paper-trading/accounts` from quote-dependent position hydration while preserving fail-loud behavior for price-truth surfaces.
