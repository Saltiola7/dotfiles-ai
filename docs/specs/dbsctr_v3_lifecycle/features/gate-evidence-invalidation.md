# Evidence Rerun Invalidation (PY-02)

## Scope and Engineering Profile

Owner and bounded context: lifecycle maintainer, `dbsctr_v3_lifecycle`.
Engineering Profile: [existing profile](../PROFILE.md); its defaults remain
unchanged. Applicable module: Python. Risk override: **elevated**, because this
repair changes shared gate-disposal and completion decisions. Proposed Build
delivery is a source-only feature branch and draft pull request into `main`.
Managed installation, consumer qualification, merge and live-cycle recovery are
separate operations. Discovery does not authorize those operations.

This is a single-context repair, not a new Initiative or a new lifecycle
controller. The existing CLI, gate order, record schemas and authority owners
remain the public interface. No new Product Intent artifact is needed: this
slice corrects an existing internal-tool contract and adds no user journey.

This repair addresses the contradiction observed in source revision `3a3cd85`.
The context README and CHANGELOG remain the durable specification and outcome
artifacts; actual gate results, launch authority, source evidence and delivery
state belong to the private Cycle Record. Source implementation does not imply
managed installation or recovery of existing live records.

## Problem and desired outcome

`record-evidence` replaces the current result, evidence reference and exception
of the selected required gate. The earlier implementation, unlike `set-gate`,
omitted downstream invalidation when that replacement changed the gate from
disposed to undisposed. Both commands now use the shared transition policy.

For example, domain and behavior can pass at one HEAD; a domain rerun can fail
and then recover at that same HEAD while behavior retains its earlier passed
result. Current completion checks validate current gate state and evidence
bindings; they cannot reconstruct the omitted invalidation from HEAD freshness.
The repair must make the earlier failure reopen dependent passed gates before
the failed result is saved. Later recovery cannot silently restore those gates.
This finding does not establish an automatic PR merge bypass.

Success means both evidence recording and manual result replacement obey one
consistent transition policy while preserving each command's admission and I/O
responsibilities. Existing subprocess execution, redaction, sidecars, locks,
profile checks, approval requirements and serialization remain outside the pure
policy boundary.

## Terms and invariants

- **Disposed:** a not-applicable gate, a passed gate, or a failed/unavailable
  gate with an existing approved exception, under the current record rules.
- **Reopening transition:** a selected gate is disposed before replacement and
  undisposed after its new result is applied and its old exception removed.
- **Dependent success:** a gate later in canonical gate order whose applicability
  is `required` and whose current result is `passed`.
- **Historical evidence:** existing envelopes and sidecar contents retained for
  provenance, distinct from a gate's current evidence reference.

Capture the selected gate's prior disposition before removing its exception.
The trigger depends on disposition, not just a change in result text. An
exception-backed failed gate rerun as failed loses its disposition even though
the result string is unchanged.

For every reopening transition, each dependent success becomes `pending` and
loses its current evidence and exception references. Historical envelopes,
sidecars, recorded commits and artifact reviews remain intact. Increment
`gate_reopen_count` once for each gate actually changed from passed to pending.
Already pending gates do not increment the counter again.

The selected gate retains its newly executed result and evidence. Existing
failure-counter rules remain unchanged: increment `gate_failure_count` when a
new failed/unavailable result replaces a result outside that pair; increment
`remediation_round_count` when passed replaces failed/unavailable. In particular,
removing an exception from a repeated failed result does not invent another
failure count, but can reopen dependent successes.

Initialize the existing metric defaults before reopening can increment a
counter. Records without a metric map retain the established zero defaults;
this does not relax record validation or migrate historical schemas.

Preserve the existing invalidation population. Later not-applicable, pending,
failed and unavailable gates remain unchanged; this includes later failed or
unavailable gates with approved exceptions. This slice does not broaden exception
revocation policy. Passing a later gate still requires disposed predecessors.

## Behavior and state evidence

| Before selected gate | Replacement after old exception removal | Required downstream result |
|---|---|---|
| Passed | Failed or unavailable | Later required passed gates reopen |
| Failed/unavailable with approved exception | Failed or unavailable, without renewed approval | Later required passed gates reopen |
| Passed | Passed | No reopening |
| Failed/unavailable with approved exception | Passed | No reopening |
| Pending or failed/unavailable without exception | Failed or unavailable | No additional reopening |
| Failed/unavailable without exception | Passed, with disposed predecessors | No automatic restoration of later pending gates |

**Text Equivalent:** A transition from disposed to undisposed reopens only later
required passed gates. A transition that stays disposed or stays undisposed does
not reopen them. Recovering the selected gate never revives invalidated later
evidence. Canonical source: the terms and invariants above and the existing
`disposed`/`invalidate_later` policy. Owner: lifecycle maintainer. Update trigger:
changes to disposition, gate order, exception handling or invalidation policy.

### Scenarios

- Given domain and behavior passed at the same HEAD, when domain evidence is
  rerun and fails, then domain retains its new failed evidence and behavior
  becomes pending without a current evidence reference; both historical
  envelopes remain available.
- Given the preceding state, when domain passes again without changing HEAD,
  then behavior remains pending and completion refuses until every required
  reopened gate is freshly disposed under the existing rules.
- Given an earlier failed or unavailable gate with approved exception and later
  required passed gates, when the earlier gate is rerun as failed or unavailable,
  then its old exception disappears and the later passed gates reopen.
- Given a repeated failed rerun after downstream gates are already pending,
  when the result remains undisposed, then no gate is reopened twice and no
  extra reopen count is recorded.
- Given later not-applicable or exception-backed failed/unavailable gates,
  when an earlier gate reopens, then those later dispositions remain unchanged.
- Given a passed-to-passed rerun with disposed predecessors, when its new
  evidence replaces the old reference, then later passed gates remain passed.

## Boundaries and interaction

| Owner | Responsibility | Preserved constraint |
|---|---|---|
| CLI admission and evidence executor | Validate the active record, applicable gate, source/profile authority and literal subprocess outcome | Existing locks, predecessor checks, sanitization and sidecar ownership remain |
| Pure gate-transition policy | Apply result/reference replacement, exception removal, downstream invalidation and existing counters | No filesystem, subprocess, provider or completion calls |
| Record writer and completion validators | Persist the coherent result and evaluate current disposal and source binding | Existing private serialization and completion/delivery checks remain authoritative |

| Order | Interaction | Required outcome |
|---|---|---|
| 1 | Admit the existing command and obtain its outcome through current paths | Rejected admission does not partially mutate gate state |
| 2 | Capture prior result and disposition before replacement | Exception-backed disposition is observable |
| 3 | Replace current result/reference and remove selected gate's old exception | The new outcome is current; history remains retained |
| 4 | Apply existing downstream invalidation and counter rules | Record is coherent before persistence |
| 5 | Persist through the existing writer | No new store, schema, journal or registry |
| 6 | Later remediation and completion use current gates | Stale downstream evidence cannot satisfy completion merely by matching HEAD |

**Text Equivalent:** Admission and execution remain CLI-owned. Pure transition
policy receives the admitted state and outcome, updates only the existing gate
and metric data, and returns control to the existing writer. Completion consumes
that updated state through its current authority checks. Canonical source: this
section and the invariants. Owner: lifecycle maintainer. Update trigger: command
ownership, transition order or persistence-boundary changes.

Historical envelopes and sidecars stay in their current private stores. No
private record, output, credentials, source paths or runtime identities are
copied into shared specifications. Source documents contain only the portable
contract and synthetic test cases.

### Internal policy interface

The standalone helper owns one internal interface:

```python
def apply_gate_result(
    record: dict, gate_name: str, result: str, evidence: str | None = None
) -> None:
    ...
```

The caller has already admitted the command, validated its result/evidence and
checked any predecessor requirement. The policy mutates the existing record in
place; it does not repeat admission, execute evidence or persist data. Supplying
an evidence ID replaces the selected gate's current reference. Without an ID,
pending clears that reference and other results preserve existing manual-command
behavior. Both callers retain their existing validation and writer boundaries.
No public import surface, package or serialized type is introduced.

## Compatibility, non-goals and recovery

- `record-evidence` continues to support schemas 3/4/5/6. Preserve supported
  manual-transition behavior for schema 1/2 and schema-less historical records;
  do not change old readers or migrate records implicitly.
- Preserve CLI arguments, stdout evidence IDs, result classifications, JSON
  shapes, current exception approvals, evidence history and counter meanings.
- Share only the small policy needed by `record-evidence` and `set-gate` after
  characterization. Applicability, amendments, authority validation and command
  dispatch stay under their existing owners; no broad helper/package rewrite.
- No dependency, checker, Python floor, async, deployment or tool migration.
  The current standalone helper delivery contract remains unchanged.
- No automatic repair of already affected records. Current gate state does not
  reliably identify missing historical invalidation. For an independently
  identified active record, operator-directed reopening and fresh evidence use
  existing commands and approvals; this Discovery performs no such operation.
- A future source rollback follows the existing reviewed Git/distribution path.
  It must not restore stale gate snapshots, reverse accumulated metrics, delete
  evidence or silently re-pass gates already reopened by corrected behavior.

## Validation strategy and capability accounting

Build first adds a regression that fails on unchanged source, then repairs the
transition and performs a bounded extraction after affected behavior passes.
Use the current schema-5 harness in `tests/test_dbsctrctl.py` and the ready
schema-6 fixture in `tests/test_dbsctr_forgejo_completion.py`. Exercise historical
policy compatibility through the pure boundary and retain the existing schema-3
read/admission-refusal tests. Do not bypass workspace-adoption requirements to
make historical CLI mutation executable.

| Case | Acceptance evidence |
|---|---|
| Passed earlier gate reruns failed/unavailable | Exactly later required passed gates become pending; current links cleared |
| Exception-backed earlier failure reruns failed/unavailable | Prior disposition captured before exception removal; same reopening population |
| Same-HEAD remediation | Earlier gate passes; later pending gates stay pending; completion still refuses |
| Fresh downstream reruns | Existing predecessor rules permit progress and completion after every required gate is disposed |
| History and mixed gate states | Old envelopes and sidecar bytes remain; later not-applicable and exception-backed failure states unchanged |
| Repeated failure and pass-to-pass | No double reopening; preserved failure/remediation counter rules |
| Cross-command policy | Evidence and manual replacements produce equivalent state/counter effects for equivalent admitted transitions |
| Legacy and authority boundaries | Existing schema readers, redaction, literal argv, locks, profile binding and no-network local completion regressions remain passing |

Finite generated pytest cases may vary valid gate maps, result/exception
combinations and affected positions against an independent small transition
model. No new property-testing library is required. The focused scope is gate
state and completion, not full-repository test or typing coverage.

Project authorities remain `pytest`, Python compilation, Git fixed-commit
inspection and publication/instruction contracts. There is no configured Python
checker in the root project; this slice does not select one or claim typing
coverage. That capability gap is explicit and does not become an invented
checker pass or a new gate. Retain Python `>=3.12` and the existing CI matrix.

Planned Build commands include `uv run --group test pytest
tests/test_dbsctrctl.py tests/test_dbsctr_forgejo_completion.py -q`, Python
compilation of the affected helper, existing amendment tests if the shared
transition call graph changes, and the configured publication/instruction check
from `.github/workflows/test.yml`. Full-suite CI remains the integration
authority. Discovery's documentation checks establish artifact integrity only;
they do not prove the implementation defect fixed or installed behavior changed.

## Applicability plan and delivery

[PY-02 applicability plan](../PY-02.plan.json) names the existing committed
Engineering Profile and all eleven gates. Build verifies the profile/base
freshness and persists the JSON under ignored `.dbsctr/plans/` using the normal
registration flow. No profile identity, launch approval or Cycle Record is
fabricated by Discovery. Unmerged Discovery authority remains retained for the
ordinary supported import/delivery route; do not publish a preliminary docs PR
or force an ahead/dirty checkout through registration.

| Gate | Applicability | Candidate result | Reason or required evidence |
|---|---|---|---|
| Domain | required | pending | Existing disposition, history and completion invariants |
| Behavior | required | pending | Same-HEAD failure/recovery and exception scenarios |
| Spec | required | pending | Bounded pure-policy interface and command ownership |
| Contract | required | pending | Population, counters, compatibility and admission |
| Test Driven Implementation | required | pending | Failing regression, repair and affected suite |
| Refactor | required | pending | Shared policy after characterized behavior passes |
| Review/Integrate | required | pending | Independent review, current-base scope and native CI |
| Release | not_applicable | not_run | Source-only draft delivery publishes no standalone release artifact |
| Deploy | not_applicable | not_run | No managed helper installation or runtime activation in this slice |
| Operate | not_applicable | not_run | No live cycle execution or service operation in this slice |
| Maintain/Retire | required | pending | Compatibility and evidence-preserving recovery review |

No Gate Exception is selected. Actual results and evidence belong to the Build
Cycle Record. Remaining risks are legacy/manual transition regressions, accidental
exception-policy expansion, changed counters and unknown already affected active
records. The bounded contract and validation matrix address the first three;
retrospective live-record recovery remains explicitly separate.

Own the helper's result-transition paths and their focused tests together.
Bounded read-only review is parallel-safe; simultaneous
writers to gate transitions, those tests or this feature must serialize. The
adjacent gate-aware continuous-validation proposal does not own formal gate
mutation; reconcile shared README edits before integration. This contract grants
no new launch, deployment or live-record recovery authority.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: owner/responsibility table in Boundaries and interaction |
| Interaction | required: ordered interaction table in Boundaries and interaction |
| State | required: transition table in Behavior and state evidence |
| Data/trust | not_applicable: evidence ownership and private-store retention remain unchanged and are stated explicitly above |
| Schema | not_applicable: existing gate/evidence/metric shapes and version readers remain unchanged |
| Dependency/deployment | not_applicable: no dependency, packaging or runtime topology change |
| Quantitative | not_applicable: this contract makes no performance comparison or forecast |

Required tables have adjacent Text Equivalents, source, owner and change trigger.
Their prose and tables must change together when the represented contract changes.
