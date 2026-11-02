# Isolated snapshot performance baseline

Status: Discovery specification ready; source tooling and measurements pending.
Owner: continuous-validation maintainer. Existing context: `continuous_validation`.
Coordinator: `dbsctr-cycle-speed`, slice `python-snapshot-memory-baseline`.
Engineering Profile: [../PROFILE.md](../PROFILE.md). Modules: Python and Security.
Risk: elevated. Delivery: source-only draft pull request with opt-in synthetic
benchmark tooling; no installed runner, enrollment, worker or service changes.

## Problem, outcome and non-goals

Snapshot source bytes are capped, but that bound does not establish controller
peak memory or capture cost. The current implementation can retain whole Git
batch output, per-blob copies and fast-import payloads simultaneously. This is a
source-backed hypothesis, not a measured memory failure. Measure the actual
snapshot boundary under controlled synthetic inputs before selecting a rewrite.

Produce reusable local benchmark tooling and evidence compatible with the
[PY-09 foundation](../../dbsctr_v3_lifecycle/features/python-performance.md#py-09-measurement-only-foundation).
No production source optimization, new runtime/dependency/checker, enrollment,
Dagger/VM setup, provider/model call, live host profiling, private repository or
store input, automatic retention cleanup or gate-evidence admission is included.
DKS model-service work remains deferred under its existing retirement authority.

## Ownership and interface

| Owner | Artifact/control | Excluded authority |
|---|---|---|
| Lifecycle foundation | Common evidence, ingestion, cohort binding and statistics | No snapshot implementation or runtime admission |
| Continuous-validation benchmark | Synthetic Git generation, isolated capture invocation and scoped metrics | No enrollment, backend/check execution or production runner edits |
| Existing production context | Snapshot compatibility, private state and real resource/admission policy | Benchmark success confers no activation or gate authority |

The snapshot owner may add `tests/benchmarks/snapshot_performance.py`, synthetic
`snapshot_*.json` fixtures in `tests/benchmarks/fixtures/`, and
`tests/test_snapshot_performance.py`. The foundation owns
`tests/benchmarks/performance_evidence.py`; use its validated contract rather than
forking serialization/statistics or editing it concurrently. Production
`runner.py`, backend/feedback code, adapter protocol and managed files are outside
this source slice. The benchmark uses the current committed capture implementation
without changing its normal limits or production admission.

Proposed interface after Build:
`python tests/benchmarks/snapshot_performance.py --source-tree PATH --output PATH`.
Default smoke cases use 1 MiB and 16 MiB aggregate selected inputs. `--full`
selects the declared full cohort, including 64 MiB and a 240 MiB near-limit case.
Every report identifies the exact selected cohort; smoke never counts as full.
The source checkout must be clean, committed, unchanged and read-only.

Each fresh child imports the selected snapshot implementation and invokes only
its capture boundary against a disposable synthetic Git worktree and owned
private state directory. No runner request, enrollment, check execution, engine
or session transport is started. Use isolated HOME/XDG, Git configuration/hooks
and import state as specified by the foundation. Do not copy ignored runtime or
private files from the source checkout. The source text is trusted only under
its selected commit; incompatible capture interfaces fail explicitly.

## Workloads and measurement scopes

| Dimension | Required cases and recorded identity |
|---|---|
| Selected bytes | Aggregate live plus unique historical blob bytes at 1, 16, 64 and 240 MiB; remain below existing 256 MiB source limit |
| History | Exact base/ancestor/HEAD identities; unchanged reused blobs and changed historical blobs; fixed generator seed |
| Layout | Many bounded small files and fewer larger files, within existing inventory limits; benign excluded paths prove exclusion |
| Concurrency | One controller and two simultaneously released controllers on separate scratch worktrees/state directories |
| Correctness | Exact captured selected contents, deterministic normalized identities, expected filtered Git graph and excluded-input absence |
| Evidence | Parent-observed duration, controller CPU where available, raw OS peak RSS/unit and qualified byte conversion, plus separate Python allocation profile |

Generator construction must reconcile the true selected-byte accounting before
launch; do not treat file size multiplied by revision count as unique bytes.
Fixture IDs bind every dimension and the selected source. Repeated setup uses
identical logical content and history shape, not machine-specific commit times.
Timing excludes fixture generation but total-run bounds include it. Record setup
cost separately. The full cohort has one warmup and ten planned attempts per
cell, with availability and statistical semantics inherited from the foundation.

Measure controller peak RSS in each fresh child from a supported OS resource
backend, retaining raw units and the verified platform conversion. Unknown unit
or backend capability yields unavailable, not a guessed byte value. This is
controller-process memory; Git child memory, host/VM memory, combined concurrent
RSS and foreground responsiveness remain unavailable unless independently and
explicitly measured. Summing two process peaks does not establish simultaneous
aggregate peak. Report the two-controller cell's per-controller values and
parent-observed completion time with these limits.

Python `tracemalloc` measures traced Python allocations, not total RSS. Run it in
a separate attribution cohort; its overhead must not contaminate unprofiled
latency/RSS comparisons. Stdlib resource support differs by platform; the tool
must report its actual capability rather than infer qualification from import
success. Primary references: [Python allocation tracing](https://docs.python.org/3.12/library/tracemalloc.html)
and [OS resource interface](https://docs.python.org/3.12/library/resource.html).
No new profiler installation is selected.

## Behavior and recovery

- Given a clean fixed implementation and generated allowed source population
- When the isolated cohort executes one or two capture workers
- Then each capture preserves existing snapshot identities, selected content,
  source immutability and refusal behavior
- And evidence names its workload, instrumentation and process scope.

- Given a metric, platform capability or requested case cannot be measured safely
- When its attempt is reported
- Then the metric/cell remains unavailable or partial with a bounded reason
- And no value is inferred from source-byte limits, another process or smoke data.

- Given timeout, child failure, cancellation or incorrect capture
- When the coordinator stops the attempt
- Then all owned process groups are terminated/reaped and a terminal result is
  retained without retrying uncertain work
- And existing source, production state and prior evidence remain unchanged.

- Given later optimized source is proposed
- When baseline/candidate results are compared
- Then use identical fixture, runtime, dependency, host/cache and instrument mode
- And first establish correctness parity and complete comparable attempts
- But PY-09 itself selects no optimization or performance threshold.

Bound each worker to 60 seconds, each invocation to 1,800 seconds including
setup, and aggregate generated scratch files to 4 GiB. Launch at most two workers;
never start a new cell when current ownership or cleanup is uncertain. These are
harness admission/data/time bounds, not a hard controller RAM quota. A safe
resource check may refuse a cell; report it unavailable without resizing the
workload or claiming a full cohort. No machine cache purge or concurrency
activation is permitted. Retain requested evidence and remove only current-run
scratch after owned children exit.

## Validation, gates and maintenance

Use existing Python `>=3.12` project tools, root test dependency/lock authority,
and current qualified macOS environment. Other OS RSS conversions or interpreter
variants require independently recorded capability evidence; no package/runtime
setup is performed by benchmarks. Existing configured CI remains source-validation
authority, not a performance lab or permission to dispatch new runs. No typing
migration/full typing-coverage claim is selected; the root checker authority is
unconfigured and static analysis remains a visible capability gap.

Tests use small fixtures to validate aggregate-byte accounting, exact snapshot
parity, source exclusion, repeated/different historical blobs, one/two-worker
ownership, unit/backend refusal, cancelled/failed/oversized attempts, private
output safety and separate attribution cohorts. Near-limit measurement is opt-in
and is not added to default pytest or hosted CI. Existing affected snapshot,
publication/instruction and source-compilation checks remain required; they do
not prove collected full-cohort resource results.

All kernel gates, Review/Integrate and Maintain/Retire are required and pending.
Release, Deploy and Operate are not applicable to this source-only synthetic
slice: no package publication, installed runner or worker activation. The plan is
`docs/initiatives/dbsctr-cycle-speed/SNAPSHOT-BASELINE.plan.json`; no exception is
proposed. Review README/CHANGELOG and add a completed-cycle entry only when source
is delivered. Rollback restores source tooling; private evidence is retained.
The existing continuous-validation profile and resource/admission semantics stay
authoritative; no production persistent schema migration is introduced.

The maintainer owns workload validity, resource-unit qualification and compatibility
with capture changes. Revalidate on interpreter/OS/Git/capture changes. Future
streaming/copy reduction requires a separately approved behavior change with
matched evidence. Noise, instrumentation overhead, OS cache state and partial
resource scope remain explicit risks; inconclusive results stay inconclusive.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: ownership table and interface above distinguish benchmark, foundation and production |
| Interaction | required: attempt transition table below defines start, refusal and cleanup ordering |
| State | required: attempt transition table below keeps failures and uncertainty visible |
| Data/trust | required: data-flow table below distinguishes public fixtures and private runtime evidence |
| Schema | not_applicable: foundation shared evidence-format table is canonical; no production schema change |
| Dependency/deployment | not_applicable: source-only precursor dependencies are explicit in Initiative; no runtime deployment |
| Quantitative | not_applicable: no actual measurements exist; workload sizes are experimental inputs |

| Attempt state | Guard/event | Next state and retained evidence |
|---|---|---|
| Planned | Source/fixture/budget invalid | Unavailable/not-attempted with reason; no child starts |
| Planned | Preconditions valid | Running with exact source/fixture identity |
| Running | Capture valid and metric backend qualified | Measured with typed values and scope |
| Running | Failure, invalid capture or missing metric | Failed or partial/unavailable; no fabricated values |
| Running | Timeout/cancellation | Terminal timeout/cancelled after owned cleanup; uncertainty blocks further cells |

**Text Equivalent:** Validate source, fixture and budget before starting. Successful
capture supplies only measured qualified metrics. Refusal or failure stays visible.
Timeout/cancellation requires owned cleanup before any new cell. Canonical owner:
continuous-validation maintainer; change this table with attempt/cleanup behavior.

| Source | Destination | Data and authority |
|---|---|---|
| Committed generator | Disposable local Git worktree | Synthetic bounded selected/excluded contents only |
| Selected capture code | Owned scratch state | Existing immutable snapshot behavior; no enrollment or runtime activation |
| Child/coordinator metrics | Private evidence directory | Measured values, scopes, unavailable reasons and local raw profiles |
| Validated private evidence | Local report | Shared schema/statistics; no automatic public export |

**Text Equivalent:** Synthetic fixtures enter isolated capture only. Runtime
measurements and raw profiles remain private. Local reports validate the shared
contract and confer no production or publication authority. Canonical owner:
continuous-validation maintainer; update with any data boundary change.
