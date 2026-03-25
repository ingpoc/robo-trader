# ADR 0004: Paper-Trading Learning Loop Before Trade Automation

## Status

Accepted

## Date

2026-03-23

## Context

Robo Trader's mission is paper-trading-first until execution, risk, and monitoring behavior are trustworthy.

The repo already had:

- bounded research, decision, and review artifacts
- persistent paper-trading accounts and trades
- a learning service and strategy-evolution substrate

But it did not yet close the loop between:

1. what the system researched
2. what it actually traded
3. what outcome followed
4. what future research should do differently

Without that loop, the system can generate research, but it cannot honestly claim that it is improving from paper-trading evidence day by day.

## Decision

Add a stateful paper-trading learning loop that:

- persists research packets as reusable memory
- evaluates closed paper trades against the most recent prior research for that symbol
- stores explicit lessons and improvement actions
- feeds the accumulated learning summary back into future research prompts

This loop is intentionally paper-trading-scoped. It is not a license for unattended live trading.

## Why

- Improvement should come from measured outcomes, not prompt folklore.
- Research should remember what failed and what worked for the same symbol or setup.
- The operator should be able to inspect the system's current learning state.
- Automation trust should be earned from closed-loop paper results before any claim of live-trading readiness.

## Consequences

Positive:

- Research becomes stateful across sessions.
- Closed trades create durable lessons.
- Future research can explicitly adapt to prior losses, weak-conviction wins, and stale-data failures.

Negative:

- The first iteration uses deterministic outcome heuristics, not a full causal attribution engine.
- Symbol-level and account-level lessons are stronger than strategy-family attribution for now.

## Follow-On Work

1. Attach research memory to decision packets and executed trades more explicitly.
2. Promote the learning summary into review and strategy-evolution flows.
3. Add replay and benchmark evaluation so research changes are tested before becoming automation policy.
4. Keep live trading blocked until quote freshness, execution gating, and learning evidence are all trustworthy.
