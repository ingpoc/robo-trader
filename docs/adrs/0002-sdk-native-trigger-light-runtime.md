# ADR-0002: SDK-Native, Trigger-Light Runtime

- Status: Accepted
- Date: 2026-03-18
- Linear: https://linear.app/guru-codex-workspace/issue/CODEX-24
- Notion: https://www.notion.so/32627fc6f5d381bbb3c6dafb23c09403
- PR: Pending local changes

## Context

Robo Trader had accumulated two overlapping runtime ideas:

- an in-app scheduler and scheduler-management product surface
- Claude Agent SDK-based reasoning flows for discovery, decisions, and review

The scheduler surface created product drift:

- Configuration exposed background-task management that operators do not need
- Paper Trading still carried legacy discovery trigger endpoints that bypassed the newer artifact flow
- System Health had to explain scheduler internals that were not part of the operator's real job

The repo mission is narrower:

- safer than ad hoc manual execution
- more observable than a black-box bot
- paper-trading-first until execution, risk, and monitoring are trustworthy

Primary documentation supports Claude Agent SDK for:

- agent loops
- subagents
- structured outputs
- hooks
- permissions
- sessions

It does not establish a native cron/scheduler product surface that should replace runtime triggering inside Robo Trader.

## Decision

Robo Trader adopts a trigger-light runtime model:

1. Claude Agent SDK remains the cognitive layer for discovery, decisioning, exit review, and daily review.
2. The product no longer exposes scheduler management as a first-class operator feature.
3. Manual and external triggers are the supported ways to start agent runs.
4. Paper Trading owns explicit run entrypoints for discovery, decision review, exit check, and daily review.
5. Configuration is limited to agent-runtime defaults and global limits, not scheduler administration.

## Consequences

### Easier

- the operator surface is smaller and more truthful
- Paper Trading becomes the clear home for manual agent runs
- System Health can focus on runtime truth instead of scheduler internals

### Harder

- external cron or other trigger infrastructure must exist outside the app if unattended runs are desired
- some older queue/scheduler internals may remain in the codebase until later cleanup tranches

### Risks

- internal scheduler-related services may still exist behind the product surface until deeper refactors remove them
- some older docs and helper modules may still mention scheduler concepts and need later cleanup

## Supersedes

- Any local notes or UI text that frame scheduler management as part of the normal Robo Trader operator workflow.
