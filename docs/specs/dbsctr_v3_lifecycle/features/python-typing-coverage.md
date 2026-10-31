# Python typing coverage through DBSCTR

Discovery only; no implementation or activation claim. Context: `dbsctr_v3_lifecycle`;
[Profile](../PROFILE.md). Owner: lifecycle maintainer.
Risk: elevated because shared instructions govern validation across projects.

## Scope and ownership

Core DBSCTR must apply the project's selected Python checker at every relevant phase.
For an explicitly selected migration, ty is the intended primary typing authority.
Discovery establishes scope and acceptance; DBSCTR carries them through development;
QA reports coverage and findings. Other projects retain their own tool selection.

Update existing `dot_agents/skills/dbsctr/SKILL.md`, `dot_agents/skills/qa/SKILL.md`,
and `dot_agents/skills/discovery/SKILL.md`, with existing specs and contract tests.
No new skill, module, reference, typing subsystem, gate, schema, shared wrapper or
mandatory installation. The Python module stays unchanged; consumer changes stay project-owned.

During migration, an existing checker such as mypy may remain under explicit
consumer policy. Comparisons, gating roles and retirement criteria live in that
project's profile, not permanent dual-checker choreography in the shared kernel.
After migration acceptance, remove transitional prompting in a bounded follow-up;
core guidance retains the generic obligation to honor current project authority.

## Profile and coverage contract

Discovery records checker command/version/configuration and authority, Python
targets, environments, dependencies, full artifact population, evidence location,
and setup/remediation acceptance. Missing decisions prevent readiness; QA does not install tools.

When the user selects 100% coverage including tests and notebooks, the population
includes all owned Python production code, tests, Python fixtures, scripts and
notebooks. Inventory generated, vendored, archived and unsupported artifacts
explicitly; disposition follows ownership and approved scope, not diagnostic
volume. Exclusions require rationale and authority and never count as checked.
Do not silently narrow scope through ignore rules, old checker paths or a
convenient `src/` target. Include relevant new files as well as tracked files.

Map nested projects and independent scripts/notebooks to their owning environments;
one root invocation is insufficient where targets or dependencies differ. Python
notebooks, including marimo `.py`, remain Python artifacts. Other formats need
supported checking or verified cell-to-source mapping; unsupported inputs remain gaps.
Classify structural diagnostics separately. Type checking does not authorize execution.

| Claim | Evidence required | Limit |
|---|---|---|
| Scope accounting | Every artifact has an owner, environment and disposition; selected and excluded counts reconcile | Does not prove analysis occurred |
| Analysis coverage | Every selected artifact reached appropriate analysis; skipped inputs, incomplete runs and environment/import limitations remain visible | Does not prove clean diagnostics or precise types everywhere |
| Diagnostic cleanliness | Actual findings and statuses under declared configuration, with suppressions and exceptions disclosed | Does not prove the intended population was checked |

Report counts with the independent denominator; an empty population is not applicable,
not 100%. Exit status, configured paths or checker counts alone do not prove coverage.
Findings can coexist with complete analysis; syntax or environment failures preventing
analysis remain gaps. Missing evidence is not zero findings. Source coverage proves
neither test coverage nor freedom from `Any`.

## Phase obligations

Use existing gates and order. Run the checker when type-bearing artifacts change
or typing evidence is needed. Check affected dependencies during ordinary development
and the full approved population for full-coverage setup/audit. Explain unchanged
evidence reuse; do not invent runs or repeat scans merely for a phase label change.

| Phase | Obligation and evidence |
|---|---|
| Domain | Inspect domain types, authority, environments and existing findings; check changed type models and record compatibility constraints |
| Behavior | Define typed boundaries, invalid inputs and compatibility scenarios; check changed typed tests/examples when relevant |
| Spec | Check changed signatures, protocols, aliases and stubs; distinguish intentional incomplete implementation from a clean result |
| Contract | Check annotations with runtime boundary validation; preserve contract scenarios because typing alone does not prove runtime validation |
| Test | Check implementation, tests and affected consumers in their environments; report test and typing results separately |
| Refactor | Begin after affected behavior passes; recheck changed types and consumers while preserving contracts |
| Review/Integrate | Reconcile final scope, authority, environments, suppressions, conflicts and CI against reviewed source; verify the full population when required |
| Maintain/Retire | Revalidate checker/runtime/configuration upgrades, admit new source to coverage, and remove temporary legacy guidance after migration acceptance |

**Text Equivalent:** Establish constraints, check interfaces, verify implementation
and preserved behavior, then reconcile coverage. Reuse evidence only while source,
configuration, environment and authority remain applicable. Source: this matrix.
Owner: lifecycle maintainer. Update trigger: phase or evidence obligations change.

## Setup first, then bounded remediation

Establish inventory, environments, execution and truthful reporting before cleanup.
Build a conflict census before refactors: code defects, annotation/stub issues,
dependency/environment problems, checker limitations or semantic differences,
notebook structure, and unresolved cases. Comparisons remain consumer-owned;
agreement is not proof of correctness.

LLM-proposed fixes cannot infer permission from diagnostics to change behavior,
weaken validation or broaden refactoring. Verify runtime contracts and dependency
APIs with focused tests or minimal reproductions where needed. Preserve uncertainty;
route material behavior changes into bounded DBSCTR work after the census.

Reject blanket ignores, broad exclusions, unjustified `Any`, unchecked casts,
diagnostic disabling, exit-code masking, or automatic green baselines. Narrow
suppressions need rationale, scope and review condition; suppressed concerns are
not evidence of a pass. Retain original failures and subsequent replacement evidence.

Setup may pass when inventory, environments, execution and census meet their contract
while diagnostics remain failed or explicitly advisory. That cannot pass a required
typing gate. Existing Gate Ledger and exception rules remain; setup success is no waiver.

## Scenarios, validation and delivery

| Given / when | Required outcome |
|---|---|
| Full scope includes tests/notebooks but checker defaults omit them | Expand consumer execution and reconcile inventory; a partial run cannot satisfy full coverage |
| Nested environments or notebook formats cannot be analyzed | Report incomplete analysis explicitly, even with complete scope accounting |
| Setup is complete but findings remain | Accept only the setup concern; retain actual diagnostic failure and applicable gate requirements |
| A proposed repair changes runtime behavior or hides findings | Preserve evidence; classify the conflict and route bounded remediation rather than manufacture green |
| Relevant source, imports, configuration or environment changes | Refresh affected evidence and required full-scope reconciliation |
| Selected migration completes | Remove temporary legacy-checker prompting; use the project's current authority |

Add contracts for each changed skill and existing consumers: selected authority,
phases, full scope, environments, truthful results and setup/remediation separation.
Run existing publication/instruction checks before broader tests. Shared artifacts
contain portable policy and synthetic examples; consumer evidence stays project-owned.
Source tests do not prove activation or consumer readiness.

## Visual Evidence

| Concern | Decision and canonical evidence |
|---|---|
| Boundary | required: Scope and ownership responsibilities above and handoff table below |
| Interaction | required: Phase obligations matrix above |
| State | required: acceptance handoff table below |
| Data/trust | required: acceptance handoff table below |
| Schema | not_applicable: existing profile and Gate Ledger are reused |
| Dependency/deployment | not_applicable: no new runtime topology or deployment mechanism |
| Quantitative | not_applicable: no measured comparison; coverage definitions are evidence contracts |

| From | Guard and permitted handoff | To |
|---|---|---|
| Shared maintainers | Portable instructions only; no private consumer evidence | Project Discovery and phase execution |
| Project profile | Scope, environments and authority resolved | Ready execution plan, not an analysis pass |
| Checker execution | Complete population reconciled; gaps and findings preserved in project evidence | Separate setup, analysis and diagnostic outcomes |
| Conflict census | Classification and existing scope authority permit bounded repair | Remediation with runtime contracts preserved |
| Verified migration | Project acceptance met; temporary guidance retirement scoped | Current primary checker policy |

**Text Equivalent:** Shared policy flows to projects; project evidence stays local.
Resolve scope, separate setup from diagnostic success, classify before repair,
and retire temporary prompting after acceptance. Source: contracts above; owner:
lifecycle maintainer. Update trigger: ownership, evidence or authority changes.
