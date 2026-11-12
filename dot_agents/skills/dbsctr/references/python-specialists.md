# Python Specialist Guidance

For selection or discovery questions, see the [common contract](specialist-selection.md).
Keep the Python module's outcomes and project-selected tools,
runtimes, dependencies, compatibility and acceptance criteria.

## Apply the selected technique

For an explicitly requested repository-wide Python assessment, use `python-audit`.
It considers fourteen assessment lenses and applicable database boundaries, records actual review and QA coverage, and
returns opinionated findings plus ordered refactor batches. Audit intent does not
select a migration or authorize remediation. Ordinary development continues with
the conditional selection below.

The [Python module's conditional controls](../modules/python.md#conditional-controls)
own the canonical trigger/checkpoint table. These method notes do not create a
second routing table. Framework guidance such as `django-expert` remains
conditional on actual framework behavior and an existing installed bundle.

`python-design-patterns` addresses responsibilities and dependency direction;
`property-based-testing` meaningful invariants; `python-performance-optimization`
representative measurement; and `modern-python` selected setup/migration options.
`async-python-patterns` owns concurrency technique and
`python-modernization-review` support-floor/debt assessment.

`python-testing-patterns` supplies fixture/isolation/integration technique;
`python-type-safety` supplies typed interface design; `python-resilience` addresses
remote failure/retry contracts; `python-resource-management` handles owned and
borrowed lifetimes; `python-observability` covers applicable telemetry.


Ordinary edits can need none. Reassess when evidence changes the concern, using
only relevant resources and the current primary. A skill need not run in a helper.

Property testing must express a meaningful rule; existing example tests can be
sufficient. New libraries remain project dependency decisions. Performance work
needs a baseline, equivalent workloads and correctness evidence; absent required
measurements cannot become a speedup claim. Tooling examples preserve selected
mypy/Pyright, Poetry, layout, scheduled CI and runtime commitments. Async patterns
must match supported versions, task/resource lifetimes and cancellation behavior.
Modernization review classifies evidence-backed findings before remediation.

A missing preferred skill is a guidance limitation. Missing or failed required
validation remains governed by the existing Gate Ledger, with no invented pass
or new gate solely because a technique is unavailable.

Typing techniques retain the core's selected checker and coverage policy; they
cannot prescribe a checker migration. Testing methods retain the existing suite
and QA authority. Resource, retry and observability guidance applies when actual
I/O/service behavior warrants it, with task cancellation, idempotency, ownership
and privacy intact. A file/database handle is not by itself an async requirement.

For database semantics use the Data module and `database-audit` as appropriate.
`python-database-boundaries` owns Python adapters; engine/platform specialists own
SQL/storage/workspace behavior. Keep one primary and deduplicate shared findings.

For architecture requests, use the focused mode of the same `python-audit`.
`architecture-patterns` owns system/context choices; `python-project-structure`
owns package/public-import organization; `python-architecture-fitness` owns accepted
dependency contracts and checking limits. Existing `python-design-patterns` keeps
component design. Architecture focus selects these first, then only relevant
additional techniques; full audit considers all fourteen assessment lenses.

## Sources and maintenance

The [original Python source inventory](python-specialists/sources.lock.json)
records the first four complete bundles, immutable pins, licenses, original Git
blobs/SHA-256 hashes and reversible patches. The async and Django bundles use the shared
expansion inventory at `specialist-sources/sources.lock.json`; modernization review
is locally maintained. Each vendored bundle's `UPSTREAM.md` explains adaptations
and its `LICENSE.upstream` retains the exact notice. The Trail of Bits adaptations
remain CC-BY-SA-4.0 independently of the repository license.

The five additional Python techniques use `python-data-sources/python/sources.lock.json`;
engine and platform inventories live alongside it under `engines` and `databricks`.
`python-database-boundaries` and `database-audit` are locally maintained.

The three marimo bundles use the shared expansion inventory too. Notebook and
Rust/Python techniques apply only to their actual task boundary; they do not
expand the general Python audit's selected lenses. `marimo-pair` retains live
kernel mutation ownership. The original Rust/Python method follows official
selected-version documentation instead of importing a general Rust skill tree.

Updates deliberately review the complete pinned bundle and local patches,
including supporting resources. Ordinary loading consumes installed reviewed
bytes. Use source provenance/resource tests and the distribution's exact-target
preview/application, prior-live comparison and complete verification. Preserve
unrelated installed state and report filesystem, discovery and behavioral
observations separately. Recovery restores matching reviewed bundles, routing
and inventories through the same distribution owner.


The two architecture bundles use `architecture-sources/sources.lock.json` with
complete resources, MIT notices and reversible adaptations. Fitness guidance and
architecture-focused audit synthesis are locally maintained. No separate checker,
audit coordinator or universal architecture policy is installed by those skills.
