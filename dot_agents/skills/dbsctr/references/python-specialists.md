# Python Specialist Guidance

Use the [common selection contract](specialist-selection.md) when selecting a
specialist. Keep the Python module's outcomes and project-selected tools,
runtimes, dependencies, compatibility and acceptance criteria.

## Select the relevant technique

| Evidence | Preferred guidance |
|---|---|
| Changed responsibilities, boundaries or abstractions | `python-design-patterns` |
| Meaningful parser/serializer/validation or state invariant | `property-based-testing` |
| Performance problem, requirement or measured bottleneck | `python-performance-optimization` |
| New packaging/tooling setup or selected tooling migration | `modern-python` |
| Changed async ownership, cancellation, concurrent I/O or sync boundary | `async-python-patterns` |
| Runtime/support-floor change or requested modernization/debt audit | `python-modernization-review` |

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

## Sources and maintenance

The [original Python source inventory](python-specialists/sources.lock.json)
records the first four complete bundles, immutable pins, licenses, original Git
blobs/SHA-256 hashes and reversible patches. The async and Django bundles use the shared
expansion inventory at `specialist-sources/sources.lock.json`; modernization review
is locally maintained. Each vendored bundle's `UPSTREAM.md` explains adaptations
and its `LICENSE.upstream` retains the exact notice. The Trail of Bits adaptations
remain CC-BY-SA-4.0 independently of the repository license.

Updates deliberately review the complete pinned bundle and local patches,
including supporting resources. Ordinary loading consumes installed reviewed
bytes. Use source provenance/resource tests and the distribution's exact-target
preview/application, prior-live comparison and complete verification. Preserve
unrelated installed state and report filesystem, discovery and behavioral
observations separately. Recovery restores matching reviewed bundles, routing
and inventories through the same distribution owner.
