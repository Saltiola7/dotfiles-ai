# DKS Query Performance

## Problem

Current queries validate quality policy under exclusive advisory locks and then
open a second session for shared query locks. Nonblocking contention fails as
`quality policy lock unavailable`, causing repeated retrieval loss and expensive
fallback exploration.

## Required Behavior

- A query verifies source, authority, privacy, ranking-policy, and projection
  identities before returning citations.
- Replacement preparation uses writer serialization but does not hold an
  activation barrier while parsing, embedding, or producing derived artifacts.
- The normal path uses one shared activation barrier and one repeatable-read
  transaction without acquiring an exclusive repair lock.
- A query may serve only the prior policy-valid active projection while a writer
  prepares its replacement.
- Query-visible activation is atomic and restores `dks-rrf-v1` in the same
  transaction whenever the new projection invalidates active quality-policy
  identity.
- Stale, missing, or invalid policy evidence may escalate to one bounded exclusive
  repair path.
- Activation contention uses bounded retry and returns a sanitized explicit
  availability class when exhausted.
- Partial lock acquisition is released deterministically and lock-stage duration
  is observable without exposing PostgreSQL identity.
- Query fallback never bypasses policy validation, source authority, privacy
  sequence, or projection integrity.

## Scenarios

**Scenario: Serve the prior active projection during replacement preparation**

- Given one policy-valid active projection and a serialized writer building its replacement
- When a query starts before replacement activation
- Then the query reads the prior active projection under one shared activation barrier
- And writer preparation does not cause an opaque policy-lock failure

**Scenario: Invalidate quality policy atomically**

- Given active quality ranking bound to the current projection identity
- When replacement activation changes a bound source, authority, graph, or privacy identity
- Then the activation transaction restores `dks-rrf-v1`
- And no query can observe the new projection under the stale quality policy

**Scenario: Fail closed after bounded contention**

- Given activation or repair cannot acquire every required barrier within its bound
- When retry is exhausted
- Then retrieval reports typed retryable unavailability without citations
- And no source, database session, process, path, or raw error identity is exposed

## Lock Contract

Writer locks serialize replacement work for project, code, and authority channels.
Activation barriers protect only query-visible transitions. Every query holds
shared activation barriers in canonical project, code, authority order for one
repeatable-read transaction. Activation and policy repair use the same order
exclusively. A failed partial acquisition closes its database session and releases
every acquired lock before retry or return.

## Visual Evidence

| Concern | Decision | Review question | Canonical source | Owner/change trigger |
|---|---|---|---|---|
| Boundary | not_applicable: authority and projection boundaries are unchanged | - | DKS README Visual Evidence | Authority change |
| Interaction | required: replacement/query sequence | Can queries use prior active state while replacement work proceeds? | Required Behavior and Lock Contract | Lock or activation change |
| State | required: active projection transition | Can stale quality policy observe a new active projection? | Scenarios and Lock Contract | Policy or activation change |
| Data/trust | not_applicable: no new data movement | - | DKS README Visual Evidence | Trust-boundary change |
| Schema | not_applicable: no schema change | - | Existing DKS schema contract | Schema change |
| Dependency/deployment | not_applicable: no new service or dependency | - | Existing DKS deployment contract | Runtime dependency change |
| Quantitative | required: paired contention measurements | Does the change remove opaque lock failures without citation regression? | Measurement | Acceptance-target change |

```mermaid
sequenceDiagram
    accTitle: DKS replacement and query concurrency
    accDescr: A writer prepares replacement data under a writer lock without blocking queries. A query reads the prior active projection under shared activation barriers. The writer briefly takes exclusive activation barriers, restores baseline ranking if identity changes invalidate quality policy, and atomically activates the replacement.
    participant W as Reconcile writer
    participant A as Activation barrier
    participant Q as Query
    participant P as Active projection
    W->>W: Build replacement under writer lock
    Q->>A: Acquire shared barriers
    Q->>P: Verify policy and read prior active projection
    Q-->>A: Release shared barriers
    W->>A: Acquire exclusive barriers
    W->>P: Restore baseline if required and activate replacement
    W-->>A: Release exclusive barriers
```

**Text Equivalent:** Reconciliation serializes replacement preparation without
holding query activation barriers. Queries hold shared barriers while verifying
and reading the prior active projection. The writer takes exclusive barriers only
for the final transition, restores baseline ranking in that transaction if the
new identity invalidates quality policy, activates the replacement atomically,
and releases the barriers.

## Measurement

Measure cold and warm p50/p95, contention failures, retry count, fallback count,
policy-repair count, and citation-quality equivalence. The first target is warm
p95 below 10 seconds with zero opaque lock failures and unchanged exact citation
regressions.

## Non-Goals

Do not add a new store, daemon, hosted retrieval service, weaker policy, or
unverified cache.
