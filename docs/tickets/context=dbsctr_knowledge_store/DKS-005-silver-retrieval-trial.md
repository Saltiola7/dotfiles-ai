---
schema_version: 1
id: DKS-005
slug: silver-retrieval-trial
context: dbsctr_knowledge_store
title: Run the frozen silver retrieval trial
kind: epic
state: done
priority: high
points: 8
depends_on:
  - DKS-004
relations:
  - dbsctr_knowledge_store:DKS-006
owns:
  - dot_local/bin/executable_dksctl
  - tests/test_dbsctr_knowledge_store.py
  - docs/specs/dbsctr_knowledge_store/README.md
  - docs/specs/dbsctr_knowledge_store/benchmark-silver-v1.schema.json
  - docs/specs/dbsctr_knowledge_store/benchmark-silver-runner-v1.schema.json
  - docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.generator-prompt.txt
  - docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.review-prompt.txt
  - docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.silver.json
  - docs/specs/dbsctr_knowledge_store/benchmarks/DKS-005.aggregate.json
  - docs/tickets/context=dbsctr_knowledge_store/DKS-005-silver-retrieval-trial.md
reads:
  - DKS-004 offline runner and benchmark protocol schemas
  - active immutable corpus, projections, model manifests, and baseline policy
  - committed silver questions, source citations, execution evidence, and aggregate
parallel_safe: false
validation:
  - pre-execution silver question, citation, generator, and reviewer identity
  - four-cell quality, citation, determinism, latency, and resource gates
  - exact aggregate recomputation, seven-day trial activation, expiry, and rollback
created: 2026-08-21
updated: 2026-08-24
completed: 2026-08-24
commits:
  - 995cfb9
  - 6d7c2bd
  - a4eec79
  - 3c48b54
  - 201b096
  - d28d6d6
  - 5a81814
  - d3d3a4c
  - 0dbd84b
  - edf2515
  - 9f5f509
  - ef3a605
  - d5df601
  - 88a6bc8
  - 0ef9ba0
  - d4d5e61
  - e956fdb
  - 3edcecd
  - 2c5a90d
jira_publications: []
migration: "6"
---

## Outcome

AI-generated silver relevance evidence determines whether code vectors,
reranking, both, or neither merit a reversible seven-day local trial. Silver
evidence can never permanently replace `dks-rrf-v1`.

## Context

DKS-004 delivered immutable projection identities and benchmark validation but no
four-cell executor. The silver protocol is separate from human v2 evidence and
uses only committed Git at the frozen revision as hosted-model input.

## Scope

Freeze a committed silver question/citation set before candidate execution, run
the four retrieval cells locally, and activate an eligible candidate only as a
seven-day trial with automatic baseline restoration.

## Acceptance Criteria

- Before candidate execution, a hosted AI generates at least 100 questions across
  the five fixed strata from committed Git at
  `45096bb03891e9771a891d53f92b23863ae08a3e` only, with source citations that are
  resolved independently of retrieval candidates.
- The committed suite records `evidence_class: silver`, exact provider/model and
  prompt identities, two independent alignment reviews, and no private authority,
  transcript, credential, uncommitted, or candidate-result content.
- The local runner executes baseline, code, reranker, and code-plus-reranker
  twice at depth 100, reports top-20/top-50 prefixes, derives citations from
  frozen projection chunks, and HMAC-binds continuously sampled local evidence.
- Every eligible candidate meets the existing nDCG, bootstrap, stratum, Recall@50,
  deterministic ranking, p95, memory-pressure, peak-memory, and swap gates, with
  no per-query exact-citation regression.
- Reranker calibration at the 4096-token operational limit proves one-document
  forwards remain below 20 GiB MPS allocation and 24 GiB total footprint with
  normal memory pressure and no swap growth before the complete matrix executes.
- `activate-silver-trial` accepts only a recomputed eligible aggregate, records a
  fixed 604800-second expiry, and cannot create a permanent policy.
- Expiry, source/privacy/model identity drift, or an unavailable required quality
  service atomically restores `dks-rrf-v1` before another query uses the trial.
- Manual `rollback-quality`, projection refresh, and trial replacement retain
  their existing fail-closed baseline behavior.

## Risks

Hosted-input leakage, citation fabrication, tuning on silver labels, incomplete
strata, corpus drift, or reused evidence invalidates the benchmark. Silver labels
are exploratory evidence, not human ground truth or permanent activation authority.
Full-sequence logits and decoder caching previously exhausted unified memory;
last-token-only, cache-free, single-document scoring is now a hard precondition.

## Evidence

The complete 100-query matrix is bound to aggregate SHA-256
`837271160639c5148d75984eba53c068fc20fd049e732824be080fd84c3c5b0b` and
private evidence SHA-256
`9786d288536c2ac58bef86b4a13ddf2df0c706d9293fa220c10cc3954d6bd4a5`.
Code vectors regressed relative nDCG@10 by 32.89%, had 29 exact-citation
regressions, and were nondeterministic. Reranking improved relative nDCG@10 by
66.76%, but had one exact-citation regression and a 59.74-second warm p95. Both
candidates also observed 63.95 GiB peak host memory, warning kernel pressure,
and 2.86 GB swap growth.
Neither candidate was eligible, so `dks-rrf-v1` remained active and no silver
trial was created.

## Review

The suite passed two independent fixed-commit reviews before execution. Their
committed hashes are provenance declarations, not cryptographic provider
attestations; fixed-source citation validation and explicit operator activation
remain authoritative. The local four-cell matrix completed with warning kernel
pressure and failed candidate gates without activation. The trial, expiry, drift,
service-failure, and manual rollback paths remain available for a future eligible
silver aggregate; permanent quality activation remains denied.
