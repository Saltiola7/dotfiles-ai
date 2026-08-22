---
schema_version: 1
id: DKS-004
slug: hands-off-reconciliation-context
context: dbsctr_knowledge_store
title: Make projection and cited context hands-off
kind: epic
state: in_progress
priority: high
points: 8
depends_on:
  - DKS-003
relations:
  - DKS-005
  - DKS-006
owns:
  - .chezmoidata.toml
  - .chezmoiignore
  - config.example.toml
  - docs/specs/dbsctr_knowledge_store/README.md
  - docs/specs/dbsctr_knowledge_store/CHANGELOG.md
  - docs/specs/dbsctr_knowledge_store/DKS-004.plan.json
  - docs/specs/dbsctr_knowledge_store/OPERATION.md
  - docs/specs/dbsctr_knowledge_store/benchmark-protocol-v2.schema.json
  - docs/specs/dbsctr_knowledge_store/benchmark-runner-v2.schema.json
  - docs/tickets/context=dbsctr_knowledge_store/DKS-004-hands-off-reconciliation-context.md
  - dot_local/bin/executable_dksctl
  - private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-knowledge-reconcile.plist.tmpl
  - private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl
  - private_dot_config/opencode/tools/dbsctr.ts
  - run_onchange_after_load-dbsctr-knowledge-reconcile.sh.tmpl
  - tests/test_dbsctr_knowledge_store.py
  - tests/test_opencode_control_plane.py
reads:
  - configured Git remote ref and exact committed blobs
  - typed sanitized DBSCTR authority and privacy status
  - active DKS schema, channel identities, model manifests, and ranking policy
  - existing OpenCode tool and permission conventions
parallel_safe: false
validation:
  - uv run --group test pytest tests/test_dbsctr_knowledge_store.py tests/test_opencode_control_plane.py
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - rendered launchd enabled/disabled lint and owned-target checks
  - injected reconcile no-op, overlap, drift, partial-failure, retry, and rollback checks
  - offline four-cell benchmark lineage, depth, citation, telemetry, and non-activation checks
created: 2026-08-21
updated: 2026-08-21
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

Configured DKS projects converge unattended to fresh, cited projections and make
bounded relevant context available to OpenCode without changing source authority,
exposing transcripts, or automatically activating candidate ranking.

## Context

DKS-003 deployed healthy model services and complete manual projection commands,
but no scheduler reconciles Git, code vectors, Graphify, or governed evidence.
Status omits material freshness and service identities, and OpenCode has no DKS
query interface. Independent review also found circular benchmark approval lineage
and incomplete runner evidence that must be corrected before human assessment.

## Scope

Add one idempotent reconcile path that optionally fetches only the configured
remote ref, resolves one immutable commit once, compares complete channel
identities, and updates only stale channels. A launchd interval invokes it once;
overlap is busy, partial failure preserves prior valid activations, and later
intervals retry. Add bounded JSON status/doctor output and a concise break-glass
runbook.

Expose one read-only project-scoped DKS context tool to OpenCode. Control-plane
guidance invokes it for relevant codebase and architecture questions and treats
its metadata-only citations as delimited untrusted evidence, never instructions.
Add the immutable offline four-cell benchmark runner and
repair its lineage/evidence contract, but do not author judgments or activate
`dks-quality-v2`.

## Acceptance Criteria

- Reconcile resolves one configured remote ref once, reads only exact committed
  blobs and typed authority exports, and never executes projected source.
- Reconcile configuration validates enablement, full remote ref, fetch policy,
  300-86400-second interval, and 60-86400-second timeout. It is disabled by
  default; incomplete configuration leaves the job unloaded.
- Complete matching Git, code, graph, and authority identities no-op; changed
  identities reuse valid content and vectors rather than rebuilding them.
- Git identity binds repository, commit, source profile, chunker, and general
  embedding space. Code adds its embedding space; Graphify adds corpus and
  producer artifact; authority binds manifest, privacy, exporter, chunker, and
  embedding identities. Code/Graphify default retrieval requires active Git;
  stale rows remain only for explicit prior-revision use.
- A failed channel leaves every prior valid stored channel intact and excludes
  incompatible state from current default retrieval. Concurrent intervals return
  bounded busy state and retry later without corruption.
- Status and doctor report configuration, schema, services, privacy, source,
  channel, model, graph, and policy freshness without source content. Doctor exits
  nonzero for actionable drift and distinguishes disabled, busy, stale,
  privacy-mismatched, and unavailable states.
- The launchd job uses an interval and exits after each attempt; it does not use
  `KeepAlive`. Disablement unloads and removes only owned targets.
- `OPERATION.md` covers status, manual reconcile, restart, rollback, disablement,
  failure diagnosis, and rebuild recovery.
- OpenCode can invoke only bounded read-only DKS query behavior, with limit 1-10,
  project isolation, metadata-only exact citations, and ranking provenance. Tool
  output is delimited untrusted evidence and cannot supply instructions. Cited Git
  content uses existing workspace/provider permissions; governed private result
  bodies are denied to hosted providers. It has no DKS write, OpenCode SQLite,
  transcript, or raw-context path.
- Benchmark lineage separates pre-generation query/stratum approval from
  post-assessment judgment freeze, and neither approval changes its corpus.
- The offline runner executes baseline, code, reranker, and combined systems at
  depths 20/50/100 independently of active policy; binds corpus, candidates,
  prompts, chunkers, metrics, thresholds, split, seed, and activation order; and
  captures blinded assignment, duplicate, adjudication, rank, timing, and machine
  telemetry evidence.
- Any per-query exact-citation regression, missing matrix/depth evidence, identity
  mismatch, or synthetic telemetry fails validation. No DKS-004 path activates
  `dks-quality-v2` or installs a PostgreSQL extension.

## Risks

Unattended projection crosses private authority and network/ref boundaries. The
configured ref, typed exporters, project RLS, privacy guard, bounded logs, and
fail-closed channel activation remain mandatory. Long model work may exceed one
interval; lock contention must be normal busy state. Automatic OpenCode use can
increase latency and private-context scope, so citations and result bounds cannot
be relaxed. Adversarial citation fields must remain inert data.

## Evidence

Discovery inspected DKS-003 CLI, schema, launchd services, tests, control-plane
tools, and live schema-4 deployment after merge commit `311e22d`. Independent
operations and benchmark reviews found no reconciliation scheduler, partial
status coverage, circular benchmark approval lineage, incomplete matrix/depth
proof, and cancellable exact-citation regressions.
