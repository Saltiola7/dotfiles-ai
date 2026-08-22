---
schema_version: 1
id: DKS-005
slug: human-retrieval-benchmark
context: dbsctr_knowledge_store
title: Run the frozen human retrieval benchmark
kind: epic
state: blocked
priority: high
points: 8
depends_on:
  - DKS-004
relations:
  - dbsctr_knowledge_store:DKS-006
owns:
  - docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.protocol.json
  - docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.aggregate.json
  - docs/tickets/context=dbsctr_knowledge_store/DKS-005-human-retrieval-benchmark.md
reads:
  - DKS-004 offline runner and benchmark protocol schemas
  - active immutable corpus, projections, model manifests, and baseline policy
  - owner-private query, judgment, assignment, and telemetry evidence
parallel_safe: false
validation:
  - approved query/stratum pre-generation digest and judgment-freeze lineage
  - blinded duplicate, agreement, adjudication, four-cell, three-depth, quality, latency, and resource gates
  - sanitized aggregate recomputation, explicit human review, conditional activation, and rollback
created: 2026-08-21
updated: 2026-08-21
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Human-authored private relevance evidence determines whether code vectors,
reranking, both, or neither improve cited retrieval enough to replace
`dks-rrf-v1`.

## Context

DKS-004 must first deliver the non-circular protocol and immutable offline runner.
Human judgments cannot be automated or fabricated.

## Scope

Run the frozen private human assessment and publish only its bounded protocol,
digests, aggregate evidence, reviewed policy decision, and rollback result.

## Acceptance Criteria

- Before candidate generation, a human authors and approves at least 100 queries,
  declared source/use-case strata, and at least 20 queries per stratum.
- The primary assessor grades a deduplicated randomized depth-50 pool from 0-3
  with system, model, channel, score, and rank hidden. At least 20% of pairs repeat
  blindly for intra-rater agreement.
- Quadratic-weighted Cohen's kappa over repeated primary-assessor pairs reaches
  0.70 before an independent human adjudicates disagreements and judgments freeze.
- Private query text, labels, assignments, and adjudication remain owner-private
  mode `0600`; Git receives only protocol, digests, and sanitized aggregates.
- The runner measures all four systems at depths 20, 50, and 100 with three
  warmups and five concurrency-one measured runs per query.
- Every eligible candidate meets the existing nDCG, bootstrap, stratum, Recall@50,
  deterministic ranking, p95, memory-pressure, peak-memory, and swap gates, with
  no per-query exact-citation regression.
- A human reviews the sanitized result before conditional activation. Failure or
  rejection leaves `dks-rrf-v1` active; tested rollback restores it atomically.

## Risks

Assessor leakage, tuning on labels, low agreement, incomplete strata, corpus drift,
or reused evidence invalidates the benchmark. Private text and judgments never
enter Git or PostgreSQL projection content.

## Evidence

DKS-003 specified the quality thresholds but intentionally retained the baseline
because no approved human evidence exists. DKS-004 owns correction of the runner
and lineage defects; this ticket owns only human assessment and the resulting
conditional policy decision.

## Review

Blocked pending DKS-004 delivery and explicit human-authored private judgments.
