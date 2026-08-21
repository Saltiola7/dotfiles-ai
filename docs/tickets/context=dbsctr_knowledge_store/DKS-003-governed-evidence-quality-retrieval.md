---
schema_version: 1
id: DKS-003
slug: governed-evidence-quality-retrieval
context: dbsctr_knowledge_store
title: Governed evidence into quality-gated retrieval
kind: epic
state: done
priority: high
points: 8
depends_on:
  - DKS-002
relations: []
owns:
  - README.md
  - .chezmoidata.toml
  - .chezmoiignore
  - config.example.toml
  - docs/specs/dbsctr_knowledge_store
  - docs/specs/dbsctr_v3_lifecycle
  - docs/tickets/context=dbsctr_knowledge_store
  - dot_local/bin/executable_dbsctrctl
  - dot_local/bin/executable_dks-postgres-migrate.tmpl
  - dot_local/bin/executable_dksctl
  - dot_local/share/dbsctr-knowledge
  - private_dot_config/dotfiles-ai/knowledge/projects.json.tmpl
  - private_dot_config/launchd
  - run_onchange_after_configure-dbsctr-knowledge.sh.tmpl
  - tests/test_dbsctr_knowledge_store.py
  - tests/test_dbsctrctl.py
  - private_dot_config/opencode/tools/dbsctr.ts
  - tests/test_portable_distribution.py
reads:
  - exact dotfiles-ai Git commits and regular blobs
  - typed DBSCTR cycle, evidence, review, history, benchmark, provider, execution, and improvement authorities
  - pinned Qwen3 general embedding runtime and active DKS projection
  - official Nomic Embed Code, Qwen3 Reranker, Graphify, llama.cpp, Transformers, and tokenizer artifacts
  - machine-local project, model-root, and 1Password configuration
parallel_safe: false
validation:
  - uv run --group test pytest tests/test_dbsctr_knowledge_store.py tests/test_dbsctrctl.py tests/test_portable_distribution.py
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - typed export sanitization, snapshot, expiry, tombstone, and deterministic replay checks
  - exact Git code/config sync, byte-citation, mixed-chunker, failed-activation, and rebuild checks
  - pinned offline Graphify cold/incremental parity, artifact rejection, deletion, provenance, and isolation checks
  - pinned Nomic and Qwen artifact, identity, semantic, privacy, resource, restart, and fallback checks
  - frozen retrieval benchmark at depths 20, 50, and 100 with quality/latency activation gates
  - PostgreSQL migration rerun, project RLS, backup/restore, and rollback checks
created: 2026-08-20
updated: 2026-08-21
completed: 2026-08-21
commits:
  - 68429e1
jira_publications: []
migration: null
---

## Outcome

All governed sanitized DBSCTR evidence and exact project code/config are
rebuildably searchable with exact citations; an isolated Graphify code graph,
Nomic code vectors, and Qwen pair reranking activate only when frozen local
quality, privacy, identity, resource, and latency gates pass.

## Context

DKS-002 projects committed specs/tickets through English FTS, Qwen3 general
vectors, deterministic graph edges, and fixed RRF. DBSCTR's remaining governed
evidence lives in Cycle Records, evidence sidecars, and typed private SQLite
ledgers with explicit sanitization, retention, capture, replay, and tombstone
semantics. Code/config retrieval and model-derived graph relationships are absent.

The operator selected one combined cycle, a separate code embedding channel,
top-50-to-top-10 reranking, and a 30-second warm p95 budget on a 64-GB Apple
Silicon host. PostgreSQL remains a disposable projection; canonical source
migration is a later cycle.

## Scope

Add one lifecycle-owned deterministic sanitized envelope export and one DKS-owned
mixed-source importer. Include cycles/gates/evidence, reviews/history,
captures/telemetry, longitudinal and execution benchmarks, phase/execution state,
provider evaluations, and improvement claims. Reconcile each authority's expiry,
retention, tombstones, and forgetting. Never expose raw OpenCode transcripts or
directly access live SQLite/WAL/SHM.

Expand exact-commit Git ingestion to reviewed code/config paths with
`dks-source-v1`, preserving existing Markdown identities. Pin Graphify `0.9.48`
for offline code-only AST/SQL extraction over an immutable materialized corpus;
validate and import its complete `graph.json` snapshot as derived, confidence-
labelled, citation-resolvable graph evidence.

Keep Qwen3 Embedding 8B as the general channel. Evaluate and independently
activate official Nomic Embed Code Q4_K_M as a 3584-dimensional exact code
channel. Evaluate and independently activate official Qwen3-Reranker-4B through
a pinned loopback Transformers MPS service implementing the exact official
yes/no-logit scoring contract. Rerank the deduplicated RRF top 50 to 10, preserve
exact-evidence precedence, fail unchanged to RRF, and retain complete rollback.

## Acceptance Criteria

- A typed exporter emits only schema-versioned sanitized envelopes with stable
  source identity, revision/snapshot/cursor digest, content digest, retention
  state, and deterministic ordering for every governed DBSCTR source family.
- Raw prompts/messages/tool payloads/commands/errors, credentials, URLs, email,
  machine paths, unsupported attribution, and direct SQLite/WAL/SHM access are
  absent; adversarial fixtures prove redaction and rejection.
- Retention follows each authority subtype rather than inferred age: only
  transient federated captures use 24-hour expiry and only detailed operational
  reviews use 90-day expiry unless the lifecycle contract changes. An unsigned
  64-bit privacy sequence plus digest denies tombstoned/forgotten identities
  before content activation,
  then purges active, retained, staged, cached, benchmark, and rollback derivatives.
  Failed reconciliation cannot query or resurrect denied text.
  Export/import uses status-export-status-deny-reconcile-activate-status order;
  every query holds the lifecycle shared privacy guard while tombstone writers
  require the exclusive lock.
- Exact-commit Git code/config ingestion uses the committed byte-exact default-
  deny `DKS-003.source-profile.json` selection and exclusion lists, rejects dirty
  worktree paths and unsupported Git modes, and
  produces deterministic non-overlapping exact-byte `dks-source-v1` citations.
  Existing `dks-markdown-v1` records and identities do not change.
- Schema migration supports mixed source revision kinds, both chunkers, 4096- and
  3584-dimensional exact vector spaces, source-specific active snapshots,
  Graphify provenance/mappings, retrieval/reranker provenance, project RLS, and
  rerunnable migration/rebuild identity.
- Graphify runs pinned and network-disabled without source/database credentials.
  The importer rejects unknown shape, duplicate/dangling IDs, wrong commit or
  digest, unsupported confidence, and missing/out-of-range claimed provenance;
  native external-symbol nodes plus incident or dangling reference edges are
  excluded before all remaining nodes and edges resolve to the immutable accepted corpus. Cold and
  incremental source deletion yield equivalent active graph rows.
- Nomic artifact/runtime hashes, dimensions, last-token pooling, L2 norm, query
  prefix, code semantics, exact pgvector rank parity, memory, restart, and offline
  startup pass before its channel may activate.
- Qwen reranker safetensors/tokenizer/runtime/template/instruction/truncation and
  yes/no probability identities are immutable. Golden pair scores match the
  official reference; loopback auth, no prompt logging, memory, restart, timeout,
  malformed-score, and service-loss checks pass.
- The frozen benchmark contains at least 100 graded 0-3 queries, at least 20 per
  declared stratum, judgments through depth 50, and stable tie policy. It measures
  candidate Recall@50, nDCG@10, exact citation
  correctness, rank stability, p50/p95/p99 latency, peak memory, and source/use-
  case strata at depths 20/50/100. Private judgments stay local and Git receives
  only fixtures, schema, and sanitized aggregates.
- Queries/strata precede candidate generation; labels use a blinded randomized
  depth-50 pool with 20% duplicate rejudgment, quadratic-weighted Cohen's kappa
  at least 0.70,
  and adjudication before freeze. The manifest binds all query/judgment/corpus/
  model/prompt/protocol identities and seed; any mutation creates a new benchmark.
  The quality interval uses 10,000 within-stratum query bootstrap replicates
  selected by the specified SHA-256 byte stream, arithmetic mean delta, and fixed
  sorted percentile indexes.
- Each candidate requires at least 5% relative overall nDCG@10 improvement (five
  absolute points for a zero baseline), a stratified 95% bootstrap interval above
  zero, no stratum regression beyond two absolute points, unchanged exact citation
  correctness, no lower Recall@50, and warm p95 no greater than 30 seconds. Five
  concurrency-one runs after three warmups must stay at or below 56 GiB combined
  process/Metal memory with normal memory pressure and no swap growth. Nomic is
  tested first, then Qwen against the winning channel set; the full 2x2 matrix is
  reported. A failed gate leaves its baseline unchanged.
- Ranking policy `dks-quality-v2` accepts limits 1-10 and defaults to 10;
  explicit rollback `dks-rrf-v1` preserves DKS-002 limits 1-20. Query JSON
  identifies source authority/revision/range/digest, channel ranks,
  embedding spaces, Graphify artifact/provenance, reranker/runtime/template,
  truncation, scores, benchmark activation, and fallback. Exact identity/hash/
  version evidence cannot be suppressed by semantic reranking.
- Exact-evidence precedence accepts only bounded lowercase Git/SHA identities,
  backtick-delimited canonical POSIX paths, and the specified ASCII version-token
  grammar. Match count, metadata-before-body, body-match count, and chunk ID
  define exact rank before RRF and total
  order inside the selected project/revision; malformed or out-of-scope
  identifiers add no exact candidate.
  The exact channel enters the top-50 union, caps at 20, pins deduplicated exact
  chunks before reranked non-exact chunks, and defines total ordering/fallback.
- PM backup/restore precedes shared schema/image activation, but rebuildable DKS
  private projection data is excluded from backups. Failed projection/model activation,
  crash, service restart, PostgreSQL restart, rebuild, credential revocation, and
  disablement preserve or restore the last verified cited retrieval configuration.

## Risks

The single-cycle scope deliberately combines privacy-sensitive ingestion, schema
expansion, two model services, derived graph import, and ranking activation.
Gate increments must leave a usable sanitized baseline before candidate models
can activate. Graphify is pre-1.0 and has no stable artifact-schema promise, so
every upgrade requires a golden compatibility gate. Qwen publishes no official
reranker GGUF and llama.cpp rank pooling is incompatible with its decoder score;
only official safetensors through the validated MPS scorer are in scope.

Exact scans remain acceptable only for the measured corpus. ANN and semantic
Graphify document extraction require separate evidence. PostgreSQL remains beta
and non-authoritative; the existing PM backup/scratch-restore boundary remains
mandatory for any shared image or schema risk.

## Evidence

Discovery inspected the committed DKS schema, projector, tests, lifecycle typed
authorities, and private-ledger retention contracts at merge commit
`780815a9c54a68770dfb4b3ffb73cbe0aff0e7e6`. First-party artifact research
verified the pinned Nomic model, Qwen reranker scoring contract, Graphify file
architecture, and the llama.cpp incompatibility with Qwen decoder reranking.
Implementation and deployment projected 315 exact-commit records, 2,393 chunks,
1,047 governed authority records, 984 controlled Graphify nodes, 3,005 Graphify
edges, and 596 distinct code vectors. Schema 4, external-volume candidate model
services, automatic crash restart, canonical vector hashes, deterministic rebuild,
baseline rollback, and a cited 20-result query passed. The full suite passed with
407 tests and one configured skip before final remediation; final affected checks
cover every subsequent review fix.

First-party sources:

- `https://huggingface.co/nomic-ai/nomic-embed-code-GGUF/tree/ff2ddedde976ea623178981f18e36af33c0c2a94`
- `https://huggingface.co/Qwen/Qwen3-Reranker-4B/tree/22e683669bc0f0bd69640a1354a6d0aebcfeede5`
- `https://github.com/QwenLM/Qwen3-Embedding/commit/44548aa5f0a0aed1c76d64e19afe47727a325b8f`
- `https://github.com/ggml-org/llama.cpp/commit/0e1d9185c5fe82e905d1f5ae6b2e5dcd607a8dfd`
- `https://github.com/Graphify-Labs/graphify/commit/b2cd36267456c166788c95be6e68574064a92a42`

## Review

Independent privacy, provenance, migration, runtime, retrieval, Graphify, and
benchmark reviews closed all concrete findings. Candidate assets remain pinned
under `/Volumes/ext/state/models/dbsctr`; the temporary internal model duplicate
was removed. `dks-rrf-v1` remains active because no human-authored frozen
benchmark has been approved or run; activation fails closed until its committed
query/judgment approval precedes the benchmark source revision.
