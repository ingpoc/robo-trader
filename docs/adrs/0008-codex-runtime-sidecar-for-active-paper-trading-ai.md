# ADR 0008: Codex Runtime Sidecar For Active Paper-Trading AI

## Status

Accepted

## Context

The active paper-trading AI path had become tightly coupled to the Claude Agent SDK:

- focused research packets
- decision/review synthesis
- external market research for discovery
- feature extraction for the research ledger
- prompt optimization
- runtime readiness checks shown in the operator UI

That coupling created two problems for the current repo mission:

1. The active operator path depended on a provider-specific SDK/session model that was hard to route or optimize cleanly.
2. The repo needed a way to use subscription-backed Codex access for research-first workflows without pushing broker execution or safety gates into a coding-agent runtime.

The repo mission remains paper-trading-first, observable, and deterministic at execution boundaries.

## Decision

For the active paper-trading AI path, the repo now uses a local Codex runtime sidecar:

- location: `shared/codex_runtime/`
- binding: `127.0.0.1:8765` by default
- transport: HTTP over localhost
- implementation: TypeScript with `@openai/codex-sdk`

The Python backend remains the system-of-record orchestrator and deterministic execution layer.
It assembles context, enforces broker/risk gates, persists learning artifacts, and calls the local Codex runtime only for research-first cognition tasks.

The migrated slice includes:

- focused research packet generation
- structured research/review role execution
- batch market research for discovery and morning research
- feature extraction for research-ledger entries
- prompt optimization analysis/improvement
- provider-neutral AI runtime health for paper-trading readiness

The migrated slice does not include:

- broker execution
- quote stream maintenance
- order placement
- autonomous safety gates
- repo-wide removal of legacy Claude modules outside the active path

## Rationale

This topology was chosen because:

- the official Codex SDK is TypeScript-first
- the active app backend is Python-heavy
- a local sidecar keeps Codex session/auth/model logic out of the FastAPI process
- localhost HTTP is easier to test deterministically than a Python CLI wrapper
- the runtime boundary stays explicit, which matches the repo’s observability and safety goals

Rejected for this phase:

- Python subprocess wrapper around `codex`
- Python-to-Codex MCP as the first migration target
- pushing Codex into broker execution or safety decisions

## Consequences

Positive:

- the active paper-trading research path no longer depends directly on the Claude Agent SDK
- provider status is exposed as `ai_runtime` instead of `claude_runtime`
- focused research packets and review outputs can carry provider metadata
- discovery and prompt optimization can share one runtime boundary

Tradeoffs:

- the repo now has a small Node/TypeScript sidecar to manage
- the broader codebase still contains legacy Claude modules outside the active slice
- local operator setup must include `codex login` and a running sidecar

## Follow-Up

- keep legacy Claude modules explicitly out of scope unless they affect the active operator path
- add browser validation against the live sidecar-backed UI path
- consider a future MCP-based Codex surface only if multiple local agents need to share the runtime
