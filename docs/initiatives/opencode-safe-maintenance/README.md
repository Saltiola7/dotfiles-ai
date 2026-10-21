# Safe OpenCode maintenance and exact client recovery

## Discovery status

This Initiative captures the requested update-workflow repair. The operator approved the context map and source-only draft delivery, selected
refusal when safety cannot be proved, and selected a separate explicit maintenance
command with native commands unchanged. The [feature contract](../../specs/dotfiles_ai_distribution/features/opencode-safe-maintenance.md)
records implementation readiness. Registration still requires fresh receipt,
preflight and exact launch approval.

## Requested outcome and constraints

Preserve exact pane/session mappings, active work, pending forms and permission
requests across managed update preparation and qualified recovery. The native
installer remains the sole binary owner. All implementation and validation in
this delivery use isolated state and fake runtimes. Do not restart, signal,
replace, reload or send input to live OpenCode or Herdr; do not apply managed
configuration or modify the live recovery manifest/database.

Use immutable private checkpoints, stable server/pane/process identities and a
per-pane recovery assessments. Executable recovery and its action journal remain
outside this first delivery until native preservation capabilities are qualified. Preserve unobserved mappings as uncertain instead of
forgetting them. Distinguish viewed child session from owning root and canonical
session directory from process cwd. Permit multiple views of one session.

No replay may submit prompts, approve permissions, answer forms, create an absent
conversation or overwrite a changed pane occupant. Unsupported or incomplete
state must be explicit. Native drain, exact client-state export and passive attach
are not qualified by current evidence. A wrapper lock and repeated idle polls do
not prevent new submissions by existing clients or direct native callers.

## Approved context map

| Existing context | Ownership | Dependency |
|---|---|---|
| shell_auth_startup | Durable capture, exact recovery identity, client preservation and recovery fixtures | None |
| dotfiles_ai_distribution | Explicit maintenance CLI, managed update guards, native installer delegation and source delivery | Recovery contracts from shell_auth_startup |

Both contexts belong to this repository. One coordinated source delivery should
carry the agreed contracts and implementation; independent slice workers are not
requested. Python, Security and Cloud modules apply. Risk is critical because an
incorrect generated lifecycle operation could disrupt broad active work or grant
permission unintentionally. No risk exception has been accepted.

## Settled decisions

1. Deliver one source-only draft PR using the approved two-context ownership map.
2. Refuse activation/replacement when safety cannot be proven. This delivery prepares
   and preserves recovery evidence; current missing native capabilities remain hard
   blockers for apply/recover, without a force override.
3. Add a separate explicit maintenance command; keep native managed update/restart
   behavior unchanged. Native TUI/direct-binary bypasses remain outside this command.
4. Add a supported read-only CLI observer for exact route/tabs. Draft and passive
   detach capabilities remain unavailable; no live observer registration is allowed.

## Existing authority and source ownership

Reuse `docs/specs/dotfiles_ai_distribution/features/native-platform-updates.md`,
`docs/specs/dotfiles_ai_distribution/features/opencode-v2-session-recovery.md`, and
`docs/specs/shell_auth_startup/` rather than duplicating their durable contracts.
The distribution Product Intent remains selected. Existing generated Herdr
integration must not be hand-edited as a durable extension.

Primary owns integration and lifecycle registration. Bounded helpers may research
or review explicitly assigned material; they do not stage, commit, register cycles,
push or deploy. Preserve unrelated and unmerged recovery worktrees.

## Validation and gates

Early publication/instruction authority is the configured CI pytest invocation
covering the public-tree policy, OpenCode control-plane and DBSCTR instruction
contracts. Stage intended new artifacts before the tracked-file publication
check. Use synthetic paths, identifiers and service credentials in fixtures.

Recovery and native-distribution fixtures must prove refusal for active work,
forms, permissions, drafts, unknown state, missing session identity and changed
occupants. Cover duplicate views, viewed descendants, transient metadata loss,
readiness failures, concurrent maintenance, and interruption at each journal step.
A fixture result is not live deployment or native hot-upgrade qualification.

All Development Kernel gates, Review/Integrate and Maintain/Retire are required.
Release, Deploy and Operate are not applicable to this source-only delivery;
future activation requires separate qualification and authorization. Gate results
remain pending until registered, evidenced execution. Final feature-branch push and
draft PR follow passing gates; no live deployment or restart is authorized.

## Visual Evidence

Boundary: required; context ownership table above. Interaction: not_applicable at
capture; sequence awaits activation policy. State: required; readiness table below.
Data/trust: required; private checkpoint and public fixture boundary in the prose
above. Schema: not_applicable until persistent contract is selected.
Dependency/deployment: required; context dependency table and source-only delivery
boundary above. Quantitative: not_applicable; no performance claim is made.

| State | Required evidence | Permitted next step |
|---|---|---|
| Captured | Requested outcome and proposed context map | Resolve operator decisions |
| Context approved | Approved ownership and safety policy | Amend context specifications |
| Specification ready | Publication checks, manifest check and complete contracts | Exact launch preflight |
| Launch approved | Fresh receipt and explicit digest-bound approval | Register isolated DBSCTR cycle |

**Text Equivalent:** Discovery captures the scope first. Operator decisions permit
context specifications. Passing artifact checks permit preflight. Only exact
launch approval permits cycle registration. None of these states authorizes live
activation. Canonical owner: Initiative maintainer; refresh when scope, ownership,
safety policy or delivery authorization changes.
