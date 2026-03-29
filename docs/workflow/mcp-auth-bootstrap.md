# MCP And Auth Bootstrap

This repo depends on local tooling and credentials that must be explicit.

## Current Repo Surfaces

- Codex MCP server definitions live in `~/.codex/config.toml`.
- Governance-critical remote MCP servers are:
  - `notion` -> `https://mcp.notion.com/mcp`
  - `linear` -> `https://mcp.linear.app/mcp`
- `.env.example` defines repo runtime credentials such as broker and runtime integrations.
- The active paper-trading AI path expects a local Codex runtime sidecar, not a direct Claude SDK session.

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
7. Start the local Codex runtime sidecar with `./scripts/start_codex_runtime.sh`.
8. Start the backend and frontend using the repo's documented commands.
9. Verify health before depending on UI or automation results.

## Credentials And Auth Expectations

### AI Runtime

- Active source: local Codex runtime sidecar plus `codex login`
- Do not add `ANTHROPIC_API_KEY` instructions for the active paper-trading runtime path on this branch
- Runtime health should be verified through the local sidecar at `CODEX_RUNTIME_URL`

### Notion

- Source: Codex remote MCP OAuth session
- Do not try to bootstrap Notion governance work through raw API keys in repo config

### Linear

- Source: Codex remote MCP OAuth session
- Do not use personal API keys as a substitute for the Codex MCP login path when the goal is Codex-side project management

### Zerodha

- Source: `.env`
- Required for real broker integration and OAuth callback flow
- Account context must resolve from `PAPER_TRADING_ACCOUNT_ID`, `ZERODHA_ACCOUNT_ID`, or `ZERODHA_USER_ID`

### External research providers

- Active source for paper-trading research and discovery: local Codex runtime web research
- Legacy `PERPLEXITY_API_KEYS` env vars may still exist for older modules, but they are no longer required for the primary paper-trading research path

## Verification Rules

- Prefer a direct MCP tool call over CLI metadata when checking whether Notion or Linear is usable in-session.
- Do not rely on `codex mcp list` as the only auth signal; loaded tool availability is the meaningful check.
- If a newly configured MCP server does not appear in the current session, start a new Codex session before declaring setup broken.

## Failure Modes

- Missing Codex auth or stopped sidecar: active AI features degrade or fail; do not assume local runtime auth exists on another machine.
- Missing Notion or Linear OAuth in Codex: governance workflows are blocked; fix the MCP auth path before claiming project management is ready.
- Missing Zerodha credentials: broker-backed flows remain unavailable; paper trading should remain the default path.
- Missing Zerodha account context: env tokens may load but session restore and broker-bound market-data flows can still fail.
- Missing MCP server setup: local developer automation may not behave like CI or another engineer's machine.

## Change Rule

If MCP or auth behavior changes:

- update this file
- update `.env.example` if credential expectations changed
- link the corresponding Linear issue and durable note if the change affects multiple workflows
