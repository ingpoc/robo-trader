# ADR 0006: Use Claude Agent SDK Web Research For Paper-Trading Research

## Status

Accepted

## Date

2026-03-24

## Context

The paper-trading research flow had been upgraded to require fresh external evidence, but the implementation still depended on Perplexity-oriented discovery artifacts and a removed Perplexity MCP path.

That created three problems:

- focused research was coupled to an integration that is no longer part of the intended runtime
- discovery and research were using different external-research operating models
- quota or tool failures in Claude-backed research could surface as hard `500` errors instead of truthful degraded operator state

The repo mission is paper-trading-first with transparent AI reasoning, not hidden fallbacks or fragile vendor-specific glue.

## Decision

Use Claude Agent SDK built-in web tools as the primary external-research path for paper-trading discovery and focused research.

Specifically:

- add a dedicated `ClaudeMarketResearchService` that uses Claude Agent SDK with `tools=["WebSearch", "WebFetch"]`
- keep final research-packet synthesis structured and tool-free
- feed discovery feature extraction from the Claude web-research output instead of Perplexity output
- store generic `external_research` / `claude_web_research` blobs in discovery memory rather than Perplexity-named payloads
- degrade to blocked or watch-only when Claude usage is exhausted or external evidence is unavailable, instead of failing with a `500`

## Why

- It aligns the active paper-trading workflow with the actual runtime dependencies.
- It reduces vendor coupling in the operator-critical path.
- It keeps fresh evidence inside the same Claude-centered reasoning stack used elsewhere in the product.
- It preserves deterministic downstream scoring and benchmark gates instead of letting web research directly decide trades.

## Consequences

Positive:

- Focused research no longer requires a Perplexity MCP path.
- Discovery and focused research now share the same external research source family.
- Research failures from Claude quota exhaustion are surfaced as truthful degraded state.
- Tool availability is explicit via `tools` plus `allowed_tools`, keeping the web-research session bounded.

Negative:

- Claude quota exhaustion now directly affects fresh external research availability.
- Discovery throughput depends on Claude web-tool latency and budget.
- Broader non-paper-trading Perplexity integrations still need their own migration plan.

## Follow-On Work

1. Migrate remaining portfolio-analysis and prompt-optimization Perplexity paths behind the same abstraction or retire them.
2. Add benchmark gates that score research quality by evidence mix and freshness, not just trade outcome.
3. Introduce programmatic Claude subagents for technical analysis and risk review once the base web-research path is stable enough to justify the extra latency.
