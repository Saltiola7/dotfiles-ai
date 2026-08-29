# DBSCTR Cycle Speed

This Initiative reduces interactive DBSCTR autonomous runtime while preserving
every existing quality, safety, privacy, and delivery gate. Calendar cycle time
remains visible but is not the primary optimization target.

The coordinator repository is `Saltiola7/dotfiles-ai`. The canonical machine
ledger is [`MANIFEST.json`](MANIFEST.json).

## Success

- Report autonomous-runtime mean, p50, and p90 with sample count and attribution
  coverage across the host and configured VM sources.
- Keep calendar elapsed time separate from autonomous runtime.
- Reduce autonomous-runtime p50 and p90 without increasing failed gates,
  reopened gates, remediation rounds, or unavailable required evidence.
- Treat partial timing and unavailable sources as unavailable rather than zero.

## Context Map

| Context | Responsibility | Dependency |
|---|---|---|
| `dbsctr_v3_lifecycle` | Timing semantics, source-local summaries, quality-equivalence policy, and safe concurrency | None |
| `opencode_control_plane` | Typed adapter timing boundaries and runtime correlation | Lifecycle timing contract |
| `dotfiles_ai_distribution` | Immutable host/VM capture, aggregation, retention, and trend operation | OpenCode adapter |
| `dbsctr_knowledge_store` | DKS query lock contention and bounded fast fallback | None |

The user approved this complete context map on 2026-08-29.

## Delivery Slices

| Slice | Execution owner | Outcome | Depends on |
|---|---|---|---|
| `lifecycle-runtime-summary` | `build` | Source-local autonomous-runtime summary with truthful availability | None |
| `opencode-runtime-adapter` | `build` | Runtime boundaries emitted without manual prompt discipline | `lifecycle-runtime-summary` |
| `federated-cycle-trends` | `build` | Host/VM mean, p50, and p90 from immutable sanitized captures | `opencode-runtime-adapter` |
| `dks-fast-fallback` | `build` | DKS contention avoids repeated blocking failure | None |
| `safe-cycle-concurrency` | `build` | Proven-independent real-cycle work overlaps after benchmark qualification | `federated-cycle-trends` |

Discovery owns normative specifications and ticket scope. Build owns only the
implementation paths declared by its approved slice. Late changes to metric
semantics, quality equivalence, privacy, context ownership, or dependencies
reopen readiness.

## Measurement Contract

`autonomous_runtime_ms` is the union of complete helper-timestamped execution
intervals. It includes provider, tool, QA, and internal dependency waits because
they delay autonomous completion. Explicit operator and external-approval pauses
are excluded. An active interval may not overlap an excluded pause.

Calendar elapsed time remains `created_at` through `completed_at`. It is reported
separately and is never substituted for autonomous runtime. Aggregates include
mean, p50, p90, sample count, attribution coverage, and unavailable count. Fleet
reports stratify by source, context, risk, delivery intent, Method Revision, and
exact harness identity where available.

## Quality Boundary

Optimization may reorder or overlap only work proven independent by the existing
Execution DAG contract. Every required authority and gate still runs. Activation
requires at least five paired post-warmup runs, at least 10 percent lower median
wall time, equivalent required-gate digests, and no added failures or remediation.

No slice may weaken validation, remove security or data-loss handling, convert
missing evidence into success, infer operation timing from message persistence,
or tune provider behavior from mixed or unattributed cohorts.

## Privacy

Timing evidence remains source-local and sanitized. It contains no prompt,
response, file content, command argument, URL, credential, environment value,
absolute path, account identity, or raw OpenCode database row. Federation moves
only bounded summaries and explicit source availability.

## Baseline Caveat

The discovery sample contained 25 completed cycles with a 112-minute calendar
p50, but 11 had no phase profile and only one of 13 complete profiles showed
overlap. Several complete profiles covered only a small fraction of calendar
time. These values justify instrumentation but are not an autonomous-runtime
baseline and must not be used to claim improvement.
