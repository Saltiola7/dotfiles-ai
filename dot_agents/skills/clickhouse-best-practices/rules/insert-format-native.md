---
title: Use Native Format for Best Insert Performance
impact: MEDIUM
impactDescription: "Native format is most efficient; JSONEachRow is expensive to parse"
tags: [insert, format, Native, performance]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
