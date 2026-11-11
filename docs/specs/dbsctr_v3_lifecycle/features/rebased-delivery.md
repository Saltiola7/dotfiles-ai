# Verified rebased delivery

Engineering Profile: [../PROFILE.md](../PROFILE.md). Owner: lifecycle maintainer.
Risk: critical because delivery evidence participates in destructive retirement.
Modules: Python and Security. Source-only slice: `rebased-completion-core` in the
[delivery Initiative](../../../initiatives/dbsctr-delivery-lifecycle/REBASED-DELIVERY.md).
The source implementation supplies this capability. Managed installation and
native consumer-route qualification remain separate activation obligations.

## Outcome and scope

Preserve each cycle-owned phase commit as an individual commit on the ultimate
default branch after rebase-and-merge. Git object IDs may change. Original Cycle
Record commits, gate envelopes, failures and approvals remain immutable historical
evidence; a separate verified mapping records the landed identities. The ordinary
six-phase workflow is unchanged. A routine hash rewrite alone is not a new cycle
or a new operator approval event.

Extend [external completion](external-merge-completion.md) and the existing
preservation predicate. The operation observes an already completed merge; it
does not rebase the active checkout, repair code, request a merge, waive CI, delete
a branch, synchronize a primary or start a runner. Dagger and its existing
feedback interfaces consume this capability separately.

## Engineering profile and compatibility

Use supported Python `>=3.12`, native Git and the existing authenticated GitHub
reader. Preserve current GitHub Cycle Record schemas 3/4/5 and version-1
`exact_tree` receipts. Forgejo/local-only records are outside this first slice.
No new package, service, provider credential, user interface or Product Intent
artifact is introduced. Logs, source identities and receipts stay private.

The new proof is selected explicitly. Old receipts never become rebased-delivery
authority implicitly. Older readers encountering the new receipt version may
report unsupported; an old writer must not reinterpret or erase it. Rollback
disables new admission, preserves new receipts/evidence refs and restores a
compatible reader before operations resume. Do not claim downgrade compatibility
for an older binary that does not understand the receipt.

## Domain and schema

| Entity | Meaning and relationship |
|---|---|
| Original commit | One immutable cycle-owned recorded commit, with its existing gate attribution |
| Landed commit | One distinct native single-parent commit in the verified default-branch history |
| Commit correspondence | Exactly one original-to-landed pair; order and content effect are independently verified |
| Landed base | Parent of the first landed commit; the original cycle baseline must be in its ancestry |
| Rebased delivery receipt | Immutable native PR identity, original source identity, ordered correspondence and observed protected target |
| Evidence ref | Private internal Git ref preserving the original source history after feature refs are removed |

Add version 2 to `external_completion`, using `proof=rebased_commits` and
`status=delivered_external`. Preserve the version-1 identity fields, including
original `head`, `tree`, `recorded_commits`, native `merge`, its literal
`merge_parent`, and observed `target_head`. Add `landed_base`, ordered
`commit_mapping` entries containing exactly `original` and `landed` full object
IDs, and `source_retention_ref`. The last landed commit equals `merge`.

The source list is exactly the record's complete ordered first-parent cycle
range. No commit is identified solely by a message, author, timestamp, matching
position, phase label or whitespace-normalized patch ID. Gate-to-original
relationships remain in their existing owner; the mapping adds landed attribution
without rewriting those relationships. Reject unknown fields/versions, missing,
duplicate or differently sized mappings and inconsistent object widths.

## Interface and verification

Extend the existing command with an explicit optional proof selector:

```text
dbsctrctl complete-external --proof rebased_commits
  --pr-number NUMBER --expected-head OID --expected-merge OID [--preview]
dbsctrctl complete-external --proof rebased_commits --cycle-id ID
  --pr-number NUMBER --expected-head OID --expected-merge OID [--preview]
```

Omitting `--proof` retains `exact_tree`. Explicit cycle selection remains limited
to idempotent verification/recovery of the already completed matching record.
Derive the mapping from verified Git/native objects; never accept caller-authored
mapping JSON as proof. No separate CLI, daemon or persistent queue is needed.

Admission reuses original-checkout, exact-source, artifact-review, required-gate,
valid-exception, DVC, authentication, repository and PR-identity checks. Native
`merged` metadata alone is not current CI compliance or merge authorization.

For the first supported proof:

1. Verify the original complete recorded range against retained source and the
   original baseline. Each source commit must be a nonempty single-parent commit;
   merged/imported, dropped, empty or otherwise ambiguous series remain explicitly
   unsupported rather than partially attributed. Preserve the source on refusal.
2. Starting from the native PR's verified resulting commit, identify an equally
   sized consecutive single-parent landed range and its preceding landed base.
   Verify native merged head/base/PR identities and actual Git objects. The result
   must remain in the freshly fetched ultimate default; the original baseline
   must be an ancestor of the landed base. An intermediate target does not qualify.
   For each landed commit, the native introducing-PR observation must uniquely
   match this verified PR. Otherwise a dropped leading phase could be confused
   with equivalent work already introduced by another PR. Missing or ambiguous
   native association is unavailable proof, not permission to borrow that work.
3. Verify correspondence per commit by deterministic, conflict-free replay of
   each original delta onto that landed commit's parent and exact resulting-tree
   comparison. This admits unrelated changes on the newer base without claiming
   the original final tree equals the integrated tree. Ambiguous/conflicting
   replay, missing objects, extra edits or unsupported Git semantics refuse.
   Disable replacement/graft influence and source-controlled hooks, external
   filters and merge drivers; replay must not execute repository code or mutate
   the original worktree, index, branch or gate evidence. Use bounded isolated
   native Git operations; an unsafe/unqualified capability is unavailable.
   The first implementation refuses grafts, local filter/merge-driver definitions,
   merge/filter/encoding attributes in compared trees, and submodules. Replay
   requires the selected native Git to support an explicit merge-base.
4. Recheck source/record/pointer and native PR/target identities under the existing
   evidence and target locks before persistence. Historical base advancement
   after the merge is allowed when the verified landed range remains included.
5. Preserve original Git objects through the private evidence ref, save the
   immutable receipt/completed record atomically, then remove only the matching
   active pointer. Preserve the current save-before-pointer-removal ordering.
   Reverify retained custody after the final potentially executing source/DVC
   inspection, then reobserve record, pointer and cheap source facts before save.

First-slice unsupported cases are capability limits, not permission to squash or
drop a phase. A provider grouping multiple PRs must expose an unambiguous verified
result for this PR; group-level success or a terminal group SHA alone cannot
supply another task's mapping. The adoption owner must qualify the actual route
before selecting it. Material implementation findings reopen Discovery.

## Evidence preservation and retirement

Use the Git-common owner and an internal namespace
`refs/dbsctr/evidence/<cycle-id>` for `source_retention_ref`; it points to the
original source head and is not a feature branch or tag. Validate the existing
cycle identifier as a safe ref component. Create it with an expected-absent
compare-and-set, or verify the identical already-owned ref. Never replace a
different target. Create/verify it only after proof admission and before saving
completion. A crash may leave a retained ref; retry reconciles it without losing
source. Preview creates no ref or completion state.

This ref keeps original commits and their reachable Git objects alive under Git
garbage collection. Retain private Cycle Records/envelopes under existing custody
as well. The ref is not an off-host backup or a claim that ignored data are
preserved. It is not automatically pushed, mirrored or garbage-collected by this
operation; existing governed backup and later explicit evidence retirement own
that lifecycle. This permits finished feature branches to disappear without
making original evidence depend on undocumented hosting retention.

For qualified version-2 receipts only, the existing removal predicate may satisfy
its history obligation through freshly reverified correspondence and ancestry of
every landed commit into the ultimate default, together with the matching retained
source ref and original evidence. The retained source HEAD must still match the
receipt; any later source work blocks retirement. Original baseline obligations
and foreign/pre-cycle ownership checks remain. No cached receipt-only acceptance.
The source-only default oracle also requires fresh per-landed-commit introducing-PR
observations; it does not authenticate caller-created observations or remove the
existing unavailable runtime-qualification reasons.

All other [preservation predicates](workflow-preservation-retirement.md) remain
mandatory: artifact/DVC preservation, clean and owned worktree, terminal correlated
cycles, quiescence, primary compatibility, native handoff when needed, policy and
removal coordination. Missing qualifications remain blockers. Existing exact-tip
local branch deletion and separately authorized remote branch policy own removal;
this command never deletes anything or changes hosting settings. Historical
version-1 `exact_tree`/squash receipts do not gain this exception.

## Behavior and recovery

| Given | When | Then |
|---|---|---|
| All phase commits were rebased individually with unchanged effects | Native/source proof passes | Preserve original evidence, record every landed ID and complete the original cycle |
| The target includes unrelated newer base work | Per-commit replay matches landed trees | Accept without demanding equality of the two final source trees |
| Only commit IDs changed | Completion reconciles delivery | Do not reopen development gates solely for new IDs |
| A phase is missing, squashed, reordered, conflict-edited or unprovable | Mapping is attempted | Refuse with a bounded reason; retain source/evidence; never invent a pair |
| Required local gates remain pending or invalidly excepted | PR is already merged | Refuse completion; preserve actual gate results |
| Feature branch was deleted remotely | Original source and native PR identity remain verifiable | Verify through retained source and native metadata without recreating the branch |
| Completion save succeeds but pointer removal is interrupted | Identical retry occurs | Reverify and finish pointer removal without changing receipt or completion time |
| Source, target, PR identity or evidence ref changes during verification | Persistence/retirement is attempted | Refuse or retain for fresh reconciliation; never erase competing work |
| Mapping succeeds but data, session or native-removal evidence is unavailable | Cleanup is evaluated | Report delivery as verified and cleanup as blocked, separately |

## Validation, gates and handoff

Use real disposable Git graphs plus the existing mocked authenticated native
boundary. Cover several phase commits, distinct source/landed IDs, unrelated
base changes, later target advances, remote branch deletion, local evidence-ref
retention through isolated Git GC, and cleanup-history eligibility with all other
predicates independently required. Negative cases include duplicate/reordered or
missing commits, whitespace-significant edits, same-message wrong content,
conflict resolution, source merge/empty commits, unrelated ancestry, grouped-PR
ambiguity, replacement objects, active Git drivers/filters, missing objects,
changed refs, interrupted persistence, stale identity, pending gates and dirty
worktrees. Do not call live merge or removal APIs as tests.

Extend affected tests in `tests/test_dbsctr_external_completion.py`,
`tests/test_native_adapter_retirement.py` and the existing lifecycle/helper suites
where their predicates are owned. Retain version-1 exact-tree behavior and
historical-record regressions. Use existing publication/instruction authorities,
Python compilation and `git diff --check`; no new validation framework.

Current Gate Results and any approved Gate Exceptions belong to the private Cycle
Record. This table selects applicability rather than duplicating live execution.

| Gates | Source-only applicability |
|---|---|
| Domain, Behavior, Spec, Contract, Test-driven implementation, Refactor | required |
| Review/Integrate; Maintain/Retire | required |
| Release | not_applicable: no independent package/image publication |
| Deploy; Operate | not_applicable for source-only draft PR; required in later managed qualification |

Keep source changes within the existing helper, its affected tests and lifecycle
guidance. Managed installation and a representative native rebase route require
separate activation evidence before the Dagger owner consumes this capability.
The [Initiative handoff](../../../initiatives/dbsctr-delivery-lifecycle/REBASED-DELIVERY.md)
owns queue, feedback, consent and consumer integration; this proof does not grant
those capabilities. Launch requires a fresh receipt, real preflight and exact
operator approval through the existing Initiative route.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | required: scope/profile and domain table; what does lifecycle prove versus execute? |
| Interaction | required: numbered verification and behavior table; what precedes persistence and cleanup? |
| State | required: behavior/recovery table; what completes, refuses or remains retained? |
| Data/trust | required: verification/retention tables and prose; what proves attribution and preserves private evidence? |
| Schema | required: domain table and versioned field contract; how do original and landed identities relate? |
| Dependency/deployment | required: gates/handoff table; why is source readiness distinct from adoption? |
| Quantitative | not_applicable: no benchmark or numerical performance claim |

**Text Equivalent:** Each original recorded commit maps to one verified landed
commit. Exact per-commit replay and native PR/default inclusion establish that
mapping; original evidence remains under its existing owner and a private ref
keeps its Git objects reachable. Proof and retention precede atomic completion,
which precedes matching-pointer removal. Cleanup separately revalidates the
mapping and every existing non-history guard. Unsupported or changed state
retains work. Source: this feature and its Initiative requirements. Owner:
lifecycle maintainer. Update the schema, sequence and equivalent together when
attribution, authority, retention, compatibility or recovery changes.
