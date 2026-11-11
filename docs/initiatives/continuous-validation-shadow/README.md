# Opt-in continuous validation shadow

Status: source implementation and bounded local qualification; activation and
performance results remain separately evidenced. This document does not publish
live lifecycle gate state.

## Purpose

Reduce the delay between an agent's relevant edit and useful validation feedback without exhausting the developer machine. Reuse Python pipeline logic across local and later remote execution. The first delivery is an explicitly enrolled, advisory local experiment.

## Approved ownership

The operator approved the ownership map before context discovery. The continuous_validation context owns the new shared executor, scheduling, immutable snapshots, resource budget, telemetry and default-off enrollment. Existing DBSCTR lifecycle and Codex control-plane contexts retain checkpoint policy, formal gate admission, native session semantics and supported harness interfaces. Distribution retains installation and configuration ownership. Each consumer repository owns its commands, affected selection, coverage, runtime and infrastructure contracts.

The initial source slice implements the new context through additive interfaces. Changes to an existing context's authority must reopen that context's discovery rather than being hidden inside the executor. Consumer adapters are separate same-repository deliveries. A coordinator receipt is not cross-repository document-import authority.

## Decisions

- The feature is disabled by default. Enrollment is explicit for one DBSCTR worktree and task, not automatically inherited by other worktrees or users.
- Both participating repositories share one local compute budget. Foreground responsiveness has priority over background throughput.
- Stable file changes request bounded affected checks; explicit checkpoint requests
  make expensive validation eligible. Automatic lifecycle hooks remain outside
  this slice.
- Python owns pipelines and orchestration. Dagger executes Linux lanes; required native host checks retain their own backend.
- Current failures return to their exact originating Codex CLI primary session at a safe boundary. In-scope remediation is permitted.
- An idle session may be awakened only while its enrolled task remains open and a supported, fixture-qualified exact-session route exists.
- Targets, detailed cadence and later evidence reuse are decisions made from measurements.
- Remote compute is a follow-on experiment. Existing CI remains the enforcement and production-eligibility authority.

## Delivery boundary

The local-shadow slice includes the standalone runner, versioned repository check contract, default-off controls, snapshot and scheduling behavior, telemetry, Codex CLI transport qualification and one repository's generic adapter examples. Consumer-specific check definitions are delivered in their owning repositories without publishing private context here.

Runtime acceptance requires actual source-snapshot isolation, shared-budget execution and same-session feedback evidence. Optional local setup owns a dedicated 2-CPU/4-GiB/40-GiB ARM64 Lima worker with no host mounts or SSH-agent forwarding; it does not provision GCP. Mocked transport tests alone do not qualify an installed CLI. A synthetic open interactive Codex CLI 0.163.0 fixture exercised active delivery and idle wake; closed noninteractive execution remains unqualified. Queue acceptance remains distinct from observed consumption. Unavailable Dagger or wake behavior is an explicit capability gap, never a pass. Feature activation may remain unavailable until these checks succeed; installing source does not enable it.

## Candidate artifacts and validation

The normative contract and Engineering Profile are in docs/specs/continuous_validation/. BUILD.plan.json records required kernel, integration, deployment, operation and maintenance gates; it does not register a cycle.

Validation covers default-off absence of background/network/session actions; enrollment isolation; dirty-snapshot identity and source races; conservative affected selection; coalescing and cancellation; platform-specific execution; resource caps and backpressure; current versus stale failures; duplicate and wrong-session refusal; opt-out; bounded telemetry and retention; active, idle and ended-session behavior. Configured publication and instruction authorities evaluate the exact staged candidate artifact set before receipt or publication.

## Native launch feasibility

Worktrunk owns isolated task checkouts. Shared lifecycle registration supports
explicit validated checkout operations from Codex CLI and Desktop without
requiring conversation relocation or Desktop attachment. Commands use the
selected checkout explicitly and native tool permissions remain authoritative.
An exact caller-supplied session UUID does not authenticate actor identity or
establish native session association. No workspace move or identity is fabricated.

Source implementation uses the registered lifecycle authority. Current cycle
registration, gate results, exact runtime identities and qualification artifacts
remain private. The source [runbook](../../specs/continuous_validation/README.md#local-pilot-runbook)
covers read-only engine planning, explicit optional setup, per-worktree enrollment,
bounded watching, explicit checkpoints, observation comparison, and separate
enrollment/VM stop controls. There is no automatic lifecycle hook or always-on
service. The [Engineering Profile](../../specs/continuous_validation/PROFILE.md#local-runtime-platform-contract)
records local resource ownership, drift checks, network boundaries, recovery,
maintenance pins and authorized disposal.

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
| Dependency/deployment | required: the canonical profile and source runbook identify the optional dedicated VM, private socket, pins, rollout, and separate stop/disposal boundaries |
| Quantitative | not_applicable: no pilot measurements exist; comparisons are experiment designs, not measured charts |

## Build handoff

Scope: additive default-off local shadow. Risk: elevated because project code executes and diagnostics can cause agent work. Modules: Python, Security, and Cloud for the optional local runtime bootstrap; remote compute remains deferred. Owner: repository operator. Delivery: draft pull request, with bounded local runtime qualification required for activation. The registered Build primary owns current evidence and delivery decisions. Helpers may own disjoint artifacts, never independent lifecycle state or integration.

## Checkpoint and CLI feedback follow-up

The `checkpoint-cli-feedback` slice extends this Initiative with post-Gate-Commit
private enqueue, complete bounded pytest identity evidence, and typed existing
Codex/OpenCode CLI feedback. The existing ownership map remains authoritative: the
lifecycle owns successful durable events, the shared runner owns admission and
freshness, and native control planes own transport. See the normative
[follow-up contract](../../specs/continuous_validation/SESSION-HOOKS.md) and its
explicit default-off activation and bounded qualification requirements. This is
source readiness, not a claim that hooks or current native transports are active.

## Optional Vertex review follow-up

The `vertex-pr-agent-review` slice adds an independently default-off PR-Agent
review at opted-in checkpoints or manual requests, using the same immutable
snapshot and shared local admission authority. The controller owns this generic
diagnostic capability; repository test adapters remain unchanged. The
[review contract](../../specs/continuous_validation/PR-AGENT.md) defines pinned
image execution, private advisory artifacts, explicit Vertex configuration and
existing-session completion references.

Interactive authentication stays with the existing isolated credential owner
on the operator's Mac. The native Vertex route explicitly transfers an
authorized-user ADC as an ephemeral Dagger secret to the pinned review process;
it does not mount the host credential directory or claim token-only isolation.
Authentication renewal never starts from a background review. OpenCode receives
bounded private review references through its qualified existing-session route;
using OpenCode as an inference proxy is deferred.

This source/install slice includes bounded offline and synthetic-provider
qualification. It makes no live provider call, private-source disclosure,
metered-model-quality claim, remote-compute rollout or global activation.
Configuration and interactive authentication must be established before a later
explicit real-provider qualification. Existing CI and formal gate authority
remain unchanged.

## Bounded storage repair follow-up

The `bounded-storage` slice repairs Python audit findings PY-03/PY-04 in the
existing `continuous_validation` context. The [storage contract](../../specs/continuous_validation/STORAGE.md)
defines bounded reference journals, query-only replay, whole-selection capacity
reservation, generation ordering and preserved legacy evidence. INT-032 through
INT-042 cover this repair without changing the approved context ownership map.
The committed [applicability plan](STORAGE.plan.json) supplies the same required
Python/Security development, deployment, operation and maintenance gates.

The implementation prerequisite is the already merged local-shadow source; no
unimplemented predecessor delivery is introduced. Private runtime activation is
not a launch prerequisite or a claim made by a ready slice. Discovery authority
stays on its local branch and is imported into one implementation PR through the
existing receipt/preflight route. Targeted private deployment and merge require
the selected checks and native protections; preflight never registers a cycle or
implements the repair. Oversized-journal recovery tools, compact public responses
and adjacent store-count admission remain outside this slice.
