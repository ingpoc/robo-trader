# ADR 0005: Benchmark-Gated Strategy Promotion

## Status

Accepted

## Date

2026-03-23

## Context

The paper-trading learning loop now stores research memory and post-trade lessons, but that alone is not enough to justify strategy changes.

Without a deterministic benchmark gate, the system can still:

- invent strategy proposals in review mode without proving they help
- overfit to small samples or recent anecdotes
- promote changes that reduce losses but also discard the best winners

That is not a credible path toward trustworthy automation.

## Decision

Add a benchmark-gated improvement layer that:

- derives candidate rule changes from persisted paper-trade failures and wins
- benchmarks each rule deterministically against closed paper trades plus linked research memory
- classifies each proposal as `promote`, `watch`, `reject`, or `insufficient_evidence`
- exposes the resulting report through the paper-trading API
- allows review-time strategy proposals only when they are backed by promotable benchmark results

## Why

- Strategy evolution should be evidence-backed, not free-form.
- Review outputs should not create policy drift.
- Promotion needs a visible audit trail: what rule changed, what trades it would have filtered, and whether performance improved.

## Consequences

Positive:

- The review layer is now constrained by deterministic benchmark evidence.
- Operators can inspect which proposed guardrails actually improved historical paper outcomes.
- The system has a clearer path from lesson to tested policy change.

Negative:

- The first benchmark layer only tests a small family of gating rules.
- It uses realized paper-trade outcomes, not a full market replay across all non-traded candidates.

## Follow-On Work

1. Expand benchmark coverage from entry gates into exit-management and sizing rules.
2. Connect replay-engine evidence and research-ledger signals into the same promotion report.
3. Require minimum sample sizes before any benchmark result can influence automation policy.
4. Keep live trading blocked until benchmarked improvements and fresh-market-data gates are both trustworthy.
