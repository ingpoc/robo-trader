# Codex Runtime Control Plane

Use this document when changing the local Codex sidecar, `codex login` expectations, AI runtime validation, or runtime readiness semantics.

## Owns

- local sidecar lifecycle for the active paper-trading runtime path
- required local Codex authentication
- runtime host, port, and startup expectations
- AI runtime validation and readiness semantics
- failure classification for sidecar reachability vs downstream capability blockers

## Primary Surfaces

- `scripts/start_codex_runtime.sh`
- `shared/codex_runtime/`
- `src/auth/ai_runtime_auth.py`
- `src/services/trading_capability_service.py`
- `src/web/routes/paper_trading.py`

## Startup Contract

- Start the sidecar with `./scripts/start_codex_runtime.sh`.
- Default local bind is `127.0.0.1:8765`.
- Default runtime workdir is the repo root.
- The active model defaults to `gpt-5.4`.
- The sidecar is a required dependency for the active paper-trading AI path.

## Authentication Contract

- `codex login` is required on the local machine.
- Local runtime readiness is not transferable across machines or shells by assumption.
- Do not replace the sidecar path with a different provider flow and call the active runtime unchanged.

## Readiness Truth

- Runtime is not ready unless the sidecar is reachable and runtime validation succeeds.
- `POST /api/paper-trading/runtime/validate-ai?account_id=...` is the main operator-facing truth surface.
- `GET /api/health` can show top-level runtime state, but account-scoped validation is the execution truth for the paper-trading path.
- A capability snapshot timeout is not the same failure as a sidecar timeout; surface the real blocker.

## Runtime Status Rules

- `src/auth/ai_runtime_auth.py` owns direct runtime status evaluation and freshness TTL logic.
- A recently successful validation may remain authoritative only within the configured readiness TTL.
- Runtime auth is degraded when authenticated but usage-limited.
- Runtime auth is blocked when the sidecar is unreachable, unauthenticated, or stale past the readiness TTL.

## Warmup And Timeouts

- `CODEX_RUNTIME_URL` defaults to `http://127.0.0.1:8765`.
- `AI_RUNTIME_TIMEOUT_SECONDS` controls direct runtime call timeout.
- operator readiness routes also enforce their own timeout budget; keep error reporting specific to the layer that timed out.

## Failure Classification

User-action-required:

- local `codex login` missing or expired
- sidecar depends on a local machine state the user has not completed

Code-or-runtime-fix-required:

- sidecar process not running
- wrong host or port wiring
- runtime validation reports the wrong blocker
- capability snapshot failure is misreported as a runtime failure

Do not mark AI runtime ready when reachability, authentication, or freshness is missing.

## Change Rule

If sidecar lifecycle, auth method, host or port defaults, or runtime readiness semantics change:

- update this file
- update `docs/workflow/mcp-auth-bootstrap.md` only if first-run setup changed
- update repo tests that enforce adapter and owner-doc boundaries when needed
