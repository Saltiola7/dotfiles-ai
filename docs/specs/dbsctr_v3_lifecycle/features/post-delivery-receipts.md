# Post-delivery receipts for completed draft PR cycles

Owner: lifecycle maintainer. [Engineering Profile](../PROFILE.md). Critical risk;
Python and Security. This is the source contract for the `post-delivery-receipts`
slice of [workflow convergence](../../../initiatives/dbsctr-workflow-convergence/README.md).
It specifies a capability; it does not record an implementation or a live recovery.

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

## Proposed CLI and proof

Extend the existing completion handler with an explicit `--post-delivery` mode. The
unflagged command keeps its existing meaning and refusals. Example interface, for Build:

```text
dbsctrctl complete-external --post-delivery --cycle-id ID --pr-number N \
  --expected-head MERGED_PR_HEAD --expected-merge MERGE [review selectors] --preview
dbsctrctl complete-external --post-delivery <same selectors> \
  --expected-receipt-digest SHA256 --approval agent-confirmed
dbsctrctl status --post-delivery --cycle-id ID --json
```

Select a completed GitHub `draft_pr` cycle (supported record schemas 3/4/5;
ordinary or Initiative) by exact ID in the same Git common directory. Verify
the recorded PR, repository, feature and target branches. Derive the **delivered
tip** from that cycle's verified Final Push and retained source, not the current
checkout, the initial registration base or the published prefix of a follow-up.
The caller's expected head selects the PR head **at merge**, not the delivered tip.
Missing original proof gives `unavailable`; a current branch with the right name
cannot supply it. Local-only records remain offline and ineligible for this route.

1. **Unchanged head:** the delivered tip equals the authenticated merged PR head.
   Reuse the existing [exact-tree proof](external-merge-completion.md) to verify
   the native merge result and its inclusion in the selected protected target.
2. **One base-only refresh:** the merged PR head differs from the tip by precisely
   one two-parent commit. Its first parent must be the delivered tip; its second
   must be verified pre-landing target history, not merely reachable *after*
   landing. Recompute the clean merge from those parents with trusted Git
   settings in disposable storage. Require its exact tree, including modes, to
   equal the refresh tree, then independently verify the actual landing as in
   case 1. Conflicts, extra edits, unknown parents or insufficient target history
   leave source correspondence unverified.
3. **Other changes:** report the native PR fact separately if known, and a
   bounded reason for unsupported source correspondence. Do not infer proof from
   a matching PR number, final tree resemblance or ancestry alone. In particular,
   if several cycles pushed substantive changes to one PR, the final cycle's
   proof cannot supply the earlier cycles' missing correspondence. This first
   release does not add a new rebase or multi-refresh proof.

Use the recorded account and repository and the existing native object, target
and privacy checks. Preview does not change the index, worktree, refs, record,
receipts or pointers. Use disposable storage for read-only remote verification
if needed. Offline status reads verified stored receipts; it never presents their
historical observation time as a fresh native check.

## Evidence and owner review

The optional repeatable selector `--review-evidence GATE:CONDITION:SOURCE_CYCLE:EVIDENCE_ID`
locates an existing receipt; it is not evidence. A condition ID selects the exact
approved condition within that gate. An old unstructured review condition can be
identified by its gate and the digest of its recorded text, not split into inferred
predicates. Check the selected evidence's custody, content
digest, producing repository/cycle, covered requirement and revision, and source
or runtime target and freshness as applicable. Reuse [trusted evidence
bindings](workflow-evidence-bindings.md). Different cycles may supply evidence
for the same obligation; linking one does not transfer ownership of commits or
give every gate in either cycle credit.

For judgment, a repeatable `--owner-review GATE:CONDITION` selects the recorded
owner's explicit decision to accept that particular condition. The preview must
show the condition, its evidence references and that decision separately from
the approval to append. Without that owner's decision, report `unverified`.
Unstructured narrative or a merged evidence document can locate a review; neither
is a substitute for a bound execution. Machine review evaluates existing evidence;
it does not re-execute historical commands or contact a deployment target.

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
owner, outside the Cycle Record. Bind each entry to the cycle ID, SHA-256 of
the exact original record bytes, previous receipt digest (null for the first),
published/merged identities, proof kind, and the evidence references, condition
dispositions and attribution above. Keep timestamps for the original completion,
later observation and recording separate. Public output uses opaque references
and bounded reasons; no raw credentials, logs or consumer identifiers in public Git.

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
| Boundary, schema and data/trust | Required: **The three questions** and **Storage and recovery** identify the separate owners, original record, receipt chain and evidence references. Which source can establish each fact? |
| Interaction and state | Required: the transition table below shows when durable state can change and what uncertainty preserves. |
| Dependency/deployment | See the [Build handoff](../../../initiatives/dbsctr-workflow-convergence/BUILD-HANDOFF.md#post-delivery-receipts); source delivery precedes separately qualified activation. |
| Quantitative | Not applicable: there is no measured comparison or performance claim. |

| Input | Operation | Result |
|---|---|---|
| Completed draft record | Preview native delivery and selected evidence | Per-condition report and exact plan for a recordable observation; an unsupported or unavailable merge proof has no write authority |
| Approved preview, identities unchanged | Verify again and append | One immutable receipt; original completion unchanged |
| Same append retried | Read and verify matching custody | Same receipt |
| New condition evidence, or changed plan input | Preview again | A new observation can follow the prior one; no replacement of prior evidence |

**Text Equivalent:** The cycle owns the original delivery. Native Git and GitHub
prove what landed. Evidence and the named owner answer different review questions.
The helper previews their relationship, then records the approved observation once.
Later information can extend the chain without changing earlier conclusions.
Owner: lifecycle maintainer; update these tables with any change to receipt
identity, proof, authority or retry behavior.
