# Administrative cycle retirement and preserved checkout removal

Status: Discovery specification; no implementation or installed capability claim.
Owner: lifecycle maintainer. Profile: [../PROFILE.md](../PROFILE.md). Risk: critical.
Modules: Python and Security. Initiative: [retirement recovery](../../../initiatives/dbsctr-workflow-convergence/RETIREMENT-RECOVERY.md).

## Outcome and precedence

An operator can stop pursuing a cycle without fabricating successful gates,
merging unwanted work, editing private records, or deleting its checkout. A later
explicitly approved operation can preserve that work locally and remove only its
checkout through Worktrunk. The tool owns preview, confirmation, preservation,
preparation, retry and recovery; ad hoc reset/stash/record editing is not a journey.

This is an approved additive exception to the completed-and-merged-only removal
rules in [preservation](workflow-preservation-retirement.md), including INT-012,
013, 022 and 023. It changes neither historical delivery facts nor automatic
cleanup admission. Existing successful-delivery proof remains unchanged.
[Stale retirement](../STALE_CYCLE_RETIREMENT.md) is historical; its direct Git
deletion implementation must not be reenabled. Existing orphan recovery remains
compatible but is not the general administrative interface.

Three independent facts must remain separate: lifecycle outcome, artifact
preservation, and physical checkout existence. No one fact implies the others.
The existing Cycle Record, common-Git private evidence, native Git refs and
Worktrunk remain their owners. No daemon, task registry or continuation engine.

## Domain and behavior

| Given / request | Required result |
|---|---|
| Active or finalizing supported cycle; explicit `superseded` | Record replacement intent and bounded reason; successor is optional, never inferred and need not be completed. |
| Same; explicit `cancelled` | Record intent to stop without requiring replacement or successful gates. |
| Same; explicit `empty` | Require no recorded commits (including authority import), HEAD equal to baseline, clean index/tracked/untracked state, and no unique ignored/data obligations. Unknown is not empty. |
| Branch-bound legacy, adopted or native record | Same administrative route, independent of `created_by_dbsctr`; no prerequisite adoption or registration of a replacement cycle. |
| Supported schema-6 local-only record | Administrative closure and local archival require no network, credential lookup or delivery-mode conversion. |
| Failed gates, dirty files or historical uncertain operations | Preserve original facts and bytes; they do not require successful completion before administrative closure. |
| Positively identified live cycle writer / held shared mutation lock | Refuse closure until stopped; never mark the write completed or steal its lock. |
| Unfinished historical operation interval / optional or missing operation history | Preserve uncertainty; an interval alone is not live-writer evidence and missing history never proves inactivity. Require explicit operator quiescence assertion. |
| Operator confirms writers stopped; idle MCP/read-only consumers remain | Permit record-only closure. Consumers still block preparation and removal. A PID timeout is not a quiescence assertion. |
| Completed cycle later cancelled or superseded | Keep `state=completed`, completion timestamp and any immutable local completion unchanged; add administrative disposition without relabeling its successful validation or claiming integration. |
| Several cycles share checkout | Closure affects only selected record and its exact pointer. Removal needs disposition/preservation of every correlated record and no remaining active cycle. |
| Checkout missing or branch drifted | Read-only historical diagnosis remains reachable; closure may proceed only with unambiguous repository/record custody and explicit missing/drifted disposition in approved preview. Never guess a replacement checkout or clear its pointer. |
| Malformed/unknown record, ambiguous repository or conflicting pointer | Refuse with classified reason and supported next action; no automatic record repair. |

Supersession is an operator decision, not a claim of patch equivalence. Optional
successor must be a different validated same-repository cycle; cross-context
successors are allowed and confer no delivery proof. Cancellation takes no
successor. A record-only operation leaves checkout/index/user branches/data alone.
Missing commit objects prevent archival/removal but need not prevent truthful
administrative closure while retained record/checkout obligations remain visible.
Finalizing records retain external-write attempts and unknown remote outcomes;
retirement neither undoes publication nor asserts that a PR is closed.

## Selected CLI contract

These are proposed interfaces, not commands available in the baseline helper.

Reuse `cycle-retire --cycle-id ID --disposition superseded|cancelled|empty
--reason TEXT [--superseded-by ID] --preview --json` for read-only preparation.
Apply uses the same selection plus `--expected-state SHA256` and
`--approval interactive|agent-confirmed` (default interactive). Existing `--confirm`
alone never authorizes the new operation; old invocations receive a migration
diagnostic rather than silently acquiring new semantics. `cycle-retire-worktree`
and direct cleanup deletion remain retired.

Interactive confirmation is exactly `RETIRE ID DIGEST`. Agent-confirmed means
the primary presented exact effect, disposition, reason, identities, observed
write state and digest and obtained explicit chat approval. Record assertion of
consent, not authenticated native actor identity. Both methods include explicit
operator assertion that cycle writers cannot write; no synthesized terminal input.
Native permissions and Plan/read-only restrictions remain independent.

Reuse `status --cycle-id ID --json` for source-independent administrative status
and retry guidance. Preview/status must not require active execution admission.
Do not introduce a new cycle or successful completion to obtain recovery access.

Version-1 administrative result has exactly `schema_version`, `cycle_id`, `status`,
`state_digest`, `reasons`, `next_action`; status is `preview`, `retired`,
`already_retired`, `blocked` or `recovery_required`; digest is SHA-256 or null;
reasons are bounded stable codes, never raw errors. Existing status output gains
an optional versioned retirement summary, preserving existing fields. Full exact
preview lives in owned private evidence; local terminal presentation may show
private inventory, while hosted output contains only approved bounded metadata.

### Persistence, compatibility and interruption

Preserve supported schema 3/4/5 records and explicitly extend schema-6 validation
for administrative retirement. Do not renumber or bulk-rewrite existing records.
Unknown versions still refuse. Historical retirement shapes remain readable.

New optional `retirement` version 1 contains: `schema_version`, `state`
(`retired` only), `disposition`, `reason`, nullable `superseded_by`,
`state_digest`, `before_sha256`, `record_backup`, `confirmed_at`, `approval_method`
(`interactive_cli` or `agent_confirmed`), `writers_quiescent_asserted=true`,
`worktree_removed=false`, and `pointer_status` (`pending`, `cleared`, `absent`
or `conflict`). Physical removal is recorded separately in existing removal
evidence; it must not rewrite this historical closure snapshot.

Digest binds repository common identity, original record bytes, record/pointer
identities and bytes, checkout/admin identity or explicit absence, branch/HEAD,
disposition/reason/successor and current relevant mutation evidence. Recheck under
existing cycle and checkout-registration locks in deterministic order; all updated
native CLI mutation/completion paths for that cycle must honor the same serialization.
This is bounded CLI coordination, not universal fencing of editors or old clients.
The administrative invocation itself is not an outstanding cycle write that must
finish before its own admission; check other operations before acquiring mutation
authority, then recheck under shared locks. Preserve historical uncertain rows
unchanged rather than fabricating completion to drain them.

Old writers must be stopped and incompatible clients kept out before closure;
this is an operational prerequisite, not a guarantee these locks can enforce.
Updated clients enforce terminal records. Held locks and positively identified
live writers block regardless of assertion. An optional unfinished operation
interval alone does not identify a live writer; absent history is not proof of
inactivity. Explicit operator assertion remains required in either case. No new
liveness/identity service or universal old-client fencing is implied.

Fsync exclusive private original-byte preimage before atomic record replacement.
For formerly active/finalizing records, persist `state=retired` and UTC
`retired_at` with that replacement; completed records retain original state and
completion fields. All unrelated record fields remain byte-equivalent in value.
Logical terminal replacement precedes clearing only matching active pointer;
registration refuses pending/conflicting closure reconciliation. Crash after
replacement leaves terminal record with recoverable pointer cleanup, never a
newly writable cycle. Matching repeat reconciles pointer and returns original
result. An initial conflicting pointer refuses closure. After terminal replacement,
a changed/reassigned pointer is retained, reports `recovery_required` and blocks
registration; it is never unlinked.

Replay uses only the original approved digest and verified original-byte preimage.
At minimum, validate intent against the original approved intent, preimage bytes
and hash, valid same-repository record/evidence custody, and current terminal
record against the original plus exactly approved retirement metadata and outcome,
except recorded `pointer_status` reconciliation. Only `pointer_status` may advance:
`pending` to `cleared`, `absent` or `conflict`, or `conflict` to `cleared`/`absent`
after fresh observation permits exact reconciliation. Never rewrite other closure
metadata, timestamps, original fields or outcome under stale consent. Missing or
changed preimage, digest, intent, custody or terminal record blocks replay.
`cleared`/`absent` remain final recorded reconciliation outcomes; a later reassigned
pointer is still retained and reported as `recovery_required`, blocking registration.
Prepared-only evidence lives in a private sidecar outside the active record;
original record intact means not retired. A valid new `retirement` field exists
only on terminal replacement (including a preserved completed record), never a
partially modified active record. An interrupted reply never justifies a second outcome.

All required readers must validate retirement structure independently of live
checkout resolution: status, inventory, registration, history, cycle performance,
removal, and local-only completion replay. Administrative retirement never counts
as successful completion in metrics; genuine historical completed cycles remain
counted, with their history and completion evidence unchanged. Old clients unable
to understand new metadata must not resume writes; distribution retains a
compatible reader on rollback.

## Local archive and exact artifact disposition

Record closure needs no archive and grants no deletion. Archival is separately
selected through `workspace-preserve --cycle-id ID --preview --json`; apply adds
`--expected-state SHA256 --approval interactive|agent-confirmed`. Optional
`--selection PRIVATE_JSON` names exact approved relative file paths; no globs,
recursive directory selectors, credentials in arguments or output-body forwarding.
The selection is schema 1 `{schema_version, paths}`, paths unique and normalized.
Inventory expands directories before approval. Default is Git plus private
lifecycle evidence only; other discovered files remain explicit blockers.

Reuse common-Git `dbsctr/evidence/retirement/ID/ARCHIVE_DIGEST/` for manifest and
selected byte copies; mode 0700 directories, 0600 evidence. Archive is outside
target checkout, same-repository local retention, not protection against disk loss.
No expiry, GC or automatic archive/ref deletion. Separate future disposition is
required to dispose it. No network fetch/push or remote proof in archival path.

Git closure includes recorded baseline, original Git HEAD, current HEAD if present,
all recorded commits including import commits, pre-cycle ahead commits and explicit
selected stash/WIP commit identities. Verify local objects with replacement refs
disabled and pin each under `refs/dbsctr/retired/ID/OID` using create-only native
ref transactions; conflicting refs refuse. Original user branch remains unchanged.
Reflogs, stash position, patch equivalence and IDs in JSON are not durable refs.
Shallow/missing/promisor closure, alternates outside retained repository or unknown
object dependencies retain work until qualified native preservation is available.

Manifest version 1 binds repository/admin/cycle identities, original record and
evidence digests, Git object/ref closure, exact index representation, HEAD, and
every selected file's relative path, class, byte count, executable mode and SHA-256.
Tracked deletions and index/worktree divergence are explicit so both staged and
unstaged state can be recovered. Capture private plan/approval/recovery evidence
and referenced evidence closure, not merely the Cycle Record. Sensitive selected
files remain private; archiving grants no publication permission.

Only ordinary regular files and tracked deletion records are supported initially.
Symlinks, hardlinks, special files, submodules, external paths, unsupported metadata
or changing files refuse preservation/preparation. Reject traversal and aliasing;
no following symlinks. Verify before/after identity/size/content, fsync captured
bytes and manifest, then reread/hash and perform a disposable native Git/file
restore check outside target before marking verified. No extraction may overwrite
existing user files. A complete archive may coexist with a dirty checkout.

Bound first-release inventories to 10,000 paths, manifests to 8 MiB, selected
ordinary file payload to 1 GiB total, and each command to 120 seconds; report
limit/deadline classes and retain partial preparation, never partial success.
Do not lift bounds through unapproved generic copy commands. DVC objects are not
ordinary file archival: existing declared-output/backend/closure checks still
apply; unqualified directories remain retained. All discovered artifact classes
must be covered or explicitly proven regenerable by existing producer rules.

`workspace-preserve --cycle-id ID --verify --json` revalidates recorded archive.
`--restore-to ABSOLUTE_NEW_DIRECTORY --expected-state DIGEST --approval ...`
restores into a new empty, non-primary destination using native Git and exact
file/index recovery. Preview binds destination and archive. No overwrite, active
worktree retargeting or implicit registration; missing/corrupt bytes refuse. This
is a recovery export, not a competing task allocator. Local terminal retains full
paths; agent summaries remain bounded. No archive deletion command in this scope.

## Disposition-aware manual removal

| Record/artifact class | Git predicate, additional to every other check |
|---|---|
| Completed delivered work without administrative disposition | Existing fresh integration proof; archive is not delivery proof. |
| Explicitly superseded/cancelled record, including completed-local record | Fresh verified local archival closure; no merge or remote publication prerequisite. Existing completion stays immutable. |
| Proven empty retirement | Baseline/no-work proof and preserved record/evidence. |
| Active, unclassified, uncertain preservation or unknown schema | Retain and return supported next action. |

Extend existing `agent-worktree --remove PATH` with `--preview --json` and apply
`--expected-state DIGEST --approval interactive|agent-confirmed` for manual mode.
Default invocation without these selectors retains its existing automatic refusal
semantics. Interactive exact confirmation is `REMOVE WORKTREE_ID DIGEST`.
Preview binds full correlated record set, dispositions, Git obligations, verified
archives, file/index inventory, branch/HEAD, reservation identity, exact preparation
effects and intended Worktrunk command. Approval never implies branch deletion.

Use existing reservation and removal-evidence owner, not a new broker. Manual
attempt schema is versioned distinctly from automatic schema 1; old readers
refuse new versions. Same descriptor custody, checkout identity and held-lock
proof must survive native Worktrunk/hook transport. Explicit approval replaces
automatic birth-policy admission only. Human assertion is not native actor proof.
For this manual route, operator-confirmed handoff/quiescence plus qualified native
process inventory replaces unavailable automatic conversation attribution; never
claim CLI authenticated a session. A current live conversation must use qualified
native handoff; idle checkouts need no manufactured conversation. Unknown or
contradictory consumer/ownership evidence still blocks. Automatic blockers remain.

Add manual checker schema 3, with `schema_version`, `eligible`, `reasons`,
`state_digest`, `reservation_id`, `mode=manual`, `approval_method`, and
`preservation_digest`. Existing schema 1/2 remain compatible and cannot authorize
manual mode. Caller-supplied JSON alone never becomes a checker decision; trusted
installed checker reads and revalidates source evidence under inherited reservation.

Before any destructive preparation: require separate exact approval covering its
effects, no relevant consumers or writers, compatible primary outside target,
held cooperative reservation, complete archive restoration proof and fresh exact
file/index checks. Preserve process and permission boundaries. Operator attestation
does not waive known consumers; never signal MCP servers or other processes.

Only then restore approved tracked index/worktree paths to recorded HEAD using
native Git restore (not reset), and unlink only exact approved archived ordinary
untracked/ignored files. Retain changed or unlisted paths. Write durable intent and
per-step outcome in existing removal attempt evidence before each action. Bound
file-descriptor/no-follow checks prevent replacing approved paths with aliases;
concurrent external mutation stops preparation and retains archive/current state.
Do not claim cooperative locks fence arbitrary writers.

Fresh hook recheck must prove clean prepared state, all archives still valid,
unchanged identities and no consumers, then invoke only
`wt remove --foreground --no-delete-branch` with hooks enabled. Original preview
binds expected preparation result so legitimate preparation is not mistaken for
unapproved drift. Native refusal retains checkout and archive. Verify absent
membership/path and unchanged branch tip separately before reporting removed.

Interrupted preparation/removal reports `recovery_required` with bounded next
action. Reconcile actual membership, paths/index and archive before retry; never
blindly replay removal or overwrite surviving edits. User may resume exact remaining
preparation after fresh approval or restore archive to new destination. A completed
retirement remains terminal when cleanup fails. Partial cleanup must never be
reported as successful removal. Fresh manual approval is required after drift.

## Reachability and validation

Each supported entry mode must have an executable successful and intentional
non-success exit test, plus historical read/retry after checkout removal. This is
a migration release criterion, not a new runtime state engine or blanket promise
to recover malformed records. Test schema 3/4/5 legacy, adopted and native where
supported; schema 6 native local-only; ordinary and Initiative registration;
active/finalizing/completed; empty/import-only/gate-committed/dirty/shared checkout.
Unsupported combinations must have explicit preserved-state diagnostics.

Required regression scenarios:

1. Branch-bound import-only cycle absent from default becomes superseded without
   changed gates; original commit remains reachable after branch reset and GC in
   a disposable fixture. Stash/WIP identity is preserved only when explicitly selected.
2. Native registration, failed gate, record retirement, exact pointer reconciliation,
   next registration and status all work through public CLI dispatch, not handler mocks.
3. Idle consumer permits record closure after quiescence assertion but blocks
   preparation/removal; known live write blocks both. Missing inventory is not empty.
4. Lost reply/crash at preimage, record replace, pointer clear, ref pin, byte capture,
   archive verify, every preparation step and native removal has safe supported retry.
5. Missing/changed archive, changed file/index/HEAD, conflicting pointer/ref, shared
   active cycle, unsafe path, malformed metadata, stale approval and denied native
   permission all retain work and original failed evidence.
6. Local-only completed record remains immutable and unpublished while explicit
   administrative disposition enables independently approved archival removal.
7. Fully qualified disposable manual workflow reaches actual hooked Worktrunk
   removal; archive restores original Git objects, staged/unstaged bytes and private
   evidence. Default automatic path remains blocked. Test supported Worktrunk versions.
8. Future migration cannot remove last non-success exit while registration remains
   enabled. Add reachability cases to existing configured pytest collection; no new CI engine.
9. Held shared locks and positively identified live writers refuse; historical
   unfinished intervals alone remain uncertain rather than live, and optional/missing
   history never supplies inactivity proof. All allowed closures require explicit
   quiescence assertion and the incompatible-client operational prerequisite.
10. Original-digest retry validates exact intent, preimage/hash, custody and terminal
    record against original plus approved metadata. Tampering or changed effects
    refuses; only allowed pointer-status reconciliation changes. Initial pointer
    conflict refuses; post-terminal reassignment retains pointer and blocks registration.
    Prepared sidecars leave active records unchanged. Historical completed counts
    survive while non-success retirement adds no success.

Reuse affected `tests/test_dbsctrctl.py`, `test_workspace_adoption.py`,
`test_orphan_workspace_recovery.py`, `test_native_workspace_execution.py`,
`test_native_workspace_records.py`, `test_worktrunk_registration.py`,
`test_workspace_remove_check.py`, `test_agent_worktree.py`, and local-only tests.
New `tests/test_cycle_retirement_recovery.py` owns cross-mode public-CLI journeys.
Use configured pytest/compilation and real disposable native hooks; mocks alone
cannot qualify manual deletion. Existing publication/instruction checks and CI
remain authoritative. No production mutation during source validation.

## Gates and risk

All six kernel gates, Review/Integrate and Maintain/Retire required. Source Release,
Deploy and Operate not applicable under CORE-SOURCE.plan.json; rollout has separate
required Deploy/Operate. Gate results pending; no exceptions. Critical review must
cover data loss, authorization, crash ordering and compatibility before activation.
Source delivery is feature branch/draft PR to protected main. Build may not revise
this contract or expand bounds; material findings return readiness_reopened.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership table below |
| Interaction | required: ordered state/operation table below |
| State | required: ordered state/operation table below |
| Data/trust | required: ownership table below |
| Schema | not_applicable: versioned field contracts above are canonical; no duplicate schema diagram |
| Dependency/deployment | not_applicable: Initiative owns serial delivery and installed qualification |
| Quantitative | not_applicable: bounds are limits, not measured performance claims |

| Owner | Transfer and retained authority |
|---|---|
| Operator/native harness | Exact consent and writer-quiescence assertion to CLI; stop old writers and keep incompatible clients out; native permission enforcement remains outside CLI. |
| Lifecycle/Git | Original records, refs and selected private bytes to same-repository archive; no remote publication. |
| Existing supervisor/checker | Fresh preservation and consumer predicates to native Worktrunk under cooperative reservation. |
| Worktrunk | Removes only eligible checkout; Git branch/archive/evidence stay retained. |

| Initial state | Operation | Result |
|---|---|---|
| Active/finalizing | Preview, shared-lock recheck and approved closure after operational quiescence | Retired, checkout retained, failures/uncertain history unchanged; held lock or positively identified live writer refuses. |
| Original active record and prepared sidecar only | Observe interruption | Not retired; no partial retirement metadata in active record. |
| Completed | Approved administrative disposition | Completed remains immutable, disposition recorded, checkout retained. |
| Terminal and retained | Approved capture and verify | Archive verified; checkout may remain dirty/busy. |
| Preserved and quiescent | Approved exact preparation | Prepared clean checkout, archive retained. |
| Prepared and freshly eligible | Hooked native removal | Removed only after membership/path/branch verification. |
| Terminal closure with pending/conflicting pointer | Original-digest, preimage/custody/record-validated replay | Only pointer_status reconciles; reassigned pointer retained, recovery_required and registration blocked. |
| Any interrupted cleanup | Observe/status then approved retry | Resume from observed state; never fabricate completion or replay deletion blindly. |

**Text Equivalent:** Operator approval permits separate logical closure, archive
capture and checkout preparation/removal. Lifecycle keeps failures and private
evidence and genuine completed history; Git pins recoverable objects. Closure needs
shared-lock recheck, no positively identified live writer, explicit quiescence and
operational exclusion of incompatible clients; missing history proves nothing.
Prepared sidecars do not retire records. Terminal retries validate original digest,
intent, byte preimage/hash, custody and exact approved record; only pointer_status
advances. Reassigned pointers remain and block registration. Only Worktrunk deletes the checkout after
fresh consumer and preservation checks. Every failed/interrupted step retains its
evidence and has observed-state recovery. Canonical source: this contract; owner:
lifecycle maintainer; change trigger: any transition, ownership or data-retention change.
