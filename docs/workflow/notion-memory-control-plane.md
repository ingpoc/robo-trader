# Notion Memory Control Plane

Notion is the durable memory system of record for Robo Trader.

## Put In Notion

- Architecture decisions that should outlive one coding session
- Research notes
- Incident notes
- Tradeoff analyses
- Superseded-document pointers

## Do Not Put In Notion

- Active issue status
- Sprint execution tracking
- Branch-by-branch work logs that belong in Linear or GitHub

## Minimum Durable-Memory Fields

For each durable note or database entry, capture:

- title
- memory type
- scope
- repo
- status
- confidence
- summary
- source link
- linked Linear issue
- linked PR or branch when available
- validation date
- supersedes or superseded-by field when relevant

## Supersession Rule

When a new ADR, architecture note, or research page replaces older guidance:

1. update the older artifact immediately
2. mark it as superseded
3. point to the new canonical artifact

Do not leave parallel documents to imply authority.

## Local Fallback

If Notion is unavailable and a decision cannot wait:

- capture the decision locally under `docs/adrs/`
- include a `Notion sync pending` note
- sync it into Notion once access is restored

This fallback is for continuity, not for creating a second permanent source of truth.
