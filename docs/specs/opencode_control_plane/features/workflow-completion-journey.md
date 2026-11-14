# Truthful workflow completion journey

Owner: OpenCode control-plane maintainer. Profile: [../PROFILE.md](../PROFILE.md).
Risk: elevated; source-only instruction/adapter compatibility slice. Depends on
[lifecycle reconciliation](../../dbsctr_v3_lifecycle/features/workflow-completion-reconciliation.md).

## User outcome

The primary carries Discovery's ready/done contract through amendments and
multiple PRs. Before announcing that only routine closure remains, it obtains the
supported structural completion report. It distinguishes delivered source,
deployment, acceptance, logical completion and optional cleanup.

Use existing native CLI/tools and guidance. Do not restore retired adapters,
manufacture session identity, bypass denied routes or add another lifecycle engine.
Shared Discovery/DBSCTR semantics remain lifecycle-owned; this context owns the
OpenCode presentation and supported primary journey only.

## Behaviors

- Given a proposed merge, amendment or fast-forward, inspect the supported
  completion capability before proceeding. Expose unsupported combinations early.
  Ordinary proved bookkeeping reconciliation needs no extra confirmation.
- Given a structural blocker, report classified cause, preserved state and the
  supported next action. Do not suggest private function calls, manual ledger
  edits, arbitrary retirement or repeated live tests as a repair.
- Given missing credentials or denied access, name the unavailable operation and
  stop that stage. A capability denial is not a reason to use another identity or
  repeatedly retry. Optional telemetry failure does not block source analysis.
- Given retained valid evidence, report it as reused with the original execution
  identity. Do not claim newly executed tests or current production observations.
- Given lifecycle completion with cleanup blocked, report completed/cleanup
  retained. Preserve the user's working copy and native conversation identity.
- Given unavailable writer permissions, return explicit capability_gap with owned
  artifact scope. The primary may continue only through already permitted access;
  delegation is optional and never required for readiness.
- Given shell pipelines, preserve the validator's actual exit code. An evidence
  identifier means evidence was recorded, not that its result passed.

## Interfaces and acceptance

Consume the existing CLI report with classified per-stage state: passed, blocked,
unavailable or not_evaluated; show evidence reuse separately from execution. Bound
messages must not expose private custody, raw errors, credentials or transcripts.
Unknown report versions produce capability_unavailable, not guessed success.

Qualify fixture journeys for multiple PRs/amendments, early structural refusal,
single credential prerequisite, stale evidence, private helper denial, idempotent
completion and retained cleanup. Verify shared lifecycle instruction contracts,
existing OpenCode tests and relevant Bun execution when typed adapters change.
No paid model benchmark or harness/provider migration is selected.

The source plan requires kernel, Review/Integrate and Maintain/Retire. Release,
Deploy and Operate are source-only N/A; installed route qualification belongs to
distribution. No claim that source instructions have already changed the host.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership flow below |
| Interaction | required: ordered journey below |
| State | required: outcome table below |
| Data/trust | not_applicable: canonical private-proof boundary is lifecycle-owned; no new transport |
| Schema | not_applicable: consumer of existing versioned report, no new store |
| Dependency/deployment | required: Initiative slice DAG |
| Quantitative | not_applicable: no latency/cost claim |

| Step | Owner and result |
|---|---|
| 1 | Discovery defines effective ready/done |
| 2 | Primary requests lifecycle preflight before consequential progress claims |
| 3 | Lifecycle proves or blocks reconciliation; primary acts only on supported results |
| 4 | Primary reports delivery, completion and cleanup separately |

| Observed outcome | User-visible interpretation |
|---|---|
| Proven done / retained checkout | Completed; cleanup retained |
| Merged / missing acceptance | Delivered source; completion pending |
| Structural refusal | Blocked with supported recovery, no speculative live reruns |
| Missing capability | Unavailable; retained work, no invented fallback |

**Text Equivalent:** Lifecycle owns truth and reconciliation. OpenCode's primary
checks that truth before claims, reports gaps accurately and separates completion
from cleanup. Canonical owner: control-plane maintainer; update with CLI report,
permission or user-journey changes.
