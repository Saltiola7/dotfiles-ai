# Integration runtime adapters

Discovery amendment to [integration coordination](integration-coordinator.md).
Owner: lifecycle maintainer, with distribution and native CI owners at their
existing boundaries. Critical risk; the existing Engineering Profile and
Python, Security and Cloud modules apply. This contract prepares one cohesive
shared-source slice. Installation and repository activation follow merged source
and actual target qualification; this document establishes neither.

## Outcome and ownership

Keep independent PRs, concurrent coding and all individual phase commits. One
durable coordinator per enrolled repository holds the final-candidate slot across
base refresh, existing native CI and verified rebase-and-merge. The original task
retains delivery and repair responsibility until the target contains its change.
Queued work can progress independently of its computer. Code repair waits for
the original task to resume; no new agent or conversation is launched.

| Owner | Interface and boundary |
|---|---|
| Lifecycle producer | Validate private records, gates, ownership and custody; produce public-safe source descriptors and private delivery obligations |
| Shared core | Closed schemas, FIFO, revisions, reservations, generation fencing, archive and complete append construction |
| Native adapter | Authenticate admission, observe policy/checks/security, retain source, refresh enrolled heads, merge and reconcile native outcomes |
| Distribution | One compatible installed generation and existing repository-policy owner; explicit credential and target enrollment |
| Consumer CI | Existing workflows, conditional checks, production eligibility and producer definitions |
| Dagger owner | Separately enrolled shadow observations; no execution, reuse, admission or merge authority from this change |

The shared source slice includes lifecycle, native and policy interfaces together
because their version bindings must agree. It does not change existing expensive
CI triggers, runner matrices, typing obligations or production promotion. This is
coordination first, not a runner-capacity or test-result-reuse change.

## Versioned source, refresh and local outcomes

SourceSeries v1 and offline readers remain supported. Add closed v2 records for
ordered source entries and native refresh correspondence; never reinterpret v1
phase IDs as current rebased IDs. The producer derives the complete owned source
interval from validated private records, actual Git objects and the published PR.
Entries distinguish recorded phases, approved Discovery imports and authorized
control wrappers, including entries between phases. Every required import is
accounted for even when its recorded gate list is empty. Missing, duplicated,
reordered or unexplained work refuses admission.

A native projection binds immutable original entries to the actual current PR
head and ordered refreshed entries. Candidate v2 binds that projection as well
as original source, exact base/head/tested object, tree, plan, policy and generation.
Original source and original gate evidence never change. A later repair produces
a new immutable revision under the same obligation. Historical original-to-source,
source-to-refreshed and refreshed-to-landed mappings remain individually verifiable.
An unsupported merge, empty/dropped commit or ambiguous replay blocks delivery;
tree equality alone cannot compensate for a missing phase.

Distinguish a stable opaque `obligation_handle` from a unique `ticket_handle` for
each immutable source revision. Replacements receive new ticket handles; no handle
is reused for changed source. A bounded obligation index holds its current pointer
and cumulative counters; immutable revisions/archive links retain history, read
with bounded pagination rather than an ever-growing index array. Supersession CAS checks the expected
current ticket and reserves exactly one successor/repair owner before adding the
replacement at queue tail. Duplicate retries return that successor; stale requests
cannot create competing successors or reset accounting. Archived ticket paths use
their unique ticket handles. Status by original obligation resolves the latest
revision and all retained historical outcomes without confusing superseded work
with delivered work.

Private versioned DeliveryObligation, IntegrationGrant, ChildAuthorization and
DeliveryOutcome records extend existing lifecycle custody, not a second lifecycle
kernel. They bind the exact schema-5 record, source/evidence digests, original task,
scope/risk/target, allowed operations, source revisions and cumulative repair facts.
They contain private task mappings; public metadata uses opaque handles and
bounded digests only. Native requester attestation is an explicit trust policy:
the enrolled requester reports private validation truthfully. Hashes bind content;
they do not independently prove gate execution or human identity. This release
does not require a new signing infrastructure.

A completed source-delivery Cycle Record remains immutable. `accept-outcome`
validates native rebase proof, original record binding and original-object custody,
then writes a separate outcome through the supported lifecycle API. It neither
reopens the parent nor fabricates a legacy external-completion receipt. Extend
the existing preservation/retirement verifier to consume this qualified outcome;
receipt arrival alone never authorizes branch/worktree deletion. Local status
distinguishes source-cycle completion, remote delivery pending, post-merge result,
receipt acceptance and separately guarded retirement.

## Inherited routine repair

Reuse fresh Initiative follow-up preflight, published-prefix ownership, locks and
pending gates. A qualified repair child belongs to the original delivery obligation
and owns only new work after the observed published prefix. It does not rewrite
the parent or carry passing checks across changed inputs.

Keep Cycle Record schema 5 and existing nested approval schema 1. Add only the
closed nested approval variant below, validated through controlled private grant
and ChildAuthorization custody on record reads and registration:

| Field | Required value |
|---|---|
| schema_version | integer 2 |
| method | integration_grant |
| launch_digest | exact fresh child launch digest |
| authorization_digest | immutable ChildAuthorization digest |
| authorized_at | UTC derivation timestamp; never described as fresh human confirmation |

The child authorization binds parent grant/obligation, current native source/base,
profile/plan, exact launch and mechanical scope assessment. Live use also checks
current enrollment and revocation. Historical provenance is validated against its
stored authority, not an unrelated current profile. Old helpers reject this new
variant instead of ignoring it. Other approval modes retain their existing meaning.

Routine corrections within approved intent inherit the grant. Material behavior,
scope, risk or authority changes require the operator for that task. Diagnostics
are untrusted data, never new instructions. Preserve cumulative failures/progress
across children and revisions; waiting is not repair. Do not rerun unchanged
failures without a concrete correction or impose an arbitrary fixed repair cap.
An unchanged failure with no permitted correction becomes an explicit blocker.
The separately scoped legacy supervised `ci-repair` policy remains unchanged.

## Durable state, retention and revision lifecycle

Use the existing repository-local control branch, with one unique orphan genesis,
pinned root and current native no-force/no-delete enforcement for every admitted
writer. Never initialize missing state while handling a normal command. Unknown
schema, root/policy drift, malformed data or unavailable enforcement refuses safely.
All ledger paths remain bounded closed data; no source files or executable config
are loaded from the control branch.
Activation also requires native update restrictions: every actual control-ref
updater must be an enrolled trusted mutator or qualified same-slot recovery
identity. Ordinary repository write permission is insufficient. Keep that update
restriction separate from independently nonbypassable no-force/no-delete rules;
an update exception must not authorize custody destruction. Enumerate effective
writers and rule bypasses, and prove denied ordinary-writer append as well as
allowed worker append. If the provider cannot enforce this boundary, activation
remains unavailable; a JSON admission attestation is not a substitute.

For source retention, amend append semantics to permit parents consisting of the
exact observed control tip first, followed by bounded deduplicated same-repository
source heads. Derive the tree solely from that control tree plus the validated
ledger write set. Never merge source trees. Each retained source must not contain
the unique control genesis in its ancestry. This exclusion prevents a competing
control tip from becoming an ancestor through a source parent. With protected
non-force updates, a stale append therefore cannot fast-forward over a winner.
The existing single-parent expected-head append remains valid for ordinary data
transitions. The extra-parent path requires explicit native Git Data commit/ref
qualification; GraphQL createCommitOnBranch cannot express those parents. A
control-ref linear-history requirement makes this mode unavailable; do not waive
it or silently switch to unprotected refs. Native adversarial qualification must
demonstrate this ancestry/CAS property before enabling refresh.

This retains original objects without accumulating per-task retention branches
or tags. The control branch is append-only custody, not a development integration
branch. Its first-parent history owns the ledger; source parents preserve objects.

| State/event | Guard and result |
|---|---|
| Requested source | Durable private retry outbox; no queued acknowledgement before authenticated hosted admission CAS |
| Admitted/FIFO | One immutable revision and sequence; only one active candidate per target |
| Source refresh | Retain original objects and reserve exact task/head/base before calling native REBASE |
| Refresh uncertain | Retain slot/reservation; inspect native result and worker custody before any successor mutation |
| Refresh proved | Bind projection and new generation; invalidate prior candidate CI |
| Failed candidate | Retain failure; repair-pending original task; release only with no unresolved mutator |
| Repair completed | Supersede old revision with a qualified replacement at queue tail; preserve same obligation and cumulative accounting |
| Native delivery | Durable ordered correspondence and native outcome; release slot while local acceptance/post-merge checks remain distinct |
| Terminal archival | Atomically move delivered/rejected/superseded ticket bytes to immutable handle-keyed archive and free working capacity once |

Archival is independent of an offline owner's acknowledgement. Lookup checks both
working and archive state at one pinned control tip, preserving deduplication and
late reconciliation. Never age-evict queued, repair-pending or unknown-outcome work.
Archive transitions derive exact additions/deletions and decrement only working
retention. Protected Git history, original objects, outcomes and deduplication
remain retained. The existing working-ticket bound must not become a lifetime
4096-delivery limit. Provider storage is finite; exhaustion reports backpressure
without deleting evidence or silently reinitializing state.

## Authenticated admission and public-safe requests

The local producer validates source and custody and records a bounded private
retry outbox before dispatch. Dispatch acceptance is not admission. Only the
trusted hosted worker writes the control ledger through this protocol; the local
submitter never writes arbitrary ledger paths. A trusted default-branch dispatch
binds native event sender, repository, exact handle/source digest and enrolled
requester attestation. The hosted adapter checks the current PR/head and policy,
then atomically records the request and authenticated admission in one replay-
validated CAS transition. Its retained admission attestation binds native run,
actor, exact descriptor and trusted worker source. No intermediate unauthenticated
request can be adopted by a later worker guessing lost dispatch inputs. Native
identity is verified through the platform event/run and configured trusted workflow,
not Git author text, a JSON actor field, author association, a label or a content
hash. A replaced/lost dispatch cannot lose an admitted ticket. The client reports
unadmitted/pending honestly and retains retry state until durable admission.

Workflow completion callbacks and scheduled rescans advance admitted work and
recover uncertain outcomes. An unadmitted outbox remains pending until the client
can retry; its status never claims unattended queued delivery. Ledger writers are
trusted mutators under enrolled policy; a compromised admitted writer is not
made harmless by a JSON admission digest. Descriptors and receipts contain no transcripts,
private paths, credentials, consumer identifiers or raw logs in public storage.
Only enrolled requesters may attest the private validation facts. Changing source,
policy or requester binding requires fresh admission, not a stale payload replay.
The complete UTF-8 dispatch envelope is at most 48 KiB, additionally below native
input limits. Oversized source refuses before dispatch without truncation; no
unreviewed object-store or comment transport is introduced. Normal offline core
record bounds remain unchanged unless explicitly versioned by this runtime.

## Native worker and mutation guards

Trusted short-lived hosted jobs use reviewed default-branch workflow/adapter code
and the exact compatible shared source pin. Consumers pin the same implementation;
they supply data and producer bindings, not a fork of the state machine. Use only
managed hosted runners, explicit minimal permissions and fully pinned external
actions/reusable workflows. No PR/control-branch code, arbitrary module, artifact
script, cache executable, shell fragment or untrusted URL is executed with merge
credentials. Treat bounded artifact JSON as data and verify its native producer,
run, attempt, event and candidate identity before using it.

Use workflow_dispatch, configured workflow_run wakeups and bounded scheduled
recovery. GitHub concurrency may serialize invocations but never owns the durable
queue/slot; cancel-in-progress is false and lost pending wakeups are recoverable.
Every native side effect has a durable reservation bound to run/attempt/invocation
before the call. Clock expiry is not proof of quiescence. Reconcile actual request,
run termination and native object/ref state before retry or operator takeover.

| Native boundary | Required behavior |
|---|---|
| Refresh | updatePullRequestBranch with explicit REBASE and exact observed PR-head guard; no implicit merge update |
| Refresh base race | API has no expected-base guard; reobserve native base/ancestry and projection, then qualify actual candidate afresh |
| Refresh scope | Explicitly enrolled same-repository task refs only; exclude actual default, literal main/master and control refs |
| Required checks | Discover complete effective policy; bind App/provider, configured workflow/job, event, tested object, head/base and current attempt |
| Conditional CI | Respect native selected/none applicability; a skipped required obligation is never inferred green |
| Native security | Require actual current configured analysis categories/receipts; green scanner workflow alone is insufficient |
| Merge | Exact-head rebase-and-merge plus strict native current-base checks that the selected identity cannot bypass across the request |
| Review exception | Exact enrolled repository/identity mode; retain independent nonbypassable CI/security/freshness rules |
| Unknown refresh/merge | Read-only native reconciliation first; no blind retry, timeout takeover or guessed receipt |

Only guarded refresh of explicitly enrolled task branches is authorized by the
operator's standing boundary. Native rebase is still a history rewrite: preserve
original objects first and refuse changed heads. If a Git-level repair later needs
force-with-lease, it must use the exact enrolled ref and observed old OID; no new
expectation is substituted automatically. The default/control refs are never
force updated or deleted. Conflicts and unsupported preservation return to the
original task rather than being hidden by automatic conflict resolution.

## Policy, installation and enrollment

Extend the existing exact-repository delivery table with explicit schema 2;
schema 1 retains unchanged behavior. Add a closed coordinator configuration
binding enabled/default-off state, rebase strategy, target/control refs, reviewed
remote policy/root/source pin and guarded-refresh permission. Preserve draft PR,
ready PR, ordinary merge and exact-repository review-exception modes. No global
automatic enablement, environment override or implicit migration. New cycles may
inherit personal enrollment; existing PRs require explicit source-bound adoption.

The new delivery schema retains schema-1 fields and adds only `coordinator`.
That closed nested table has the following fields; absence means disabled:

| Field | Binding |
|---|---|
| schema_version | integer 1 for this nested table |
| enabled | boolean, default false |
| protocol_version | integer 2; incompatible helpers refuse |
| strategy | rebase only |
| remote_repository | exact native owner/name, matched to the selected remote |
| target_ref | one exact refs/heads target listed in delivery.targets and equal to the native default |
| control_ref | distinct exact refs/heads control branch |
| policy_path | exact committed regular JSON data path, with the existing safe-path rules |
| policy_digest | SHA-256 of the reviewed remote enrollment/check policy |
| guarded_refresh | boolean, default false; enrolled task refs and exact old-head guard remain mandatory |

The remote policy is closed/versioned data containing repository/default/control
and orphan-root bindings, compatible shared source pin, allowed native requester
and mutator identities, permitted events/workflow identity, check/security producer
configuration and finite operational bounds. Root/identity/credential enrollment
values are target-owned rollout artifacts, not portable source defaults. The new
runtime uses core record version 2; existing v1 offline records remain readable
and never acquire live authority. There is no silent live-ledger migration.

The thin CLI retains offline validate/status behavior. Explicit live commands are
`submit --cycle-id`, `adopt --cycle-id --pr`, `status --remote --cycle-id`,
`reconcile --cycle-id`, trusted-host `advance`, and `operator-resume --handle
--expected-generation`. Source comes from validated private custody, not a supplied
manifest file. `reconcile` may accept a proved outcome but cannot remove work.
Repair preflight derives a ChildAuthorization; existing `dbsctrctl begin` receives
an explicit `--integration-authorization DIGEST` and exact fresh launch digest.
That mode is mutually exclusive with fresh human-confirmation claims. It performs
the same feasibility, follow-up ownership, current-policy and grant-scope checks.
The skill waits on the delivery obligation after source publication and uses this
qualified repair path on failure. Resume/status picks up that obligation even
after the parent source cycle is completed. It never enables the Dagger/shadow
feedback channel or assumes an unavailable agent can execute repairs.

Keep one generated private workflow-policy owner and one compatible installed
generation for helper, package, entrypoint and guidance. Render from a clean
reviewed generation and preview/apply only owned targets; preserve unrelated local
edits and existing Dagger guidance. Update the lifecycle method revision/help and
capability qualification together when the new path is delivered.

Each repository owns its native check/trigger adapter and reviewed enrollment
data. Credentials are a separate explicit runtime boundary: prefer a least-scope
supported credential and dedicated protected environment allowing only the exact
default branch. Environment ref restrictions do not isolate a particular workflow
or job: permitted-ref workflow authors remain trusted credential principals.
Reviewed coordinator code verifies exact workflow/job/source/run identity; stronger
job-only isolation is not claimed. Never copy local credentials automatically or
reuse a production-promotion key. An installation token does not inherit a human
review exception; qualify the actual delegated identity. Source refresh must cause
unattended native PR CI and genuine merge pushes must cause existing post-merge CI.
GITHUB_TOKEN event behavior is not assumed to satisfy these requirements.

If hosted exception identity is unavailable, preserve awaiting-operator in the
same slot/protocol. `operator-resume` uses fresh guards after hosted custody is
resolved. Assisted recovery remains available without new organization approval,
but cannot be reported as unattended/offline activation. A credential value or
identity not yet enrolled is an explicit activation blocker, not a reason to
weaken policy.

## Qualification and reversible rollout

The shared source Build delivers code, default-off workflow, synthetic fixtures,
policy support and operator documentation to a draft PR. Release is not applicable
to that source slice; Deploy/Operate apply to later managed/hosted rollout and to
the activation-enabled consumer plan. Rollout records exact source/installed pins,
repository/default/control/root, requester/mutator identities, native rule IDs,
workflow/environment policy and secret reference without its value.

Require actual target evidence before activation: denied and allowed requester;
stale head/base refusal; concurrent append and retained-source ancestry attack;
refresh preservation and native PR CI; exact check/attempt/security coverage;
ordinary or review-exception merge without CI waiver; genuine post-merge native
trigger; sleeping-origin delivery; duplicate/lost wakeups; uncertain mutation
reconciliation; original-task repair pickup; archive lookup; disable/recovery.
Safe synthetic source tests are necessary and do not establish these live claims.

Disable stops admission/new mutations while preserving accepted work, source and
uncertain reservations. Reconcile uncertainty before surrendering custody. Revoke
credential delegation through its owner; retain compatible readers, ledger and
private obligations. Rollback must not apply a stale canonical generation, erase
history or strand nested approval/outcome records. No automatic cleanup is added.
Report admission wait, base invalidations, native CI queue/setup/execution, merge,
post-merge result and local acceptance separately; unavailable timing stays unknown.

## Acceptance and visual evidence

| Case | Required result |
|---|---|
| New source contains interleaved import/wrapper/repair | Complete ordered source and correspondence; original phase evidence unchanged |
| Forged JSON, requester, run or stale source | No admission or native mutation |
| Twelve admitted tasks | Durable FIFO and one final slot; independent coding/CI continue |
| Repaired or refreshed revision | Old facts retained; fresh qualification; no budget/ownership reset |
| Inherited child | Fresh exact launch and pending gates; truthful integration_grant provenance; immutable parent |
| Legacy completed source record | Separate verified outcome and custody; no opaque record edit |
| Stale retention append or source containing control genesis | Native non-force refusal; no lost ledger update |
| Changed task head or missing original source | No refresh; no default/control rewrite |
| Lost callback/unknown native effect | Durable reservation and read-only reconciliation, no duplicate mutator |
| Beyond working-ticket lifetime count | Terminal archive permits continued work and same-handle offline lookup |
| Two repairs with archived predecessors | Original obligation resolves latest ticket and all outcomes; duplicate/stale replacement or child authorization creates no competing successor/repair owner |
| Missing category/App/attempt/current base | No merge even in review-exception mode |
| Offline origin | Admitted green work may merge; repairs and local acceptance remain for original task |
| Disabled or missing credential/enrollment | No implicit enablement; same-slot assisted path remains honest |
| Existing CI, ty and shadow validation | Obligations/triggers/owners unchanged; no Dagger startup or result reuse |

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: ownership table; who validates source and who may mutate native state? |
| Interaction | required: state/event and native-boundary tables; does retention precede exact-head refresh? |
| State | required: durable-state transition table; what retains ownership during uncertainty? |
| Data/trust | required: admission and native-boundary tables; which facts authenticate an attestation? |
| Schema | required: versioned source/approval/outcome tables; how do immutable parent and new child relate? |
| Dependency/deployment | required: source-to-install-to-enrollment sequence; when is actual hosted capability proved? |
| Quantitative | not_applicable: no measured throughput claim; finite bounds and archival are safety invariants |

**Text Equivalent:** The private lifecycle validates source and attests through an
enrolled native requester. One shared core admits and coordinates immutable source
revisions. Protected control history retains source before exact-head task refresh;
fresh native CI and nonbypassable freshness permit rebase delivery. Unknown effects
retain custody. Original tasks own repair and local outcome acceptance, with honest
inherited grants and unchanged parent records. Terminal archives preserve lookup
without exhausting working state. Reviewed source precedes compatible installation,
credential qualification and target activation. Canonical source: this amendment
and linked lifecycle/distribution contracts. Owners: lifecycle, distribution and
native CI maintainers. Update tables/text together when interfaces, authority,
versions, custody, transitions or rollout dependencies change.
