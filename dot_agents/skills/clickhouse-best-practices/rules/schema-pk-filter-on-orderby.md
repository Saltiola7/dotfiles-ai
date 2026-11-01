---
title: Filter on ORDER BY Columns in Queries
impact: CRITICAL
impactDescription: "Leading-key predicates often improve pruning; verify actual plans"
tags: [schema, primary-key, WHERE, query]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
