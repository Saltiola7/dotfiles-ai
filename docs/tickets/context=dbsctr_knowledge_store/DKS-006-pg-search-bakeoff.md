---
schema_version: 1
id: DKS-006
slug: pg-search-bakeoff
context: dbsctr_knowledge_store
title: Compare native FTS with isolated pg_search BM25
kind: story
state: blocked
priority: medium
points: 5
depends_on:
  - DKS-005
relations: []
owns:
  - docs/specs/dbsctr_knowledge_store/experiments/DKS-006
  - docs/tickets/context=dbsctr_knowledge_store/DKS-006-pg-search-bakeoff.md
reads:
  - DKS-005 frozen judgments and sanitized immutable corpus
  - native PostgreSQL FTS query and result identities
  - official ParadeDB release, compatibility, installation, and license records
parallel_safe: true
validation:
  - disposable isolated PostgreSQL 18 fixture and pinned pg_search identity
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

## Blockers

DKS-005 must first supply frozen human judgments. Production evaluation remains
blocked until PostgreSQL 19 is GA and ParadeDB publishes an official `pg_search`
build for the exact production major.

## Acceptance Criteria

- Use a disposable network- and storage-isolated PostgreSQL 18 environment with
  pinned `pg_search` and pgvector; never use production credentials or volumes.
- Import only an approved sanitized immutable corpus and reuse DKS-005 judgments.
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

The PG18 experiment may not predict PG19 behavior. AGPL-3.0-or-later and separate
enterprise licensing require review before distribution or service use. A result
cannot override exact-citation, privacy, or production compatibility gates.

## Evidence

As of 2026-08-21, `pg_search` v0.25.3 supports PostgreSQL 15-18, declares pgvector,
requires `shared_preload_libraries = 'pg_search'` plus restart, and has no PG19
build while production uses PostgreSQL 19 Beta 3.

Official sources:

- https://github.com/paradedb/paradedb/releases/tag/v0.25.3
- https://github.com/paradedb/paradedb/blob/v0.25.3/pg_search/Cargo.toml
- https://github.com/paradedb/paradedb/blob/v0.25.3/pg_search/pg_search.control
- https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-SHARED-PRELOAD-LIBRARIES
- https://www.postgresql.org/about/news/postgresql-186-1711-1615-1519-1424-and-19-beta-3-released-3365/
