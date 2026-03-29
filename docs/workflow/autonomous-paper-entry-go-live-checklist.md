# Autonomous Paper Entry Go-Live Checklist

Use this workflow before allowing Robo Trader to place autonomous paper-trading
entries without an operator manually approving each trade.

Default state: `NO-GO`

The current repo posture remains `operator_confirmed_execution`. Autonomous
paper entries stay disabled until this checklist is passed with evidence.

## Goal

Promote autonomy only when the system has proved that it can:

- observe truthfully
- decide with sufficient evidence
- refuse bad actions consistently

This checklist governs autonomous paper entries only. It does not authorize
live-money trading.

## Required Evidence Windows

Do not promote on a single good run.

Minimum evidence before a `GO` decision:

- at least 5 consecutive automation cycles during trading hours
- at least 5 consecutive dry-run proposal cycles with no false-positive entry
  approvals
- at least 10 closed paper trades with outcome lineage recorded
- at least 1 retrospective cycle that uses real trade outcomes rather than only
  infrastructure observations

If these minimum windows are not met, the result is automatically `NO-GO`.

## Gate 1: Runtime Stability

All of the following must hold across the evidence window:

- AI runtime remains ready across repeated validation checks
- quote stream remains connected and market data remains fresh during trading
  hours
- no hidden queue activity or stuck runs
- operator snapshot matches backend truth for readiness, positions, incidents,
  and learning state

Immediate `NO-GO` triggers:

- false readiness
- stale quotes presented as live
- blocked dependencies that the snapshot reports as ready
- queue work created by manual or autonomous operator flows unexpectedly

## Gate 2: Research Quality

All of the following must hold across the evidence window:

- focused research returns usable evidence within budget on most justified runs
- entry candidates clear the repo confidence and actionability thresholds for
  the right reasons
- primary-source evidence appears often enough to support entry decisions
- research packets do not routinely degrade to weak, missing, or blocked states

Immediate `NO-GO` triggers:

- frequent research timeouts that erase decision value
- entries justified only by `watch_only` or thin evidence
- confidence inflation without primary-source support

## Gate 3: Decision And Execution Consistency

All of the following must hold across the evidence window:

- proposal and preflight agree consistently for the same intended action
- execution remains blocked whenever freshness, research, or risk gates are weak
- dry-run cycles propose sensible paper trades and refuse weak ones
- no duplicate, contradictory, or racing actions appear

Immediate `NO-GO` triggers:

- a weak or stale entry proposal is allowed
- proposal allows while preflight denies without an explained state change
- mutation paths bypass proposal or preflight

## Gate 4: Learning Loop Maturity

All of the following must hold:

- closed paper trades are being evaluated with outcome lineage
- retrospectives are populated from real outcomes, not only operator opinion
- improvement decisions include outcome evidence or replay/benchmark evidence
- truthfulness and reliability improvements can be distinguished from strategy
  changes

Immediate `NO-GO` triggers:

- no meaningful outcome sample
- prompt or threshold changes promoted without benchmark evidence
- learning queue decisions based only on intuition

## Gate 5: Operating Posture And Kill Switch

All of the following must hold:

- the app/API advertises the active execution posture truthfully
- the backend enforces paper-only autonomous execution
- a tested kill switch or revert-to-no-trade path exists
- reverting from autonomous entries back to `operator_confirmed_execution` is
  deterministic and quick

Immediate `NO-GO` triggers:

- automation can place entries when execution posture is not explicitly allowed
- no tested downgrade path back to no-trade mode

## Decision Rule

The decision is:

- `GO` only if every gate passes and the evidence window is met
- `NO-GO` if any gate fails, any immediate trigger fires, or the evidence
  window is incomplete

When in doubt, keep autonomous entries disabled.

## Required Artifacts For A Go/No-Go Review

Every review should leave:

- a timestamped run artifact under `run/`
- the current operator snapshot summary
- dry-run proposal evidence
- learning-readiness summary
- outcome-lineage summary
- explicit `GO` or `NO-GO`
- the single highest-value blocker if the result is `NO-GO`

## Promotion Authority

Passing this checklist does not silently change the runtime posture.

A promotion from `operator_confirmed_execution` to any autonomous-entry posture
requires:

- a repo-local ADR or workflow update if the posture meaning changes
- the checklist evidence recorded in repo artifacts and durable memory
- an explicit code/config change that enables the new posture

Until then, the automation may monitor, research, review, propose, evaluate,
and govern learning, but it must not place autonomous paper entries.
