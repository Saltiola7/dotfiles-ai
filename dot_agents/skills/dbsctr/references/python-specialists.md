# Python Specialist Guidance

Read when the Python module identifies a relevant specialist. This reference
does not add a gate or replace project-selected tools, QA or the current primary.

## Select and load

Use the Python module's evidence-based triggers. `python-design-patterns` informs
architecture and abstractions; `property-based-testing` informs meaningful
invariants; `python-performance-optimization` informs measurement and optimization;
`modern-python` informs new setup or a selected tooling migration. These are
independently discoverable skills, not mandatory steps for every Python task.

Load a selected skill through the client's native skill loader. If no loader is
exposed, read its installed `SKILL.md` from the available skill catalog and resolve
resources relative to that bundle. Load only the supporting references needed for
the current question. Do not fetch a moving upstream version during task execution.

Keep one primary. Loading guidance does not require a helper agent. The primary
may delegate a bounded, independent investigation under existing DBSCTR rules,
then reconciles its result. New findings can change selection or reopen an affected
phase; they do not silently expand scope.

## Policy and interaction

User intent and the project Engineering Profile determine supported runtimes,
selected tools, dependencies, layout, compatibility and acceptance criteria.
Upstream examples, coverage numbers and design heuristics are not universal
requirements. In particular, `modern-python` does not replace mypy/Pyright,
Poetry, build backends or scheduled CI unless that migration is selected.

Proceed with routine selection and already-authorized work. Ask only when an
unresolved choice materially changes scope, compatibility, tooling or tradeoffs,
or native permissions require it. Present a concrete decision supported by the
available evidence; do not repeatedly ask for authorization already given.

Property testing must express a meaningful rule; a reasoned decision to use
example tests is valid. New libraries remain project dependency decisions, and
working code need not be redesigned solely to introduce Hypothesis. Profiling
needs a baseline, equivalent workloads and correctness checks; missing required
measurements cannot become an unmeasured speedup claim.

If a preferred skill is missing, say so and use equivalent guidance if it can
satisfy the task. Do not auto-install it or invent a gate failure solely for its
absence. Missing, failed or unavailable required validation still follows the
existing Gate Ledger and exception rules.

## Return to the existing cycle

Carry only decision-relevant results into existing artifacts/evidence:

- affected scope, selected skill and reviewed revision;
- applicable project policy and concrete findings or recommendations;
- affected interfaces, contracts, tests or other artifacts;
- actual evidence, measurements/counterexamples and their limitations;
- unresolved decisions and the validation needed to resolve them.

The primary accepts or rejects recommendations and owns lifecycle decisions.
QA runs project-selected authorities. A loaded skill, an installation check or a
specialist's assertion is not proof that a required capability passed. Keep live
execution evidence in the existing private cycle owner, not a parallel ledger.

## Source, deployment and maintenance

The [source inventory](python-specialists/sources.lock.json) records immutable
upstream commits, licenses, original Git blobs/SHA-256 hashes, complete packaged
file hashes and local patches. Each bundle's `UPSTREAM.md` explains adaptations;
its `LICENSE.upstream` retains the upstream license. The two Trail of Bits
adaptations remain CC-BY-SA-4.0, separately from the repository license.

Maintainers review the complete proposed upstream bundle and all local patches
before updating the pin. Reverse/reapply patches and compare complete inventories
using the source repository's `tests/test_python_specialists.py`. Review changed
policy in supporting references as well as entrypoints. Retain all selected
resources; optional external skills stay optional. The source bundles exclude
plugin hooks/shims and external eval runners; upstream documentation describing
those components does not mean they are installed.

Deploy through the existing distribution workflow: compare relevant live copies
with their prior managed source, validate isolated exact-target rendering, preview
the four bundles plus this reference, its inventory directory and the Python
module, then apply only those targets with scripts excluded. Compare complete
bytes/file sets and require an empty second-apply diff. Preserve unrelated skills
and divergent live edits. Updating these skills does not install target-project
tools or change provider settings.

Filesystem installation, native client discovery and useful task behavior are
separate claims. Verify discovery when the client exposes it; otherwise report
that observation as unavailable and note any required client refresh. Rollback
uses the complete prior reviewed bundles, inventory and routing from Git through
the same exact-target preview, preserving divergent files before replacement.
