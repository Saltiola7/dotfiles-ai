# Rebased delivery and validation handoff

Discovery amendment, 2026-11-10. The operator approved the context map below
and narrowed this chat's source slice to reusable lifecycle support. This is
specification authority, not evidence of implementation, installation or launch
approval. The Initiative remains discovering for its other work.

## Outcome and current slice

Many independent tasks may develop concurrently. An authorized task remains
responsible until its changes reach the selected default branch. Required CI
failures must return to that task for diagnosis, code correction and renewed
validation. Repeated execution of unchanged failing code is not that repair loop.
The operator did not approve a fixed three-failure stopping rule for this journey.

Preserve individual phase commits on the default branch using rebase-and-merge;
new object IDs are acceptable. Retain original evidence and verified original-to-
landed correspondence, then allow separately guarded retirement. A hash change
alone does not restart the six development phases or require renewed delivery
consent. Material scope, behavior, authority or risk changes still require the
operator. Preserve independent progress while one task needs a decision.

The first Build slice is `rebased-completion-core`, specified by
[rebased delivery](../../specs/dbsctr_v3_lifecycle/features/rebased-delivery.md).
It extends external completion, evidence retention and the delivery-preservation
predicate. It does not implement a queue, runner, service, CI transport or new
repair agent. The existing Dagger work owns adoption of those interfaces after
its cutover. The original merge-commit route and historical records remain valid.

## Approved context map and ownership

| Existing context / home | Responsibility | Dependency for this amendment |
|---|---|---|
| `dbsctr_v3_lifecycle` / coordinator repository | Rebased delivery proof, phase attribution, completion, preservation predicate and lifecycle-side repair authority | Existing external completion and retirement contracts |
| `dotfiles_ai_distribution` / coordinator repository | Default-off installation, personal preferences, repository/task overrides and later coordinator configuration | Qualified lifecycle capability and selected deployment contract |
| `continuous_validation` / coordinator repository | Existing Dagger execution, failure-feedback interfaces and later queue integration | Lifecycle receipt capability; repository-owned validation contracts |
| Existing consumer toolchain / each governed consumer repository | Required checks, affected selection, native CI triggers and local policy qualification | Shared interfaces; consumer-owned CI cutover |

The consumer row is an approved adjacent boundary. Its private identity, source,
configuration and results do not enter the public manifest. Its existing owner
must persist exact adopter changes in the governed repository; no synthetic
public repository identity is substituted. Existing native control planes own
their session transports; this amendment does not add a transport or relocate
conversations. Previously approved continuation slices remain independent.

## Dagger adoption contract

| Condition | Required behavior and owner |
|---|---|
| Personal delivery policy selects draft PR, ready PR, normal merge or configured administrator merge | Preserve the selected outcome; shared automation remains off by default. Distribution owns configuration; lifecycle owns enforcement |
| Operator enables rebase preference for initial adopters | Apply the personal preference with repository/task overrides; do not reinterpret a generic setting as administrator permission |
| Work is ready | Queue owner orders final integration and validates the candidate containing its predecessors; a private integration branch alone is not delivery |
| Required candidate checks are green | Merge through an authorized native route and retain its native outcome; the original task consumes it through the qualified completion proof when its checkout is available |
| Required CI fails for the current task revision | Deliver current diagnostics through the qualified existing-session interface; the owning agent diagnoses and changes code through DBSCTR, then validates the new revision |
| The agent is active, or idle in an open enrolled session | Use its native safe-boundary input/resumption route, preserving task ownership and existing authorization |
| The originating agent is unavailable or the task is closed | Preserve repair work for resumption; no new agent or fabricated session. Independently available merge coordination may finish already-qualified queued work |
| The developer computer is asleep or offline | Queue coordination remains independently available; local receipt reconciliation waits until the retained checkout is available. Choosing and qualifying that runtime belongs to the Dagger/deployment work |
| Only commit IDs, routine reconciliation or repair details change within approved intent | Revalidate affected evidence and update delivery correspondence without a new user merge checkpoint solely for changed hashes |
| Requirements conflict, scope/risk changes or needed authority is absent | Ask about that task, retain its evidence and keep unrelated eligible tasks moving |
| A caller claims native queue availability or review exemption compatibility | Verify the capability; use the coordinated alternative where qualified, rather than assume an administrator flag enrolls a queue |
| A native route cannot enforce current required checks or prevent stale-base delivery | Report unavailable; passing an earlier PR run is insufficient |

The existing [checkpoint and feedback contract](../../specs/continuous_validation/SESSION-HOOKS.md)
already owns typed enrollment, current-source identity, safe-boundary dispatch,
duplicate suppression and native session transport. It remains advisory until
the owning pipeline qualifies formal validation use. Do not equate diagnostic
feedback with a gate pass or reuse old evidence for changed integration content.
Required affected checks remain before the default branch; consumer-owned full
validation remains before production. Earlier qualified validation may reduce
work left at integration; this source slice grants no new evidence-reuse authority.

The existing [supervised repair contract](../../specs/dbsctr_v3_lifecycle/features/supervised-ci-repairs.md)
is a different, explicitly approved reservation route with its own budget and
approval rules. It is not a complete implementation of this desired autonomous
loop. The Dagger adoption owner must reconcile that boundary explicitly; neither
reset its counters nor present its three-attempt cap as newly accepted intent.
Transport backoff, duplicate events and changed-code repair are different concerns.

## Slices, readiness and launch

| Slice | Execution owner | Current scope/state | Dependency |
|---|---|---|---|
| `rebased-completion-core` | build | First source slice; specification ready after document validation, implementation and launch feasibility unverified | Existing merged source; no dependency on a new queue |
| `rebased-delivery-policy` | discovery | Deferred installation, personal defaults and per-repository activation | Delivered core and a qualified deployment plan |
| `dagger-delivery-adoption` | discovery | Deferred to the existing Dagger work: independent queue, CI-to-agent loop and consumer integration | Delivered core and existing validation/consumer qualification |

All accepted intent is covered by INT-055 through INT-079 in MANIFEST.json.
Deferred means outside this small source slice, not rejected user intent. In
particular, high-concurrency integration, offline coordination and repair feedback
are still desired; this amendment does not claim they are delivered by ID mapping.

Build owns the first source implementation in the existing lifecycle context.
Use [REBASED-COMPLETION.plan.json](REBASED-COMPLETION.plan.json), import this
slice's entire changed-document closure, and preserve other Initiative work.
The first slice may change only the existing lifecycle helper, affected completion
and retirement tests, necessary lifecycle usage guidance and its listed authority
documents. It must not edit Dagger execution, CI workflow YAML, repository settings,
native transports or another task's implementation.

The source baseline is commit `15993ed65b7b14b8e23f7b0283e0af0d6b6bf5db`.
Configured publication authority is the publication/instruction check in
`.github/workflows/test.yml`, including the tracked-file inventory in
`tests/test_portable_distribution.py::test_public_tree_has_no_maintainer_identifiers`.
Stage intended additions before running it; a manifest check alone is insufficient.
Run `initiative-check` after every material manifest change. After all publication
checks pass, a Build-owned ready slice may issue its fresh receipt.

Discovery does not register a cycle. Build must first perform exact Initiative
preflight in an explicit Worktrunk checkout and present scope, risk, target and
launch digest for approval. No-upstream Discovery branches do not justify an
extra publication. Same-repository draft delivery carries this documentation with
implementation. Launch feasibility remains unverified until that preflight.

## Risks and deferred decisions

- One-to-one, content-preserving rebase is the bounded first capability. Dropped,
  squashed, reordered, conflict-edited or unprovable commits cannot acquire a
  successful correspondence merely because the final tree looks similar.
- Internal evidence refs retain old Git objects without keeping feature branches
  open. They consume storage and require the existing private repository backup
  and retention owner; they are not themselves an off-host backup.
- Review-exception compatibility with a native queue is a qualification concern.
  The first usable integration path must not depend on obtaining new organization
  approval, and it must preserve required CI and linear-history obligations.
- Queue hosting, its native safeguards, resource/backoff policy and the exact
  consumer cutover remain with Dagger adoption. No fixed source-repair count was
  settled here. Missing external capability is a blocker, not a fabricated pass.
- Current cleanup may have unrelated native/data-preservation blockers. Proving
  rebased delivery satisfies only the history obligation; it cannot remove them.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: approved context table; who owns each source and adopter interface? |
| Interaction | required: adoption table; how do CI, the original agent and completion interact? |
| State | required: slice/readiness table; what is specified, deferred or launchable? |
| Data/trust | required: ownership/adoption tables; what stays private and what confers authority? |
| Schema | not_applicable: the lifecycle feature owns the canonical receipt extension |
| Dependency/deployment | required: slice table; what can ship before Dagger cutover? |
| Quantitative | not_applicable: no performance result or numerical readiness claim |

**Text Equivalent:** The lifecycle source slice supplies verified rebase
attribution and preservation. Distribution later installs and configures it.
The existing Dagger owner integrates execution, an independently available queue
and feedback to the original enrolled agent; consumer repositories retain their
check authority and private details. Source delivery precedes separately qualified
activation. Failed CI returns to coding; material ambiguity returns to the
operator; unrelated work may continue. Source: INT-055 through INT-079 and the
linked contracts. Owner: delivery Discovery primary. Update these tables and
this equivalent whenever scope, ownership, failure handling or dependencies change.
