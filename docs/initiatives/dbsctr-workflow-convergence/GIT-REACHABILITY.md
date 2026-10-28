# Ordinary Git reachability — captured Discovery

## Intent and readiness boundary

Tracked deletions and ordinary same-repository branch integration are normal Git
behavior the lifecycle must support. INT-081/082 capture this requirement in the
existing lifecycle context. `ordinary-git-reachability` is **captured, non-ready,
Discovery-owned**, depending only on `safety-inventory`. No implementation closure,
launch approval or deployed behavior is established here.

This is separate from the ready `cycle-authority-amendment` source repair and
does not broaden it or the original retirement remedy. Including this note in
that slice's complete changed-document import closure carries captured Discovery
evidence only, not source-edit authority or permission to implement this slice.
There is no dependency from the ready amendment slice to this unfinished work.

## Bounded source evidence

Primary reports source inspection and disposable local Git probes, with no live
cycle or remote touched. These demonstrate source-level gaps, not a verified
cause of any live cycle remaining active. No private cycle/session/account or
consumer repository facts belong in this note.

| Source boundary | Reported observation | Bounded conclusion |
|---|---|---|
| CLI `safe_paths`, lines 17393–17410; `gate-commit`, 17414–17460 | A missing tracked path passes while its index entry remains; `evidence_path_blobs` returns `path: None`. After `git add -u` stages deletion, `git ls-files --error-unmatch` fails and the path is rejected as nonexistent. | Staged deletion needs explicit tracked-absence handling, not permission for arbitrary missing paths. Unstaged absence has a partial representation, not proven end-to-end support. |
| Ordinary final push, lines 18821–18827 | Full `rev-list baseline..HEAD` is compared exactly with `record.commits`. Recording only a no-ff merge commit does not account for incoming side-parent commits. | Ordinary side-branch integration needs explicit reviewed incoming-closure accounting; do not bypass the pre-cycle safeguard. |
| Existing `validate_draft_reconciliation` | Approved-default reconciliation already has a special validated path. | Preserve it; do not claim all merges are broken or replace its authority. |

Canonical source is `dot_local/bin/executable_dbsctrctl`; line numbers are
inspection locators, not stable identities. Primary must bind fresh source/Git
evidence before readiness. No live target diagnosis, remediation or gate result
is asserted by these reports.

## Captured requirements and constraints

**INT-081:** Ordinary staged and unstaged tracked deletions must work through
evidence collection, Gate Commit, readers and completion with explicit absence
semantics. Establish tracking from authoritative Git state rather than treating
any missing path as valid. Reject never-tracked, unsafe and secret paths. Rename
delete/add behavior must remain reviewable without silently broadening path sets.
The exact absence representation and compatibility rules remain Discovery work.

**INT-082:** Ordinary same-repository branch integration must be explicitly
reviewable and recordable with exact incoming commit closure, resulting tree and
required gates. Keep cycle-owned commits distinct from imported commits. Existing
approved-default reconciliation stays supported. This does not authorize every
commit ahead of baseline, inferred patch equivalence or passed gates for an
unvalidated merge.

Retain original baseline/registration/import and failed evidence. Do not rewrite
history, auto-close live cycles, bypass DVC preservation or remote consent, or
weaken unrelated/pre-cycle commit safeguards. Use existing lifecycle owners,
not a second merge, identity or delivery engine. Gate success requires actual
required validation of the resulting tree, never merge presence alone.

## Unresolved decisions — block readiness

1. **Authority/import interface:** How are exact incoming commit identities,
   closure, parents, scope and resulting tree selected, reviewed, consent-bound
   and recorded? Which existing record/evidence owner distinguishes imported
   from cycle-owned commits without granting arbitrary ahead history?
2. **Already-recorded merge recovery:** How may an existing merge reconcile
   missing incoming-closure accounting without retroactively asserting validation,
   rewriting history or losing failures? Define stale state, denied approval,
   interrupted apply/retry and retained uncertain outcomes.
3. **Deletion representation:** Settle authoritative tracking/absence proof for
   staged and unstaged deletion, compatible readers, rename delete/add, evidence
   freshness/path sets and completion. Absence is not a secret/unsafe-path exemption.

Discovery must settle these choices and bounded implementation ownership,
risk/applicability and approval/recovery contracts before promoting the slice.
No command name or schema repair is invented to preempt that decision.

## Proposed validation (not executed here)

- Disposable real no-ff side-branch public-CLI journey with explicitly approved
  foreign-to-cycle incoming commit closure and validated resulting tree/gates.
- Existing approved-default reconciliation regression.
- Staged/unstaged tracked deletion through evidence, commit, read and completion;
  rename delete/add and historical reading.
- Reject never-tracked, unsafe/secret paths and unapproved imports; retain
  unrelated/pre-cycle safeguards and independent DVC/remote consent.
- Fail/retry and already-recorded-merge recovery retain original failed evidence;
  distinguish validated success from blocked/uncertain continuation.

## Visual Evidence

Review question: which source gaps remain outside the ready repair?
Scope: captured evidence and ownership, not an approved mutation flow.

| Concern | Decision |
|---|---|
| Boundary | required: source-boundary table above |
| Interaction | not_applicable: approval/recovery protocol remains unresolved |
| State | not_applicable: only captured/non-ready status is established |
| Data/trust | not_applicable: no new transfer/schema selected; existing privacy constraints remain |
| Schema | not_applicable: deletion/import representations remain unresolved |
| Dependency/deployment | not_applicable: single dependency explicit in prose; no rollout selected |
| Quantitative | not_applicable: no measured comparison |

**Text Equivalent:** Path validation partially accepts unstaged tracked absence
but rejects staged deletion. Ordinary final-push exact ancestry accounting omits
side-parent commits when only the merge is recorded. Approved-default reconciliation
already has a supported special path. Discovery must settle absence proof, import
authority and recorded-merge recovery separately; no live cause, implementation
or gate pass follows. Source: primary-reported inspection/disposable probes above;
owner: lifecycle Discovery primary; update with source findings, scope, authority,
approval or recovery choices, and bind fresh evidence before readiness.
