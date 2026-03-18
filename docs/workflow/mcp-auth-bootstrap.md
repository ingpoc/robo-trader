# MCP And Auth Bootstrap

This repo depends on local tooling and credentials that must be explicit.

## Current Repo Surfaces

- Codex MCP server definitions live in `~/.codex/config.toml`.
- Governance-critical remote MCP servers are:
  - `notion` -> `https://mcp.notion.com/mcp`
  - `linear` -> `https://mcp.linear.app/mcp`
- `.env.example` defines repo runtime credentials such as broker and research integrations.
- Claude auth is expected to come from the local Claude CLI session, not from an `ANTHROPIC_API_KEY` in `.env.example`.

## Baseline Bootstrap

1. Copy `.env.example` to `.env`.
2. Fill in required repo runtime credentials for the mode you need.
3. Authenticate Claude CLI with `claude auth`.
4. Ensure Codex has the required governance MCP servers configured:
   - `codex mcp add notion --url https://mcp.notion.com/mcp`
   - `codex mcp add linear --url https://mcp.linear.app/mcp`
5. Complete OAuth for both remote MCP servers:
   - `codex mcp login notion`
   - `codex mcp login linear`
6. Start a new Codex session after adding or authenticating a new MCP server so the tool surface is reloaded.
7. Start the backend and frontend using the repo's documented commands.
8. Verify health before depending on UI or automation results.

## Credentials And Auth Expectations

### Claude

- Source: Claude CLI auth session
- Do not add duplicate Anthropic key instructions to repo docs unless the runtime truly changes

### Notion

- Source: Codex remote MCP OAuth session
- Do not try to bootstrap Notion governance work through raw API keys in repo config

### Linear

- Source: Codex remote MCP OAuth session
- Do not use personal API keys as a substitute for the Codex MCP login path when the goal is Codex-side project management

### Zerodha

- Source: `.env`
- Required for real broker integration and OAuth callback flow

### Perplexity

- Source: `.env`
- Required for research and analysis paths that depend on those services

## Verification Rules

- Prefer a direct MCP tool call over CLI metadata when checking whether Notion or Linear is usable in-session.
- Do not rely on `codex mcp list` as the only auth signal; loaded tool availability is the meaningful check.
- If a newly configured MCP server does not appear in the current session, start a new Codex session before declaring setup broken.

## Failure Modes

- Missing Claude auth: AI features may degrade or fail; do not assume local auth exists on another machine.
- Missing Notion or Linear OAuth in Codex: governance workflows are blocked; fix the MCP auth path before claiming project management is ready.
- Missing Zerodha credentials: broker-backed flows remain unavailable; paper trading should remain the default path.
- Missing MCP server setup: local developer automation may not behave like CI or another engineer's machine.

## Change Rule

If MCP or auth behavior changes:

- update this file
- update `.env.example` if credential expectations changed
- link the corresponding Linear issue and durable note if the change affects multiple workflows
