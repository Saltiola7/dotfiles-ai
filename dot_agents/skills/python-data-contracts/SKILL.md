---
name: python-data-contracts
description: Design or review dataframe schemas, coercion and dataset value invariants at actual Python data boundaries. Use for dataframe validation and contract drift; preserve the selected backend and validation framework.
---

# Python Data Contracts

Start at an actual producer/consumer boundary: ingestion, a transformation's
output, a join or a published dataset. Identify its owner, accepted inputs,
emitted schema and existing validation. Preserve the project's engine, runtime
and dependency choices; Pandera is an option when selected, not a prerequisite.
This method contributes to the current task or audit without opening another one.

## Define the guarantee

- Separate column presence/order and dtypes from nullability, allowed values,
  uniqueness and cross-column or cross-row rules. Missing columns and present
  columns containing nulls are different failures. Specify null/NaN treatment,
  empty-input behavior and whether extra columns are allowed.
- Establish uniqueness at the intended key, including composite keys, and join
  cardinality before trusting downstream totals. A per-batch check does not prove
  dataset-wide uniqueness or referential integrity.
- Make coercion a deliberate transformation. State whether parsing, rounding,
  timezone normalization, defaults, column filtering or invalid-row removal is
  allowed. Validate the returned object; do not discard normalized output or
  silently weaken a failure into successful publication.
- Treat inferred schemas and samples as evidence about observed data. Confirm
  business invariants with an authoritative contract before enforcing them.

## Place validation where it can prove the claim

Distinguish schema inspection, sampled checks, full value validation and
cross-partition checks in both implementation and audit findings. Name the
execution/materialization boundary and its memory/I/O cost. Schema resolution
can itself read metadata or remote sources; keep inputs within the selected scope.

For selected Pandera/Polars work, read [validation depth and failures](references/pandera.md).
For another backend, verify equivalent guarantees against its installed version.
Keep object/API validation and SQL constraints with their existing owners;
dataframe checks supplement those boundaries rather than replacing them.

## Evidence

Exercise a valid case and contract-breaking cases that still have plausible
schemas: duplicate keys across batches, invalid values, nulls, coercion failures
and a violated relation between columns. Check that failures prevent the intended
output and retain useful, bounded diagnostics without dumping sensitive rows.
Report checked scope and any unavailable runtime, unexecuted full scan or
dataset-wide invariant left unproven.

Primary references: [schema semantics](https://pandera.readthedocs.io/en/stable/dataframe_schemas.html),
[custom checks](https://pandera.readthedocs.io/en/stable/checks.html) and
[Polars schema resolution](https://docs.pola.rs/api/python/stable/reference/lazyframe/api/polars.LazyFrame.collect_schema.html).
Resolve project versions before applying current documentation.
