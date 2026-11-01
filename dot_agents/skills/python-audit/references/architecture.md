# Focused Python architecture assessment

Use within the same Python audit primary and report. Establish scope before
loading techniques; start with architecture-patterns, python-project-structure,
python-architecture-fitness and python-design-patterns. Other lenses follow actual
async, database, compatibility, resource or reliability concerns.

## Establish intent and actual structure

Read accepted ADRs/specs, public contracts, entrypoints, package/build metadata,
composition roots, tests and existing architectural checks. Separate declared
architecture, inferred intent and proposed alternatives. Folder names, framework
conventions and generic API/Service/Repository examples do not establish a project
rule. Preserve supported versions and existing tools.

Build a source-backed map of relevant contexts/components, responsibilities,
entrypoints/callers, public imports and integration boundaries. Trace representative
end-to-end flows and concrete dependency witnesses, including indirect paths,
re-exports, registration/plugins, generated/type-only imports and import-time I/O.
Consult an existing graph where useful; verify edges against source and disclose
stale/missing graph coverage. Do not import the application merely to discover it.

| Component/boundary | Declared intent and owner | Actual source/callers | Evidence and limits |
|---|---|---|---|
| Concrete paths and interfaces | Accepted rule, inferred intent, or absent decision | Import/call chain, composition seam, public consumer | Reviewed/sampled scope, dynamic or unreviewed edges |

Map state, resource and transaction ownership where they influence correctness;
an import graph alone cannot establish atomicity, replay safety or runtime effects.
For actual database concerns return a bounded database subreport through existing
routing. For mixed-language interfaces inspect relevant schemas/consumers and
state what remains unreviewed; this is not automatic whole-stack qualification.

## Judge choices against needs

Use actual change cost, coupling, cohesion, domain invariants and required quality
attributes. A modular monolith, flat library, functions or framework-native design
can be the right retained choice. Compare alternatives and explain their costs,
including public import/API compatibility, data evolution, deployment ownership
and test seams. Do not require DDD, microservices, an interface at every boundary,
repository wrappers or duplicate ORM/domain models merely to match a pattern.

Distinguish an accepted-rule contradiction from an advisory design recommendation.
For the former name the rule, authority, concrete witness chain and consequence.
For inferred intent label uncertainty and the decision that needs confirmation.
Proposed architectural contracts are options, not existing validation failures.
A cycle or large file is a review signal; show concrete consequences before
recommending a structural change. Static topology is not a performance measurement.

## Validate and propose a bounded roadmap

Use the fitness lens to inspect actual configured architectural checks and their
roots, environments, exclusions and limits. Keep source review, graph construction,
checker execution and test coverage distinct. Missing tools remain gaps; no installs,
application imports, generated configuration, ADR edits or new gates follow from
an audit. Inspect custom checker code/cache effects before using existing execution
authority. QA retains actual result/status ownership.

Return the normal report with chosen focus, component/boundary map, accepted versus
inferred intent, concrete findings, useful retain decisions and evidence gaps.
For each proposed batch specify owning component, prerequisite characterization,
expected boundary change, consumer compatibility, alternatives/tradeoffs and
focused validation. Put contract agreement or measurement before dependent work.
Recommend prospective dependency rules only with their intended authority, scope
and explicit exception policy. Avoid broad rewrites or architecture scores without
a defensible measurement model.

Complete means complete for the declared reviewed scope; samples, missing guidance
and unreviewed components remain visible. A graph or checker with no findings does
not prove good architecture. Hand selected remediation to DBSCTR using the same
artifacts and roadmap; do not start a second audit, ledger or automatic fixes.
