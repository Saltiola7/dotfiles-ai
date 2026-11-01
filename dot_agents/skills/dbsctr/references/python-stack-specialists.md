# Conditional Python stack and runtime methods

The [Python module](../modules/python.md#conditional-controls) owns the canonical
selector/checkpoint table. The existing primary owns the task; project policy owns
runtimes, dependencies and compatibility; QA owns executed check evidence. These
conditional methods add detail when actual project evidence needs it. They do not expand
ordinary work into a full audit or replace the fourteen generic audit lenses.

[`pydantic`](../../pydantic/SKILL.md) owns runtime input/output validation and serialization technique. Keep
strictness/coercion, aliases, extra fields, validator order and public field
exposure explicit. Static annotations are not runtime validation. Internal domain
models do not automatically need Pydantic; settings integration is conditional on
the project's selected configuration sources and precedence.

[`fastapi`](../../fastapi/SKILL.md) owns concrete framework dependencies, response/streaming and route
semantics. Reuse async/resource/database techniques when that boundary needs them,
without duplicating findings. [`typer`](../../typer/SKILL.md) owns its actual CLI framework interfaces;
existing commands, exit codes, stdout/stderr and noninteractive compatibility
remain project contracts. Neither technique selects its framework or an unrelated
ORM, async library, checker or output library.

[`polars`](../../polars/SKILL.md) owns expression/query execution and dataframe semantics. Python and Data
route to the same method. Check schema, cardinality, null/order, period and sink
contracts; planning/schema discovery may perform I/O. Keep DuckDB, pandas and other
chosen stacks unless a migration is explicitly selected. Profiling needs actual
representative evidence and retains the performance specialist's contract.

[`atheris`](../../atheris/SKILL.md) owns a selected coverage-guided harness, target instrumentation, corpus
and crash reproduction. Keep expected rejections distinct from unexpected bugs,
and bound inputs, time, memory, output and external effects. Native sanitizers
need the actual selected compiler/runtime/extension environment. Installing the
skill does not install compilers, change environments or run a fuzz campaign.

[`secure-python-release-pipeline`](../../secure-python-release-pipeline/SKILL.md) reviews actual source distributions, wheel contents, isolated
installation/smoke and provenance/publishing boundaries. Existing lifecycle
Release and CI policy remain authoritative. A successful metadata check is not an
artifact behavior test; build examples grant no registry or credential operation.
[`port-to-free-threaded-python`](../../port-to-free-threaded-python/SKILL.md) reviews actual shared-state ownership, synchronization,
extensions, GIL state and selected runtime evidence. Failed imports remain errors;
import success is neither no-GIL proof nor thread-safety proof. Keep async,
modernization and Python/Rust responsibilities distinct. Both upstream methods
remain Experimental and need applicable primary-source/version verification.

## Locally authored advanced methods

[`python-process-parallelism`](../../python-process-parallelism/SKILL.md) owns
actual process/subinterpreter pools, serialization, bounded submission, IPC and
child/shared-memory lifecycle. Keep async task ownership, selected free-threaded
runtime qualification and resource cleanup with their existing specialists; reuse
rather than duplicate findings. Runtime-version gates matter: a cancelled Future
is not proof that running work stopped or that executor shutdown is bounded.

[`python-data-contracts`](../../python-data-contracts/SKILL.md) owns actual
frame schema, coercion and value invariants. Pydantic retains object/API boundary
validation; Polars retains query/expression semantics. Inspect the chosen backend
and actual validation depth. Lazy error aggregation does not imply LazyFrame
value validation, and schema discovery may access data.
[`python-arrow-interchange`](../../python-arrow-interchange/SKILL.md) owns actual
Arrow schemas, batches, null/time semantics, representation/lifetime and columnar
handoffs. Engine specialists retain query/storage choices; zero-copy, round trips
and bounded memory need producer/consumer-specific evidence.

[`python-mutation-testing`](../../python-mutation-testing/SKILL.md) owns explicitly
requested mutation analysis or existing mutation configuration. Preserve a green
baseline, isolated source, selected target/test scope and time budget. Static
audit can recommend a campaign without executing it. Distinguish raw tool status
from a meaningful killed mutant and unsupported equivalence claims; retain
property-based and ordinary testing as complementary methods, without adding a
universal score or gate.

[`python-durable-jobs`](../../python-durable-jobs/SKILL.md) owns durable enqueue,
claims/leases, effects, acknowledgement, redelivery and crash recovery. Database
boundaries retain client/transaction mechanics; resilience retains per-call retry
policy. Databricks Jobs retains platform task graphs. Request-local background
callbacks and ordinary async tasks do not become durable queues. Review dual-write
and stale-worker windows against actual engine guarantees.

These five are original local guidance informed by linked primary documentation.
They are not additions to the seven vendored provenance records below. Maintain
version-sensitive decisions against project-selected runtimes/backends and refresh
with demonstrated usage failures. No tool installation or operation is implied.

## Provenance and delivery

Complete bundles, immutable originals, exact licenses, file mappings/modes and
reversible changes are recorded under:

- [Frameworks](python-expansion-sources/frameworks/sources.lock.json)
- [Data and fuzzing](python-expansion-sources/data-testing/sources.lock.json)
- [Runtime and release](python-expansion-sources/runtime/sources.lock.json)

Official framework/data bundles retain MIT, Atheris guidance CC-BY-SA-4.0, and
runtime/release guidance Apache-2.0 with modification notices. Follow the existing
distribution owner for complete-bundle updates, original creator validation,
resource/provenance tests, scoped preview and apply, prior-live drift guards and
recovery. Preserve separately installed skills and routing. File installation,
physical-sibling resolution, native catalog selection and consumer execution are
separate evidence; missing capability never becomes a pass.
