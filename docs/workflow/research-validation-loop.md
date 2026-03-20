# Research And Validation Loop

Use this when technical uncertainty affects architecture, dependencies, broker integrations, external APIs, or safety-critical behavior.

## Goal

Replace assumptions with inspected evidence.

## Default Order

1. Inspect the current repo state.
2. Inspect repo-local docs and current configuration.
3. Use repo-grounded tools when helpful:
   - DeepWiki for repository structure or dependency questions
   - Context7 for framework or library documentation
4. Use primary external docs for broker, API, protocol, or platform behavior.
5. Use broader web search only after primary sources or when corroboration is needed.

## Confidence Labels

- `High`: directly verified in code or official docs
- `Medium`: partly verified, some inference remains
- `Low`: limited evidence or conflicting signals

## Output Standard

When validation matters, distinguish:

- what is known
- what is inferred
- what remains unverified

## Failure Standard

- Missing access to a required verification source is a blocker, not a detail to route around.
- If the chosen operating model depends on a tool, auth state, or source of truth, fix that dependency before proceeding whenever feasible.
- Do not recommend a fallback architecture just because the primary integration is currently broken.

## Tool Guidance

### Use repo inspection first

If the answer is visible in code, tests, config, or repo docs, inspect that before reaching for outside sources.

### Use primary docs for protocol truth

For broker APIs, framework behavior, security guidance, or third-party integrations, prefer official documentation.

### Use MCP tools to reduce uncertainty

Use the provided MCP surfaces to get grounded answers:

- repo and code understanding tools for codebase truth
- docs tools for library or platform truth
- browser and network tools for runtime truth
- Linear and Notion tools only when the task depends on those systems of record

## Why This Exists

This repo mixes AI workflows, market integrations, persistent state, and UI control surfaces. The cost of a wrong assumption is often operational, not cosmetic.
