# ADR-0001: Mission Cut To A Paper-Trading Core

- Status: Accepted
- Date: 2026-03-17
- Linear: https://linear.app/guru-codex-workspace/issue/CODEX-24
- Notion: https://www.notion.so/32627fc6f5d381bbb3c6dafb23c09403
- PR: Pending local changes

## Context

Robo Trader had drifted into a broader “AI trading platform” shape with several mission-hostile behaviors:

- duplicate paper-trading truth across state and store layers
- synthetic success responses for execution and queue workflows
- CSV/mock fallbacks that made missing broker or queue dependencies look healthy
- duplicate or orphaned UI surfaces that did not match the routed operator console
- dark-theme and custom-style drift on top of an incomplete shadcn foundation

The repo mission is narrower:

- safer than ad hoc manual execution
- more observable than a black-box bot
- paper-trading-first until execution, risk, and monitoring are trustworthy

## Decision

Robo Trader is being cut down to a mission-first operator console with these rules:

1. Claude Agent SDK is the cognitive layer, not the source of execution truth.
2. Paper trading is the default and only product claim in active runtime paths.
3. Queue, broker, and account blockers fail loud; they do not silently downgrade to CSV, mock success, or synthetic healthy status.
4. One routed UI shell owns the operator workflow; duplicate legacy pages are removed.
5. The active UI is light-only until dark mode is deliberately designed and supported.

## Consequences

### Easier

- the runtime surface is easier to reason about
- operator-facing status is more trustworthy
- frontend routes have a clearer ownership model
- future refactors can target a smaller, more coherent product

### Harder

- some legacy workflows now return blockers instead of “best effort” results
- missing queue/broker/auth setup is surfaced immediately
- unused or aspirational features will need to be rebuilt intentionally if they return

### Risks

- parts of the repo still contain legacy state and mock/live fallbacks outside the first cut
- some inactive or lightly used screens may still carry old styling or dead code until later tranches

## Supersedes

- Any local notes or README language describing Robo Trader as a general autonomous live-trading platform.
