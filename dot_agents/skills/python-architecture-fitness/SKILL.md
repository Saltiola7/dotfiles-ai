---
name: python-architecture-fitness
description: Design and review repeatable Python dependency-boundary checks when accepted architecture rules, package relationships or import contracts change. Use as an architecture-audit lens; preserve project-selected checking tools.
---

# Python Architecture Fitness

Turn accepted architectural decisions into useful, repeatable checks. Start with
project instructions, ADRs, existing contracts and affected consumers. Distinguish
an accepted rule from an inferred pattern or proposed improvement; a graph shape
alone cannot establish architectural correctness or a required refactor.

## Review the boundary

Identify package roots, owning environments, public entrypoints, adapters and
cross-context dependencies actually involved. Trace concrete imports and callers,
including re-exports and indirect paths. Record the rule's authority, rationale,
allowed direction, affected population and exceptions before calling a path a
violation. A runtime dependency rule and a type-only dependency rule may differ.

Read [contract techniques](references/contracts.md) for selecting a check,
reviewing its coverage or proposing an Import Linter contract. Import Linter is
one optional implementation, not a mandatory dependency. Existing project rules
and equivalent authorities remain valid. A missing checker is an execution gap,
not proof that the architecture is defective.

For static review, read source and existing configuration. Do not import
application modules, start entrypoints or execute notebooks to discover a graph.
Treat an existing graph as navigation evidence and verify important paths against
source. Disclose unresolved dynamic/plugin/generated dependencies rather than
claiming a complete runtime graph.

## Check only within project authority

Use the existing configured checker and environment when checking is authorized.
Inspect its version, configuration, custom contract code and cache effects first.
An apparently static command can load custom Python contracts or write caches;
source review does not implicitly authorize those effects. Do not install tools,
create or rewrite configuration, add CI gates or broaden exclusions merely to
finish an audit. Reuse explicit task authorization and record unavailable checks.

Keep actual commands, inputs, configuration/version, selected contracts, scope,
exit status, broken/kept results and limitations separate from manual review.
A successful subset cannot establish repository-wide coverage. Do not make a
contract pass by suppressing the observed edge, moving it behind a type guard or
weakening a rule without an independently justified project decision.

## Return decision-relevant evidence

For an accepted-rule violation, give its authoritative rule and a source-backed
witness path, affected consumers, consequence, compatible repair options and a
focused validation plan. For an inferred concern, explain the maintenance cost
and label the recommendation advisory. Cycles, file size or absent layers alone
are not runtime defects. Keep sound simple designs and justified exceptions.

Propose small contracts and refactor batches with owners and compatibility costs;
do not silently turn a proposal into project policy. When called by `python-audit`,
return this boundary evidence and coverage to its primary for one deduplicated
report. Existing QA owns check results and DBSCTR owns later implementation gates;
this technique does not create another coordinator, ledger or audit workflow.
