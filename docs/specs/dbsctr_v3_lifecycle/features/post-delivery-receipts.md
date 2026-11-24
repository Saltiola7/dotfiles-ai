# Post-delivery receipts for completed draft PR cycles

Owner: lifecycle maintainer. [Engineering Profile](../PROFILE.md). Critical risk;
Python and Security. This is the source contract for the `post-delivery-receipts`
slice of [workflow convergence](../../../initiatives/dbsctr-workflow-convergence/README.md).
The interface below is implemented in source. It records neither installed
qualification nor a live recovery; both need a separately approved rollout.

## The three questions

Final Push completes the cycle at draft delivery. A PR may merge later, and an
operating check may only become possible after that. The operator needs three
answers with separate authorities:

| Question | Source of truth | What the receipt may say |
|---|---|---|
| What did this cycle deliver? | Original completed Cycle Record, delivery metadata and owned commit identities | Published feature head, completion time, original results and exceptions, **as recorded** |
| What landed? | Authenticated PR metadata **and** native Git objects in the recorded repository and protected branch | Whether that published head is accounted for in the verified merge, and how |
| Which review conditions were met later? | Original condition and its owner, plus individually bound later evidence or an explicit owner decision | A disposition for **each condition**, including what is still unverified |

A post-delivery receipt is a separate, private, immutable observation. Original record
bytes, completion time, evidence, failed runs, exceptions and active pointers stay
unchanged. A merged PR is neither a passing CI result nor proof of deployment,
operation or cleanup eligibility. [External completion](external-merge-completion.md)
still owns active-cycle completion and retries of its own completed receipts.

## CLI and proof

`complete-external --post-delivery` extends the existing completion handler. The
unflagged command keeps its meaning and its refusals.

```text
dbsctrctl complete-external --post-delivery --cycle-id ID --pr-number N \
  --expected-head MERGED_PR_HEAD --expected-merge MERGE \
  [--review-evidence GATE:CONDITION:SOURCE_CYCLE:EVIDENCE_ID] [--owner-review GATE:CONDITION] --preview
dbsctrctl complete-external --post-delivery <same selectors> \
  --expected-receipt-digest SHA256 --approval agent-confirmed
dbsctrctl status --post-delivery --cycle-id ID --json
```

| Step | Contract |
|---|---|
| Selection | A completed GitHub `draft_pr` record (schemas 3/4/5; ordinary or Initiative), by exact ID in the invoking Git common directory. The PR number must equal the recorded one. An active record, a local-only record and a record that already holds an `external_completion` receipt are each refused with a bounded reason. |
| Where it runs | Any checkout of that repository. The cycle's own checkout, branch and active pointer are not required, and none is recreated or removed. The mode writes no cycle state, so the checkout-binding guards that protect lifecycle writes do not apply to it. |
| Delivered tip | The last entry of `record.commits`, when the cycle base and every recorded commit are retained and their first-parent chain equals the recorded commits. Otherwise the landing is `unavailable` with `retained_source_unavailable`. The current checkout and a branch name never supply it. |
| Request pins | `--expected-head` is the PR head at merge and must equal the authenticated PR head. `--expected-merge` is the landing commit. `--proof` stays `exact_tree`. |
| Options | The review options, `--expected-receipt-digest` and `--approval` are refused without `--post-delivery`, and the last two are refused on a preview. `--delivery-segment` is refused with `--post-delivery`, and so is `status --cycle-id` without it. Nothing is silently ignored. |
| Native reads | The record's authenticated account reads PR metadata. The protected base is read into a disposable object store that is linked to the retained local objects and registered under the remote name the delivery recorded; the server is told which history is already retained, and a stalled transfer gives up. Preview therefore changes no index, worktree, ref (remote-tracking refs included), record, receipt or pointer. |

| Merged PR head against the delivered tip | Proof | Bounded reason when not verified |
|---|---|---|
| Equal | `unchanged_head`: the existing [exact-tree proof](external-merge-completion.md) of the native merge and of its inclusion in the protected target | — |
| One two-parent commit whose first parent is the tip | `base_refresh`: the second parent is contained in the base as it stood before landing and does not contain the tip; the clean merge, recomputed in disposable storage with Git's own recursive merge base, equals the refresh tree exactly; the landing is then verified as above | `landing_commit_does_not_land_pull_head`, `head_changed_beyond_base_refresh`, `refresh_base_is_not_pre_landing_target`, `refresh_is_not_a_clean_merge`, `refresh_changed_content` |
| Anything else | None; the native PR fact is reported separately | `delivered_tip_outside_pull_head`, `pull_head_not_retained` |

A two-parent landing commit must contain the pull request head. A squash landing
cannot, and is judged by its tree and by the native proof.

Do not infer proof from a matching PR number, final tree resemblance or ancestry
alone. If several cycles pushed substantive changes to one PR, the final cycle's
proof cannot supply the earlier cycles' correspondence. This release adds no
rebase or multi-refresh proof. An unverified or unavailable landing is reported
but carries no write authority.

## Evidence and owner review

Every deferred gate exception of the record yields one condition, in gate order.
Omitting a selector cannot hide one. A required gate that did not pass and has no
valid approved exception is refused outright; it is never left out.

| Condition | Identity in a selector | Attainable dispositions |
|---|---|---|
| Legacy prose: only the recorded `review_condition` text | `GATE:` plus the SHA-256 of that text | `owner_accepted` or `unverified`. Linked evidence is listed but never verifies prose. |
| Declared predicate: an optional `review` object on the exception, `{"schema_version": 1, "id", "predicate": {"gate", "authority", "result", "requirement"?}}` | `GATE:id` | `verified`, `not_met`, `owner_accepted` or `unverified` |

The predicate is the read contract of this release. Its `gate` must be the gate
holding the exception. Declaring one while a cycle is active belongs to the
prospective deferral work; this release has no writer for it and refuses a
malformed declaration.

The repeatable `--review-evidence GATE:CONDITION:SOURCE_CYCLE:EVIDENCE_ID` locates
one stored evidence item. It locates evidence; it is not evidence by itself. A
link is applicable only when every check below holds, and otherwise reports the
first one that fails. This reuses [trusted evidence bindings](workflow-evidence-bindings.md).

| Check of the linked evidence | Reason when it fails |
|---|---|
| The source record is readable and its cycle completed, in a cycle delivered to the same push URL (the remote name may differ) | `source_cycle_not_found`, `source_cycle_unreadable`, `source_repository_differs`, `source_cycle_not_completed` |
| The item is the gate's current evidence, and its envelope, sidecar digest and commit binding verify | `evidence_is_not_current_for_gate`, `evidence_or_binding_unavailable` |
| It is bound to the source delivery: a Gate Commit of that gate, or the head that cycle pushed | `evidence_not_bound_to_source_delivery` |
| It was recorded after the original completion | `evidence_predates_delivery` |
| Under an approved policy it carries a captured binding whose runtime acceptance is inside the declared maximum age; evidence from a cycle without a policy is accepted | `binding_unavailable`, `runtime_acceptance_stale` |
| It matches the predicate: gate and authority are equal, and a pinned requirement is covered | `authority_mismatch`, `requirement_not_covered` |

Different cycles may supply evidence for the same obligation. Linking one does
not transfer ownership of commits or give every gate in either cycle credit.

For judgment, a repeatable `--owner-review GATE:CONDITION` reports the recorded
owner's explicit decision to accept that particular condition. The preview shows
the condition, its evidence references and that decision separately from the
approval to append. The decision is caller-reported, like `--approval`; it is
attributed as such and is never an authenticated identity. Without that decision
the condition stays `unverified`. Unstructured narrative or a merged evidence
document can locate a review; neither is a substitute for a bound execution.
Machine review evaluates existing evidence; it does not re-execute historical
commands or contact a deployment target.

| Condition | Required disposition |
|---|---|
| Measurable predicate declared in approved authority before the observation | `verified` only when the trusted, applicable evidence satisfies the entire predicate. No second subjective sign-off is needed. |
| Trusted observation contradicts that predicate | `not_met`; keep the observation and original exception. |
| Explicit judgment of the named owner | `owner_accepted`, separately attributed and dated, only on an explicit decision tied to that condition and evidence. Record the existing consent route and its attribution limits. Recording approval alone is not acceptance; acceptance is not a passing execution. |
| Legacy prose, missing evidence, stale binding or incomplete scope | Keep `unverified` with a reason. Never infer a machine predicate from prose. A later owner review may accept judgment explicitly, but cannot turn missing machine proof into `verified`. |

For example, a publication readback and a zero-difference reconciliation are two
observations. A verified readback plus an interrupted reconciliation proves the
first only. Neither the publication nor an owner acknowledgement proves the
second. Assessment must enumerate the full set of original deferred conditions;
omitting a selector cannot hide an outstanding condition.

## Storage and recovery

Keep a versioned receipt in the existing Git-common-directory private custody
owner, outside the Cycle Record: `dbsctr/evidence/<cycle-id>/post-delivery/<NNNN>-<digest>.json`,
mode `0600` inside `0700` directories, written once. `NNNN` is the sequence.
A receipt holds `schema_version` 1, `kind` `post_delivery_receipt`, `sequence`,
`previous`, `digest`, `approval`, `original`, `landing`, `conditions`,
`observed_at` and `recorded_at`. `original` binds the cycle ID, SHA-256 of the
exact original record bytes, the recorded commits, the pull request and the
original gate results and exceptions. The digest covers `cycle_id`, `previous`,
`original`, `landing` and `conditions`; clocks and the sequence sit outside it.
Keep timestamps for the original completion, later observation and recording
separate. Public output uses opaque references and bounded reasons; no raw
credentials, logs or consumer identifiers in public Git.

`status --post-delivery` reads that chain offline and verifies each receipt
against its digest and predecessor. It never repeats a native check and never
presents a historical observation time as a fresh one. It reports which
conditions of the latest receipt are still outstanding and whether the current
record still matches each receipt. A temporary file left behind by an
interrupted writer was never linked into the chain and is ignored; any other
unexpected entry makes the chain invalid.

Preview returns a digest over stable inputs and proposed effects, including
the expected receipt predecessor, target observation and any explicit owner
decision. Fresh clocks alone must not invalidate a plan. Persist only after
exact approval and revalidation under the existing writer/evidence and target
locks. Reuse canonical digest encoding and atomic write-once custody. A retry
first checks for an already committed matching approved plan: return that same
receipt without creating a sibling. Otherwise recheck the predecessor before
appending. A later genuine observation appends another entry. Changed pins, record
bytes, evidence or predecessor require a fresh preview; conflicting custody or
an unknown version must refuse. Ordinary readers and writers keep their
historical semantics. No pointer is recreated or removed by this mode.

## Acceptance and gates

Use disposable public-CLI fixtures with synthetic records and native Git graphs;
mock the authenticated GitHub boundary. Exercise both ordinary and Initiative
draft delivery. Prove the three views independently, including:

- unchanged head; verified single base refresh; conflict resolution, extra edit,
  wrong PR/target, stale head and two substantive cycles sharing the PR;
- evidence from a later cycle with the right binding and with a mismatched or
  stale binding; an unmet predicate; explicit owner acceptance; partial and
  missing observations;
- no active pointer, an unrelated active cycle, concurrent append, interrupted
  write/retry, changed digest, corrupt custody and offline historical reading.
  Compare original bytes, refs and pointers before/after; no duplicated receipt,
  repaired history, push, merge, evidence replay or worktree removal.

`tests/test_post_delivery_receipts.py` exercises this matrix through the public
CLI with the GitHub transport synthetic. One focused test also serves its
binding payload and policy on purpose, to check the freshness rule itself.

The source-only draft PR uses the existing [CORE-SOURCE plan](../../../initiatives/dbsctr-workflow-convergence/CORE-SOURCE.plan.json).
All six kernel gates, Review/Integrate and Maintain/Retire are required.
Release (no package), Deploy and Operate (no managed activation) are not applicable
to the source slice. No gate result or exception is granted by this specification.
Maintenance owns schema compatibility, replay and historical readability, including
after rollback to a reader unaware of the extension. Installed qualification and
any real consumer write require a separately approved rollout.

## Visual Evidence

| Concern | Canonical evidence and review question |
|---|---|
| Boundary, schema and data/trust | Required: **The three questions**, the selection and proof tables in **CLI and proof**, the condition and evidence-check tables in **Evidence and owner review**, and **Storage and recovery** identify the separate owners, the original record, the receipt chain and the evidence references. Which source can establish each fact, and which reason is reported when it cannot? |
| Interaction and state | Required: the transition table below shows when durable state can change and what uncertainty preserves. |
| Dependency/deployment | See the [Build handoff](../../../initiatives/dbsctr-workflow-convergence/BUILD-HANDOFF.md#post-delivery-receipts); source delivery precedes separately qualified activation. |
| Quantitative | Not applicable: there is no measured comparison or performance claim. |

| Input | Operation | Result |
|---|---|---|
| Completed draft record | Preview native delivery and selected evidence | Per-condition report and exact plan for a recordable observation; an unsupported or unavailable merge proof has no write authority |
| Approved preview, identities unchanged | Verify again and append | One immutable receipt; record, refs and pointers unchanged |
| Same append retried | Read and verify matching custody | Same receipt |
| New condition evidence, or changed plan input | Preview again | A new observation can follow the prior one; no replacement of prior evidence |
| Stored receipts | `status --post-delivery` | Verified chain, read offline; no native check is repeated |

**Text Equivalent:** The cycle owns the original delivery. Native Git and GitHub
prove what landed. Evidence and the named owner answer different review questions.
The helper previews their relationship, then records the approved observation once.
Later information can extend the chain without changing earlier conclusions.
Owner: lifecycle maintainer; update these tables with any change to receipt
identity, proof, authority or retry behavior.
