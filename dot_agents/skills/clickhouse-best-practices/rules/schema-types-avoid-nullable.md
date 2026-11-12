---
title: Avoid Nullable Unless Semantically Required
impact: HIGH
impactDescription: "Nullable adds storage overhead; use DEFAULT values instead"
tags: [schema, data-types, Nullable, DEFAULT]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
