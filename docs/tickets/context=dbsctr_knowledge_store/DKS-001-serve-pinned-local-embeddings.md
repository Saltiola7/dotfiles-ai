---
schema_version: 1
id: DKS-001
slug: serve-pinned-local-embeddings
context: dbsctr_knowledge_store
title: Serve pinned local embeddings
kind: task
state: in_progress
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
completed: null
commits: []
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
  input is deterministic, instruction changes query output, and a fixed relevant
  document scores above an irrelevant document.
- launchd restart returns the same runtime, model, and embedding-space identity.
- Removal unloads only the owned LaunchAgent and retains immutable model/runtime
  assets for rollback unless retirement is separately approved.

## Evidence

Official source identities and digests are recorded in the bounded-context
specification. Focused red/green implementation tests pass. Runtime, deployment,
operation, and live semantic evidence remain pending.

## Risks

The model and runtime are large external artifacts; interrupted downloads must
not replace valid assets. Logs and metrics must not retain private request text.
Qwen 8B quality and throughput remain hypotheses until a later corpus bakeoff.

## Review

Discovery is implementation-ready. No unresolved question changes DKS-001 scope,
security, interface, deployment, or validation.
