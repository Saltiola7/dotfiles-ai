# Digest-bound effective Initiative authority amendment

## Status, intent and boundaries

Approved narrow prerequisite **source repair**, pending Build launch and validation;
not an installed command, live amendment, replacement cycle or gate pass.
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
never bulk staging. Existing evidence path-set checks stay unchanged. Record this
checkpoint through existing gate/commit evidence and an amendment-owned projection
of its commit ID and validated closure identity, not a second commit engine.
Completion must revalidate the effective closure at HEAD, as must final-push
readiness; a historical checkpoint alone does not permit drift. Subsequent material
normative edits require fresh Discovery/amendment. Editorial remediation requires
explicit existing scope authority and recorded exact validation of the resulting
closure; no general editorial exemption from completion checks. Original
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

Original `initiative`, `initiative_approval`, `discovery_import`, IDs, baseline,
commits, original approvals and evidence history are immutable. Material amendment
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
reopening. No broad receipt-equality shortcut: changed record bytes/chain block
stale replay. An exclusively persisted preimage without replacement is recoverable
only under the same exact bound state and approval. Lost reply must be reconciled
from durable evidence before any different effect is attempted.

## Behavior and validation acceptance

| Given | When | Required result |
|---|---|---|
| Registered native cycle with failed evidence and changed committed authority | Fresh receipt, preflight and exact consent are applied | Append one amendment; preserve registration/import/failures; required gates pending; status/resume use validated effective authority. |
| Same receipt/digest and exact verified postimage after lost reply | Retry | `already_applied`; no duplicate or repeated gate invalidation. |
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
blocks completion, and editorial remediation needs explicit scope/exact validation.
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

## Visual Evidence

Review question: which authority changes, in what order, without losing history?
Scope: this amendment only; accessible tables above are editable visual sources.

| Concern | Decision / source table |
|---|---|
| Boundary | required: ownership/transfer table below |
| Interaction | required: ordered transition table below |
| State | required: ordered transition table below |
| Data/trust | required: ownership/transfer table below |
| Schema | not_applicable: exact entry shape and persistent-chain prose are canonical; no duplicate schema diagram |
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
| Drift, malformed chain, terminal or wrong pointer | Any admission/recheck | Block and retain evidence; no replacement |

**Text Equivalent:** Discovery supplies committed same-repository authority to a
private preflight. Exact operator consent permits a locked, durable preimage then
one private-record append; original registration and Git remain untouched.
Validated readers resolve the full chain; required gates lose current evidence
and exceptions without erasing failures/history. Preimage ledger IDs cannot
dispose reopened gates; new execution is required even at unchanged HEAD. The
immutable envelope and separate deterministic outcome avoid recursive hashes.
Exact retry does nothing; drift or terminal state blocks. Build imports
docs only later through an ordinary recorded Gate Commit establishing the full
closure; completion/final push revalidate it at HEAD. Source merge, separately
approved installation and exact real-cycle amendment precede retirement recovery.
Canonical source: this contract and manifest; owner: lifecycle Discovery primary;
change trigger: any represented interface, state, ownership, trust or dependency
change, updated together in the same PR.
