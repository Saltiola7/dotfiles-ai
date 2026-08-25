---
schema_version: 1
id: DKS-006
slug: pg-textsearch-bakeoff
context: dbsctr_knowledge_store
title: Compare native FTS with isolated pg_textsearch BM25
kind: story
state: blocked
priority: medium
points: 5
depends_on:
  - DKS-005
relations: []
owns:
  - docs/specs/dbsctr_knowledge_store/experiments/DKS-006
  - docs/tickets/context=dbsctr_knowledge_store/DKS-006-pg-textsearch-bakeoff.md
reads:
  - DKS-005 frozen silver evidence and sanitized immutable corpus
  - native PostgreSQL FTS query and result identities
  - official Tiger Data pg_textsearch release, compatibility, installation, and license records
parallel_safe: true
validation:
  - disposable isolated PostgreSQL 18 fixture and pinned pg_textsearch identity
  - identical-corpus native FTS and BM25 quality, latency, build-time, and storage comparison
  - production non-mutation and recommendation-only evidence
created: 2026-08-21
updated: 2026-08-21
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

A production-independent benchmark decides whether BM25 merits later PostgreSQL
19 adoption work; this ticket cannot install, configure, or route production.

## Context

DKS-005 supplied frozen silver evidence, with neither quality candidate eligible.
Production evaluation remains blocked until Tiger Data publishes official
`pg_textsearch` support and an artifact for the exact PostgreSQL 19 production
major.

## Scope

Compare native FTS and isolated BM25 on the frozen sanitized corpus, then publish
only a recommendation and destruction evidence without changing production.

## Acceptance Criteria

- Use a disposable network- and storage-isolated PostgreSQL 18 environment with
  pinned `pg_textsearch` and pgvector; never use production credentials or volumes.
- Import only an approved sanitized immutable corpus and reuse DKS-005 silver evidence.
- Compare native English FTS and BM25 on identical document/query identities using
  nDCG@10, MRR@10, Recall@50, p50/p95 latency, index build time, and storage.
- Record PostgreSQL, extension, image, SQL, corpus, query, and judgment digests.
- Keep query, judgment, and unsanitized result evidence outside Git with mode
  `0600`; publish only bounded aggregate metrics and a sanitized recommendation.
- Destroy the disposable database and volume after evidence verification and
  record destruction without claiming secure erasure of the underlying device.
- Produce a written recommendation only. No production extension, preload setting,
  restart, schema, query routing, or ranking policy changes are permitted.

## Risks

The PG18 experiment may not predict PG19 behavior. The PostgreSQL License does
not waive extension compatibility, restart, exact-citation, privacy, or production
change-control gates.

## Evidence

As of 2026-08-22, `pg_textsearch` v1.4.0 supports PostgreSQL 17-18, requires
`shared_preload_libraries = 'pg_textsearch'` plus restart, and has no official
PG19 artifact while production uses PostgreSQL 19 Beta 3. Unmerged upstream PR
460 is experimental evidence only and is not an installable release.

Official sources:

- https://github.com/timescale/pg_textsearch/releases/tag/v1.4.0
- https://github.com/timescale/pg_textsearch/blob/v1.4.0/README.md
- https://github.com/timescale/pg_textsearch/blob/v1.4.0/pg_textsearch.control
- https://github.com/timescale/pg_textsearch/pull/460
- https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-SHARED-PRELOAD-LIBRARIES
- https://www.postgresql.org/about/news/postgresql-186-1711-1615-1519-1424-and-19-beta-3-released-3365/

## Review

Blocked pending official exact-major PostgreSQL 19 `pg_textsearch` support;
DKS-005 evidence is available, and no production mutation is authorized.
