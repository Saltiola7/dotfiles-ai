---
title: Use Incremental MVs for Real-Time Aggregations
impact: HIGH
impactDescription: "Read thousands of rows instead of billions; minimal cluster overhead"
tags: [query, materialized-view, aggregation, real-time]
---

> **Modified by dotfiles-ai.** This file differs from the pinned upstream source. See [UPSTREAM.md](../UPSTREAM.md) for attribution and adaptation details.

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
