---
schema_version: 1
id: DKS-005
slug: silver-retrieval-trial
context: dbsctr_knowledge_store
title: Run the frozen silver retrieval trial
kind: epic
state: in_progress
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
updated: 2026-08-22
completed: null
commits: []
jira_publications: []
migration: null
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
  `0975428470e53282545676cbd3bf261a91aecb77` only, with source citations that are
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

## Evidence

DKS-003 specified the quality thresholds and retained the baseline. DKS-004
delivered evidence validation but no executor. This ticket owns the missing
executor, explicit silver lineage, bounded trial, and automatic rollback.

## Review

DKS-004 is delivered. The earlier private TSV increment remains compatible with
human v2 evidence but does not authorize this trial. Candidate execution remains
blocked until the committed silver suite is schema-valid and independently
reviewed.
