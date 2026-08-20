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
