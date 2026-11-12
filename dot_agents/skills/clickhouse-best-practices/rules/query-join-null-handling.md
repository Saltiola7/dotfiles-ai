---
title: Optimize NULL Handling in Outer JOINs
impact: MEDIUM
impactDescription: "Default values instead of NULL reduces memory overhead"
tags: [query, JOIN, NULL, memory]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
