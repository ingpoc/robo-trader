# Validator References

This directory is an application-specific validation reference for Robo Trader.

Browser-testing method and evidence rules are owned by `docs/workflow/browser-testing-control-plane.md`.
Broker and runtime readiness rules are owned by:

- `docs/workflow/zerodha-broker-control-plane.md`
- `docs/workflow/codex-runtime-control-plane.md`

## Runtime And API Reference

Useful validation endpoints for this repo:

- `GET /api/health`
- `GET /api/auth/zerodha/status`
- `POST /api/paper-trading/runtime/validate-ai?account_id=paper_swing_main`
- `POST /api/paper-trading/accounts/paper_swing_main/operator/refresh-readiness`

Useful browser validation surface:

- `http://localhost:3000/system-health`

## Scope

Keep this directory focused on:

- endpoint lists used during validation
- historical or implementation notes that should stay close to tests

Do not move workflow doctrine, browser method, or readiness policy into this directory.
