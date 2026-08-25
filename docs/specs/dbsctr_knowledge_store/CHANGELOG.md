# DBSCTR Knowledge Store Changelog

## 2026-08-25 - DKS-008 Discovery

- Scoped the pinned Graphify `0.9.50` compatibility upgrade and one disposable,
  owner-private, identity-namespaced whole-extraction cache.
- Required external locking, atomic publication, corruption fallback, cold/warm
  normalized parity, retained sanitized execution receipts, and prior-active graph
  preservation while keeping Git authoritative and PostgreSQL rebuildable.
- Retained immutable `0.9.48` runtime material for rollback and deferred deployment,
  schema migration, and live reconciliation to separate operator approval.

## 2026-08-25 - DKS-008 Implementation

- Pinned and verified Graphify `0.9.50`, added an owner-private locked atomic
  whole-extraction cache, and retained validated sanitized receipts in schema 7.
- Proved byte-identical cold, warm, and corruption-recovery artifacts against the
  real runtime; 88 focused tests cover compatibility, permissions, installer
  verification, cache recovery, receipt freshness, schema, and prior-active safety.
- Independent review drove runtime installer, schema constraint, corruption, and
  freshness hardening; final fixed-commit re-review found no remaining issue.
- Local runtime installation, schema migration, reconciliation, operation, and
  rollback verification remain pending separate deployment approval.

## 2026-08-25 - DKS-007 Recovery

- Accepted upstream PR #50's canonical DKS-005 state correction after affected
  PM validation returned no DKS findings; no duplicate ticket edit was made.
- Preserved the prior-valid projection when a long scheduled refresh observed
  changing authority, then used one runbook retry to converge Git, code, graph,
  and governed evidence to merge commit `87d20d0`.
- Verified healthy doctor status, launchd exit 0, a four-stage unchanged follow-up,
  84 focused passing tests, and retained baseline `dks-rrf-v1`; no runtime code,
  configuration, schema, model, benchmark, or ranking change was needed.

## 2026-08-25 - DKS-007 Discovery

- Scoped one elevated recovery cycle to correct DKS-005's unsupported PM state
  and restore the live projection to merged `origin/main` without changing source
  authority, schema, models, benchmarks, or baseline ranking.
- Live evidence showed retained prior-valid projection `b96dd297`, target
  `d9b09ec`, stale Git/graph/authority channels, a nonzero prior launchd exit, and
  a new scheduled reconcile actively retrying during discovery.
- Recovery first observes that in-flight run, then permits one manual runbook
  retry; only a reproduced failure may expand to a minimal code/config repair.

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

## 2026-08-20 - DKS-002 Implementation

- Added exact-commit Git Markdown projection, byte-stable chunking, embedding
  provenance checks, project-forced RLS, English FTS, exact `vector(4096)` search,
  SQL/PGQ one-hop retrieval, deterministic fixed RRF, and cited JSON commands.
- Added a pinned PostgreSQL 19 Beta 3 plus pgvector 0.8.6 derivative, immutable
  image verification, same-base PM migration guards, baseline comparison,
  dedicated database/role provisioning, and explicit access removal.
- Validated the image and rerunnable schema on target arm64, adversarial RLS,
  generated CLI SQL including `GRAPH_TABLE`, and affected tests. Deployed after
  verified PM backup/scratch restore; PM state survived image activation, and the
  exact-commit projection, hybrid query, rebuild identity, failed activation,
  project isolation, and PostgreSQL/embedding restart recovery passed.

## 2026-08-20 - DKS-003 Discovery

- Scoped one combined elevated cycle to project all governed sanitized DBSCTR
  evidence, exact Git code/config, and a pinned offline Graphify code graph while
  keeping Git and typed private ledgers authoritative.
- Required lifecycle-owned typed bounded export, subtype-specific authority
  retention, monotonic privacy-sequence denial and tombstone purging,
  deterministic cited source chunking, untrusted Graphify artifact
  validation, and atomic mixed-source activation without direct SQLite access.
- Selected the existing Qwen3 8B general space plus a separately gated official
  Nomic Embed Code Q4_K_M 3584-dimensional channel, and selected the official
  Qwen3-Reranker-4B safetensors model behind an exact local MPS scoring contract.
- Fixed reranking at a deduplicated top-50 candidate union to top-10 results,
  required identical RRF candidate-order fallback, and set quality gates of at least 5%
  relative nDCG@10 improvement with a positive stratified confidence interval,
  bounded stratum regression, unchanged exact
  citations/Recall@50, and warm end-to-end p95 latency no greater than 30 seconds.
- Deferred Graphify semantic document extraction, graph-database push, ANN,
  hosted inference, and any move of canonical JSON/SQLite authority to PostgreSQL.

## 2026-08-21 - DKS-003 Implementation

- Added governed lifecycle export and monotonic privacy projection, exact Git
  code/config chunking, controlled offline Graphify import, Nomic code vectors,
  Qwen reranking, frozen benchmark verification, atomic activation, and rollback.
- Deployed schema 4 and both candidate services from pinned external-volume
  models; validated automatic restart hashing, 315 records, 2,393 chunks, 596
  code vectors, 984 imported nodes, 3,005 imported edges, deterministic rebuild,
  baseline rollback, and a cited 20-result query.
- Kept `dks-rrf-v1` active. `dks-quality-v2` remains blocked until a committed
  pre-generation query/judgment approval and passing human-authored private
  benchmark evidence exist. No public release applies.

## 2026-08-21 - DKS-004 Discovery

- Scoped unattended identity-based reconciliation, bounded freshness diagnosis,
  interval launchd operation, break-glass recovery, and automatic read-only cited
  OpenCode context while preserving Git and typed private authorities.
- Required unchanged-channel skips, one resolved Git commit per run, benign busy
  overlap, prior-active preservation, privacy-safe diagnostics, and no automatic
  ranking activation.
- Planned benchmark corrections around separate pre-generation and post-assessment
  lineage, a complete offline four-cell/three-depth runner, per-query citation
  safety, blinded assessment evidence, and machine-captured telemetry.
- Split retrieval assessment into dependent DKS-005 and an isolated
  recommendation-only BM25 bakeoff in DKS-006; production PostgreSQL 19 remains
  untouched. Later source verification corrected the extension identity from
  ParadeDB `pg_search` to Tiger Data `pg_textsearch`.

## 2026-08-21 - DKS-004 Delivery

- Added fixed-ref unattended reconciliation, complete channel health identities,
  break-glass operations, and bounded metadata-only OpenCode context.
- Deployed schema 5, a dedicated Keychain credential mirror, and the interval
  LaunchAgent; projection converged to `b830bae`, doctor reported healthy, and a
  subsequent four-stage unchanged run exited 0.
- Corrected benchmark lineage and execution evidence without authoring human
  judgments or activating `dks-quality-v2`; 175 union affected tests passed and
  independent final review found no P0/P1 issues.
- Gate commits: `4d3c35d`, `5cdca8a`, `bf9377e`, `b584f53`, `3c47cea`,
  `bc50702`, and `81ae12b`. Release remained not applicable.

## 2026-08-24 - DKS-005 Delivery

- Added the committed 100-query silver suite, exact fixed-commit provenance,
  four-cell local runner, continuously sampled HMAC-bound evidence, schema 6
  trial lease, and automatic baseline restoration.
- Bounded Qwen3-Reranker-4B to batch 1, 4,096 tokens, cache-free last-token
  logits, 20 GiB MPS allocation, and 24 GiB process footprint; the final real
  depth-100 smoke stayed near 11.46 GB while kernel pressure moved from normal
  to warning and swap usage decreased.
- Completed the matrix at aggregate SHA-256
  `837271160639c5148d75984eba53c068fc20fd049e732824be080fd84c3c5b0b`.
  Code vectors regressed quality; reranking improved nDCG but failed citation,
  latency, kernel-pressure, peak-memory, and swap gates. Neither candidate
  activated, and `dks-rrf-v1` remained the production policy.
- Retained DKS-006 as recommendation-only and blocked production
  `pg_textsearch` work solely on official PostgreSQL 19 support.
