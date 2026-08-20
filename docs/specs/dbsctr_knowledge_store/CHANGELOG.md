# DBSCTR Knowledge Store Changelog

## 2026-08-19 - Discovery

- Established the repository-wide knowledge-store boundary: Git and existing
  SQLite systems remain authoritative while PostgreSQL begins as a rebuildable
  lexical, vector, and property-graph projection.
- Selected a host-side snapshot/incremental projector instead of direct live
  SQLite federation and selected standalone pinned llama.cpp services for durable
  Apple Silicon embedding and later reranking.
- Scoped DKS-001 to the immutable embedding runtime, local deployment, semantic
  validation, and recovery evidence. No ingestion, vectors, or database changes
  occur in this cycle.
- Adapted restart verification to macOS external-volume System Policy: full tree
  verification remains before bootstrap, while launchd uses a native signed
  SHA-256 helper and read-only runtime assets.

## 2026-08-19 - DKS-001 Delivery

- Deployed the pinned Qwen3 embedding space on loopback with private API access,
  semantic readiness, metrics, and launchd restart recovery.
- Validated exact runtime/model identities, affected tests, HTTP 401 rejection,
  4096-dimensional normalized output, relevance ordering, and stable identity
  across restart. Release was not applicable; immutable assets remain for
  rollback and disabling unloads only the owned service.
- Gate commits before final lifecycle review: `ea8ee02`, `ca542e4`, and
  `ab602f0`.

## 2026-08-19 - DKS-002 Discovery

- Scoped the first corpus to exact-commit dotfiles-ai specs and tickets in a
  project namespace inside a separate knowledge database per client VM.
- Selected pinned pgvector `0.8.6` on PostgreSQL 19 Beta 3, native
  `vector(4096)` exact search, English FTS, deterministic SQL/PGQ edges, and fixed
  reciprocal-rank fusion behind a JSON `dksctl` CLI.
- Required PM backup/scratch restore before the shared image migration, atomic
  revision activation, retained immutable revisions, dedicated 1Password
  credentials, and rebuild-based recovery. OpenCode ingestion, ANN, inferred
  graph edges, reranking, and automatic sync remain deferred.
- Kept canonical tickets as work authority and prohibited reintroducing
  per-context `BACKLOG.md`; stale deployed lifecycle skill wording is part of the
  DKS-002 serialized update while legacy migration fixtures remain historical.
