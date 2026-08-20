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
