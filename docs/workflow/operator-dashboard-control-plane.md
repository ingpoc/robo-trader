# Operator Dashboard Control Plane

Canonical operator-surface owner doc.
Repo-local. Robo Trader.

## Control Owner

Owner for:
- dashboard tab ownership
- operator truth visibility
- canonical lane truth
- execution-posture visibility
- stage freshness and empty semantics
- discovery candidate memory and provenance visibility
- current-account obligation ordering
- anti-duplication rules across operator tabs

Should contain:
- which tab owns which truth
- what must be visible before an operator spends tokens or mutates state
- how latest research memory is surfaced on discovery candidates
- how freshness and empty states are named
- which surfaces must fail loud on stale backend or quota state
- how the active paper-trading loop and candidate lanes are surfaced

Should not contain:
- broker auth doctrine already owned by `zerodha-broker-control-plane.md`
- AI runtime readiness doctrine already owned by `codex-runtime-control-plane.md`
- browser-testing method already owned by `browser-testing-control-plane.md`
- architecture intent already owned by ADRs and reference docs

## Tab Ownership

- `Overview` -> operator summary, next action, obligation ordering, compact performance
- `Health` -> runtime identity, active lane truth, broker state, quote stream, market-data freshness, AI quota state, execution posture
- `Paper Trading` -> discovery, focused research, decision review, daily review, positions, trade history
- `Configuration` -> editable global policy, account policy, stage criteria and guardrails

Do not repeat a full readiness, runtime-truth, or posture panel outside `Health`.

## Canonical Truth

- `/api/health` is the canonical lane-truth endpoint
- operator surfaces must show backend runtime identity and active lane
- stale frontend/backend revision mismatch must render loudly before operator conclusions
- AI quota state and retry time must be visible before research actions consume budget

## Discovery Candidate Memory

- latest persisted research memory is the source of truth for candidate memory
- store research packets in the paper-trading learning database, not files
- candidates should not remain in one flat discovery list after research runs
- discovery should show only the fresh-work queue
- candidates with fresh research memory should move into explicit lifecycle lanes instead of remaining in discovery or research by default
- the visible lanes are:
  - `Fresh queue`
  - `Actionable`
  - `Keep watch`
  - `Rejected`
- stale research memory returns a candidate to the discovery queue until refreshed
- discovery candidate cards should expose:
  - `last_researched_at`
  - `last_actionability`
  - `last_thesis_confidence`
  - `last_analysis_mode`
  - `research_freshness`
- `last_researched_at` is derived from the latest persisted `generated_at`
- `research_freshness` is derived at read time, not persisted

## Provenance Visibility

- discovery and research surfaces should expose:
  - fresh primary source count
  - fresh external source count
  - market-data freshness
  - technical-context availability
  - evidence mode
- if fresh research already exists, default CTA becomes `View research`
- the analyzed watchlist should let the operator reopen stored packets without rediscovering the symbol first

## Stage Semantics

Every stage envelope must always publish:
- `status`
- `criteria`
- `considered`
- `last_generated_at`
- `freshness_state`
- `empty_reason`
- `status_reason`

Standard `empty_reason` values:
- `never_run`
- `stale`
- `blocked_by_runtime`
- `blocked_by_quota`
- `no_candidates`
- `requires_selection`

## Obligation Ordering

- existing account obligations outrank new discovery work
- `Overview` should show an `Act Now` section ordered by urgency
- open-loss review, pending exit review, and blocked mutation work appear before new-entry scouting
- `Paper Trading` should default the research stage to the next candidate that still needs fresh work, not to the first symbol that already has fresh watch-only memory
- the candidate lifecycle lanes are the carry-forward memory between sessions for `keep watch`, `rejected`, and `actionable` outcomes
- `Paper Trading` should show the active loop state:
  - current candidate
  - attempts made
  - why the last candidate moved
  - why the loop stopped

## Flat Account Truth

- A fully flat paper account is a first-class operator state, not an error case.
- After the last open position is closed:
  - `positions` must return an empty list with truthful valuation state
  - `trade history` must continue to show the realized outcomes
  - `performance` must continue to return valid realized metrics instead of `500`, null summary fields, or empty placeholders
- Operator surfaces must not require open positions in order to render truthful closed-trade performance.
- Route and UI logic must tolerate both legacy and current closed-trade payload shapes when deriving realized metrics such as loss counts, average loss, drawdown, and volatility.

## Freshness Defaults

- discovery candidate freshness: governed by current watchlist age rules
- latest focused research is `fresh` for 6 hours from `generated_at`
- research older than 6 hours is `stale` until regenerated
- when freshness cannot be computed, render `unknown` and fail loud in the UI copy

## Mechanical Enforcement

- add tests for tab ownership and non-duplication
- add tests that stage envelopes always include required fields
- add tests that discovery candidates expose latest research memory from DB
- add tests for flat-account truth after the final close:
  - `positions` returns `[]`
  - `trade history` still renders closed trades
  - `performance` still returns realized metrics without nulls or server errors
- keep feature READMEs pointer-only
- if these rules drift, update this owner doc and its tests together
