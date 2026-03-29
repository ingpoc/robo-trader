# Robo Trader Mission

Robo Trader exists to turn a retail trading workflow into a trustworthy AI-assisted operating system for paper trading first, and only later for broader execution claims if the system proves it is safe, observable, and reliable.

The mission is not to make an AI that "usually picks good trades." The mission is to build a trading system in which an autonomous agent can observe, research, recommend, and operate within explicit deterministic boundaries without hiding uncertainty, stale data, degraded dependencies, or risk.

## Product Goal

Build a production-grade paper-trading platform where the autonomous agent can act as the primary operator while the system remains:

- safer than ad hoc human trading
- more transparent than a black-box bot
- more deterministic than a prompt-only workflow
- more auditable than a typical retail trading stack

## What Production-Grade Means In This Repo

Production-grade for Robo Trader means:

- the agent sees truthful state across account, positions, market data, AI artifacts, and system health
- every important action runs through deterministic backend rules, persistence, and risk gates
- stale, weak, or missing evidence causes explicit downgrade or refusal, not bluffing
- every AI run is bounded by schema, timeout, cost, and observability constraints
- every decision, recommendation, and action is inspectable after the fact
- the system improves from outcomes through measured promotion, not silent prompt drift

Production-grade in this repo currently means manual and operator-confirmed paper trading. It does not mean unattended live-money trading.

## Autonomy Model

The autonomous agent is allowed to:

- inspect operator state
- validate runtime and market readiness
- run discovery, research, decision review, and daily review
- surface incidents, blockers, and degraded dependencies
- propose trade actions and operational fixes
- operate through approved control-plane tools and backend APIs
- learn from outcomes through governed introspection and replay-backed improvement loops

The autonomous agent is not allowed to bypass:

- deterministic execution and persistence logic
- backend-enforced risk limits
- freshness requirements for market data and evidence
- audit trails
- promotion rules for strategy, prompt, or policy changes

## Deterministic Boundary

AI may assist with research, synthesis, ranking, and operator guidance.

Deterministic code must remain the source of truth for:

- account state
- trade and position state
- risk checks
- order and position mutations
- market-data freshness enforcement
- capability and readiness gating
- audit logging
- policy promotion

The system must prefer blocking over pretending readiness.

## Core Invariants

The repo should always move toward these invariants:

- state shown to the agent and UI matches backend and database truth
- no position-management guidance is produced from stale marks
- no research packet is promoted when evidence quality is below threshold
- no autonomy path creates hidden background work or token-consuming loops
- every material run has a bounded timeout, explicit status, and run metadata
- every improvement has evidence, owner, and promotion discipline

## Default Operating Posture

The default operating posture is:

- paper trading first
- manual and operator-confirmed runs
- explicit blocked/degraded/ready states
- WebMCP and backend APIs as the agent control plane
- no hidden schedulers or silent automation

This repo should make the autonomous agent more capable only when that capability also makes the system more truthful, more reversible, and easier to audit.

## What This Repo Is Optimizing For

- truthful operator state
- transparent AI reasoning and artifact lineage
- deterministic execution boundaries
- bounded manual and autonomous workflows
- strong paper-trading reliability before any live-trading expansion
- a UI and WebMCP surface that act as an operator console, not just a chart surface

## Non-Goals

This repo is not optimizing for:

- maximum trade frequency
- impressive but weakly grounded AI narration
- autonomy that outruns system observability
- live-trading claims before paper-trading reliability is proven
- hidden fallback behavior presented as success

## Mission Test

Any meaningful change in this repo should be judged against this question:

Does this make Robo Trader more trustworthy for an autonomous agent operating a paper-trading account under deterministic controls?

If the change makes the agent more powerful but the system less truthful, less bounded, or less auditable, it is not mission-aligned.
