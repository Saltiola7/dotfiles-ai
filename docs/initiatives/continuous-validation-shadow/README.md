# Opt-in continuous validation shadow

Status: specification preparation; implementation and runtime qualification are pending.

## Purpose

Reduce the delay between an agent's relevant edit and useful validation feedback without exhausting the developer machine. Reuse Python pipeline logic across local and later remote execution. The first delivery is an explicitly enrolled, advisory local experiment.

## Approved ownership

The operator approved the ownership map before context discovery. The continuous_validation context owns the new shared executor, scheduling, immutable snapshots, resource budget, telemetry and default-off enrollment. Existing DBSCTR lifecycle and Codex control-plane contexts retain checkpoint policy, formal gate admission, native session semantics and supported harness interfaces. Distribution retains installation and configuration ownership. Each consumer repository owns its commands, affected selection, coverage, runtime and infrastructure contracts.

The initial source slice implements the new context through additive interfaces. Changes to an existing context's authority must reopen that context's discovery rather than being hidden inside the executor. Consumer adapters are separate same-repository deliveries. A coordinator receipt is not cross-repository document-import authority.

## Decisions

- The feature is disabled by default. Enrollment is explicit for one DBSCTR worktree and task, not automatically inherited by other worktrees or users.
- Both participating repositories share one local compute budget. Foreground responsiveness has priority over background throughput.
- Stable file changes request bounded affected checks; DBSCTR checkpoints request expensive validation.
- Python owns pipelines and orchestration. Dagger executes Linux lanes; required native host checks retain their own backend.
- Current failures return to their exact originating Codex CLI primary session at a safe boundary. In-scope remediation is permitted.
- An idle session may be awakened only while its enrolled task remains open and a supported, fixture-qualified exact-session route exists.
- Targets, detailed cadence and later evidence reuse are decisions made from measurements.
- Remote compute is a follow-on experiment. Existing CI remains the enforcement and production-eligibility authority.

## Delivery boundary

The local-shadow slice includes the standalone runner, versioned repository check contract, default-off controls, snapshot and scheduling behavior, telemetry, Codex CLI transport qualification and one repository's generic adapter examples. Consumer-specific check definitions are delivered in their owning repositories without publishing private context here.

Runtime acceptance requires actual source-snapshot isolation, shared-budget execution and same-session feedback evidence. Mocked transport tests alone do not qualify an installed CLI. Unavailable Dagger or wake behavior is an explicit capability gap, never a pass. Feature activation may remain unavailable until these checks succeed; installing source does not enable it.

## Candidate artifacts and validation

The normative contract and Engineering Profile are in docs/specs/continuous_validation/. BUILD.plan.json records required kernel, integration, deployment, operation and maintenance gates; it does not register a cycle.

Validation covers default-off absence of background/network/session actions; enrollment isolation; dirty-snapshot identity and source races; conservative affected selection; coalescing and cancellation; platform-specific execution; resource caps and backpressure; current versus stale failures; duplicate and wrong-session refusal; opt-out; bounded telemetry and retention; active, idle and ended-session behavior. Configured publication and instruction authorities evaluate the exact staged candidate artifact set before receipt or publication.

## Native launch feasibility

Worktrunk created isolated Discovery and Build checkouts. Shared lifecycle registration already supports explicit validated checkout operations from Codex CLI and Desktop. The obsolete instruction requiring conversation relocation or Desktop attachment was corrected separately, installed locally, and preserved in source commit 7a2eebc. Missing Desktop attachment is not a launch blocker. Every operation must still target the selected checkout under actual native tool permissions; native session association and actor attribution remain unavailable unless independently verified. No workspace move or identity may be fabricated.

After the Discovery closure is committed, same-repository Build starts from the freshly fetched approved remote base and imports only the approved regular documentation closure. New profile import is supported. Fresh receipt and preflight must precede exact launch-digest approval; general implementation authorization is not that approval.

## Deferred work

Controlled remote execution and authoritative local-evidence admission are explicitly deferred. They do not block measuring an advisory local pilot, and they cannot be represented as delivered.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | not_applicable: the ownership table and canonical context specification own executable-system boundaries |
| Interaction | not_applicable: the canonical context specification owns request, execution and feedback sequences |
| State | not_applicable: the manifest is the authoritative slice-state inventory |
| Data/trust | not_applicable: the canonical context specification owns snapshot, result and session trust boundaries |
| Schema | not_applicable: the manifest and versioned context contract define canonical fields without duplicate diagrams |
| Dependency/deployment | not_applicable: one local source slice has no independently deployable dependency graph in this Initiative |
| Quantitative | not_applicable: no pilot measurements exist; comparisons are experiment designs, not measured charts |

## Build handoff

Scope: additive default-off local shadow. Risk: elevated because project code executes and diagnostics can cause agent work. Modules: Python and Security; Cloud applies when a remote-compute slice is prepared. Owner: repository operator. Delivery: draft pull request, with bounded local runtime qualification required for activation. Recommended primary: the current authorized Build agent once native launch eligibility and exact preflight approval are resolved. Helpers may own disjoint artifacts, never independent lifecycle state or integration.
