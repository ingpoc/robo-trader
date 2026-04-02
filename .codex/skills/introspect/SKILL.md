---
name: introspect
description: Use at the end of any meaningful Robo Trader session to capture durable keep/remove/fix/improve learnings, prioritize operator truthfulness and runtime reliability, and route each item to the correct owner surface.
---

# Introspect

## Overview

Use this skill before the final response after meaningful Robo Trader work. It turns a session into a compact operator-grade retrospective instead of narrative journaling.

This skill is repo-specific. It favors trading truthfulness, runtime reliability, deterministic behavior, and clear routing over generic productivity advice.

The core question is mandatory:

- Based on this workflow, what information, visibility, or defaults should have been available at the start so the session would not waste tokens on debugging or rediscovering context the user had to supply?

## Use When

- code, docs, config, prompts, or workflow surfaces changed
- a manual operator flow was tested end to end
- a blocker, timeout, stale-data issue, or recovery exposed a recurring weakness
- a better next improvement became clear during the session
- durable learning should be routed into code, repo docs, ADRs, or Notion memory

Skip it for trivial chat, small lookups, or sessions with no durable learning.

## Required Inputs

- intended outcome
- actual outcome
- evidence observed in the session
- changed files or runtime surfaces
- friction encountered and how it was resolved
- what missing start-of-session information forced avoidable debugging, re-checking, or user correction
- next recommended move

Evidence must be concrete when available:
- test result
- API response
- browser state
- log line
- DB query
- inspected code path

## Lenses

Classify durable learnings into at most one strong item per lens:

- `keep`: what worked and should remain unchanged
- `remove`: what is redundant, misleading, or not pulling its weight
- `fix`: what is broken, stale, noisy, or causing avoidable delay
- `improve`: what would make the next run clearer, faster, or more reliable

## Priority Order

Rank items by operator impact, not convenience:

1. `P0 truthfulness`: UI/API/DB mismatches, false readiness, hidden failures, unsafe trading state
2. `P1 reliability`: timeouts, flaky runtime paths, broker/session instability, queue leaks
3. `P2 quality`: weak research packets, poor decision framing, missing evidence, weak observability
4. `P3 speed`: extra clicks, redundant prompts, unnecessary manual steps, polish

Do not let a `P3` improvement displace a `P0` or `P1` fix.

## Workflow

1. Summarize the session outcome in 2-4 concrete lines.
2. Answer the core question explicitly:
   - what should have been visible, preloaded, or enforced at the start
   - why its absence wasted time or tokens
   - what exact change would prevent the same friction next time
3. Extract only durable learnings.
4. Classify them with `keep/remove/fix/improve`.
5. Attach concrete evidence to each item.
6. Assign one owner to each item.
7. If the safe owner is obvious, apply the change now instead of leaving a note.
8. Keep the closeout compact.

## Owner Routing

Route each item to exactly one owner:

- `code-now`: implementation bug, truthfulness fix, timeout tuning, instrumentation, test gap
- `repo-workflow`: repo-local operating contract under `docs/workflow/`
- `adr`: material architecture or operator-model change under `docs/adrs/`
- `notion-memory`: durable incident, research note, tradeoff analysis, or decision memory
- `session-only`: useful note with no durable owner
- `global-skill`: only if the learning is clearly cross-project, not Robo Trader-specific

Use these repo rules while routing:
- repo-local workflow guidance belongs in `docs/workflow/`
- architecture direction belongs in `docs/adrs/`
- durable incident/research memory belongs in Notion
- do not duplicate the same rule in multiple owners

## Promotion Rules

- Promote operational fixes immediately when evidence is strong and scope is local.
- Do not promote a one-off outage into permanent workflow policy.
- Do not turn an implementation bug into a process rule.
- Do not promote trading-policy, prompt-policy, or research-policy changes from one session alone.
- Trading or research strategy changes require repeated evidence, replay support, or benchmark support before promotion.

## Output Format

Use this compact structure:

```md
Outcome
- Intended:
- Actual:

Start Gap
- [missing starting info / visibility / default] | friction: [...] | prevent-next-time: [...] | owner: [...]

Keep
- [item] | evidence: [...] | owner: [...]

Remove
- [item] | evidence: [...] | owner: [...]

Fix
- [item] | priority: P0/P1/P2/P3 | evidence: [...] | owner: [...]

Improve
- [item] | evidence: [...] | owner: [...]

Next
- [single highest-value next move]
```

If a lens has no meaningful item, omit it.

`Start Gap` is required whenever the session involved debugging, re-validation, stale runtime discovery, repeated user correction, or any avoidable token spend caused by missing initial context.

## Robo Trader-Specific Checks

Always ask whether the session changed or exposed any of these:

- AI runtime truthfulness
- broker auth/session integrity
- quote stream freshness
- market-data freshness gating
- queue cleanliness
- discovery/research/decision/review boundedness
- WebMCP/operator tool gaps
- UI/API/DB consistency
- risk-control visibility
- start-of-session visibility gaps

If yes, prefer a `fix` item over a vague `improve` item.

## Guardrails

- Do not close with generic “could be better” statements.
- Do not record five weak items when one strong item is clear.
- Do not widen a repo-local lesson into a global baseline without cross-project evidence.
- Do not confuse trading insight with infrastructure insight; route them separately.
- Do not stop at “what broke”; state what should have been available at the start and where that truth should live.
- Do not omit the `Start Gap` section when the user had to correct missing context, stale-lane assumptions, hidden state, or undiscoverable workflow expectations.
- If nothing durable was learned, say that briefly and stop.
