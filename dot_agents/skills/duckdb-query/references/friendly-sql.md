# DuckDB Friendly SQL

Apply [query task boundaries](../SKILL.md). These syntax examples are not
instructions to execute writes, attach sources or change schemas. Verify feature
availability against the selected runtime and primary docs. Prefer constructs
that simplify the actual query; avoid changing result grain, ordering or null
semantics merely to use a newer idiom. `SUMMARIZE` can scan the source, and an
explicit ORDER BY is needed when consumers depend on order.


When generating SQL, prefer these idiomatic DuckDB constructs:

### Compact clauses
- **FROM-first**: `FROM table WHERE x > 10` (implicit `SELECT *`)
- **GROUP BY ALL**: auto-groups by all non-aggregate columns
- **ORDER BY ALL**: orders by all columns for deterministic results
- **SELECT * EXCLUDE (col1, col2)**: drop columns from wildcard
- **SELECT * REPLACE (expr AS col)**: transform a column in-place
- **UNION ALL BY NAME**: combine tables with different column orders
- **Percentage LIMIT**: `LIMIT 10%` returns a percentage of rows
- **Prefix aliases**: `SELECT x: 42` instead of `SELECT 42 AS x`
- **Trailing commas** allowed in SELECT lists

### Query features
- **count()**: no need for `count(*)`
- **Reusable aliases**: use column aliases in WHERE / GROUP BY / HAVING
- **Lateral column aliases**: `SELECT i+1 AS j, j+2 AS k`
- **COLUMNS(*)**: apply expressions across columns; supports regex, EXCLUDE, REPLACE, lambdas
- **FILTER clause**: `count() FILTER (WHERE x > 10)` for conditional aggregation
- **GROUPING SETS / CUBE / ROLLUP**: advanced multi-level aggregation
- **Top-N per group**: `max(col, 3)` returns top 3 as a list; also `arg_max(arg, val, n)`, `min_by(arg, val, n)`
- **DESCRIBE table_name**: schema summary (column names and types)
- **SUMMARIZE table_name**: statistical profile (potential full scan)
- **PIVOT / UNPIVOT**: reshape between wide and long formats
- **SET VARIABLE x = expr**: define SQL-level variables, reference with `getvariable('x')`

### Data import
- **Direct file queries**: `FROM 'file.csv'`, `FROM 'data.parquet'`
- **Globbing**: `FROM 'data/part-*.parquet'` reads multiple files
- **Auto-detection**: CSV headers and schemas are inferred automatically

### Expressions and types
- **Dot operator chaining**: `'hello'.upper()` or `col.trim().lower()`
- **List comprehensions**: `[x*2 FOR x IN list_col]`
- **List/string slicing**: `col[1:3]`, negative indexing `col[-1]`
- **STRUCT.* notation**: `SELECT s.* FROM (SELECT {'a': 1, 'b': 2} AS s)`
- **Square bracket lists**: `[1, 2, 3]`
- **format()**: `format('{}->{}', a, b)` for string formatting

### Joins
- **ASOF joins**: approximate matching on ordered data (e.g. timestamps)
- **POSITIONAL joins**: match rows by position, not keys
- **LATERAL joins**: reference prior table expressions in subqueries

### Data modification
- **CREATE OR REPLACE TABLE**: no need for `DROP TABLE IF EXISTS` first
- **CREATE TABLE ... AS SELECT (CTAS)**: create tables from query results
- **INSERT INTO ... BY NAME**: match columns by name, not position
- **INSERT OR IGNORE INTO / INSERT OR REPLACE INTO**: upsert patterns
