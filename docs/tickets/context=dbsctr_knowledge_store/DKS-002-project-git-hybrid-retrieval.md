---
schema_version: 1
id: DKS-002
slug: project-git-hybrid-retrieval
context: dbsctr_knowledge_store
title: Project Git knowledge into hybrid retrieval
kind: epic
state: ready
priority: high
points: 8
depends_on:
  - DKS-001
relations: []
owns:
  - .chezmoidata.toml
  - .chezmoiignore
  - config.example.toml
  - docs/specs/dbsctr_knowledge_store
  - docs/tickets/context=dbsctr_knowledge_store
  - dot_agents/skills/dbsctr/SKILL.md
  - dot_agents/skills/discovery/SKILL.md
  - dot_local/bin/executable_dks-postgres-migrate.tmpl
  - dot_local/bin/executable_dks-psql.tmpl
  - dot_local/bin/executable_dksctl
  - dot_local/bin/executable_sandbox-vm
  - dot_local/bin/executable_pm-postgres-baseline.tmpl
  - dot_local/bin/executable_pm-postgres-image-build
  - dot_local/bin/executable_pm-postgres-image-verify
  - dot_local/share/dbsctr-knowledge
  - dot_local/share/pm-kernel/Containerfile.pgvector
  - private_dot_config/containers/systemd/pm-postgres.container.tmpl
  - private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl
  - private_dot_config/dotfiles-ai/sandbox.json.tmpl
  - run_onchange_after_configure-pm-postgres.sh.tmpl
  - run_onchange_after_enable-pm-postgres.sh.tmpl
  - tests/test_dbsctr_knowledge_store.py
  - tests/test_dbsctr_lifecycle.py
  - tests/test_dbsctrctl.py
  - tests/test_pm_kernel.py
  - tests/test_portable_distribution.py
reads:
  - exact dotfiles-ai Git commits and blobs
  - PM PostgreSQL deployment, migration, backup, and scratch restore
  - pinned local embedding service and manifest
  - machine-local project and 1Password configuration
  - pgvector 0.8.6 and PostgreSQL 19 Beta 3 sources
parallel_safe: false
validation:
  - uv run --group test pytest tests/test_dbsctr_knowledge_store.py tests/test_pm_kernel.py tests/test_portable_distribution.py
  - uv run --group test pytest tests/test_dbsctr_lifecycle.py tests/test_dbsctrctl.py
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - pinned pgvector image build and extension 0.8.6 proof on arm64
  - PM logical backup and scratch restore before image migration
  - exact Git sync, failed-activation, retained-revision, and rebuild identity checks
  - project-scoped FTS, vector, SQL/PGQ, fixed-RRF, and citation checks
  - PostgreSQL and embedding restart recovery with unchanged active identities
created: 2026-08-19
updated: 2026-08-19
completed: null
commits: []
jira_publications: []
migration: null
---

## Outcome

An exact dotfiles-ai Git commit is rebuildably projected into a client-isolated,
project-scoped PostgreSQL lexical, native-vector, and deterministic SQL/PGQ graph
index, and `dksctl` returns transparent fused results with exact citations.

## Context

DKS-001 provides a pinned, private loopback embedding service, while the PM
Kernel already runs PostgreSQL 19 Beta 3 in the personal sandbox. DKS-002 adds a
separate rebuildable knowledge database without changing Git authority or PM
data, and must migrate the shared image only after verified backup and restore.

## Scope

Build a pinned PostgreSQL 19 Beta 3 plus pgvector 0.8.6 local image, preserve and
revalidate PM data during the shared service image migration, create a dedicated
`dbsctr_knowledge` database/role, and project only tracked Markdown beneath
`docs/specs` and `docs/tickets`. Add deterministic heading/paragraph chunking,
native `vector(4096)` exact search, English FTS, source-derived graph edges,
fixed RRF, retained immutable revisions, and JSON `dksctl` sync/query/status/
rebuild commands.

Do not ingest OpenCode, scan another repository, watch Git automatically, create
ANN indexes, truncate embeddings, infer graph edges, rerank results, or move
source authority into PostgreSQL.

## Acceptance Criteria

- The custom image derives from the exact approved PostgreSQL digest and pgvector
  archive, runs on arm64, and reports extension version `0.8.6`.
- PM backup and scratch restore pass before image replacement; PM schema, row
  counts, health, and restart recovery remain unchanged afterward.
- A dedicated generated knowledge credential creates one separate knowledge
  database inside the client VM through the bootstrap administrator; the
  no-login owner and per-project application role are least-privilege, and forced
  RLS binds session user plus local scope to exactly one project.
- Sync reads exact Git blobs, not worktree overlays, and atomically activates only
  complete revisions while retaining prior revision links and deduplicated data.
- Chunks preserve heading context and exact byte citations, contain at most 1024
  pinned-model tokens, and never overlap.
- FTS, exact normalized-vector search, deterministic one-hop graph expansion, and
  fixed `k=60` RRF return stable JSON with channel ranks and source provenance.
- Failed sync leaves the active revision unchanged; rebuild reproduces identities.
- Concurrent sync, crash points, malformed Git/Markdown, direct cross-project
  access, SQL/PGQ capability, and fixed-vector rank boundaries have executable
  failure checks.
- No `docs/specs/<context>/BACKLOG.md` is created or required; deployed Discovery
  and DBSCTR wording uses affected canonical tickets as work authority while
  legacy migration fixtures and serialized Cycle Record keys remain compatible.
- `dks-markdown-v1` fixtures cover CRLF/LF/CR, fences, headings, blank lines,
  oversized paragraphs/sentences/tokens, empty heading context, and exact byte
  ranges and identities.
- Disablement removes knowledge entry points and access while retaining source
  Git and explicitly approved immutable projection assets for rollback.

## Evidence

The pinned PostgreSQL 19 Beta 3 plus pgvector 0.8.6 image built on target arm64.
A fresh disposable database accepted the schema twice; forced-RLS checks denied
unset and mismatched project scopes, and the exact generated `dksctl` query SQL
returned FTS, exact-vector, cited chunk, node, and `GRAPH_TABLE` edge rows. The
affected suite passed 289 tests with one expected skip before final embedding
provenance checks; the focused suite then passed 29 tests. Independent review
closed all implementation blockers. Current PM compatibility evidence records
the exact approved base, PostgreSQL 19, migration 1, 147 tickets, one Jira
publication, and nine source envelopes. Live backup/restore, image activation,
projection, restart, and recovery evidence remain pending.

The `owns` list is this serialized cycle's writable scope, not durable domain
ownership. Distribution owns the image build and Quadlet activation; PM owns the
shared cluster, volume, migration compatibility, backup, restore, and rollback;
DKS owns its database, project roles, schema, projector, and retrieval contracts.

## Risks

PostgreSQL 19 remains beta and pgvector publishes no PG19 image. DKS-002 therefore
owns a pinned local derivative and must preserve PM recovery before migration.
Exact 4096-dimensional scans are intentionally bounded to one small corpus; ANN
requires a later measured representation change. Same-account compromise remains
outside the local integrity boundary and requires credential rotation and rebuild.

## Review

Implementation review is accepted with no remaining code blocker. Deployment is
paused until desktop 1Password authorizes creation of the dedicated project
credential; the read-only Automation service account cannot create that item.
