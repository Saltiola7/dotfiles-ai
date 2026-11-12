---
name: python-mutation-testing
description: Design or review explicitly selected, bounded Python mutation tests and triage surviving changes against behavioral contracts. Use to evaluate assertion strength; a repository audit alone does not select a mutation campaign.
---

# Python Mutation Testing

Use mutation testing when a concrete behavior matters and passing tests may not
distinguish a plausible wrong implementation. Retain the project's selected test
runner, mutation engine, Python support floor and existing QA policy. Loading
this skill does not install an engine, start a campaign or create a score gate.
DBSCTR owns lifecycle decisions; QA owns configured validation evidence.

## Select the experiment

- In report-only review, inspect existing mutation configuration and assertion
  seams. Propose a small experiment without executing it. For execution, resolve
  the selected module/functions, tests, tool version, environment, process limits,
  time budget and stopping condition from the task and project policy. Ask only
  about a material missing choice.
- Establish a passing, reproducible unmutated baseline for those exact inputs.
  A broken baseline, import mismatch or missing fixture is a harness failure,
  not a test weakness established by mutation.
- Use an isolated, project-approved workspace. Record the source revision and
  any intentional dirty overlay; preserve original files and unrelated edits.
  Inspect how the chosen engine writes source, tests, caches and reports before
  starting it. Never restore the user's source with a broad checkout or reset.

For mutmut-specific configuration and execution caveats, read
[references/mutmut.md](references/mutmut.md). Check installed-version help and
matching primary documentation before using examples; current documentation can
describe features absent from an older project dependency.

## Evaluate what the result proves

Keep raw engine outcomes, semantic triage and budget-limited omissions separate.
For each actionable mutant, retain its identifier, source diff, selected tests,
actual failure or pass output and a reproducible command.

| Observation | Required interpretation |
|---|---|
| Killed | Verify that a relevant behavioral assertion detected the change. Import, fixture or runner errors can be counted as kills by an engine. |
| Survived | The selected tests passed. Find a contract-backed counterexample before proposing a new assertion; survival alone does not prove a defect. |
| Equivalent candidate | Explain why the change preserves behavior over the intended input domain. Keep uncertainty visible; “hard to kill” is not equivalence evidence. |
| No tests / uncovered | Check test selection, import identity, instrumentation and filtering. This does not establish that production code is unreachable. |
| Timeout | Inspect whether the change causes nontermination or whether the harness, resource contention or budget prevented a useful result. |
| Invalid / incompetent / suspicious / crash | Investigate execution validity and infrastructure separately. Preserve the engine's actual label; terminology differs across tools. |
| Skipped / interrupted / not checked | Report incomplete scope, rather than claiming a tested pass. |

If adding a test, express the public contract through an observable result,
failure or state transition. Confirm that it passes on the original and detects
the selected non-equivalent mutant. Avoid assertions about mutant identifiers,
implementation text or incidental logging unless those are actual contracts.
Example tests or properties may supply the oracle; use the existing testing
method rather than introducing another framework solely for mutation testing.

## Report and stop

Report source and environment identity, scope, baseline, elapsed budget, outcome
counts, inspected survivors, proposed assertions and unresolved harness issues.
Define the denominator and exclusions for any score; type-filtered and unrun
mutants are not tests that killed a behavioral change. Do not invent a universal
score target or silently broaden the campaign. Stop at the selected limit,
preserve owned evidence, and verify that the original source remains intact.
