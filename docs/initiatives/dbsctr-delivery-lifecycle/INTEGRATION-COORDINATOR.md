# Durable integration coordination

Discovery amendment, 2026-11-11. This extends the existing approved lifecycle,
distribution, shared-validation and adjacent consumer-toolchain map. The operator
now assigns coordinator and current GitHub Actions adoption to this delivery
work; the separate validation owner receives a Dagger handoff. It supersedes only
the deferred queue-ownership and after-cutover assumptions in
[REBASED-DELIVERY.md](REBASED-DELIVERY.md). Earlier delivered behavior, source
history and unrelated slices remain intact.

## Settled outcome and boundaries

Keep concurrent coding, separate cohesive pull requests and individual phase
commits. One shared implementation coordinates each enrolled repository's default
branch. GitHub Actions hosts it independently of a developer computer or chat.
One final candidate is active per target; repositories progress independently.
The normal personal merge path uses that coordinator. A direct default-branch
merge is an explicit override and invalidates an outstanding candidate.

The first release preserves all current CI triggers and check obligations. It
addresses moving-base invalidation among cooperating mergers, not the separate
runner-capacity problem. It neither gates expensive suites until admission nor
promises shorter runner queues. Batching, speculative candidates, altered matrix
coverage and result reuse remain later qualified changes.

GitHub Actions is authoritative. Dagger remains a separately enrolled, default-off
shadow pilot. A shared candidate contract lets that owner observe the same
source/base/plan while preserving its compute budgets; it confers no native
status, merge or lifecycle-gate authority.

Shared automation remains off by default. Personal repository/task delivery
selection preserves draft PR, ready PR, ordinary merge and explicitly allowed
review-exception merge. New cycles may inherit enrolled policy; existing pull
requests require explicit adoption. No historical cycle is silently upgraded.

## Approved context map and implementation ownership

| Existing home | Responsibility in this amendment | Implementation owner |
|---|---|---|
| Lifecycle / coordinator repository | Portable queue, candidate and native-outcome contract; source-series attribution; original-task reconciliation and repair ownership | This delivery work |
| Distribution / coordinator repository | Compatible installation, personal policy, credential enrollment and hosted-runtime qualification | This delivery work, with explicit activation approval |
| Shared continuous validation / coordinator repository | Existing snapshots, Dagger shadow execution, resource admission and qualified feedback; later execution reuse | Existing validation work, through the handoff |
| Adjacent consumer toolchain / governed repository | Existing authoritative checks, native trigger behavior, producer bindings, current adapter and telemetry | Consumer delivery work |

The adjacent consumer's exact identity and implementation artifacts remain in its
own governed repository and private handoff. No private consumer source, account,
URL or local runtime identity enters this public Initiative. Existing control
planes remain feedback transports; no new conversation or repair agent is created.

## Minimum architecture

Use one portable Python core and one thin entrypoint, with pinned reusable Actions
steps and repository-owned check configuration. Do not copy coordinator logic
into consumers or Dagger. The [lifecycle feature](../../specs/dbsctr_v3_lifecycle/features/integration-coordinator.md)
owns proposed interfaces, state guards and acceptance cases.

The independent core slice implements bounded schemas, deterministic transitions,
CAS construction and injected native/source/persistence interfaces. Unsupported or
unqualified live ports return unavailable. SourceSeries production, authenticated
native adapters, lifecycle reconciliation and hosted authority are later slices;
fixtures and a source entrypoint do not establish those capabilities.

Durable state is repository-local metadata on one enrolled control branch. Native
expected-head compare-and-swap appends preserve its history. Bounded request and
receipt files use opaque handles; exact local task/session mappings remain private.
A submission is not admitted merely because an event or workflow was accepted.
Only durable admission creates a queued ticket. Native no-rewrite/no-delete rules
must cover every ledger writer; expected-tip CAS alone cannot detect a historical
rollback after a stateless restart. Root ancestry and bound current native rules
are checked on every load; unqualified enforcement blocks hosted activation.
Short stateless hosted invocations
advance that state; dispatch, completion callbacks and scheduled recovery are
wakeups, not another queue or evidence ledger.

The logical candidate slot spans fresh base capture, source refresh, native CI,
security qualification and merge. Clock expiry alone never grants another merge
owner. Stale callbacks cannot overwrite a newer generation. A worker recovering
from a crash reconciles native outcomes before retrying uncertain mutations.
Outside writers can still invalidate the candidate; native current-base protection
remains necessary across the actual merge request.

Current passing CI may be used only for the exact eligible source/base, actual
producer and current attempt under its existing contract. This is observation of
native CI, not cross-commit test-result reuse. A green scanner workflow alone is
insufficient when the native security policy expects another analysis category.

## Review exception and unavailable-identity fallback

Ordinary and review-exception delivery use the same queue, candidate, CI verifier
and native outcome reconciliation. Administrator use is exact-repository and
identity-bound; it cannot waive failed, pending, missing or unqualified checks.
Require a native freshness guard that the selected identity cannot bypass across
the merge request. Unknown protection behavior leaves delivery unavailable.

Hosted credentials need their own enrollment and trigger qualification. Do not
copy a local credential, assume an Actions token inherits an operator exception,
or enable another identity automatically. Qualification must prove unattended
source-refresh CI and post-merge validation triggers as well as merge permission.

If the remote merge identity is unavailable, preserve the active ticket as
awaiting an authorized operator. The operator may resume the same candidate with
the existing exception and fresh guards; this is one coordinated protocol, not a
second independent merger. It cannot promise unattended delivery while that
identity is unavailable. No new organization approval is assumed by the first
assisted path; full hosted activation remains contingent on qualified enrollment.

## Source history, completion and feedback

Capture the original recorded Gate Commit series before later integration
wrappers. Authorized default-base refresh merges and explicit empty CI-refresh
commits are separately identified control history; they cannot hide source edits,
dropped/reordered phases or new unvalidated work. Rebase delivery verifies the
ordered original-to-landed phase correspondence and native introducing PR.

A hosted receipt records verified remote delivery. It does not edit an offline
Cycle Record, establish local source-object custody or authorize cleanup. The
original checkout later consumes the receipt through a qualified lifecycle API,
retaining original evidence and existing preservation checks. Explicit selected
old-PR adoption must handle a completed source-delivery record and authorized
wrapper lineage; the current helper's narrower completion route is not assumed
to support that case. No opaque state editing is permitted.

Required failure diagnostics return to the original task. A closed or offline
agent retains pending repair until it resumes; no replacement agent is launched.
Routine changed-code repairs preserve inherited intent consent. Competing behavior,
material scope, authority or risk changes require the operator. The service does
not repeatedly rerun unchanged failing tests or invent a fixed three-repair cap;
existing repair authorities require explicit compatibility qualification.

Post-merge checks and production eligibility retain their consumer-owned contracts.
Report merge, post-merge validation and local reconciliation separately. Pending
post-merge results are not reported green. An integration slot may finish after
verified default-branch delivery while downstream native validation proceeds;
this amendment adds no failure waiver or new global production policy.

## Delivery slices and dependencies

### Runtime-adapter consolidation, 2026-11-12

The operator now authorizes completing lifecycle/current-Actions adoption and
activating both selected targets. The
[runtime adapter amendment](../../specs/dbsctr_v3_lifecycle/features/integration-runtime-adapters.md)
owns the qualified source delta and target rollout requirements. One cohesive
`integration-runtime-adapters` Build slice replaces the three unstarted
lifecycle/actions/distribution placeholders below; their manifests are deferred
as duplicate scopes, not three additional implementations. The delivered offline
core remains the prerequisite. A private consumer follows its own adapter plan
against the resulting merged source pin, then exact-target installation/hosted
qualification follows. Dagger remains with its separate owner.

The offline foundation delivered in PR #311 at
`6ec4d3f68a9014fdae52dab4cd63f006864c2847`, with native post-merge validation
successful. That evidence supports marking only its source slice delivered;
installation of an unavailable-by-default CLI does not establish live adapters.
Fresh staged publication/instruction qualification for this amendment passes 57
cases. Independent lifecycle and native-authority reviews found no remaining
source-readiness blocker after revision-identity and writer-restriction corrections.
These are Discovery results, not runtime or activation qualification.

The source slice includes ordered source/refresh records, repair/supersession and
bounded working-state archival, private obligation/outcome custody, honest inherited
repair authorization, the thin native worker and schema-2 existing delivery policy.
Guarded task-head refresh is expressly allowed after original-object retention
with an exact old-head guard. The actual default, literal main/master and control
refs are excluded. This narrows the historical never-force rule only for that
enrolled task operation; it grants no default/control rewrite, cleanup or automatic
conflict resolution.

New-source preflight/approval, credential delegation and actual activation evidence
remain distinct. General target activation is authorized; no credential is copied
or enrolled by inference. The source PR stays default-off until merged, installed
and qualified. The runtime amendment supersedes earlier assumptions that a flat
phase/wrapper list, original-head-only candidate or lifetime retained-ticket bound
would be sufficient for live adoption.

| Slice | Scope | Boundary |
|---|---|---|
| integration-coordinator-core | New shared core, thin standalone entrypoint and deterministic fixtures; no existing lifecycle/helper rewrites | Source-only critical draft; production activation off |
| integration-lifecycle-adoption | Local descriptor/submission, selected old-PR adoption, receipt reconciliation and existing helper/guidance hooks | After core; serialize shared helper changes with active lifecycle work |
| integration-actions-adapters | Default-off reusable controller workflow and current repository adapter; native producer/security/trigger qualification fixtures | After core and lifecycle contract |
| integration-distribution-policy | Versioned existing repository policy and targeted compatible module installation | After source interfaces; no competing policy or credential owner |
| integration-hosted-rollout | Enrollment, control-state initialization, exact hosted identity and both native-route qualification | Separate target-bound deployment approval |
| integration-runtime-adapters | Consolidated lifecycle, native worker, compatible policy and durable-v2 source after delivered offline core | Critical shared source draft; target activation follows actual qualification |
| dagger-delivery-adoption | Shared candidate references and explicit shadow observations only in the first adoption stage | Existing validation owner; no queue fork or cutover |

The adjacent consumer persists its own adapter feature and launch plan against the
qualified shared core pin. Private artifact coverage stays there. This is one
method with per-repository configuration, not two coordinator implementations.

The first source slice deliberately owns new module/entrypoint/test files. Active
validation work touches the existing lifecycle CLI, skill and README. Later hook
integration must reconcile its merged source and preserve both histories; this
plan grants no takeover, reset or managed apply from a stale primary checkout.

## Engineering profile and validation

Critical risk: unattended protected-branch mutation, credential authority and
source-history reconciliation. Python and Security apply; Cloud applies to hosted
execution, and Shell applies where execution/environment semantics change. Shared
core supports Python >=3.12 on the qualified Linux hosted runner and installed
operator platforms; it requires no Dagger engine or new runtime installation.

The core plan marks all kernel, Review/Integrate and Maintain/Retire gates required.
Release, Deploy and Operate are not applicable to its source-only draft with no
installation, credential export, repository setting change or live worker start.
Later rollout requires actual Deploy/Operate evidence. Project-selected typing,
pytest, public-content/instruction checks and relevant workflow/security review
remain authoritative. Source fixtures do not establish native hosted authority.

Qualification covers simultaneous submissions/CAS, duplicate/lost wakeups, crash
and uncertain merge recovery, stale generations, base/head/policy drift, actual
required-check producers and attempts, missing scanner categories, ordinary versus
review-exception guards, denied identity, current CI trigger preservation, phase
mapping, local custody and privacy. Require no Dagger startup on the default path.
Measure queue wait, base invalidations, CI queue/setup/execution, merge time,
post-merge outcome and local reconciliation separately; unavailable timing stays
unavailable. No forecast is presented as a measured speedup.

## Readiness and launch

Intent and ownership are settled for coordination-first. Source readiness follows
publication and contract review. The operator's subsequent instruction authorizes
the two-target rollout; exact credential delegation and native qualification remain
required and are not established by this document.
Only a Build-owned ready slice may issue a fresh Initiative receipt. Build must
perform the actual import-aware preflight and obtain its exact launch approval.
No separate Discovery publication is a prerequisite; the normal implementation
PR carries the complete changed-document closure. Later source and rollout slices
retain their own dependency, authority and feasibility checks.

## Registration qualification correction

The first approved launch preserved its document import, then native registration
refused before writing a Cycle Record. Its post-import inventory read an unrelated
historical amendment against the caller's changed distribution profile. That
profile's pre-import bytes match the retained source authority. Preserve that
interrupted checkout and import; do not reset it, edit private records or infer a
completed registration.

This editorial correction retains both existing Engineering Profiles unchanged.
Their Python, Security and Cloud defaults already apply; the feature and explicit
cycle plan retain critical risk and source-only applicability. No behavior,
acceptance, required check, implementation scope or risk is reduced. This avoids
expanding the core source slice into lifecycle-helper changes. Historical guard
repair and interrupted-creation recovery remain separate owner work. Prepare a
new clean Worktrunk target, qualify it and obtain its fresh exact launch approval.

## Discovery validation

The configured public-content and instruction authority ran over the complete
staged artifact inventory: 92 cases passed, one existing capability skip. The
initial missing canonical Visual Evidence headings were corrected before that
successful run. Native Initiative consistency and staged whitespace checks pass.
These are Discovery/publication results, not implementation gate passes, hosted
qualification or runtime evidence. The private consumer's configured pre-commit
checks, including secret detection and documentation colocation, pass separately.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: context table; who owns each interface without duplicating a coordinator? |
| Interaction | required: architecture and exception paragraphs plus feature interaction table; which steps survive a closed chat? |
| State | required: feature transition table; when is queued, delivered, blocked or uncertain truthful? |
| Data/trust | required: feature trust table; which evidence may authorize a mutation? |
| Schema | required: feature record table; how do original source and current candidates remain distinct? |
| Dependency/deployment | required: slice table; what may ship before hosted enrollment or Dagger cutover? |
| Quantitative | not_applicable: timing fields are specified, with no numerical performance projection |

**Text Equivalent:** Concurrent tasks submit to one per-target durable queue.
One pinned candidate is validated with existing native CI and merged through
qualified ordinary or operator-exception authority. Shared validation may observe
it in shadow mode. Remote delivery and original-checkout reconciliation are
separate. Source precedes credential/runtime enrollment. Failed work returns to
its original task while other eligible work continues. Owner: delivery Discovery;
canonical source: this amendment and the linked feature. Update when ownership,
source lineage, authority, state or release dependencies change.
