# Durable DBSCTR integration coordinator

## Status, scope and profile

Proposed normative contract in the existing Delivery Lifecycle Initiative.
Owner: `dbsctr_v3_lifecycle`; the existing Engineering Profile applies with a
critical risk override for delivery authority. Python, Security and Cloud apply.
This document defines readiness for later Build slices, not installed capability,
merge consent, credential enrollment, source implementation or live activation.

The [runtime adapter amendment](integration-runtime-adapters.md) refines this
contract for live adoption: ordered source and refresh projections, private
delivery obligations, inherited repair authorization, terminal archival, native
attested admission, protected source retention and guarded task-head refresh.
Its explicit v2 runtime/compatibility rules supersede the narrower proposed v1
source assumptions below. The delivered v1 offline core retains its own semantics.
The operator has subsequently authorized rollout to selected targets; no text
here establishes actual enrollment, secret delegation or passing live qualification.

V1 coordinates integration while existing GitHub Actions remain authoritative.
Independent agents keep separate PRs, phase commits and concurrent coding/checks.
One final candidate per repository/default branch owns the integration slot from
base capture through candidate CI and verified merge. A final-merge-only mutex
cannot prevent earlier candidates from repeatedly becoming stale.

No native merge queue, batching, speculation, CI-trigger replacement, reduced check
set, result-reuse authority, Dagger activation or automatic cleanup is included.
Dagger remains a default-off advisory pilot under its existing owner. Coordination
can reduce avoidable stale-base work; it does not promise more runner capacity or
eliminate waiting for existing CI matrices.

## Ownership and existing authority

| Owner | Responsibility and preserved boundary |
|---|---|
| Lifecycle | Admission, source-series binding, integration state, current-candidate verification, delivery proof and repair ownership |
| Distribution | One versioned opt-in policy, compatible installed generation, credentials projection, rollout, disable and recovery |
| Repository CI owner | Existing triggers, required-check plan, trusted producer definitions, native safeguards and production eligibility |
| Existing control planes | Qualified exact-task feedback and private delivery-handle mapping; no new session or agent |
| Continuous validation / Dagger | Advisory execution and later qualified receipt adoption; no second integration scheduler |

Reuse the existing exact-head/base, trusted-producer, preservation, supervised
repair and rebased-completion authorities. Existing delivery schema 1 and the
structurally blocked `check pr-review` path retain their current semantics.
They do not become an enabled coordinator or authenticated CI evidence by inference.

The new `integration-coordinator-v1` capability requires an explicit new policy
version, installed-generation qualification and exact repository enrollment.
Shared defaults are off. Personal opt-in selects the normal coordinated route
for all participating personal merges; overrides remain explicit and invalidate
any candidate affected by their source, base or authority change.
New cycles may enroll through the later lifecycle hook. Existing PRs require
explicit, source-bound adoption; opening a PR, adding a label or having an old
Cycle Record is not adoption. Existing active cycles keep their original authority.

## One implementation and proposed interfaces

Proposed source home: `private_dot_config/dotfiles-ai/integration_coordinator/`.
A thin `dot_local/bin/executable_dbsctr-integration` entry point invokes that same
Python core locally and in short Ubuntu GitHub Actions jobs, with Python >=3.12.
No shared CLI edits are needed for the first core slice. Later lifecycle hook and
receipt integration serialize changes to the existing helper with its owner.

The independent first source slice owns closed record schemas, deterministic
state transitions, CAS request construction and injected persistence, requester,
SourceSeries, native-check and native-mutation interfaces. Deterministic fixtures
exercise their guards. It does not implement a live SourceSeries producer,
credential adapter, hosted check inventory or lifecycle receipt consumer. Missing
or unqualified ports return unavailable before native reads/writes; a test double
cannot become production authority. Its entrypoint supports bounded offline
validation/status fixtures only until later adapters qualify live operations.

The following are proposed interfaces, not claims about existing commands:

| Operation | Proposed input and result |
|---|---|
| `submit` | Exact enrolled repository/PR plus lifecycle SourceSeries descriptor; append a durable request and return its control commit/reference |
| `adopt` | Explicitly authorized existing PR and the same source descriptor; no retrospective gate pass or fabricated cycle |
| `status` | Bounded read-only ticket, active generation, qualification and unresolved obligations |
| `advance` | One bounded trusted wakeup; reread ledger/native authority and perform an eligible fenced transition |
| `reconcile` | Resolve an uncertain native request from actual forge state; never assume failure or repeat mutation blindly |
| `operator-resume` | Same active ticket/generation using a qualified operator credential and the same guards; no independent manual merger |

Admission is asynchronous: `submit` may acknowledge **durable requested** after
its append succeeds, but only the worker's verified CAS transition acknowledges
**admitted/queued** and assigns its monotonic FIFO sequence. The response states
which acknowledgment was obtained. Failed persistence is not accepted work.

## Durable repository-local ledger

Each enrolled repository has one precreated control branch and one default-target
index. Its name, native repository identity and allowed writers are explicit
activation policy. Disabled enrollment or a missing branch never creates, repairs
or enables a branch automatically. The control branch is data, never executable
source; repository visibility also applies to every byte and its Git history.

Use bounded typed JSON per ticket plus a bounded target index. Ticket records bind
an opaque integration handle, PR/source version, SourceSeries digest, requester
policy/provenance, state, generation and native operation/evidence references.
The target index binds its schema/policy, FIFO sequence, queued handles, active
handle/generation, candidate identities and any unresolved mutation reservation.
Reject unknown fields/versions, duplicate identities, noncanonical paths and
inconsistent references. Policy fixes finite byte/count limits; enforce them on
both writes and reads before mutation. Capacity refusal retains accepted work
and returns an explicit blocker; it is not permission to discard history.

| Initial v1 bound | Required validation |
|---|---|
| Ticket / target index | At most 128 KiB / 64 KiB of canonical UTF-8 JSON; closed schema/version/state enums |
| Queue / retained tickets | At most 256 admitted queued tickets / 4096 retained tickets; refuse new admission at capacity |
| Source / evidence populations | At most 1024 ordered source commits and 512 bounded native evidence references per ticket |
| Scalar identities | Opaque ASCII handles at most 64 characters; bounded non-secret strings at most 512 characters; native integers positive and <=2^53-1; full repository-format Git OIDs |

Larger limits or retention/disposal need a reviewed policy amendment. No automatic
history rewrite, record deletion or bound increase follows saturation.

No secret, token, raw log, local path, private Cycle Record ID, session identifier
or private adopter identity enters the branch. Use fresh opaque handles; the
existing private lifecycle/control-plane owner maps them to original tasks.
Public-safe original commit IDs and bounded native run/job/result references may
be retained. Diagnostic bodies stay in their existing private evidence stores.

Every accepted update is an append in Git history. Prefer native GraphQL
`createCommitOnBranch` with `CommittableBranch.branchName` and `expectedHeadOid`.
A separately qualified implementation may use one child commit of the observed
tip plus a non-force fast-forward ref update with equivalent stale-writer refusal.
Neither an arbitrary ref update nor a fresh read alone is a CAS guarantee.
On contention, reload and reevaluate. Never force, rewrite or reset the ledger.
Unknown append outcomes are resolved by request/operation identity and native
ancestry before retry. Missing, corrupt or observed rewritten state blocks.

Expected-tip CAS prevents concurrent stale writes; it does not detect arbitrary
rollback after a stateless restart. Enrollment therefore requires native rules
prohibiting force updates and deletion on the control branch for every admitted
writer, including controller/exception credentials, and binds the root commit,
allowed writers and those rules' identity/configuration. Each load verifies root
ancestry and current rules against that binding. Unavailable enforcement, policy
drift or an actor able to bypass these constraints blocks hosted activation.
A trusted repository administrator maliciously changing rules, rewinding history
and restoring the identical policy is outside this source-only threat model;
do not claim standalone cryptographic rollback detection or silently reset state.
A consumer needing that assurance requires a separately qualified continuity
anchor beyond this stateless branch protocol.

Dispatches, callbacks, scheduled wakeups and GitHub's pending job queue are not
the ledger. Wakeups may be duplicated, reordered or lost. A scheduled bounded
rescan recovers durable work without inventing another queue. In particular,
GitHub concurrency's pending-run replacement must not drop accepted tickets.

## Candidate slot, fencing and recovery

A positive generation increases monotonically on candidate/authority replacement;
restart cannot reset or reuse it. It binds the active handle, SourceSeries, native PR head, observed
ultimate-default base, tested candidate/parents, policy and required-check plan.
Its logical slot persists while no job is running. Short stateless invocations
release compute after bounded inspection; they do not surrender that slot while
waiting for CI. Other PRs and CI matrix jobs can run concurrently.

Only CAS-authorized transitions may claim or change the slot. Each external
mutation has a durable unique reservation before the call, a bound invocation
identity and an outcome reference afterward. Competing callbacks cannot both
issue the same reserved mutation. A stale generation cannot update current state.

A generation is not a wall-clock lease. Timeout, silence or worker age never
transfers mutation authority or proves that an earlier actor stopped. Before a
successor can mutate, reconcile the previous native request and invocation's
termination/custody. A ledger fence alone cannot stop a paused old process from
calling GitHub; do not overlap such owners or claim external exactly-once effects.
Unknown outcomes retain the slot until reconciled, not until an arbitrary expiry.

| Current state / event | Required transition or result |
|---|---|
| Durable requested | Verify native requester, enrollment and source authority; admit FIFO or retain a reasoned rejection |
| Queued, slot free | CAS-select one eligible ticket and capture fresh native base/head/policy |
| Qualifying | Request or observe existing candidate CI; record exact candidate and native producer/attempt identities |
| CI pending | Retain logical slot, end invocation and await callback/scheduled reinspection |
| Current complete success | Recheck all guards; reserve one native merge request |
| Failed current candidate | Retain failure and move to repair-pending; release only after outstanding mutation/worker custody is resolved |
| Source/base/policy changes | Invalidate qualification; replan that ticket or block the lost authority |
| Merge request uncertain | Reconcile actual PR/default-ref/object state before any new request |
| Native merge verified | Record delivery; release integration slot while local receipt reconciliation may remain pending |
| Original task unavailable | Retain repair/receipt work for that task; unrelated eligible tickets continue |
| Disabled enrollment | Admit no new work; reconcile owned uncertainty and preserve all records |

A direct merge or another actor's default-branch advance invalidates affected
qualification even if changes look unrelated. The coordinator is cooperative
across enrolled writers, not a lock over every GitHub actor. Unexpected mutations
are observed, recorded and reconciled; no automatic reset or compensating merge.

## Native qualification and merge guards

| Evidence / trust boundary | Required guard |
|---|---|
| Coordinator code | Pinned reviewed default-branch core/workflow and compatible policy; never checkout, import or execute PR/control-branch code |
| Requester | Verified native actor and enrolled policy scope; request JSON, labels, roles or Git author strings alone authenticate nothing |
| Source | Current same-repository PR head and SourceSeries authority; changed content invalidates qualification |
| Candidate | Actual tested object and ordered parents bind current base/head; names, branch labels and tree similarity alone are insufficient |
| Required checks | Complete current native check/security plan, actual check App/provider, workflow/job/run/attempt and successful applicable outcomes |
| Code scanning | Current required analysis categories/configuration and actual native analysis receipts for the candidate's accepted ref/SHA binding, not merely a green workflow or aggregate |
| Merge request | Exact head guard plus native strict current-base enforcement across the request; immediate rereads and local fencing alone do not close the base race |
| Native outcome | Query uncertain results; verify actual merge strategy, destination ancestry and source correspondence before declaring delivery |

Preserve every existing CI trigger and its event applicability. V1 may request
only independently authorized native branch synchronization or CI continuation;
it does not add force-full shortcuts, skip workflows or convert stale passes.
A credential must be qualified to cause the required native checks on changed
candidates; automation-token event suppression cannot be treated as successful CI.
Unknown/missing/skipped/neutral/canceled/failed required evidence never passes.
A missing category after a security-configuration change remains uncovered.

Normal and admin modes use the same engine and every qualification guard.
The selected v1 strategy is rebase-and-merge, preserving each original phase
commit through verified correspondence; squash is outside this capability.
Historical merge-commit routes/readers retain their existing authority.
Admin mode requires exact-repository policy and the enrolled human's existing
review exception, as permitted by current native protections. It is not a CI,
security, freshness or global protection waiver. Missing native enforcement
blocks even when the merge command accepts an administrator flag.

When the worker lacks the qualified credential, record awaiting-operator.
The operator may resume the same active candidate/slot with the same core,
fresh reads and native guards only after competing mutation authority is resolved.
Do not suggest a separate direct merge command as a second route. If this requires
an online operator, report degraded offline delivery honestly; no stored policy
or source test proves that a sleeping machine can supply the needed credential.
Credential enrollment, storage and revocation require separate runtime approval.

## SourceSeries, repairs and completion

The lifecycle hook produces the versioned public-safe SourceSeries descriptor
from its actual private authority. The remote worker does not parse Cycle Records
or accept arbitrary caller JSON as proof of formal gate success. Original Gate
Commits, their evidence and their order remain immutable. Record authorized
base-sync merges and empty CI-trigger wrappers separately; never add them as
invented Gate Commits or lose the original-to-landed attribution requirement.

Code-changing repairs return to the original authorized task through its existing
qualified feedback route. Logs are untrusted diagnostics, not instructions or
new write authority. Do not create another agent/session, repeatedly execute
unchanged failures, reset repair accounting or invent a universal three-repair
cap. Existing supervised repair approvals/budgets still apply unless an explicit
qualified amendment changes that authority. Material semantic/scope/risk choices
return to the operator for that ticket, while unrelated work remains eligible.

A remote delivery receipt records actual forge outcome and source correspondence;
it waits for the original retained checkout's supported custody/completion route.
It cannot reopen a closed cycle, hand-edit opaque state, fabricate a helper v2
receipt or authorize branch/worktree deletion. Keep original source reachable
until existing preservation and separately qualified retirement guards are met.
Native delivery may be verified while local lifecycle reconciliation is pending.

## Qualification, rollout and acceptance

Source, Deploy and Operate are separate claims. First deliver the new core and
entrypoint under the existing Initiative. Later hook/receipt integration preserves
other active shared-helper work. Install compatible code/policy and precreate the
control branch only through approved activation. Qualify credentials, native
protections, scheduled recovery, disable/rollback and original-task feedback
before enabling either repository. No existing shadow enrollment enables this.

| Acceptance case | Required evidence |
|---|---|
| Twelve ready tasks | Concurrent coding/CI; one final candidate slot and no final-merge-only locking claim |
| Client/dispatch lost | Durable requested work survives; no queued acknowledgment before admission or loss through pending-run replacement |
| Two writers / stale tip | Exactly one CAS transition wins; loser rereads without force or overwrite |
| Disabled/missing control state | No automatic enablement, branch creation or silent reinitialization |
| Restart/timeout/late actor | Slot and mutation reservation survive; no age-based takeover or overlapping unknown mutator |
| Outside merge or changed head | Qualification invalidates; native base guard prevents stale delivery across the request |
| Changed CodeQL requirements | Missing current category blocks despite earlier green checks |
| Wrong App/attempt/policy or forged descriptor | No admission/pass; native and lifecycle authority remain distinct |
| Failed ticket / unavailable task | Original failure and repair ownership retained; unrelated tickets continue |
| Base-sync/empty wrappers and rebase | All original phase attribution verified; wrappers accounted separately without forged gate/state changes |
| Credential absent / operator resume | Same slot/core and fresh guards; degraded offline capability explicit |
| Merge timeout / lost response | Read-only outcome reconciliation precedes retry; no guessed duplicate merge |
| Ledger limits / corrupt state | Bounded refusal preserving accepted work; no history deletion or zero initialization |
| Source-only delivery / rollback | No enrollment, CI-trigger change, cleanup, Dagger authority or runtime activation claimed |

## Visual Evidence

### Risks and evidence plan

Remaining qualification risks are native actor/protection visibility, credential
scope and event suppression, control-branch tampering, stale external mutators,
source-wrapper correspondence, bounded state growth and unavailable task delivery.
A cooperative integration owner cannot prevent unenrolled actors or freeze a
changing security policy. Native enforcement and honest unavailability remain
required. V1 does not promise throughput gains before comparable measurements.

| Visual concern | Decision and canonical source |
|---|---|
| Boundary/data trust | Required: Ownership and Native qualification tables |
| Interaction/state | Required: proposed interfaces and Candidate slot transition table |
| Schema | Required: Durable repository-local ledger fields/bounds and CAS ordering |
| Deployment | Required: separate Source/Deploy/Operate sequence above |
| Quantitative | Not applicable: no measured speedup or capacity projection |

**Text Equivalent:** A trusted client durably requests integration. The shared
core admits eligible work, assigns one repository/default-branch candidate slot,
and observes existing native CI. Fresh policy, producer, candidate and native
base guards permit one reserved merge request. Verified outcomes release the slot;
uncertainty retains custody, and original tasks retain repairs and local receipt
reconciliation. Owner: lifecycle maintainer with distribution/CI/control-plane
owners at their existing boundaries. Update the tables and this text together
when authority, persistence, state transitions, runtime or evidence changes.

## Offline core source foundation

The [source contract](integration-coordinator-core.md) owns the independent core's
concrete records, pure transitions, complete append construction, offline command
surface and outcome-capacity safeguards. This source foundation preserves every
authority/activation boundary above. It is not a live integration coordinator or
an installed lifecycle receipt consumer.
