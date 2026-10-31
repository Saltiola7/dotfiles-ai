# Conditional Python Specialists

The later [platform/language expansion](platform-specialists.md) adds async Python
and modernization review and centralizes the shared loading/return contract in
`references/specialist-selection.md`. This feature retains the original four
bundles and their provenance owner.

## Domain and Engineering Profile

The existing lifecycle Engineering Profile applies. This feature adds four
reviewed, independently discoverable Python skill bundles and conditional routing
from the Python module. Risk is elevated because shared instructions influence
future development. Applicable modules are Python and ML/AI; distribution owns
the source-to-shared-skill projection. No new product journey or runtime service
is introduced.

| Owner | Responsibility |
|---|---|
| DBSCTR core | Scope, phase order, lifecycle state, approvals and gate decisions |
| Python module | Python obligations and evidence-driven specialist selection |
| Project Engineering Profile | Runtimes, tools, dependencies, compatibility and acceptance criteria |
| Specialist bundle | Bounded technique, recommendations and supporting evidence |
| QA | Execute project-selected validation and report capability evidence |
| Distribution | Reviewed pins, complete licensed bundles, deployment and recovery |

The selected specialists are `modern-python`, `python-design-patterns`,
`python-performance-optimization` and `property-based-testing`. A specialist is
guidance, not a coordinator, validation authority or permission grant. Source
availability, filesystem installation, live discovery and demonstrated usefulness
are distinct claims. Existing project policies outrank specialist defaults.

The initial scope excludes a new toolkit coordinator, automatic upstream
updates, tool installation, plugin hooks, release-driven architecture-debt
audits and unrelated changes to project CI or toolchains. Required outcomes
retain their existing evidence requirements even when a preferred skill is absent.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: ownership table above |
| Interaction | required: selection and return table added with interfaces |
| State | not_applicable: no new state machine; existing lifecycle retains ownership |
| Data/trust | required: source and evidence transfer table added with contracts |
| Schema | not_applicable: source inventory is provenance, not a new domain entity |
| Dependency/deployment | required: delivery dependency table added with contracts |
| Quantitative | not_applicable: no measured performance claim or universal threshold |

**Text Equivalent:** DBSCTR owns the cycle; the project owns policy; the Python
module selects a relevant specialist; the specialist returns scoped advice and
evidence to the primary; QA validates applicable outcomes. Distribution installs
reviewed instructions independently of target-project tools. Canonical sources
are this feature, the Python module and the reviewed source inventory. Owner:
lifecycle and distribution maintainers. Update these tables whenever represented
selection, authority, evidence or delivery boundaries change.

## Behavior

- Given an ordinary Python bug fix with no affected architecture, invariant,
  performance concern or tooling change, the primary proceeds without loading
  all specialists or inventing an additional review gate.
- Given changed responsibilities, component boundaries, dependency direction or
  abstractions, the primary loads `python-design-patterns` before settling the
  relevant design, and reassesses during a structural refactor.
- Given a parser, serializer, normalizer, validator or state transition with a
  meaningful invariant, the primary loads `property-based-testing` while defining
  behavior/contracts. It may conclude property testing adds no value; it does not
  redesign working code solely to force Hypothesis into the project.
- Given a reported slowdown, explicit performance requirement or measured
  bottleneck, the primary loads `python-performance-optimization`, establishes
  an appropriate baseline and compares equivalent workloads after changes.
- Given new packaging/tooling setup or an explicitly selected tooling migration,
  the primary loads `modern-python`. Existing mypy, Pyright, Poetry, runtime floors,
  coverage policy and scheduled CI remain authoritative unless their change is
  part of the authorized work.
- Given newly discovered evidence, the primary selects only newly relevant
  guidance and revisits the affected existing phase. Routine skill loading does
  not ask for repeated approval or create a new coordinator/subagent by default.
- Given a missing preferred skill, the primary reports that limitation and uses
  equivalent guidance if sufficient. Missing required evidence remains an
  explicit capability gap governed by the existing Gate Ledger.
- Given a fresh installation, exact-target application reproduces every selected
  bundle and required resource without installing tools or activating plugin hooks.
- Given a changed source bundle or divergent installed copy, provenance/byte
  verification exposes the mismatch; deployment preserves unrelated live edits.
- Given a skill update, maintainers review the complete pinned revision and local
  adaptations before source inventory and deployed files change together.

## Interfaces

`dot_agents/skills/dbsctr/modules/python.md` contains a small conditional routing
table. `references/python-specialists.md` supplies the invocation/result and
maintenance contract; the existing `references/python.md` retains its separate
secret-settings purpose. Each specialist remains a sibling skill with its full
upstream resource tree, license and `UPSTREAM.md` attribution.

| Signal | Selection | Return to primary |
|---|---|---|
| Changed architecture or abstractions | `python-design-patterns` at Domain/Spec or structural Refactor | Tradeoffs, affected boundaries and justified simplification |
| Meaningful input/state invariant | `property-based-testing` at Behavior/Contract/Test | Property, generators/counterexamples or reason not to use PBT |
| Performance problem or requirement | `python-performance-optimization` before optimization | Baseline, equivalent comparison, correctness and measurement limits |
| New setup or selected tooling migration | `modern-python` at Profile/Spec | Compatible setup/migration decisions and validation plan |

Selection uses current task evidence and remains revisable. The primary uses the
native skill loader or reads the installed `SKILL.md` when no loader is exposed,
then only relevant supporting resources. A skill need not run in a subagent.
Outputs identify scope, applicable project policy, findings or recommendations,
supporting evidence, affected artifacts and unresolved limitations. They do not
write a second Gate Ledger or imply that the primary accepted a recommendation.

The source inventory lives at
`dbsctr/references/python-specialists/sources.lock.json`. Schema 1 records each
package's immutable repository commit, selected source root, license, original
Git blob identities/SHA-256 hashes, complete packaged file hashes, local patch
hashes and adaptation rationale. Unified patches live under the same reference
directory and reconstruct the original selected files when reversed. A clean
checkout supplies all deployment bytes offline; network access is needed only
for a deliberately reviewed upstream update.

`tests/test_python_specialists.py` validates complete inventories, reversible
adaptations, local resource closure and exact-target isolated delivery. Existing
lifecycle/publication checks cover the changed instruction surfaces. Small
independent task evaluations compare baseline and candidate decisions for
selection, policy preservation and evidence quality; they do not claim broad
model effectiveness from a few cases.

**Text Equivalent (interaction):** The primary recognizes a concrete signal,
loads the selected installed guidance at the affected checkpoint, receives a
bounded result and decides how it changes the existing artifacts. QA remains the
evidence authority. The table is canonical for trigger/checkpoint relationships;
maintainers update it with corresponding routing changes.

## Contracts and Validation

- User scope and the project Engineering Profile control supported runtimes,
  selected tools, dependencies, compatibility, test strategy and acceptance
  thresholds. Recipes and numeric heuristics are examples, not universal gates.
- Loading guidance neither installs tools nor expands scope. Existing task
  authorization persists; ask only about an unresolved material decision or a
  genuinely required permission. Missing preferred guidance does not invent a
  gate; missing required evidence is not a pass.
- Modern tooling recipes apply only when their tools/migration were selected.
  Adapt repeated contrary instructions in supporting references as well as the
  entrypoint. Preserve scheduled CI, dependency constraints and active files;
  remove only confirmed superseded artifacts within the migration scope.
- Property testing preserves project test policy and does not force a new
  library. Profiling preserves correctness, uses authorized workloads and reports
  uncertainty. Specialist instructions do not select a model or reasoning effort.
- Selected typing migrations follow the core typing-coverage contract: establish
  an independent artifact/environment inventory and conflict census, retain actual
  diagnostic results and exit status, and distinguish setup from remediation.
  Specialist recipes cannot establish a green baseline through global rule ignores
  or narrow the approved population to a convenient source directory. Narrow
  suppressions require justification and a review condition.
- Source pins are `trailofbits/skills` at
  `2be6433b39e009cd2b6fd3be1895f6b1faa5af9a` and `wshobson/agents` at
  `7e2fb559cf4b824b27f1fec49fe88f7511066d26`. The two Trail of Bits adaptations
  retain CC-BY-SA-4.0; the other two retain MIT and upstream attribution.
- Preserve all selected upstream skill-root files. Exclude sibling plugin
  manifests, hooks/shims and external evaluation runners. Replace references to
  unselected sibling skills with optional pinned upstream links, not dangling
  installed paths or implicit dependencies.
- Inventory tests compare the entire file set, not only listed entries. Test
  missing, changed, extra and linked files plus reversible patches. No fetched
  content is executed during source acquisition or installation.
- Deployment is exact-target, uses the selected task source and existing machine
  chezmoi configuration, excludes scripts, and follows isolated delivery tests.
  Compare live copies with their prior managed source before replacing them.
  Verify bytes/file sets and an empty second-apply diff. Do not overwrite unrelated
  state or claim live discovery when only filesystem installation was observed.
- Recovery restores complete reviewed bundles plus their matching inventory and
  routing through an exact-target preview. Keep prior Git pins and divergent live
  files; do not delete unrelated skills or downgrade project tools.

| Transfer | Boundary and evidence |
|---|---|
| Pinned vendor source to managed source | Original blob/hash verification, retained license, reviewed patch and packaged inventory |
| Project context to selected specialist | Current provider and task scope; bounded recommendations returned to primary |
| Specialist result to lifecycle artifacts | Primary reconciles findings; QA checks real capabilities; loading is not gate evidence |

| Delivery dependency | Completion evidence |
|---|---|
| Source preparation | Complete inventory, reversible patches, valid entrypoints and resource links |
| Isolated projection | Selected bundle/module/reference bytes match; second apply produces no diff |
| Shared projection | Prior-state comparison, exact-target application and complete byte verification |
| Client use | Native discovery observation when available; otherwise explicitly unverified |

**Text Equivalent (trust and delivery):** Maintainers verify immutable upstream
bytes and review adaptations before managed source is eligible for offline
deployment. The current provider processes only task-authorized context. A
specialist returns evidence to the primary without owning gates. Isolated
projection precedes shared projection, and neither alone proves client discovery
or skill effectiveness. Canonical evidence: inventory, patches, focused tests and
private cycle deployment receipts. Update these tables when source, context,
authority or deployment dependencies change.

Focused authority: `uv run --group test pytest tests/test_python_specialists.py
tests/test_dbsctr_lifecycle.py tests/test_portable_distribution.py`. Run the
original skill creator validator on all four new skill entrypoints. The existing
DBSCTR entrypoint is unchanged. Keep independent behavioral evaluation artifacts
and actual deployment/merge evidence in the cycle; publish only sanitized outcomes.
