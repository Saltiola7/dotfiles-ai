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
| `dbsctr_v3_lifecycle` | Timing semantics, source-local summaries, History/Incident query reduction, dedicated knowledge privacy isolation, quality-equivalence policy, and safe concurrency | None |
| `opencode_control_plane` | Typed adapter timing boundaries, runtime correlation, optional DKS routing and value activation, and bounded DKS, History, and Incident availability | Lifecycle timing contract |
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
| `performance-audit-workflow` | `build` | Reproducible report-only audit and ranked optimization portfolio | `lifecycle-runtime-summary` |
| `runtime-query-recovery` | `build` | OpenCode attempts project- and revision-compatible DKS once within five seconds, then returns typed availability and continues | None |
| `history-incident-query-core` | `build` | Page-first aggregate History and bounded Incident summaries | None |
| `history-incident-runtime-recovery` | `build` | OpenCode returns bounded typed History/Incident availability | `history-incident-query-core`, `runtime-query-recovery` |
| `knowledge-privacy-lock-isolation` | `build` | DKS privacy guarding no longer contends with unrelated review-ledger work | None |
| `dks-routing-value-gate` | `build` | Automatic DKS routing remains enabled only when paired evidence beats direct source inspection | `runtime-query-recovery`, `dks-fast-fallback`, `knowledge-privacy-lock-isolation` |
| `performance-audit-v2` | `build` | Deterministic audit reduction, aggregate evidence, and verified source-absence handling | `performance-audit-workflow`, `history-incident-runtime-recovery` |
| `validation-evidence-reuse` | `build` | Exact unchanged validation is reused across applicable gates | `performance-audit-workflow` |
| `agent-context-budget` | `build` | Conditional subagents, reviewer enforcement, and bounded context growth | `performance-audit-workflow` |

Discovery owns normative specifications and slice scope. Build owns only the
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

## Audit Baseline

The 2026-08-29 audit found eight retained lifecycle cycles, three complete
autonomous samples, 37.5 percent timing coverage, a 28.8-minute autonomous p50,
and five gate-failure/remediation rounds. A separate 26-session sanitized cohort
contained 2,752 tool calls, 131 tool errors, a 495,327-token p50, and a
27,480,270-token p90. Nineteen members were review sessions and fourteen cycles
were active, so reviewer and model associations are confounded rather than causal.

The same audit reproduced DKS quality-lock failures, a 30-second history telemetry
timeout, and a direct Incident Scan exceeding 120 seconds. These are reliability
defects and optimization inputs, not evidence for removing lifecycle gates.

The 2026-08-30 follow-up retained those defects but changed cohort membership:
12 lifecycle cycles contained four complete timing samples, or 33.33 percent
coverage. It therefore does not establish improvement over the first audit. DKS
again failed on quality-lock contention, structured telemetry timed out once,
and Incident output overflowed. The delivered audit workflow itself followed its
one-shot fallback and privacy boundaries.

## Opportunity Portfolio

| Priority | Surface | Delivery boundary | Quality guardrail |
|---|---|---|---|
| P0 | Incident and history queries | Page first, aggregate in bulk, bound cancellation | Preserve snapshot, recovery, privacy, and exact availability semantics |
| P0 | DKS query locks | Shared verified fast path; exclusive repair only when required | Never query under unverified policy or bypass source authority |
| P1 | Validation reuse | Reuse exact command/commit/path/toolchain evidence across gates | Separate gate decisions and rerun after any identity change |
| P1 | Reviewer and context budget | Enforce explicit/critical review and milestone compaction | Compare equivalent cohorts; retain primary integration review and QA |
| P2 | Safe concurrency | Overlap proven-independent reads and read-only QA | Require paired benchmark gain and equivalent gate evidence |
| P2 | Automatic delivery | Remove avoidable operator wait after verified CI | Preserve protected-base, expected-head, and merge verification |
| P3 | Begin, Git, DVC, phase locks, deployment | Instrument before changing | Optimize only measured nontrivial cost |

## Reproducible Audit

`dbsctr-performance-audit` is the canonical report-only workflow. It reads the
source-local cycle summary, bounded sanitized review history, incident signals,
runtime health, fixed-commit source, and current authoritative external guidance
when material. It performs no review completion, incident mutation, lifecycle
mutation, claim, optimization activation, or raw-session export.

The workflow records unavailable tools once and falls back rather than retrying
them indefinitely. It checks for an existing Graphify graph before loading that
skill, keeps private telemetry out of hosted subagents, and uses at most three
independent Scout or Explore lanes. Every report separates measured findings,
source-backed unmeasured opportunities, assumptions, and rejected shortcuts.
Reports bind conclusions to one fixed source identity, Method Revision,
sanitized filters, evidence availability, cohort composition, attribution
quality, and coverage. Equal-priority findings sort by reproduced frequency,
confidence, lower quality risk, then lower effort. Private snapshot identities
remain local.

## DKS Recovery

DKS replacement builds retain separate writer serialization while query-visible
activation locks remain short. Queries continue against the prior policy-valid
active projection until replacement activation, and an activation that invalidates
quality policy restores baseline ranking atomically. OpenCode uses DKS only as an
optional accelerator for broad questions in a configured project. Exact-path,
fixed-commit, unconfigured-project, unavailable, or stale-revision work proceeds
directly to authoritative source inspection. One attempt shares one five-second
monotonic deadline across every internal stage; OpenCode maps exhausted or unsafe
retrieval to bounded typed unavailability and never retries automatically, turns
unavailable retrieval into citations, or exposes raw database, process, path, or
error details.

The DKS CLI preserves successful query JSON. Exhausted activation contention has
one machine boundary: exit `75`, empty stdout, and stderr exactly
`projection_busy`. Lock acquisition and one optional policy repair share a
two-second deadline. OpenCode, not DKS, owns the later model-visible availability
envelope.

## History Materialized Projection

History aggregate and Incident summary reads use one owner-private body-free
materialized projection instead of reconstructing membership and metrics from the
full OpenCode source. The lifecycle context owns this rebuildable cache. Bounded
maintenance derives session eligibility, exact ordering, source-heavy counters,
safe model/tool categories, and failure/recovery classifications while storing no
prompt, response, command, raw error, credential, or tool payload content.

Only an atomically ready generation may serve aggregate or summary queries. A
missing, preparing, source-incompatible, privacy-stale, or corrupt generation is
explicitly unavailable and returns no partial population. Incremental maintenance
builds immutable append-delta generations over one active chain and compacts
before depth sixteen. Captures bind one generation, so source append never changes
an existing continuation. Source replacement, rowid regression, schema
incompatibility, or a privacy tombstone invalidates affected state and requires
bounded rebuild. Ready queries read no source body columns; detailed History and
Incident modes remain independent of this projection.

DKS privacy guarding uses a dedicated lifecycle privacy lock. Unrelated review,
History, Incident, and capture work cannot block a query, while forget and expiry
mutations still cannot race cited result completion. Automatic routing remains
active only after a paired fixed-source benchmark shows no correctness regression
or added tool errors, p95 below five seconds, and at least ten percent lower median
completion time than direct authoritative inspection. A failed value gate disables
automatic routing without retiring the projection or manual CLI.
