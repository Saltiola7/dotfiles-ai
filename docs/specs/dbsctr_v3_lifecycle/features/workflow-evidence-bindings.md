# Trusted evidence bindings for completion reconciliation

Owner: lifecycle maintainer. Profile: [../PROFILE.md](../PROFILE.md).
Parent contract: [completion reconciliation](workflow-completion-reconciliation.md).
Risk: critical; Python and Security. This approved Discovery refinement specifies
source behavior to implement and qualify, not installed capability.

## Authority and compatibility

Extend the existing applicability-plan owner with optional `evidence_policy` v1.
It is part of the exact plan bytes approved at Initiative launch. Neither a
branch-authored file nor `record-evidence --path` independently declares complete
validation inputs. That option continues to select Gate Commit output paths.
No new policy service, credential store, telemetry database or lifecycle engine.

Existing plans, envelope bytes and schemas 3/4/5/6 retain their historical meaning.
No implicit enrollment or retrofit of missing bindings. An old source envelope may
still satisfy its original exact-source rule; it cannot acquire cross-HEAD reuse
or runtime-identity credit by inference. Missing scope/identity is unavailable for
that new proof and has a supported enrollment/revalidation path below.

The plan contains these optional declarations; examples are synthetic and omit
unrelated required gate-applicability entries:

```json
{
  "evidence_policy": {
    "schema_version": 1,
    "requirements": {
      "EXAMPLE-001": {"revision": "1", "depends_on": [], "gates": ["contract", "test_driven_implementation"]}
    },
    "gates": {
      "test_driven_implementation": {
        "authority": "project-tests",
        "argv": ["python3", "scripts/validate_source.py"],
        "inputs": ["src", "tests", "scripts/validate_source.py", "pyproject.toml", "uv.lock"],
        "environment": ["PROJECT_TEST_MODE"],
        "toolchain_paths": ["uv.lock"],
        "scope_complete": true
      }
    }
  }
}
```

All objects reject unknown versions, duplicate/unknown fields, duplicate IDs and
invalid references. Requirement IDs must exactly match effective Initiative
requirements, or the existing approved non-Initiative requirement authority;
non-Initiative enrollment without such an authority remains unavailable. Every
requirement maps to at least one required gate. Dependency edges reference that
same population and must be acyclic. Gate names are existing gate IDs. Policies
may omit a gate's input declaration, but that gate gets no cross-source reuse.
Runtime gates require the runtime declaration below before new runtime proof.

Each requirement has exactly `revision`, `depends_on` and `gates`. Revision is a
nonempty, at-most-128-byte UTF-8 semantic revision selected by approved Discovery;
it changes when that requirement's acceptance, dependency or gate mapping changes.
An editorial authority revision may explicitly preserve it. An unapproved branch
claim cannot establish semantic equivalence. Revision is not inferred from prose
similarity. The policy amendment's explicit correspondence binds this judgment.

Coverage is deterministic: gate G's binding covers exactly the sorted requirement
IDs whose `gates` includes G. No command/caller-supplied coverage list is admitted.
A requirement is satisfied only when **every** mapped required gate and every
prerequisite requirement is disposed under current authority. Passing one of
several mapped gates is partial coverage. An approved valid gate exception yields
an explicit exception disposition, not passing execution or a new binding. These
rules are conjunctive; no implicit any-of or waived dependency exists.

Each declared gate requires exact `authority`, literal argv, nonempty `inputs`,
`environment`, `toolchain_paths` and `scope_complete: true`. Empty environment or
toolchain-path lists are allowed only as explicit complete declarations. The
resolved executable is always captured independently. Commands/arguments contain
no credentials; existing secret controls still reject unsafe use. Native process
permissions remain authoritative. No shell interpolation or command discovery
from output. A declaration is a reviewed dependency claim, not proof of execution.
`toolchain_paths` selects exact repository-relative configuration files or private
absolute installed-tool files, including relevant subprocess binaries. Resolve and
capture their regular-file targets, mode and content before/after execution and
at applicability checking. Reject secret/special files. Retain external locations
only as keyed private identities; their bytes are never copied into evidence.
Completeness includes interpreters and subprocess tools, not merely a lockfile
whose declared environment might differ from the installed one.

Bound policies to 1024 requirements, 4096 dependency edges, the existing gate
inventory, 256 paths and 128 environment keys per gate, 64 argv entries and one
MiB serialized policy. Exceeding a bound is typed unavailable with a partition
action, never truncated acceptance. These are work bounds, not coverage exemptions.

## Normalized source and environment inputs

Input paths are canonical repository-relative regular files, directories or
explicit tracked absences, not globs, pathspec expressions, absolute paths or
paths containing traversal/control components. Reject symlink ancestors, selected
symlinks, submodule traversal, secret/ignored paths and unsupported encodings.
Explicit tracked absence binds predecessor blob and mode using the deletion
contract. A never-tracked missing path is not a valid empty dependency.

Expand selected directories to their complete tracked and nonignored untracked
regular-file population. Include additions, removals, content and mode; a new file
inside a declared directory changes its identity. Bound traversal and bytes, and
return unavailable when the complete population cannot be established. Ignore
rules themselves are relevant configuration and must remain bound. Merely checking
the files that changed or the files already in an older list is insufficient.

Capture selected policy identity, current Engineering Profile and requirement
authority, exact argv, resolved executable bytes and declared toolchain/configuration
files, normalized source input identities and relevant inherited environment.
Capture inputs before and after the authority runs; drift prevents acceptance of
a stable-input binding even when the child exits zero. Preserve the execution and
return a classified unavailable binding; never manufacture a passing replacement.

Environment values, missing-value distinctions and private executable locations
stay in existing private custody, never public reports. Use a per-cycle private
random HMAC key for environment/other sensitive-value comparisons, retained by the
same custody owner with restrictive permissions. Do not publish an unsalted digest
of low-entropy secret values. No raw secret value is retained. Key loss makes
comparisons unavailable; it does not authorize reconstruction or a match claim.
Only declared relevant environment keys affect equivalence; undeclared dependency
completeness is the approved project's responsibility, not an agent inference.

Full policy and authority-receipt digests are provenance, **not** global equivalence
keys. Compare each gate's own declaration, direct requirement coverage and the
semantic revisions/dependency/mapped-gate edges of its prerequisite closure.
Changes outside that population do not invalidate its binding. Actual changed
inputs or declaration changes first affect their mapped requirements; propagate
through reverse dependency edges before deciding retained/rerun dispositions.
Unknown scope propagates conservatively through that same affected closure.

## Machine capture and immutable custody

Keep the `record-evidence GATE --authority NAME -- PROGRAM ...` interface. When an
effective approved declaration matches the gate, authority and exact argv, the
helper captures v1 bindings automatically; it does not accept a caller-authored
binding JSON argument. Mismatched invocation is not equivalent execution and gets
no reuse credit. Preserve existing result and exception behavior.

Add optional `evidence.bindings` keyed by original evidence ID. Each value is an
exact `{schema_version: 1, sha256: DIGEST}` reference to a helper-owned immutable
binding payload under the existing private evidence owner. Do not add or change
fields on historical envelopes. Payloads bind cycle/evidence IDs, effective policy,
authority revision, covered requirement IDs, command/toolchain, normalized inputs,
environment and, where applicable, runtime identity. The helper owns timestamps.

Write binding payload and required comparison-key custody before saving its record
reference. Use existing locks, checked descriptors, immutable writes, bounded reads
and atomic save. Exact interrupted retries reuse matching payloads; conflicting
bytes, missing payloads, unsupported versions and mismatched references fail closed.
Original runs, failures and exception history remain readable. Status/report output
shows disposition/reason and opaque reference only, never payload/private paths.
Historical validation verifies custody without executing commands or using network.

### Binding payload v1 and comparison encoding

Payloads have exactly these fields; nullable fields remain present:

| Field | Type / meaning |
|---|---|
| `schema_version`, `cycle_id`, `evidence_id`, `gate` | Integer 1; original record/envelope identity and existing gate ID |
| `policy_digest`, `authority_receipt_digest` | Lowercase SHA-256 of full approved policy and effective receipt, for provenance |
| `coverage` | Sorted array of exact `{id, revision}` objects derived from policy, never reported by the child |
| `gate_policy_digest` | Canonical digest of this gate declaration, coverage and prerequisite requirement closure |
| `command_digest` | Canonical digest of actual exact argv, checked against declared argv |
| `inputs` | Sorted exact `{path, mode, sha256, predecessor}` entries described below |
| `toolchain` | Sorted exact `{selection_digest, location_hmac, mode, sha256}` entries including resolved executable |
| `environment` | Exact `{algorithm: "hmac-sha256", key_id, values_hmac}`; opaque per-cycle key ID and keyed comparison of selected name/value-or-missing pairs |
| `observed_at` | Helper-owned UTC execution-finish timestamp, equal to referenced envelope's finish timestamp |
| `runtime` | Null for source-only capture; otherwise exact `{identity, validated_at}` with runtime JSON above and helper-owned validation-finish timestamp |

Input file `mode` is `100644` or `100755`, `sha256` hashes actual unfiltered file
bytes and `predecessor` is null. A tracked absence has null mode/sha256 and exact
predecessor `{commit, blob, mode}` from the validated predecessor tree. Git object
IDs retain repository object width; content digests use lowercase SHA-256. Empty
directory populations still bind their declared roots through the gate policy,
and fresh expansion must include all new files. Toolchain modes are regular-file
modes. `selection_digest` hashes the exact selected toolchain path or executable
selector; locations use HMAC rather than exposing private paths.

Canonical value encoding is UTF-8 JSON with sorted object keys, ASCII escaping,
`,`/`:` separators, no insignificant whitespace or trailing newline, and exact
integer/string/null types; this reuses the existing lifecycle canonical digest
authority. Set-like arrays above are sorted and unique; argv remains ordered.
The binding reference hashes the exact canonical payload bytes. Reject noncanonical
or structurally inconsistent payloads rather than normalizing hostile custody.
Environment and location HMAC inputs use separate fixed v1 domain labels plus
cycle ID and canonical values, preventing cross-purpose/cycle substitution.
Labels are exactly UTF-8 `DBSCTR:environment:v1` and `DBSCTR:location:v1`; encode
`label + NUL + cycle_id + NUL + canonical_value_bytes`. Key ID is an independent
random 32-character lowercase hexadecimal identifier; HMAC values are lowercase
64-character hexadecimal strings. Environment canonical values are sorted exact
`{name, present, value}` entries, with boolean presence and null for an absent
value, preserving absent versus present-empty. Reject unsupported environment
encoding instead of silently dropping keys. Location canonical value is the
resolved absolute regular-file path string. Tool selections canonically encode
`{kind: "executable", value: ARGV_ZERO}` or
`{kind: "toolchain_path", value: DECLARED_PATH}` before selection hashing.

`gate_policy_digest` projects exactly `{gate, declaration, coverage, prerequisites}`:
coverage is the direct array above; prerequisites is the sorted union of transitive
prerequisite requirement records `{id, revision, depends_on, gates}`. It excludes
the full policy/receipt digest and unrelated requirements/gates. Source-input,
toolchain and environment equivalence are compared independently. A global policy
edit alone can therefore neither erase unaffected credit nor approve changed
inputs. New applicability decisions retain both old and new provenance identities.

## Runtime capture and current identity

Required Release/Deploy/Operate evidence that depends on a running target uses a
gate declaration with this additional `runtime` object:

```json
{
  "probe_argv": ["python3", "scripts/observe_runtime.py"],
  "probe_timeout_seconds": 20,
  "max_age_seconds": 3600
}
```

`max_age_seconds` is a required positive project-selected freshness policy, not a
universal default; it is bounded to a signed 32-bit integer. Timeout is 1–60
seconds. Probe implementation/configuration and its relevant toolchain/environment
belong to the declared inputs. The approved owner must establish that the probe
is read-only. Policy selection grants no otherwise missing native permission,
credential access, deployment/apply authority or provider expenditure.

For the selected runtime validation command, the helper creates a fresh private
output file and supplies its path only to that child as
`DBSCTR_EVIDENCE_OUTPUT`. It overrides any caller-provided value. No preseeded path
or JSON is admitted. After successful execution, read one bounded UTF-8 JSON object:

```json
{
  "schema_version": 1,
  "artifact_digest": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "configuration_digest": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "target_digest": "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc",
  "environment_digest": "dddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd"
}
```

Digests are lowercase SHA-256 identities derived by the project-owned execution
authority from actual deployed artifact/configuration, target and runtime
environment, not supplied by the operator as asserted success. Capture is bounded
to 64 KiB, exact fields/version and no duplicate keys. Validate secure regular-file
ownership, single-link custody, no symlink ancestors and stable descriptor reads;
remove the temporary output through its existing owner.
Do not retain raw provider metadata or grant CI/approval credit from these fields.
The project authority remains accountable for semantic correctness of observations.

Before retaining runtime evidence at completion, structural checks must pass.
Run the declared lightweight probe under native permissions and the same fresh
private-output protocol. Its identities must match captured runtime identities;
its successful execution is a current observation, not a new deployment or full
acceptance-test execution. The original acceptance timestamp must still satisfy
`max_age_seconds`; reject missing, future or unparsable timestamps. A changed target,
artifact, configuration or environment, expired acceptance, failed probe or expired
credentials requires supported revalidation or a typed prerequisite, not a waiver.

Deduplicate identical probes within one invocation by policy/command/input/environment
identity. Bound the whole probe stage to 60 seconds and 32 distinct probes; stop
before launching excess work and return unavailable/partition, never partial success.
No deterministic permission retry, credential bypass or implied live execution
during source qualification. Local-only completion stays offline and never starts
a runtime probe. A selection requiring one is typed unavailable for reconciliation;
the historical exact-source local-completion rules remain unchanged.

## Reconciliation, amendment and legacy recovery

Retained means the original execution's policy, requirement coverage, declared
inputs, command/toolchain/environment and applicable runtime identity/freshness
remain equivalent. A new applicability decision binds that original evidence ID
to the effective authority/current source; it never changes the original run.
Changed requirements reopen their transitive dependants and mapped gates. Missing
scope, new requirements, changed command/policy/toolchain/environment or unknown
dependency closure conservatively require revalidation. Removed requirements keep
historical superseded dispositions and require approved authority correspondence.

For active legacy cycles, extend existing `initiative-amend --plan ... --preflight`
with an explicitly versioned evidence-policy enrollment/revision. Exact receipt,
current bytes, unchanged required gate applicability/risk/delivery and policy bytes
participate in its digest-bound approval. A policy-only revision is permitted with
the same effective requirement authority. Retain original applicability plan and
all prior approvals; append policy revision custody. Ordinary `update-plan` or a
branch-file edit cannot replace trusted policy or silently relax input coverage.
Unsupported installed writers must report capability unavailable; no manual ledger
edit or self-bootstrap with unmerged source is a recovery route.

Enrollment alone grants no evidence credit. The supported next action is ordinary
`record-evidence` through the selected project authority to populate missing
bindings, followed by ordinary completion. Unknown legacy runtime metadata needs
one real bounded revalidation/capture; it must not become a permanent refusal with
no writer capable of establishing the missing proof. Existing exact-source source
gates retain their historical rules without being mislabeled as newly bound.

### Policy enrollment/revision custody

An initial plan policy is revision zero and retains its original launch approval.
For later enrollment/revision, extend the existing Initiative amendment entry with
schema version 3 and exactly one additional `evidence_policy_revision` field.
Its exact object is:

```json
{
  "schema_version": 1,
  "kind": "enroll",
  "previous_policy_digest": null,
  "policy_digest": "eeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
  "policy": {"schema_version": 1, "requirements": {}, "gates": {}},
  "requirement_dispositions": {"EXAMPLE-001": "unchanged"}
}
```

This shape example abbreviates the policy only: an actual empty requirement map
cannot satisfy a nonempty effective receipt. `kind` is `enroll` only if no prior
effective policy exists, with null previous digest; otherwise it is `revise` and
previous digest must equal the exact effective policy digest. New policy digest
must equal canonical policy bytes. The latest validated v3 amendment selects the
effective policy; otherwise the original plan policy, if any, remains effective.
No second policy-revision list or mutable policy pointer is added.

Correspondence covers the union of old and new authority requirement IDs exactly.
`added`/`superseded` mean present only in new/old authority; common IDs are
`unchanged` or `changed`. Known semantic revision/dependency/gate-mapping changes
cannot be labeled unchanged. Unknown legacy revision metadata never establishes
retained binding applicability, even when approved correspondence preserves intent.
An unchanged requirement may still need revalidation because its actual inputs,
gate declaration or prerequisites changed. No correspondence creates execution.

The existing amendment plan/envelope adds this exact revision object to its digest
projection. Approval binds cycle, immediate original-byte record digest, prior and
new effective authority receipts, old/new policy digests and correspondence, exact
plan bytes, profile/risk/required gate applicability/delivery, selected document
closure and native checkout/destination identities. Existing preimage/envelope/
outcome custody and interruption/replay rules remain authoritative. Historical
readers verify the policy/receipt chain and dispositions locally; they never probe
current runtime, replay commands or require the original checkout. Schemas 1/2
amendments retain their original semantics; no retrospective selective reset.

The writer must advertise support for plan evidence policy v1, binding payload v1
and amendment v3 before enrollment. Missing installed support is an activation
prerequisite, not permission to invoke unmerged source against a consumer. The
source's own authority-only amendment can still use its existing qualified v1/v2
route with unchanged applicability, without enrolling its pending new capability.

## Acceptance and validation

Use public CLI synthetic journeys for plan approval, policy-only active enrollment,
record-evidence capture, unchanged-scope cross-HEAD reuse, selective amendment
reopening, runtime capture/probe and completion. Prove that ignored/unrelated
changes do not cause an equivalent-input run to be repeated, while additions in a
declared directory and relevant blob/mode/config/environment changes do.

Include wrong/partial requirement coverage, cyclic dependencies, preseeded output,
foreign/symlink/hardlinked output, malformed/oversized/future observation, missing
key/payload, changed command/executable, undeclared legacy scope, expired freshness,
changed target, credential denial, offline reader, local-only refusal, interrupted
capture/save and conflicting custody. Count validation executions and probes in
fixtures; no projected whole-session savings. Existing historical readers and
failures retain meaning. Source qualification uses no live cloud/provider target.

## Visual Evidence

| Concern | Decision |
|---|---|
| Boundary | required: ownership table below |
| Interaction | required: capture/verification flow below |
| State | required: applicability transition table below |
| Data/trust | required: private capture flow below |
| Schema | required: policy, binding reference and runtime JSON above |
| Dependency/deployment | not_applicable: same three-context delivery DAG; no new service/deployment |
| Quantitative | not_applicable: work bounds and freshness policy are not performance claims |

| Owner | Authority / boundary |
|---|---|
| Discovery and approved plan | Complete requirements/dependencies, validation inputs and freshness policy |
| Existing project validator/probe | Actual execution and observed runtime identities, under native permissions |
| Lifecycle helper | Secure capture, immutable binding, affected applicability and bounded result |
| Distribution | Compatible installation and separately approved private consumer enrollment |

| Order | Data flow / trust decision |
|---|---|
| 1 | Approved exact plan and current source supply declared scope, not branch assertions |
| 2 | Helper captures before-inputs and provides fresh private output to executed authority |
| 3 | Stable after-inputs and successful result permit immutable private binding/reference |
| 4 | Structural completion proof permits at most one matching bounded runtime probe per identity |
| 5 | Equal inputs and valid observations permit retained applicability; missing/changed proof requests revalidation |

| Prior state | Observation | Disposition |
|---|---|---|
| Legacy/unbound | No trusted scope/runtime metadata | Unavailable for new reuse; enroll and revalidate through public CLI |
| Bound | Same approved scope and valid identities/freshness | Retained with new applicability decision |
| Bound | Relevant change or expired observation | Rerun required for affected closure |
| Any | Invalid custody/version or denied prerequisite | Blocked/unavailable; preserve work and original evidence |

**Text Equivalent:** Discovery/plan declares completeness; the project authority
executes and observes; the helper captures privately and decides applicability.
Only structural success permits bounded current runtime observation. Equal trusted
inputs allow retention, while missing or changed proof has a supported revalidation
route. No flow authorizes new external actions or cleanup. Canonical source/owner:
this contract and lifecycle maintainer; update with policy, capture, schema,
freshness, approval or recovery-interface changes.
