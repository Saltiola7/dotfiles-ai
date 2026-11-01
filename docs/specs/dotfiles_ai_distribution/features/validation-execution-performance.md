# Equivalent validation without duplicate execution

Status: specification ready; implementation pending delivery of
`lifecycle-performance-core`. Slice: `validation-execution-performance` in the
existing `dbsctr-cycle-speed` Initiative. Owner: distribution maintainers;
lifecycle owns the early-publication contract. Engineering Profile:
[../PROFILE.md](../PROFILE.md). Product Intent: [journey 12](../PRODUCT.md),
reviewable source with required quality evidence. Risk: elevated. Modules:
Python and Security. Delivery: source-only feature branch and draft pull request.

## Outcome and boundary

Remove repeated execution of already-required checks within the same hosted CI
job, preserving test coverage, failure behavior and early feedback. This is an
execution partition, not cross-command cached evidence or a new gate-admission
authority. Existing runtime/Worktrunk matrix, job names, triggers, cancellation,
permissions, dependencies and required status semantics remain unchanged.

The lifecycle performance slice supplies the common measurement protocol and
baseline procedure. This separate distribution slice owns hosted workflow edits.
No native harness, model, session, continuous-validation runner, adapter,
enrollment, local feedback or installed runtime is changed.

## Behavior and contracts

- Given the same source, test collection, toolchain, environment and CI lane
- When early publication/instruction and native compilation checks succeed
- Then the remaining test step executes every other required test identity
- And the union of executed identities equals the current required suite
- And tests intentionally required on different lanes still run on each lane.

- Given an early required check fails
- When the workflow evaluates subsequent steps and job conclusion
- Then current failure/stop behavior and required status remain unchanged
- And no absent execution is represented as a passing check.

- Given collection, selection, plugin, fixture or test-order changes could alter
  the required identity set or invalidate independent execution
- When equivalence cannot be established
- Then retain the original full execution and report the candidate rejected.

Preserve the early-publication contract in the existing lifecycle specification.
Never remove tests to satisfy performance targets, weaken assertions, waive
failures, skip a runtime lane, change security checks or accept stale evidence.
Do not reuse test results across jobs, commits or gate decisions. A test name is
not proof of current success; each partition must execute and pass independently.

## PY-09 retained-CI baseline precursor

The separate `python-ci-baseline` slice implements an opt-in analyzer of retained
CI evidence. It depends on `python-cli-baseline` for the shared version-1 evidence
contract. It does not implement the execution partition above, edit a workflow,
start a CI run or require performance-core delivery. The later optimization
slice requires both delivered performance core and this baseline precursor.

Distribution owns `tests/benchmarks/ci_performance.py`, synthetic `ci_*.json`
fixtures in `tests/benchmarks/fixtures/`, and `tests/test_ci_performance.py`.
The proposed interface is
`python tests/benchmarks/ci_performance.py --input PATH --output PATH`.
The accepted input is a version-1 envelope with an explicit list of at most
32 jobs, each containing job/step metadata, explicit bounded log-file references
and their digests. Limit the metadata envelope to 1 MiB before parsing.
Inputs are caller-selected existing job metadata and logs; the analyzer performs
no authentication, network request, workflow dispatch or source/test execution.
Raw inputs and outputs use the foundation's private storage contract. Published
examples use synthetic jobs, generic names and invented timestamps only.

Evidence identifies tested commit/tree, exact workflow and command identities,
runner image/toolchain, Python and Worktrunk versions, dependency-lock identity,
job/step start and finish, conclusion, and log/metadata provenance digests.
Queue, job, setup and test execution durations are separate. A job duration is
not Python test time. Unknown timestamps or command intervals are unavailable;
missing command intervals must not be estimated from output order. An observed
historical duration is descriptive evidence for that exact job, not a current
source pass or a repeatable machine benchmark.

Accept only consistent metadata/log bindings. Digest checks prove selected-byte
consistency, not provider authenticity. An internally consistent fabrication is
not detectable by an offline parser; mark input authenticity unverified unless
independently retained trusted verification is available under the existing CI
evidence owner. An attached external-verification assertion is not verification
performed by this tool. Unverified evidence may produce explicitly attributed
descriptive summaries; it cannot establish a current green check, trusted source
provenance or performance activation. Each job defaults to a distinct execution
cohort; matching runner image labels alone never justify pooling different jobs. Mark incomplete, cancelled,
truncated, mismatched or ambiguous records with explicit availability rather than
mixing them into a successful cohort. Never combine different source/workflow,
runtime/Worktrunk, runner or dependency identities. Retain each failure in the
cohort denominator. Apply the shared statistics only to comparable measured
attempts; a singleton may be reported as a singleton, with no comparative claim.

Keep explicit test collection/execution identities when retained evidence has
them. Counts alone cannot prove duplicate execution, unique-test coverage or
fixture equivalence. Without identities, retain `test_identity_coverage` as
unavailable and supply the later optimization slice's required collection plan.
This does not block a truthful duration-only baseline and cannot satisfy the
optimization's exact-coverage acceptance. Existing runtime/Worktrunk lanes,
early checks, job names and failure/stop behavior remain unchanged.

Bound input to at most 32 explicitly selected jobs, 32 MiB per log and 128 MiB
aggregate input. Stream bounded parsing; do not load an unrestricted log archive.
Default wall budget is 60 seconds. Refuse unsafe paths and oversized inputs before
analysis. Cancelled parsing records partial coverage and preserves original files;
there are no automatic retries or uploads. Limits may be lowered explicitly;
raising them requires a reviewed workload-contract change.

Acceptance: deterministic parsing/statistics over valid synthetic records;
refusal or explicit unavailability for contradictory identity/digest bindings,
missing timestamps,
cancellation, clock/order contradictions, malformed/oversized data, duplicate
records and incompatible cohorts. Include self-consistent fabricated records to
assert that authenticity remains unverified, not falsely authenticated.
The retained matching-tree CI evidence from
the Python audit is a provenance-qualified input candidate, not required public
fixture data and not fresh validation. No minimum CI speed improvement is a
baseline-tool acceptance condition.

The [distribution profile](../PROFILE.md) applies with Python and Security,
elevated risk and source-only draft delivery. Use existing affected pytest,
publication/instruction checks, Python compilation and configured CI. No package,
checker, workflow, runtime or protection change is selected. Kernel,
Review/Integrate and Maintain/Retire gates are required; Release, Deploy and
Operate are not applicable. The committed plan is
`docs/initiatives/dbsctr-cycle-speed/CI-BASELINE.plan.json`; required results stay
pending. Review README/CHANGELOG; record implementation only after completed
delivery. Source rollback removes the opt-in analyzer without changing any
required validation or deleting retained evidence. Distribution maintains parser
compatibility when retained CI metadata/log formats change.

## Implementation and validation

Writable source: `.github/workflows/test.yml` and affected workflow/lifecycle
contract tests. Documentation: this feature, distribution README/CHANGELOG,
relevant early-publication contract, and the existing Initiative artifacts.
Changes to `.github/continuous_validation.py` or continuous-validation runtime
are excluded; their checks are separate advisory executions, not duplicates in
this hosted job. Required dependencies and lockfiles remain unchanged.

Before implementation, collect the existing required suite and early-check
identities on the same fixed source. Use exact deselection or equivalent explicit
partitions only if their union and fixture behavior preserve coverage. Add
contract tests that catch missing identities, duplicate selection, renamed tests,
new tests and changed early-check ordering. Run the existing repository-selected
publication/instruction authorities and full CI, including supported-runtime
compatibility cadence. No new test tool is required.

Use the [shared performance protocol](../../dbsctr_v3_lifecycle/features/python-performance.md#profiling-and-benchmark-contract):
same source workload, runtime, tools, machine and cache condition; one warmup and
at least five alternating matched pairs; report mean, nearest-rank p50/p90,
sample counts, failures and unavailable attempts. Hosted queue time is separate
from command execution. Record test identity counts beside timing.

Acceptance requires identical required coverage and job failure behavior, zero
duplicate test executions caused by the targeted overlapping steps, and no new
test failures. Aim for at least 10 percent lower median execution time of the
affected overlapping checks without more than 5 percent repeatable p90 regression
in control workloads. Overall job savings may be smaller and must be reported
separately. If duplication removal cannot preserve test isolation or lacks a
repeatable gain, retain the baseline and document the rejected candidate.

## Gates and delivery

All Development Kernel gates, Review/Integrate and Maintain/Retire are required.
Release is not applicable because no independently published package is created.
Deploy and Operate are not applicable to the source-only draft: no installed
runtime or repository protection/permission configuration is changed. Candidate
CI execution remains required integration evidence. All required gate results
start pending; no exception is proposed. Fresh receipt and launch preflight
follow verified predecessor delivery; specification readiness does not promote
the captured slice automatically.

Rollback restores the prior workflow selection without changing required checks
or deleting evidence. Distribution maintains selection/fixture equivalence as
the suite grows. Residual risk: test order or plugin behavior may make apparently
identical partitions non-equivalent; preserve a conservative baseline fallback.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | not_applicable: distribution workflow ownership and lifecycle contract ownership are explicit |
| Interaction | required: ordered table below preserves early failure semantics |
| State | not_applicable: existing job result states are unchanged |
| Data/trust | not_applicable: no new evidence source, storage or trust boundary |
| Schema | not_applicable: no result or persistence schema change |
| Dependency/deployment | not_applicable: existing CI lanes and source-only delivery remain unchanged |
| Quantitative | not_applicable: candidate measurements do not yet exist; protocol supplies future comparison requirements |

| Order | Work | Condition to continue |
|---|---|---|
| 1 | Existing publication and instruction checks | Actual success |
| 2 | Existing native compilation check | Actual success |
| 3 | Remaining required test identities | Actual success for the same job/lane |
| 4 | Existing job conclusion | Every applicable step succeeded |

**Text Equivalent:** Early publication/instruction checks run before native
compilation and the remaining required tests. A failed required step retains its
existing stopping and job-failure behavior. Every applicable partition must
actually succeed. Canonical owner: distribution; update when workflow ordering
or required test selection changes.
