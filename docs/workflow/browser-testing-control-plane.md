# Browser Testing Control Plane

Use this workflow when browser validation matters for runtime state, authenticated flows, or end-to-end UI behavior.

## Goals

- keep browser testing reviewable
- avoid drawing product conclusions from broken tooling or bad session state
- validate UI behavior against the real backend and persisted state
- capture findings in the right system of record

## Validation Order

1. run repo-local deterministic checks first
2. run targeted API or runtime checks second
3. run browser testing only after the first two layers are green or the browser itself is the suspected failure point
4. rerun the smallest meaningful verification set after each browser-found fix

## Tool Selection

Use the lightest tool that can validate real behavior:

- `chrome-devtools` MCP for DOM inspection, console errors, and network inspection
- Comet only for exploratory flows where deterministic browser tooling is not enough
- repo-native test harnesses when the flow must become repeatable

Do not conclude that the product is broken when the browser or auth context is invalid.

## Robo Trader Standard

- Treat backend health and API correctness as prerequisites for meaningful browser testing.
- Use `tests/validator/README.md` as the application-specific reference for active UI validation endpoints and browser surfaces.
- For UI state mismatches, verify the backend response and persisted state before classifying the problem as purely frontend.

## Evidence Capture

Every meaningful browser run should record:

- browser mode used
- exact journey exercised
- visible result
- console or network failures, if any
- whether the run was blocked by auth, tooling, or data constraints

Store the outcome in:

- Linear for execution status and review evidence
- Notion only when the finding changes future governance, tool choice, or architecture

## Failure Handling

If browser testing fails because of tooling rather than product behavior:

- stop and classify the failure correctly
- fix the browser, session, auth, or backend path first
- do not report product conclusions from an invalid environment
- do not route around the failure with a weaker validation method and call the issue closed

Examples of failure that must be fixed before product conclusions:

- frontend loaded against the wrong backend
- stale auth or missing credentials invalidate the journey
- API responses and database state disagree with what the browser shows
- browser tooling cannot inspect the active page or network path
