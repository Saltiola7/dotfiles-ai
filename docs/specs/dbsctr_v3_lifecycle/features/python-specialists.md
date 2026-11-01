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
| State | required: audit coverage/disposition table in Audit interfaces; existing lifecycle retains gate ownership |
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

## Repository-wide audit domain

`python-audit` is a standalone assessment entrypoint for existing repositories.
The [Python/data extension](python-data-specialists.md) and architecture extension
below define fourteen assessment lenses plus conditional Python database boundary
and engine delegation. Original six-lens qualification remains historical evidence.
An explicit full audit considers all fourteen assessment lenses, inventories owned
Python across production code, tests, scripts, stubs and notebooks, and returns
evidence-backed recommendations and an ordered refactoring roadmap. It retains
one primary and reuses QA for configured validation. The target repository is
report-only unless the user separately requests artifact writing or remediation.

An audit finding can be a confirmed defect, design recommendation, modernization
option or performance hypothesis. Specialist opinion is advisory evidence, not a
project requirement. The audit can challenge an existing design or propose a tool
or runtime migration while preserving the distinction between a proposal and an
authorized implementation. Findings identify compatibility costs and reasons to
retain a sound existing approach. Audit completion and a clean validation result
are independent outcomes.

The audit composes the fourteen current assessment skills through one primary.
The original six include `async-python-patterns` and
`python-modernization-review`. Async review checks task, cancellation and resource contracts; modernization review owns
runtime/support and architectural-debt assessment using current primary sources.

The wrapper owns scope, lens coverage, deduplication and synthesis. Existing
specialists own techniques, the project owns policy and environments, QA owns
executed validation evidence, and DBSCTR owns subsequent behavior changes. The
existing bundles and their source inventories remain unchanged.

## Behavior

### Audit behavior

- Given an explicit repository-wide Python audit, the primary assesses all fourteen
  assessment lenses and reports actual scope, evidence and a prioritized roadmap.
  Ordinary scoped development does not automatically start this audit.
- Given existing project policy, the audit distinguishes compatible improvements
  from proposals that change tooling, runtime support or public contracts. It may
  recommend a change with tradeoffs; the recommendation does not authorize it.
- Given a static performance concern without representative measurements, the
  report labels a hypothesis and proposes validation, without claiming a measured
  bottleneck, speedup or performance acceptance.
- Given useful input/state invariants, the audit proposes concrete properties and
  generators; missing Hypothesis alone is not a defect. Suitable example tests
  and sound existing architecture can be explicit retain decisions.
- Given a newer Python feature, the report checks the supported runtime floor,
  verifies version/support claims against official sources when available, and
  separates compatible modernization from a proposed floor increase.
- Given nested projects, notebooks, dirty or untracked source, the audit records
  the reviewed snapshot and owning environments. Inventory is distinct from
  inspected coverage; sampling and unreviewed units remain visible.
- Given a missing specialist, unavailable configured check or unsupported input,
  the audit continues useful available work and reports the gap. It cannot claim
  complete all-lens coverage or a passing validation authority it did not observe.
- Given report-only audit intent, the primary produces findings and refactor
  batches without source edits, auto-fixes, dependency installation or tool
  migration. File output follows user-selected artifact authority; remediation
  follows a separate bounded task and applicable DBSCTR gates.

### Development selection

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

## Audit interfaces

The new bundle is `dot_agents/skills/python-audit/`, containing `SKILL.md`,
`agents/openai.yaml`, `references/report.md` and the on-demand
`references/architecture.md`. The entrypoint resolves the fourteen current
assessment skills through the native catalog or their managed sibling paths. It loads entrypoints for assessment and relevant resources progressively;
it does not duplicate their bodies or change their pinned files. Existing QA is
the validation owner. A short link in `references/python-specialists.md` exposes
the explicit audit route without changing ordinary development selection.

Example request: `Use $python-audit to audit this repository across all fourteen Python/architecture
lenses and propose prioritized refactor batches.` The repository defaults to the
current target; an explicit package or concern narrows the reported scope.

The report identifies the source commit and dirty-overlay treatment, supported
runtimes and environments, inventory/dispositions, per-component lens coverage,
configured check results, deduplicated findings and an ordered roadmap. Each
finding includes location, category, evidence, impact, confidence, proposed change,
tradeoffs, compatibility and validation. Effort estimates are labeled estimates.
Output defaults to the conversation; saving a report uses the user's requested
path or existing project artifact authority. Audit intent does not create tickets
or a new repository-root documentation hierarchy.

| Handoff | Owner and output |
|---|---|
| Project source and policy to inventory | Primary records reviewed snapshot, artifact population and owning environments |
| Inventory to specialist assessment | Same primary considers fourteen lenses in full mode or the architecture-focused subset; bounded read-only helpers may report independent evidence |
| Configured authorities to findings | QA reports actual scope, child results and unavailable capabilities |
| Findings to roadmap | Primary deduplicates root causes and separates defects, recommendations, migration options and hypotheses |
| Roadmap to implementation | User selects bounded work; existing DBSCTR handles applicable behavior changes |

| Audit disposition | Required report meaning |
|---|---|
| Complete for declared scope | All selected units/lenses assessed or explicitly justified as not applicable; debt and validation failures can remain |
| Partial | Sampled/unreviewed units, missing lenses or unavailable evidence limit the stated assessment; do not claim full repository coverage |
| Not applicable | No owned Python in the declared scope; zero units is not 100% coverage |

**Text Equivalent (audit):** The primary inventories project-owned source, uses
the fourteen assessment techniques and QA results, then returns a report and roadmap.
The user selects implementation separately. Audit disposition describes assessment
coverage, while validation retains its actual result. Canonical source: these
tables and the report reference. Owner: lifecycle/skill maintainer. Update when
audit scope, evidence fields or handoff responsibilities change.

## Contracts and Validation

- The explicit full audit considers all fourteen installed entrypoints as assessment
  lenses; loading a recipe does not select its migration or authorize execution.
  Missing lenses stay visible and preclude a complete all-lens claim.
- Inventory covers owned Python, stubs, tests, scripts and notebooks with nested
  environments and generated/vendor/archive dispositions. Record actual inspected
  coverage per component/lens; sampled units and unchecked cells remain gaps.
  A clean configured check does not prove architectural review or full coverage.
- Opinionated recommendations need concrete source evidence, tradeoffs and a
  retain alternative where appropriate. Existing tools, older supported syntax,
  example-only tests or a heuristic threshold violation are not defects alone.
- Version-specific modernization records its minimum runtime and compatibility
  cost. Current feature/support assertions use official Python/tool sources or
  remain explicitly unverified. Do not fetch moving skill bodies during an audit.
- Performance hypotheses remain distinct from representative measurements and
  acceptance. Property-testing proposals identify meaningful invariants and input
  strategies without treating library absence as a failure.
- Audit output defaults to the conversation. Run only existing authorized checks
  through QA, without auto-fix flags or source/dependency/environment mutation.
  Notebook execution, new tools, production profiling and expensive workloads
  require their own applicable authority. Missing evidence remains a limitation.
- Roadmap batches name affected components, behavior/compatibility constraints,
  dependencies, effort/risk assumptions and validation. The audit does not start
  implementation, invent Gate Exceptions or create a second lifecycle ledger.
- Validate complete isolated installation of the wrapper and its actual resource
  dependencies, file/link closure and idempotency. Forward-test a realistic audit
  plus missing-dependency/coverage limits independently; retain synthetic reports
  privately and make no broad effectiveness claim from these cases.
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

Focused authority: `uv run --group test pytest tests/test_python_audit.py tests/test_python_specialists.py
tests/test_dbsctr_lifecycle.py tests/test_portable_distribution.py`. Run the
original skill creator validator on the six Python specialist entrypoints and
the audit wrapper. The existing DBSCTR entrypoint is unchanged. Keep independent
behavioral evaluation artifacts
and actual deployment/merge evidence in the cycle; publish only sanitized outcomes.


## Architecture assessment extension

### Domain and ownership

Architecture assessment for Python projects remains a mode of `python-audit`.
The default full assessment considers all current language/architecture lenses;
a focused architecture request considers system boundaries, package organization,
component design and architectural fitness first. Other techniques enter only
when the actual boundary or contract needs them. Reusable `architecture-patterns`
may help non-Python work, but Python audit does not claim full cross-language coverage.

Add `architecture-patterns` for Clean/Hexagonal/DDD and context/dependency decisions,
`python-project-structure` for packages/public import surfaces, and locally authored
`python-architecture-fitness` for accepted dependency-rule checks and their limits.
Existing `python-design-patterns` retains component responsibilities and composition.
Project policy defines accepted architecture; inferred intent and generic patterns
remain advisory. No pattern mandates layers, services, repositories, duplicate
ORM/domain models, a runtime increase or a new checker.

The audit primary owns snapshot, coverage, findings and one refactor roadmap.
Specialists own techniques, QA owns configured evidence, and DBSCTR owns later
remediation. Default report-only assessment does not write ADRs, import contracts,
configuration, tickets or fixes, execute target imports/notebooks, install tools
or authenticate external systems. Existing execution authorization remains usable.

This cycle builds on the reviewed Python/data source and reconciles merged router/
infrastructure guidance, preserving both source histories and all gate ancestry.
It does not remediate unrelated pending pull requests or their validated findings.

### Architecture behaviors

| Given / when | Required outcome |
|---|---|
| A full Python audit is requested without a narrower focus | Consider fourteen current assessment lenses and applicable boundaries; keep coverage/evidence gaps visible |
| Architecture-only review is requested in natural language | Load three architecture lenses plus component design first; other techniques follow actual evidence, not a full automatic tooling/runtime audit |
| An accepted dependency rule has a concrete contrary source path | Report the rule, witness chain, owning boundary and consequence; distinguish source observation from checker execution |
| A cycle or layering preference has no accepted project rule | Explain concrete maintenance cost and alternatives as advisory design, not a fabricated contract violation |
| A small flat library or modular monolith already meets needs | Retain simple design; no mandatory services, DDD layers, interfaces or checker installation |
| Existing checker is missing, unavailable or configured with exclusions | Continue bounded source review and disclose guidance/check/coverage limits; no invented pass |
| Re-exports, dynamic plugins, generated or type-only imports affect the boundary | Trace relevant actual paths and expose static-check limitations |
| Python interacts with other languages | Inspect relevant interface consumers and disclose unreviewed scope; no full cross-language architecture claim |
| No Python is present | Explain Python-audit scope and use reusable architecture guidance if sufficient, without mislabeling a full Python audit |
| Audit identifies refactoring or proposed contracts | Return one ordered roadmap; no automatic source/ADR/config changes or second lifecycle ledger |

### Architecture interfaces and visual evidence

The existing Python module owns three new conditional trigger rows. Existing
Python method notes own technique distinctions and immutable source inventory
links. Two complete upstream bundles use existing schema 1 provenance at
`dbsctr/references/architecture-sources/sources.lock.json`, retaining MIT notices,
original SHA-256/Git blobs/modes and reversible per-file patches. The local fitness
skill has one on-demand contracts reference; no helper, installer or dispatcher.

`python-audit/SKILL.md` chooses full or architecture focus before lens loading.
Natural-language invocation: `Use $python-audit to audit architecture only and
prioritize refactors.` This is a prompt, not a CLI flag or new command. The
on-demand `references/architecture.md` defines architecture evidence; the existing
report contract adds actual/declared boundary, witness, tradeoff and contract-plan
fields without creating another report owner. UI metadata exposes both uses.

| Architecture concern | Evidence owner and permitted handoff |
|---|---|
| System/context and dependency design | `architecture-patterns`; options, costs and compatibility at Domain/Spec |
| Package/module/public surface organization | `python-project-structure`; project layout and consumers at Spec/Refactor |
| Component responsibilities/composition | Existing `python-design-patterns`; focused structural technique |
| Accepted dependency contracts and static-check limits | `python-architecture-fitness`; QA executes selected authority at Contract/Test |
| Snapshot, review coverage, findings and ordered work | Same `python-audit` primary; later selected remediation enters DBSCTR |

**Text Equivalent:** System design, packaging, components and fitness are separate
techniques feeding one audit primary and existing QA/DBSCTR. Canonical source:
this table and architecture interfaces; owner: lifecycle maintainer; update when
mode, ownership, resources or handoffs change. This extends the existing Visual
Evidence Plan: Boundary/Interaction/Data-trust/Dependency evidence is required in
this table and the mode/contract text; State uses the behavior/disposition table.
Schema is not applicable because profiles and Gate Ledger remain unchanged;
Quantitative is not applicable because no effectiveness or performance claim is made.

### Architecture contracts and validation

Project-declared architecture takes precedence over generic layer examples.
Distinguish accepted rules, inferred intent and proposed alternatives. Findings
need concrete locations, actual callers/import witnesses, impact/confidence,
compatibility and validation; import topology alone does not establish good or
bad design. Public APIs are not access-controlled by `__all__`. Preserve supported
Python/tool versions, existing libraries and intentional architecture decisions.

Import Linter is an optional example when selected by the project. Report roots,
configuration, selected contracts, direct/indirect semantics, type-only/external
exclusions, dynamic/generated/plugin coverage and cache/environment limits.
Do not execute target imports to discover topology. A configured custom checker
can execute code or write caches; inspect effects before using existing execution
authority. Missing tooling stays a gap, not installation permission. A proposed
rule is not an accepted gate; narrow exceptions need actual authority and scope.

Architecture focus uses relevant configured checks; it does not silently request
full typing, packaging or performance validation. Full-mode coverage retains
existing obligations. Preserve snapshots/dirty overlays and resource privacy.
Return in conversation by default; artifact writes, fixes, environments, services
and external actions require the existing user/project scope.

Validate intentional failing composition before authoring new skills. Verify
complete upstream reconstruction, resource closure, declared mode routing and
isolated exact-target/idempotent projection; run original creator validators.
Independent source-only exercises cover a declared-boundary monolith, a simple
library, focused/full scope and missing guidance/check evidence. Preserve actual
coverage and target bytes; samples do not prove universal routing or effectiveness.
Source reconciliation preserves both published Python/data and current-main
router/infrastructure scopes and revalidates their union before delivery.


## Conditional Python stack and runtime expansion

### Domain and ownership

Add seven reviewed technique bundles: `pydantic`, `polars`, `typer`, `fastapi`,
`atheris`, `secure-python-release-pipeline` and `port-to-free-threaded-python`.
They supplement the existing fourteen generic audit lenses. Framework, dataframe,
fuzzing, release and no-GIL methods apply only to relevant project evidence or an
explicitly selected migration. Installing guidance does not select dependencies,
a framework, a toolchain, a runtime floor, a fuzz campaign or publication.

The Python module owns the canonical conditional selector table. The Data module
routes actual Polars work to the same technique; it does not select a dataframe
engine merely because data is present. `python-audit` keeps one primary, the full
versus architecture-focused scope, and one deduplicated roadmap. Project policy
owns tools, runtime compatibility and contracts; QA owns executed evidence; DBSCTR
owns remediation and applicable Release/Deploy gates. Existing notebook/Rust
selectors already installed from separately owned work remain preserved; this
cycle does not adopt or deliver that separate batch.

Preserve complete selected upstream roots, relevant shared resources, exact
licenses and immutable original identities. The four official framework/data
bundles are MIT; Atheris guidance retains CC-BY-SA-4.0; the two runtime/release
bundles retain Apache-2.0 and their Experimental status. Review adaptations across
supporting resources, including substantive examples, rather than changing only
the entrypoint. No plugin hooks, authentication setup or unrelated skills are
installed. User data, credentials and raw evaluation evidence remain private.

### Behavior

| Given / when | Required outcome |
|---|---|
| An ordinary edit has no selected framework, dataframe, fuzz, release or free-threaded concern | No new specialist is loaded just because Python is present |
| Pydantic validates or serializes an actual external boundary | Preserve coercion/strictness, aliases, invalid inputs and exposed fields; do not replace internal domain models automatically |
| A Polars transformation changes | Check actual schema, lazy execution, joins/null/order and output bounds; schema discovery may perform I/O; preserve selected engine |
| A Typer CLI changes | Preserve commands/options, exit status, stdout/stderr, automation and existing framework/version conventions |
| A FastAPI boundary changes | Check dependency/resource scope, response filtering and streaming; keep blocking work out of asynchronous handlers and preserve selected dependencies |
| A coverage-guided fuzz target is selected | Preserve expected versus unexpected failures, instrument actual target code, bound resources/corpus/output and record crash reproduction; no live or unbounded campaign is implied |
| A package release path is selected | Check source-distribution contents, built artifacts and installation/smoke evidence; publication remains a separately authorized effect |
| A free-threaded target is selected | Check shared state and native dependencies, failed imports, actual GIL state and stress evidence; imports alone do not prove thread safety |
| An explicit full or architecture-focused audit encounters these concerns | Select relevant additional methods within that scope, deduplicate findings and retain fourteen generic lenses |
| Guidance/tools or relevant runtime are unavailable | Continue useful static assessment and disclose missing coverage; never convert missing evidence into a pass |
| Shared live routing contains known notebook/Rust selectors | Preserve those selectors and unrelated bundles during this exact-target deployment |
| Experimental release/no-GIL guidance is consulted | Disclose maturity and verify applicable recipes against project-selected versions and primary authorities |
