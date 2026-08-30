# DKS Query Performance

## Problem

Current queries validate quality policy under exclusive advisory locks and then
open a second session for shared query locks. Nonblocking contention fails as
`quality policy lock unavailable`, causing repeated retrieval loss and expensive
fallback exploration.

## Required Behavior

- A query verifies source, authority, privacy, ranking-policy, and projection
  identities before returning citations.
- The normal path uses shared query protection and persisted validated activation
  identity without acquiring an exclusive repair lock.
- Stale, missing, or invalid policy evidence may escalate to one bounded exclusive
  repair path.
- Contention uses bounded retry with jitter and returns an explicit availability
  class when exhausted.
- Partial lock acquisition is released deterministically and lock-stage duration
  is observable without exposing PostgreSQL identity.
- Query fallback never bypasses policy validation, source authority, privacy
  sequence, or projection integrity.

## Measurement

Measure cold and warm p50/p95, contention failures, retry count, fallback count,
policy-repair count, and citation-quality equivalence. The first target is warm
p95 below 10 seconds with zero opaque lock failures and unchanged exact citation
regressions.

## Non-Goals

Do not add a new store, daemon, hosted retrieval service, weaker policy, or
unverified cache.
