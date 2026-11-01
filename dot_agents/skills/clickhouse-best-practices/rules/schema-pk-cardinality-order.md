---
title: Order Columns by Cardinality (Low to High)
impact: CRITICAL
impactDescription: "Balance predicate selectivity, cardinality and locality for the workload"
tags: [schema, primary-key, cardinality, ORDER BY]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
