---
schema_version: 1
id: DKS-008
slug: upgrade-graphify-and-cache-extractions
context: dbsctr_knowledge_store
title: Upgrade Graphify and cache extractions
kind: task
state: in_progress
priority: high
points: 5
depends_on:
  - DKS-007
relations: []
owns:
  - docs/specs/dbsctr_knowledge_store/DKS-003.models.json
  - docs/specs/dbsctr_knowledge_store/DKS-008.plan.json
  - docs/specs/dbsctr_knowledge_store/README.md
  - docs/specs/dbsctr_knowledge_store/CHANGELOG.md
  - docs/specs/dbsctr_knowledge_store/OPERATION.md
  - docs/tickets/context=dbsctr_knowledge_store/DKS-008-upgrade-graphify-and-cache-extractions.md
  - dot_local/bin/executable_dbsctr-graphify
  - dot_local/bin/executable_dksctl
  - dot_local/bin/executable_dks-postgres-migrate.tmpl
  - dot_local/share/dbsctr-knowledge/schema.sql
  - run_onchange_after_install-dbsctr-quality-services.sh.tmpl
  - tests/test_dbsctr_knowledge_store.py
reads:
  - pinned Graphify 0.9.48 and 0.9.50 package source and runtime trees
  - immutable Git corpus manifests and derived Graphify artifacts
  - private cache metadata, execution receipts, and active graph projection status
parallel_safe: false
validation:
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - uv run --group test pytest tests/test_dbsctr_knowledge_store.py
  - dksctl reconcile --project dotfiles-ai
  - dksctl doctor --project dotfiles-ai
  - dksctl status --project dotfiles-ai
created: 2026-08-25
updated: 2026-08-25
completed: null
commits:
  - 066afd0
  - f74b9cd
  - dd67877
  - e67570e
  - 9e54fa5
jira_publications: []
migration: null
---

## Outcome

DKS uses pinned Graphify `0.9.50` and safely reuses byte-identical offline
extractions without changing normalized graph identity or source authority.

## Context

Graphify `0.9.50` fixes extraction and ignore matching and adds legitimate code
entities and relations. DKS currently pins `0.9.48` and repeats the complete
sandboxed extraction for an unchanged corpus. Graphify `0.9.x` does not promise a
stable artifact schema, so the upgrade needs an explicit compatibility gate.

## Scope

Pin and verify the `0.9.50` runtime and producer, retain `0.9.48` for rollback,
and add one disposable producer-owned filesystem cache for complete raw extraction
results. Namespace entries by project, extractor configuration, runtime, and corpus
identity. Persist the validated sanitized execution receipt with each graph import.
Do not add a daemon, remote cache, database cache authority, semantic extraction,
or direct graph-database adapter.

## Acceptance Criteria

- Package `graphifyy[sql]==0.9.50` binds revision
  `43d54acbfa9e731f7a592bb582c1f4b9d48ed73e`, exact runtime identity, producer
  identity, Python identity, and code-only offline configuration.
- The compatibility fixture accepts expected `0.9.50` entities and relations while
  rejecting unknown top-level shape, unsafe locations, dangling claims, and failed
  sources.
- Cache paths are absolute, owner-controlled, non-symlinked, mode `0700`, and
  namespaced by project, configuration, runtime, and corpus digests.
- A mode-`0600` external lock serializes cache readers and writers. Entries publish
  atomically and are bounded, schema-checked, identity-checked, and digest-checked.
- Missing, stale, unsafe, or corrupt entries are discarded and rebuilt through the
  existing default-deny network sandbox; they never fail or poison graph import.
- Cold and warm runs emit byte-identical normalized graph artifacts. Receipts state
  the cache schema, key, and hit result without making cache state graph identity.
- Schema 7 retains the complete validated sanitized execution receipt and its
  digest; PostgreSQL remains a rebuildable projection and stores no cache body.
- Failed extraction, receipt validation, migration, or import preserves the prior
  active graph and baseline ranking.
- Deployment installs the immutable `0.9.50` runtime without deleting `0.9.48`;
  rollback can restore the prior producer/runtime and rebuild the retained graph.
- Doctor, status, reconcile, focused tests, cold/warm parity, corruption recovery,
  restart, and rollback checks pass without source bodies or credentials in logs.

## Risks

Graphify output has no stable schema promise, and a reusable cache can amplify stale
or corrupt derived data. Strict identity binding, owner-only storage, external
locking, atomic publication, cold fallback, normalized parity, and retained prior
runtime/projection bound those risks. Deployment changes a private production
projection and therefore remains separately approved.

## Evidence

Discovery compared upstream `v0.9.48...v0.9.50`, inspected commit
`43d54acbfa9e731f7a592bb582c1f4b9d48ed73e`, traced the existing sandboxed
producer and transactional importer, and verified that no persistent extraction
cache or dedicated cache authority exists. The current runtime and producer remain
available as rollback identities until post-deployment operation checks pass.

Implementation produced byte-identical cold, warm, and corruption-recovery graph
artifacts with pinned runtime SHA-256
`26b1be946c79b13611ab7e5c1d24cb56cbe80576036147f764a282c1f6fedd5e`.
All 88 focused tests and Python/shell syntax checks pass. Repository-wide PM ticket
validation retains one unrelated V3.37 YAML finding; focused DKS-008 validation
has no finding.

## Review

Independent review found installer verification, upgraded-schema receipt,
directory-corruption, freshness, symlink-path, and recovery-test gaps. The fixes
passed final fixed-commit re-review with no findings. The real pre-v7 PostgreSQL
migration remains deploy-gate evidence and is not claimed by static tests.
