---
title: Plan PRIMARY KEY Before Table Creation
impact: CRITICAL
impactDescription: "Sort-key redesign can require table migration; plan from query evidence"
tags: [schema, primary-key, ORDER BY]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
