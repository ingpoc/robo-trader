# ADR 0007: Claude-Native Research Provider Unification

## Status

Accepted

## Context

The paper-trading research flow had already been migrated from Perplexity to Claude Agent SDK web research, but other active runtime paths still depended on Perplexity-shaped services or language:

- morning paper-trading research coordinator
- evening performance insight generation
- prompt optimization service used by `ClaudeAgentService`
- user-facing transparency copy and auth bootstrap docs

This split created three problems:

1. the repo still implied that Perplexity was part of the active autonomy path
2. the prompt-optimization loop was not actually Claude-native end to end
3. the system still mixed provider-specific assumptions into active paper-trading workflows

## Decision

For active paper-trading and Claude-agent runtime flows, standardize on Claude Agent SDK as the external research provider and analysis engine.

Specifically:

- use Claude web research for morning paper-trading research batches
- use Claude tool-free synthesis for evening performance insights
- feed the prompt-optimization service from Claude web research instead of a Perplexity client
- allow Claude web research to use specialized SDK subagents through the `Task` tool
- keep any remaining `perplexity_service` registration as a compatibility alias only, not as the active provider of truth

## Consequences

### Positive

- the active research path now depends on one provider model: Claude Agent SDK
- prompt optimization is now grounded in the same research system the runtime actually uses
- docs and UI can describe the system truthfully
- the research service can leverage SDK-native capabilities like subagents and built-in web tools

### Negative

- Claude quota now directly affects more of the research surface
- some older legacy modules still retain Perplexity-specific code and naming and need separate migration or retirement

## Follow-up

1. Migrate or retire remaining legacy modules that still import `PerplexityClient`, especially older fundamental-analysis and portfolio-analysis code paths.
2. Add more deterministic eval coverage around research quality and prompt-optimization outcomes.
3. Consider SDK hooks for stricter source controls or research audit logging if the research surface expands further.
