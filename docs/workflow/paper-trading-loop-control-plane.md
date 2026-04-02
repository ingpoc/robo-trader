# Paper Trading Loop Control Plane

Canonical discovery-to-research loop owner doc.
Repo-local. Robo Trader.

## Control Owner

Owner for:
- discovery posture
- dark-horse candidate definition
- discovery-to-research loop continuation
- analyzed outcome buckets
- reentry rules for `keep_watch` and `rejected`
- model-routing and token-efficiency rules for the loop
- loop introspection metrics

Should contain:
- how the paper-trading candidate loop advances
- which candidates belong in each lifecycle lane
- when analyzed names reenter active discovery
- which stages use cheap routing vs expensive synthesis
- which metrics are captured to improve discovery and research quality

Should not contain:
- runtime readiness semantics already owned by `codex-runtime-control-plane.md`
- dashboard tab ownership already owned by `operator-dashboard-control-plane.md`
- session closeout doctrine already owned by `introspection-control-plane.md`
- autonomous entry promotion rules already owned by `autonomous-paper-entry-go-live-checklist.md`

## Default Posture

- default discovery posture is `balanced`
- discovery should favor undercovered small and mid caps with stronger evidence and current regime fit
- discovery should not optimize for novelty alone
- discovery should not spend research budget broadly across speculative names

## Lifecycle Lanes

- `fresh_queue` -> candidates that still need fresh research
- `actionable` -> candidates with fresh research ready for proposal and preflight
- `keep_watch` -> candidates with fresh research that are not ready now but may reactivate later
- `rejected` -> candidates whose current setup is insufficient, blocked, or not fit for promotion

Discovery should show only the `fresh_queue`.
Previously analyzed names should not remain in the active discovery lane unless they reenter under the reentry rules.

## Session Loop Rule

- the loop continues until:
  - `1` new actionable candidate is found, or
  - the eligible queue is exhausted
- do not stop the session because one candidate becomes `keep_watch`, `rejected`, or `blocked`
- when a candidate finishes as `keep_watch`, `rejected`, or `blocked`, immediately advance to the next eligible candidate in `fresh_queue`

## Reentry Rule

`keep_watch` or `rejected` names reenter active discovery only when:
- the latest research memory is stale, or
- a fresh trigger appears:
  - earnings
  - filing
  - material news
  - guidance change
  - order win
  - price-regime change

If neither is true, keep them out of the active queue.
Do not treat trigger words already captured inside the latest fresh research packet as a new reentry event; a fresh packet must move out of active discovery until there is genuinely newer evidence or the packet goes stale.

## Dark-Horse Ranking

Before deep research, discovery ranking should include:
- market regime summary
- favored and caution sectors
- dark-horse bonus for undercovered small and mid caps with adequate liquidity
- penalties for:
  - recent rejection without a new trigger
  - repeated weak evidence
  - stale market-data context
  - repeated sector or setup failures
- promotion for:
  - fresh earnings or filing triggers
  - fresh order wins or guidance changes
  - improving relative strength or breakout context
  - sectors helped by recent regime and learning outcomes

## Research Classification

Research must explicitly classify new candidates into:
- `actionable_buy_candidate`
- `keep_watch`
- `rejected`

Research should:
- optimize for probability of passing actionability, not just novelty
- stop early when evidence is too thin
- separate screening confidence, evidence quality, thesis confidence, and trade readiness
- explain what changed when a previously analyzed name reenters

## Model Routing

Use cheaper models and lower reasoning effort for routine work:
- `gpt-5-nano` or `gpt-5-mini`, `minimal` reasoning:
  - candidate triage
  - reentry classification
  - trigger detection
  - simple bucket and state decisions
- `gpt-5-mini`, `low` reasoning:
  - discovery market scout summarization
  - external research normalization
  - evidence and provenance extraction
  - candidate ranking helpers
- `gpt-5.4`, `medium` reasoning:
  - final focused-research synthesis
  - final decision packet for near-trade-ready candidates

Keep reasoning effort at `minimal` or `low` for routine work unless the step is genuinely complex.
If the active Codex runtime is `local_runtime_service` backed by a ChatGPT login and rejects compact GPT-5 variants, cheap stages must fall back to the configured default model and keep the cost control in the reasoning profile instead.
If a cheap stage still uses `web_search`, keep reasoning at `low` when the runtime rejects `minimal` plus `web_search`.

## Token Efficiency

- split research into:
  - cheap trigger and evidence collection
  - cheap filter and classification
  - expensive synthesis only for survivors
- keep prompt prefixes stable across repeated runs
- cap context to:
  - latest research memory only
  - compact market context
  - compact sector and learning summary
  - top few fresh sources
- add prompt and source-count ceilings so weak candidates do not consume long synthesis runs

## Route-Time Budget

- the manual focused-research route timeout must leave headroom for the full loop, not just one candidate
- default route budget should be at least 360 seconds unless live evidence proves a smaller value is safe
- do not set the enclosing route deadline below the sum of the active subphase budgets plus orchestration overhead
- if the loop can advance across multiple fresh candidates, the route deadline must account for that continuation instead of normalizing `blocked_by_runtime`

## Introspection Metrics

Capture per loop session:
- candidates scanned
- research attempts
- actionable promotion rate
- keep-watch rate
- rejected and blocked rate
- top reject reasons
- sector hit rate
- evidence-quality hit rate
- model used by phase
- token and runtime cost by phase
- time to first actionable candidate

Use those metrics to:
- penalize sectors and setups with repeated weak packets
- boost trigger types that lead to actionable packets
- penalize repeated reentry without new evidence
- surface promotable threshold or ranking changes

## Mechanical Enforcement

- add tests for lane transitions
- add tests for loop continuation until actionable or queue exhaustion
- add tests for stale or event-based reentry
- add tests for stage-based model routing
- add tests for loop-summary persistence and visibility
