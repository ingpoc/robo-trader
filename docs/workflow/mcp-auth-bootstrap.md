# MCP And Auth Bootstrap

Use this document for machine bootstrap only.

Ongoing Zerodha behavior belongs in `docs/workflow/zerodha-broker-control-plane.md`.
Ongoing Codex runtime behavior belongs in `docs/workflow/codex-runtime-control-plane.md`.

## Owns

- initial repo auth and MCP setup
- required local credential surfaces
- first-run verification before deeper workflow work starts
- pointers to the long-lived owner docs after bootstrap is complete

## Required Surfaces

- Codex MCP server definitions live in `~/.codex/config.toml`.
- Required governance MCP servers:
  - `notion` -> `https://mcp.notion.com/mcp`
  - `linear` -> `https://mcp.linear.app/mcp`
- Repo runtime credentials live in `.env`.
- The active paper-trading AI path uses the local Codex runtime sidecar, not a direct SDK session.

## Baseline Bootstrap

1. Copy `.env.example` to `.env`.
2. Fill in required repo runtime credentials for the mode you need.
3. Authenticate Codex with `codex login`.
4. Ensure Codex has the required governance MCP servers configured:
   - `codex mcp add notion --url https://mcp.notion.com/mcp`
   - `codex mcp add linear --url https://mcp.linear.app/mcp`
5. Complete OAuth for both remote MCP servers:
   - `codex mcp login notion`
   - `codex mcp login linear`
6. Start a new Codex session after adding or authenticating a new MCP server so the tool surface is reloaded.
7. Start the local runtime sidecar with `./scripts/start_codex_runtime.sh`.
8. Start the backend and frontend with the repo's normal commands.
9. Run high-level verification before trusting UI or automation output.

## First-Run Verification

- `GET /api/health`
- `GET /api/auth/zerodha/status`
- `POST /api/paper-trading/runtime/validate-ai?account_id=paper_swing_main`

If any of these fail, fix bootstrap before diagnosing product behavior.

## Authentication Rules

- Notion source: Codex remote MCP OAuth session
- Do not try to bootstrap Notion governance work through raw API keys in repo config.
- Linear source: Codex remote MCP OAuth session
- Do not use personal API keys as a substitute for the Codex MCP login path when the goal is Codex-side project management.
- Zerodha bootstrap requires `.env` credentials plus interactive OAuth when broker-backed flows are needed.
- External research bootstrap follows the local Codex runtime path; legacy provider env vars are not the primary path.

## Hand-Off

After bootstrap:

- use `docs/workflow/zerodha-broker-control-plane.md` for broker auth, callback, quote-stream, and live market-data truth
- use `docs/workflow/codex-runtime-control-plane.md` for sidecar lifecycle, `codex login`, and runtime readiness semantics

## Verification Notes

- Prefer a direct MCP tool call over CLI metadata when checking whether Notion or Linear is usable in-session.
- Do not rely on `codex mcp list` as the only auth signal; loaded tool availability is the meaningful check.
- If a newly configured MCP server does not appear in the current session, start a new Codex session before declaring setup broken.
