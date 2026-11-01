# Conditional stack assessment

Use the chosen full or architecture-focused audit scope. These methods are
conditional additions to the fourteen generic lenses, not mandatory new lenses
for every repository. Read installed entrypoints and only relevant resources;
missing selected guidance remains an explicit coverage gap.

- [Pydantic](../../pydantic/SKILL.md): inspect actual external model boundaries,
  constraints/coercion, invalid inputs, aliases and output field exposure.
- [FastAPI](../../fastapi/SKILL.md): inspect actual route/dependency/resource and
  response/streaming contracts, including blocking calls and caller compatibility.
- [Typer](../../typer/SKILL.md): inspect actual CLI command/argument, exit-status,
  stdout/stderr and automated/noninteractive consumer contracts.
- [Polars](../../polars/SKILL.md): inspect actual lazy/eager execution, schema,
  cardinality, null/order/period and materialization boundaries. Do not run reads or
  planning that accesses data outside the authorized scope just to complete a cell.
- [Atheris](../../atheris/SKILL.md): assess an existing or explicitly requested
  coverage-guided harness, instrumentation, bounded corpus/campaign and meaningful
  crash handling. Finding a parser does not authorize a new campaign or toolchain.
- [Release pipeline](../../secure-python-release-pipeline/SKILL.md): inspect an
  existing or requested package distribution/release path. Separate source-tree
  tests, metadata checks, wheel installation/smoke and publication evidence.
- [Free-threaded Python](../../port-to-free-threaded-python/SKILL.md): inspect a
  selected no-GIL target or explicitly requested compatibility assessment. Check
  shared state, native dependencies, failed imports, actual GIL state and races.
  A proposed runtime migration stays a proposal with costs and validation needs.

Architecture focus limits each method to relevant component, data/state, ownership
and consumer boundaries. It does not expand into full query tuning, framework
replacement, fuzzing or runtime migration. Preserve one primary and deduplicate
root causes with async/resource/resilience, database and Python/Rust techniques.
Project-selected tools, deployment/publication authorization and existing QA gates
remain authoritative. Record Experimental release/free-threading guidance as
advisory input, without turning its examples into accepted project policy.
