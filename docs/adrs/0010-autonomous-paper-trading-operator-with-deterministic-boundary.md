# ADR 0010: Autonomous Paper-Trading Operator With Deterministic Boundary

## Status

Accepted

## Context

Robo Trader has moved beyond a generic "AI-assisted trading platform" framing.
The repo now contains:

- a manual-first paper-trading product surface
- bounded AI artifact generation for discovery, research, decision review, and daily review
- WebMCP tools for operator-facing control
- explicit runtime, queue, and market-data health surfaces

At the same time, earlier versions of the product and repo language left a
critical question underspecified:

What is the autonomy model of this system, and where does deterministic control
end versus AI judgment begin?

Without an explicit decision, the repo risks drifting into an unsafe middle
ground where:

1. the agent appears more autonomous than the backend can safely support
2. UI and docs imply stronger autonomy than the system should exercise
3. execution and learning boundaries blur between deterministic rules and AI
   recommendations

## Decision

Robo Trader will be built as an autonomous paper-trading operator with a strict
deterministic boundary.

### The autonomous agent owns:

- operator-state inspection
- runtime and dependency validation
- discovery, focused research, decision review, and daily review
- incident surfacing and operational diagnosis
- proposal of trade and system actions
- governed introspection and improvement proposals

### Deterministic backend code owns:

- paper-trading account state
- trade and position state
- market-data freshness enforcement
- risk checks and execution preflight
- trade and position mutations
- persistence and audit trails
- readiness and capability gating
- promotion rules for prompts, policies, and strategy changes

### Default operating mode

The default active mode remains:

- paper trading
- manual and operator-confirmed execution
- request-driven runtime
- no hidden background schedulers

### Operational principle

The system must block, downgrade, or surface degraded confidence when evidence,
freshness, or dependency health is insufficient. It must not present weak or
stale outputs as trade-ready simply because an AI run completed.

## Consequences

Positive:

- autonomy is made explicit without surrendering control of risk and state to AI
- docs, WebMCP tooling, and backend behavior can align to one operating model
- future work can be judged against a stable mission boundary
- learning loops can improve agent behavior without silently altering execution
  policy

Tradeoffs:

- live-money unattended autonomy remains out of scope until paper-trading
  reliability is proven under this model
- some AI outputs will be blocked or downgraded more often, which reduces
  apparent fluency but improves trustworthiness
- additional implementation work is required in WebMCP, execution preflight,
  replay-backed learning, and observability before the target state is reached

## Follow-Up

- expand the WebMCP operator control plane to cover incidents, run history,
  readiness validation, and repair actions
- keep improving focused research quality and external evidence latency
- add explicit execution-mode distinctions such as observe, propose, and
  operator-confirmed execution
- connect session introspection and trade outcomes to governed promotion logic
