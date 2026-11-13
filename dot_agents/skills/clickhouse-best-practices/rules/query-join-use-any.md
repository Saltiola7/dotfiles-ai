---
title: Use ANY JOIN When Only One Match Needed
impact: HIGH
impactDescription: "Returns first match only; less memory and faster execution"
tags: [query, JOIN, ANY, performance]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
