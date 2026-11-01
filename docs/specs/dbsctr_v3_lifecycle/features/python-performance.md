# Behavior-preserving Python performance

Status: Discovery specification ready; implementation and performance gains pending.
Owner: lifecycle maintainers. Initiative: `dbsctr-cycle-speed`, slice
`lifecycle-performance-core`. Engineering Profile: [../PROFILE.md](../PROFILE.md).
Risk: elevated. Modules: Python, Security, Data, Analytics. Delivery: source-only
feature branch and draft pull request; no installed-harness activation.

## Outcome and compatibility

Reduce repeated Python, SQLite and Git work while preserving harness behavior.
Every audited finding has a disposition below. Existing contexts and authorities
remain in place; this is not a new workflow, scheduler or telemetry service.
The existing cycle-speed contracts remain authoritative for whole-cycle timing,
privacy, projection generations and required evidence.

Successful optimization preserves CLI arguments, help, exit classes, result
schemas, deterministic ordering, capture identities, privacy invalidation,
authorization, native identity availability, feature defaults, provider/model
routes, gate applicability and gate decisions. Correcting the documented overlap
metric and preventing automatic-operation categories from masquerading as
duplicate work are diagnostic corrections, not changes to execution authority.

No user data migration, retention deletion, tool installation, DKS operation,
new native route, automatic retry, background service, concurrency activation,
gate skipping or formal advisory-evidence admission is included. Synthetic
benchmark qualification never authorizes runtime activation in this slice.

## Ownership and audit disposition

| Finding | Disposition and owner | Completion evidence |
|---|---|---|
| Repeated connected-family traversal | Implement one request-local family computation; lifecycle | Exact family/correlation parity and deterministic near-linear traversal counts |
| Population work behind page limits | Separate discovery from enrichment; reuse validated capture objects in the same request; lifecycle | Page, continuation, privacy and tamper parity; rows/decodes attributable by stage |
| Optional telemetry under global lock | Bound complete local collection and remove duplicate validation within one locked transaction; lifecycle | Contention/large-ledger/crash tests preserve command outcome and evidence |
| Incident full materialization and sort | Stream exact bounded first 101 eligible rows or use bounded selection; lifecycle | Identical first 100 groups/order/recovery and truthful overflow |
| Repeated Git and continuation reads | Reuse immutable metadata only within a read operation; lifecycle | Bounded subprocess counts, relocation/source-change and malformed-record tests |
| Startup compilation/import/parser cost | Measure and optimize only compatible internal work; lifecycle | Whole-process baseline/candidate results and standalone/import/sibling-helper parity |
| Inaccurate overlap/repeated-work interpretation | Correct diagnostic math and explicit automatic-event classification; lifecycle | Gap/nesting/touching/automatic-category cases, unchanged result schema |
| Unavailable automatic native attribution | Preserve unavailable attribution and full-cycle denominator semantics; lifecycle | Manual-only, automatic-only, mixed and incomplete cases never fabricate coverage |
| Source-index unavailability | Preserve typed refusal; qualify available and unavailable synthetic projection paths; lifecycle | No implicit refresh or raw-source fallback; unavailable remains distinct from empty |
| Synthetic concurrency qualification and stale fixture closure | Repair fixture dependency coverage and document limited evidence; lifecycle | Every fixture input resolves at its fixed commit; no activation command invoked |
| Duplicate CI execution | Supply baseline/protocol here; the dependent distribution-owned validation slice implements any hosted workflow change | Exact collected/executed test identity coverage and unchanged required checks |
| Missing reproducible Python profiling | Add repository-owned synthetic benchmark/profile tooling; lifecycle | Fixed workload/source/runtime identity, repeatable reductions and parity oracle |
| Stale Initiative/spec/model prose | Reconcile source status and reference canonical routing; existing document owners | Merge/source evidence, manifest validation and publication/instruction checks |
| Native adapter recovery, federation and complete-primary telemetry | Existing separate slices remain captured | No source/activation claim from helper timings or this implementation |
| Formal validation reuse, shadow activation and resource/cost claims | Existing separate owners retain authority | No advisory result admitted as a gate; unsupported metrics remain unavailable |
| DKS, routing/model changes, new concurrency and cleanup/merge automation | Excluded by the behavior-preservation constraint | No runtime changes or readiness promotion for these capabilities |

The context map remains lifecycle, OpenCode control plane, distribution and DKS
in the existing coordinator repository. Control-plane and distribution changes
in this lifecycle slice are documentary reconciliation only. The dependent
[validation-execution-performance](../../dotfiles_ai_distribution/features/validation-execution-performance.md)
slice owns hosted workflow implementation under the distribution profile. Continuous-validation source
status is reconciled in its existing Initiative; its runner, feedback, enrollment
and execution behavior are not modified.

## Domain and data boundaries

| Term | Meaning |
|---|---|
| Compatibility oracle | Exact pre/post observable output or an explicit diagnostic-correction expectation, including refusal and corruption cases |
| Request-local proof | Parsed/validated state reusable only while the same lock, open connection, transaction, source and privacy identity remain valid |
| Family component | Connected session membership computed once, without copying a complete family independently for every member |
| Selected enrichment | Metric work for the immutable selected page and necessary family members, after required population validation |
| Collection budget | A monotonic deadline for optional local telemetry, never a timeout for the required command it observes |
| Comparable pair | Baseline and candidate on identical fixture, interpreter, dependencies, configuration and cache condition |

Synthetic sessions, projection rows, records and workload identities are public
fixtures, not copies of private stores. Runtime ledger data remains governed by
existing APIs. No private database, prompt, error body, account identity or
machine path enters committed benchmark artifacts. Profilers can expose paths:
raw profiles remain local; only classified synthetic aggregates may be exported.

## Behavior

### Preserve History and Incident meaning

- Given a fixed projection generation, privacy epoch, capture and query
- When optimized discovery, enrichment or Incident reduction runs
- Then outputs, identities, ordering, availability and corruption refusals match
  the existing compatibility oracle
- And family traversal is shared rather than repeated for each related member
- And selected-page work does not unnecessarily decode unrelated metric payloads
- But global validation required by the current trust contract is not omitted.

### Bound optional collection

- Given optional collection is activated under existing policy
- When local start or finish collection begins
- Then one 1,000 ms monotonic budget covers policy lookup, association, lock
  acquisition, SQLite validation/write/commit and local feedback enqueue
- And SQLite busy waits and progress/validation loops consume the same remaining
  budget rather than each receiving a fresh timeout
- And timeout rolls back an incomplete transaction or retains an already committed
  valid event, reports existing unavailable coverage, and preserves the required
  command's original outcome
- But required command/gate execution and an independently authorized external
  feedback flush retain their existing separate authorities and bounds.

The budget starts at the collector boundary, not process launch. It cannot bound
an uninterruptible operating-system filesystem call; tests and the final report
must state that residual risk. Start proof expires before the required command;
finish must revalidate. No cross-process integrity cache or shortcut based only on
file timestamps is allowed. Existing retention remains unchanged; introducing
workflow-event pruning requires its own data-retention contract and is excluded.

### Correct diagnostic interpretation

- Given complete spans with gaps, nesting or touching boundaries
- When overlap is reported
- Then overlap is the sum of durations minus their interval-union duration
- And partial/missing intervals retain current unavailable semantics.

- Given distinct automatic operations share a generic phase-span category
- When repeated-work diagnostics are reduced
- Then only exact validated event-to-span association identifies automatic spans
- And those distinct events do not imply duplicate execution
- And legacy explicit-marker category repetition remains documented as a
  heuristic, never proof of repeated validation or avoidable work.

Helper-only intervals remain distinct from complete primary execution and native
actor identity. Do not remove unavailable spans from autonomous coverage merely
to increase complete sample counts. Local-only quiet paths remain quiet.

### Reuse only stable local work

- Given a read operation retains unchanged repository/source and lock identities
- When it needs the same Git metadata, continuation data or validated capture
- Then it reuses the request-local result
- But a mutation, lock release, source/privacy change or new command invalidates
  that proof, and required checks still run before authority is granted.

### Report defensible performance gains

- Given matched baseline/candidate source and synthetic workload identities
- When paired post-warmup measurements finish
- Then report mean, nearest-rank p50/p90, sample count, failures, unavailable
  attempts, workload shape and correctness result for each measured surface
- And report absolute and percentage differences only for comparable successful
  pairs, retaining every eligible failure in the denominator
- And never present isolated reducer or CLI gains as whole-cycle speedup.

## PY-09 measurement-only foundation

The operator selected three active owners for PY-09: lifecycle owns the common
measurement contract and CLI baselines, distribution owns retained-CI analysis,
and `continuous_validation` owns isolated snapshot-memory measurements. All live
and synthetic DKS model-service work is deferred. This extends the existing
cycle-speed Initiative; it creates no new bounded context or audit controller.

The `python-cli-baseline` source slice supplies reusable, explicitly invoked
benchmark tooling and a versioned evidence format before optimization. The
`python-ci-baseline` and `python-snapshot-memory-baseline` slices consume that
contract. Existing `lifecycle-performance-core` and
`validation-execution-performance` implementation scopes remain separate; their
new prerequisites invalidate earlier launch receipts. Measurement success proves
benchmark integrity and coverage, not faster application behavior.

### Scope and source closure

Lifecycle may add `tests/benchmarks/performance_evidence.py`,
`tests/benchmarks/python_performance.py`, synthetic `cli_*.json` fixtures in
`tests/benchmarks/fixtures/`, and `tests/test_python_performance.py`. No production
helper, managed skill, runtime, dependency, lockfile, workflow or deployment is
changed by this foundation. The existing Engineering Profile applies with Python
and Security modules, elevated risk and source-only draft delivery. This is
internal developer infrastructure; no separate Product Intent is introduced.

Proposed repository interface, available only after Build:

- `python tests/benchmarks/python_performance.py cli --source-tree PATH --output PATH`
  runs the declared CLI cohort in disposable synthetic repositories.
- `python tests/benchmarks/python_performance.py report --input PATH --output PATH`
  validates and summarizes evidence without executing workloads. Multiple input
  records are combined only within identical comparison cells and a verified
  execution cohort; otherwise display them separately without aggregation.
- `--profile` selects a separate attribution cohort. `--smoke` selects a small
  explicitly incomplete fixture cohort. Neither changes the meaning of a full
  timing cohort or a required project check.

`PATH` arguments are local caller inputs, never committed runtime identities.
Output must be a fresh owner-private directory outside the source checkout;
refuse symlinked or unsafe targets. Create files with mode 0600 and directories
with mode 0700. Do not overwrite prior evidence, erase failures, install tools,
create a registered cycle, or inspect private lifecycle/session stores.

### CLI workload and instrumentation contract

The initial cohort covers fresh-process `--help`, `status --json` with no active
cycle, and `initiative-check` over valid synthetic manifests containing 10 and
100 finite dependency nodes. Run these against disposable Git histories with
one and 100 commits. Pin the manifest generator seed and exact expected output,
exit class and source-immutability oracle. Fixtures must use existing accepted
record/manifest semantics; no real operator approval, credential, enrollment or
mutation authority is manufactured to make a fixture run. An unsupported valid
fixture is unavailable and cannot silently become a different successful case.

Whole-process wall time is measured by the parent. Process CPU is reported only
when its child/process scope is established. Git launch counts come from a
separate instrumented cohort using fixed public operation classes, without raw
arguments or output. Timing runs use the qualified Git executable without a
counting wrapper; instrumentation overhead must not become apparent CLI latency.
Profile with existing stdlib `cProfile`/`pstats` in separate runs. Count subprocess
launches without changing the production helper or caching its authority checks.

Use the current selected interpreter and qualified Git, isolated temporary HOME
and XDG directories, disabled ambient Git configuration/hooks/signing, no agent
sockets or project credentials, and no inherited Python import customization.
The target checkout is read-only and must identify one clean committed source.
No network fetch, private database, provider call, service discovery, implicit
refresh or installed-harness activation is allowed. If a CLI path cannot satisfy
this isolation, refuse that cell explicitly rather than bypassing its guards.

### Shared evidence format and statistics

The additive benchmark format has `schema_version: 1` and these required groups:

| Group | Required meaning |
|---|---|
| Source | Full commit and tree IDs, benchmark-tool revision, clean-source proof, dependency-lock digest and workload/generator digest |
| Environment | Python version, executable/tool digests, OS family/version, architecture, logical CPU count and launcher-bound opaque execution cohort; no host/user identity or absolute executable path |
| Cell | Surface, fixture size/topology, controller count where relevant, instrumentation mode, cache condition and declared required/optional metrics |
| Attempts | Warmup flag, sequence, measured/partial/failed/unavailable/timed_out/cancelled/not_attempted status, bounded reason code, duration/CPU/count/memory values with units and scope, and compatibility result |
| Coverage | Planned, attempted, successful, failed, unavailable and excluded counts with explicit exclusion reasons |
| Summary | Integer-floor mean and nearest-rank p50/p90 for each comparable metric, per-metric eligible sample counts and uncertainty/limitations |

The launcher generates one opaque private `execution_cohort` binding per local
invocation after verifying its execution environment, rechecking source/tool
identity outside each timing window. It contains no host identifier. Sharing OS,
architecture and tool digests cannot establish the same host: separate invocations
must remain distinct cohorts unless independently verified retained execution
provenance binds them. A caller-supplied equal string alone is insufficient.
Offline reports cannot authenticate fabricated cohort bindings and must label
unverified inputs; they cannot claim measured cross-host or cross-invocation
comparability. Retained CI jobs default to separate host cohorts unless their
retained provenance establishes one shared execution environment.

A missing metric is null with an availability reason, never zero. Numeric values
must be finite and nonnegative; bool is not a numeric observation. Keep attempts
immutable. Unknown fields, unsupported schema versions and conflicting source or
cell identities refuse ingestion. Recompute summaries from attempts and reject
forged counts or statistics. Schema validation uses the existing Python/pytest
stack; no new validation package, static checker or runtime is selected.

One unprofiled baseline cell has one warmup and ten planned recorded attempts.
Warmup, failures and unavailable attempts remain in evidence; each metric summary uses qualified compatible values from measured or partial
non-warmup observations, with its own eligible sample count. A missing CPU or RSS
value never erases an independently valid wall-time observation.
Do not mix Python versions, hosts, Worktrunk lanes, sources, workload sizes,
profiling modes or cache conditions. A fresh process is not proof of a cold OS
page cache. Do not purge caches; record filesystem cache state as uncontrolled.
A complete successful baseline means all ten planned attempts have compatible
measurements for the cell's declared required metrics; missing optional values
remain unavailable and are excluded only from their own metric summaries. Incomplete cells remain partial; no latency
threshold or speedup is required to accept the tooling itself.

Future comparisons use at least five alternating baseline/candidate pairs under
the existing optimization contract above. Baseline-only data, a single retained
CI job or component RSS cannot establish a whole-cycle gain, foreground
responsiveness, total host memory use or a performance regression. No percentile
is invented for unavailable samples. No candidate is optimized in PY-09.

### Concrete foundation interfaces

The implementation has two modules: `performance_evidence.py` owns immutable
records, bounded file I/O and statistics; `python_performance.py` owns fixture,
process and CLI orchestration. Tests use their public seams, not production
helper monkeypatches. The checked-in `cli_workloads.json` freezes source-helper
and runtime-specific help digests before timing; a different source/help oracle
is unavailable until deliberately requalified. The initial supported-runtime
oracles cover Python 3.12, 3.13 and 3.14. Native Git system configuration must be
qualified inert independently because the selected helper drops injected Git
configuration variables. Reject non-inert configuration; do not use a timing
wrapper as a substitute. Fixture-local hooks, signing, credential helpers,
fsmonitor, maintenance and templates are disabled explicitly.

Evidence module signatures:

- `canonical(value: object) -> bytes` and `digest(value: object) -> str`.
- `build_record(source, environment, cell, attempts, planned) -> dict` computes
  coverage/statistics from attempts; `validate_record(record) -> dict` refuses
  malformed or inconsistent serialized records.
- `read_records(paths: Sequence[Path]) -> list[dict]` applies the declared file,
  population, ownership and byte bounds before returning validated records.
- `create_private_output(path: Path, source: Path | None = None) -> Path` creates
  a fresh safe directory; `write_private_json(directory, name, value) -> Path`
  writes one bounded owner-private file without replacement.

Record fields are closed: `schema_version`, `source`, `environment`, `cell`,
`attempts`, `coverage` and `summary`. Source holds `commit`, `tree`, `tool_commit`,
`lock_sha256`, `workload_sha256` and `clean`. Environment holds `python`,
`python_sha256`, `git_version`, `git_sha256`, `os`, `os_version`, `architecture`,
`cpu_count` and `execution_cohort`. Cell holds `surface`, `workload`, `dimensions`,
`fixture_sha256`, `instrumentation`, `cache` and `metrics`. Metric descriptors
hold `unit`, `scope` and `required`; each attempt holds `sequence`, `warmup`,
`status`, `reason`, `compatible`, `returncode`, `metrics`, `unavailable` and
`output_sha256`. Coverage and per-metric summary are derived and checked exactly;
unknown fields or duplicate JSON keys refuse ingestion. Serialized cohort and
source claims are not authenticated by an offline report. Separate input files
remain separate cohorts unless independently verified provenance exists.

CLI success is exit 0 for a complete requested cohort/report, exit 75 for an
unavailable/incomplete required measurement, exit 1 for an incompatible execution
or failed cohort, and exit 2 for invalid input. Optional unavailable metrics never
erase a qualified primary wall-time observation. A report validates input without
executing code or upgrading provenance. No actual runtime paths enter records.

### Bounds, recovery and publication

| Benchmark attempt | Condition | Disposition |
|---|---|---|
| Planned | Identity, isolation or budget invalid | Unavailable/not_attempted; retain reason and start no child |
| Planned | Preconditions valid | Running with exact source/workload binding |
| Running | Correct output and qualified metric | Measured; retain bounded typed values |
| Running | Some metrics absent | Partial; retain available scoped values and missing reasons |
| Running | Failure, timeout or cancellation | Failed/timed_out/cancelled; retain disposition and reap owned work |

**Text Equivalent:** A benchmark starts only after its binding/isolation checks.
Successful observations retain actual values; partial observations expose missing
metrics. Failures and cancellation keep terminal evidence and require owned
cleanup. Canonical owner: lifecycle maintainer; update with attempt semantics.

Report ingestion is bounded to 32 explicitly selected evidence files, 16 MiB per
file, 128 MiB aggregate, 256 cells and 10,000 attempts per file. Validate file sizes
before parsing and reject oversized schemas/populations rather than slicing off
unreported attempts. Default report budget is 60 seconds; a budget failure retains
a terminal error and never emits a complete summary. No recursive directory or
unrestricted archive ingestion is permitted.

CLI defaults: at most 10 seconds per child and 600 seconds total, including
fixture setup. Bound generated scratch including raw outputs/profiles to 1 GiB
per invocation and each profile to 16 MiB. Reserve fixture/output budgets before
creation and enforce bounded producer writes or stop the owned producer on
observed overflow. Overflow is a failed/unavailable attempt with retained reason,
not a truncated successful profile or an implicit limit increase. Own a separate process group, concurrently drain bounded output,
terminate and reap owned descendants on timeout/cancellation, and retain a
terminal attempt disposition. Limit each captured stream to 1 MiB and keep raw
profiles/output private. Reaching a budget records remaining cells as not
attempted with a reason; it never converts them to successful samples.

The public repository contains only generic tooling, schemas/contracts and
synthetic fixtures. Existing publication/instruction authority applies to the
complete staged artifact closure before receipt or publication. Retained CI logs,
raw profiles, runtime paths and local evidence remain private. No automatic
upload, issue creation, optimization, runtime change, cleanup or deployment
follows from a report. Cleanup may remove only scratch artifacts created by the
current invocation after all owned work is reaped; retain requested evidence.

Acceptance tests cover source/cell isolation, deterministic fixtures, exact
statistics, missing/invalid/duplicate observations, mismatched identities, unsafe
output paths, command failures, output overflow, cancellation and descendant
cleanup. A compatibility failure keeps its measurement unusable. Run the existing
affected pytest, compilation, publication/instruction checks and configured CI
for source delivery. Existing profile authority has no configured Python checker;
static-analysis coverage remains unavailable, with no typing migration or full
population claim in this slice.

The source applicability plan is
`docs/initiatives/dbsctr-cycle-speed/PYTHON-BASELINE.plan.json`: all kernel gates,
Review/Integrate and Maintain/Retire required; Release, Deploy and Operate not
applicable for the source-only synthetic tooling. Every required result starts
pending; no exception or launch approval is implied by Discovery readiness.
Review README and CHANGELOG; add a completed-cycle entry only after delivery,
never present Discovery as an implemented benchmark or measured improvement.

The lifecycle maintainer owns this protocol and evidence compatibility. Bump the
format version for incompatible changes, retain prior evidence readers or state a
reviewed retirement policy, and rerun capability/fixture checks on Python, Git,
platform or source changes. Source restoration is rollback; no private records
or installed configuration require migration.

## Implementation boundaries and sequence

This optimization slice follows delivered `python-cli-baseline`. The invoking
primary owns one cycle and serializes shared helper/test edits.
Use incremental phases, retaining red regression evidence before each change:

1. Freeze compatibility fixtures and reproducible baseline/profile procedure.
2. Optimize family traversal and page/capture reuse, then Incident selection.
3. Optimize request-local Git/continuation work and optional telemetry validation
   within the existing private evidence owner; enforce collection deadline.
4. Correct diagnostic reductions and retained benchmark fixture closure.
5. Evaluate startup and provide the duplicate-CI baseline to the dependent
   distribution slice. Ship only measured compatible changes; document a
   rejected candidate with evidence rather than forcing a rewrite.
6. Run matched final benchmarks, downstream QA and source-status reconciliation.

Source write closure: `dot_local/bin/executable_dbsctrctl`, affected lifecycle
tests, additive public/synthetic performance fixtures and a repository-owned
benchmark runner under `tests/`. Hosted CI implementation belongs only to the
dependent distribution slice. No hosted workflow, continuous-validation runner
or adapter, or native harness code changes belong to this lifecycle slice.
Documentation closure is the complete artifact list in the Initiative receipt.
New runtime packages, sibling modules or changed distribution paths require
reopened readiness; standalone copied-script and SourceFileLoader consumers,
monkeypatch behavior, sibling helper lookup, source digests and self-execution
are existing compatibility constraints, not incidental tests to delete.

## Profiling and benchmark contract

Use existing project Python/test tools and stdlib `cProfile`, `pstats`,
`tracemalloc`, monotonic wall and process CPU clocks. Profile attribution and
unprofiled performance timing are separate runs. No new dependency is required.
Freeze a benchmark fixture before comparing implementations; the same runner
loads both source identities. Private lifecycle stores are never benchmark input.

Workloads cover singleton/chain/star/disjoint families at multiple sizes;
fixed pages amid growing unrelated populations; Incident 100/101 overflow,
dispositions, recovery and ties; ledgers with increasing event/capture counts;
multiple synthetic Cycle Records; CLI help and read-only fixture commands;
complete/partial/mixed-attribution timing; and lock/contention/crash cases.
Collect deterministic visits/rows/decodes/subprocesses as correctness-regression
oracles. Wall-time thresholds do not become flaky unit-test assertions.

Run one warmup and at least five alternating baseline/candidate pairs on the
same supported interpreter, host, dependency identity and cache condition. Keep
cold and warm results separate. Memory profiling is separate and reports Python
allocation peaks, not total process RSS. Performance acceptance requires exact
compatibility, no new failures, improved work bounds on targeted algorithms and
at least 10 percent median improvement on each designated performance target
without more than 5 percent repeatable p90 regression in control workloads.
If noise prevents a conclusion, repeat the predeclared complete cohort once and
report inconclusive; do not cherry-pick runs. A no-benefit optional refactor is
rejected, not counted as an improvement. These targets do not activate concurrency.

CI optimization must preserve every unique required test identity on each
existing runtime/Worktrunk lane and early publication checks. Cross-gate evidence
admission, changed test authorities and reduced runtime matrices are excluded.
A reduction in successful telemetry coverage is not a performance gain. Large
ledgers that exhaust the collector budget remain explicitly unavailable; retain
that denominator beside throughput and latency. No whole-cycle claim is possible
without independently complete comparable
autonomous samples, which remain an existing separate measurement requirement.

## Validation and gates

Authoritative dependencies: `pyproject.toml` and `uv.lock`; supported Python
versions remain unchanged. Use repository-selected pytest, compilation,
publication/instruction checks, affected downstream fixtures and full configured
CI. Discovery runs publication checks over staged new documents before receipt.
Every material manifest change runs `dbsctrctl initiative-check`.

| Gate | Applicability | Current result | Required evidence |
|---|---|---|---|
| Domain | required | pending | Ownership, complete audit disposition and unchanged authority |
| Behavior | required | pending | Parity, failure, availability and metric scenarios |
| Spec | required | pending | Committed contracts, profiles and benchmark identity |
| Contract | required | pending | Trust, transaction, deadline, CLI and import compatibility |
| Test-driven implementation | required | pending | Intended red evidence then affected passing tests |
| Refactor | required | pending | Coherent source and benchmark comparisons |
| Review/Integrate | required | pending | Independent scoped review, downstream QA and configured CI |
| Release | not_applicable | not_run | No independently published package |
| Deploy | not_applicable | not_run | Source-only draft; no installed helper/configuration changes |
| Operate | not_applicable | not_run | Disposable synthetic tests; no live rollout or activation |
| Maintain/Retire | required | pending | Compatibility, reproducible procedure, retained evidence and no state deletion |

No Gate Exception is proposed. Source readiness is not launch approval or a gate
pass. Build must obtain a fresh digest-bound receipt and preflight for the exact
source and target. Final reporting separates source delivery, test/benchmark
results, installed activation and whole-cycle availability.

## Visual Evidence

| Concern | Decision and review question |
|---|---|
| Boundary | not_applicable: ownership/disposition table directly identifies every affected and excluded owner |
| Interaction | not_applicable: ordered implementation sequence and collector behavior specify ordering without another diagram |
| State | required: benchmark-attempt table above and optional-collection table below define distinct lifecycles |
| Data/trust | not_applicable: domain/data and request-local proof contracts explicitly retain the existing trust boundaries |
| Schema | required: shared evidence-format table above defines additive benchmark records; production schemas are unchanged |
| Dependency/deployment | not_applicable: existing delivered audit dependency and source-only closure are explicit |
| Quantitative | not_applicable: benchmark protocol is normative; no candidate results exist to chart |

| Collection state | Condition | Outcome |
|---|---|---|
| Not selected | Existing activation policy unavailable or local-only quiet path | Existing unavailable/quiet behavior; no fabricated event |
| Pending start | Local budget and validation succeed | Existing start event committed |
| Pending start/finish | Budget or validation fails before commit | Rollback partial transaction; preserve command outcome |
| Start retained | Command crashes or finish unavailable | Existing partial interval retained |
| Finished | Valid finish commits within budget | Existing event outcome; attribution remains truthful |

**Text Equivalent:** Existing policy determines whether collection runs. A valid
bounded start creates an event; incomplete transaction failure rolls back without
changing the required command. Missing finish leaves a partial interval. A valid
finish records outcome without manufacturing native attribution. Canonical owner:
lifecycle; update this table when collection or recovery contracts change.
