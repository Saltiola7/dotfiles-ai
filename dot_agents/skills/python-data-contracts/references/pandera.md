# Selected Pandera and Polars Boundaries

Use this reference only when Pandera is already selected or the task explicitly
requests it. Resolve the installed Pandera version, dataframe backend and
validation configuration before choosing APIs; backend feature support differs.

For Pandera's Polars backend, the documented default for a `LazyFrame` is
schema-level validation. Successful validation of that plan does not prove
positive amounts, non-null keys or other value predicates. Validating a
materialized `DataFrame` performs schema and data checks. A deliberately selected
`SCHEMA_AND_DATA` validation depth can also run value checks on a `LazyFrame`,
making internal collection necessary while still returning a lazy object. Make
that execution cost visible; prefer a scoped setting over changing unrelated
validation globally.

`validate(..., lazy=True)` controls error aggregation. It does not select Polars
lazy execution or enable data-level checks. Aggregated failures use
`SchemaErrors`; fail-fast validation uses `SchemaError`. Translate only expected
validation failures at the boundary, preserving failure status and bounded
failure counts/identifiers. Raw failure cases may contain sensitive input.

Coercion/parsers can alter returned data or defer errors until collection. Test
the actual downstream output, not only whether schema construction succeeds.
Use a typed but invalid value to prove a value check really executes. Separately
test duplicate keys split across batches; local validation cannot establish a
global key guarantee without appropriate shared state or a global check.

Sources: [Polars validation behavior and depth](https://pandera.readthedocs.io/en/stable/polars.html),
[error aggregation](https://pandera.readthedocs.io/en/stable/lazy_validation.html).
