---
name: python-modernization-review
description: Review Python runtime/support-floor changes and requested modernization or architectural-debt audits. Identify justified migrations using current version evidence and project compatibility constraints.
---

# Python Modernization Review

Produce an evidence-backed modernization assessment or carry out the explicitly
selected bounded migration through the existing lifecycle. New syntax alone is
not a reason to change working architecture.

## Establish the compatibility contract

Read supported Python versions/implementations, package metadata, runtime images,
CI matrix, dependency constraints, public interfaces and target platforms. Resolve
whether a proposed version is a minimum, an additional target or a deployment pin.
Keep existing package managers, build/check/test authorities and SDK constraints.

Inspect actual runtime/dependency use before describing old-version debt. A
compatibility wrapper can still serve an active caller or platform. Distinguish
owned production code, tests, examples, vendored/generated material and public
consumer commitments.

## Compare current primary evidence

Use the [Python version status](https://devguide.python.org/versions/), selected
version's [What's New and porting notes](https://docs.python.org/3/whatsnew/index.html),
applicable accepted PEPs and official dependency/framework migration documents.
Record source date and target version. Development/nightly documentation is not
proof that a supported stable runtime exposes the same API.

Review relevant removals/deprecations, standard-library replacements, typing and
packaging changes, async/task semantics, native extension/ABI requirements and
platform support. Match each finding to code or dependency evidence. Interpreter,
GIL/free-threading and native-extension behavior must follow the selected target;
do not generalize CPython-specific performance claims to all runtimes.

## Classify before refactoring

| Finding class | Required reasoning |
|---|---|
| Mechanical cleanup | Minimum supported version permits it; affected semantics and callers are preserved |
| Compatibility retirement | All active consumers/platforms have migrated; public support/deprecation commitments are met |
| Semantic migration | Show changed behavior, invalid/edge cases, dependencies and required contract/test changes |
| Architectural opportunity | Identify actual coupling/duplication or operational cost, simpler alternatives and concrete expected benefit |
| Unsupported claim | Keep missing runtime, dependency or workload evidence explicit; do not promote a hypothesis to a finding |

Return priorities with locations, primary-source support, compatibility impact,
expected benefit, effort/risk and focused validation/recovery. Avoid a generic
debt score that conceals different risks or an assumed benefit from adopting the
latest feature. Preserve uncertainty and existing backlog ownership.

## Bounded implementation and acceptance

Routine task authorization persists. For an approved migration, establish a
baseline, make scoped changes and validate affected supported runtimes and
consumers through configured authorities. Do not install a formatter/upgrader or
run broad automatic fixes merely because a recipe names one.

Check typing, tests, packaging/native builds and meaningful performance outcomes
where affected. Static complexity or fewer lines is not measured speedup. Use
`async-python-patterns`, `python-design-patterns` or performance guidance only
when findings actually require them; keep QA as the evidence authority.

Feed accepted findings into the current project artifacts and Maintain/Retire
concerns. Review can recur on runtime/dependency/support-policy changes or an
explicitly selected maintenance cadence; this skill creates no scheduler, updater
or additional lifecycle coordinator.
