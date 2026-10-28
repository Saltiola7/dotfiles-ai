# Digest-bound effective Initiative authority amendment

## Status, intent and boundaries

Approved narrow prerequisite **source repair**; normative reconciliation is pending
primary validation. The registered source cycle remains retained `readiness_reopened`
under its prior receipt. No supported live authority-adoption route is currently
qualified; these prospective refinements authorize neither current implementation
under changed authority nor fresh launch approval, replacement cycle or gate pass.
INT-077..080 in the workflow-convergence manifest own this scope. Reuse the
existing lifecycle CLI, record validators, locks, receipts and approval machinery;
no second lifecycle engine or self-amending bootstrap.

An existing ACTIVE native-owned schema 3/4/5/6 cycle with an Initiative receipt
may explicitly adopt newly committed same-repository Discovery authority for the
same Initiative/context/slice. Original registration and import remain historical
truth. Status, readers and ordinary resume resolve effective authority only after
validating the complete amendment chain. Ordinary begin/resume still requires an
exact effective-receipt match; changed receipts never silently amend a cycle.

## Interface and consent

Proposed preflight (placeholders, not an executable instruction):

```text
dbsctrctl initiative-amend --cycle-id ID --initiative-manifest REL \
  --initiative-slice ID --initiative-source PATH --initiative-digest SHA \
  --expected-plan-digest SHA --plan PATH --reason TEXT --preflight --json
```

Apply uses the same selection, replacing `--preflight` with
`--expected-launch-digest SHA --approval interactive|agent-confirmed`.
Default approval is interactive. The operator's exact terminal text is
`AMEND ID SHA`, with the selected cycle ID and approved launch digest substituted.
Agents never synthesize that input. Agent-confirmed records an assertion of exact
chat consent, not authenticated operator identity. Shell permission, source-plan
approval and general continuation are not live-amendment consent.

Preflight writes only the full local private plan/evidence, not the Cycle Record
or Git. Hosted output is the bounded schema-1 result:
`{schema_version,cycle_id,status,state_digest,reasons,next_action}`.
In preflight, `state_digest` equals the approval launch digest so the bounded
result is actionable. Apply/replay returns that same approved digest; invalid
selection without a trustworthy digest returns null. Reasons/next_action are bounded classified codes,
not raw errors, host paths, selected private text or credentials. A private reason
is retained exactly in approval/amendment evidence, not echoed to hosted output.

Statuses are exactly `preflight`, `applied`, `already_applied`, `blocked` and
`recovery_required`. Exit 0 accompanies the first three, exit 1 `blocked`, and
exit 75 `recovery_required` (durable outcome/custody needs reconciliation).
Status JSON may add only a sanitized amendment summary
`{schema_version:1,count,effective_receipt_digest,latest_launch_digest}`. Preserve
existing original public-compatible fields; never add the exact new reason,
private preimage/envelope locators or raw envelope to hosted output. Internal
full-record readers remain private and validate more than this optional summary.

The launch digest binds selection, exact reason, receipt, previous effective
authority, applicability plan and delivery identity, private record bytes,
committed source and selected document blobs/modes, current native-owned checkout,
branch, HEAD, index and dirty-file inventory/content/index digests. Receipt and
dependency validation must be fresh and Build-owned. Source membership must be
proven by native same-repository Git custody, not a portable docs path pattern.
No lazy/promisor fetching: unavailable objects block locally.

## Admission and preservation

Require the exact existing active pointer, native ownership and original checkout.
Reject completed, finalizing, retired, unadopted legacy or unknown-schema records;
wrong repository/context/slice/Initiative; identity, delivery target or mode changes;
unsafe/symlink evidence; dirty selected documents; malformed chains or records.
The source authority must be committed and its selected working/index documents
must match its exact approved blobs/modes. Selected paths in the owned cycle
checkout must be clean against that checkout's bound HEAD/index; they need not
already contain the new authority, since this operation never imports it.
Unrelated dirty files are allowed but
their inventory, contents and index are bound and left untouched. Unreadable or
unsupported state blocks rather than weakening drift checks.

Risk, Engineering Profile and gate applicability stay unchanged in this release.
Risk increases or applicability-plan changes use existing explicit routes first,
then require a fresh amendment preflight and approval against the resulting state.
The supplied plan must match `--expected-plan-digest` and the recorded effective
plan. This command cannot create an exception or change a delivery promise.

No network, credential access, Git refs/index/file/checkout mutation, document
import or commit occurs during amendment. Only private amendment plan/preimage
evidence and the existing Cycle Record may be written. Exact approved documents
are imported later by a separately validated ordinary Gate Commit; no auto-import
or auto-commit, baseline reset or replacement discovery_import. Gate validation
must distinguish original-import verification from the later effective-authority
document closure without relaxing commit/final-push lineage.

Completion requires one recorded ordinary Gate Commit whose resulting tree
establishes the entire approved selected `{path,blob,mode}` closure. Files already
identical need not be staged; changed selected files use exact explicit paths,
never bulk staging. Existing evidence path-set checks stay unchanged. Record the
checkpoint through existing gate/commit evidence and this optional top-level
ordered array in supported record schemas:

```text
"initiative_authority_checkpoints": [
  {"schema_version":1,"launch_digest":SHA256,"commit":GIT_OID,"closure_sha256":SHA256}
]
```

Each entry has exactly those four fields. `closure_sha256` is SHA-256 of canonical
JSON UTF-8 of the full selected sorted-by-path `{path,blob,mode}` array from the
approved immutable envelope, using the existing canonical digest helper. Permit
at most one entry per amendment launch digest, referencing an existing validated
amendment and ordered by amendment order. Absence is valid for unamended records;
an amended record may lack a checkpoint while work is pending, but cannot complete
without its latest amendment's checkpoint.

An ordinary recorded Gate Commit with nonempty gates and existing current fresh
evidence/path-set validation appends the projection when its resulting tree first
establishes the latest full closure. Keep `commits` entries' existing `id`/`gates`
shape. Do not create a checkpoint during `initiative-amend`. Subsequent amendment
preimages/outcomes retain earlier checkpoint entries; each newer amendment needs
its own qualifying checkpoint. The projection changes no immutable amendment
entry, envelope or outcome and adds no second commit engine.

Historical readers validate the referenced commit is recorded, its exact tree
closure, custody and lineage using existing safe local no-fetch Git access.
Completion and final-push readiness additionally require the latest checkpoint
to be an ancestor of HEAD and the full exact effective closure at HEAD. Coincidentally
matching HEAD documents without a qualifying recorded Gate Commit cannot complete.

In this v1 operation, ANY change to the effective selected closure's path/blob/mode,
including editorial change, needs a fresh committed Discovery receipt, preflight
and exact amendment approval before the replacement closure can satisfy completion.
General bounded editorial remediation remains applicable outside this exact selected
closure; it cannot override these bytes or create a parallel exemption/mutable
envelope. This is prospective tightening, not authority to change an already-approved
active cycle. Original
`discovery_import` remains unchanged and independently validated.

## Persistent chain, atomicity and replay

Add an optional ordered `initiative_amendments` array to supported record schemas;
absence preserves old-record behavior without implicit schema migration. A version
1 entry has exactly these fields (uppercase values are type placeholders):

```text
{
  "schema_version": 1,
  "previous_effective_receipt_digest": SHA256,
  "receipt": VALIDATED_NEW_RECEIPT,
  "before_record_sha256": SHA256,
  "preimage_locator": OWNED_PRIVATE_RELATIVE_LOCATOR,
  "launch_digest": SHA256,
  "reason": EXACT_TEXT,
  "approval_method": "interactive_cli" | "agent_confirmed",
  "approved_at": FIXED_UTC_TIMESTAMP,
  "plan_digest": UNCHANGED_APPLICABILITY_PLAN_SHA256,
  "envelope_sha256": SHA256,
  "envelope_locator": OWNED_PRIVATE_RELATIVE_LOCATOR
}
```

`before` means the immediate pre-amendment record bytes, including earlier
amendments, not registration bytes. The hash-bound owned private version-1 envelope
retains the full approved private launch plan, exact selected `{path,blob,mode}`
closure, source commit, before-record hash/preimage locator, receipt, exact reason,
unchanged applicability-plan digest, consent method and fixed consent timestamp.
Use the existing private evidence owner and safe regular-file/custody validation;
no supplied arbitrary public path becomes an evidence owner. Freeze consent time
once after consent and durably retain it before replacement; retries never
fabricate a new time or native actor attribution.

Avoid a self-referential hash: the immutable envelope does **not** contain the
replacement hash. After hashing that envelope, construct deterministic replacement
bytes from the verified preimage, fixed entry and required gate invalidation.
Before replacement, exclusively persist a hash-bound owned private version-1
outcome descriptor holding envelope identity, exact expected replacement bytes and
their SHA-256. It is separate from the entry/envelope and cannot change their
identity. Fsync envelope, preimage and descriptor before record replacement;
replay validates their custody, bytes and cross-references. Missing or inconsistent
durable outcome evidence yields `recovery_required`, never a guessed success.

The first previous digest refers
to original `initiative`; subsequent entries refer to the preceding effective
receipt. Original receipt is never overwritten. Readers validate every entry,
receipt, ordered link and preimage/hash/custody before resolving the latest receipt.
Unknown entry versions or inconsistent chains block; no fallback to an earlier
apparently valid authority. Helper-observed time is not native actor attribution.

The amendment cannot overwrite original `initiative`, `initiative_approval`,
`discovery_import`, registration identity, baseline, recorded commit prefix or
ledger history. This does not freeze normal lifecycle progress. Material amendment
reopens **all required gates to pending**, removing their current evidence AND
exception fields. Retain the evidence ledger, failed evidence, exception history and
prior gate outcomes in recoverable history/preimage. No exception disposes a gate
under new authority without renewed explicit scoped approval. Applicability and
non-applicable gate dispositions remain unchanged. Amendment itself proves no gate.

Evidence IDs present in the latest amendment preimage ledger cannot dispose any
reopened gate. Newly executed evidence is required under the new authority even
if HEAD has not changed. Compare IDs against that preimage internally; add no
per-evidence schema fields. Enforce this in set-gate, Gate Commit, completion and
final-push readiness, not only the interactive gate setter. Previous results and
exceptions remain recoverable in the preimage/history, not active dispositions.

Ordinary readers validate every historical preimage, envelope and deterministic
outcome, and immutable amendment prefixes; they do NOT require current record bytes
to equal the last outcome. Current records and each next amendment's immediate
preimage preserve original registration identity/receipt/approval/import/baseline,
the immutable amendment prefix, recorded commit prefix and ledger history. Existing
validated commands may append evidence/commits, bind evidence to its Gate Commit,
update gate/exception/artifact/metrics state and perform otherwise authorized
profile/risk/plan changes and terminal transitions. The amendment itself still
cannot perform those separate changes. Validate normal intrinsic record, evidence
and commit invariants and checkpoint retention; raw mutable JSON is not proof of
authenticated writer identity or complete event history. No new event engine is
introduced to make that unsupported claim.

Under existing deterministic cycle/checkout locks: freshly revalidate all bound
state and terminal guards, exclusively persist and fsync an original-byte preimage,
then durably atomically replace the record with the appended entry and gate
invalidation. Fsync the containing directories; never overwrite an existing
preimage. Failures retain recovery evidence and report uncertainty, not success.
Git is untouched, so no multi-resource transaction is required. This is updated-
client serialization, not fencing of arbitrary processes; old/incompatible writers
must be kept out operationally. Updated terminal checks remain mandatory.

Retry of the exact same approved digest/new receipt, with verified preimage and
exact expected postimage, returns `already_applied` without another entry or gate
reopening. Exact current-postimage equality governs `initiative-amend` replay
admission ONLY, not ordinary historical reading. Legitimate progress after apply
makes that old replay `blocked`, with no gate reopening; it does not invalidate
ordinary readers or prohibit a second fresh amendment bound to immediate current
bytes. No broad receipt-equality shortcut: changed record bytes/chain block stale
replay. An exclusively persisted preimage without replacement is recoverable
only under the same exact bound state and approval. Lost reply must be reconciled
from durable evidence before any different effect is attempted.

## Behavior and validation acceptance

| Given | When | Required result |
|---|---|---|
| Registered native cycle with failed evidence and changed committed authority | Fresh receipt, preflight and exact consent are applied | Append one amendment; preserve registration/import/failures; required gates pending; status/resume use validated effective authority. |
| Same receipt/digest and exact verified postimage after lost reply | Retry | `already_applied`; no duplicate or repeated gate invalidation. |
| Valid evidence/commit bindings, gate/artifact/metrics or authorized plan/terminal progress after apply | Ordinary read/status/resume | Validate historical outcomes and preserved prefixes/intrinsic invariants, not current-postimage equality; valid progress remains readable. |
| Legitimate record progress after apply | Retry old approved amendment | `blocked`; do not reopen gates or reject valid progress as a corrupt historical outcome. |
| ACTIVE progressed record | Second fresh amendment with fresh exact approval | Bind immediate current bytes; preserve historical chain/checkpoints/commits/ledger, require new evidence and its own checkpoint. |
| No checkpoint, duplicate/out-of-order/foreign checkpoint or mismatched recorded commit/tree | Read/complete as applicable | Invalid projection blocks reading; missing latest qualifying checkpoint blocks completion even if HEAD docs match. |
| Latest qualifying checkpoint and matching HEAD closure | Completion | Validate recorded nonempty-gate commit, exact closure, custody/lineage and ancestry plus ordinary gates. |
| Editorial-only selected blob/mode/path change without fresh amendment | Completion/final-push readiness | Refuse replacement closure; no editorial exemption. |
| Stale consent, dirty selected docs, changed unrelated dirt/index, pointer or chain | Preflight/apply/resume | Block; no Git mutation, record rewrite or approval reuse. |
| Two updated writers or terminal transition | Locked recheck | Serialize and reject stale/terminal operation; no claimed universal process fencing. |
| Old supported record with no amendments | Read or continue | Existing receipt and behavior remain valid; no migration or invented amendment. |
| Schema 6 local-only cycle | Amend then validate completion/replay | No network/credentials or publication authority; immutable local completion replay remains intact. |

Exercise public CLI registration -> failed evidence -> amendment -> status ->
resume, not helper-only success. Include schema 5 and schema 6 fixtures and native
schema 3/4 compatibility; concurrency, stale approvals, interrupted preimage/replace,
lost reply, full-chain tampering, unsafe evidence and denied/no-mutation cases.
Test exact entry/envelope/outcome hashes, immediate-before semantics across two
amendments, fixed timestamps and deterministic replay without hash recursion;
assert status/exit mapping and sanitized summaries. Test old evidence rejection
through gate setter, Gate Commit, completion and final push even at unchanged
HEAD; test cleared current exceptions with preserved history. Verify one Gate
Commit establishes the full closure including already-identical files, HEAD drift
blocks completion, and selected editorial changes require a fresh amendment.
Exercise normal evidence binding, commit/gate/artifact/metrics updates, separately
authorized plan changes and terminal reads after amendment without exact-postimage
reader rejection. Then retry stale consent (blocked, no reopening) and apply a
second fresh amendment against immediate current bytes. Verify immutable-prefix
and ledger-history protection without claiming authenticated mutation history.
Test exact checkpoint fields, canonical sorted closure digest, one per launch,
ordering/retention across amendments, no checkpoint on amendment itself, recorded
nonempty-gate commit/tree/ancestry validation, missing checkpoint despite matching
HEAD, no-fetch refusal and editorial replacement-closure refusal.
Assert original failed evidence survives, old records still read, ordinary begin/
resume exact-match refusal remains, final-push lineage is unchanged, and local-only
completion/replay performs no network. Source-only fixtures do not qualify a live
amendment or installed-client compatibility.

## Build handoff and gates

Reuse [PROFILE.md](../PROFILE.md) unchanged: critical risk, Python/Security,
feature-branch source PR. Use the existing CORE-SOURCE plan: every kernel gate,
Review/Integrate and Maintain/Retire required; Release/Deploy/Operate not applicable
for source-only delivery under its existing reasons. All results pending, no
exceptions. No product-intent/profile duplication.

Implementation closure: `dot_local/bin/executable_dbsctrctl`, new
`tests/test_initiative_authority_amendment.py`; existing
`tests/test_initiative_cli_approval.py`, `tests/test_initiative_local_launch.py`,
`tests/test_native_workspace_records.py`, `tests/test_worktrunk_registration.py`,
`tests/test_dbsctr_forgejo_identity.py`, `tests/test_dbsctr_forgejo_completion.py`
as necessary for the same contract, plus lifecycle README/CHANGELOG completion
notes. No helper configuration or unrelated source changes. Primary must verify
existing test filenames before launch; a missing filename is not authority to add
a different implementation owner silently.

The `cycle-authority-amendment` slice supplies the mechanism only, depending on
`safety-inventory`. It must not bootstrap by amending its own launch authority.
Keep the blocked original retirement cycle and all failures/import/approval
history intact. Separate approved merged installation and exact real-cycle
amendment follow source delivery; separate native permission repair is independent.
Only then can fresh retirement readiness/approval proceed. Manifest `ready` means
settled specification, not verified publication, receipt, preflight or deployment.
The retained manifest label is not fresh readiness validation of this reconciliation
and cannot supersede the registered source cycle's prior receipt/reopened state.

## Visual Evidence

Review question: which authority changes, in what order, without losing history?
Scope: this amendment only; accessible tables above are editable visual sources.

| Concern | Decision / source table |
|---|---|
| Boundary | required: ownership/transfer table below |
| Interaction | required: ordered transition table below |
| State | required: ordered transition table below |
| Data/trust | required: ownership/transfer table below |
| Schema | not_applicable: exact amendment/checkpoint shapes and chain prose are canonical; no duplicate schema diagram |
| Dependency/deployment | required: ownership/transfer table below |
| Quantitative | not_applicable: no measured comparison or performance claim |

| Source / owner | Direction and guard | Sink / owner |
|---|---|---|
| Committed Discovery authority / Discovery | Same-repository exact blobs/modes + fresh dependency-satisfied receipt | Private preflight / lifecycle CLI |
| Operator / consent | Exact launch digest + reason; never actor authentication | Locked private record append / lifecycle CLI |
| Immediate pre-amendment record / lifecycle CLI | Exclusive fsynced preimage, envelope and separate deterministic outcome descriptor; immutable original fields | Ordered effective chain / validated readers |
| Effective committed docs / Discovery | Later separately validated ordinary Gate Commit only | Existing checkout / Build |
| Merged mechanism / source owner | Separate installation approval, then exact live-amendment approval | Retained blocked cycle / existing primary |

| Observed state | Trigger / guard | Next state / effects |
|---|---|---|
| ACTIVE exact owned pointer | Preflight, supported schema and stable unchanged plan | ACTIVE unchanged; private bound plan only |
| ACTIVE approved preimage | Locked exact recheck + consent + durable preimage | ACTIVE with appended effective authority; required gates pending |
| Exact applied postimage | Same digest/receipt retry and verified preimage | `already_applied`, no mutation |
| Valid progressed record | Ordinary reader validates historical outcomes/prefixes and intrinsic invariants | Progress remains readable; no exact current-postimage requirement |
| Valid progressed ACTIVE record | Fresh second amendment approval bound to immediate current bytes | Append new authority; retain checkpoint history, require own checkpoint |
| Latest closure established by recorded nonempty-gate commit | Existing fresh evidence/path-set validation | Append exact checkpoint projection; completion also checks ancestor and HEAD closure |
| Progressed record | Old amendment replay | `blocked`, no reopening |
| Drift, malformed chain, terminal or wrong pointer | Amendment admission/recheck | Block and retain evidence; no replacement |

**Text Equivalent:** Discovery supplies committed same-repository authority to a
private preflight. Exact operator consent permits a locked, durable preimage then
one private-record append; original registration and Git remain untouched.
Validated readers resolve the full chain; required gates lose current evidence
and exceptions without erasing failures/history. Preimage ledger IDs cannot
dispose reopened gates; new execution is required even at unchanged HEAD. The
immutable envelope and separate deterministic outcome avoid recursive hashes.
Exact-postimage equality is replay-only: legitimate progress remains readable
under historical/prefix and intrinsic invariant checks, but old replay is blocked.
A fresh second amendment binds current bytes and retains checkpoint history.
Build imports docs only later through an ordinary nonempty-gate recorded Gate
Commit establishing full closure and appending the exact launch/commit/closure
checkpoint. Each amendment needs its own checkpoint; completion/final push check
its ancestry and exact HEAD closure. Even editorial changes to selected bytes need
fresh Discovery/receipt/preflight/exact amendment consent. Source merge, separately
approved installation and exact real-cycle amendment precede retirement recovery.
Canonical source: this contract and manifest; owner: lifecycle Discovery primary;
change trigger: any represented interface, state, ownership, trust or dependency
change, updated together in the same PR.
