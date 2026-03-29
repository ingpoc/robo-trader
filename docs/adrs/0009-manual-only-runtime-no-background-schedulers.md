# ADR 0009: Manual-Only Runtime With No Background Schedulers

## Status

Accepted

## Context

The active Robo Trader product is a paper-trading-first operator console. The
repo still carried legacy scheduler and autonomous event-routing infrastructure
from earlier iterations, even though the routed UI had already removed scheduler
controls from the active product surface.

That mismatch created two problems:

1. The backend still exposed autonomous execution concepts that no longer match
   the operator-facing product.
2. Background scheduler wiring made it harder to guarantee token-silent startup
   and manual-only execution of AI-heavy flows.

## Decision

The active runtime is now explicitly manual-only:

- legacy background scheduler startup is removed from the active dependency graph
- automatic queue event routing is disabled on initialization
- legacy scheduler call sites resolve to a manual-only compatibility boundary
- configuration status reports the manual-only execution model directly

Manual execution paths remain available through explicit operator actions and
direct API calls.

## Consequences

Positive:

- app startup is token-silent by default
- autonomous scheduler state no longer misrepresents the active product
- emergency/lifecycle wiring remains stable without re-enabling background jobs
- browser and API validation can reason about a single execution model

Tradeoffs:

- legacy scheduler code still exists in the repo for compatibility and future
  cleanup, but it is no longer part of the active runtime path
- any future reintroduction of autonomous execution must be a deliberate
  architecture decision, not an accidental side effect of old wiring

## Follow-Up

- remove dead scheduler-only codepaths once references are fully retired
- update stale validation docs that still describe scheduler controls as active
- keep AI-heavy operations behind explicit operator-triggered flows
