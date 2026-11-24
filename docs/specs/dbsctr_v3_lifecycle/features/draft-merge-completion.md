# Complete a published source cycle at verified merge

**Discovery contract; not yet implemented.** Owner: lifecycle maintainer.
Critical risk; Python and Security; [Engineering Profile](../PROFILE.md).
For new GitHub `draft_pr` cycles, publication releases the checkout. Successful
completion means the cycle's work is proven to have landed. This applies both
to ordinary draft publication and to explicitly enrolled coordinated PRs.

## Which facts are known?

| Fact | Authority and binding | What it does not establish |
|---|---|---|
| Published | Final Push independently confirms the same-repository PR, feature ref and exact published tip. Freeze the cycle ID, original source and Gate Commits, evidence/exception and effective Initiative bindings, repository/account, PR number/URL, target and publication time. | Merge, completion or current CI |
| PR merged | Authenticated GitHub reports this closed, merged PR, its full head and merge IDs and native merge time. Verify the repository and both refs, the actual Git merge object, and its inclusion in the independently fetched protected target. | Which published changes survived, a gate pass or cleanup eligibility |
| Delivered | Existing qualified Git/GitHub proof accounts for the selected cycle's work at that merge; its effective required gates have valid dispositions. Use the applicable exact-tree, supported base refresh, verified rebase or reconciled-segment proof with its own guards. | Delivery of a different cycle on the same PR or a fresh check of CI, deployment or operation |

`--expected-head` selects the PR head at merge; the frozen **published** head
may differ. Keep both. A PR closed without merging, a wrong pin, absent
target inclusion or an unavailable provider cannot produce a merged fact.
Conversely, a verified merged fact is recordable even when source correspondence
is unavailable. Report the missing proof and the next verification action.

## State, custody and recovery

| From | Event | Durable result |
|---|---|---|
| Active/finalizing | Publish the verified draft or ready PR | Save its immutable publication snapshot and `awaiting_merge`; no `completed_at`. Only then release that cycle's matching active pointer. |
| Awaiting merge | Review requires changes | Keep the snapshot frozen. A linked, separately admitted follow-up owns corrections. A new active cycle may occupy the original checkout. |
| Awaiting merge | PR merge observed, but delivery or required evidence is unverified | Append the approved observation. Show `PR merged` and `delivery unverified` with reason; the cycle is still pending verification. |
| Awaiting merge (including a prior merged observation) | The exact merge, qualified delivery proof and required gate dispositions verify | Bind completion to the snapshot and proof; set `completed_at` once. Keep `published_at`, native `merged_at` and verification time distinct. |
| Legacy Final Push already completed | Observe its matching PR by cycle ID | Append separately from the historical record. Keep the original record bytes, open/draft publication snapshot, `completed_at`, evidence and any pointer unchanged. |
| Any state | Identical retry, stale pins, changed input, or interrupted write | Replay the exact stored outcome once, or refuse with the changed binding. Never republish, recreate a pointer, remove a foreign pointer or assign another cycle credit. |

Bind the prospective lifecycle contract/version at registration. An older active
cycle still uses its original delivery contract. Older writers must refuse new
state they cannot preserve. Preserve schemas 3/4/5 and existing external and
post-delivery receipt versions; Forgejo/local-only and branch delivery keep
their meanings. There is no bulk migration or reinterpretation of old completions.

Use existing private receipt custody. The new observation must distinguish the
native PR fact, cycle delivery disposition and source proof (nullable with
reason). Bind its cycle/publication digest, expected predecessor, repository,
target, PR/head/merge pins, ordered owned source and stable evidence identities.
Use a versioned entry; do not stamp a v1 verified receipt on an unverified
landing. Retain each deferred condition under its original meaning. Historical
records bind their original bytes; new records bind the immutable snapshot
rather than their changing current state. Preserve approved append semantics:
recheck pins, identity, digest and predecessor under the existing writer/evidence
and target locks. An exact retry after interruption between append and state
save finishes only that transition. A later observation appends; it cannot
rewrite an earlier one.

## Operator and coordinator interfaces

- `final-push` reports the selected PR, published head and pending merge. Once
  frozen, ordinary gate, amendment and publication writers cannot change it.
  Resolve an uncertain publish by reading the exact remote ref and PR first.
- `complete-external --cycle-id ID --pr-number N --expected-head HEAD
  --expected-merge MERGE --preview` selects the exact publication without an
  active pointer. An append uses the same pins, `--expected-receipt-digest`
  and existing exact approval. Do not rerun work or infer the selected record
  from the current branch. Explicit retries of existing `external_completion`
  receipts and the existing active-cycle route keep their original contracts.
- `status --cycle-id ID --json` reads the stored publication, latest native
  observation, delivery disposition/reason and dates **offline**, even with a
  different active cycle. Plain `status` retains its active-checkout meaning.
  Preserve [post-delivery v1](post-delivery-receipts.md) and its explicit
  `--post-delivery` read/append interface. Route compatible requests to the
  same custody owner; never create competing histories. Preview changes no
  record, receipts, pointers, refs, index or working files.
- The [integration coordinator](integration-runtime-adapters.md) accepts the
  frozen source before completion, using its existing enrollment, grant,
  source retention, native outcome verifier and private obligation. Its existing
  verified outcome can complete the exact cycle under that grant. Preserve
  old completed-record digest checks for old tickets; a new ticket binds the
  frozen snapshot. A ticket alone cannot prove delivery. Ordinary publication
  neither creates a ticket nor authorizes a merge. Both paths converge on one
  idempotent completion for the same proof.

## Build acceptance

Use disposable Git histories and the existing synthetic GitHub boundary:

1. Register a native Initiative, amend it, pass its actual fixture gates, publish
   through the CLI, and acquire the freed slot with a second cycle. From another
   checkout preview, record, inspect offline and retry the first merge by ID.
   Assert identical receipt/time on retry and byte-identical second pointer.
2. Cover an unchanged tip, an accepted base refresh, and a different substantive
   head on the same PR. In the last case persist the native fact only unless a
   qualified proof accounts for this cycle. A later successful proof completes
   exactly once. Closed-unmerged, wrong pins/repository/target, pending gates,
   unavailable native evidence and a deleted feature ref have distinct outcomes.
3. Repeat with a historical Final Push record, old external receipts, and an
   enrolled coordinator submit, verified outcome and duplicate callback. Exercise
   contention, binding drift, interrupted publication/append/completion and a
   replaced or absent pointer. Verify original evidence/approvals, source
   retention, checkout and existing retirement guards survive every path.

Start with `tests/test_dbsctr_external_completion.py`,
`tests/test_post_delivery_receipts.py`, `tests/test_completion_reconciliation.py`
and `tests/test_integration_lifecycle.py`. Include existing registration,
follow-up, status/inventory, preservation and negative local-only consumers
where they interpret cycle state. See the [source handoff](../../../initiatives/dbsctr-workflow-convergence/BUILD-HANDOFF.md#publication-and-evidence).

## Visual Evidence

- **Boundary and data/trust — required:** “Which facts are known?” identifies
  the lifecycle writer, GitHub, Git and their separate authorities.
- **Interaction, state and schema — required:** the transition table and custody
  rules show one frozen publication, successive observations and at most one
  successful completion.
- **Dependency/deployment — required:** the source handoff orders the slices;
  Build tests both coordinator and ordinary routes before separate activation.
- **Quantitative — not applicable:** no measured comparison or threshold.

**Text Equivalent:** Publication freezes source and frees its slot. Native reads
may establish a merge before they establish delivery. The cycle completes only
on qualified delivery and disposed gates. A legacy completion never changes.
Owner: lifecycle maintainer; update both tables when an authority, transition,
receipt binding or outcome changes.
