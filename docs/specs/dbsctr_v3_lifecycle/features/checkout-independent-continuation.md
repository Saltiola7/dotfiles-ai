# Checkout-Independent Continuation Contract

Status: specification ready; implementation and native qualification pending.
Authority: [corrective Discovery](../../../initiatives/dbsctr-delivery-lifecycle/CHECKOUT-INDEPENDENT-CONTINUATION.md)
and INT-035 through INT-049. Profile: `../PROFILE.md`; critical risk. Owner:
dotfiles operator. Python, Security and ML/AI modules apply. Source-only core
delivery is a feature-branch draft PR; adapter and host rollout are dependent
slices. No Cycle Record rewrite, live binding or relocation occurs during core.

## Identity And Record Validation

Keep Cycle Record schemas 3/4/5 and their existing IDs unchanged. Their recorded
source and runtime locators are provenance, not mandatory live source resources.
`read_cycle_record` validates complete structure, locator syntax, activation and
generic/legacy agreement without resolving historical checkout availability.
Source-dependent actions, including source synchronization and legacy native
attachment, must explicitly resolve and validate their required source. Missing
source never permits updating a different checkout. Report unavailable provenance
without changing attribution. Historical reports remain immutable.

Use one random 128-bit lowercase-hex **binding ID** per physical Git registration,
scoped to the existing owner-private repository continuation store. Do not replace
`worktree_id()` globally or recalculate old record IDs. Existing branch/path IDs
remain legacy aliases, not physical identity. No second global registry or daemon.

Binding creation validates all of: exact native primary/repository identity;
resolved common-Git-directory equality; membership in Git's registered worktree
list; Git administrative-directory and worktree back-reference agreement; safe
filesystem custody; unambiguous current active pointer; structurally valid exact
Cycle Record; matching legacy recorded worktree identity and expected branch.
The historical source need not exist. A mismatched legacy target cannot be bound
by guessing its branch, path, newest record or equal remote URL.

Record the administrative directory's path relative to the common directory
(`.` for its primary worktree), and its device/inode plus the common directory's
device/inode as local replacement-detection evidence. Record the resolved
worktree locator privately. Identity is the random binding plus validated custody,
not those filesystem numbers alone. A branch change preserves physical binding
but invalidates cycle writes when it violates the recorded branch constraint.
Distinct detached registrations have distinct binding IDs; this does not allow
starting or writing a branch-constrained cycle on detached HEAD.

Revalidate Git registration, back-references, custody and recorded locator before
using a bound target. Missing/replaced administrative directories, changed common
directory custody or changed locator require explicit future relocation/rebinding
authority. Never follow a stale binding to a replacement registration. Ordinary
check, attach and bind cannot update an existing binding's locator. A supported
future move may preserve binding ID only under its own approved transaction;
implementing that move belongs to relocation, not this slice.

## Additive Private Schema

Retain companion metadata version 1 and existing cycles, routes, operations,
activations and approvals. Add the following tables only in an explicit successful
v2 enroll/bind/recover/release transaction under the existing state lock and `BEGIN IMMEDIATE`.
Missing tables mean legacy-only capability, not corruption; read-only commands
never create them. A partial/incorrect present table set is invalid state.
Existing table rows are not bulk rewritten. Foreign keys are enforced.
Legacy route-only recovery/release may create the complete empty binding table set together
with its route version and receipt; this does not activate or bind any cycle.

| Table | Key / relationship | Exact additional columns |
|---|---|---|
| `worktree_bindings` | `binding_id` TEXT PK, 32 lowercase hex | `git_dir_relative` TEXT UNIQUE; `common_dev`, `common_ino`, `admin_dev`, `admin_ino` INTEGER; `locator` TEXT; `registration_digest` TEXT (64 lowercase hex) |
| `cycle_bindings` | `cycle_id` TEXT PK references cycles; `binding_id` TEXT references worktree_bindings | `legacy_worktree_id` TEXT; `record_identity_digest` TEXT (64 lowercase hex); `protocol` INTEGER CHECK = 2 |
| `route_versions` | `session_key` TEXT PK | `version` INTEGER >= 0 and <= 2^53-1 |
| `control_requests` | `(session_key, request_id)` TEXT composite PK | `request_digest` TEXT (64 lowercase hex); `response` TEXT (bounded JSON) |

One registration may have successive cycle bindings, but at most one active cycle
may use it. Cycle rows and bindings remain as history after completion. Route
versions are retained even when routes are deleted: every selection creation,
replacement or release advances the version, even when activation is identical.
Old routes have conceptual version 0 until their first v2 mutation. Every new-helper
route mutator, including legacy attach/completion/recovery, advances a present
route version so a release snapshot cannot survive another selection.

V2 attach may replace a reader selection but must refuse replacement while the
caller still owns a different selected cycle's writer. Require explicit release
first; never leave an orphan writer behind a new route. Same-cycle attachment
retains ownership semantics and still advances the route version on a successful
new selection request; receipt replay does not advance it again.

`record_identity_digest` hashes canonical JSON of cycle ID, record schema,
recorded worktree ID and recorded branch. It excludes mutable gate state, source
availability and absolute runtime locations. `registration_digest` hashes the
canonical private registration fields above except itself and binding ID. Validate
the actual fields and repository boundary, not a digest alone. File ownership,
symlink/hard-link, SQLite integrity, bounds and storage-recovery safeguards from
[canonical continuation](canonical-continuation.md) continue to apply.

**Text Equivalent:** Repository-private registration bindings identify physical
worktrees. Existing cycle rows reference them through an additive compatibility
table while retaining legacy record IDs. Existing session routes retain their
cycle relation and acquire monotonic versions. Request receipts are keyed by
native actor and request identity, independently of mutable routes. No private
path, inode or native session key enters public Git or typed diagnostic output.
Lifecycle Discovery owns this schema and updates it when identity or replay
relationships change.

## Explicit Compatibility Activation

New v2 enrollment atomically performs existing approved enrollment plus binding.
For already-enrolled cycles, v2 `bind` requires exact current state approval,
no outstanding operations and no writer. Use separately approved legacy ownership
recovery first where needed; bind neither recovers nor claims a writer. Its
confirmation includes exclusion of nonparticipating old runtimes for that cycle.
The source-validation correction permits this legacy recovery when only historical
source lookup was broken. Ambiguous target identity still cannot be upgraded.

Binding does not change generation or clear routes; it records compatibility
and physical identity. Existing enrollment/history is preserved. Other cycles
remain v1 unless explicitly activated; no repository-wide enrollment or pause.
Creation of a shared registration binding never activates a different cycle.

The new helper accepts the exact existing v1 response schema. On a v2-bound cycle,
v1 check/mutation/finish return existing `revision_incompatible` without mutation;
v1 checks may identify the cycle but never return usable admission or approval.
Unbound v1 behavior remains compatible, apart from corrected source-independent
structure validation. Old installed executables cannot obey tables they do not
know: exclude those writers before bind. Test old adapters against the new helper,
new adapters against old helpers, and affected Codex v1 conformance. Native Codex
v2 capability is not delivered here and must not be inferred from core support.

## Versioned Local Interface

Add `dbsctrctl continuation-v2 --request-json -`. The protocol version is selected
by command and `schema_version: 2`; never add fields to v1 or retry failed v2
mutations through v1. Unknown fields, actions or protocol versions refuse before
mutation. One request is <=64 KiB; responses <=64 KiB; at most 100 outstanding
operations/diagnostic entries. Use existing two-second lock-admission deadline;
never replay a transaction body after contention. No free-form diagnostics.

Every request contains exactly `schema_version`, `action`, `session_id`,
`message_id`, `runtime_worktree`, `runtime_directory`, `harness_activation`, plus
the action fields below. These identity fields are adapter-supplied native
evidence, not typed model arguments. Existing native-context validation applies.

| Action | Additional fields | Behavior |
|---|---|---|
| `check` | optional `worktree`; optional `for_action` (defaults check); optional `mode` / `target_session_id` only for matching attach/handover preparation | Inspect explicit target or exact stored route, never select by recency; emit only a binding appropriate to the prepared action |
| `enroll` | `worktree`, `request_id`, `expected`, `approval` | Existing enrollment consent plus exact registration binding; no writer claim |
| `bind` | `worktree`, `request_id`, `expected`, `approval` | Explicit compatibility activation for enrolled reader-only cycle |
| `attach` | optional `worktree`; `request_id`, `expected`, `mode`; optional `approval` for provider change | Validated bound cycle selection; existing reader/writer authority rules |
| `admit` | `expected`, `call_id`, `operation_class` | Exact owned-cycle admission; existing class allowlist and call replay rules |
| `finish` | `operation_id`, `outcome` | Exact admitted operation completion or uncertainty; bind through stored operation, not current source or route |
| `handover` | `request_id`, `expected`, `target_session_id`, `approval` | Existing explicit drain/transfer with generation fencing |
| `recover` | optional `worktree`; `request_id`, `expected`, `approval` | Exact-state quiescence recovery; invalid targets require the caller's stored route, never guessed target identity; no automatic writer claim |
| `release` | `request_id`, `expected` | Release only current actor's snapshotted route and eligible ownership |
| `resolve` | `expected` | Return private local target only after full execution-target validation; never expose that payload as a typed tool result |

`request_id` uses existing opaque-ID grammar; the adapter supplies native call
identity for retry, never model-supplied consent. `approval` remains exactly
`{receipt_id, binding}` from a native permission interaction; its binding equals
`expected`. No approval boolean or raw shell environment grants authority.

Every response has exactly these fields:
`schema_version`, `ok`, `reason`, `cycle_id`, `state`, `generation`,
`writer_relation`, `binding_id`, `route_version`, `activation_changes`,
`checks`, `next_action`, `expected`, `operation_id`, `event_id`, `request_id`,
`replayed`, `local_target`.

`schema_version` is 2; booleans are actual booleans; cycle/operation/event/activation
types retain v1 validation; generation and route_version are safe nonnegative
integers or null when unknown; writer_relation is self/other/none or null when
unavailable, never default none on failed inspection. Binding ID is 32 hex or
null. Optional-result fields are null, not omitted. `local_target` is null except
successful resolve; there it is exactly `{path, binding_id, registration_digest}`,
with an absolute canonical path kept solely inside the local adapter. The adapter
rechecks before admission and never logs/returns this local payload to the model.

`checks` has exactly `source`, `target`, `ownership`, `storage`. Each contains
exactly `status` (available, unavailable, not_requested) and `reason` (null for
available/not_requested, otherwise a reason below). Source availability is
informative unless the requested operation actually uses that source. Check may
succeed with target unavailable and still permit a narrowly scoped release.
No selection yields null cycle/generation/version and `select_target`.

Reasons are the existing v1 reasons plus `source_unavailable`, `branch_mismatch`,
`registration_missing`, `registration_changed`, `binding_required`,
`route_changed`, `protocol_unavailable`, `capacity_unavailable`. Next actions are
the existing v1 actions plus `bind`, `release`, `restore_target`; none never implies
permission. Unknown values reject. Check reason reports the first blocking class
in native/repository, storage, binding, registration/branch, ownership order;
informative source failure remains in checks.source rather than masking eligibility.

`expected` is null or exactly `{action, cycle_id, binding_id, generation,
route_version, state_digest, record_digest, registration_digest, session_key,
activation_digest, mode, target_session_id}`. Digests are 64 hex; mode and target
session are null unless relevant. Record/registration digests may be null only
for route-only recovery/release inspection when those resources are unavailable. A missing
binding ID is permitted only before enroll/bind or for legacy route-only recovery/release.
All other action-required authority must be available. Snapshot hashing uses
canonical JSON and binds the selected route, current writer, pending operations,
activation and requested action. Legacy route inspection includes its exact stored
cycle/locator identity in state_digest without accepting an unknown live target.

Apart from explicit enroll/bind, route-only `recover` and `release` are the only
v2 mutations permitted on an unbound legacy cycle; this allows
escape from an invalid old selection without guessing or upgrading target identity.
It uses exact native/repository/store/route authority, never live target authority.
Storage repair retains the separately approved existing physical-recovery protocol;
unreadable or unsafe storage cannot issue a logical release or recovery binding.

### Approved Route-Only Recovery Amendment

INT-049 records the operator-approved correction after the original core launch.
Preserve the original receipt, failed regression and reopened-readiness evidence;
this amendment neither rewrites launch history nor asserts live quiescence.

If target validation fails, recovery may use only the caller's authenticated stored
route in a verified same-repository private store. An explicit worktree must not
select an alternative cycle: refuse if it cannot be corroborated with that route.
Bind native actor/activation, exact cycle row, generation, route version, complete
outstanding-operation set and available record/registration evidence. Recheck under
the mutation lock after separate exact operator confirmation that prior writers
and outstanding work are quiescent. Never derive approval from this design consent.

Approved recovery retains every operation with operator-quiescence attribution,
clears writer and advances generation atomically. It preserves selection for an
explicit subsequent release. A validated terminal record or already-closed state
remains closed. Otherwise reader_only means no writer, not a valid active target;
attachment/admission still require full live record, registration and branch
validation. Missing target evidence is never repaired or inferred by recovery.
If record state becomes available as terminal, reconcile to closed before any
attachment; never revive completed work. No target file or Cycle Record changes.

Cover unbound legacy and bound targets, missing active pointer/registration/record,
stale approval, denied consent, another writer, unsafe storage and operation races.
Show that recovery followed by release restores control without admitting target
writes; old-generation operation completion remains fenced.

## Atomic Release And Replay

The typed `dbsctr_continuation_release({})` selects only its caller's stored route.
It prepares a release snapshot internally and applies it without a redundant idle
writer confirmation. No worktree/session arguments permit releasing another actor.
For a reader, remove only its route. For the current writer require owned state
and zero running/uncertain operations, then clear writer, increment generation,
return cycle to reader_only and remove route in one transaction. Draining or
recovery_required remains a recovery blocker even with no pending rows. Completed
cycles retain closed semantics; release never makes them active/reader_only.

For enroll/bind/attach/handover/recover/release, check stored request receipt after
authenticating native/repository custody but before requiring a live route or
target. Same actor/request ID plus identical canonical request returns saved
response with replayed=true and no writes; changed body returns invalid_state.
No receipt is created for a refused transition. Insert successful receipt atomically
with all authority changes. Exhausted safe counters or size bounds refuse without
partial state changes. No automatic receipt expiry or pruning.

A reader with no caller-owned outstanding operations may release while another
writer is busy; that other writer's operations and generation are unchanged. If
the caller has an outstanding operation from a prior ownership generation, require
its existing exact completion/recovery disposition before removing its route.

A successful release response identifies the released cycle and pre-release
route_version, plus resulting cycle generation/state. The adapter may clear a
cache only if it still names that exact cycle/version. Before the next tool, read
durable selection afresh. Replaying an old release cannot clear a later attachment,
including reattachment to the same cycle. Lost callbacks retain existing operation
uncertainty semantics; only exact completion or approved quiescence resolves them.

## Native Adapter And Lifecycle Consumers

Extend typed preflight with v2 capability/diagnostic projection and add typed release
to Build permission rules; Plan has diagnostics only. No model identity or approval
fields are exposed. Capability discovery is read-only; old helper absence is
protocol_unavailable, not permission to fall back after a v2 mutation attempt.
Legacy unbound sessions remain qualified for their old path until explicit bind.

Keep controls outside generic mutation admission. A known invalid execution route
must not block typed diagnostic/status controls; status reports validated bounded
record facts and availability without inventing a valid execution target. Generic
shell calls still require admission, even if their text claims read-only intent.
No arbitrary shell classifier or new general filesystem permission is introduced.

Resolve through the helper's private local interface, consume path only internally,
and associate caches with cycle plus route_version. Revalidate generation/binding
at admission. Common-directory cache alone is not custody evidence. On protocol
or storage failure block mutation, retaining typed diagnostics.

Shared consumers use bound lookup only for explicitly bound cycles: active-pointer
lookup uses the recorded legacy ID plus exact cycle binding, not current branch;
finish/completion resolves its exact operation/record; route lookup uses its exact
cycle row. Lifecycle admission, status, worktree matching, delivery and cleanup
must all validate bound physical identity and expected branch where needed. Source
sync remains a separately validated best-effort step under its existing contract.
No global change to historical IDs or pointer names is authorized.

## Acceptance, Gates And Visual Evidence

CI-01 through CI-11 in corrective Discovery apply, plus:

- Bind denial, unknown/partial additive schema, unsafe custody and stale snapshots
  leave all record and companion bytes unchanged.
- First bind or legacy release and schema extension are one transaction;
  interruption cannot leave half-created schema or an activated writer. Legacy
  v1 cycles remain usable, including release before any cycle has been v2-bound.
- V1 cannot admit/finish a bound-cycle mutation through the new helper; old
  executable exclusion remains an explicit activation prerequisite.
- Duplicate release receipt returns its original result after a later same-cycle
  selection without removing it; reader release cannot release another writer.
- Attaching to a different cycle cannot orphan a writer; reader selection changes
  remain independent of another actor's admitted operations.
- Changed admin custody or locator refuses attachment/admission even with the
  same branch and cycle record. Distinct detached targets remain inspectable.
- Deleted historical source does not change stored attribution, grant source
  sync permission or prevent exact operation completion in a valid cycle target.
- Typed output never includes local_target paths, custody metadata or raw errors.

The three corrective plans enumerate gate applicability. Kernel, Review/Integrate
and Maintain/Retire are required; no exception is approved. All implementation,
review, native and live evidence is pending. The future relocation contract must
explicitly preserve/update this binding under its approved move, not reinterpret
branch aliases as physical identity. Build reports readiness_reopened for a
material contradiction rather than adjusting these normative rules itself.

| Concern | Decision | Owner / change trigger |
|---|---|---|
| Boundary | required: corrective Discovery context/ownership tables | Discovery; owner or authority changes |
| Interaction | required: interface table and release/replay ordering above | Lifecycle/adapter Discovery; ordering or consent changes |
| State | required: corrective Discovery release state table | Lifecycle Discovery; transition changes |
| Data/trust | required: private schema/interface tables and local-target boundary | Lifecycle/adapter Discovery; disclosure or custody changes |
| Schema | required: additive relationship table and Text Equivalent above | Lifecycle Discovery; keys/cardinality/compatibility changes |
| Dependency/deployment | required: corrective Discovery slice ordering | Distribution Discovery; activation or rollback changes |
| Quantitative | not_applicable: limits are contracts, not measured comparative claims | No chart justified |

**Text Equivalent:** Explicit approved binding adds private compatibility state
while retaining old records. Versioned controls separate diagnostic authority,
release authority and execution authority. Native identity and exact snapshots
precede mutations, durable transitions precede cache changes, and replay cannot
affect a newer selection. Qualified core precedes adapter, then host installation
and same-conversation recovery; none of these stages performs relocation.
