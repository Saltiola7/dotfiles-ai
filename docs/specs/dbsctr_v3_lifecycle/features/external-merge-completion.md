# Completion after an external merge

[Verified rebased delivery](rebased-delivery.md) specifies a separate explicit
version-2 proof for individual commit correspondence and source preservation.
Its source implementation is additive; managed activation and consumer
qualification remain separate. The version-1 exact-tree contract below remains
unchanged and does not acquire cleanup authority.

Context: `dbsctr_v3_lifecycle`. Risk: elevated. Python support remains `>=3.12`.
This additive interface observes an already performed GitHub merge. It does not
change the merge-only execution contract in [automatic delivery](automatic-delivery.md).

## Domain and ownership

| Owner | Authority |
|---|---|
| Operator | Select the exact pull request, retained source head and observed merge object |
| GitHub | Authenticated repository, account, pull-request identity and merged outcome |
| Git | Original checkout, source content, recorded first-parent history and protected-base inclusion |
| Cycle Record | Existing gates, evidence, artifact reviews, original source identity and immutable completion receipt |

A squash can preserve the complete source tree while replacing every Gate Commit
ID. Exact tree equivalence proves delivered content; it does not establish that
Gate Commits became ancestors of the protected branch. One parent does not prove
a particular merge strategy. The proof is named `exact_tree`.

## Behavior

| Given | When | Required outcome |
|---|---|---|
| A matching GitHub cycle was externally merged with an identical source tree | Explicit completion verifies all local and remote authorities | Record `completed` with `delivered_external` evidence; preserve commits, evidence and checkout |
| An operational or other required gate is pending | Completion is attempted | Refuse without changing canonical state or active pointer, even if the PR is merged |
| A failed/unavailable gate has an existing valid operator-approved exception | Local evidence is checked | Preserve that disposition; never manufacture an exception or accept one on a pending gate |
| The target advanced after the merge | Completion checks inclusion | Compare the retained head with the merge tree, and prove the merge remains in the current protected base |
| The feature branch was deleted after merge | GitHub retains the exact PR head | Use that retained identity; do not recreate or push a feature branch |
| A different repository, base, head, merge, tree or recorded lineage is observed | Verification runs | Refuse; do not create another draft or reinterpret another PR as this cycle |
| Source, record or active pointer changes during verification | Persistence is about to occur | Refuse rather than completing changed work |
| Completion was saved but active-pointer removal was interrupted | The identical completed cycle is retried | Verify the same receipt/source and finish pointer removal without republishing or changing completion time |

## Interface and contracts

```text
dbsctrctl complete-external --pr-number NUMBER --expected-head OID --expected-merge OID [--preview]
dbsctrctl complete-external --cycle-id ID --pr-number NUMBER --expected-head OID --expected-merge OID [--preview]
```

The initial operation uses the original active checkout. An explicit cycle ID is
only for verification/recovery of an already externally completed record in its
original checkout. Supported records are GitHub `draft_pr` schemas 3, 4 and 5;
Forgejo/local-only and unversioned historical delivery are outside this interface.
Commit pins are full lowercase object IDs, with the repository's object width.
Admission supports two native merge shapes, both under the `exact_tree` proof: a
single-parent object (GitHub squash, rebase or fast-forward production is not
inferred), and an ordinary two-parent merge object accepted only as an exact-tree
merge of the retained source — the retained head must be the literal second
parent, the pre-merge base tip must already be contained in that head, and the
merge tree must equal the retained head tree, so the merge contributed no content
and rewrote no history. Any other two-parent shape, including a reconciliation
merge whose tree differs, stays outside this interface.

Admission reuses current profile, amendment, import, Graphify, gate-envelope,
artifact, clean checkout, original branch/upstream and DVC checks. Pending gates
never receive exceptions. Failed/unavailable exceptions must have the existing
validated approval shape. The reviewed CHANGELOG must be committed. The complete
ordered first-parent range from the original cycle baseline to the retained head
must equal all recorded cycle commits, including imports with no gate labels.
Every imported secondary parent must be within the delivered history: the
single-parent shape anchors them to the merge's first parent, the exact-tree
two-parent shape anchors them to the merge object itself, where the retained
head already carries them into the protected base. Unrecorded protected-base
history is not mistaken for cycle-owned work.

Use the record's selected native GitHub account, verify the authenticated principal,
pin `github.com`, and validate both configured fetch and push repository identities.
Require the exact same-repository PR number, canonical URL, recorded head/base
branches, retained head, merged state/time and expected merge object. Fetch only
the canonical protected base using existing authenticated transport. Verify the
native merge object's SHA, parents and tree against actual Git objects, its
inclusion in the fetched protected base, and equality with the retained head tree.
Replacement objects cannot supply any of these facts. Native read failures remain
unavailable evidence; no account, host or credential fallback is allowed.

`--preview` performs the same checks and may refresh remote-tracking metadata,
but never writes cycle completion or removes its pointer. Neither mode pushes,
creates/updates a PR, requests a merge, synchronizes another checkout, deletes
work, changes gates, or exports workflow feedback. A historical merged result is
not a new merge authorization or proof of current CI/protection compliance.

## Persistent state and recovery

| Relationship | Stored fact |
|---|---|
| Cycle to completion | Optional version-1 `external_completion`, immutable after successful admission |
| Completion to repository | Recorded host, repository and selected account; no token or raw API response |
| Completion to PR/source | Canonical PR number/URL, retained head/tree, merge/first parent, target branch/observed head, native merged time and verification time |
| Completion to owned history | Original ordered recorded commit IDs; existing gate envelopes remain unchanged |
| Completion to active pointer | Save the completed record atomically first, then remove only that cycle's unchanged pointer |

The receipt uses `status=delivered_external` and `proof=exact_tree`. Existing draft
publication metadata remains historical; add a compatible merged PR identity when
none was recorded. Completed retries require identical pins and receipt identity,
retain the original completion time, and never remove a different active cycle.
Final Push cannot republish an externally completed record.

Serialize through the existing cycle-evidence and delivery-target locks. Reobserve
source, record digest and pointer immediately before persistence. Rejection retains
canonical state; crashes leave either the original record or an immutable completed
record that can be retried. No checkout, branch or evidence cleanup is implied.
Existing destructive-retirement ancestry and ownership checks remain unchanged.

## Validation and maintenance

Use real disposable Git graphs and mocked native GitHub boundaries for exact-tree
squash delivery, exact-tree two-parent merge delivery, imported protected-base
history, later base advances and deleted feature refs. Refusal coverage includes
wrong identities, nonmerged/native failure, tree/parent mismatch, two-parent
merges that are not exact-tree merges of the retained head, replacement objects, unrecorded commits, stale evidence,
pending gates, dirty checkout, DVC obligations, changed source/record/pointer and
lock contention. Verify preview and rejection preserve canonical bytes, completed
retry is idempotent, and no publishing command is invoked. Existing Final Push and
local-only completion regressions remain required.

The lifecycle maintainer owns compatibility and recovery. Deploy only a verified
merged helper revision through the managed installer. Consumer qualification uses
the consumer's real gates; source tests cannot close a still-pending production
cycle. Rollback restores the previous helper while retaining the additive receipt
and evidence; it does not undo the external merge or delete completed work.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: Domain and ownership table |
| Interaction | required: ordered transition table below |
| State | required: ordered transition table below |
| Data/trust | required: owner-to-authority and persistent-state relationship tables |
| Schema | required: persistent-state relationship table |
| Dependency/deployment | not_applicable: no runtime topology changes; managed activation is an explicit later operation |
| Quantitative | not_applicable: no measured comparison or performance threshold |

| State | Guard/action | Next state |
|---|---|---|
| Active/finalizing source | Existing completion authorities and authenticated external merge proof | Verified candidate; no state mutation yet |
| Verified candidate | Preview requested | Return proof; original cycle remains unchanged |
| Verified candidate | Locks held; source, record and pointer unchanged | Atomically completed record with immutable external receipt |
| Completed record; pointer remains | Same receipt/source verified | Remove only its own pointer |
| Any rejected check | Retain source, canonical record and evidence | Blocked invocation; no invented pass |

**Text Equivalent:** The operator selects immutable remote identities. Existing
local evidence and authenticated GitHub/Git facts must all pass before completion.
Preview retains the original cycle. Mutation saves one completed receipt before
removing its pointer; an interrupted removal can be retried. Rejection grants no
delivery or cleanup authority. Canonical source: this feature; owner: lifecycle
maintainer. Update these tables when authority, ordering or receipt shape changes.
