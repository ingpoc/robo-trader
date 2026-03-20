# Repo Governance Workflow

Use this workflow before major feature, enhancement, architecture, or governance changes in Robo Trader.

## Workflow

1. Define the user, problem, and desired outcome.
2. Inspect the current repo state before proposing direction.
3. List assumptions and unknowns explicitly.
4. Verify technical or product uncertainty against code, config, repo docs, and primary documentation when needed.
5. Decide whether the change is repo-local only or also needs a broader workspace or external-system update.
6. Create or confirm the Linear issue if the work is actionable.
7. Create or update a Notion page if the work creates durable memory:
   - ADR
   - research note
   - architecture note
   - incident note
8. Implement in the repo.
9. Sync Linear status and Notion summary when the work lands or materially changes direction.
10. If the change supersedes an older local note, ADR, or guidance page, update the older artifact to point to the governing replacement.

## Pushback Requirement

Do not silently follow a direction that is:

- architecturally unsound
- inconsistent with the current codebase
- contradicted by verified documentation
- weaker than a clearly better alternative

In those cases:

1. say what is wrong
2. explain why
3. propose the stronger direction

## Confidence Standard

- If the answer is code-retrievable, inspect the code.
- If the answer is repo-history or architecture-retrievable, inspect repo docs and current configuration.
- If the answer depends on an external API, product, or broker behavior, verify with primary docs before treating it as fact.
- State confidence explicitly when the difference between known and inferred changes the recommendation.

## Decision Threshold For ADRs

Create or update a local ADR when any of the following are true:

- the change alters the trading safety model
- the change introduces or removes a core integration
- the change changes the operator workflow in a durable way
- the change reverses or supersedes a previous architecture direction
