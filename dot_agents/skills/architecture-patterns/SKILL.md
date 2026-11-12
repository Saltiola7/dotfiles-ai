---
name: architecture-patterns
license: MIT
description: Design and review backend boundaries, dependency direction and Clean, Hexagonal or DDD tradeoffs when system structure changes. Use for actual architectural decisions or explicitly scoped architecture assessments.
---

# Architecture Patterns

Choose the smallest structure that addresses demonstrated change cost, coupling,
consistency or ownership concerns. Inspect the current design, callers, contracts
and project decisions first. A modular monolith, direct function or existing
framework model may remain the best design. A pattern name does not justify
new layers, interfaces, services, repositories or duplicated models.

Preserve project-selected runtimes, frameworks, storage, dependencies, validation
and compatibility. Examples illustrate alternatives, not a mandatory layout or
production recipe. Existing authorization persists; this guidance alone does not
install tools, run services, migrate code or expand remediation scope. The current
primary owns synthesis and DBSCTR/QA ownership remains unchanged. Attribution and
reviewed adaptations are in [UPSTREAM.md](UPSTREAM.md).

## Decisions this guidance supports

- Untangle business policy from HTTP, persistence or external effects when the
  coupling creates concrete change or testing costs.
- Establish a coherent model and ownership boundary before considering service
  extraction; a bounded context can remain a package in one process.
- Review dependency cycles and public interfaces using actual import/call paths.
- Choose consistency boundaries and domain vocabulary from real invariants and
  consumers, rather than folder counts or class naming.
- Compare an incremental refactor with retaining the existing design.

## Pattern options and their costs

| Option | Useful when | Cost to justify |
|---|---|---|
| Clean/Onion architecture | Business rules need an explicit dependency boundary from delivery and infrastructure | Additional mapping, indirection and maintenance; framework-free models are a selected tradeoff |
| Hexagonal ports/adapters | Actual variation or effect ownership benefits from a stable interface | A function, callable, Protocol or module API can suffice; an abstract base class at every boundary is unnecessary |
| DDD bounded contexts/context mapping | Different business models, language or owners need explicit integration contracts | Translation and governance; separate deployment and an anti-corruption layer are not automatic consequences |
| Entities/value objects/aggregates | Identity, value semantics or consistency invariants need an explicit model | Model complexity and persistence behavior; validate against actual business and storage contracts |
| Domain events/outbox | A real cross-boundary effect or reliable publication requirement exists | Ordering, deduplication, recovery, schemas and operational ownership; events do not create reliability by themselves |

For selected inward-dependency designs, keep policy independent of concrete
infrastructure and put wiring at the composition root. Define the actual allowed
edges for this project; standard-library imports and suitable pure dependencies
are not layering violations. Avoid introducing a shared miscellaneous module
merely to hide cycles.

## Read examples progressively

Read [detailed patterns](references/details.md) for a selected Clean/Hexagonal
boundary, port/adapter testing or value/aggregate example. Read
[advanced patterns](references/advanced-patterns.md) for context maps, selected
service extraction, Onion comparison, composition-root lifetimes, outbox or
cycle analysis. Do not read or apply every example for an ordinary local edit.

## Review and validation

Trace representative change paths, effects, invariants, imports and consumers.
Explain the observed friction, proposed boundary and retained alternative, costs,
compatibility and the evidence needed. A static import diagram, file-size rule or
personal navigation preference alone is not a confirmed defect.

Use pure-policy tests or in-memory adapters where they express the contract, and
selected-engine/framework integration tests for semantics fakes cannot establish.
A mocked repository does not prove isolation, SQL constraints, mapping or replay
safety. Keep meaningful existing tests and project-selected runner/checker policy.

When adopted architectural rules need repeatable evidence, use the project's
existing architecture checks or relevant `python-architecture-fitness` guidance
if available. Do not install a linter or turn example dependencies into gates.
A graph is an observation, not proof of every runtime dependency or good design.

An explicitly requested audit is report-only by default. Return source-backed
findings and bounded alternatives to its current primary; do not start a second
audit, issue workflow or refactor. Loading this skill does not select DDD, a
microservice migration, a framework rewrite or transactional guarantees.

## Optional upstream reading

These are related sources, not required installed dependencies:

- [Microservice patterns](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/backend-development/skills/microservices-patterns)
- [CQRS implementation](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/backend-development/skills/cqrs-implementation)
- [Saga orchestration](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/backend-development/skills/saga-orchestration)
- [Event-store design](https://github.com/wshobson/agents/tree/7e2fb559cf4b824b27f1fec49fe88f7511066d26/plugins/backend-development/skills/event-store-design)

Ordinary loading uses this reviewed bundle, not moving upstream instructions.
