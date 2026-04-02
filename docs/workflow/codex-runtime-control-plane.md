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
- Sidecar process start and runtime readiness are separate steps.
- On startup, the sidecar should kick a minimal warmup validation automatically.
- Until that warmup succeeds, `/health` should remain degraded and must not be treated as ready.

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
- the operator-facing `validate-ai` route timeout must be larger than the forced runtime-validation timeout; do not leave the outer route at 25s while the inner validation path is allowed to run for 45s
- focused-research route timeouts must leave explicit headroom above their internal subphase budgets.
- do not tune focused research so tightly that healthy live runs fail at synthesis because the enclosing route timeout has no slack for transport and orchestration overhead.
- if valid live candidates repeatedly fail on research timeout, treat undersized synthesis or route budgets as a code/runtime issue and fix them directly instead of normalizing blocked research.
- the paper-trading manual research loop is multi-candidate by design; its enclosing route deadline must be sized for continuation across weak candidates, not just a single synthesis pass
- current live evidence says 180s is still undersized for the dark-horse loop; keep the default manual research route at 360s unless measurements show a smaller safe floor
- startup warmup should reuse the same validation path as `POST /v1/runtime/validate` instead of inventing a second readiness path
- if a manual validation arrives while warmup is in flight, the sidecar should reuse the in-flight validation work instead of starting a duplicate request

## Stage-Based Model Routing

- do not spend frontier-model tokens on routine routing or classification by default
- keep routine loop steps at `minimal` or `low` reasoning effort unless complexity justifies more
- expected defaults for the paper-trading loop:
  - `gpt-5-nano` or `gpt-5-mini` for triage, reentry classification, trigger detection, and simple bucket decisions
  - `gpt-5-mini` for discovery market-scout summarization, external research normalization, and provenance extraction
  - `gpt-5.4` for final focused-research synthesis and near-trade-ready decision synthesis
- if the runtime sidecar supports per-request model overrides, the paper-trading loop should use them instead of one global model for every stage
- if the runtime mode is `local_runtime_service` backed by a ChatGPT Codex login, compact GPT-5 variants may be rejected; in that mode, cheap stages must fall back to the configured default model and reduce spend through `minimal` or `low` reasoning instead of forcing unsupported models
- if a stage requires `web_search`, do not push reasoning effort below what the local runtime accepts; in current ChatGPT-backed local runtime mode, `web_search` with `minimal` reasoning is invalid and must be floored to `low`
- if prompt-cache keys are supported, thread them through repeated loop phases with stable prefixes; otherwise still standardize prompt prefixes for future cache locality

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
