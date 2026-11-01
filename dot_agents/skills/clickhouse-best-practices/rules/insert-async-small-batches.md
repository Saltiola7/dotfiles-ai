---
title: Use Async Inserts for High-Frequency Small Batches
impact: HIGH
impactDescription: "Server-side buffering when client batching isn't practical"
tags: [insert, async, buffering, small-batches]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
