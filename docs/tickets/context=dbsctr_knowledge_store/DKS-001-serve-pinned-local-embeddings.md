---
schema_version: 1
id: DKS-001
slug: serve-pinned-local-embeddings
context: dbsctr_knowledge_store
title: Serve pinned local embeddings
kind: task
state: done
priority: high
points: 5
depends_on: []
relations: []
owns:
  - .chezmoidata.toml
  - .chezmoiignore
  - config.example.toml
  - docs/specs/dbsctr_knowledge_store
  - docs/tickets/context=dbsctr_knowledge_store
  - private_dot_config/dotfiles-ai/knowledge/embedding-space.json.tmpl
  - private_Library/LaunchAgents/dev.dotfiles-ai.dbsctr-embedding.plist.tmpl
  - run_onchange_after_install-dbsctr-embedding.sh.tmpl
  - run_onchange_after_load-dbsctr-embedding.sh.tmpl
  - dot_local/bin/executable_dbsctr-embedding.tmpl
  - dot_local/bin/executable_dbsctr-embedding-runtime-verify
  - tests/test_dbsctr_knowledge_store.py
reads:
  - machine-local durable state root
  - machine-local external model root
  - official llama.cpp releases
  - official Qwen3 Embedding GGUF repository
parallel_safe: false
validation:
  - uv run --group test pytest tests/test_dbsctr_knowledge_store.py tests/test_portable_distribution.py
  - python3 dot_local/bin/executable_pmctl tickets check --root . --json
  - plutil -lint rendered LaunchAgent
  - exact runtime and model SHA-256 checks
  - loopback listener and API-key rejection
  - embedding dimension, norm, determinism, instruction, and relevance checks
  - LaunchAgent restart recovery with unchanged embedding-space identity
created: 2026-08-19
updated: 2026-08-19
completed: 2026-08-19
commits:
  - "ea8ee02"
  - "ca542e4"
  - "ab602f0"
jira_publications: []
migration: null
---

## Outcome

DBSCTR has one durable, loopback-only, reproducible local embedding endpoint that
implements the approved Qwen semantics and recovers after restart without model
selection, downloads, or private-content logging.

## Context

The existing MLX Qwen3 embedding weights load in LM Studio as a causal language
model rather than an embedding endpoint. The future knowledge store needs an
operationally independent embedding service with explicit last-token pooling,
L2 normalization, immutable artifacts, and stable readiness behavior.

## Scope

Install exact llama.cpp `b10505` macOS arm64 runtime assets and the official
Qwen3 Embedding 8B Q4_K_M GGUF beneath configured external roots. Add a private
API credential, wrapper, launchd service, enabled/disabled configuration,
artifact manifest, and public-fixture semantic health check. Do not ingest a
corpus, alter PostgreSQL, create vectors, or deploy reranking.

## Acceptance Criteria

- Disabled configuration creates no runtime, model, key, LaunchAgent, or listener.
- Enabled rendering fails on missing/unsafe roots or invalid service settings.
- Downloads use exact immutable URLs and pass approved SHA-256 values before
  atomic installation; production startup performs no network access.
- The service starts only from exact local paths, binds `127.0.0.1`, requires its
  private API key, disables the web UI, and exposes bounded readiness/metrics.
- Qwen responses contain 4096 finite approximately unit-normal vectors; repeated
  input has at least `0.9999` cosine stability, instruction changes query output,
  and a fixed relevant
  document scores above an irrelevant document.
- launchd restart returns the same runtime, model, and embedding-space identity.
- Removal unloads only the owned LaunchAgent and retains immutable model/runtime
  assets for rollback unless retirement is separately approved.

## Evidence

Official source identities and digests are recorded in the bounded-context
specification. The scoped chezmoi deployment installed the exact 11,087,492-byte
runtime archive and 4,676,804,928-byte model, generated a mode-`0600` API key,
and loaded `dev.dotfiles-ai.dbsctr-embedding`. Live evidence confirms:

- `llama-server` listens only on `127.0.0.1:11435`; unauthenticated embedding
  requests return HTTP 401, while health and authenticated metrics return 200.
- The public fixture returns 4096 finite unit-normal vectors, repeated-input
  cosine above `0.9999`, instruction-sensitive output, and correct relevance
  ordering.
- A forced launchd restart changed the process ID while preserving manifest
  SHA-256 `5a37fee8f978aa425cc8e7ed295289cfafdade8d47e566c884e2cba3704cecb9`.
- Focused knowledge-store and portable-distribution tests pass on the deployed
  implementation.

## Risks

The model and runtime are large external artifacts; interrupted downloads must
not replace valid assets. Logs and metrics must not retain private request text.
Qwen 8B quality and throughput remain hypotheses until a later corpus bakeoff.

## Review

Independent post-deployment review found no remaining actionable correctness,
security, or lifecycle issue after remediation. Same-user account compromise is
outside the integrity threat model and requires reinstall plus key rotation.
