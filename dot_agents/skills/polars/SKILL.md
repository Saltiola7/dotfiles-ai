---
name: polars
description: Write, review or optimize actual Polars transformations, lazy queries, joins and sinks, or explicitly requested pandas-to-Polars migrations. Preserve the selected dataframe engine and project version; use for single-node Polars work.
license: MIT
metadata:
  author: Polars
  homepage: https://pola.rs
  tags: polars, python, dataframes, lazyframe, data-processing, data-analysis, data-transformation, analytics, sql, pandas
  runtime_compatibility: Examples target Polars 2.0; Polars 1.x differences are in references/lazy-api.md. Resolve the project's selected Python and Polars versions before applying examples.
---

# Polars

## Default stance

Use this skill when the project already uses Polars or the user explicitly
selects it. Preserve an existing pandas, DuckDB or other engine choice; installing
this skill does not select a dependency, migration or runtime upgrade. Work only
with the selected inputs and permitted output paths. Schema discovery, previews
and scans can perform I/O, including remote reads; keep them within task scope.

For a Polars transformation pipeline, prefer the lazy API: build the whole
query, then execute it at the intended output boundary, so Polars can optimize
the plan. On Polars 2.0, `.collect()` runs on the streaming engine, which
processes data in batches to reduce memory pressure. Do not collect
intermediate results: each `.collect()` materializes data and discards the
plan, so everything after it optimizes from scratch. Preserve a deliberately
eager interface or small operation when lazy execution adds no useful benefit.

**In-memory data can also benefit from a lazy pipeline.** When a query starts from a
`DataFrame` — a function argument, `pl.from_pandas(pdf)`,
`pl.DataFrame(...)`, or an earlier `collect()` — call `.lazy()` before the
first operation and `.collect()` at the end. `.lazy()` is free (it wraps the
data, it does not copy it) and it is what turns a step-by-step eager pipeline
into one optimized plan. Preserve the function's return type and execution boundary.

```python
# start from a file
pl.scan_csv("data.csv").filter(...).collect()

# start from an existing DataFrame — wrap it first
df.lazy().filter(...).group_by(...).agg(...).collect()

# avoid: eager, step by step, nothing to optimize
df = pl.read_csv("data.csv")
df.filter(...).group_by(...).agg(...)
```

## From question to insight

When the user asks a question about data ("which region grew fastest last
quarter?"), the goal is a correct answer in one shot: spend one cheap step
on schema discovery, then write the full query once. Read
`references/insight-recipes.md` first: it has ready-made query shapes
(top-k, period-over-period, distributions, time series, cohort-style
questions) and the sanity checks to run before answering.

1. **Discover the schema first. Never guess column names or dtypes.**

```python
lf = pl.scan_csv("sales.csv")        # or scan_parquet / scan_ndjson
print(lf.collect_schema())           # resolves names/dtypes; may read metadata/samples
print(lf.head(5).collect())          # eyeball values, formats, dirt
```

2. **Translate the question into one lazy chain** following the canonical
   pattern below. Map vague terms to explicit definitions and state them
   in the answer ("growth = revenue vs. previous quarter, percent").
3. **Handle dirt at the scan**, not downstream:
   `pl.scan_csv(path, null_values=["N/A", ""], try_parse_dates=True)`.
4. **Sanity-check the result** before answering.
5. **Answer with numbers, not just code.** Lead with the insight, show the
   supporting table, and keep the LazyFrame around so follow-ups extend the
   chain instead of rebuilding it.

## Core rules

- **Prefer equivalent native expressions.** Elementwise Python callbacks can
  add substantial interpreter overhead and limit optimization. A batch UDF can
  instead pass a whole Series to vectorized/native library code; it does not
  necessarily process every value in Python. Preserve a justified batch boundary,
  verify output dtype/null semantics and inspect the actual plan/performance.
- **Filter early when semantics permit.** Push source-column predicates before
  expensive operations; keep aggregate, computed-column and outer-join predicates
  at the boundary their meaning requires. Moving them can change results.
- **Group independent expressions when useful.** A lazy optimizer can cluster
  sequential independent `with_columns()` calls; repeated calls do not inherently
  serialize execution. Dependent expressions may need separate contexts. When the same operation applies
  to several columns, write one expression that expands over the schema
  instead of one per column. Rename the expanded set with `.name.suffix()` /
  `.name.prefix()`; `.alias()` names one output only. Selector forms and
  caveats: `references/expressions.md`.
- **Check actual dtypes and coercion.** Columns have defined dtypes, but Polars
  can coerce compatible types during operations. Inspect the schema and result
  dtype; cast explicitly where the contract requires it. Use
  `.cast(pl.Float64, strict=False)` to turn unparseable values into nulls
  instead of errors. Parse strings to dates and datetimes with
  `str.to_date()` / `str.to_datetime()`, not `.cast()`.
- **Investigate actionable warnings.** A performance warning signals a possible
  cost, not proof that a chosen operation is wrong. Apply an equivalent fix when
  warranted, preserving project warning policy and justified, narrowly scoped
  filters. `warnings.catch_warnings()` also supports testing/capture; it is not
  inherently suppression. Avoid blanket ignores that hide unresolved or new
  warnings, and document the reason for a deliberate exception.

```python
import polars.selectors as cs

# avoid: same operation, one expression per column
lf.with_columns([(pl.col(c) * 1.1).alias(f"{c}_adj") for c in ["a", "b", "c"]])

# prefer: one expression, expanded by the schema
lf.with_columns((pl.col("a", "b", "c") * 1.1).name.suffix("_adj"))
lf.with_columns(cs.numeric().fill_null(0))          # in place, same names
```

## Canonical query pattern

This example filters source rows before joining and aggregating. Adapt operation
order to the required semantics; joins and computed columns may expand data.

```python
customers = pl.scan_csv("customers.csv")

result = (
    pl.scan_csv("orders.csv")                    # 1. scan, never read
    .filter(pl.col("year") == 2024)              # 2. filter early
    .join(customers, on="customer_id", how="left")   # 3. join filtered data
    .with_columns(                               # 4. add computed columns
        (pl.col("revenue") - pl.col("cost")).alias("profit")
    )
    .group_by("region")                          # 5. group
    .agg(                                        # 6. aggregate
        pl.col("profit").sum().alias("total_profit"),
        pl.col("profit").mean().alias("avg_profit"),
        pl.len().alias("count"),
    )
    .filter(pl.col("count") > 10)                # 7. filter groups
    .sort("total_profit", descending=True)       # 8. sort
    .select("region", "total_profit", "avg_profit")  # 9. final columns
    .collect()                                   # 10. execute once
)
```

## SQL

Polars also runs SQL — `pl.sql(...)`, `lf.sql(...)`, `pl.SQLContext` — on
the same lazy engine, compiled to the same optimized plan. Use it when the
user writes or asks for SQL, or when porting SQL queries; otherwise write
expressions. Read `references/sql.md` before writing it for the entry points
and the few dialect differences.

## Gotchas

Each of these is easy to get wrong.

- **Strings in `then()`/`otherwise()` are column names, not values.**
  `pl.when(c).then("adult")` reads a column called `adult` (or raises
  `ColumnNotFoundError`). Wrap literals: `.then(pl.lit("adult"))`.
- **Null comparisons drop rows silently.** `filter(pl.col("v") > 2)`
  excludes nulls because `null > 2` is null, which is falsy. If nulls
  should be kept: `(pl.col("v") > 2) | pl.col("v").is_null()`.
- **Use `&`, `|`, `~` with parentheses around each condition.** Python's
  `and`/`or`/`not` raise on expressions, and without parentheses operator
  precedence binds the comparison wrong:
  `(pl.col("a") > 1) & (pl.col("b") < 5)`.
- **A bare aggregation in `with_columns()` broadcasts the global value to
  every row.** `with_columns(pl.col("v").mean())` fills the column with the
  overall mean — it does not error. Add `.over("group")` for the per-group
  value aligned to each row.
- **Duplicate output names raise `DuplicateError`.** A computed column
  keeps its source name; `select(pl.col("p"), pl.col("p") * 1.1)` fails.
  Always `.alias()` derived columns — or `.name.suffix(...)` for an expanded
  expression, which keeps every source name.
- **Regex column selection needs `^...$` anchors.** `pl.col("sales_.*")` is
  read as a literal column name and raises `ColumnNotFoundError`;
  `pl.col("^sales_.*$")` expands. One `col()` call cannot mix names with
  dtypes — use a selector instead.
- **Nulls don't match in joins by default.** Rows with null keys silently
  drop out of inner joins; pass `nulls_equal=True` if they should match.
- **Joins and group-bys don't keep row order.** End with `.sort()` when the
  order of the result matters, or pass `join(..., maintain_order="left")`
  to keep the left frame's order.

## Version and API verification

Before writing a method call you are not certain about, verify it against
the installed version rather than memory. Do not assume a pandas spelling
exists in Polars: there is no index, no `iloc`, no `groupby`. On Polars 1.x,
read the "On Polars 1.x" section at the end of `references/lazy-api.md`
first.

- **If the `polars-mcp` server's tools are available, use them:**
  `polars_search_api("filter")` finds methods by keyword,
  `polars_browse("Expr.str")` explores a namespace, and
  `polars_get_docstring("Expr.str.contains")` gets the exact signature.
- **Otherwise fetch the docs:** the top of `references/expressions.md` maps
  every expression category to its live URL on https://docs.pola.rs.

## When to load references

These reference files hold detail that is NOT in this file. When a task
matches one below, you MUST read that reference before writing code — do not
translate or answer from memory when a reference covers the task. Each file
opens with a `## Contents` line for jumping to a section.

- **Translating pandas → Polars** — MUST read
  `references/pandas-to-polars.md` first (it's short). It carries
  API-difference traps absent from this file.
- **Answering a natural-language data question** —
  `references/insight-recipes.md` (see "From question to insight" above).
- `references/contexts.md` — detailed behavior of `select`, `with_columns`,
  `filter`, `group_by`/`agg`, `over` (window mapping strategies), `sort`,
  and `join`.
- `references/expressions.md` — string, temporal, list, struct, expansion
  and selector syntax; casting; null handling; conditionals; plus the
  fetch-map described above.
- `references/lazy-api.md` — scan options for dirty data, query plan
  inspection with `explain()`, larger-than-memory data and sinks
  (`sink_parquet`), and the differences on Polars 1.x.
- `references/sql.md` — SQL entry points, mixing SQL with expressions,
  dialect notes, and the SQL reference fetch-map.
