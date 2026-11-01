# Python Audit Report Contract

Scale detail to the repository. Lead with actionable findings and recommended
starting work, then show enough coverage and evidence to assess the conclusions.
An audit can complete with debt; completion never means every check passed.

## Scope and evidence

Identify the repository/snapshot, commit and reviewed dirty/untracked overlay,
scope boundaries, supported runtimes, public contracts and owning environments.
Record relevant project policy and the installed specialist revisions used when
available. Avoid copying secrets or unrelated private artifacts into the report.

Show component/lens coverage with concrete reviewed paths and dispositions:

| Component / environment | Lens | Review status | Evidence and limits |
|---|---|---|---|
| Actual component | One of the eleven language or applicable boundary/database lenses | reviewed / sampled / unavailable / not applicable | Paths, samples, exclusions, unreviewed units and rationale |

Inventory totals, actual inspected coverage, typing-analysis coverage and test
coverage have different denominators. State each denominator used; zero units is
not 100%. Describe generated/vendor/archive decisions and unsupported notebooks.
Do not label the whole repository reviewed when only selected files were read.

List actual configured checks and their command/environment/scope, exit status,
result and limitations. Separate executed checks from proposed checks. Missing,
failed, skipped, unavailable or not-run evidence must stay visible. Use existing
QA capability/Gate Result conventions when an active cycle needs structured
results; do not introduce a second lifecycle state format.

## Findings

Give findings stable local IDs and one primary category:

- **Confirmed defect:** reproducible failure or a concrete source/contract
  contradiction. Explain the observed trigger and consequence.
- **Design recommendation:** a maintainability tradeoff supported by actual
  coupling, responsibilities or change cost; label the judgment as advisory.
- **Modernization option:** compatible improvement or explicit migration proposal.
  State minimum runtime, policy/consumer impact, costs and alternatives.
- **Performance hypothesis:** static concern or incomplete measurement that still
  needs representative validation. Use a measured-performance finding only when
  workload, environment, raw evidence and uncertainty support that description.

For each, include source location, relevant lens(es), evidence versus inference,
impact/priority and confidence with reasons, proposed change, retain alternative
where useful, compatibility/behavior constraints and a validation plan. Attach
actual commands/results or counterexamples when available. Do not call a
heuristic threshold violation, older supported syntax or library absence a defect.

Property-testing recommendations name a meaningful invariant, input strategies
and useful boundary cases. Performance recommendations specify the baseline,
representative workload/environment, metric and correctness checks still needed.
No invented speedups, acceptance passes or universal coverage thresholds.

## Ordered refactor batches

For each recommended batch, state goal, finding IDs, expected components/files,
dependencies, estimated effort and risk with assumptions, preserved behavior and
compatibility, and focused validation/acceptance. Put prerequisite characterization
or measurement before a change that depends on it. Prefer small useful changes
over a repository-wide rewrite or a permanent dual-tool migration by default.

End with sound choices to retain, unresolved questions, coverage/evidence gaps,
and the audit disposition: complete for the declared reviewed scope, partial, or
not applicable. Scope-complete with failures/debt is valid; unsupported claims of
full review or clean validation are not. Present the next bounded decision for
the developer; implementing it is a separate authorized task.


When data-access code exists, include boundary and selected engine/platform
coverage in the same report. Reconcile database subreports by root cause and
owner; separate static/live evidence and retain unsupported engine gaps. Service
retry/resource/telemetry lenses may be not applicable with concrete reasons.
