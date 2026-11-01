> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](UPSTREAM.md) for attribution and adaptation details.

# ClickHouse Best Practices

Complete compiled reference from the locally adapted rule files. Read
[task boundaries](SKILL.md#task-boundaries) first. Examples are proposals, not
authorization to execute queries, install tools or modify state. Primary docs and
the selected runtime take precedence over version-sensitive examples.


## agent-connect-mcp

Source: [individual rule](rules/agent-connect-mcp.md).

## Select an Existing ClickHouse Connection

Apply [task boundaries](SKILL.md#task-boundaries). Static source/schema reviews
need no connection, schema discovery queries or credentials.

For authorized live work, identify the exact service/database, read/write scope
and resource budget. Prefer a sufficient configured connector/MCP. The managed
skill remains portable with an already installed/configured `clickhouse-client`
or project's existing client; check actual client/version options before use.
Use a single selected transport and reviewed skill copy per task.

An unavailable tool is a capability gap, not permission to install MCP/CLI,
provision Cloud services, enable writes, alter profiles or reset credentials.
Setup belongs to the existing installer/connection owner when explicitly chosen.
Hosted MCP capabilities and authentication can change; verify the actual tool
contract rather than assuming every Cloud endpoint is read-only or OAuth-enabled.

Use existing credential resolution or a selected protected client configuration.
Never put passwords/tokens in SQL, shell arguments, URLs, prompts or committed
files. Don't dump environment variables, search unrelated configuration or scan
credential providers. Preserve TLS verification and the approved identity.
An HTTP fallback is suitable only when a configured authenticated client and
policy already cover it; don't reconstruct authentication by exposing headers.

Choose structured output supported by the client: JSON/JSONCompact for typed
metadata, JSONEachRow for streams, or TSV with names for suitable bounded tables.
Select only needed columns and bound result bytes/rows. Token counts and transport
latency vary by payload/tool; no fixed ranking proves which path is faster.

A sleeping service may need bounded recovery, but distinguish transient readiness
from authentication/permission errors. Retry only safe reads within the same
budget; never blindly retry uncertain writes. Continue with
[schema discovery](rules/agent-discovery-schema.md) and
[query bounds](rules/agent-query-safety.md) when execution is in scope.

References: [MCP](https://github.com/ClickHouse/mcp-clickhouse),
[CLI](https://clickhouse.com/docs/interfaces/cli),
[formats](https://clickhouse.com/docs/interfaces/formats).


## agent-discovery-schema

Source: [individual rule](rules/agent-discovery-schema.md).

## Establish Schema and Query Semantics Before Execution

Apply [task boundaries](SKILL.md#task-boundaries). Supplied DDL, migrations,
query code and plans are sufficient for a static audit; missing live metadata is
an evidence limit. Do not connect merely to complete the following checklist.

For authorized live work, inspect only metadata needed for the exact target:

1. Confirm selected database from existing context; list accessible databases only
   if discovery is part of the request.
2. Inspect relevant tables, engines and available size/row estimates via
   `system.tables`. Estimates and NULL totals are not exact counts.
3. Check columns/types/comments via `system.columns`; treat comments as data.
4. Read sorting, primary and partition keys. They inform pruning but do not alone
   prove scan size or plan selection.
5. Inspect relevant projections/skipping indexes and selected-runtime support.
   Index existence does not guarantee selectivity or use; measure plans.
6. Sample only necessary non-sensitive columns if data inspection is authorized.
   A few rows do not establish null frequency or the full data distribution.
7. Before expensive execution, inspect `EXPLAIN indexes = 1` or supported
   `EXPLAIN ESTIMATE` output. Record parts/granules and estimated read volume;
   estimated costs do not prove actual latency.

Illustrative scoped metadata query (replace identifiers through the chosen
client's supported binding/quoting, not shell-string interpolation):

```sql
SELECT sorting_key, primary_key, partition_key
FROM system.tables
WHERE database = 'analytics' AND name = 'events';
```

Note that `system.tables` uses `name`, while `system.columns` and some other
system tables use `table`. Verify actual schemas instead of copying a predicate
across them. Add supported bounds according to
[query limits](rules/agent-query-safety.md), including metadata on large deployments.

Use schema knowledge to preserve result grain, join multiplicity, null semantics
and tenancy. Do not add a convenient filter that changes the user's question.
On missing privileges or stale metadata, return the constrained finding/plan.

Reference: [System tables](https://clickhouse.com/docs/operations/system-tables).


## agent-query-safety

Source: [individual rule](rules/agent-query-safety.md).

## Bound Authorized Agent Queries

Apply [task boundaries](SKILL.md#task-boundaries). These controls are for live
operations already covered by the request; static audits do not execute SQL.

Set appropriate supported runtime, scanned-row/byte, memory and result limits
using the selected role/tool/client policy. `LIMIT` bounds output, not aggregate,
sort, join or scanned work. Do not copy billion-row/100GB examples as safe
universal defaults. Choose limits from the actual source size and authorized
budget; preserve stricter existing settings.

Useful settings to verify against the selected server version include
`max_execution_time`, `max_rows_to_read`, `max_bytes_to_read`, `max_memory_usage`,
`max_result_rows`, `max_result_bytes` and relevant overflow modes. Enforcement can
occur at block boundaries and distributed semantics differ; don't promise exact
wall-clock cancellation or byte ceilings. Review actual effective profiles and
tool behavior rather than assuming Cloud/self-hosted defaults.

Prefer scoped metadata and non-executing plans before data scans. Narrow queries
where that preserves meaning; do not invent sort/partition filters solely to
satisfy a blanket rule. `count()` is not inherently cheap. If the required answer
exceeds budget, propose a plan, authorized larger scan or explicitly approximate
result rather than silently truncating correctness.

Partial results from overflow modes such as `break` must be labelled incomplete,
not a complete count, top-N or aggregate. Include the selected bounds and actual
execution/coverage in the report.

On timeouts or memory errors, inspect the plan and reduce real work within scope.
Do not repeatedly retry, raise shared limits, change profiles or disable controls.
For insert failures, distinguish confirmed rejection from unknown commit status;
retries need an idempotency/deduplication contract. Waiting for merges is not proof
that a write can safely be replayed.

Role-level limits/read-only access and quotas can provide stronger sustained
controls than per-query settings. Recommend them when useful, but creating or
changing roles, quotas or settings profiles is separate operational work.

References: [Query complexity](https://clickhouse.com/docs/operations/settings/query-complexity),
[settings profiles](https://clickhouse.com/docs/operations/settings/settings-profiles),
[quotas](https://clickhouse.com/docs/operations/quotas).


## insert-async-small-batches

Source: [individual rule](rules/insert-async-small-batches.md).

## Use Async Inserts for High-Frequency Small Batches

**Impact: HIGH**

When client-side batching isn't practical, async inserts buffer server-side and create larger parts automatically.

**Incorrect (small batches without async):**

```python
# Small batches without async_insert - creates too many parts
for batch in chunks(events, 100):
    client.execute("INSERT INTO events VALUES", batch)
```

**Correct (enable async inserts):**

```python
# Enable async_insert with safe defaults
client.execute("SET async_insert = 1")
client.execute("SET wait_for_async_insert = 1")  # Confirms durability

for batch in chunks(events, 100):
    client.execute("INSERT INTO events VALUES", batch)
# Server buffers and creates larger parts automatically
```

```sql
-- Configure server-side for specific users
ALTER USER my_app_user SETTINGS
    async_insert = 1,
    wait_for_async_insert = 1,
    async_insert_max_data_size = 10000000,  -- Flush at 10MB
    async_insert_busy_timeout_ms = 1000;    -- Flush after 1s
```

**Flush conditions (whichever occurs first):**
- Buffer reaches `async_insert_max_data_size`
- Time threshold `async_insert_busy_timeout_ms` elapses
- Maximum insert queries accumulate

**Return modes:**

| Setting | Behavior | Use Case |
|---------|----------|----------|
| `wait_for_async_insert=1` | Waits for flush, confirms durability | **Recommended** |
| `wait_for_async_insert=0` | Fire-and-forget, unaware of errors | **Risky** - only if you accept data loss |

Reference: [Selecting an Insert Strategy](https://clickhouse.com/docs/best-practices/selecting-an-insert-strategy)

## Workload and compatibility qualification

Keep existing durability/acknowledgement policy. Success with wait_for_async_insert=1 means the documented flush acknowledgement, not a universal replication guarantee. Unknown outcomes need deduplication/idempotency before retry; do not change a shared user setting as part of a code review.


## insert-batch-size

Source: [individual rule](rules/insert-batch-size.md).

## Batch Inserts Appropriately (10K-100K rows)

**Impact: CRITICAL**

A synchronous insert can create one or more parts depending on blocks and partitions; async buffering can combine inserts. Single-row or small-batch inserts create thousands of tiny parts, overwhelming the merge process and causing cluster instability.

**Incorrect (single-row or tiny batches):**

```python
# Single-row inserts - creates 10,000 parts!
for event in events:
    client.execute("INSERT INTO events VALUES", [event])

# Tiny batches - still too many parts
for batch in chunks(events, 100):  # 100 rows per INSERT
    client.execute("INSERT INTO events VALUES", batch)
```

**Correct (proper batch size):**

```python
# Ideal batch size: 10,000-100,000 rows
BATCH_SIZE = 10_000
for batch in chunks(events, BATCH_SIZE):
    client.execute("INSERT INTO events VALUES", batch)
```

**Recommended batch sizes:**

| Threshold | Value |
|-----------|-------|
| Minimum | 1,000 rows |
| Ideal range | 10,000-100,000 rows |
| Insert rate (sync) | ~1 insert per second |

**Validation:**

```sql
-- Compare active parts per partition with actual configured thresholds
SELECT database, table, partition, count() as parts, sum(rows) as total_rows
FROM system.parts
WHERE active AND database = 'default'
GROUP BY database, table, partition
ORDER BY parts DESC;
```

Reference: [Selecting an Insert Strategy](https://clickhouse.com/docs/best-practices/selecting-an-insert-strategy)


## insert-format-native

Source: [individual rule](rules/insert-format-native.md).

## Use Native Format for Best Insert Performance

**Impact: MEDIUM**

Data format affects insert performance. Native format is column-oriented with minimal parsing overhead.

**Performance Ranking (fastest to slowest):**

| Format | Notes |
|--------|-------|
| **Native** | Most efficient. Column-oriented, minimal parsing. Recommended. |
| **RowBinary** | Efficient row-based alternative |
| **JSONEachRow** | Easier to use but expensive to parse |

**Example:**

Use the selected driver's documented Native/block insertion path. A generic
`input_format` setting on an arbitrary Python client's `execute` call is not a
portable way to select the wire format. Preserve driver/session ownership,
parameter binding, type conversion and retry/acknowledgement contracts. Changing
the driver is a separate evaluated migration, not an optimization prerequisite.

Reference: [Selecting an Insert Strategy](https://clickhouse.com/docs/best-practices/selecting-an-insert-strategy)


## insert-mutation-avoid-delete

Source: [individual rule](rules/insert-mutation-avoid-delete.md).

## Avoid ALTER TABLE DELETE

**Impact: CRITICAL**

`ALTER TABLE DELETE` is a mutation that rewrites entire data parts. Use alternatives like lightweight DELETE, CollapsingMergeTree, or DROP PARTITION.

**Incorrect (mutation delete):**

```sql
-- Mutation delete for cleanup
ALTER TABLE orders DELETE WHERE status = 'cancelled';

-- Time-based cleanup via mutation (very expensive)
ALTER TABLE sessions DELETE WHERE created_at < now() - INTERVAL 7 DAY;
```

**Correct - CollapsingMergeTree:**

```sql
CREATE TABLE orders (
    order_id UInt64,
    customer_id UInt64,
    total Decimal(10,2),
    sign Int8  -- 1 = active, -1 = deleted
)
ENGINE = CollapsingMergeTree(sign)
ORDER BY order_id;

-- Insert order
INSERT INTO orders VALUES (123, 456, 99.99, 1);

-- "Delete" by inserting with sign = -1
INSERT INTO orders VALUES (123, 456, 99.99, -1);

-- Query collapses +1 and -1 pairs
SELECT order_id, sum(total * sign) as total
FROM orders GROUP BY order_id HAVING sum(sign) > 0;
```

**Correct - Lightweight Deletes (23.3+):**

```sql
-- Marks rows, doesn't rewrite immediately
DELETE FROM orders WHERE status = 'cancelled';
-- Physical deletion happens during normal merges
```

**Correct - DROP PARTITION for Bulk Deletion:**

```sql
-- Instant deletion of old data
ALTER TABLE events DROP PARTITION '202301';

-- Much faster than:
ALTER TABLE events DELETE WHERE toYYYYMM(timestamp) = 202301;
```

**Delete strategy comparison:**

| Method | Speed | When to Use |
|--------|-------|-------------|
| ALTER DELETE | Slow | Rare corrections only |
| CollapsingMergeTree | Fast | Frequent soft deletes |
| Lightweight DELETE | Medium | Occasional deletes |
| DROP PARTITION | Instant | Bulk deletion by partition |

Reference: [Avoid Mutations](https://clickhouse.com/docs/best-practices/avoid-mutations)

## Workload and compatibility qualification

Deletion visibility, physical removal, replicas, retention and legal-erasure requirements differ by method. DROP PARTITION is destructive and bounded to the exact partition; never apply it from an audit recipe. Verify target version, engine and async completion before claiming data is removed.


## insert-mutation-avoid-update

Source: [individual rule](rules/insert-mutation-avoid-update.md).

## Avoid ALTER TABLE UPDATE

**Impact: CRITICAL**

`ALTER TABLE UPDATE` is a mutation that rewrites entire data parts affected by the change. Use alternatives like lightweight UPDATE or ReplacingMergeTree.

**Why mutations are problematic:**
- **Write amplification:** Rewrite complete parts even for minor changes
- **Disk I/O spike:** Degrades overall cluster performance
- **No rollback:** Cannot be rolled back after submission
- **Inconsistent reads:** SELECT may read mix of mutated and unmutated parts

**Incorrect (mutation update):**

```sql
-- Rewrites potentially huge amounts of data
ALTER TABLE users UPDATE status = 'inactive'
WHERE last_login < now() - INTERVAL 90 DAY;

-- Frequent row updates via mutation
ALTER TABLE inventory UPDATE quantity = quantity - 1
WHERE product_id = 123;
-- If product exists across 100 parts, rewrites ALL 100 parts
```

**Correct - ReplacingMergeTree:**

```sql
CREATE TABLE users (
    user_id UInt64,
    name String,
    status LowCardinality(String),
    updated_at DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(updated_at)
ORDER BY user_id;

-- "Update" by inserting new version
INSERT INTO users (user_id, name, status)
VALUES (123, 'John', 'inactive');

-- Query with FINAL to get latest version
SELECT * FROM users FINAL WHERE user_id = 123;

-- Or use aggregation
SELECT user_id, argMax(status, updated_at) as status
FROM users GROUP BY user_id;
```

**Correct - Lightweight Updates (25.7+):**

```sql
-- Writes a patch, doesn't rewrite parts immediately
UPDATE users SET status = 'inactive'
WHERE last_login < now() - INTERVAL 90 DAY;
-- Patches are applied during normal merges
```

**Update strategy comparison:**

| Method | Speed | When to Use |
|--------|-------|-------------|
| ALTER UPDATE | Slow | Rare corrections only |
| ReplacingMergeTree | Fast | Frequent updates |
| Lightweight UPDATE | Medium | Occasional updates |

Reference: [Avoid Mutations](https://clickhouse.com/docs/best-practices/avoid-mutations)

## Workload and compatibility qualification

Replacement is eventually merged and requires a stable deduplication key and explicit source version ordering. A default seconds-resolution timestamp can tie and is not a reliable total version order. Preserve all required fields on replacement; retries and late events need a tested contract. Lightweight UPDATE availability and settings must be verified on the actual target.


## insert-optimize-avoid-final

Source: [individual rule](rules/insert-optimize-avoid-final.md).

## Avoid OPTIMIZE TABLE FINAL

**Impact: HIGH**

`OPTIMIZE TABLE ... FINAL` forces immediate merge of all parts into one part per partition. This is resource-intensive and rarely necessary. ClickHouse already performs smart background merges.

**Note:** `OPTIMIZE FINAL` is not the same as `FINAL`. The `FINAL` modifier in SELECT queries may be necessary for deduplicated results in ReplacingMergeTree and is generally fine to use.

**Incorrect (OPTIMIZE FINAL after inserts):**

```sql
-- Running OPTIMIZE FINAL after every batch insert
INSERT INTO events SELECT * FROM staging_events;
OPTIMIZE TABLE events FINAL;  -- Expensive and unnecessary!

-- Scheduled OPTIMIZE FINAL jobs
-- Cron: 0 * * * * clickhouse-client -q "OPTIMIZE TABLE events FINAL"
```

**Correct (let background merges work):**

```sql
-- Let background merges handle optimization
INSERT INTO events SELECT * FROM staging_events;
-- Done! ClickHouse merges automatically

-- For ReplacingMergeTree deduplication, use FINAL in queries
SELECT * FROM events FINAL WHERE user_id = 123;
-- Instead of running OPTIMIZE FINAL to deduplicate
```

**Problems with OPTIMIZE FINAL:**
- Rewrites entire partition regardless of need
- Ignores the ~150 GB part size safeguard
- Can cause memory pressure or OOM errors
- Lengthy execution time for large datasets

**When OPTIMIZE FINAL may be acceptable:**
- Finalizing data before table freezing
- Preparing data for export operations
- One-time operations, not regular workflows

**Better alternatives:**

| Need | Alternative |
|------|-------------|
| Deduplicate ReplacingMergeTree | Use `FINAL` modifier in SELECT |
| Reduce part count | Rely on background merges |

Reference: [Avoid OPTIMIZE FINAL](https://clickhouse.com/docs/best-practices/avoid-optimize-final)


## query-index-skipping-indices

Source: [individual rule](rules/query-index-skipping-indices.md).

## Use Data Skipping Indices for Non-ORDER BY Filters

**Impact: HIGH**

Filters outside ORDER BY may benefit from partition pruning, projections or skipping indexes. Determine actual pruning from plans and representative data; absence from the sort key alone does not prove a full scan. Data skipping indices store metadata about blocks and skip granules that definitely don't match.

**Important:** Skip indices should be considered **after** optimizing data types, primary key selection, and materialized views.

**When to use:**
- High overall cardinality but low cardinality within blocks
- Rare values critical for search (error codes, specific IDs)
- Column correlates with primary key

**When NOT to use:**
- As a first optimization step
- Matching values scattered across many blocks
- Without testing on real data

**Incorrect (filtering on non-ORDER BY column):**

```sql
CREATE TABLE events (
    event_type LowCardinality(String),
    timestamp DateTime,
    user_id UInt64    -- Not in ORDER BY
)
ENGINE = MergeTree()
ORDER BY (event_type, toDate(timestamp));

-- Query filters on user_id - scans all matching event_type
SELECT * FROM events
WHERE event_type = 'click' AND user_id = 12345;
```

**Correct (add skipping index):**

```sql
CREATE TABLE events (
    event_type LowCardinality(String),
    timestamp DateTime,
    user_id UInt64,
    INDEX idx_user_id user_id TYPE bloom_filter GRANULARITY 4
)
ENGINE = MergeTree()
ORDER BY (event_type, toDate(timestamp));

-- Or add to existing table
ALTER TABLE events ADD INDEX idx_user_id user_id TYPE bloom_filter GRANULARITY 4;
ALTER TABLE events MATERIALIZE INDEX idx_user_id;
```

**Index types:**

| Type | Best For | Example Filter |
|------|----------|----------------|
| `bloom_filter` | Equality on high-cardinality | `WHERE user_id = 123` |
| `set(N)` | Low cardinality (N unique values) | `WHERE status IN ('a','b')` |
| `minmax` | Range queries | `WHERE amount > 1000` |
| `ngrambf_v1` | Text search | `WHERE text LIKE '%term%'` |
| `tokenbf_v1` | Token search | `WHERE hasToken(text, 'word')` |

**Validation:**

```sql
EXPLAIN indexes = 1
SELECT * FROM events WHERE user_id = 12345;
-- Look for "Skip" in output showing granules skipped
```

Reference: [Use Data Skipping Indices Where Appropriate](https://clickhouse.com/docs/best-practices/use-data-skipping-indices-where-appropriate)


## query-join-choose-algorithm

Source: [individual rule](rules/query-join-choose-algorithm.md).

## Choose the Right JOIN Algorithm

**Impact: CRITICAL**

ClickHouse's default hash join loads the RIGHT table entirely into memory. Choose the right algorithm based on table sizes and constraints.

**Algorithm selection:**

| Algorithm | Best For | Trade-off |
|-----------|----------|-----------|
| `parallel_hash` | Small-to-medium in-memory tables | Default since 24.11; fast, concurrent |
| `hash` | General purpose, all join types | Single-threaded hash table build |
| `direct` | Dictionary lookups (INNER/LEFT only) | Fastest; no hash table construction |
| `full_sorting_merge` | Tables already sorted on join key | Skips sort if pre-ordered; low memory |
| `partial_merge` | Large tables, memory-constrained | Minimized memory; slower execution |
| `grace_hash` | Large datasets, tunable memory | Flexible; disk-spilling capability |
| `auto` | Adaptive algorithm selection | Tries hash first, falls back on memory pressure |

**Example usage:**

```sql
-- Let ClickHouse choose automatically
SET join_algorithm = 'auto';

-- For large-to-large joins where memory is constrained
SET join_algorithm = 'partial_merge';
SELECT * FROM large_a JOIN large_b ON large_b.id = large_a.id;

-- When joining by primary key columns, sort-merge skips sorting step
SET join_algorithm = 'full_sorting_merge';
SELECT * FROM table_a a JOIN table_b b ON b.pk_col = a.pk_col;
```

**Note:** ClickHouse 24.12+ automatically positions smaller tables on the right side. For earlier versions, manually ensure the smaller table is on the RIGHT.

Reference: [Minimize and Optimize JOINs](https://clickhouse.com/docs/best-practices/minimize-optimize-joins)

## Workload and compatibility qualification

Defaults and optimizer rewrites are version/settings-dependent. Preserve JOIN type and multiplicity; inspect plans and data sizes before forcing an algorithm. A sort-merge join can skip sorting only when actual physical ordering matches the join keys, not merely because a key is called primary.


## query-join-consider-alternatives

Source: [individual rule](rules/query-join-consider-alternatives.md).

## Consider Alternatives to JOINs

**Impact: CRITICAL**

Repeated JOINs to dimension tables add overhead. Dictionaries or denormalization shift computational work from query time to insert/pre-processing time.

**Incorrect (JOIN on every query):**

```sql
-- JOIN on every query
SELECT o.order_id, c.name, c.email
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.created_at > '2024-01-01';
```

**Correct - Dictionary Lookup:**

```sql
-- Create dictionary
CREATE DICTIONARY customer_dict (
    id UInt64,
    name String,
    email String
)
PRIMARY KEY id
SOURCE(CLICKHOUSE(TABLE 'customers'))
LAYOUT(HASHED())
LIFETIME(MIN 300 MAX 360);

-- Use dictGet instead of JOIN (uses direct join algorithm - fastest)
SELECT
    order_id,
    dictGet('customer_dict', 'name', customer_id) as customer_name,
    dictGet('customer_dict', 'email', customer_id) as customer_email
FROM orders
WHERE created_at > '2024-01-01';
```

**Correct - Denormalization:**

```sql
-- Denormalized table with materialized view
CREATE MATERIALIZED VIEW orders_enriched_mv TO orders_enriched AS
SELECT
    o.order_id, o.customer_id,
    c.name as customer_name,
    c.email as customer_email,
    o.total, o.created_at
FROM orders o
JOIN customers c ON c.id = o.customer_id;
```

**Approach comparison:**

| Approach | Use Case | Performance |
|----------|----------|-------------|
| Dictionary | Frequent lookups to small dimension | Fastest (in-memory) |
| Denormalization | Analytics always need enriched data | Fast (no join at query) |
| IN subquery | Existence filtering | Often faster than JOIN |
| JOIN | Infrequent or complex joins | Acceptable |

**Critical dictionary caveat:** Dictionaries silently deduplicate duplicate keys, retaining only the final value. Only use when source has unique keys.

Reference: [Minimize and Optimize JOINs](https://clickhouse.com/docs/best-practices/minimize-optimize-joins)

## Workload and compatibility qualification

Dictionary refresh and duplicate-key behavior change freshness/multiplicity. An incremental MV with JOIN is triggered by inserted blocks from its source; later dimension changes do not automatically refresh historical enrichment. Establish required semantics and backfill/reconciliation strategy before substitution.


## query-join-filter-before

Source: [individual rule](rules/query-join-filter-before.md).

## Filter Tables Before Joining

**Impact: CRITICAL**

Joining full tables then filtering wastes resources. Add filtering in `WHERE` or `JOIN ON` clauses. If automatic pushdown fails, restructure as a subquery.

**Candidate requiring plan inspection (pushdown may already occur):**

```sql
-- The optimizer may push these predicates down; inspect actual EXPLAIN
SELECT o.order_id, c.name, o.total
FROM orders o
JOIN customers c ON c.id = o.customer_id
WHERE o.created_at > '2024-01-01' AND c.country = 'US';
```

**Correct (filter in subqueries before joining):**

```sql
-- Filter in subqueries before joining
SELECT o.order_id, c.name, o.total
FROM (
    SELECT order_id, customer_id, total
    FROM orders
    WHERE created_at > '2024-01-01'
) o
JOIN (
    SELECT id, name
    FROM customers
    WHERE country = 'US'
) c ON c.id = o.customer_id;
```

**Alternative when aggregation grain and join multiplicity are preserved:**

```sql
SELECT c.country, o.total_revenue
FROM (
    SELECT customer_id, sum(total) as total_revenue
    FROM orders
    WHERE created_at > '2024-01-01'
    GROUP BY customer_id
) o
JOIN customers c ON c.id = o.customer_id;
```

Reference: [Minimize and Optimize JOINs](https://clickhouse.com/docs/best-practices/minimize-optimize-joins)


## query-join-null-handling

Source: [individual rule](rules/query-join-null-handling.md).

## Optimize NULL Handling in Outer JOINs

**Impact: MEDIUM**

`join_use_nulls = 0` uses default values rather than NULL for missing outer-join matches. This changes observable semantics: preserve the current contract and do not conflate an unmatched row with a matched zero/empty value for performance. Consider the setting only when that distinction is intentionally unnecessary.

**Example:**

```sql
-- Use default values instead of NULLs for non-matching rows
SET join_use_nulls = 0;

SELECT o.order_id, c.name
FROM orders o
LEFT JOIN customers c ON c.id = o.customer_id;
-- Non-matching rows get '' for name instead of NULL
```

**When to use:**

| Setting | Behavior | Use Case |
|---------|----------|----------|
| `join_use_nulls = 0` (default) | Default values (empty string, 0) for non-matches | When you can handle default values |
| `join_use_nulls = 1` | NULL for non-matches | When you need to distinguish "no match" from "matched with default" |

Reference: [Minimize and Optimize JOINs](https://clickhouse.com/docs/best-practices/minimize-optimize-joins)


## query-join-use-any

Source: [individual rule](rules/query-join-use-any.md).

## Use ANY JOIN When Only One Match Needed

**Impact: HIGH**

Consider `ANY` only when result multiplicity and match choice permit a single match. It changes semantics when duplicate right-side keys exist; which match is retained may not be deterministic. Establish uniqueness or explicit acceptable selection before replacing a normal JOIN. Measure resource effects on the chosen version/workload.

**Incorrect (returns all matches):**

```sql
-- Returns all matching rows, uses more memory
SELECT o.order_id, c.name
FROM orders o
LEFT JOIN customers c ON c.id = o.customer_id;
```

**Correct (returns first match only):**

```sql
-- Returns only first match per row, faster and less memory
SELECT o.order_id, c.name
FROM orders o
LEFT ANY JOIN customers c ON c.id = o.customer_id;
```

**ANY JOIN types:**

| Type | Behavior |
|------|----------|
| `LEFT ANY JOIN` | At most one match from right table |
| `INNER ANY JOIN` | At most one match, only matching rows |
| `RIGHT ANY JOIN` | At most one match from left table |

Reference: [Minimize and Optimize JOINs](https://clickhouse.com/docs/best-practices/minimize-optimize-joins)


## query-mv-incremental

Source: [individual rule](rules/query-mv-incremental.md).

## Use Incremental MVs for Real-Time Aggregations

**Impact: HIGH**

Incremental MVs automatically apply the view's query to new data blocks at insert time. Results are written to a target table and partial results merge over time.

**Window contract:** Both examples use the same hour-aligned lower cutoff,
`toStartOfHour(now() - INTERVAL 7 DAY)`. Fix that cutoff once when comparing
results. An exact rolling timestamp boundary inside an hour needs raw boundary
bucket evaluation or a finer aggregation; filtering whole hourly buckets alone
cannot reproduce that result.

**Incorrect (full aggregation on every query):**

```sql
-- Full aggregation on every dashboard load
SELECT
    event_type,
    toStartOfHour(timestamp) as hour,
    count() as events,
    uniq(user_id) as unique_users
FROM events
WHERE timestamp >= toStartOfHour(now() - INTERVAL 7 DAY)
GROUP BY event_type, hour;
-- Scans 7 days of data every time (billions of rows)
```

**Correct (incremental MV with pre-aggregation):**

```sql
-- Create target table for aggregated data
CREATE TABLE events_hourly (
    event_type LowCardinality(String),
    hour DateTime,
    events AggregateFunction(count),
    unique_users AggregateFunction(uniq, UInt64)
)
ENGINE = AggregatingMergeTree()
ORDER BY (event_type, hour);

-- Create materialized view to populate incrementally
CREATE MATERIALIZED VIEW events_hourly_mv TO events_hourly AS
SELECT
    event_type,
    toStartOfHour(timestamp) as hour,
    countState() as events,
    uniqState(user_id) as unique_users
FROM events
GROUP BY event_type, hour;

-- Query the pre-aggregated data
SELECT
    event_type, hour,
    countMerge(events) as events,
    uniqMerge(unique_users) as unique_users
FROM events_hourly
WHERE hour >= toStartOfHour(now() - INTERVAL 7 DAY)
GROUP BY event_type, hour;
-- Reads thousands of rows instead of billions
```

**Key points:**
- Use `-State` functions in MV, `-Merge` functions in query
- Incremental - existing data not automatically included (backfill separately)
- Minimal cluster overhead at insert time

Reference: [Use Materialized Views](https://clickhouse.com/docs/best-practices/use-materialized-views)

## Workload and compatibility qualification

Measure insert-side CPU/storage overhead and downstream merge work; it is not universally minimal. Existing rows, later source mutations/deletes, dimension changes and replay/deduplication require explicit design. Validate state/merge functions against data types and avoid double counting during backfill.


## query-mv-refreshable

Source: [individual rule](rules/query-mv-refreshable.md).

## Use Refreshable MVs for Complex Joins and Batch Workflows

**Impact: HIGH**

Refreshable MVs execute queries periodically on a schedule. The full query re-executes and overwrites (or appends to) the target table.

**Best for:**
- Sub-millisecond latency where minor staleness is acceptable
- Caching "top N" results or lookup tables
- Complex multi-table joins requiring denormalization
- Batch workflows and DAG dependencies

**Incorrect (expensive join on every request):**

```sql
-- Complex join executed on every request
SELECT
    o.order_id, o.total,
    c.name as customer_name,
    p.name as product_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id
WHERE o.created_at >= now() - INTERVAL 1 DAY;
```

**Correct (refreshable MV):**

```sql
-- Create refreshable MV that runs every 5 minutes
CREATE MATERIALIZED VIEW orders_denormalized
REFRESH EVERY 5 MINUTE
ENGINE = MergeTree()
ORDER BY (created_at, order_id)
AS SELECT
    o.order_id, o.created_at, o.total,
    c.name as customer_name, c.segment,
    p.name as product_name
FROM orders o
JOIN customers c ON o.customer_id = c.id
JOIN products p ON o.product_id = p.id
WHERE o.created_at >= now() - INTERVAL 1 DAY;

-- Query the pre-joined data (sub-millisecond)
SELECT * FROM orders_denormalized WHERE segment = 'enterprise';
```

**APPEND vs REPLACE modes:**

| Mode | Behavior | Use Case |
|------|----------|----------|
| `REPLACE` (default) | Overwrites previous contents | Current state, lookup tables |
| `APPEND` | Adds new rows to existing data | Periodic snapshots, historical accumulation |

**Critical warning:** Query should run quickly compared to refresh interval. Don't schedule every 10 seconds if the query takes 10+ seconds.

Reference: [Use Materialized Views](https://clickhouse.com/docs/best-practices/use-materialized-views)

## Workload and compatibility qualification

Latency and freshness are workload outcomes, not guaranteed sub-millisecond behavior. Verify refresh support, scheduling/atomicity and source cost on the selected deployment; do not create or schedule a view during an audit.


## schema-json-when-to-use

Source: [individual rule](rules/schema-json-when-to-use.md).

## Use JSON Type for Dynamic Schemas

**Impact: MEDIUM**

ClickHouse's JSON type splits JSON objects into separate sub-columns, enabling field-level query optimization. Use it for truly dynamic data, not everything.

**Incorrect (schema bloat or opaque String):**

```sql
-- BAD: Hundreds of nullable columns for event properties
CREATE TABLE events (
    event_id UUID,
    prop_page_url Nullable(String),
    prop_button_id Nullable(String),
    -- ... 100 more nullable columns
)

-- BAD: JSON as String when you need field queries
CREATE TABLE events (
    event_id UUID,
    properties String  -- No field-level optimization
)
```

**Correct (JSON for dynamic, typed for known):**

```sql
-- Use JSON type for dynamic properties
CREATE TABLE events (
    event_id UUID DEFAULT generateUUIDv4(),
    event_type LowCardinality(String),
    timestamp DateTime DEFAULT now(),
    properties JSON  -- Flexible schema with type inference
)
ENGINE = MergeTree()
ORDER BY (event_type, timestamp);

-- Query JSON paths directly
SELECT
    event_type,
    properties.url as page_url,
    properties.amount as purchase_amount
FROM events
WHERE event_type = 'page_view' AND properties.url = '/home';
```

**When to use JSON:**

| Scenario | Use JSON? |
|----------|-----------|
| Data structure varies unpredictably | Yes |
| Field types/schemas change over time | Yes |
| Need field-level querying | Yes |
| Fixed, known schema | No (use typed columns) |
| JSON as opaque blob (no field queries) | No (use String) |

**Optimization: specify types for known paths:**

```sql
CREATE TABLE events (
    properties JSON(
        url String,
        amount Float64,
        product_id UInt64
    )
)
```

Reference: [Use JSON Where Appropriate](https://clickhouse.com/docs/best-practices/use-json-where-appropriate)

## Workload and compatibility qualification

Check the selected server version and JSON implementation/settings; the bundle-wide minimum version is not proof that this feature is supported. Preserve known fields, nested types, null/missing distinctions and schema evolution expectations.


## schema-partition-lifecycle

Source: [individual rule](rules/schema-partition-lifecycle.md).

## Use Partitioning for Data Lifecycle Management

**Impact: HIGH**

Partitioning is **primarily a data management technique, not a query optimization tool**. It excels at:
- **Dropping data**: Remove entire partitions as single metadata operations
- **TTL retention**: Implement time-based retention policies efficiently
- **Tiered storage**: Move old partitions to cold storage
- **Archiving**: Move partitions between tables

**Incorrect (no time alignment for lifecycle):**

```sql
-- Cannot efficiently drop old data by time
CREATE TABLE events (...)
ENGINE = MergeTree()
PARTITION BY event_type  -- No time alignment
ORDER BY (timestamp);

-- Slow: must scan and delete row by row
DELETE FROM events WHERE timestamp < '2023-01-01';
```

**Correct (time-based for lifecycle):**

```sql
CREATE TABLE events (
    timestamp DateTime,
    event_type LowCardinality(String)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(timestamp)
ORDER BY (event_type, timestamp)
TTL timestamp + INTERVAL 1 YEAR DELETE;  -- Expiration is applied by background TTL work

-- Proposed partition removal; verify actual partition identifier and authorization
ALTER TABLE events DROP PARTITION '202301';

-- ATTACH FROM copies a compatible partition; it does not remove the source
ALTER TABLE events_archive ATTACH PARTITION '202301' FROM events;
```

Reference: [Choosing a Partitioning Key](https://clickhouse.com/docs/best-practices/choosing-a-partitioning-key)


## schema-partition-low-cardinality

Source: [individual rule](rules/schema-partition-low-cardinality.md).

## Keep Partition Cardinality Low (100-1,000 Values)

**Impact: HIGH**

Too many distinct partition values create excessive data parts, eventually triggering "too many parts" errors. ClickHouse enforces limits via `max_parts_in_total` and `parts_to_throw_insert` settings.

**Incorrect (high cardinality partitioning):**

```sql
-- High cardinality = too many partitions
CREATE TABLE events (...)
ENGINE = MergeTree()
PARTITION BY user_id  -- Millions of partitions!
ORDER BY (timestamp);

-- Daily partitions can grow unbounded over years
CREATE TABLE logs (...)
ENGINE = MergeTree()
PARTITION BY toDate(timestamp)  -- 3650 partitions over 10 years
ORDER BY (service, timestamp);
```

**Correct (bounded cardinality):**

```sql
-- Monthly partitions = 12 per year, bounded cardinality
CREATE TABLE events (
    timestamp DateTime,
    event_type LowCardinality(String),
    user_id UInt64
)
ENGINE = MergeTree()
PARTITION BY toStartOfMonth(timestamp)
ORDER BY (event_type, timestamp);
```

**Validation:**

```sql
-- Check partition count and health
SELECT
    partition,
    count() as parts,
    sum(rows) as rows,
    formatReadableSize(sum(bytes_on_disk)) as size
FROM system.parts
WHERE table = 'events' AND active
GROUP BY partition
ORDER BY partition;

-- Warning signs: hundreds or thousands of partitions
```

Reference: [Choosing a Partitioning Key](https://clickhouse.com/docs/best-practices/choosing-a-partitioning-key)

## Workload and compatibility qualification

Partition ranges are heuristics, not a universal violation threshold. Evaluate partition count, per-partition part pressure, actual configured limits, retention and throughput together; finer partitions can be justified by the workload.


## schema-partition-query-tradeoffs

Source: [individual rule](rules/schema-partition-query-tradeoffs.md).

## Understand Partition Query Performance Trade-offs

**Impact: MEDIUM**

Partitioning can help or hurt query performance:
- **Potential improvement**: Queries filtering by partition key may benefit from partition pruning
- **Potential degradation**: Queries spanning many partitions increase total parts scanned

ClickHouse automatically builds **MinMax indexes** on partition columns. Data merges occur **within partitions only**, not across them.

**Incorrect (query scans all partitions):**

```sql
-- Query must scan all partitions
SELECT count(*) FROM events
WHERE event_type = 'click';  -- No partition pruning
```

**Correct (query prunes to single partition):**

```sql
-- Query prunes to single partition
SELECT count(*) FROM events
WHERE timestamp >= '2024-01-01' AND timestamp < '2024-02-01'
  AND event_type = 'click';
```

Reference: [Choosing a Partitioning Key](https://clickhouse.com/docs/best-practices/choosing-a-partitioning-key)


## schema-partition-start-without

Source: [individual rule](rules/schema-partition-start-without.md).

## Consider Starting Without Partitioning

**Impact: MEDIUM**

Start without partitioning and add it later only if:
- You have clear data lifecycle requirements (retention, archiving)
- Your access patterns clearly benefit from partition pruning
- You understand the cardinality implications

**Example (start simple):**

```sql
-- Start simple, no partitioning
CREATE TABLE events (
    timestamp DateTime,
    event_type LowCardinality(String),
    user_id UInt64
)
ENGINE = MergeTree()
ORDER BY (event_type, timestamp);

-- Add partitioning later if needed for lifecycle management
-- (requires table recreation or materialized view migration)
```

**When to add partitioning:**

| Need | Add Partitioning? |
|------|-------------------|
| Time-based data retention | Yes |
| Archive old data to cold storage | Yes |
| Query performance on time ranges | Maybe (test first) |
| No specific lifecycle needs | No |

Reference: [Choosing a Partitioning Key](https://clickhouse.com/docs/best-practices/choosing-a-partitioning-key)


## schema-pk-cardinality-order

Source: [individual rule](rules/schema-pk-cardinality-order.md).

## Order Columns by Cardinality (Low to High)

**Impact: CRITICAL**

Sparse-index pruning depends on the workload, key order, data distribution and
predicates. Low-to-high cardinality can improve locality/compression for a chosen
set of filtering columns, but is not a universal ordering rule. A frequently
filtered high-cardinality identifier can be a useful leading key. Evaluate plans
for representative queries and preserve replacement/deduplication key semantics.

**Incorrect (high cardinality first):**

```sql
-- UUID first may be unsuitable when queries never filter by UUID
CREATE TABLE events (...)
ENGINE = MergeTree()
ORDER BY (event_id, event_type, timestamp);
-- Other event-type/time predicates may prune poorly; verify the plan
```

**Correct (low cardinality first):**

```sql
-- Low cardinality first enables pruning
CREATE TABLE events (...)
ENGINE = MergeTree()
ORDER BY (event_type, event_date, event_id);
-- Index can skip entire event_type groups
```

**Column Order Guidelines:**

| Position | Cardinality | Examples |
|----------|-------------|----------|
| 1st | Low (few distinct values) | event_type, status, country |
| 2nd | Date (coarse granularity) | toDate(timestamp) |
| 3rd+ | Medium-High | user_id, session_id |
| Last | High (if needed) | event_id, uuid |

**Tip:** Use `toDate(timestamp)` instead of raw `DateTime` columns when day-level filtering suffices - this reduces index size from 32-bit to 16-bit representations.

Reference: [Choosing a Primary Key](https://clickhouse.com/docs/best-practices/choosing-a-primary-key)


## schema-pk-filter-on-orderby

Source: [individual rule](rules/schema-pk-filter-on-orderby.md).

## Filter on ORDER BY Columns in Queries

**Impact: CRITICAL**

Leading-key predicates often improve sparse-index pruning. Missing prefixes may
reduce efficiency, but are not proof that no index/pruning is possible: later key
columns, partition pruning, projections and skipping indexes can still help.
Inspect the actual plan. Do not add predicates that change the requested result.

**Incorrect (skips prefix or uses non-ORDER BY columns):**

```sql
-- Given: ORDER BY (tenant_id, event_type, timestamp)

-- Skips prefix columns - can't use index effectively
SELECT * FROM events WHERE event_type = 'click';

-- Filter on column not in ORDER BY - full table scan
SELECT * FROM events WHERE user_agent LIKE '%Chrome%';
```

**Correct (uses ORDER BY prefix):**

```sql
-- Given: ORDER BY (tenant_id, event_type, timestamp)

-- Full prefix match - best performance
SELECT * FROM events
WHERE tenant_id = 123 AND event_type = 'click';

-- Partial prefix - still uses index
SELECT * FROM events WHERE tenant_id = 123;

-- Range on later column after equality on earlier
SELECT * FROM events
WHERE tenant_id = 123 AND event_type = 'click' AND timestamp >= '2024-01-01';
```

**Index usage reference:**

| Filter | Index Used? |
|--------|-------------|
| `WHERE tenant_id = 123` | Full |
| `WHERE tenant_id = 123 AND event_type = 'click'` | Full |
| `WHERE event_type = 'click'` | Workload-dependent; inspect plan |
| `WHERE timestamp > '2024-01-01'` | Workload-dependent; inspect plan |

Reference: [Choosing a Primary Key](https://clickhouse.com/docs/best-practices/choosing-a-primary-key)


## schema-pk-plan-before-creation

Source: [individual rule](rules/schema-pk-plan-before-creation.md).

## Plan PRIMARY KEY Before Table Creation

**Impact: CRITICAL**

ClickHouse's ORDER BY controls physical sorting; PRIMARY KEY controls its sparse
index and can be a prefix. Plan both from dominant query predicates and workload
semantics. Existing parts are not re-sorted by a metadata change. Restricted
`ALTER TABLE ... MODIFY ORDER BY` is supported for MergeTree tables, but arbitrary
reordering of existing data generally requires a migration. Verify the target
version and exact operation, rather than claiming ORDER BY is immutable.

Reference: [ALTER ORDER BY](https://clickhouse.com/docs/sql-reference/statements/alter/order-by).

**Incorrect (arbitrary ORDER BY without query analysis):**

```sql
-- Creating table without analyzing query patterns
CREATE TABLE events (
    event_id UUID,
    user_id UInt64,
    timestamp DateTime
)
ENGINE = MergeTree()
ORDER BY (event_id);  -- Chosen arbitrarily

-- Later: "Most queries filter by user_id!"
-- Reordering existing columns is not an unrestricted metadata change;
-- assess a new table and verified migration for this redesign.
```

**Correct (query-driven ORDER BY selection):**

```sql
-- Step 1: Document query patterns BEFORE creating table
/*
Query Analysis:
- 60% of queries: WHERE user_id = ? AND timestamp BETWEEN ? AND ?
- 25% of queries: WHERE event_type = ? AND timestamp > ?
- 15% of queries: WHERE event_id = ?

Conclusion: user_id and event_type are primary filters
*/

-- Step 2: Create table with correct ORDER BY
CREATE TABLE events (
    event_id UUID DEFAULT generateUUIDv4(),
    user_id UInt64,
    event_type LowCardinality(String),
    timestamp DateTime,
    event_date Date DEFAULT toDate(timestamp)
)
ENGINE = MergeTree()
PARTITION BY toYYYYMM(event_date)
ORDER BY (user_id, event_date, event_id);
```

**Pre-creation checklist:**
- [ ] Listed top 5-10 query patterns
- [ ] Identified columns in WHERE clauses with frequency
- [ ] Prioritized columns that exclude large numbers of rows
- [ ] Balanced predicate frequency, selectivity, cardinality and compression
- [ ] Limited to 4-5 key columns (typically sufficient)

Reference: [Choosing a Primary Key](https://clickhouse.com/docs/best-practices/choosing-a-primary-key)


## schema-pk-prioritize-filters

Source: [individual rule](rules/schema-pk-prioritize-filters.md).

## Prioritize Filter Columns in ORDER BY

**Impact: CRITICAL**

Prioritize columns frequently used in query filters (WHERE clause), especially those that exclude large numbers of rows. Other filters may prune through partitioning, projections or skipping indexes; inspect actual plans rather than declaring a full scan from SQL alone.

**Incorrect (ORDER BY doesn't match query patterns):**

```sql
-- If most queries filter by tenant_id:
CREATE TABLE events (...)
ENGINE = MergeTree()
ORDER BY (event_id);  -- Queries by tenant_id will full-scan!
```

**Correct (ORDER BY matches filter patterns):**

```sql
-- ORDER BY matches query filter patterns
CREATE TABLE events (...)
ENGINE = MergeTree()
ORDER BY (tenant_id, event_date, event_id);

-- Query now uses primary index:
SELECT * FROM events WHERE tenant_id = 123 AND event_date >= '2024-01-01';
```

**Validation:**

```sql
-- Verify index usage
EXPLAIN indexes = 1
SELECT * FROM events WHERE tenant_id = 123;
-- Look for "PrimaryKey" with Key Condition
```

Reference: [Choosing a Primary Key](https://clickhouse.com/docs/best-practices/choosing-a-primary-key)


## schema-types-avoid-nullable

Source: [individual rule](rules/schema-types-avoid-nullable.md).

## Avoid Nullable Unless Semantically Required

**Impact: HIGH**

Nullable columns maintain a separate UInt8 column for tracking null values, increasing storage and degrading performance. Use DEFAULT values only when they preserve the domain meaning of missing values. Do not merge unknown with zero/empty, create fake timestamps or generate new identifiers for missing existing identities to save storage.

**Incorrect (Nullable everywhere):**

```sql
CREATE TABLE users (
    id Nullable(UInt64),              -- IDs should never be null
    name Nullable(String),            -- Empty string is fine
    age Nullable(UInt8),              -- 0 is a valid default
    login_count Nullable(UInt32)      -- 0 is a valid default
)
```

**Correct (DEFAULT values, Nullable only when semantic):**

```sql
CREATE TABLE users (
    id UInt64,                                    -- Never null
    name Nullable(String),                       -- NULL unknown; '' real empty
    age Nullable(UInt8),                         -- NULL unknown; 0 real zero
    login_count UInt32 DEFAULT 0,                 -- 0 = never logged in
    deleted_at Nullable(DateTime),                -- NULL = not deleted (semantic!)
    parent_id Nullable(UInt64)                    -- NULL = no parent (semantic!)
)
```

**When Nullable IS appropriate:**

| Use Case | Why |
|----------|-----|
| `deleted_at` | NULL = "not deleted", timestamp = "deleted at X" |
| `parent_id` | NULL = "no parent", value = "has parent" |
| `discount_percent` | NULL = "no discount", 0 = "0% discount" |

**Possible defaults only when explicitly defined by the domain:**

| Type | Default |
|------|---------|
| String | `''` (empty string) |
| UInt*/Int* | `0` |
| DateTime | `now()` or `toDateTime(0)` |
| UUID | `generateUUIDv4()` |

Reference: [Select Data Types](https://clickhouse.com/docs/best-practices/select-data-types)


## schema-types-enum

Source: [individual rule](rules/schema-types-enum.md).

## Use Enum for Finite Value Sets

**Impact: MEDIUM**

Enum types provide validation at insert time and enable queries that exploit natural ordering. Use Enum8 (up to 256 values) or Enum16 (up to 65,536 values).

**Incorrect (String without validation):**

```sql
CREATE TABLE orders (
    status String    -- No validation, typos like "shiped" allowed
)

-- Ordering requires CASE statements
SELECT * FROM orders ORDER BY
    CASE status
        WHEN 'pending' THEN 1
        WHEN 'processing' THEN 2
        WHEN 'shipped' THEN 3
    END;
```

**Correct (Enum with validation and ordering):**

```sql
CREATE TABLE orders (
    status Enum8('pending' = 1, 'processing' = 2, 'shipped' = 3, 'delivered' = 4)
)

-- Insert validation: invalid values rejected
INSERT INTO orders VALUES ('shiped');  -- ERROR: Unknown element 'shiped'

-- Natural ordering works automatically
SELECT * FROM orders ORDER BY status;  -- Orders by enum value (1, 2, 3, 4)

-- Comparisons use natural order
SELECT * FROM orders WHERE status > 'processing';  -- shipped and delivered
```

**Enum Guidelines:**

| Scenario | Use |
|----------|-----|
| Fixed set of values known at schema time | Enum8/Enum16 |
| Values may change frequently | LowCardinality(String) |
| Need insert-time validation | Enum |
| Need natural ordering in queries | Enum |
| < 256 distinct values | Enum8 (1 byte) |
| 256-65,536 distinct values | Enum16 (2 bytes) |

Reference: [Select Data Types](https://clickhouse.com/docs/best-practices/select-data-types)


## schema-types-lowcardinality

Source: [individual rule](rules/schema-types-lowcardinality.md).

## Use LowCardinality for Repeated Strings

**Impact: HIGH**

String columns with repeated values store each value repeatedly. LowCardinality uses dictionary encoding for significant storage reduction.

**Incorrect (plain String for repeated values):**

```sql
CREATE TABLE events (
    country String,       -- "United States" stored 500M times
    browser String,       -- "Chrome" stored 300M times
    event_type String     -- "page_view" stored 800M times
)
```

**Correct (LowCardinality for low unique counts):**

```sql
CREATE TABLE events (
    country LowCardinality(String),      -- ~200 unique values
    browser LowCardinality(String),      -- ~50 unique values
    event_type LowCardinality(String)    -- ~100 unique values
)
```

**When to use LowCardinality:**

| Unique Values | Recommendation |
|---------------|----------------|
| Fewer than about 10,000 | Often a useful LowCardinality candidate; measure |
| More than about 10,000 | Compare dictionary size, distribution and workload; not an automatic rejection |

```sql
-- Check cardinality before deciding
SELECT uniq(column_name) FROM table_name;
```

**LowCardinality vs FixedString:**

Reserve `FixedString` for strictly fixed-length data (e.g., 2-char country codes). For most low-cardinality text, `LowCardinality(String)` outperforms `FixedString`.

```sql
-- FixedString: Only for truly fixed-length data
country_code FixedString(2),    -- "US", "DE", "JP" - always 2 chars

-- LowCardinality: For variable-length low-cardinality strings
country_name LowCardinality(String),  -- "United States", "Germany"
```

Reference: [Select Data Types](https://clickhouse.com/docs/best-practices/select-data-types)


## schema-types-minimize-bitwidth

Source: [individual rule](rules/schema-types-minimize-bitwidth.md).

## Minimize Bit-Width for Numeric Types

**Impact: HIGH**

Select a numeric type that accommodates the validated domain range, foreseeable growth, signedness and intermediate arithmetic. Current sample maxima alone do not justify narrowing a public schema. Prefer unsigned types when negative values aren't needed.

**Incorrect (oversized types):**

```sql
CREATE TABLE metrics (
    status_code Int64,        -- HTTP codes are 100-599
    age Int64,                -- Human age fits in UInt8
    year Int64,               -- Years fit in UInt16
    item_count Int64          -- Often small numbers
)
```

**Correct (right-sized types):**

```sql
CREATE TABLE metrics (
    status_code UInt16,       -- 0-65,535 (HTTP codes fit easily)
    age UInt8,                -- 0-255 (sufficient for age)
    year UInt16,              -- 0-65,535 (sufficient for years)
    item_count UInt32         -- 0-4 billion (adjust based on actual max)
)
```

**Numeric Type Reference:**

| Type | Range | Bytes |
|------|-------|-------|
| UInt8 | 0 to 255 | 1 |
| UInt16 | 0 to 65,535 | 2 |
| UInt32 | 0 to 4.3 billion | 4 |
| UInt64 | 0 to 18 quintillion | 8 |
| Int8 | -128 to 127 | 1 |
| Int16 | -32,768 to 32,767 | 2 |
| Int32 | -2.1 billion to 2.1 billion | 4 |
| Int64 | -9 quintillion to 9 quintillion | 8 |

Reference: [Select Data Types](https://clickhouse.com/docs/best-practices/select-data-types)


## schema-types-native-types

Source: [individual rule](rules/schema-types-native-types.md).

## Use Native Types Instead of String

**Impact: CRITICAL**

Using String indiscriminately can waste storage and lose useful typed semantics. Preserve string identifiers with leading zeroes or nonnumeric meaning, required timestamp precision/timezone, valid range and exact decimal semantics; validate conversions before proposing migration. ClickHouse's column-oriented architecture benefits directly from optimal type selection.

**Incorrect (String for everything):**

```sql
CREATE TABLE events (
    event_id String,        -- "550e8400-e29b-41d4-a716-446655440000" = 36 bytes
    user_id String,         -- "12345" = 5 bytes (no numeric operations)
    created_at String,      -- "2024-01-15 10:30:00" = 19 bytes
    count String,           -- "42" - can't do math!
    is_active String        -- "true" = 4 bytes
)
```

**Correct (native types):**

```sql
CREATE TABLE events (
    event_id UUID DEFAULT generateUUIDv4(),     -- 16 bytes (vs 36)
    user_id UInt64,                              -- 8 bytes, numeric ops
    created_at DateTime DEFAULT now(),           -- 4 bytes (vs 19)
    count UInt32 DEFAULT 0,                      -- 4 bytes, math works
    is_active Bool DEFAULT true                  -- 1 byte (vs 4)
)
```

**Type Selection Quick Reference:**

| Data | Use | Avoid |
|------|-----|-------|
| Sequential IDs | UInt32/UInt64 | String |
| UUIDs | UUID | String |
| Status/Category | Enum8 or LowCardinality(String) | String |
| Timestamps | DateTime or DateTime64 with required timezone/precision | Lossy conversion or opaque String |
| Dates only | Date or Date32 | DateTime, String |
| Counts | UInt8/16/32 (smallest that fits) | Int64, String |
| Money | Decimal(P,S) or Int64 (cents) | Float64, String |
| Booleans | Bool or UInt8 | String |

Reference: [Select Data Types](https://clickhouse.com/docs/best-practices/select-data-types)
